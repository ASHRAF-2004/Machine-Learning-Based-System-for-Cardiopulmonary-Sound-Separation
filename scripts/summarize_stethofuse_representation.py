"""Verify complete A/B endpoints, apply the frozen gate and write the decision."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.representation_selection import aggregate, adoption_gate, select_winner
from scripts.train_stethofuse_representation import (ARTIFACT_ROOT, PLAN, atomic_json,
                                                      file_sha256)

FOLDS = ("f1", "f2", "f3", "f4", "f5")
CONTROL_ROOT = ROOT / ".local/training/stethofuse-tcn-v1/pre-t9-family-refit-v1"
OUTPUT = ROOT / "research/evidence/final_model_comparison_decision_v1.json"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("Decision evidence already exists; refusing overwrite")
    plan = json.loads(PLAN.read_text())
    control_rows = []
    per_fold_control = {}
    for fold in FOLDS:
        path = CONTROL_ROOT / f"cv-{fold}-seed20260928" / "validation-0576.jsonl"
        rows = read_jsonl(path)
        per_fold_control[fold] = rows
        control_rows.extend({**row, "fold": fold} for row in rows)
    control = aggregate(control_rows)
    if (abs(control["heart_macro_si_sdri_db"] - 2.012519064941707) > 1e-6 or
            abs(control["lung_macro_si_sdri_db"] - 1.9134161560248084) > 1e-6 or
            abs(control["Q_db"] - 1.9134161560248084) > 1e-6 or
            abs(control["balanced_mean_db"] - 1.9629676104832576) > 1e-6):
        raise RuntimeError("Recomputed saved control differs from authoritative frozen metrics")

    candidate_aggregates, candidate_results, gates, passes = {}, {}, {}, {}
    capacity = None
    gate_path = ARTIFACT_ROOT / "tf-capacity-seed20260928" / "gate.json"
    if gate_path.is_file():
        capacity = json.loads(gate_path.read_text())
        passes["A"] = capacity.get("status") == "PASS"
    else:
        passes["A"] = False
    if passes["A"]:
        a_rows = []
        for fold in FOLDS:
            run_id = f"a-tfcomplex-{fold}-seed20260928"
            run_dir = ARTIFACT_ROOT / run_id
            result = json.loads((run_dir / "result.json").read_text())
            endpoint = run_dir / "endpoint.pt"
            if result.get("status") != "COMPLETE_FIXED_ENDPOINT" or file_sha256(endpoint) != result.get("endpoint_sha256"):
                raise RuntimeError(f"Treatment A endpoint integrity failure in {fold}")
            rows = read_jsonl(run_dir / "validation-0576.jsonl")
            expected = per_fold_control[fold]
            if len(rows) != len(expected) or [r["mixture_id"] for r in rows] != [r["mixture_id"] for r in expected]:
                raise RuntimeError(f"Treatment A changed validation conditions in {fold}")
            for row, control_row in zip(rows, expected):
                for key in ("heart_id", "lung_id", "heart_family", "lung_family", "relative_lung_to_heart_db"):
                    if row[key] != control_row[key]:
                        raise RuntimeError(f"Treatment A validation recipe mismatch ({fold}, {key})")
            a_rows.extend({**row, "fold": fold} for row in rows)
        candidate_aggregates["A"] = aggregate(a_rows)
        candidate_results["A"] = {"capacity_gate": capacity,
                                   "runs": [json.loads((ARTIFACT_ROOT / f"a-tfcomplex-{fold}-seed20260928" / "result.json").read_text()) for fold in FOLDS]}
        gates["A"] = adoption_gate(candidate_aggregates["A"], control)
        passes["A"] = gates["A"]["pass"]

    b_rows = []
    for fold in FOLDS:
        run_id = f"b-tcn-spectral-{fold}-seed20260928"
        run_dir = ARTIFACT_ROOT / run_id
        result = json.loads((run_dir / "result.json").read_text())
        endpoint = run_dir / "endpoint.pt"
        if result.get("status") != "COMPLETE_FIXED_ENDPOINT" or file_sha256(endpoint) != result.get("endpoint_sha256"):
            raise RuntimeError(f"Treatment B endpoint integrity failure in {fold}")
        rows = read_jsonl(run_dir / "validation-0576.jsonl")
        expected = per_fold_control[fold]
        if len(rows) != len(expected) or [r["mixture_id"] for r in rows] != [r["mixture_id"] for r in expected]:
            raise RuntimeError(f"Treatment B changed validation conditions in {fold}")
        for row, control_row in zip(rows, expected):
            for key in ("heart_id", "lung_id", "heart_family", "lung_family", "relative_lung_to_heart_db"):
                if row[key] != control_row[key]:
                    raise RuntimeError(f"Treatment B validation recipe mismatch ({fold}, {key})")
        b_rows.extend({**row, "fold": fold} for row in rows)
    candidate_aggregates["B"] = aggregate(b_rows)
    candidate_results["B"] = {"runs": [json.loads((ARTIFACT_ROOT / f"b-tcn-spectral-{fold}-seed20260928" / "result.json").read_text()) for fold in FOLDS]}
    gates["B"] = adoption_gate(candidate_aggregates["B"], control)
    passes["B"] = gates["B"]["pass"]

    winner = select_winner(passes, candidate_aggregates, gates)
    code_commits = set()
    for treatment_name in ("A", "B"):
        if treatment_name == "A" and not passes["A"]:
            continue
        for fold in FOLDS:
            run_dir = ARTIFACT_ROOT / (("a-tfcomplex" if treatment_name == "A" else "b-tcn-spectral") +
                                       f"-{fold}-seed20260928")
            provenance = json.loads((run_dir / "provenance.json").read_text())
            code_commits.add(provenance["starting_git"]["commit"])
    if len(code_commits) != 1:
        raise RuntimeError("Treatment folds do not share one clean implementation commit")
    evidence = {"schema_version": 1, "status": "FROZEN_PRE_T9_DECISION",
                "plan_sha256": file_sha256(PLAN),
                "implementation_sha": next(iter(code_commits)),
                "control": {"decision_receipt_sha256": file_sha256(ROOT / plan["control"]["receipt"]),
                            "aggregate": control,
                            "fold_validation_sha256": {f: file_sha256(CONTROL_ROOT / f"cv-{f}-seed20260928" / "validation-0576.jsonl") for f in FOLDS}},
                "treatments": {name: {"aggregate": candidate_aggregates.get(name),
                                      "gate": gates.get(name), "result": candidate_results.get(name),
                                      "pass": passes[name]} for name in ("A", "B")},
                "winner": winner, "test_access": False, "production_touched": False,
                "frontend_touched": False,
                "interpretation": "Grouped non-test evidence only; no T9 generalization claim.",
                "final_refit_authorized": winner in {"A", "B"}}
    atomic_json(OUTPUT, evidence)
    print(json.dumps({"winner": winner, "control": control,
                      "treatment_aggregates": candidate_aggregates,
                      "gates": gates, "evidence": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
