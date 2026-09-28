"""Restricted runner for the frozen final pre-T9 treatments A and B only."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import platform
from pathlib import Path
import random
import resource
import subprocess
import sys
import time

import numpy as np
import torch
import torchaudio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.stethofuse_tf import StethoFuseComplexTFUNet
from app.ml.spectral_objective import SPECTRAL_WEIGHT, spectral_log1p_loss
from app.ml.training_data import (make_mixture, materialize_recipe, read_manifest,
                                  read_source, sha256_file, training_epoch)
from app.ml.training_objective import fixed_label_components
from scripts.train_stethofuse_baseline import (evaluate_validation, file_sha256,
                                               get_mix_target, si_sdr,
                                               state_sha256)

PLAN = ROOT / "research/configs/final_pre_t9_model_plan_v1.json"
PLAN_SHA = "6776e53c1d53c66d39c8882169b6de729bc05358f337e26a91257fd74dce8103"
ELIGIBLE_SHA = "82e677af9f27256aa163b8aa80ca096874bc5cc37da10f29d029f7fee93999dd"
FOLD_SHA = "630bb9935f4720fbed66df6f1858d47f0561e89f4894fe7635ed24977e317e58"
CONTROL_SHA = "0d8893d61d9ed9517d0227781f33b3357b1c41f85d4ee80228f1691545d47dbe"
SEED = 20260928
UPDATES = 576
BATCH = 4
ARTIFACT_ROOT = ROOT / ".local/training/stethofuse-representation-v1"


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def recipe_reproduces(expected: dict, actual: dict) -> bool:
    """The materializer rehashes a derived mixture_id; compare all other frozen fields."""
    left, right = dict(expected), dict(actual)
    left.pop("mixture_id", None)
    right.pop("mixture_id", None)
    return left == right


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def atomic_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    temp.replace(path)


def git_state() -> dict:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    if dirty:
        raise RuntimeError("Refuse optimizer work from a dirty implementation worktree")
    return {"commit": commit, "dirty": False}


def check_integrity(plan: dict) -> tuple[list, dict]:
    if file_sha256(PLAN) != PLAN_SHA:
        raise RuntimeError("Frozen experiment plan hash changed")
    if plan.get("test_access_allowed") is not False or plan.get("production_changes_allowed") is not False:
        raise RuntimeError("Frozen safety flags changed")
    eligible_path = ROOT / plan["data"]["eligible_manifest"]
    fold_path = ROOT / plan["data"]["fold_manifest"]
    base_plan_path = ROOT / plan["data"]["base_plan"]
    control_receipt = ROOT / plan["control"]["receipt"]
    if (file_sha256(eligible_path) != ELIGIBLE_SHA or file_sha256(fold_path) != FOLD_SHA or
            file_sha256(base_plan_path) != plan["data"]["base_plan_sha256"] or
            file_sha256(control_receipt) != CONTROL_SHA):
        raise RuntimeError("Frozen eligible/fold/control integrity check failed")
    rows = read_manifest(eligible_path)
    if (len(rows) != 86 or any(s.split not in {"development", "validation"} for s in rows) or
            sum(s.kind == "HS" for s in rows) != 45 or sum(s.kind == "LS" for s in rows) != 41 or
            len({(s.kind, s.id) for s in rows}) != 86 or len({s.sha256 for s in rows}) != 86):
        raise RuntimeError("Frozen non-test allowlist changed")
    for kind in ("HS", "LS"):
        for family in {s.family for s in rows if s.kind == kind}:
            if len({s.split for s in rows if s.kind == kind and s.family == family}) != 1:
                raise RuntimeError("A family crosses the source split")
    return rows, json.loads(control_receipt.read_text())


def partition(rows: list, plan: dict, fold_id: str) -> tuple[list, list]:
    if fold_id == "refit":
        return rows, []
    base = json.loads((ROOT / plan["data"]["base_plan"]).read_text())
    fold = next((f for f in plan["validation"]["folds"] if f == fold_id), None)
    fold_row = next((f for f in base["folds"] if f["id"] == fold_id), None)
    if fold is None or fold_row is None:
        raise ValueError("Unknown fold")
    training, holdout = [], []
    for source in rows:
        held = source.family in (fold_row["holdout_heart_families"] if source.kind == "HS"
                                 else fold_row["holdout_lung_families"])
        (holdout if held else training).append(source)
    if ({(s.kind, s.family) for s in training} & {(s.kind, s.family) for s in holdout} or
            any(s.split == "test" for s in training + holdout)):
        raise RuntimeError("Held-out family leakage or test source detected")
    return training, holdout


def saved_control(plan: dict, fold: str) -> tuple[Path, list[dict], list[dict]]:
    run_name = ("refit-all-nontest-seed20260928" if fold == "refit"
                else f"cv-{fold}-seed20260928")
    root = ROOT / plan["control"]["root"] / run_name
    manifest_path = root / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    provenance = manifest["provenance"]
    expected_updates = 576 if fold == "refit" else 1152
    expected = {"plan_sha256": plan["data"]["base_plan_sha256"],
                "eligible_manifest_sha256": ELIGIBLE_SHA,
                "fold_manifest_sha256": FOLD_SHA, "fold": fold,
                "seed": SEED, "architecture_version": "stethofuse-convtasnet-4k-small-v1",
                "parameter_count": 171313, "device": "cpu", "updates": expected_updates}
    if (manifest.get("status") != "COMPLETE_FIXED_ENDPOINT" or manifest.get("failures") != 0 or
            manifest.get("optimizer_updates") != expected_updates or
            any(provenance.get(k) != v for k, v in expected.items())):
        raise RuntimeError(f"Stored control is not a valid matched source: {fold}")
    hashes = manifest["artifact_hashes"]
    for filename in ("training_recipes.jsonl", "cv_recipes.json"):
        if file_sha256(root / filename) != hashes[filename]:
            raise RuntimeError(f"Stored control recipe hash mismatch: {fold}/{filename}")
    recipe_rows = [json.loads(line) for line in (root / "training_recipes.jsonl").read_text().splitlines()]
    if len(recipe_rows) < 2304:
        raise RuntimeError("Stored control lacks frozen 2304-recipe exposure")
    cv = json.loads((root / "cv_recipes.json").read_text())
    if fold == "refit":
        if len(recipe_rows) != 2304:
            raise RuntimeError("v2 refit control must have exactly 2,304 draws")
        return root, recipe_rows, []
    if not isinstance(cv, dict) or fold not in cv:
        raise RuntimeError("Stored control CV recipe map is malformed")
    base = json.loads((ROOT / plan["data"]["base_plan"]).read_text())
    fold_conditions = {row["id"]: row["validation_conditions"] for row in base["folds"]}
    actual_val = (root / "validation-0576.jsonl").read_text().splitlines()
    if len(actual_val) != fold_conditions[fold]:
        raise RuntimeError("Stored control endpoint conditions are incomplete")
    return root, recipe_rows[:2304], cv[fold]


def prepare_training(training: list, recipes: list[dict]) -> tuple[list[dict], dict]:
    cache = {}
    for source in training:
        if file_sha256(source.path) != source.sha256:
            raise RuntimeError(f"Allowlisted source hash mismatch: {source.kind}/{source.id}")
        audio = read_source(source)
        if audio.shape != (60000,) or not np.isfinite(audio).all():
            raise RuntimeError("Invalid allowlisted source")
        cache[(source.kind, source.id)] = audio
    for recipe in recipes:
        mix, target, receipt = materialize_recipe(recipe, training, cache)
        # The control rows already contain a mixture hash after realization.
        if recipe.get("mixture_sha256") and receipt["mixture_sha256"] != recipe["mixture_sha256"]:
            raise RuntimeError("Frozen control recipe no longer reproduces")
        if mix.shape != (32000,) or target.shape != (2, 32000):
            raise RuntimeError("Unexpected training crop shape")
    return recipes, cache


def model_for(treatment: str) -> torch.nn.Module:
    if treatment == "A":
        return StethoFuseComplexTFUNet().cpu()
    if treatment == "B":
        return StethoFuseConvTasNet("stethofuse-convtasnet-4k-small-v1").cpu()
    raise ValueError("Only frozen treatments A and B are allowed")


def fit(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    git = git_state()
    plan = json.loads(PLAN.read_text())
    rows, _ = check_integrity(plan)
    if args.fold not in {*{f"f{i}" for i in range(1, 6)}, "refit"}:
        raise ValueError("Protocol accepts only frozen f1..f5 or authorized refit")
    arm_prefix = "a-tfcomplex" if args.treatment == "A" else "b-tcn-spectral"
    expected_id = (f"{arm_prefix}-refit-all-nontest-seed{SEED}" if args.fold == "refit"
                   else f"{arm_prefix}-{args.fold}-seed{SEED}")
    if args.run_id != expected_id:
        raise ValueError("Run ID must match the sole frozen treatment/fold/seed")
    decision_hash = None
    if args.fold == "refit":
        if args.decision_receipt is None or not args.decision_receipt.is_file():
            raise ValueError("Final refit requires the machine-readable PASS decision receipt")
        decision = json.loads(args.decision_receipt.read_text())
        arm = decision.get("winner")
        if (arm != args.treatment or decision.get("final_refit_authorized") is not True or
                decision.get("treatments", {}).get(arm, {}).get("pass") is not True or
                decision.get("implementation_sha") != git["commit"]):
            raise ValueError("Decision receipt does not authorize this arm and clean code SHA")
        decision_hash = file_sha256(args.decision_receipt)
    elif args.decision_receipt is not None:
        raise ValueError("Decision receipt is accepted only for the final refit")
    artifact = ARTIFACT_ROOT / args.run_id
    if artifact.exists() != args.resume:
        raise FileExistsError("Choose a new run ID, or --resume the identical interrupted run")
    training, holdout = partition(rows, plan, args.fold)
    control_dir, recipes, cv = saved_control(plan, args.fold)
    base_plan = json.loads((ROOT / plan["data"]["base_plan"]).read_text())
    fold_conditions = {row["id"]: row["validation_conditions"] for row in base_plan["folds"]}
    if args.fold != "refit" and len(cv) != fold_conditions[args.fold]:
        raise RuntimeError("Frozen CV recipe count mismatch")
    # Read/verify only this fold's training and held-out validation sources from the 86-row allowlist.
    cache = {}
    for source in rows:
        if file_sha256(source.path) != source.sha256:
            raise RuntimeError(f"Allowlisted source hash mismatch: {source.kind}/{source.id}")
        audio = read_source(source)
        if audio.shape != (60000,) or not np.isfinite(audio).all():
            raise RuntimeError("Invalid allowlisted source")
        cache[(source.kind, source.id)] = audio
    # Re-materialize each training recipe and require exact control hashes/gains.
    for recipe in recipes:
        _, _, receipt = materialize_recipe(recipe, training, cache)
        if not recipe_reproduces(recipe, receipt):
            raise RuntimeError("Stored control training recipe does not reproduce byte-for-byte")
    if args.fold != "refit":
        cv_ids = [str(r["mixture_id"]) for r in cv]
        control_ids = [json.loads(line)["mixture_id"] for line in (control_dir / "validation-0576.jsonl").read_text().splitlines()]
        if cv_ids != control_ids:
            raise RuntimeError("Treatment CV conditions differ from saved control evaluation")

    provenance = {"starting_git": git, "plan_sha256": PLAN_SHA,
                  "treatment": args.treatment, "fold": args.fold, "seed": SEED,
                  "optimizer_updates": UPDATES, "training_draws": 2304,
                  "training_recipe_prefix_sha256": canonical_hash(recipes),
                  "control_recipe_sha256": file_sha256(control_dir / "training_recipes.jsonl"),
                  "validation_recipe_sha256": file_sha256(control_dir / "cv_recipes.json"),
                  "eligible_manifest_sha256": ELIGIBLE_SHA, "fold_manifest_sha256": FOLD_SHA,
                  "control_decision_sha256": CONTROL_SHA,
                  "control_endpoint_sha256": (file_sha256(control_dir / "validation-0576.jsonl")
                                               if args.fold != "refit" else None),
                  "decision_receipt_sha256": decision_hash,
                  "fold_training_families": sorted({f"{s.kind}:{s.family}" for s in training}),
                  "heldout_families": sorted({f"{s.kind}:{s.family}" for s in holdout}),
                  "training_source_ids": sorted(f"{s.kind}:{s.id}" for s in training),
                  "heldout_source_ids": sorted(f"{s.kind}:{s.id}" for s in holdout),
                  "model_source_sha256": file_sha256(ROOT / ("app/ml/stethofuse_tf.py" if args.treatment == "A" else "app/ml/stethofuse_tcn.py")),
                  "loss_source_sha256": file_sha256(ROOT / ("app/ml/training_objective.py" if args.treatment == "A" else "app/ml/spectral_objective.py")),
                  "runner_source_sha256": file_sha256(Path(__file__)),
                  "training_manifest_sha256": file_sha256(ROOT / plan["data"]["eligible_manifest"]),
                  "parameter_count": 390450 if args.treatment == "A" else 171313,
                  "optimizer": {"name": "AdamW", "lr": .001, "betas": [.9, .999],
                                "eps": 1e-8, "weight_decay": .0001, "gradient_clip_norm": 5},
                  "python": platform.python_version(), "torch": str(torch.__version__),
                  "torchaudio": torchaudio.__version__, "device": "cpu"}
    provenance_sha = canonical_hash(provenance)
    if not args.resume:
        artifact.mkdir(parents=True)
        atomic_json(artifact / "provenance.json", provenance)
        atomic_json(artifact / "plan.json", plan)
        atomic_json(artifact / "training_recipes.json", recipes)
        if args.fold != "refit":
            atomic_json(artifact / "validation_recipes.json", cv)
        atomic_json(artifact / "eligible_sources.json", [
            {"kind": s.kind, "id": s.id, "family": s.family, "original_split": s.split,
             "sha256": s.sha256} for s in rows])
    else:
        old = json.loads((artifact / "provenance.json").read_text())
        if canonical_hash(old) != provenance_sha:
            raise RuntimeError("Resume provenance differs")

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    model = model_for(args.treatment)
    wanted_count = 390450 if args.treatment == "A" else 171313
    wanted_state = ("8d617e4199c55ce0f0e1502ca7413305e1600c701f70e585f6dd41bd1584d687"
                    if args.treatment == "A" else "7171ef15eadc33e001c833271bd8e1301145e974af64337fdbb2ef51c205f9b9")
    if sum(p.numel() for p in model.parameters()) != wanted_count:
        raise RuntimeError("Treatment parameter count mismatch")
    initial_sha = state_sha256(model)
    if initial_sha != wanted_state:
        raise RuntimeError("Treatment fresh initialization does not match frozen state hash")
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, betas=(.9, .999),
                                  eps=1e-8, weight_decay=.0001)
    if len(optimizer.state):
        raise RuntimeError("Optimizer must start fresh")
    history: list[dict] = []
    completed = 0
    if args.resume:
        state_path = artifact / "resume.pt"
        if file_sha256(state_path) != json.loads((artifact / "checkpoint_hashes.json").read_text())["resume.pt"]:
            raise RuntimeError("Resume checkpoint hash mismatch")
        state = torch.load(state_path, map_location="cpu", weights_only=False)
        if state["provenance_sha256"] != provenance_sha:
            raise RuntimeError("Resume state is not this exact experiment")
        model.load_state_dict(state["model"], strict=True)
        optimizer.load_state_dict(state["optimizer"])
        completed, history = state["update"], state["history"]
        torch.set_rng_state(state["torch_rng"])
        np.random.set_state(state["numpy_rng"])
        random.setstate(state["python_rng"])
    else:
        atomic_json(artifact / "initial.json", {"state_sha256": initial_sha,
                    "parameter_count": wanted_count, "optimizer_state_entries": 0})

    def persist(update: int) -> None:
        state = {"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                 "update": update, "history": history, "torch_rng": torch.get_rng_state(),
                 "numpy_rng": np.random.get_state(), "python_rng": random.getstate(),
                 "provenance_sha256": provenance_sha}
        path = artifact / "resume.pt"
        temp = path.with_suffix(".tmp")
        torch.save(state, temp); temp.replace(path)
        atomic_json(artifact / "checkpoint_hashes.json", {"resume.pt": file_sha256(path)})
        atomic_jsonl(artifact / "history.jsonl", history)

    model.train()
    for update in range(completed + 1, UPDATES + 1):
        batch_recipes = recipes[(update - 1) * BATCH:update * BATCH]
        xs, ys = [], []
        for recipe in batch_recipes:
            mixture, target, realized = materialize_recipe(recipe, training, cache)
            if not recipe_reproduces(recipe, realized):
                raise RuntimeError("Recipe changed during optimizer stream")
            scale = float(recipe["network_shared_peak_scale"])
            xs.append(mixture / scale); ys.append(target / scale)
        x = torch.from_numpy(np.stack(xs)[:, None])
        target = torch.from_numpy(np.stack(ys))
        optimizer.zero_grad(set_to_none=True)
        estimate = model(x)
        components = fixed_label_components(estimate, target)
        spectral = torch.zeros(())
        loss = components["loss"]
        if args.treatment == "B":
            spectral = spectral_log1p_loss(estimate, target)
            loss = loss + SPECTRAL_WEIGHT * spectral
        if not torch.isfinite(loss):
            raise RuntimeError("Nonfinite treatment objective")
        loss.backward()
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
            raise RuntimeError("Nonfinite treatment gradient")
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0, error_if_nonfinite=True)
        optimizer.step()
        if any(not torch.isfinite(p).all() for p in model.parameters()):
            raise RuntimeError("Nonfinite parameters after optimizer step")
        if update % 144 == 0 or update == UPDATES:
            row = {"optimizer_updates": update, "loss": float(loss.detach()),
                   "negative_si_sdr": float(components["negative_si_sdr"].detach()),
                   "normalized_waveform_l1": float(components["normalized_waveform_l1"].detach()),
                   "spectral_loss": float(spectral.detach()),
                   "weighted_spectral_loss": float((SPECTRAL_WEIGHT * spectral).detach()),
                   "gradient_norm_before_clip": float(grad_norm), "learning_rate": .001,
                   "runtime_seconds": time.perf_counter() - started,
                   "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                   "nonfinite_count": 0}
            history.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
            persist(update)
        if (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 > 8 * 1024 or
                time.perf_counter() - started > (20 * 60)):
            raise RuntimeError("Frozen 8-GiB/20-minute per-fit resource limit exceeded")

    validation_rows, summary = [], None
    if args.fold != "refit":
        model.eval()
        summary, validation_rows = evaluate_validation(model, cv, cache)
        if len(validation_rows) != fold_conditions[args.fold]:
            raise RuntimeError("Treatment endpoint produced incomplete validation")
        if not all(math.isfinite(float(row[k])) for row in validation_rows for k in
                   ("heart_si_sdr_db", "heart_si_sdri_db", "lung_si_sdr_db", "lung_si_sdri_db")):
            raise RuntimeError("Nonfinite validation result")
        atomic_json(artifact / "validation-0576-summary.json", summary)
        atomic_jsonl(artifact / "validation-0576.jsonl", validation_rows)
    endpoint = artifact / "endpoint.pt"
    temp = endpoint.with_suffix(".tmp")
    torch.save({"architecture_version": getattr(model, "architecture_version"),
                "parameter_count": wanted_count, "state_dict": model.state_dict(),
                "optimizer_updates": UPDATES, "seed": SEED,
                "provenance_sha256": provenance_sha}, temp)
    temp.replace(endpoint)
    result = {"status": "COMPLETE_FIXED_ENDPOINT", "run_id": args.run_id,
              "treatment": args.treatment, "fold": args.fold, "seed": SEED,
              "optimizer_updates": UPDATES, "initial_state_sha256": initial_sha,
              "parameter_count": wanted_count, "endpoint_sha256": file_sha256(endpoint),
              "validation_summary": summary, "validation_rows": len(validation_rows),
              "failures": 0,
              "runtime_seconds": time.perf_counter() - started,
              "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
              "provenance_sha256": provenance_sha}
    atomic_json(artifact / "result.json", result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--treatment", choices=("A", "B"), required=True)
    parser.add_argument("--fold", choices=("f1", "f2", "f3", "f4", "f5", "refit"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--decision-receipt", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.plan.resolve() != PLAN.resolve():
        raise SystemExit("Only the frozen plan path is allowed")
    fit(args)


if __name__ == "__main__":
    main()
