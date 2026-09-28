"""Frozen CPU-only T5 baseline and T6 validation; never opens test audio."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import resource
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torchaudio
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
sys.path.insert(0, str(ROOT))
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_data import (MANIFEST_SHA256, Source,
                                  make_mixture, materialize_recipe, read_manifest,
                                  read_source, training_epoch, write_json)
from app.ml.training_objective import (fixed_label_components, normalized_l1,
                                      selection_score)
from scripts.evaluate_ensemble_qualification import si_sdr

ARTIFACTS = ROOT / ".local/training/stethofuse-tcn-v1"
FROZEN_VALIDATION = ARTIFACTS / "t0-t4-20260927T204454Z/validation_recipes.json"
TRAIN_MANIFEST = ROOT / "research/manifests/hls_cmds_split_v1.csv"
CONFIG_PATH = ROOT / "research/configs/stethofuse_tcn_v1.yaml"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def state_sha256(model: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def git_metadata() -> dict[str, object]:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                     text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT,
                                     text=True)
    if status.strip():
        raise RuntimeError("T5 requires a clean committed implementation worktree")
    return {"commit": commit, "dirty": False}


def atomic_torch_save(value: object, path: Path) -> None:
    temporary = path.with_name(path.name + ".tmp")
    torch.save(value, temporary)
    os.replace(temporary, path)


def atomic_json(value: object, path: Path) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def atomic_jsonl(rows: list[dict[str, object]], path: Path) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(temporary, path)


def resource_snapshot() -> dict[str, float]:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {"process_peak_rss_mib": float(peak / 1024)}


def load_allowed_sources() -> tuple[list[Source], dict[tuple[str, str], np.ndarray]]:
    manifest_sha = file_sha256(TRAIN_MANIFEST)
    if manifest_sha != MANIFEST_SHA256:
        raise RuntimeError(f"Frozen source manifest changed: {manifest_sha}")
    # Metadata rows include the locked split, but only development/validation
    # WAV paths are retained or opened below. No test file is hashed or decoded.
    allowed = [source for source in read_manifest()
               if source.split in {"development", "validation"}]
    expected = {("HS", "development"): 36, ("HS", "validation"): 9,
                ("LS", "development"): 36, ("LS", "validation"): 5}
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for source in allowed:
        counts[(source.kind, source.split)] += 1
    if dict(counts) != expected:
        raise RuntimeError(f"Development/validation metadata count mismatch: {dict(counts)}")
    by_family: dict[tuple[str, str], set[str]] = defaultdict(set)
    for source in allowed:
        by_family[(source.kind, source.family)].add(source.split)
        if file_sha256(source.path) != source.sha256:
            raise RuntimeError(f"Development/validation source hash mismatch: {source.kind}/{source.id}")
    if any(len(splits) > 1 for splits in by_family.values()):
        raise RuntimeError("Development/validation family leakage detected")
    cache = {(source.kind, source.id): read_source(source) for source in allowed}
    return allowed, cache


def load_frozen_validation(sources: list[Source], cache: dict[tuple[str, str], np.ndarray]
                           ) -> tuple[list[dict[str, object]], str]:
    if not FROZEN_VALIDATION.is_file():
        raise RuntimeError("Frozen T0-T4 validation recipe manifest is missing; do not regenerate it")
    manifest_sha = file_sha256(FROZEN_VALIDATION)
    payload = json.loads(FROZEN_VALIDATION.read_text())
    if payload.get("source_manifest_sha256") != MANIFEST_SHA256:
        raise RuntimeError("Frozen validation manifest references a different source manifest")
    recipes = payload.get("recipes")
    if not isinstance(recipes, list) or len(recipes) != 225:
        raise RuntimeError("Frozen validation manifest must contain exactly225 recipes")
    source_map = {(s.kind, s.id): s for s in sources}
    by_id = {s.id: s for s in sources}
    if len(by_id) != len(sources):
        raise RuntimeError("Source IDs are ambiguous across allowed partitions")
    seen = set()
    for recipe in recipes:
        key = recipe.get("mixture_id")
        if not key or key in seen:
            raise RuntimeError("Frozen validation mixture IDs are missing or duplicated")
        seen.add(key)
        heart = source_map.get(("HS", str(recipe["heart_id"])))
        lung = source_map.get(("LS", str(recipe["lung_id"])))
        if heart is None or lung is None or heart.split != "validation" or lung.split != "validation":
            raise RuntimeError("Frozen validation recipe references a non-validation source")
        if heart.sha256 != recipe.get("heart_sha256") or lung.sha256 != recipe.get("lung_sha256"):
            raise RuntimeError("Validation source hash differs from frozen recipe")
        if (int(recipe["heart_start"]) != 0 or int(recipe["lung_start"]) != 0 or
                int(recipe.get("crop_samples", 60000)) != 60000):
            raise RuntimeError("Frozen validation crop contract changed")
        if float(recipe["relative_lung_to_heart_db"]) not in {-10, -5, 0, 5, 10}:
            raise RuntimeError("Frozen validation gain condition changed")
    # Avoid reading any split beyond validation while resolving recipes.
    if any(source.split == "test" for source in sources):
        raise RuntimeError("Internal error: locked test source passed to validation evaluator")
    return recipes, manifest_sha


def get_mix_target(recipe: dict[str, object], cache: dict[tuple[str, str], np.ndarray]
                   ) -> tuple[np.ndarray, np.ndarray]:
    heart = cache[("HS", str(recipe["heart_id"]))]
    lung = cache[("LS", str(recipe["lung_id"]))]
    mix, target, gains = make_mixture(
        heart, lung, float(recipe["relative_lung_to_heart_db"]),
        int(recipe["heart_start"]), int(recipe["lung_start"]), crop_samples=60000)
    # Prove the byte-level frozen recipe was followed; do not generate a new
    # condition or replace a failed row.
    for field in ("lung_gain", "shared_gain", "mixture_peak", "network_shared_peak_scale"):
        if field in recipe and not math.isclose(float(recipe[field]),
                float(gains["mixture_peak"] if field == "network_shared_peak_scale" else gains[field]),
                rel_tol=2e-6, abs_tol=1e-8):
            raise RuntimeError(f"Frozen validation {field} does not reproduce")
    return mix, target


def aggregate_absolute(rows: list[dict[str, object]], field: str) -> float:
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        groups[(str(row["heart_family"]), str(row["lung_family"]))].append(float(row[field]))
    return float(np.mean([np.mean(values) for values in groups.values()]))


def evaluate_validation(model: StethoFuseConvTasNet,
                        recipes: list[dict[str, object]],
                        cache: dict[tuple[str, str], np.ndarray]
                        ) -> tuple[dict[str, object], list[dict[str, object]]]:
    started = time.perf_counter()
    rows = []
    model.eval()
    with torch.inference_mode():
        for recipe in recipes:
            mixture, target = get_mix_target(recipe, cache)
            estimated = model.separate_recording(torch.from_numpy(mixture.copy()))
            if estimated.shape != target.shape or not torch.isfinite(estimated).all():
                raise RuntimeError(f"Invalid validation output for {recipe['mixture_id']}")
            estimates = estimated.cpu().numpy()
            source_metrics = {}
            for index, label in enumerate(("heart", "lung")):
                score = si_sdr(estimates[index], target[index])
                baseline = si_sdr(mixture, target[index])
                source_metrics[label] = {"si_sdr_db": score,
                                         "si_sdri_db": score - baseline}
            rows.append({"mixture_id": recipe["mixture_id"],
                         "heart_id": recipe["heart_id"], "lung_id": recipe["lung_id"],
                         "heart_family": recipe["heart_family"], "lung_family": recipe["lung_family"],
                         "relative_lung_to_heart_db": recipe["relative_lung_to_heart_db"],
                         "heart_si_sdr_db": source_metrics["heart"]["si_sdr_db"],
                         "heart_si_sdri_db": source_metrics["heart"]["si_sdri_db"],
                         "lung_si_sdr_db": source_metrics["lung"]["si_sdr_db"],
                         "lung_si_sdri_db": source_metrics["lung"]["si_sdri_db"]})
    model.train()
    selection = selection_score(rows)
    summaries = {}
    for source in ("heart", "lung"):
        for metric in ("si_sdr_db", "si_sdri_db"):
            key = f"{source}_{metric}"
            values = np.asarray([float(row[key]) for row in rows], dtype=np.float64)
            summaries[key] = {"family_balanced_mean": aggregate_absolute(rows, key),
                               "pooled_mean": float(values.mean()),
                               "pooled_median": float(np.median(values)),
                               "pooled_iqr": float(np.quantile(values, .75) - np.quantile(values, .25))}
    summary = {**summaries, **selection, "conditions": len(rows), "failures": 0,
               "runtime_seconds": time.perf_counter() - started,
               "family_pair_groups": len({(r["heart_family"], r["lung_family"]) for r in rows})}
    return summary, rows


def realize_training_epoch(epoch: int, sources: list[Source],
                           cache: dict[tuple[str, str], np.ndarray],
                           recipe_root: Path, seed: int, retry_limit: int
                           ) -> tuple[torch.Tensor, torch.Tensor, str]:
    recipes = training_epoch(sources, epoch, seed)
    if len(recipes) != 576:
        raise RuntimeError(f"Training epoch {epoch} has {len(recipes)} recipes, expected576")
    receipts, mixtures, targets = [], [], []
    for recipe in recipes:
        # The frozen config permits at most three additional independent crops
        # for a near-silent source window. All retry choices use keyed PCG64
        # streams and the realized offsets/retry count are saved in the recipe.
        realized = dict(recipe)
        h_source = cache[("HS", str(recipe["heart_id"]))]
        l_source = cache[("LS", str(recipe["lung_id"]))]
        retries = 0
        while True:
            hs = int(realized["heart_start"])
            ls = int(realized["lung_start"])
            h_crop = h_source[hs:hs + 32000]
            l_crop = l_source[ls:ls + 32000]
            h_rms = float(np.sqrt(np.mean(h_crop.astype(np.float64) ** 2)))
            l_rms = float(np.sqrt(np.mean(l_crop.astype(np.float64) ** 2)))
            if h_crop.size == 32000 and l_crop.size == 32000 and min(h_rms, l_rms) >= 1e-6:
                break
            if retries >= retry_limit:
                raise RuntimeError(f"Silent crop after {retry_limit} retries: "
                                   f"{recipe['heart_id']}/{recipe['lung_id']}")
            rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(
                [seed, epoch, int(recipe["draw_index"]), 100 + retries])))
            realized["heart_start"] = int(rng.integers(0, 28001))
            realized["lung_start"] = int(rng.integers(0, 28001))
            retries += 1
        realized["silent_crop_retries"] = retries
        mix, target, receipt = materialize_recipe(realized, sources, cache)
        scale = float(receipt["network_shared_peak_scale"])
        if not math.isfinite(scale) or scale <= 0:
            raise RuntimeError("Invalid shared network input gain")
        x = mix / scale
        y = target / scale
        if not np.isfinite(x).all() or not np.isfinite(y).all():
            raise RuntimeError("Nonfinite materialized training mixture")
        receipts.append(receipt)
        mixtures.append(x)
        targets.append(y)
    serialized = "".join(json.dumps(row, sort_keys=True) + "\n" for row in receipts).encode()
    recipe_hash = bytes_sha256(serialized)
    path = recipe_root / f"epoch-{epoch:03d}.jsonl"
    if path.exists() and path.read_bytes() != serialized:
        raise RuntimeError(f"Existing deterministic epoch recipe differs: {path}")
    if not path.exists():
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(serialized)
        os.replace(temporary, path)
    # Recipes are on disk before this epoch's first optimizer update.
    return (torch.from_numpy(np.stack(mixtures)[:, None, :]),
            torch.from_numpy(np.stack(targets)), recipe_hash)


def model_checkpoint(model: StethoFuseConvTasNet, epoch: int,
                     metadata: dict[str, object]) -> dict[str, object]:
    return {"architecture_version": model.architecture_version,
            "parameter_count": model.parameter_count, "epoch": epoch,
            "state_dict": model.state_dict(), "metadata": metadata}


def resume_state(model: StethoFuseConvTasNet, optimizer: torch.optim.Optimizer,
                 scheduler: torch.optim.lr_scheduler.ReduceLROnPlateau,
                 next_epoch: int, run_state: dict[str, object]) -> dict[str, object]:
    return {"schema_version": 1, "architecture_version": model.architecture_version,
            "model": model.state_dict(), "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(), "next_epoch": next_epoch,
            "run_state": run_state, "torch_rng_state": torch.get_rng_state(),
            "numpy_rng_state": np.random.get_state(), "python_rng_state": random.getstate()}


def write_checksum_file(run_dir: Path) -> None:
    rows = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256" or path.name.endswith(".tmp"):
            continue
        rows.append(f"{file_sha256(path)}  {path.relative_to(run_dir)}")
    (run_dir / "checksums.sha256").write_text("\n".join(rows) + "\n")


def rebuild_history(run_dir: Path) -> None:
    records = []
    for path in sorted((run_dir / "validation").glob("epoch-*.json")):
        records.append(json.loads(path.read_text()))
    atomic_jsonl(records, run_dir / "history.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-id", help="Fresh baseline run ID; must not exist")
    group.add_argument("--resume", type=Path, help="Resume an epoch-boundary checkpoint")
    args = parser.parse_args()

    metadata = git_metadata()  # Exact clean commit recorded before model initialization.
    config = yaml.safe_load(CONFIG_PATH.read_text())
    if config["training"]["device"] != "cpu" or torch.cuda.is_available():
        # CUDA availability is not used even if present; this run is explicitly CPU.
        if config["training"]["device"] != "cpu":
            raise RuntimeError("Frozen baseline configuration is no longer CPU")
    if torch.__version__ != config["dependencies"]["torch"] or \
            torchaudio.__version__ != config["dependencies"]["torchaudio"]:
        raise RuntimeError("Training environment differs from the frozen Torch/torchaudio pin")
    if file_sha256(TRAIN_MANIFEST) != MANIFEST_SHA256:
        raise RuntimeError("Frozen source manifest SHA-256 mismatch")

    if args.run_id:
        run_dir = ARTIFACTS / args.run_id
        if run_dir.exists():
            raise RuntimeError("Run ID already exists; refusing to overwrite an experiment")
        run_dir.mkdir(parents=True)
    else:
        run_dir = args.resume.resolve()
        if not run_dir.is_dir():
            raise RuntimeError("Resume directory does not exist")
    for child in ("recipes", "validation", "checkpoints"):
        (run_dir / child).mkdir(exist_ok=True)
    config_bytes = CONFIG_PATH.read_bytes()
    config_hash = bytes_sha256(config_bytes)
    config_copy = run_dir / "config.yaml"
    if config_copy.exists() and config_copy.read_bytes() != config_bytes:
        raise RuntimeError("Run configuration changed; cannot resume this experiment")
    if not config_copy.exists():
        config_copy.write_bytes(config_bytes)
    sources, source_cache = load_allowed_sources()
    val_recipes, val_manifest_hash = load_frozen_validation(sources, source_cache)
    frozen_copy = run_dir / "validation/frozen_recipes.json"
    original_validation_bytes = FROZEN_VALIDATION.read_bytes()
    if frozen_copy.exists() and frozen_copy.read_bytes() != original_validation_bytes:
        raise RuntimeError("Run validation recipe copy differs from the frozen manifest")
    if not frozen_copy.exists():
        frozen_copy.write_bytes(original_validation_bytes)
    split_snapshot = run_dir / "eligible_split.csv"
    if not split_snapshot.exists():
        with split_snapshot.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("kind", "id", "family", "split", "sha256"))
            for source in sorted(sources, key=lambda s: (s.kind, s.split, s.family, s.id)):
                writer.writerow((source.kind, source.id, source.family, source.split, source.sha256))

    if args.run_id:
        if args.run_id != "baseline-seed20260928" and not args.run_id.startswith("baseline-seed20260928-"):
            raise RuntimeError("Fresh T5 run ID must identify the frozen seed20260928 baseline")
        torch.set_num_threads(config["training"]["threads"])
        torch.set_num_interop_threads(config["training"]["interop_threads"])
        torch.manual_seed(config["seed"])
        np.random.seed(config["seed"])
        random.seed(config["seed"])
        torch.use_deterministic_algorithms(True)
        model = StethoFuseConvTasNet().cpu()
        if model.parameter_count != config["model"]["parameter_count"]:
            raise RuntimeError(f"Parameter count mismatch: {model.parameter_count}")
        initialization_hash = state_sha256(model)
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=config["training"]["learning_rate"],
            betas=tuple(config["training"]["betas"]),
            eps=config["training"]["optimizer_epsilon"],
            weight_decay=config["training"]["weight_decay"])
        scheduler_config = config["training"]["scheduler"]
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode=scheduler_config["mode"], factor=scheduler_config["factor"],
            patience=scheduler_config["patience"], threshold=scheduler_config["threshold"],
            threshold_mode=scheduler_config["threshold_mode"], min_lr=scheduler_config["min_lr"])
        run_state: dict[str, object] = {
            "best_q": None, "best_tie_mean": None, "best_epoch": None,
            "early_anchor_q": None, "early_wait": 0, "elapsed_prior_seconds": 0.0,
            "last_lr": config["training"]["learning_rate"], "status": "running"}
        atomic_json({"schema_version": 1, "status": "running", "run_id": args.run_id,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "git_commit": metadata["commit"], "git_dirty": metadata["dirty"],
            "starting_commit_before_initialization": metadata["commit"],
            "fresh_initialization": True, "initialization_source": "seeded_torchaudio_scratch_no_checkpoint",
            "fresh_initialization_state_sha256": initialization_hash,
            "parameter_count": model.parameter_count, "seed": config["seed"],
            "architecture_version": config["architecture_version"],
            "optimizer": config["training"]["optimizer"],
            "initial_learning_rate": config["training"]["learning_rate"],
            "weight_decay": config["training"]["weight_decay"],
            "batch_size": config["training"]["batch_size"],
            "gradient_clip_norm": config["training"]["gradient_clip_norm"],
            "loss": config["loss"], "scheduler": config["training"]["scheduler"],
            "early_stopping": config["training"]["early_stopping"],
            "config_sha256": config_hash, "source_manifest_sha256": MANIFEST_SHA256,
            "frozen_validation_manifest_sha256": val_manifest_hash,
            "torch": torch.__version__, "torchaudio": torchaudio.__version__,
            "numpy": np.__version__, "python": platform.python_version(),
            "platform": platform.platform(), "cpu_count": os.cpu_count(),
            "torch_threads": config["training"]["threads"],
            "torch_interop_threads": config["training"]["interop_threads"],
            "device": "cpu", "test_access": "NONE", "t4_checkpoint_loaded": False,
            "validation_conditions": len(val_recipes)}, run_dir / "run.json")
        # Persist seeded initial state so an interruption in epoch zero can resume
        # the exact experiment instead of initializing another run.
        initial_state = resume_state(model, optimizer, scheduler, 0, run_state)
        atomic_torch_save(initial_state, run_dir / "checkpoints/resume.pt")
    else:
        run_manifest = json.loads((run_dir / "run.json").read_text())
        if run_manifest.get("status") not in {"running", "interrupted"}:
            raise RuntimeError("Only a running or interrupted baseline may be resumed")
        for field, expected_value in (("git_commit", metadata["commit"]),
                                      ("config_sha256", config_hash),
                                      ("source_manifest_sha256", MANIFEST_SHA256),
                                      ("frozen_validation_manifest_sha256", val_manifest_hash)):
            if run_manifest.get(field) != expected_value:
                raise RuntimeError(f"Cannot resume: {field} differs from original experiment")
        resume_path = run_dir / "checkpoints/resume.pt"
        state = torch.load(resume_path, map_location="cpu", weights_only=False)
        if state.get("architecture_version") != StethoFuseConvTasNet.architecture_version:
            raise RuntimeError("Resume architecture mismatch")
        torch.set_num_threads(config["training"]["threads"])
        torch.set_num_interop_threads(config["training"]["interop_threads"])
        torch.use_deterministic_algorithms(True)
        model = StethoFuseConvTasNet().cpu()
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=config["training"]["learning_rate"],
            betas=tuple(config["training"]["betas"]), eps=config["training"]["optimizer_epsilon"],
            weight_decay=config["training"]["weight_decay"])
        sc = config["training"]["scheduler"]
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode=sc["mode"], factor=sc["factor"], patience=sc["patience"],
            threshold=sc["threshold"], threshold_mode=sc["threshold_mode"], min_lr=sc["min_lr"])
        model.load_state_dict(state["model"], strict=True)
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        torch.set_rng_state(state["torch_rng_state"])
        np.random.set_state(state["numpy_rng_state"])
        random.setstate(state["python_rng_state"])
        run_state = state["run_state"]
        if run_state.get("status") not in {"running", "interrupted"}:
            raise RuntimeError("Only an interrupted/in-progress run can be resumed")
        run_state["status"] = "running"
        atomic_json({**run_manifest, "status": "running", "resumed_at_utc":
                     datetime.now(timezone.utc).isoformat()}, run_dir / "run.json")

    run_id = run_dir.name
    epoch_seconds: list[float] = []
    session_start = time.perf_counter()
    start_epoch = int(0 if args.run_id else state["next_epoch"])
    completed_epoch = start_epoch
    elapsed_prior = float(run_state.get("elapsed_prior_seconds", 0.0))
    max_epochs = int(config["training"]["max_epochs"])
    patience = int(config["training"]["early_stopping"]["patience_epochs"])
    significant = float(config["training"]["early_stopping"]["significant_improvement_db"])
    best_path = run_dir / "checkpoints/best.pt"
    latest_record = run_dir / "run.json"

    try:
        for epoch in range(start_epoch, max_epochs):
            epoch_start = time.perf_counter()
            train_x, train_y, recipe_hash = realize_training_epoch(
                epoch, sources, source_cache, run_dir / "recipes", int(config["seed"]),
                int(config["data"]["crop_retry_limit"]))
            # Persist the complete deterministic epoch recipe before its first
            # optimizer update. For epoch 0 this is the baseline's training
            # recipe hash required in the pre-update provenance record.
            run_meta = json.loads(latest_record.read_text())
            prepared_recipes = dict(run_meta.get("training_recipe_sha256_by_epoch", {}))
            prior_hash = prepared_recipes.get(str(epoch + 1))
            if prior_hash is not None and prior_hash != recipe_hash:
                raise RuntimeError(f"Deterministic training recipe changed for epoch {epoch + 1}")
            prepared_recipes[str(epoch + 1)] = recipe_hash
            run_meta.update({"prepared_epoch": epoch + 1,
                             "prepared_epoch_recipe_sha256": recipe_hash,
                             "training_recipe_sha256_by_epoch": prepared_recipes})
            atomic_json(run_meta, latest_record)
            model.train()
            size = int(train_x.shape[0])
            batch_size = int(config["training"]["batch_size"])
            losses, si_terms, l1_terms, grad_norms = [], [], [], []
            nonfinite_count = 0
            for begin in range(0, size, batch_size):
                x = train_x[begin:begin + batch_size]
                y = train_y[begin:begin + batch_size]
                optimizer.zero_grad(set_to_none=True)
                estimate = model(x)
                components = fixed_label_components(estimate, y)
                loss = components["loss"]
                if not torch.isfinite(loss) or not all(torch.isfinite(v) for v in components.values()):
                    nonfinite_count += 1
                    raise RuntimeError(f"Nonfinite training objective at epoch{epoch + 1}")
                loss.backward()
                grad_norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), float(config["training"]["gradient_clip_norm"]))
                if not torch.isfinite(grad_norm) or any(
                        p.grad is not None and not torch.isfinite(p.grad).all()
                        for p in model.parameters()):
                    nonfinite_count += 1
                    raise RuntimeError(f"Nonfinite training gradient at epoch{epoch + 1}")
                grad_norms.append(float(grad_norm.detach()))
                optimizer.step()
                losses.append(float(loss.detach()))
                si_terms.append(float(components["negative_si_sdr"].detach()))
                l1_terms.append(float(components["normalized_waveform_l1"].detach()))
            del train_x, train_y

            val_summary, val_rows = evaluate_validation(model, val_recipes, source_cache)
            q = float(val_summary["selection_q_db"])
            tie_mean = float(val_summary["tie_break_mean_db"])
            best_q = run_state.get("best_q")
            best_mean = run_state.get("best_tie_mean")
            is_best = (best_q is None or q > float(best_q) + 1e-6 or
                       (abs(q - float(best_q)) <= 1e-6 and tie_mean > float(best_mean) + 1e-6))
            old_lr = float(optimizer.param_groups[0]["lr"])
            scheduler.step(q)
            new_lr = float(optimizer.param_groups[0]["lr"])
            if is_best:
                run_state["best_q"] = q
                run_state["best_tie_mean"] = tie_mean
                run_state["best_epoch"] = epoch + 1
                atomic_torch_save(model_checkpoint(model, epoch + 1, {
                    "selection_q_db": q, "tie_break_mean_db": tie_mean,
                    "validation_summary": val_summary, "config_sha256": config_hash,
                    "source_manifest_sha256": MANIFEST_SHA256,
                    "validation_manifest_sha256": val_manifest_hash,
                    "training_recipe_sha256": recipe_hash, "git_commit": metadata["commit"]}),
                    best_path)
            anchor = run_state.get("early_anchor_q")
            if anchor is None or q >= float(anchor) + significant:
                run_state["early_anchor_q"] = q
                run_state["early_wait"] = 0
            else:
                run_state["early_wait"] = int(run_state["early_wait"]) + 1

            duration = time.perf_counter() - epoch_start
            epoch_seconds.append(duration)
            completed = epoch + 1
            completed_epoch = completed
            elapsed_total = elapsed_prior + time.perf_counter() - session_start
            record = {"epoch": completed, "training_loss": float(np.mean(losses)),
                      "negative_si_sdr_component": float(np.mean(si_terms)),
                      "normalized_waveform_l1_component": float(np.mean(l1_terms)),
                      "learning_rate": new_lr, "learning_rate_changed": old_lr != new_lr,
                      "validation": val_summary, "selection_q_db": q,
                      "balanced_mean_db": tie_mean, "best_so_far": bool(is_best),
                      "best_epoch": run_state["best_epoch"], "duration_seconds": duration,
                      "cumulative_training_seconds": elapsed_total,
                      "peak_rss_mib": resource_snapshot()["process_peak_rss_mib"],
                      "nonfinite_count": nonfinite_count, "gradient_health": "finite",
                      "max_preclip_gradient_norm": max(grad_norms),
                      "training_recipe_sha256": recipe_hash,
                      "validation_failure_count": val_summary["failures"]}
            atomic_jsonl(val_rows, run_dir / f"validation/epoch-{completed:03d}.jsonl")
            atomic_json(record, run_dir / f"validation/epoch-{completed:03d}.json")
            run_state["elapsed_prior_seconds"] = elapsed_total
            run_state["last_lr"] = new_lr
            run_state["status"] = "running"
            state = resume_state(model, optimizer, scheduler, completed, run_state)
            atomic_torch_save(state, run_dir / "checkpoints/resume.pt")
            run_meta = json.loads(latest_record.read_text())
            run_meta.update({"status": "running", "last_completed_epoch": completed,
                             "best_epoch": run_state["best_epoch"],
                             "best_selection_q_db": run_state["best_q"],
                             "last_epoch_recipe_sha256": recipe_hash,
                             "cumulative_training_seconds": elapsed_total,
                             **resource_snapshot()})
            atomic_json(run_meta, latest_record)
            rebuild_history(run_dir)
            print(json.dumps({"epoch": completed, "loss": record["training_loss"],
                "heart_si_sdr": val_summary["heart_si_sdr_db"]["family_balanced_mean"],
                "heart_si_sdri": val_summary["heart_si_sdri_db"]["family_balanced_mean"],
                "lung_si_sdr": val_summary["lung_si_sdr_db"]["family_balanced_mean"],
                "lung_si_sdri": val_summary["lung_si_sdri_db"]["family_balanced_mean"],
                "selection_q": q, "lr": new_lr, "epoch_seconds": duration,
                "cumulative_seconds": elapsed_total, "best": bool(is_best)}, sort_keys=True),
                flush=True)

            if record["peak_rss_mib"] > 4096:
                run_state["status"] = "resource_stopped"
                break
            if completed >= 3:
                mean_epoch = float(np.mean(epoch_seconds[-3:])) if epoch_seconds else duration
                projected = elapsed_total + mean_epoch * max_epochs - completed * mean_epoch
                if projected / 3600 > float(config["training"]["resource_guard"]["stop_and_checkpoint_if_projected_hours_exceed"]):
                    run_state["status"] = "runtime_guard_stopped"
                    run_meta = json.loads(latest_record.read_text())
                    run_meta["runtime_projection_hours_after_epoch_3"] = projected / 3600
                    atomic_json(run_meta, latest_record)
                    break
            if int(run_state["early_wait"]) >= patience:
                run_state["status"] = "early_stopped"
                break
            if completed == max_epochs:
                run_state["status"] = "completed_80_epochs"
                break
    except KeyboardInterrupt:
        run_state["status"] = "interrupted"
        atomic_json({**json.loads(latest_record.read_text()), "status": "interrupted",
                     "interrupted_at_utc": datetime.now(timezone.utc).isoformat()}, latest_record)
        print("Interrupted at an epoch boundary; resume.pt contains the last completed state.",
              file=sys.stderr, flush=True)
        return 130
    except Exception as exc:
        atomic_json({**json.loads(latest_record.read_text()), "status": "failed",
                     "failure_type": type(exc).__name__, "failure_message": str(exc),
                     "failed_at_utc": datetime.now(timezone.utc).isoformat()}, latest_record)
        raise

    final_epoch = completed_epoch
    if run_state["status"] == "running":
        run_state["status"] = "completed_80_epochs" if final_epoch >= max_epochs else "resource_stopped"
    run_state["elapsed_prior_seconds"] = elapsed_prior + time.perf_counter() - session_start
    atomic_torch_save(model_checkpoint(model, final_epoch, {"status": run_state["status"]}),
                      run_dir / "checkpoints/final.pt")
    if best_path.is_file():
        best_state = torch.load(best_path, map_location="cpu", weights_only=False)
        model.load_state_dict(best_state["state_dict"], strict=True)
        final_summary, final_rows = evaluate_validation(model, val_recipes, source_cache)
        atomic_json(final_summary, run_dir / "validation/best_checkpoint_summary.json")
        atomic_jsonl(final_rows, run_dir / "validation/best_checkpoint_per_condition.jsonl")
    else:
        raise RuntimeError("No valid best checkpoint was produced")
    final_run = json.loads(latest_record.read_text())
    final_run.update({"status": run_state["status"], "epochs_completed": final_epoch,
                      "best_epoch": run_state["best_epoch"], "best_selection_q_db": run_state["best_q"],
                      "best_tie_break_mean_db": run_state["best_tie_mean"],
                      "total_training_seconds": run_state["elapsed_prior_seconds"],
                      "best_checkpoint_sha256": file_sha256(best_path),
                      "final_checkpoint_sha256": file_sha256(run_dir / "checkpoints/final.pt"),
                      "final_best_validation": final_summary,
                      "test_audio_opened": False, "test_metrics_computed": False})
    atomic_json(final_run, latest_record)
    write_checksum_file(run_dir)
    print(json.dumps({"run_id": run_id, "status": run_state["status"],
                      "epochs_completed": final_epoch, "best_epoch": run_state["best_epoch"],
                      "best_validation": final_summary,
                      "runtime_seconds": run_state["elapsed_prior_seconds"],
                      "peak_rss_mib": resource_snapshot()["process_peak_rss_mib"],
                      "test_access": "NONE", "production_touched": False}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
