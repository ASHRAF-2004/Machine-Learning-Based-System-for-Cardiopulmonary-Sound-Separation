"""Run the bounded small-profile gate using two fixed development mixtures only."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torchaudio
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_data import MANIFEST_SHA256, materialize_recipe, read_manifest, read_source
from app.ml.training_objective import fixed_label_components, normalized_l1
from scripts.evaluate_ensemble_qualification import si_sdr

EXPECTED_PAIRS = (("F_AF_A", "F_N_LLA"), ("F_ESM_LLSB", "F_PR_LLA"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_sha256(model: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def evaluate(model: StethoFuseConvTasNet, mixtures: torch.Tensor,
             targets: torch.Tensor) -> list[dict[str, float]]:
    model.eval()
    rows = []
    with torch.inference_mode():
        outputs = model(mixtures)
        for index in range(len(mixtures)):
            result: dict[str, float] = {}
            for source, name in enumerate(("heart", "lung")):
                estimate = outputs[index:index + 1, source:source + 1]
                target = targets[index:index + 1, source:source + 1]
                score = si_sdr(outputs[index, source].cpu().numpy(),
                               targets[index, source].cpu().numpy())
                mixture_score = si_sdr(mixtures[index, 0].cpu().numpy(),
                                       targets[index, source].cpu().numpy())
                result[f"{name}_si_sdri_db"] = float(score - mixture_score)
                result[f"{name}_normalized_l1"] = float(normalized_l1(estimate, target).item())
            rows.append(result)
    model.train()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--attempt", choices=("initial", "fix1"), default="initial",
                        help="One initial attempt and, only after a proven fix, at most one rerun")
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = yaml.safe_load(config_path.read_text())
    if config.get("architecture_version") != "stethofuse-convtasnet-4k-small-v1":
        raise RuntimeError("Capacity gate is restricted to the approved small T7 profile")
    if config.get("seed") != 20260928 or config.get("data", {}).get("manifest_sha256") != MANIFEST_SHA256:
        raise RuntimeError("Capacity gate seed or frozen source manifest differs")
    if torch.__version__ != config["dependencies"]["torch"] or \
            torchaudio.__version__ != config["dependencies"]["torchaudio"]:
        raise RuntimeError("Pinned CPU training environment mismatch")

    artifacts = ROOT / ".local/training/stethofuse-tcn-v1"
    run_id = "t7-small-gate-seed20260928" + ("-fix1" if args.attempt == "fix1" else "")
    run_dir = artifacts / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "config.yaml").write_bytes(config_path.read_bytes())

    # Read manifest metadata, then resolve and open only the four named development files.
    wanted = {("HS", h) for h, _ in EXPECTED_PAIRS} | {("LS", l) for _, l in EXPECTED_PAIRS}
    selected = {(source.kind, source.id): source for source in read_manifest()
                if source.split == "development" and (source.kind, source.id) in wanted}
    if set(selected) != wanted:
        raise RuntimeError("Predeclared development gate source IDs are missing or ambiguous")
    cache = {}
    for key in sorted(wanted):
        source = selected[key]
        if sha256(source.path) != source.sha256:
            raise RuntimeError(f"Development source checksum mismatch for {key}")
        cache[key] = read_source(source)

    selected_sources = list(selected.values())
    mixtures, targets, receipts = [], [], []
    for heart_id, lung_id in EXPECTED_PAIRS:
        recipe = {"heart_id": heart_id, "heart_start": 0,
                  "lung_id": lung_id, "lung_start": 0,
                  "relative_lung_to_heart_db": 0.0, "crop_samples": 32000}
        mixture, target, receipt = materialize_recipe(recipe, selected_sources, cache)
        peak = float(np.max(np.abs(mixture)))
        if not np.isfinite(peak) or peak <= 0:
            raise RuntimeError("Invalid capacity-gate mixture peak")
        mixtures.append(mixture / peak)
        targets.append(target / peak)
        receipt["network_shared_peak_scale"] = peak
        receipts.append(receipt)

    torch.set_num_threads(config["training"]["threads"])
    torch.set_num_interop_threads(config["training"]["interop_threads"])
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(20260928)
    np.random.seed(20260928)
    model = StethoFuseConvTasNet(config["architecture_version"]).cpu().train()
    if model.parameter_count != config["model"]["parameter_count"]:
        raise RuntimeError("Small-profile parameter-count assertion failed")
    initial_state_sha256 = state_sha256(model)
    batch_x = torch.from_numpy(np.stack(mixtures)[:, None, :])
    batch_y = torch.from_numpy(np.stack(targets))
    before = evaluate(model, batch_x, batch_y)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.0)

    gate = config["overfit_gate"]
    step_limit = min(400, int(gate["max_optimizer_steps"]))
    time_limit = min(600.0, float(gate["wall_time_limit_minutes"]) * 60)
    update = 0
    history = []
    started = time.perf_counter()
    status = "T7_SMALL_CAPACITY_GATE_FAILED"
    after = before
    while update < step_limit and time.perf_counter() - started < time_limit:
        model.train()
        optimizer.zero_grad(set_to_none=True)
        output = model(batch_x)
        losses = fixed_label_components(output, batch_y)
        if not all(torch.isfinite(value) for value in losses.values()):
            raise RuntimeError("Nonfinite capacity-gate loss")
        losses["loss"].backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        if not torch.isfinite(grad_norm) or any(
                parameter.grad is not None and not torch.isfinite(parameter.grad).all()
                for parameter in model.parameters()):
            raise RuntimeError("Nonfinite capacity-gate gradient")
        optimizer.step()
        update += 1
        elapsed = time.perf_counter() - started
        if update % 20 == 0 or update == step_limit:
            after = evaluate(model, batch_x, batch_y)
            cases = []
            for index, result in enumerate(after):
                case = {"pair": list(EXPECTED_PAIRS[index]), **result}
                for source in ("heart", "lung"):
                    key = f"{source}_normalized_l1"
                    case[f"{source}_l1_reduction_fraction"] = 1.0 - result[key] / before[index][key]
                cases.append(case)
            passed = all(case[f"{source}_si_sdri_db"] >= 10.0 and
                         case[f"{source}_l1_reduction_fraction"] >= 0.5
                         for case in cases for source in ("heart", "lung"))
            history.append({"update": update, "elapsed_seconds": elapsed,
                            "loss": float(losses["loss"].detach()),
                            "negative_si_sdr": float(losses["negative_si_sdr"].detach()),
                            "normalized_waveform_l1": float(losses["normalized_waveform_l1"].detach()),
                            "cases": cases})
            print(json.dumps({"update": update, "elapsed_seconds": round(elapsed, 2),
                              "loss": history[-1]["loss"], "gate": "PASS" if passed else "pending"}),
                  flush=True)
            if passed:
                status = "T7_SMALL_CAPACITY_GATE_PASSED"
                break

    elapsed = time.perf_counter() - started
    if not history or history[-1]["update"] != update:
        after = evaluate(model, batch_x, batch_y)
        cases = []
        for index, result in enumerate(after):
            case = {"pair": list(EXPECTED_PAIRS[index]), **result}
            for source in ("heart", "lung"):
                key = f"{source}_normalized_l1"
                case[f"{source}_l1_reduction_fraction"] = 1.0 - result[key] / before[index][key]
            cases.append(case)
        history.append({"update": update, "elapsed_seconds": elapsed, "cases": cases})
        if all(case[f"{source}_si_sdri_db"] >= 10.0 and
               case[f"{source}_l1_reduction_fraction"] >= 0.5
               for case in cases for source in ("heart", "lung")):
            status = "T7_SMALL_CAPACITY_GATE_PASSED"

    checkpoint_path = run_dir / "gate_final.pt"
    torch.save({"architecture_version": model.architecture_version,
                "parameter_count": model.parameter_count,
                "initial_state_sha256": initial_state_sha256,
                "state_dict": model.state_dict()}, checkpoint_path)
    report = {"status": status, "run_id": run_id,
              "git_commit": __import__("subprocess").check_output(
                  ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "git_worktree_dirty": bool(__import__("subprocess").check_output(
                  ["git", "status", "--porcelain=v1"], cwd=ROOT, text=True).strip()),
              "architecture_version": model.architecture_version,
              "parameter_count": model.parameter_count,
              "seed": 20260928, "fresh_initialization_state_sha256": initial_state_sha256,
              "initialization_source": "seeded small Conv-TasNet from scratch; no checkpoint",
              "config_sha256": sha256(config_path), "source_manifest_sha256": MANIFEST_SHA256,
              "selected_pairs": [list(pair) for pair in EXPECTED_PAIRS],
              "recipes": receipts, "before": before, "after": after,
              "optimizer_updates": update, "elapsed_seconds": elapsed,
              "process_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
              "torch": torch.__version__, "torchaudio": torchaudio.__version__,
              "device": "cpu", "test_audio_opened": False,
              "checkpoint_sha256": sha256(checkpoint_path), "history": history}
    report_path = run_dir / "gate_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in
                      ("status", "parameter_count", "optimizer_updates", "elapsed_seconds",
                       "process_peak_rss_mib", "after", "checkpoint_sha256")}, indent=2), flush=True)
    return 0 if status == "T7_SMALL_CAPACITY_GATE_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
