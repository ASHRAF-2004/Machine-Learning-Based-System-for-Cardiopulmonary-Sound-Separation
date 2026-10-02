"""Read-only pre-T9 history/exposure audit; no model or audio is loaded.

Only saved development recipes, validation results and an eligible non-test
split snapshot are read. Counts of remixes/crops are not independent samples.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / ".local/training/stethofuse-tcn-v1"
NAMES = ("baseline-seed20260928", "t7-small-seed20260928",
         "t7-confirm-small-seed20260929")
OUTPUT = ROOT / ".local/diagnosis/pre_t9_plateau/v1/history.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def describe(values) -> dict:
    a = np.asarray(list(values), dtype=float)
    return {"n": len(a), "mean": float(a.mean()), "min": float(a.min()),
            "q25": float(np.quantile(a, .25)), "median": float(np.median(a)),
            "q75": float(np.quantile(a, .75)), "max": float(a.max())}


def means(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in keys)].append(row)
    result = []
    for group, members in sorted(groups.items()):
        out = {**dict(zip(keys, group)), "conditions": len(members)}
        for source in ("heart", "lung"):
            vals = [r[f"{source}_si_sdri_db"] for r in members]
            out[source] = describe(vals)
            out[source]["negative_conditions"] = sum(v < 0 for v in vals)
        result.append(out)
    return result


def macro_levels(rows: list[dict]) -> list[dict]:
    groups = means(rows, ("relative_lung_to_heart_db", "heart_family", "lung_family"))
    result = []
    for level in sorted({r["relative_lung_to_heart_db"] for r in rows}):
        members = [g for g in groups if g["relative_lung_to_heart_db"] == level]
        result.append({"level_db": level, **{s: float(np.mean([g[s]["mean"] for g in members]))
                       for s in ("heart", "lung")}})
    return result


def main() -> None:
    split_path = RUNS / NAMES[1] / "eligible_split.csv"
    sources = list(csv.DictReader(split_path.open(newline="")))
    assert len(sources) == 86 and all(s["split"] in {"development", "validation"} for s in sources)
    source_map = {(s["kind"], s["id"]): s for s in sources}
    family_counts = Counter((s["kind"], s["split"], s["family"]) for s in sources)
    dev_counts = {kind: Counter(s["family"] for s in sources if s["kind"] == kind and
                               s["split"] == "development") for kind in ("HS", "LS")}
    runs, best_rows = {}, {}
    for name in NAMES:
        path = RUNS / name
        meta = json.loads((path / "run.json").read_text())
        history = jsonl(path / "history.jsonl")
        rows = jsonl(path / "validation/best_checkpoint_per_condition.jsonl")
        for row in rows:
            for kind, field in (("HS", "heart_id"), ("LS", "lung_id")):
                assert source_map[(kind, row[field])]["split"] == "validation"
        best_rows[name] = rows
        best = int(meta["best_epoch"])
        epochs = []
        previous_lr = float(meta["initial_learning_rate"])
        for row in history:
            # Baseline logging stored the LR after scheduler.step; T7 explicitly
            # records the LR actually used plus the next epoch's LR.
            if "next_learning_rate" in row:
                used, next_lr = row["learning_rate"], row["next_learning_rate"]
            else:
                used, next_lr = previous_lr, row["learning_rate"]
            previous_lr = next_lr
            epochs.append({"epoch": row["epoch"], "updates": row["epoch"] * 144,
                "loss": row["training_loss"], "negative_si_sdr": row["negative_si_sdr_component"],
                "normalized_l1": row["normalized_waveform_l1_component"],
                "weighted_l1": 5 * row["normalized_waveform_l1_component"],
                "heart_si_sdri": row["validation"]["heart_si_sdri_db"]["family_balanced_mean"],
                "lung_si_sdri": row["validation"]["lung_si_sdri_db"]["family_balanced_mean"],
                "q": row["selection_q_db"], "balanced": row["balanced_mean_db"],
                "lr_used": used, "lr_next": next_lr, "duration_seconds": row["duration_seconds"],
                "nonfinite_count": row["nonfinite_count"],
                "max_preclip_gradient_norm": row["max_preclip_gradient_norm"]})
        recipes = []
        recipe_hashes = {}
        for epoch in range(best):
            recipe_path = path / f"recipes/epoch-{epoch:03d}.jsonl"
            chunk = jsonl(recipe_path)
            assert len(chunk) == 576
            for row in chunk:
                for kind, field in (("HS", "heart_id"), ("LS", "lung_id")):
                    assert source_map[(kind, row[field])]["split"] == "development"
            recipes.extend(chunk)
            recipe_hashes[recipe_path.name] = sha(recipe_path)
        exposure = {}
        for kind, label in (("HS", "heart"), ("LS", "lung")):
            counts = Counter(r[f"{label}_id"] for r in recipes)
            starts = defaultdict(set)
            for r in recipes:
                starts[r[f"{label}_id"]].add(r[f"{label}_start"])
            exposure[label] = {"unique_files": len(counts), "source_reuse": describe(counts.values()),
                "distinct_crop_offsets_per_source": describe(map(len, starts.values())),
                "exact_source_crop_count": sum(map(len, starts.values())),
                "distinct_source_recorded_seconds": 15 * len(counts),
                "presented_source_crop_seconds": 8 * len(recipes),
                "family_draws": dict(sorted(Counter(r[f"{label}_family"] for r in recipes).items()))}
        pairs = Counter((r["heart_id"], r["lung_id"]) for r in recipes)
        expected_distinct_iid_within_family = sum(h * l * (1 - (1 - 1 / (h * l)) ** (24 * best))
            for h in dev_counts["HS"].values() for l in dev_counts["LS"].values())
        level_counts = Counter(int(np.digitize(r["relative_lung_to_heart_db"], [-6, -2, 2, 6])) for r in recipes)
        chosen, final = epochs[best - 1], epochs[-1]
        stopped_recipes = recipes.copy()
        for epoch in range(best, int(meta["epochs_completed"])):
            chunk = jsonl(path / f"recipes/epoch-{epoch:03d}.jsonl")
            assert len(chunk) == 576
            for row in chunk:
                for kind, field in (("HS", "heart_id"), ("LS", "lung_id")):
                    assert source_map[(kind, row[field])]["split"] == "development"
            stopped_recipes.extend(chunk)
        improvement = chosen["loss"] - final["loss"]
        si_improvement = chosen["negative_si_sdr"] - final["negative_si_sdr"]
        weighted_l1_improvement = chosen["weighted_l1"] - final["weighted_l1"]
        runs[name] = {"run_manifest_sha256": sha(path / "run.json"), "history_sha256": sha(path / "history.jsonl"),
            "best_epoch": best, "stop_epoch": meta["epochs_completed"], "best_updates": best * 144,
            "best_mixture_draws": len(recipes), "total_training_seconds": meta["total_training_seconds"],
            "epochs": epochs, "lr_transitions": [{"after_epoch": e["epoch"], "next_lr": e["lr_next"]}
                for e in epochs if e["lr_used"] != e["lr_next"]],
            "post_best": {"total_loss_improvement": improvement,
                "negative_si_sdr_improvement": si_improvement,
                "weighted_l1_improvement": weighted_l1_improvement,
                "si_sdr_fraction_of_value_improvement": si_improvement / improvement,
                "q_change_best_to_final_db": final["q"] - chosen["q"]},
            "exposure_at_best": exposure, "unique_file_pairs_at_best": len(pairs),
            "possible_file_pairs": 1296, "pair_draw_reuse": describe(pairs.values()),
            "exposure_at_stop": {"updates": int(meta["epochs_completed"]) * 144,
                "mixture_draws": len(stopped_recipes),
                "unique_file_pairs": len({(r["heart_id"], r["lung_id"]) for r in stopped_recipes}),
                "mean_uses_per_source": len(stopped_recipes) / 36},
            "iid_within_family_distinct_pair_expectation_not_actual_sampler": expected_distinct_iid_within_family,
            "training_relative_level_bins": {label: level_counts[i] for i, label in enumerate(
                ("[-10,-6)", "[-6,-2)", "[-2,2)", "[2,6)", "[6,10]"))},
            "training_extreme_absolute_level_ge_8_fraction": sum(abs(r["relative_lung_to_heart_db"]) >= 8
                for r in recipes) / len(recipes),
            "silent_crop_retries_total": sum(r.get("silent_crop_retries", 0) for r in recipes),
            "recipe_sha256_to_best": recipe_hashes,
            "family_pair": means(rows, ("heart_family", "lung_family")),
            "family_pair_level": means(rows, ("heart_family", "lung_family", "relative_lung_to_heart_db")),
            "family_macro_level": macro_levels(rows)}
    primary = {r["mixture_id"]: r for r in best_rows[NAMES[1]]}
    confirmation = {r["mixture_id"]: r for r in best_rows[NAMES[2]]}
    assert primary.keys() == confirmation.keys()
    deltas = [{**r, **{f"{s}_si_sdri_db": confirmation[k][f"{s}_si_sdri_db"] - r[f"{s}_si_sdri_db"]
                       for s in ("heart", "lung")}} for k, r in primary.items()]
    result = {"scope": "Existing non-test metadata/recipes/results only; no audio or model loaded, no training",
        "eligible_split_sha256": sha(split_path), "audio_opened": False, "test_access": "NONE",
        "family_inventory": [{"kind": k, "split": s, "family": f, "count": n}
            for (k, s, f), n in sorted(family_counts.items())], "runs": runs,
        "seed_confirmation_minus_primary": {"family_pair": means(deltas, ("heart_family", "lung_family")),
            "family_macro_level": macro_levels(deltas)},
        "crop_geometry": {"source_seconds": 15, "crop_seconds": 8, "start_range_seconds": [0, 7],
            "minimum_pairwise_same_file_crop_overlap_seconds": 1,
            "expected_overlap_uniform_independent_starts_seconds": 8 - 7 / 3,
            "expected_overlap_fraction": (8 - 7 / 3) / 8,
            "caution": "Exact distinct offsets do not create independent recordings; uniform continuous approximation"},
        "statistical_caution": "225 validation rows comprise 45 file pairs at five levels; two heart families share one lung family and the same five lung files. No IID confidence interval or effective sample size is estimated."}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "sha256": sha(OUTPUT),
                      "run_count": len(runs), "audio_opened": False}))


if __name__ == "__main__":
    main()
