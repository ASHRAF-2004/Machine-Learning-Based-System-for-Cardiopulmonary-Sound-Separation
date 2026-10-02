"""Qualified additive-release supervision, never source discovery or automatic purity approval.

Metadata authorization precedes every audio read. No I/O occurs on import.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import wave

import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_native_plan(plan: dict, base: dict, base_hash: str, updates: int) -> None:
    expected = {"schema_version": 1, "test_access_allowed": False, "production_changes_allowed": False,
                "role": "A_DIRECT_WAVEFORM_QUALIFIED_AFFINE_ADDITIVE_SUBSET_ONLY",
                "base_plan_sha256": base_hash, "architecture_version": base["architecture_version"],
                "parameter_count": 171313, "seed": 20260928, "device": "cpu", "threads": 2,
                "interop_threads": 1, "optimizer_updates": 576, "synthetic_batch_size": 4,
                "native_batch_size": 4, "sample_rate": 4000, "crop_samples": 32000,
                "native_loss_weight": .25, "initialization": "fresh_library_default_no_checkpoint_loading",
                "scheduler": None, "early_stopping": False, "optimizer": base["optimizer"],
                "source_eligible_manifest_sha256": base["eligible_manifest_sha256"],
                "native_rng": {"generator": "PCG64", "seed_sequence": [20260928, 7731, "draw_index"]},
                "lr_schedule": [{"from_update_inclusive": 1, "through_update_inclusive": 576, "lr": .001}],
                "synthetic_loss": base["loss"],
                "native_loss": "same_fixed_label_mean_negative_si_sdr_plus_5_rms_normalized_l1",
                "folds": ["f1", "f2", "f3", "f4", "f5"]}
    if updates != 576 or any(plan.get(k) != v for k, v in expected.items()):
        raise ValueError("Native plan differs from the single approved waveform intervention")
    if base["initialization"] != "fresh_library_default_no_checkpoint_loading":
        raise ValueError("Native treatment cannot use external initialization")
    for key in ("qualified_manifest_sha256", "registry_sha256", "fold_manifest_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(plan.get(key))):
            raise ValueError("Native metadata hashes must be frozen before execution")


def select_native_rows(qualified: dict, registry: dict, sources: list, base: dict, fold: str) -> list[dict]:
    """Metadata only. Check both family guards before returning any file for decoding."""
    selected = qualified["selected_ids"]
    if len(selected) != 26 or len(set(selected)) != 26 or "M0126" in selected:
        raise ValueError("Expected the 26 unique prequalified additive triplets")
    rows = {r["triplet_id"]: r for r in qualified["rows"] if r["triplet_id"] in selected}
    originals = {r["triplet_id"]: r for r in registry["rows"] if r["triplet_id"] in selected}
    if set(rows) != set(selected) or set(originals) != set(selected):
        raise ValueError("Selected native metadata incomplete")
    families = {kind: {s.family for s in sources if s.kind == kind and s.split in {"development", "validation"}}
                for kind in ("HS", "LS")}
    result = []
    for ident in sorted(selected):
        row, original = rows[ident], originals[ident]
        if (not re.fullmatch(r"M\d{4}", ident) or row.get("eligible_non_test") is not True or
                original.get("eligible_non_test") is not True or original.get("exclusion_reasons") or
                row.get("selected") is not True or row.get("quality_tier") != "N1" or row.get("reasons") or
                row["heart_family"] not in families["HS"] or row["lung_family"] not in families["LS"]):
            raise ValueError("Native row is excluded by qualification or the T9/family seal")
        for key in ("heart_family", "lung_family", "files", "eligible_training_folds"):
            if row[key] != original[key]:
                raise ValueError("Qualified native identity differs from the pinned registry")
        allowed = [f["id"] for f in base["folds"] if row["heart_family"] not in f["holdout_heart_families"]
                   and row["lung_family"] not in f["holdout_lung_families"]]
        if row["eligible_training_folds"] != allowed:
            raise ValueError("Native family fold assignment changed")
        if fold != "refit" and fold not in allowed:
            continue  # No file path resolution, hashing, or decoding for held-out native families.
        if (not np.isfinite(row["gain"]) or row["gain"] <= 0 or
                row.get("heart_lag_samples") != 0 or row.get("lung_lag_samples") != 0 or
                row.get("transfer_filter") != "identity" or
                len(row["full_flank_residual_weaker_source_rms_ratios"]) != 2 or
                not all(np.isfinite(v) and 0 <= v <= .10 for v in row["full_flank_residual_weaker_source_rms_ratios"])):
            raise ValueError("Native correspondence no longer meets the predeclared common-gain rule")
        result.append(row)
    if fold not in {"refit", *[f["id"] for f in base["folds"]]} or not result:
        raise ValueError("Unknown fold or empty qualified native training subset")
    return result


def load_native_selection(root: Path, plan: dict, sources: list, base: dict, fold: str) -> list[dict]:
    loaded = {}
    for key in ("qualified_manifest", "registry"):
        path = root / plan[key]
        if sha256(path) != plan[key + "_sha256"]:
            raise ValueError(f"Frozen {key} bytes changed")
        loaded[key] = json.loads(path.read_text())
    if loaded["qualified_manifest"]["registry_sha256"] != plan["registry_sha256"]:
        raise ValueError("Qualification/registry lineage mismatch")
    return select_native_rows(loaded["qualified_manifest"], loaded["registry"], sources, base, fold)


def load_native_audio(root: Path, rows: list[dict], fold: str) -> dict:
    """Accept only already fold-authorized records; immutable 4k mono PCM16 sources."""
    from scripts.audit_hls_native_registry import ROOT, authorized_native_path
    if root.resolve() != ROOT.resolve():
        raise ValueError("Native loader requires the independently authorized project root")
    cache = {}
    for row in rows:
        values = []
        for role, prefix in (("mixture", "M"), ("heart", "H"), ("lung", "L")):
            file = row["files"][role]
            # The guard independently re-derives identity/fold authorization from
            # frozen metadata; it never reads excluded audio.
            path = authorized_native_path(row, file["path"], None if fold == "refit" else fold)
            if sha256(path) != file["sha256"]:
                raise ValueError("Native original audio bytes changed")
            with wave.open(str(path), "rb") as wav:
                if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getnframes(),
                        wav.getcomptype()) != (4000, 1, 2, 60000, "NONE"):
                    raise ValueError("Native audio contract changed")
                audio = np.frombuffer(wav.readframes(60000), dtype="<i2").astype(np.float32) / 32768
            if audio.shape != (60000,) or not np.isfinite(audio).all():
                raise ValueError("Invalid native audio")
            values.append(audio)
        cache[row["triplet_id"]] = np.stack(values)
    return cache


def native_recipe_prefix(rows: list[dict], draws: int = 2304) -> list[dict]:
    tree = {}
    for row in sorted(rows, key=lambda r: r["triplet_id"]):
        tree.setdefault(row["heart_family"], {}).setdefault(row["lung_family"], []).append(row)
    recipes = []
    for draw in range(draws):
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([20260928, 7731, draw])))
        heart = sorted(tree)[int(rng.integers(len(tree)))]
        lung = sorted(tree[heart])[int(rng.integers(len(tree[heart])))]
        row = tree[heart][lung][int(rng.integers(len(tree[heart][lung]))) ]
        recipes.append({"draw_index": draw, "seed_key": [20260928, 7731, draw],
                        "triplet_id": row["triplet_id"], "heart_family": heart, "lung_family": lung,
                        "crop_start": int(rng.integers(0, 28001)), "crop_samples": 32000,
                        "gain": row["gain"],
                        "source_sha256": {role: f["sha256"] for role, f in row["files"].items()}})
    return recipes


def materialize_native(recipe: dict, cache: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    start = recipe["crop_start"]
    if not 0 <= start <= 28000 or recipe["crop_samples"] != 32000:
        raise ValueError("Invalid aligned native crop")
    crop = cache[recipe["triplet_id"]][:, start:start + 32000]
    if crop.shape != (3, 32000) or not np.isfinite(crop).all():
        raise ValueError("Invalid native crop audio")
    mixture = crop[0].copy()  # Never replace the recorded mixture with the target sum.
    target = crop[1:] * np.float32(recipe["gain"])
    scale = float(np.max(np.abs(mixture)))
    if scale <= 1e-6 or np.min(np.sqrt(np.mean(target.astype(np.float64) ** 2, axis=1))) < 1e-6:
        raise ValueError("Silent native mixture/target; stop rather than silently resample")
    x, y = np.asarray(mixture / scale, dtype=np.float32), np.asarray(target / scale, dtype=np.float32)
    receipt = {**recipe, "network_shared_peak_scale": scale,
               "network_normalization": "divide original mixture and common-gain targets by cropped mixture peak",
               "mixture_sha256": hashlib.sha256(x.tobytes()).hexdigest(),
               "target_sha256": hashlib.sha256(y.tobytes()).hexdigest()}
    return x, y, receipt
