"""Pure, frozen aggregation/adoption rules for the pre-T9 comparison."""
from __future__ import annotations

from collections import defaultdict
import math
import numpy as np


def aggregate(rows: list[dict]) -> dict:
    if len(rows) != 1775 or any(not math.isfinite(float(row[k])) for row in rows for k in
                               ("heart_si_sdr_db", "heart_si_sdri_db", "lung_si_sdr_db", "lung_si_sdri_db")):
        raise ValueError("Expected 1,775 finite held-out condition rows")
    pairs: dict[tuple[str, str], list[dict]] = defaultdict(list)
    folds: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        pairs[(row["heart_family"], row["lung_family"])].append(row)
        folds[row["fold"]].append(row)
    if len(pairs) != 8 or set(folds) != {"f1", "f2", "f3", "f4", "f5"}:
        raise ValueError("Frozen family-pair/fold structure changed")

    def mean(values):
        return float(np.mean(np.asarray(values, dtype=np.float64)))

    pair_table = {}
    for (heart, lung), group in sorted(pairs.items()):
        h, l = mean([r["heart_si_sdri_db"] for r in group]), mean([r["lung_si_sdri_db"] for r in group])
        pair_table[f"{heart} × {lung}"] = {"heart_si_sdr_db": mean([r["heart_si_sdr_db"] for r in group]),
            "heart_si_sdri_db": h, "lung_si_sdr_db": mean([r["lung_si_sdr_db"] for r in group]),
            "lung_si_sdri_db": l, "balanced_mean_db": (h + l) / 2,
            "conditions": len(group)}
    heart_macro = mean([v["heart_si_sdri_db"] for v in pair_table.values()])
    lung_macro = mean([v["lung_si_sdri_db"] for v in pair_table.values()])
    fold_table = {}
    for fold, group in sorted(folds.items()):
        fold_pairs: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in group:
            fold_pairs[(row["heart_family"], row["lung_family"])].append(row)
        h = mean([mean([r["heart_si_sdri_db"] for r in pair_rows])
                  for pair_rows in fold_pairs.values()])
        l = mean([mean([r["lung_si_sdri_db"] for r in pair_rows])
                  for pair_rows in fold_pairs.values()])
        fold_table[fold] = {"heart_si_sdri_db": h, "lung_si_sdri_db": l, "Q_db": min(h, l),
                            "balanced_mean_db": (h + l) / 2, "conditions": len(group),
                            "family_pair_groups": len(fold_pairs)}
    return {"heart_macro_si_sdr_db": mean([v["heart_si_sdr_db"] for v in pair_table.values()]),
            "heart_macro_si_sdri_db": heart_macro,
            "lung_macro_si_sdr_db": mean([v["lung_si_sdr_db"] for v in pair_table.values()]),
            "lung_macro_si_sdri_db": lung_macro,
            "Q_db": min(heart_macro, lung_macro), "balanced_mean_db": (heart_macro + lung_macro) / 2,
            "pair_table": pair_table, "fold_table": fold_table,
            "negative_condition_rate_heart": mean([r["heart_si_sdri_db"] < 0 for r in rows]),
            "negative_condition_rate_lung": mean([r["lung_si_sdri_db"] < 0 for r in rows]),
            "conditions": len(rows), "family_pair_groups": len(pair_table), "failures": 0}


def adoption_gate(candidate: dict, control: dict) -> dict:
    pair_deltas = {key: candidate["pair_table"][key]["balanced_mean_db"] - value["balanced_mean_db"]
                   for key, value in control["pair_table"].items()}
    source_pair_deltas = {key: {source: candidate["pair_table"][key][f"{source}_si_sdri_db"] -
                                         value[f"{source}_si_sdri_db"]
                                for source in ("heart", "lung")}
                          for key, value in control["pair_table"].items()}
    fold_deltas = {fold: candidate["fold_table"][fold]["Q_db"] - value["Q_db"]
                   for fold, value in control["fold_table"].items()}
    clauses = {
        "delta_Q_at_least_0_50": candidate["Q_db"] - control["Q_db"] >= .50,
        "delta_balanced_at_least_0_50": candidate["balanced_mean_db"] - control["balanced_mean_db"] >= .50,
        "heart_gain_at_least_0_25": candidate["heart_macro_si_sdri_db"] - control["heart_macro_si_sdri_db"] >= .25,
        "lung_gain_at_least_0_25": candidate["lung_macro_si_sdri_db"] - control["lung_macro_si_sdri_db"] >= .25,
        "balanced_pair_improves_at_least_6_of_8": sum(v > 0 for v in pair_deltas.values()) >= 6,
        "fold_Q_improves_at_least_4_of_5": sum(v > 0 for v in fold_deltas.values()) >= 4,
        "worst_pair_source_regression_not_below_minus_0_50": min(
            d for p in source_pair_deltas.values() for d in p.values()) >= -.50,
        "heart_negative_rate_increase_at_most_5pp": candidate["negative_condition_rate_heart"] -
            control["negative_condition_rate_heart"] <= .05,
        "lung_negative_rate_increase_at_most_5pp": candidate["negative_condition_rate_lung"] -
            control["negative_condition_rate_lung"] <= .05,
        "zero_failures_and_all_conditions": candidate["failures"] == 0 and candidate["conditions"] == 1775,
        "heart_absolute_macro_at_least_1": candidate["heart_macro_si_sdri_db"] >= 1.0,
        "lung_absolute_macro_at_least_1": candidate["lung_macro_si_sdri_db"] >= 1.0,
        "every_pair_source_nonnegative": all(v[f"{s}_si_sdri_db"] >= 0
                                             for v in candidate["pair_table"].values()
                                             for s in ("heart", "lung"))}
    return {"pass": all(clauses.values()), "clauses": clauses,
            "delta_Q_db": candidate["Q_db"] - control["Q_db"],
            "delta_balanced_mean_db": candidate["balanced_mean_db"] - control["balanced_mean_db"],
            "delta_heart_macro_si_sdri_db": candidate["heart_macro_si_sdri_db"] - control["heart_macro_si_sdri_db"],
            "delta_lung_macro_si_sdri_db": candidate["lung_macro_si_sdri_db"] - control["lung_macro_si_sdri_db"],
            "pair_balanced_deltas_db": pair_deltas, "fold_Q_deltas_db": fold_deltas,
            "source_pair_deltas_db": source_pair_deltas,
            "worst_pair_source_delta_db": min(d for p in source_pair_deltas.values() for d in p.values()),
            "heart_negative_rate_delta_pp": 100 * (candidate["negative_condition_rate_heart"] - control["negative_condition_rate_heart"]),
            "lung_negative_rate_delta_pp": 100 * (candidate["negative_condition_rate_lung"] - control["negative_condition_rate_lung"])}


def select_winner(passes: dict[str, bool], aggregates: dict[str, dict],
                  gates: dict[str, dict]) -> str:
    eligible = [name for name, passed in passes.items() if passed]
    if not eligible:
        return "CONTROL"
    if len(eligible) == 1:
        return eligible[0]
    a, b = aggregates["A"], aggregates["B"]
    for key in ("Q_db", "balanced_mean_db"):
        delta = a[key] - b[key]
        if abs(delta) > 1e-6:
            return "A" if delta > 0 else "B"
    def consistency(name):
        metric = gates[name]
        return (sum(v > 0 for v in metric["pair_balanced_deltas_db"].values()),
                sum(v > 0 for v in metric["fold_Q_deltas_db"].values()))
    con_a = consistency("A")
    con_b = consistency("B")
    if con_a != con_b:
        return "A" if con_a > con_b else "B"
    return "B"
