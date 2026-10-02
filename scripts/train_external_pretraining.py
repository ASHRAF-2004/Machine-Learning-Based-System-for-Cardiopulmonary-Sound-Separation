"""Frozen external-source pretraining only; no HLS source or T9 file discovery.

Accepted clinical recordings are source-dominant Tier B targets, not isolated
clean references. This runner never selects a checkpoint by external/HLS score.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
from datetime import datetime, timezone
import hashlib
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_data import make_mixture
from app.ml.training_objective import fixed_label_components
from scripts.train_stethofuse_baseline import (
    atomic_json, atomic_jsonl, atomic_torch_save, file_sha256, git_metadata,
    model_checkpoint, resource_snapshot, state_sha256,
)
from scripts.evaluate_ensemble_qualification import si_sdr

KNOWN_AGES = {"Neonate", "Infant", "Child", "Adolescent", "Young Adult", "Adult", "Older Adult"}
SOURCES = ("heart", "lung")


def content_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def external_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    resolved = path.resolve()
    if any(part.lower() == "hls_cmds" for p in (path, resolved) for part in p.parts):
        raise ValueError("HLS/T9 paths are forbidden in external pretraining")
    return resolved


def subject_key(row: dict) -> tuple[str, str]:
    group = row.get("dataset_group") or row["dataset_id"]
    subject = row.get("merged_subject_id") or row.get("split_group") or row.get("subject_id")
    if not group or subject is None or str(subject).strip().lower() in {"", "unknown", "none", "null"}:
        raise ValueError("An explicit known subject/split group is required")
    return str(group), str(subject)


def external_holdout(row: dict) -> bool:
    group, subject = subject_key(row)
    return int(hashlib.sha256(f"external-v1:{group}:{subject}".encode()).hexdigest(), 16) % 10 == 0


def normalize_registry(payload: dict) -> list[dict]:
    rows = payload.get("recordings")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a frozen accepted registry with a nonempty recordings list")
    normalized, ids, hashes = [], set(), set()
    for original in rows:
        row = dict(original)
        if row.get("source_type") not in SOURCES or row.get("source_purity_tier") not in {"A", "B"}:
            raise ValueError("Every accepted row must have a fixed source class and qualified A/B tier")
        if row.get("exclusion_reasons") or str(row.get("quality_status", "")).startswith("EXCLUDED"):
            raise ValueError("Rejected quality rows cannot enter the accepted registry")
        if not all(row.get(key) for key in ("source_purity_evidence", "source_purity_confidence", "purity_reviewer")):
            raise ValueError("Source-purity evidence/reviewer/confidence must be explicit")
        if row.get("canonical_sample_rate") != 4000 or row.get("canonical_channel_count") != 1:
            raise ValueError("Expected qualified 4-kHz mono canonical recordings")
        key = f"{row['dataset_id']}:{row['recording_id']}"
        if key in ids or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("derived_sha256"))):
            raise ValueError("Recording IDs/hashes are invalid or duplicated")
        ids.add(key)
        if row["derived_sha256"] in hashes:
            raise ValueError("Exact duplicate canonical recording remains in accepted registry")
        hashes.add(row["derived_sha256"])
        path = external_path(str(row["derived_path"]))
        if path.suffix != ".npy":
            raise ValueError("Only qualified canonical NPY files may be decoded")
        samples = int(row["canonical_samples"])
        if row.get("valid_intervals_4k") is not None:
            intervals = row["valid_intervals_4k"]
        else:
            intervals = [[math.ceil(float(a) * 4000), math.floor(float(b) * 4000)]
                         for a, b in row.get("eligible_intervals_seconds", [])]
        intervals = sorted(intervals)
        last_end = -1
        for a, b in intervals:
            if not (isinstance(a, int) and isinstance(b, int) and 0 <= a < b <= samples and
                    b - a >= 32000 and a >= last_end):
                raise ValueError("Eligible crop intervals must be disjoint, in bounds and at least eight seconds")
            last_end = b
        if not intervals:
            raise ValueError("No eligible eight-second interval")
        label = row.get("family_id") or row.get("annotation", {}).get("record_annotation") or row.get("pathology")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("A released sound-label family must be explicit")
        group, subject = subject_key(row)
        partition = "external_validation" if external_holdout(row) else "train"
        if row.get("partition", partition) != partition:
            raise ValueError("Registry partition differs from the frozen merged-subject hash rule")
        row.update({"registry_key": key, "derived_path": str(path), "valid_intervals_4k": intervals,
                    "resolved_dataset_group": group, "resolved_subject_id": subject,
                    "sampling_label": label, "resolved_partition": partition})
        normalized.append(row)
    return sorted(normalized, key=lambda row: row["registry_key"])


def hierarchy(rows: list[dict], partition: str = "train") -> tuple[list[str], dict, list[dict]]:
    if partition not in {"train", "external_validation"}:
        raise ValueError("Unknown external partition")
    known = [r for r in rows if r["resolved_partition"] == partition and r.get("age_group") in KNOWN_AGES]
    ages = sorted(set(r["age_group"] for r in known if r["source_type"] == "heart") &
                  set(r["age_group"] for r in known if r["source_type"] == "lung"))
    if not ages:
        raise ValueError("No known age domain is shared by eligible heart and lung subjects")
    tree, used = {}, []
    for row in known:
        if row["age_group"] not in ages:
            continue
        node = tree.setdefault(row["age_group"], {}).setdefault(row["source_type"], {})
        # Releases/mirrors of one corpus are one dataset domain, not extra votes.
        node = node.setdefault(row["resolved_dataset_group"], {}).setdefault(row["sampling_label"], {})
        node.setdefault((row["resolved_dataset_group"], row["resolved_subject_id"]), []).append(row)
        used.append(row)
    return ages, tree, used


def choose_crop(row: dict, rng: np.random.Generator) -> int:
    intervals = row["valid_intervals_4k"]
    counts = [b - a - 32000 + 1 for a, b in intervals]
    selected = int(rng.integers(sum(counts)))
    for (start, _), count in zip(intervals, counts):
        if selected < count:
            return start + selected
        selected -= count
    raise AssertionError("Crop index outside enumerated valid starts")


def recipe_schedule(rows: list[dict], draws: int, seed: int, partition: str = "train") -> list[dict]:
    ages, tree, _ = hierarchy(rows, partition)
    recipes = []
    for draw in range(draws):
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, draw, 0])))
        age = ages[int(rng.integers(len(ages)))]
        recipe = {"draw_index": draw, "age_group": age, "seed_key": [seed, draw, 0], "partition": partition}
        for source in SOURCES:
            node = tree[age][source]
            # Uniform dataset, then released label, then merged subject, then recording.
            for _ in range(3):
                keys = sorted(node)
                node = node[keys[int(rng.integers(len(keys)))]]
            selected = node[int(rng.integers(len(node)))]
            recipe[f"{source}_registry_key"] = selected["registry_key"]
            recipe[f"{source}_derived_sha256"] = selected["derived_sha256"]
            recipe[f"{source}_start"] = choose_crop(selected, rng)
        recipe["relative_lung_to_heart_db"] = float(rng.uniform(-10, 10))
        recipe["recipe_id"] = content_hash(recipe)[:20]
        recipes.append(recipe)
    return recipes


class AudioCache:
    """Bounded read-only maps; originals are never opened by the trainer."""
    def __init__(self, rows: list[dict], capacity: int = 32):
        self.rows = {row["registry_key"]: row for row in rows}
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: str) -> np.ndarray:
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            row = self.rows[key]
            data = np.load(external_path(row["derived_path"]), mmap_mode="r", allow_pickle=False)
            if data.dtype != np.float32 or data.shape != (row["canonical_samples"],):
                raise ValueError("Canonical array dtype or shape changed")
            self.cache[key] = data
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
        return self.cache[key]


def materialize(recipe: dict, cache: AudioCache) -> tuple[np.ndarray, np.ndarray, dict]:
    heart = cache.get(recipe["heart_registry_key"])
    lung = cache.get(recipe["lung_registry_key"])
    mixture, targets, gains = make_mixture(heart, lung, recipe["relative_lung_to_heart_db"],
                                         recipe["heart_start"], recipe["lung_start"], 32000)
    peak = float(np.max(np.abs(mixture)))
    if not math.isfinite(peak) or peak <= 0:
        raise RuntimeError("Invalid shared mixture normalization")
    receipt = {**recipe, **gains, "network_shared_peak_scale": peak,
               "mixture_sha256": hashlib.sha256(mixture.astype("<f4").tobytes()).hexdigest()}
    return mixture / peak, targets / peak, receipt


def validate_config(config: dict, phase: str) -> int:
    expected = {"test_access_allowed": False, "architecture_version": "stethofuse-convtasnet-4k-small-v1",
                "parameter_count": 171313, "seed": 20260928, "cpu_threads": 2, "interop_threads": 1,
                "batch_size": 4, "sample_rate": 4000, "crop_samples": 32000,
                "loss": "fixed_label_mean_negative_si_sdr_plus_5_rms_normalized_l1", "scheduler": None}
    optimizer = {"name": "AdamW", "lr": .001, "weight_decay": .0001, "betas": [.9, .999],
                 "eps": 1e-8, "gradient_clip_norm": 5.0}
    if any(config.get(key) != value for key, value in expected.items()) or config["optimizer"] != optimizer:
        raise ValueError("External pretraining config differs from the frozen first data experiment")
    updates = config["pilot_optimizer_updates"] if phase == "pilot" else config["if_pilot_passes"]["full_pretrain_updates"]
    if updates != (2304 if phase == "pilot" else 9216):
        raise ValueError("Unapproved external optimizer budget")
    if (config["external_validation"]["conditions"] != 32 or config["external_validation"]["seed"] != 20260929 or
            config["external_validation"]["timing"] != "endpoint only"):
        raise ValueError("External sanity policy changed")
    return updates


def external_sanity(model: StethoFuseConvTasNet, recipes: list[dict], cache: AudioCache) -> tuple[dict, list[dict]]:
    """One 32-condition held-out-subject check; imperfect targets, never selection."""
    started = time.perf_counter()
    rows = []
    model.eval()
    with torch.inference_mode():
        for recipe in recipes:
            if recipe["partition"] != "external_validation":
                raise ValueError("External sanity recipe is not held out")
            mix, target, _ = materialize(recipe, cache)
            estimate = model(torch.from_numpy(mix)[None, None])[0].numpy()
            if estimate.shape != (2, 32000) or not np.isfinite(estimate).all():
                raise RuntimeError("Nonfinite external endpoint sanity output")
            row = {"recipe_id": recipe["recipe_id"], "age_group": recipe["age_group"],
                   "heart_registry_key": recipe["heart_registry_key"], "lung_registry_key": recipe["lung_registry_key"],
                   "relative_lung_to_heart_db": recipe["relative_lung_to_heart_db"]}
            for index, source in enumerate(SOURCES):
                value = si_sdr(estimate[index], target[index])
                improvement = value - si_sdr(mix, target[index])
                if not math.isfinite(value) or not math.isfinite(improvement):
                    raise RuntimeError("Nonfinite external endpoint sanity metric")
                row[f"{source}_si_sdr_db"] = value
                row[f"{source}_si_sdri_db"] = improvement
            rows.append(row)
    model.train()
    summary = {"conditions": len(rows), "failures": 0, "runtime_seconds": time.perf_counter() - started,
               "checkpoint_selection_used": False, "source_targets": "Tier B imperfect clinical sources, not isolated references",
               "inference": "8-second normalized forward with fixed-label target-free consistency; external sanity only",
               "independence": "correlated remixes, not 32 independent subjects"}
    for source in SOURCES:
        for metric in ("si_sdr_db", "si_sdri_db"):
            values = [row[f"{source}_{metric}"] for row in rows]
            summary[f"{source}_{metric}"] = {"descriptive_mean": float(np.mean(values)),
                                             "descriptive_median": float(np.median(values))}
    return summary, rows


def run(args: argparse.Namespace) -> None:
    start = time.perf_counter()
    git = git_metadata()
    for path, expected in ((args.config, args.config_sha256), (args.registry, args.registry_sha256)):
        if not re.fullmatch(r"[0-9a-f]{64}", expected) or file_sha256(external_path(path)) != expected:
            raise ValueError("Frozen config/accepted-registry hash mismatch")
    config = json.loads(args.config.read_text())
    updates = validate_config(config, args.phase)
    pilot_decision_hash = None
    if args.phase == 'full':
        if not args.pilot_decision:
            raise ValueError('Full pretraining requires the accepted frozen pilot transfer decision')
        decision = json.loads(args.pilot_decision.read_text())
        if (decision.get('kind') != 'EXTERNAL_TRANSFER_ADOPTION_DECISION' or
                decision.get('accepted') is not True or
                decision.get('pilot_protocol_sha256') != args.config_sha256 or
                not decision.get('checks') or not all(decision['checks'].values())):
            raise ValueError('Pilot decision does not authorize this full pretraining protocol')
        pilot_decision_hash = file_sha256(args.pilot_decision)
    elif args.pilot_decision:
        raise ValueError('A pilot run cannot depend on its future adoption decision')
    if str(torch.__version__) != "2.11.0+cpu" or torchaudio.__version__ != "2.11.0+cpu":
        raise ValueError("Use the pinned torch/torchaudio CPU environment")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_id):
        raise ValueError("Unsafe run ID")
    rows = normalize_registry(json.loads(args.registry.read_text()))
    if any(r['resolved_dataset_group'] not in {'circor', 'sprsound'} for r in rows):
        raise ValueError('Only the qualified CirCor/SPRSound external populations are allowed')
    ages, _, used = hierarchy(rows)
    if args.phase == "pilot" and any(row["dataset_id"] not in config["datasets"] for row in rows):
        raise ValueError("Pilot contains an undeclared external dataset")
    training_subject_counts = {kind: len({(r["resolved_dataset_group"], r["resolved_subject_id"])
                                         for r in used if r["source_type"] == kind}) for kind in SOURCES}
    if min(training_subject_counts.values()) < config["minimum_training_subjects_each_source"]:
        raise ValueError("Fewer than the frozen minimum training subjects in compatible age domains")
    for row in rows:
        if file_sha256(external_path(row["derived_path"])) != row["derived_sha256"]:
            raise ValueError(f"Derived audio hash mismatch: {row['registry_key']}")
        data = np.load(row["derived_path"], mmap_mode="r", allow_pickle=False)
        if data.dtype != np.float32 or data.shape != (row["canonical_samples"],) or not np.isfinite(data).all():
            raise ValueError("Invalid canonical audio in the accepted registry")
    recipes = recipe_schedule(rows, 4 * updates, config["seed"])
    validation_recipes = recipe_schedule(rows, 32, 20260929, "external_validation")
    _, _, validation_used = hierarchy(rows, "external_validation")
    if {(r["resolved_dataset_group"], r["resolved_subject_id"]) for r in used} & {
            (r["resolved_dataset_group"], r["resolved_subject_id"]) for r in validation_used}:
        raise ValueError("External merged-subject train/validation overlap")
    artifact_root = (ROOT / config["artifact_root"]).resolve()
    if not artifact_root.is_relative_to((ROOT / ".local/training").resolve()):
        raise ValueError("Large artifacts must remain in ignored local training storage")
    directory = artifact_root / args.run_id
    if directory.exists() != args.resume or (args.resume and (directory / "failure.json").exists()):
        raise ValueError("New run ID required, or clean interruption resume without a recorded failure")
    provenance = {"git": git, "config_path": str(args.config.resolve()), "config_sha256": args.config_sha256,
                  "registry_path": str(args.registry.resolve()), "registry_sha256": args.registry_sha256,
                  "normalized_registry_sha256": content_hash(rows), "recipe_content_sha256": content_hash(recipes),
                  "external_validation_recipe_content_sha256": content_hash(validation_recipes),
                  "phase": args.phase, "optimizer_updates": updates, "seed": config["seed"],
                  "pilot_decision_sha256": pilot_decision_hash,
                  "python": platform.python_version(), "torch": str(torch.__version__), "torchaudio": torchaudio.__version__,
                  "numpy": np.__version__, "device": "cpu", "architecture_version": config["architecture_version"],
                  "parameter_count": 171313, "initialization": "fresh_seeded_library_default_no_checkpoint",
                  "optimizer": config["optimizer"], "loss": config["loss"], "test_access": False, "hls_audio_access": False}
    provenance_hash = content_hash(provenance)
    directory.mkdir(parents=True, exist_ok=args.resume)
    checkpoints = directory / "checkpoints"
    checkpoints.mkdir(exist_ok=True)
    if args.resume:
        manifest = json.loads((directory / "run_manifest.json").read_text())
        if manifest["provenance_sha256"] != provenance_hash or manifest["status"] == "COMPLETE_FIXED_ENDPOINT":
            raise ValueError("Cannot resume a different or completed experiment")
    else:
        atomic_json(config, directory / "config.json")
        atomic_json({"recordings": rows}, directory / "resolved_registry.json")
        atomic_jsonl(recipes, directory / "recipes.jsonl")
        atomic_jsonl(validation_recipes, directory / "external_validation_recipes.jsonl")
        used_keys = {r["registry_key"] for r in used}
        manifest = {"run_id": args.run_id, "created_utc": datetime.now(timezone.utc).isoformat(),
                    "status": "PREPARED", "training_stage": "external_pretraining", "provenance": provenance,
                    "provenance_sha256": provenance_hash, "shared_age_domains": ages,
                    "training_subject_counts": training_subject_counts,
                    "training_record_counts": dict(Counter(r["source_type"] for r in used)),
                    "unused_rows": [{"registry_key": r["registry_key"], "reason": "heldout_subject" if
                                     r["resolved_partition"] != "train" else "unknown_or_unshared_age_domain"}
                                    for r in rows if r["registry_key"] not in used_keys],
                    "initial_artifact_hashes": {p.name: file_sha256(p) for p in directory.iterdir() if p.is_file()}}
        atomic_json(manifest, directory / "run_manifest.json")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(config["seed"])
    np.random.seed(config["seed"])
    torch.manual_seed(config["seed"])
    if git_metadata() != git:
        raise RuntimeError("Source changed before external model initialization")
    model = StethoFuseConvTasNet(config["architecture_version"]).cpu()
    if model.parameter_count != 171313:
        raise ValueError("External pretraining model parameter count changed")
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, betas=(.9, .999), eps=1e-8, weight_decay=.0001)
    completed, prior_runtime, history = 0, 0.0, []
    if args.resume:
        hashes = json.loads((directory / "checkpoint_hashes.json").read_text())
        if file_sha256(checkpoints / "resume.pt") != hashes["resume.pt"]:
            raise ValueError("Resume checkpoint hash mismatch")
        state = torch.load(checkpoints / "resume.pt", map_location="cpu", weights_only=False)
        if state["provenance_sha256"] != provenance_hash:
            raise ValueError("Resume provenance mismatch")
        model.load_state_dict(state["state_dict"], strict=True)
        optimizer.load_state_dict(state["optimizer_state_dict"])
        completed, prior_runtime, history = state["optimizer_updates"], state["runtime_seconds"], state["history"]
        if not 0 <= completed <= updates or state["recipe_cursor"] != 4 * completed:
            raise ValueError("Invalid resume recipe cursor")
        torch.set_rng_state(state["torch_rng_state"])
        np.random.set_state(state["numpy_rng_state"])
        random.setstate(state["python_rng_state"])
    else:
        manifest.update({"status": "INITIALIZED", "fresh_seeded_state_sha256": state_sha256(model),
                         "optimizer_state_entries_at_start": len(optimizer.state)})
        atomic_json(manifest, directory / "run_manifest.json")
    cache = AudioCache(used + validation_used)
    model.train()
    sums, norms, receipts, interval_start = Counter(), [], [], completed
    maximum_seconds = 60 * config["resource_limits"]["pilot_wall_minutes" if args.phase == "pilot" else "full_pretraining_wall_minutes"]

    def persist(name: str) -> None:
        state = model_checkpoint(model, 0, {"training_stage": "external_pretraining",
                                           "provenance_sha256": provenance_hash, "phase": args.phase})
        state.pop("epoch")
        state.update({"optimizer_updates": completed, "recipe_cursor": completed * 4,
                      "optimizer_state_dict": optimizer.state_dict(), "scheduler": None,
                      "torch_rng_state": torch.get_rng_state(), "numpy_rng_state": np.random.get_state(),
                      "python_rng_state": random.getstate(), "history": history,
                      "runtime_seconds": prior_runtime + time.perf_counter() - start,
                      "provenance_sha256": provenance_hash})
        atomic_torch_save(state, checkpoints / name)
        if name != "resume.pt":
            atomic_torch_save(state, checkpoints / "resume.pt")
        atomic_json({p.name: file_sha256(p) for p in checkpoints.glob("*.pt")}, directory / "checkpoint_hashes.json")
        atomic_jsonl(history, directory / "history.jsonl")

    try:
        if not args.resume:
            persist("initial.pt")
        for update in range(completed + 1, updates + 1):
            batch = [materialize(recipe, cache) for recipe in recipes[(update - 1) * 4:update * 4]]
            x = torch.from_numpy(np.stack([sample[0] for sample in batch])[:, None])
            target = torch.from_numpy(np.stack([sample[1] for sample in batch]))
            optimizer.zero_grad(set_to_none=True)
            components = fixed_label_components(model(x), target)
            if any(not torch.isfinite(value) for value in components.values()):
                raise RuntimeError("Nonfinite external loss")
            components["loss"].backward()
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
                raise RuntimeError("Nonfinite external gradient")
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0, error_if_nonfinite=True)
            optimizer.step()
            if any(not torch.isfinite(p).all() for p in model.parameters()):
                raise RuntimeError("Nonfinite external model parameter")
            completed = update
            sums.update({key: float(value.detach()) for key, value in components.items()})
            norms.append(float(norm))
            receipts.extend(sample[2] for sample in batch)
            if update % 144 == 0:
                receipt_path = directory / f"realized-{interval_start + 1:05d}-{update:05d}.jsonl"
                atomic_jsonl(receipts, receipt_path)
                row = {"optimizer_updates": update, "interval_updates": update - interval_start,
                       **{key: value / (update - interval_start) for key, value in sums.items()},
                       "lr": optimizer.param_groups[0]["lr"], "gradient_norm_before_clip_max": max(norms),
                       "nonfinite_count": 0, "runtime_seconds": prior_runtime + time.perf_counter() - start,
                       "realized_recipes_sha256": file_sha256(receipt_path), **resource_snapshot()}
                history.append(row)
                print(json.dumps(row, sort_keys=True), flush=True)
                persist("resume.pt")
                sums, norms, receipts, interval_start = Counter(), [], [], update
            if (resource_snapshot()["process_peak_rss_mib"] > 1024 * config["resource_limits"]["pretraining_peak_rss_gib"] or
                    prior_runtime + time.perf_counter() - start > maximum_seconds):
                raise RuntimeError("Predeclared pretraining CPU time/memory limit exceeded")
        persist("endpoint.pt")
        summary, validation_rows = external_sanity(model, validation_recipes, cache)
        atomic_json(summary, directory / "external_validation_summary.json")
        atomic_jsonl(validation_rows, directory / "external_validation_results.jsonl")
        manifest.update({"status": "COMPLETE_FIXED_ENDPOINT", "optimizer_updates": completed,
                         "stopping_reason": "predeclared_fixed_update_budget", "failures": 0,
                         "runtime_seconds": prior_runtime + time.perf_counter() - start,
                         "endpoint_sha256": file_sha256(checkpoints / "endpoint.pt"),
                         "external_validation_summary": summary, **resource_snapshot()})
        atomic_json(manifest, directory / "run_manifest.json")
    except BaseException as error:
        atomic_json({"status": "STOPPED_REQUIRES_REVIEW", "error_type": type(error).__name__, "error": str(error),
                     "last_completed_optimizer_update": completed,
                     "runtime_seconds": prior_runtime + time.perf_counter() - start,
                     "test_access": False, "hls_audio_access": False}, directory / "failure.json")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--registry-sha256", required=True)
    parser.add_argument("--phase", choices=("pilot", "full"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pilot-decision", type=Path, help="Required accepted transfer receipt for full scale-up")
    parser.add_argument("--resume", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
