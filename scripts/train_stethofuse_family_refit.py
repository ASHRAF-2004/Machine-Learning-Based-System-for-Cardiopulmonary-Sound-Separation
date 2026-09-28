"""Fixed-update non-test HLS family control/refit; external initialization is explicit.

No training occurs on import. The only HLS source discovery is the frozen
86-row eligible CSV, never the original full split or filesystem enumeration.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import random
import re
import sys
import time

import numpy as np
import torch
import torchaudio
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_data import Source, make_mixture, materialize_recipe, read_manifest, read_source, training_epoch
from app.ml.training_objective import fixed_label_components
from app.ml.native_supervision import (load_native_audio, load_native_selection, materialize_native,
                                       native_recipe_prefix, validate_native_plan)
from scripts.train_stethofuse_baseline import (
    atomic_json, atomic_jsonl, atomic_torch_save, evaluate_validation, file_sha256,
    git_metadata, model_checkpoint, resource_snapshot, state_sha256,
)

ELIGIBLE_HASH = "82e677af9f27256aa163b8aa80ca096874bc5cc37da10f29d029f7fee93999dd"
T8_HASH = "89f8d66134c0a49aa2a05971720cdffbdd1e501ebce99bb83119e6683d58ac93"
BUDGETS = (576, 864, 1152)
SEED = 20260928


def json_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_plan(plan: dict, updates: int) -> None:
    expected = {"test_access_allowed": False, "production_changes_allowed": False,
                "eligible_manifest_sha256": ELIGIBLE_HASH,
                "architecture_version": "stethofuse-convtasnet-4k-small-v1",
                "parameter_count": 171313, "seed_all_runs": SEED, "device": "cpu",
                "threads": 2, "interop_threads": 1, "batch_size": 4,
                "plateau_scheduler": False, "early_stopping": False}
    if any(plan.get(key) != value for key, value in expected.items()):
        raise ValueError("Plan differs from the approved fixed-update small-model contract")
    optimizer = {"name": "AdamW", "lr": .001, "betas": [.9, .999], "eps": 1e-8,
                 "weight_decay": .0001, "gradient_clip_norm": 5.0}
    if plan.get("optimizer") != optimizer or updates not in BUDGETS:
        raise ValueError("Optimizer or update budget is not predeclared")
    policy = plan.get("initialization")
    if policy == "fresh_library_default_no_checkpoint_loading":
        if (plan.get("cv_max_optimizer_updates_per_fold") != 1152 or
                plan.get("cv_evaluation_updates") != list(BUDGETS) or
                plan.get("initialization_checkpoint_sha256") is not None):
            raise ValueError("Fresh control plan must retain its original budget candidates and no initializer")
    elif policy == "external_pretraining_endpoint":
        if (plan.get("cv_max_optimizer_updates_per_fold") != updates or
                plan.get("cv_evaluation_updates") != [updates] or
                not re.fullmatch(r"[0-9a-f]{64}", str(plan.get("initialization_checkpoint_sha256"))) or
                plan["initialization_checkpoint_sha256"] == T8_HASH):
            raise ValueError("Treatment plan must freeze one endpoint and its external initializer hash")
    else:
        raise ValueError("Unrecognized predeclared initialization policy")
    if plan.get("lr_schedule") != [{"from_update_inclusive": 1,
                                    "through_update_inclusive": 1152, "lr": .001}]:
        raise ValueError("Expected constant approved learning rate")
    cv = plan["cv_validation"]
    if (cv["levels_db"] != [-10, -5, 0, 5, 10] or cv["samples"] != 60000 or
            cv["start_samples"] != 0 or plan["recipe_epoch_origin"] != 0):
        raise ValueError("Crop/validation policy changed")


def validate_initialization(plan: dict, checkpoint: Path | None, supplied_hash: str | None,
                            refit_receipt: dict | None = None) -> None:
    if plan["initialization"] == "fresh_library_default_no_checkpoint_loading":
        if checkpoint is not None or supplied_hash is not None:
            raise ValueError("Fresh-only plan forbids any checkpoint initialization")
        if refit_receipt is not None and "initialization_checkpoint_sha256" in refit_receipt:
            raise ValueError("Fresh refit receipt must not declare an initialization checkpoint")
    elif plan["initialization"] == "external_pretraining_endpoint":
        if checkpoint is None or supplied_hash != plan["initialization_checkpoint_sha256"]:
            raise ValueError("External initialization must match the hash frozen in the treatment plan")
        if refit_receipt is not None and refit_receipt.get("initialization_checkpoint_sha256") != supplied_hash:
            raise ValueError("External refit receipt must bind the same initialization checkpoint hash")
    else:
        raise ValueError("Unrecognized predeclared initialization policy")


def prepare_fold_manifest(plan: dict, destination: Path) -> dict:
    """Emit immutable assignment metadata from the 86-row CSV; never open audio."""
    validate_plan(plan, plan["cv_max_optimizer_updates_per_fold"])
    sources = load_eligible_metadata(plan)
    if destination.suffix.lower() != ".csv" or "hls_cmds" in destination.resolve().parts:
        raise ValueError("Fold manifest destination must be a metadata CSV outside the audio dataset")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=["original_split", "kind", "id", "family", "sha256", "holdout_fold"],
                            lineterminator="\n")
    writer.writeheader()
    for source in sorted(sources, key=lambda s: (s.kind, s.family, s.id)):
        fold = next(f["id"] for f in plan["folds"] if source.family in f[
            "holdout_heart_families" if source.kind == "HS" else "holdout_lung_families"])
        writer.writerow({"original_split": source.split, "kind": source.kind, "id": source.id,
                         "family": source.family, "sha256": source.sha256, "holdout_fold": fold})
    payload = stream.getvalue().encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != payload:
            raise FileExistsError("Refusing to replace different fold-assignment metadata")
    else:
        with destination.open("xb") as handle:
            handle.write(payload)
    return {"path": str(destination), "sha256": hashlib.sha256(payload).hexdigest(),
            "rows": len(sources), "audio_opened": False}


def load_eligible_metadata(plan: dict) -> list[Source]:
    path = ROOT / plan["eligible_manifest"]
    if file_sha256(path) != ELIGIBLE_HASH:
        raise ValueError("Eligible-only source manifest changed")
    sources = read_manifest(path)  # Explicit path: never call the default full manifest.
    validate_sources(sources, plan)
    return sources


def validate_sources(sources: list[Source], plan: dict) -> None:
    if (len(sources) != 86 or any(s.split not in {"development", "validation"} for s in sources) or
            Counter(s.kind for s in sources) != {"HS": 45, "LS": 41} or
            len({(s.kind, s.id) for s in sources}) != 86 or len({s.sha256 for s in sources}) != 86):
        raise ValueError("Expected 86 unique non-test allowlisted sources, 45 heart / 41 lung")
    if len({s.family for s in sources if s.kind == "HS"}) != 8 or len(
            {s.family for s in sources if s.kind == "LS"}) != 5:
        raise ValueError("Non-test family counts changed")
    family_splits = {}
    for source in sources:
        family_splits.setdefault((source.kind, source.family), set()).add(source.split)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", source.id):
            raise ValueError("Unsafe source ID")
        assignments = [fold for fold in plan["folds"] if source.family in fold[
            "holdout_heart_families" if source.kind == "HS" else "holdout_lung_families"]]
        if len(assignments) != 1:
            raise ValueError("Every eligible source family must have exactly one holdout fold")
    if any(len(splits) != 1 for splits in family_splits.values()):
        raise ValueError("Original source family crosses development/validation partitions")
    for fold in plan["folds"]:
        training, holdout = partition_sources(sources, plan, fold["id"])
        counts = (sum(s.kind == "HS" for s in training), sum(s.kind == "LS" for s in training),
                  sum(s.kind == "HS" for s in holdout), sum(s.kind == "LS" for s in holdout))
        if counts != tuple(fold[k] for k in ("train_heart", "train_lung", "holdout_heart", "holdout_lung")):
            raise ValueError(f"Source count mismatch for {fold['id']}")


def partition_sources(sources: list[Source], plan: dict, fold_id: str) -> tuple[list[Source], list[Source]]:
    if any(s.split not in {"development", "validation"} for s in sources):
        raise ValueError("Locked or unrecognized source cannot be relabelled")
    if fold_id == "refit":
        return [replace(s, split="development") for s in sources], []
    fold = next((f for f in plan["folds"] if f["id"] == fold_id), None)
    if fold is None:
        raise ValueError("Unknown held-out family fold")
    training, holdout = [], []
    for source in sources:
        held = source.family in fold["holdout_heart_families" if source.kind == "HS" else "holdout_lung_families"]
        (holdout if held else training).append(replace(source, split="validation" if held else "development"))
    return training, holdout


def training_prefix(sources: list[Source], updates: int) -> list[dict]:
    if updates not in BUDGETS or any(s.split != "development" for s in sources):
        raise ValueError("Training prefix requires a planned budget and development-role sources")
    prefix, epoch = [], 0
    while len(prefix) < 4 * updates:
        epoch_rows = training_epoch(sources, epoch, SEED)
        if not epoch_rows:
            raise ValueError("Empty family-balanced recipe epoch")
        prefix.extend({**row, "virtual_epoch": epoch} for row in epoch_rows)
        epoch += 1
    return prefix[:4 * updates]


def realize_prefix(recipes: list[dict], sources: list[Source], cache: dict) -> list[dict]:
    receipts = []
    for row in recipes:
        realized = dict(row)
        for retries in range(4):
            h = cache[("HS", row["heart_id"])][realized["heart_start"]:realized["heart_start"] + 32000]
            l = cache[("LS", row["lung_id"])][realized["lung_start"]:realized["lung_start"] + 32000]
            if h.size == l.size == 32000 and min(float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
                                                for x in (h, l)) >= 1e-6:
                break
            if retries == 3:
                raise RuntimeError("Silent/invalid crop after the approved three retries")
            rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(
                [SEED, row["virtual_epoch"], row["draw_index"], 100 + retries])))
            realized["heart_start"], realized["lung_start"] = int(rng.integers(0, 28001)), int(rng.integers(0, 28001))
        realized["silent_crop_retries"] = retries
        _, _, receipt = materialize_recipe(realized, sources, cache)
        receipts.append(receipt)
    return receipts


def cv_recipes(holdout: list[Source], cache: dict, fold_id: str) -> list[dict]:
    if any(s.split != "validation" for s in holdout):
        raise ValueError("Only held-out allowlisted families can form CV recipes")
    rows = []
    hearts = sorted((s for s in holdout if s.kind == "HS"), key=lambda s: (s.family, s.id))
    lungs = sorted((s for s in holdout if s.kind == "LS"), key=lambda s: (s.family, s.id))
    for hi, h in enumerate(hearts):
        for li, l in enumerate(lungs):
            for level in (-10, -5, 0, 5, 10):
                _, _, gain = make_mixture(cache[("HS", h.id)], cache[("LS", l.id)], level, crop_samples=60000)
                row = {"fold": fold_id, "heart_id": h.id, "lung_id": l.id,
                       "heart_family": h.family, "lung_family": l.family,
                       "heart_sha256": h.sha256, "lung_sha256": l.sha256,
                       "heart_start": 0, "lung_start": 0, "crop_samples": 60000,
                       "seed_key": [SEED, hi, li, level], **gain,
                       "network_shared_peak_scale": gain["mixture_peak"],
                       "network_normalization": "divide mixture and both targets by mixture peak"}
                row["mixture_id"] = json_hash(row)[:20]
                rows.append(row)
    return rows


def snapshot(model: StethoFuseConvTasNet, optimizer: torch.optim.Optimizer, update: int,
             manifest: dict, history: list[dict], elapsed: float) -> dict:
    result = model_checkpoint(model, 0, {"training_stage": manifest["training_stage"],
                                        "provenance_sha256": manifest["provenance_sha256"]})
    result.pop("epoch")  # Fixed updates are not legacy baseline epochs.
    result.update({"optimizer_updates": update, "recipe_cursor": update * 4,
                   "optimizer_state_dict": optimizer.state_dict(), "scheduler": None,
                   "torch_rng_state": torch.get_rng_state(), "numpy_rng_state": np.random.get_state(),
                   "python_rng_state": random.getstate(), "history": history,
                   "runtime_seconds": elapsed, "provenance_sha256": manifest["provenance_sha256"]})
    if "native_plan_sha256" in manifest.get("provenance", {}):
        result["native_recipe_cursor"] = update * 4
    return result


def native_control_proof(native: dict, fold: str, recipes: list[dict], cv: dict,
                         provenance: dict) -> dict:
    """Check historical control identities, not its performance, before training."""
    decision = ROOT / native["control"]["decision_receipt"]
    if file_sha256(decision) != native["control"]["decision_receipt_sha256"]:
        raise ValueError("Frozen control decision receipt changed")
    name = (native["control"]["run_pattern"].format(fold=fold) if fold != "refit"
            else "refit-all-nontest-seed20260928")
    directory = ROOT / native["control"]["artifact_root"] / name
    manifest_path = directory / "run_manifest.json"
    control = json.loads(manifest_path.read_text())
    if (control["status"] != "COMPLETE_FIXED_ENDPOINT" or control["failures"] != 0 or
            control["training_stage"] != "hls_fixed_update_control" or
            control["optimizer_updates"] < 576 or control["optimizer_state_entries_at_start"] != 0 or
            control["fresh_seeded_state_sha256"] != control["initialized_state_sha256"]):
        raise ValueError("Historical matched control is not a valid fresh completed experiment")
    for key in ("plan_sha256", "base_config_sha256", "eligible_manifest_sha256", "fold_manifest_sha256",
                "fold", "seed", "architecture_version", "parameter_count", "optimizer", "lr_schedule",
                "loss", "device", "python", "torch", "torchaudio", "numpy"):
        if control["provenance"][key] != provenance[key]:
            raise ValueError(f"Native/control contract mismatch: {key}")
    for filename in ("training_recipes.jsonl", "cv_recipes.json"):
        if file_sha256(directory / filename) != control["artifact_hashes"][filename]:
            raise ValueError("Historical control recipe artifact changed")
    original = [json.loads(line) for line in (directory / "training_recipes.jsonl").read_text().splitlines()]
    if len(recipes) != 2304 or original[:2304] != recipes:
        raise ValueError("Native treatment must retain the EXACT first2304 realized control mixtures")
    if json.loads((directory / "cv_recipes.json").read_text()) != cv:
        raise ValueError("Native treatment validation conditions differ from control")
    return {"control_run_id": control["run_id"], "control_manifest_sha256": file_sha256(manifest_path),
            "control_fresh_seeded_state_sha256": control["fresh_seeded_state_sha256"],
            "control_recipe_prefix_sha256": json_hash(original[:2304]),
            "synthetic_recipe_prefix_equal": True, "cv_recipes_equal": True,
            "matched_synthetic_draws": 2304, "optimizer_and_environment_equal": True}


def run(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    git = git_metadata()  # Fail before any initialization if the implementation is dirty.
    plan_path = args.plan.resolve()
    plan = json.loads(plan_path.read_text())
    validate_plan(plan, args.updates)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_id):
        raise ValueError("Unsafe run ID")
    if bool(args.init_checkpoint) != bool(args.init_sha256):
        raise ValueError("External initialization needs both --init-checkpoint and --init-sha256")
    plan_hash = file_sha256(plan_path)
    native_path, native_hash = getattr(args, "native_plan", None), getattr(args, "native_plan_sha256", None)
    native = None
    if bool(native_path) != bool(native_hash):
        raise ValueError("Native treatment needs both --native-plan and --native-plan-sha256")
    if native_path:
        if file_sha256(native_path) != native_hash:
            raise ValueError("Native plan hash mismatch")
        native = json.loads(native_path.read_text())
        validate_native_plan(native, plan, plan_hash, args.updates)
        if args.init_checkpoint or args.init_sha256:
            raise ValueError("Native treatment must use fresh initialization, never a checkpoint")
        if any(native[k] != v for k, v in {"python": platform.python_version(),
                                          "torch": str(torch.__version__), "torchaudio": torchaudio.__version__}.items()):
            raise ValueError("Native treatment requires the exact frozen CPU environment")
    receipt_hash = None
    receipt = None
    if args.fold == "refit":
        if not args.decision_receipt:
            raise ValueError("Refit requires the predeclared accepted budget decision receipt")
        receipt = json.loads(args.decision_receipt.read_text())
        plan_bound = (receipt.get("native_plan_sha256") == native_hash and
                      receipt.get("base_plan_sha256") == plan_hash) if native else receipt.get("plan_sha256") == plan_hash
        if (receipt.get("accepted") is not True or receipt.get("selected_optimizer_updates") != args.updates or
                not plan_bound):
            raise ValueError("Refit receipt does not authorize this exact plan and endpoint")
        receipt_hash = file_sha256(args.decision_receipt)
    validate_initialization(plan, args.init_checkpoint, args.init_sha256, receipt)
    config_path = ROOT / plan["base_config"]
    if file_sha256(config_path) != plan["base_config_sha256"]:
        raise ValueError("Frozen small-model config changed")
    config = yaml.safe_load(config_path.read_text())
    if (str(torch.__version__) != config["dependencies"]["torch"] or
            torchaudio.__version__ != config["dependencies"]["torchaudio"]):
        raise ValueError("Pinned CPU torch/torchaudio environment required")
    fold_manifest_path = ROOT / "research/manifests/pre_t9_family_cv_v1.csv"
    if not fold_manifest_path.is_file():
        raise ValueError("Prepare and commit the metadata-only fold manifest before training")
    fold_manifest_receipt = prepare_fold_manifest(plan, fold_manifest_path)
    if native and fold_manifest_receipt["sha256"] != native["fold_manifest_sha256"]:
        raise ValueError("Native frozen family-fold assignment changed")
    sources = load_eligible_metadata(plan)
    training, holdout = partition_sources(sources, plan, args.fold)
    artifact_root = (ROOT / (native or plan)["artifact_root"]).resolve()
    if not artifact_root.is_relative_to((ROOT / ".local/training").resolve()):
        raise ValueError("Artifacts must remain in ignored local training storage")
    directory = artifact_root / args.run_id
    if directory.exists() != args.resume:
        raise ValueError("Use a new run ID, or --resume for an existing identical run")
    if args.resume and (directory / "failure.json").exists():
        raise ValueError("A recorded failure requires owner review, not automatic resume")
    # Hash/decode only the 86 explicit allowed sources. No glob, test metadata,
    # original full split CSV, audit_manifest(), or implicit source discovery.
    cache = {}
    for source in sources:
        if file_sha256(source.path) != source.sha256:
            raise ValueError(f"Allowed source bytes changed: {source.kind}/{source.id}")
        audio = read_source(source)
        if audio.shape != (60000,) or not np.isfinite(audio).all():
            raise ValueError("Expected finite 15-second allowlisted source")
        cache[(source.kind, source.id)] = audio
    realized = realize_prefix(training_prefix(training, args.updates), training, cache)
    all_cv = {}
    if args.fold != "refit":
        for fold in plan["folds"]:
            _, eligible_holdout = partition_sources(sources, plan, fold["id"])
            all_cv[fold["id"]] = cv_recipes(eligible_holdout, cache, fold["id"])
            if len(all_cv[fold["id"]]) != fold["validation_conditions"]:
                raise ValueError("Predeclared CV condition count changed")
        if sum(map(len, all_cv.values())) != 1775:
            raise ValueError("Expected all 1775 non-test CV conditions")
    native_rows, native_cache, native_recipes = [], {}, []
    if native:
        native_rows = load_native_selection(ROOT, native, sources, plan, args.fold)
        native_cache = load_native_audio(ROOT, native_rows, args.fold)
        native_recipes = [materialize_native(r, native_cache)[2] for r in native_recipe_prefix(native_rows)]
    provenance = {"git": git, "plan_sha256": plan_hash,
                  "base_config_sha256": file_sha256(config_path), "eligible_manifest_sha256": ELIGIBLE_HASH,
                  "fold_manifest_sha256": fold_manifest_receipt["sha256"],
                  "original_source_manifest_sha256_provenance_only": plan["source_manifest_sha256"],
                  "training_recipe_content_sha256": json_hash(realized), "cv_recipe_content_sha256": json_hash(all_cv),
                  "fold": args.fold, "updates": args.updates, "seed": SEED,
                  "decision_receipt_sha256": receipt_hash, "initialization_checkpoint_sha256": args.init_sha256,
                  "initialization_checkpoint_path": str(args.init_checkpoint.resolve()) if args.init_checkpoint else None,
                  "resolved_initialization_policy": "external_pretraining_weights_fresh_optimizer" if args.init_checkpoint
                  else "fresh_library_default_no_checkpoint_loading",
                  "original_plan_initialization_policy": plan["initialization"],
                  "python": platform.python_version(), "torch": str(torch.__version__),
                  "torchaudio": torchaudio.__version__, "numpy": np.__version__, "device": "cpu",
                  "architecture_version": plan["architecture_version"], "parameter_count": 171313,
                  "optimizer": plan["optimizer"], "lr_schedule": plan["lr_schedule"],
                  "loss": plan["loss"], "test_access": False, "production_access": False}
    control_proof = None
    if native:
        control_proof = native_control_proof(native, args.fold, realized, all_cv, provenance)
        provenance.update({"native_plan_sha256": native_hash,
                           "native_qualified_manifest_sha256": native["qualified_manifest_sha256"],
                           "native_registry_sha256": native["registry_sha256"],
                           "native_training_triplet_ids": [r["triplet_id"] for r in native_rows],
                           "native_recipe_content_sha256": json_hash(native_recipes),
                           "native_loss_weight": native["native_loss_weight"],
                           "matched_control_proof": control_proof})
    provenance_hash = json_hash(provenance)
    directory.mkdir(parents=True, exist_ok=args.resume)
    checkpoint_dir = directory / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    if args.resume:
        manifest = json.loads((directory / "run_manifest.json").read_text())
        if manifest["provenance_sha256"] != provenance_hash:
            raise ValueError("Cannot resume a changed code/config/data/environment/initialization experiment")
        if manifest["status"] == "COMPLETE_FIXED_ENDPOINT":
            raise ValueError("This experiment already completed; do not restart it")
    else:
        atomic_json(plan, directory / "plan.json")
        atomic_json(config, directory / "base_config.json")
        atomic_jsonl(realized, directory / "training_recipes.jsonl")
        atomic_json(all_cv, directory / "cv_recipes.json")
        if native:
            atomic_json(native, directory / "native_plan.json")
            atomic_json(native_rows, directory / "native_training_selection.json")
            atomic_jsonl(native_recipes, directory / "native_recipes.jsonl")
        atomic_json([{"kind": s.kind, "id": s.id, "family": s.family, "original_split": s.split,
                      "sha256": s.sha256, "path": str(s.path)} for s in sources], directory / "eligible_sources.json")
        manifest = {"run_id": args.run_id, "created_utc": datetime.now(timezone.utc).isoformat(),
                    "status": "PREPARED", "provenance": provenance, "provenance_sha256": provenance_hash,
                    "training_stage": ("hls_native_supervised_pilot" if native else
                                       "hls_external_initialized_finetuning" if args.init_checkpoint else "hls_fixed_update_control"),
                    "artifact_hashes": {p.name: file_sha256(p) for p in directory.iterdir() if p.is_file()}}
        atomic_json(manifest, directory / "run_manifest.json")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if git_metadata() != git:
        raise RuntimeError("Source changed before model initialization")
    model = StethoFuseConvTasNet(plan["architecture_version"]).cpu()
    if model.parameter_count != 171313:
        raise ValueError("Small-model parameter count changed")
    fresh_hash = state_sha256(model)
    if native and fresh_hash != control_proof["control_fresh_seeded_state_sha256"]:
        raise ValueError("Native/control fresh seeded model states are not identical")
    if args.init_checkpoint:
        if args.init_sha256 == T8_HASH or file_sha256(args.init_checkpoint) != args.init_sha256:
            raise ValueError("Forbidden T8 initialization or external checkpoint hash mismatch")
        initial = torch.load(args.init_checkpoint, map_location="cpu", weights_only=False)
        if (initial.get("architecture_version") != model.architecture_version or
                initial.get("parameter_count") != model.parameter_count or
                initial.get("metadata", {}).get("training_stage") != "external_pretraining"):
            raise ValueError("Initializer must be an explicitly identified matching external-pretraining checkpoint")
        model.load_state_dict(initial["state_dict"], strict=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, betas=(.9, .999), eps=1e-8, weight_decay=.0001)
    initial_hash = state_sha256(model)
    completed, elapsed_prior, history = 0, 0.0, []
    if args.resume:
        resume_path = checkpoint_dir / "resume.pt"
        hashes = json.loads((directory / "checkpoint_hashes.json").read_text())
        if file_sha256(resume_path) != hashes["resume.pt"]:
            raise ValueError("Resume checkpoint hash mismatch")
        state = torch.load(resume_path, map_location="cpu", weights_only=False)
        if state["provenance_sha256"] != provenance_hash:
            raise ValueError("Resume provenance mismatch")
        model.load_state_dict(state["state_dict"], strict=True)
        optimizer.load_state_dict(state["optimizer_state_dict"])
        completed, elapsed_prior, history = state["optimizer_updates"], state["runtime_seconds"], state["history"]
        if state["recipe_cursor"] != completed * 4 or not 0 <= completed <= args.updates:
            raise ValueError("Resume recipe cursor mismatch")
        if native and state.get("native_recipe_cursor") != completed * 4:
            raise ValueError("Resume native recipe cursor mismatch")
        torch.set_rng_state(state["torch_rng_state"])
        np.random.set_state(state["numpy_rng_state"])
        random.setstate(state["python_rng_state"])
    else:
        manifest.update({"fresh_seeded_state_sha256": fresh_hash, "initialized_state_sha256": initial_hash,
                         "optimizer_state_entries_at_start": len(optimizer.state), "status": "INITIALIZED"})
        atomic_json(manifest, directory / "run_manifest.json")
    model.train()
    sums, norms, interval_start = Counter(), [], completed

    def persist(update: int, name: str = "resume.pt") -> None:
        state = snapshot(model, optimizer, update, manifest, history, elapsed_prior + time.perf_counter() - started)
        atomic_torch_save(state, checkpoint_dir / name)
        if name != "resume.pt":
            atomic_torch_save(state, checkpoint_dir / "resume.pt")
        atomic_json({p.name: file_sha256(p) for p in checkpoint_dir.glob("*.pt")}, directory / "checkpoint_hashes.json")
        atomic_jsonl(history, directory / "history.jsonl")

    try:
        if not args.resume:
            persist(0, "initial.pt")
        for update in range(completed + 1, args.updates + 1):
            xs, ys = [], []
            for receipt in realized[(update - 1) * 4:update * 4]:
                mix, target, replay = materialize_recipe(receipt, training, cache)
                if replay["mixture_sha256"] != receipt["mixture_sha256"]:
                    raise RuntimeError("Frozen training recipe did not reproduce")
                scale = float(receipt["network_shared_peak_scale"])
                xs.append(mix / scale)
                ys.append(target / scale)
            x, target = torch.from_numpy(np.stack(xs)[:, None]), torch.from_numpy(np.stack(ys))
            optimizer.zero_grad(set_to_none=True)
            components = fixed_label_components(model(x), target)
            if any(not torch.isfinite(value) for value in components.values()):
                raise RuntimeError("Nonfinite fixed-label loss")
            components["loss"].backward()
            native_components = None
            if native:
                nx, ny = [], []
                for receipt in native_recipes[(update - 1) * 4:update * 4]:
                    mx, my, replay = materialize_native(receipt, native_cache)
                    if replay != receipt:
                        raise RuntimeError("Frozen native crop/target recipe did not reproduce")
                    nx.append(mx)
                    ny.append(my)
                native_components = fixed_label_components(model(torch.from_numpy(np.stack(nx)[:, None])),
                                                            torch.from_numpy(np.stack(ny)))
                if any(not torch.isfinite(value) for value in native_components.values()):
                    raise RuntimeError("Nonfinite native fixed-label loss")
                (native["native_loss_weight"] * native_components["loss"]).backward()
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
                raise RuntimeError("Nonfinite gradient")
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0, error_if_nonfinite=True)
            optimizer.step()
            if any(not torch.isfinite(p).all() for p in model.parameters()):
                raise RuntimeError("Nonfinite model parameters after optimizer step")
            completed = update
            sums.update({key: float(value.detach()) for key, value in components.items()})
            if native_components is not None:
                sums.update({"synthetic_" + key: float(value.detach()) for key, value in components.items()})
                sums.update({"native_" + key: float(value.detach()) for key, value in native_components.items()})
                sums["loss"] += native["native_loss_weight"] * float(native_components["loss"].detach())
            norms.append(float(norm))
            if update % 144 == 0 or update == args.updates:
                row = {"optimizer_updates": update, "interval_updates": update - interval_start,
                       **{key: value / (update - interval_start) for key, value in sums.items()},
                       "learning_rate": optimizer.param_groups[0]["lr"],
                       "gradient_norm_before_clip_max": max(norms), "nonfinite_count": 0,
                       "runtime_seconds": elapsed_prior + time.perf_counter() - started, **resource_snapshot()}
                if args.fold != "refit" and update in plan["cv_evaluation_updates"]:
                    summary, rows = evaluate_validation(model, all_cv[args.fold], cache)
                    if not all(math.isfinite(float(r[key])) for r in rows for key in
                               ("heart_si_sdr_db", "heart_si_sdri_db", "lung_si_sdr_db", "lung_si_sdri_db")):
                        raise RuntimeError("Nonfinite CV metric")
                    row["validation"] = summary
                    atomic_json(summary, directory / f"validation-{update:04d}-summary.json")
                    atomic_jsonl(rows, directory / f"validation-{update:04d}.jsonl")
                    row["runtime_seconds"] = elapsed_prior + time.perf_counter() - started
                history.append(row)
                print(json.dumps(row, sort_keys=True), flush=True)
                persist(update, f"update-{update:04d}.pt" if update in BUDGETS else "resume.pt")
                sums, norms, interval_start = Counter(), [], update
            limits = (native or plan)["resource_limits"]
            if (resource_snapshot()["process_peak_rss_mib"] > limits["peak_rss_gib"] * 1024 or
                    elapsed_prior + time.perf_counter() - started > limits["fold_wall_minutes"] * 60):
                raise RuntimeError("Predeclared CPU memory/runtime budget exceeded")
        persist(completed, "endpoint.pt")
        manifest.update({"status": "COMPLETE_FIXED_ENDPOINT", "optimizer_updates": completed,
                         "stopping_reason": "predeclared_fixed_update_budget", "failures": 0,
                         "runtime_seconds": elapsed_prior + time.perf_counter() - started,
                         "endpoint_sha256": file_sha256(checkpoint_dir / "endpoint.pt"), **resource_snapshot()})
        atomic_json(manifest, directory / "run_manifest.json")
    except BaseException as exc:
        # A failed partial update is not silently resumed as valid evidence.
        atomic_json({"status": "STOPPED_REQUIRES_REVIEW", "error_type": type(exc).__name__,
                     "error": str(exc), "last_completed_optimizer_update": completed,
                     "runtime_seconds": elapsed_prior + time.perf_counter() - started,
                     "test_access": False}, directory / "failure.json")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--prepare-fold-manifest", type=Path,
                        help="Metadata-only: write fold CSV without model initialization or audio reads")
    parser.add_argument("--run-id")
    parser.add_argument("--fold", choices=("f1", "f2", "f3", "f4", "f5", "refit"))
    parser.add_argument("--updates", type=int, choices=BUDGETS)
    parser.add_argument("--init-checkpoint", type=Path)
    parser.add_argument("--init-sha256")
    parser.add_argument("--native-plan", type=Path, help="Optional single predeclared additive-release intervention")
    parser.add_argument("--native-plan-sha256")
    parser.add_argument("--decision-receipt", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.prepare_fold_manifest:
        if any((args.run_id, args.fold, args.updates, args.init_checkpoint,
                args.init_sha256, args.decision_receipt, args.resume, args.native_plan, args.native_plan_sha256)):
            parser.error("Metadata-only preparation cannot be combined with training arguments")
        print(json.dumps(prepare_fold_manifest(json.loads(args.plan.read_text()), args.prepare_fold_manifest), sort_keys=True))
        return
    if not args.run_id or not args.fold or args.updates is None:
        parser.error("Training requires --run-id, --fold, and --updates")
    run(args)


if __name__ == "__main__":
    main()
