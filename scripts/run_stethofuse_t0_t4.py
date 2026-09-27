"""Execute frozen T0-T4 preparation and tiny overfit gate; never runs T5."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_data import (audit_manifest, frozen_validation_recipes,
                                  materialize_recipe, read_manifest,
                                  training_epoch, write_json)
from app.ml.training_objective import fixed_label_loss, normalized_l1
from scripts.evaluate_ensemble_qualification import si_sdr


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def git_worktree_dirty() -> bool | None:
    try:
        output = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT,
                                         text=True, stderr=subprocess.DEVNULL)
        return bool(output.strip())
    except Exception:
        return None


def metric_rows(model: StethoFuseConvTasNet, mixtures: list[torch.Tensor],
                targets: list[torch.Tensor]) -> list[dict[str, float]]:
    rows = []
    model.eval()
    with torch.inference_mode():
        for mix, target in zip(mixtures, targets):
            estimate = model(mix)
            estimates = estimate[0].cpu().numpy()
            refs = target[0].cpu().numpy()
            source = []
            for index in range(2):
                score = si_sdr(estimates[index], refs[index])
                baseline = si_sdr(mix[0, 0].cpu().numpy(), refs[index])
                source.append({"si_sdr_db": score, "si_sdri_db": score - baseline,
                               "normalized_l1": float(normalized_l1(
                                   estimate[:, index:index + 1], target[:, index:index + 1]).item())})
            rows.append({"heart": source[0], "lung": source[1],
                         "max_additivity_error": float((estimate.sum(1, keepdim=True) - mix).abs().max())})
    model.train()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overfit", action="store_true", help="Required explicit T4 opt-in")
    args = parser.parse_args()
    if not args.overfit:
        parser.error("This script only runs T0-T4; pass --overfit to confirm the capped T4 gate")
    config_path = ROOT / "research/configs/stethofuse_tcn_v1.yaml"
    config = yaml.safe_load(config_path.read_text())
    out = ROOT / ".local/training/stethofuse-tcn-v1"
    run_id = "t0-t4-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out / run_id
    (run_dir / "recipes").mkdir(parents=True, exist_ok=False)

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(config["seed"])
    np.random.seed(config["seed"])
    torch.use_deterministic_algorithms(True)

    sources = read_manifest()
    audit = audit_manifest()
    write_json(run_dir / "t0_manifest_audit.json", audit)
    cache: dict[tuple[str, str], np.ndarray] = {}

    recipes = training_epoch(sources, 0, config["seed"])
    if len(recipes) != 576:
        raise RuntimeError(f"Unexpected train recipe count: {len(recipes)}")
    train_receipts = []
    for recipe in recipes:
        _, _, receipt = materialize_recipe(recipe, sources, cache)
        train_receipts.append(receipt)
    with (run_dir / "recipes/epoch-000.jsonl").open("w") as stream:
        for receipt in train_receipts:
            stream.write(json.dumps(receipt, sort_keys=True) + "\n")
    pair_counts = {}
    for receipt in train_receipts:
        key = f"{receipt['heart_family']}|{receipt['lung_family']}"
        pair_counts[key] = pair_counts.get(key, 0) + 1
    if len(pair_counts) != 24 or set(pair_counts.values()) != {24}:
        raise RuntimeError("Family-pair balance contract failed")

    val_recipes = frozen_validation_recipes(sources)
    if len(val_recipes) != 225:
        raise RuntimeError(f"Unexpected validation recipe count: {len(val_recipes)}")
    write_json(run_dir / "validation_recipes.json", {
        "classification": "FROZEN VALIDATION RECIPES; TEST SOURCES NOT OPENED",
        "source_manifest_sha256": audit["manifest_sha256"], "recipes": val_recipes})

    # T2 shape/finite/gradient smoke on synthetic data, without reading test audio.
    model = StethoFuseConvTasNet().cpu()
    if model.parameter_count != config["model"]["parameter_count"]:
        raise RuntimeError(f"Parameter count mismatch: {model.parameter_count}")
    smoke = torch.randn(2, 1, 32001, dtype=torch.float32) * 0.1
    output = model(smoke)
    smoke_loss = output.square().mean()
    smoke_loss.backward()
    if output.shape != (2, 2, 32001) or not torch.isfinite(output).all():
        raise RuntimeError("T2 forward shape/finite check failed")
    if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
        raise RuntimeError("T2 backward gradient check failed")
    consistency_error = float((output.detach().sum(1, keepdim=True) - smoke).abs().max())
    del smoke, output, smoke_loss
    model.zero_grad(set_to_none=True)

    # Fixed T4 examples from the design; record before fitting and never substitute.
    gate_specs = [("F_AF_A", "F_N_LLA"), ("F_ESM_LLSB", "F_PR_LLA")]
    gate_recipes = []
    for heart_id, lung_id in gate_specs:
        gate_recipes.append({"heart_id": heart_id, "heart_start": 0,
                             "lung_id": lung_id, "lung_start": 0,
                             "relative_lung_to_heart_db": 0.0, "crop_samples": 32000})
    mixtures_np, targets_np = [], []
    gate_receipts = []
    for recipe in gate_recipes:
        mixture, target, receipt = materialize_recipe(recipe, sources, cache)
        # The network uses one shared mixture peak scale for input and references.
        peak = float(np.max(np.abs(mixture)))
        if peak <= 0 or not np.isfinite(peak):
            raise RuntimeError("Invalid T4 mixture peak")
        mixtures_np.append(mixture / peak)
        targets_np.append(target / peak)
        receipt["network_shared_peak_scale"] = peak
        gate_receipts.append(receipt)
    write_json(run_dir / "t4_fixed_mixtures.json", {
        "classification": "PREDECLARED DEVELOPMENT-ONLY OVERFIT GATE; NEVER TEST",
        "mixtures": gate_receipts})
    mixes = [torch.from_numpy(x.copy()).view(1, 1, -1) for x in mixtures_np]
    targets = [torch.from_numpy(x.copy()).view(1, 2, -1) for x in targets_np]

    torch.manual_seed(config["seed"])
    model = StethoFuseConvTasNet().cpu().train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.0)
    before = metric_rows(model, mixes, targets)
    started = time.perf_counter()
    update_limit = min(int(config["overfit_gate"]["max_optimizer_steps"]), 400)
    wall_limit = min(float(config["overfit_gate"]["wall_time_limit_minutes"]), 10.0) * 60
    history = []
    updates = 0
    status = "T4_FAIL"
    last_rows = before
    while updates < update_limit and time.perf_counter() - started < wall_limit:
        optimizer.zero_grad(set_to_none=True)
        batch_x = torch.cat(mixes, dim=0)
        batch_y = torch.cat(targets, dim=0)
        estimate = model(batch_x)
        loss = fixed_label_loss(estimate, batch_y)
        if not torch.isfinite(loss):
            raise RuntimeError("Nonfinite T4 loss; abort before optimizer update")
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        if not torch.isfinite(grad_norm) or any(p.grad is not None and not torch.isfinite(p.grad).all()
                                               for p in model.parameters()):
            raise RuntimeError("Nonfinite T4 gradient; abort before optimizer update")
        optimizer.step()
        updates += 1
        elapsed = time.perf_counter() - started
        if updates % 20 == 0 or updates == update_limit:
            last_rows = metric_rows(model, mixes, targets)
            per_case = []
            for idx, row in enumerate(last_rows):
                b = before[idx]
                per_case.append({"heart_si_sdri_db": row["heart"]["si_sdri_db"],
                                 "lung_si_sdri_db": row["lung"]["si_sdri_db"],
                                 "heart_l1_reduction_fraction": 1 - row["heart"]["normalized_l1"] /
                                                                   b["heart"]["normalized_l1"],
                                 "lung_l1_reduction_fraction": 1 - row["lung"]["normalized_l1"] /
                                                                 b["lung"]["normalized_l1"]})
            passed = all(r["heart_si_sdri_db"] >= 10 and r["lung_si_sdri_db"] >= 10 and
                         r["heart_l1_reduction_fraction"] >= 0.5 and
                         r["lung_l1_reduction_fraction"] >= 0.5 for r in per_case)
            history.append({"optimizer_updates": updates, "elapsed_seconds": elapsed,
                            "loss": float(loss.detach()), "cases": per_case})
            print(f"T4 update={updates} elapsed={elapsed:.1f}s loss={float(loss.detach()):.4f} "
                  f"gate={'PASS' if passed else 'pending'}", flush=True)
            if passed:
                status = "T4_PASS"
                break

    elapsed = time.perf_counter() - started
    if status != "T4_PASS":
        last_rows = metric_rows(model, mixes, targets)
        per_case = []
        for idx, row in enumerate(last_rows):
            b = before[idx]
            per_case.append({"heart_si_sdri_db": row["heart"]["si_sdri_db"],
                             "lung_si_sdri_db": row["lung"]["si_sdri_db"],
                             "heart_l1_reduction_fraction": 1 - row["heart"]["normalized_l1"] /
                                                               b["heart"]["normalized_l1"],
                             "lung_l1_reduction_fraction": 1 - row["lung"]["normalized_l1"] /
                                                             b["lung"]["normalized_l1"]})
    else:
        per_case = history[-1]["cases"]
    checkpoint = run_dir / "overfit_state.pt"
    torch.save({"architecture_version": model.architecture_version,
                "state_dict": model.state_dict(), "run_id": run_id}, checkpoint)
    report = {"classification": "DEVELOPMENT-ONLY TINY CAPACITY GATE; NOT BASELINE TRAINING",
              "run_id": run_id, "git_commit": git_commit(),
              "git_worktree_dirty": git_worktree_dirty(),
              "config_sha256": digest_file(config_path),
              "source_manifest_sha256": audit["manifest_sha256"],
              "torch": torch.__version__, "torchaudio": __import__("torchaudio").__version__,
              "device": "cpu", "seed": config["seed"], "parameter_count": model.parameter_count,
              "input_shape": [2, 1, 32000], "output_shape": [2, 2, 32000],
              "target_free_consistency_max_abs_error": consistency_error,
              "selected_mixture_ids": [r["mixture_id"] for r in gate_receipts],
              "selected_pairs": gate_specs, "before": before, "after": last_rows,
              "per_case_gate": per_case, "optimizer_updates": updates,
              "elapsed_seconds": elapsed,
              "process_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
              "status": status, "checkpoint_sha256": digest_file(checkpoint),
              "training_recipe_count": len(train_receipts),
              "validation_recipe_count": len(val_recipes), "test_audio_decoded": False,
              "production_touched": False, "history": history}
    write_json(run_dir / "t4_report.json", report)
    write_json(out / "latest_t0_t4.json", {"run_id": run_id, "status": status,
                                             "report": str((run_dir / "t4_report.json").relative_to(ROOT))})
    print(json.dumps({k: report[k] for k in ("run_id", "parameter_count", "selected_mixture_ids",
          "before", "after", "per_case_gate", "optimizer_updates", "elapsed_seconds",
          "process_peak_rss_mib", "status", "checkpoint_sha256")}, indent=2))
    return 0 if status == "T4_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
