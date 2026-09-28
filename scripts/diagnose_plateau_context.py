"""Descriptive non-test context probe; no new window rule or training.

Source-level ratios use all 225 existing validation conditions. Inference uses
only the lexicographically first source pair in each existing validation family
pair, at all five already-frozen levels. Regions are declared before inference.
"""
from __future__ import annotations

import csv
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torchaudio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_data import DATA_ROOT, Source, read_source, sha256_file, write_json
from scripts.evaluate_ensemble_qualification import si_sdr
from scripts.train_stethofuse_baseline import get_mix_target

RUN = ROOT / ".local/training/stethofuse-tcn-v1/t7-small-seed20260928"
OUTPUT_ROOT = ROOT / ".local/diagnosis/pre_t9_plateau/v1"
CHECKPOINT_HASH = "89f8d66134c0a49aa2a05971720cdffbdd1e501ebce99bb83119e6683d58ac93"
RECIPE_HASH = "b4cef517cd4a64c267d3645ea6b918b5dfb72945f7536c0245b73228f00fdc90"
LOCAL_REGIONS = {
    "crop_8s_at_0s": (0, 32000),
    "crop_8s_at_3.5s": (14000, 46000),
    "crop_8s_at_7s": (28000, 60000),
    "inference_first_10s": (0, 40000),
    "inference_second_valid_7s": (32000, 60000),
}
OUTPUT_REGIONS = {
    "early_0_to_8s": (0, 32000),
    "overlap_8_to_10s": (32000, 40000),
    "tail_10_to_15s": (40000, 60000),
    "full_0_to_15s": (0, 60000),
}


def rms(values):
    return float(np.sqrt(np.mean(np.asarray(values, dtype=np.float64) ** 2)))


def describe(values):
    a = np.asarray(values, dtype=np.float64)
    return {"n": len(a), "mean": float(a.mean()), "median": float(np.median(a)),
            "min": float(a.min()), "max": float(a.max()),
            "q25": float(np.quantile(a, .25)), "q75": float(np.quantile(a, .75))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-regions", action="store_true",
                        help="Replay all225 unchanged validation conditions by fixed region")
    args = parser.parse_args()
    output = OUTPUT_ROOT / ("context_all.json" if args.all_regions else "context.json")
    if output.exists():
        raise RuntimeError("Refuse to overwrite context evidence")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    assert torch.__version__ == torchaudio.__version__ == "2.11.0+cpu"
    checkpoint = RUN / "checkpoints/best.pt"
    recipe_path = RUN / "validation/frozen_recipes.json"
    eligible = RUN / "eligible_split.csv"
    assert sha256_file(checkpoint) == CHECKPOINT_HASH
    assert sha256_file(recipe_path) == RECIPE_HASH
    metadata = list(csv.DictReader(eligible.open(newline="")))
    assert len(metadata) == 86
    assert all(r["split"] in {"development", "validation"} for r in metadata)
    sources = {(r["kind"], r["id"]): Source(r["kind"], r["id"], r["family"], r["split"],
                r["sha256"], DATA_ROOT / r["kind"] / f"{r['id']}.wav")
               for r in metadata if r["split"] == "validation"}
    assert len(sources) == 14
    for source in sources.values():
        assert source.split == "validation" and sha256_file(source.path) == source.sha256
    cache = {key: read_source(source) for key, source in sources.items()}
    recipes = json.loads(recipe_path.read_text())["recipes"]
    assert len(recipes) == 225
    first_pairs = {}
    for recipe in sorted(recipes, key=lambda r: (r["heart_family"], r["lung_family"],
                                                r["heart_id"], r["lung_id"])):
        first_pairs.setdefault((recipe["heart_family"], recipe["lung_family"]),
                               (recipe["heart_id"], recipe["lung_id"]))
    assert len(first_pairs) == 2
    first_selected = [r for r in recipes if (r["heart_id"], r["lung_id"]) ==
                first_pairs[(r["heart_family"], r["lung_family"])]]
    assert len(first_selected) == 10
    selected = recipes if args.all_regions else first_selected
    # Selection depends only on metadata, never scores or waveform features.
    print(json.dumps({"predeclared_pairs": "all_frozen_validation_pairs" if args.all_regions else list(first_pairs.values()),
                      "condition_count": len(selected)}), flush=True)
    model = StethoFuseConvTasNet("stethofuse-convtasnet-4k-small-v1").eval()
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    assert state["epoch"] == 8 and state["parameter_count"] == 171313
    model.load_state_dict(state["state_dict"], strict=True)
    before = {key: value.clone() for key, value in model.state_dict().items()}
    local_rows, metric_rows = [], []
    selected_ids = {r["mixture_id"] for r in selected}
    started = time.perf_counter()
    with torch.inference_mode():
        for recipe in recipes:
            assert ("HS", recipe["heart_id"]) in sources and ("LS", recipe["lung_id"]) in sources
            x, target = get_mix_target(recipe, cache)
            base = {key: recipe[key] for key in ("mixture_id", "heart_id", "lung_id",
                    "heart_family", "lung_family", "relative_lung_to_heart_db")}
            for region, (start, end) in LOCAL_REGIONS.items():
                local_db = 20 * np.log10(rms(target[1, start:end]) / rms(target[0, start:end]))
                local_rows.append({**base, "region": region, "local_lung_heart_db": float(local_db),
                                   "local_minus_nominal_db": float(local_db - recipe["relative_lung_to_heart_db"])})
            if recipe["mixture_id"] not in selected_ids:
                continue
            estimate = model.separate_recording(torch.from_numpy(x)).numpy()
            assert estimate.shape == target.shape and np.isfinite(estimate).all()
            for region, (start, end) in OUTPUT_REGIONS.items():
                row = {**base, "region": region}
                for index, label in enumerate(("heart", "lung")):
                    score = si_sdr(estimate[index, start:end], target[index, start:end])
                    baseline = si_sdr(x[start:end], target[index, start:end])
                    row[f"{label}_si_sdr_db"] = score
                    row[f"{label}_si_sdri_db"] = score - baseline
                metric_rows.append(row)
    assert all(torch.equal(value, before[key]) for key, value in model.state_dict().items())
    saved = {r["mixture_id"]: r for r in map(json.loads,
             (RUN / "validation/best_checkpoint_per_condition.jsonl").read_text().splitlines())}
    fields = ("heart_si_sdr_db", "heart_si_sdri_db", "lung_si_sdr_db", "lung_si_sdri_db")
    replay_error = max(abs(row[field] - saved[row["mixture_id"]][field])
                       for row in metric_rows if row["region"] == "full_0_to_15s" for field in fields)
    assert replay_error < 1e-6
    local_summary = {}
    for region in LOCAL_REGIONS:
        rows = [r for r in local_rows if r["region"] == region]
        local_summary[region] = {
            "local_minus_nominal_db": describe([r["local_minus_nominal_db"] for r in rows]),
            "outside_minus10_plus10_count": sum(abs(r["local_lung_heart_db"]) > 10 + 1e-6 for r in rows),
            "by_nominal_level": {str(level): describe([r["local_lung_heart_db"] for r in rows
                                if r["relative_lung_to_heart_db"] == level]) for level in (-10, -5, 0, 5, 10)},
        }
    metric_summary = {}
    for group in ("ALL", *sorted({r["heart_family"] for r in selected})):
        metric_summary[group] = {}
        for region in OUTPUT_REGIONS:
            rows = [r for r in metric_rows if r["region"] == region and
                    (group == "ALL" or r["heart_family"] == group)]
            metric_summary[group][region] = {
                field: describe([r[field] for r in rows]) for field in fields}
    macro_summary = {}
    for region in OUTPUT_REGIONS:
        groups = sorted({(r["heart_family"], r["lung_family"]) for r in metric_rows})
        macro_summary[region] = {field: float(np.mean([
            np.mean([r[field] for r in metric_rows if r["region"] == region and
                     (r["heart_family"], r["lung_family"]) == group])
            for group in groups])) for field in fields}
    by_lung = {}
    for lung_id in sorted({r["lung_id"] for r in metric_rows}):
        by_lung[lung_id] = {}
        for region in OUTPUT_REGIONS:
            groups = sorted({r["heart_family"] for r in metric_rows if r["lung_id"] == lung_id})
            by_lung[lung_id][region] = {field: float(np.mean([
                np.mean([r[field] for r in metric_rows if r["region"] == region and
                         r["lung_id"] == lung_id and r["heart_family"] == group])
                for group in groups])) for field in fields}
    payload = {"classification": "DESCRIPTIVE CONTEXT DIAGNOSIS; NOT AN INTERVENTION",
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": sha256_file(Path(__file__)), "checkpoint_sha256": CHECKPOINT_HASH,
        "validation_recipe_sha256": RECIPE_HASH, "eligible_manifest_sha256": sha256_file(eligible),
        "optimizer_updates": 0, "test_sources_accessed": False,
        "inference_rule_unchanged": True, "model_state_unchanged": True,
        "max_saved_full_replay_difference_db": replay_error,
        "selection_policy": "all_frozen_validation_conditions" if args.all_regions else "metadata_first_pair_per_family",
        "local_level_condition_count": 225, "inference_condition_count": len(selected),
        "predeclared_pairs": [{"heart_family": family[0], "lung_family": family[1],
                                "heart_id": pair[0], "lung_id": pair[1]}
                               for family, pair in first_pairs.items()],
        "local_regions": LOCAL_REGIONS, "output_regions": OUTPUT_REGIONS,
        "local_summary": local_summary, "metric_summary": metric_summary,
        "family_pair_macro_by_region": macro_summary, "family_macro_by_lung_and_region": by_lung,
        "local_rows": local_rows, "metric_rows": metric_rows,
        "runtime_seconds": time.perf_counter() - started,
        "limitations": ["225 correlated conditions, only two heart families and one shared lung family." if args.all_regions else
                         "Only two metadata-selected pairs receive inference; not representative precision.",
                         "Regions differ in source content and duration, so score differences do not isolate padding causality.",
                         "Local 8s crops use aligned offsets; no alternate recipes or inference policy is scored."]}
    write_json(output, payload)
    print(json.dumps({"output": str(output.relative_to(ROOT)), "runtime_seconds": payload["runtime_seconds"],
                      "max_saved_full_replay_difference_db": replay_error,
                      "family_pair_macro_by_region": macro_summary,
                      "family_macro_by_lung_and_region": by_lung}, indent=2))


if __name__ == "__main__":
    main()
