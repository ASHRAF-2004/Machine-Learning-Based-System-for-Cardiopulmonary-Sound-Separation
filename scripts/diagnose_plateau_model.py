"""Bounded pre-T9 inference/gradient diagnosis. No optimizer or test sources.

Uses only the selected checkpoint, frozen validation recipes and the prior
86-source eligible manifest. Gradients use the predeclared two T4 development
pairs at -10/0/+10 dB, first 8 seconds. No model or inference rule is changed.
"""
from __future__ import annotations

import csv
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
from app.ml.training_data import DATA_ROOT, Source, read_source, sha256_file, make_mixture, write_json
from app.ml.training_objective import fixed_label_si_sdr_db, normalized_l1
from scripts.diagnose_final_ensemble import FIELDS, summarize, grouped, pearson
from scripts.evaluate_ensemble_qualification import si_sdr
from scripts.train_stethofuse_baseline import get_mix_target

RUN = ROOT / ".local/training/stethofuse-tcn-v1/t7-small-seed20260928"
OUT = ROOT / ".local/diagnosis/pre_t9_plateau/v1"
HASH = "89f8d66134c0a49aa2a05971720cdffbdd1e501ebce99bb83119e6683d58ac93"
RECIPE_HASH = "b4cef517cd4a64c267d3645ea6b918b5dfb72945f7536c0245b73228f00fdc90"
DEV_PAIRS = (("F_AF_A", "F_N_LLA"), ("F_ESM_LLSB", "F_PR_LLA"))


class BeforeConsistency(torch.nn.Module):
    inference_window_samples = StethoFuseConvTasNet.inference_window_samples
    inference_hop_samples = StethoFuseConvTasNet.inference_hop_samples
    overlap_samples = StethoFuseConvTasNet.overlap_samples
    separate_recording = StethoFuseConvTasNet.separate_recording

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, mixture):
        length = mixture.shape[-1]
        pad = (-length) % self.model.stride
        padded = torch.nn.functional.pad(mixture, (0, pad)) if pad else mixture
        return self.model.separator(padded)[..., :length]


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=np.float64) ** 2)))


def vector_grad(value, params):
    gradients = torch.autograd.grad(value, params, retain_graph=True, allow_unused=True)
    return torch.cat([(torch.zeros_like(p) if g is None else g).detach().reshape(-1)
                      for p, g in zip(params, gradients)]).double()


def comparison(a, b):
    na, nb = float(a.norm()), float(b.norm())
    return {"norm_a": na, "norm_b": nb, "b_over_a": nb / max(na, 1e-30),
            "cosine": float(torch.dot(a, b)) / max(na * nb, 1e-30)}


def gradient_probe(model, sources):
    params = tuple(model.parameters())
    results = []
    for level in (-10, 0, 10):
        inputs, targets = [], []
        for hid, lid in DEV_PAIRS:
            hs, ls = sources[("HS", hid)], sources[("LS", lid)]
            assert hs.split == ls.split == "development"
            x, y, _ = make_mixture(read_source(hs), read_source(ls), level)
            scale = np.max(np.abs(x))
            inputs.append(x / scale)
            targets.append(y / scale)
        x = torch.from_numpy(np.stack(inputs)[:, None])
        y = torch.from_numpy(np.stack(targets))
        estimate = model(x)
        si = -fixed_label_si_sdr_db(estimate, y)
        l1 = 5 * normalized_l1(estimate, y)
        a, b = vector_grad(si.mean(), params), vector_grad(l1.mean(), params)
        h = vector_grad((si[:, 0] + l1[:, 0]).mean(), params)
        l = vector_grad((si[:, 1] + l1[:, 1]).mean(), params)
        cases = []
        for index, pair in enumerate(DEV_PAIRS):
            ah = vector_grad(si[index, 0] + l1[index, 0], params)
            al = vector_grad(si[index, 1] + l1[index, 1], params)
            cases.append({"ids": pair, "heart_vs_lung": comparison(ah, al),
                          "negative_si_sdr": si[index].detach().tolist(),
                          "weighted_l1": l1[index].detach().tolist()})
        assert all(torch.isfinite(v).all() for v in (a, b, h, l))
        results.append({"relative_db": level, "negative_si_sdr": float(si.mean().detach()),
                        "weighted_l1": float(l1.mean().detach()),
                        "si_vs_weighted_l1": comparison(a, b),
                        "heart_vs_lung": comparison(h, l), "cases": cases})
    return results


def main():
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    assert torch.__version__ == torchaudio.__version__ == "2.11.0+cpu"
    if (OUT / "model_summary.json").exists():
        raise RuntimeError("Refuse to overwrite diagnosis evidence")
    checkpoint = RUN / "checkpoints/best.pt"
    recipes_path = RUN / "validation/frozen_recipes.json"
    assert sha256_file(checkpoint) == HASH and sha256_file(recipes_path) == RECIPE_HASH
    metadata = list(csv.DictReader((RUN / "eligible_split.csv").open(newline="")))
    assert len(metadata) == 86 and all(r["split"] in ("development", "validation") for r in metadata)
    sources = {(r["kind"], r["id"]): Source(r["kind"], r["id"], r["family"], r["split"],
                r["sha256"], DATA_ROOT / r["kind"] / f"{r['id']}.wav") for r in metadata}
    allowed = [s for s in sources.values() if s.split == "validation" or
               any((s.kind, s.id) in (("HS", h), ("LS", l)) for h, l in DEV_PAIRS)]
    assert len(allowed) == 18
    for s in allowed:
        assert sha256_file(s.path) == s.sha256
    cache = {(s.kind, s.id): read_source(s) for s in allowed if s.split == "validation"}
    recipes = json.loads(recipes_path.read_text())["recipes"]
    assert len(recipes) == 225
    saved = {r["mixture_id"]: r for r in map(json.loads,
             (RUN / "validation/best_checkpoint_per_condition.jsonl").read_text().splitlines())}
    model = StethoFuseConvTasNet("stethofuse-convtasnet-4k-small-v1").eval()
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    assert state["epoch"] == 8 and state["parameter_count"] == 171313
    model.load_state_dict(state["state_dict"], strict=True)
    initial = {k: v.clone() for k, v in model.state_dict().items()}
    before = BeforeConsistency(model).eval()
    rows = {"before_consistency": [], "after_consistency": []}
    residuals = []
    max_replay = max_equiv = max_db_error = 0.0
    tic = time.perf_counter()
    with torch.inference_mode():
        for recipe in recipes:
            assert sources[("HS", recipe["heart_id"])].split == "validation"
            assert sources[("LS", recipe["lung_id"])].split == "validation"
            x, target = get_mix_target(recipe, cache)
            actual_db = 20 * np.log10(rms(target[1]) / rms(target[0]))
            max_db_error = max(max_db_error, abs(actual_db - recipe["relative_lung_to_heart_db"]))
            info = {k: recipe[k] for k in ("mixture_id", "heart_id", "lung_id", "heart_family",
                                           "lung_family", "relative_lung_to_heart_db")}
            raw = before.separate_recording(torch.from_numpy(x)).numpy()
            after = model.separate_recording(torch.from_numpy(x)).numpy()
            assert raw.shape == after.shape == target.shape and np.isfinite(raw).all()
            residual = x - raw.sum(0)
            max_equiv = max(max_equiv, float(np.max(np.abs(after - (raw + residual[None] / 2)))))
            residuals.append({**info, "rms": rms(residual), "rms_to_mixture": rms(residual) / rms(x),
                              "heart_correlation": pearson(residual, target[0]),
                              "lung_correlation": pearson(residual, target[1]),
                              "mixture_correlation": pearson(residual, x),
                              "mse_before": float(np.mean((raw.astype(float) - target) ** 2)),
                              "mse_after": float(np.mean((after.astype(float) - target) ** 2))})
            for method, output in (("before_consistency", raw), ("after_consistency", after)):
                row = dict(info)
                for i, label in enumerate(("heart", "lung")):
                    score = si_sdr(output[i], target[i])
                    row[f"{label}_si_sdr_db"] = score
                    row[f"{label}_si_sdri_db"] = score - si_sdr(x, target[i])
                    row[f"{label}_normalized_l1"] = float(np.mean(np.abs(output[i] - target[i]))) / (rms(target[i]) + 1e-6)
                    row[f"{label}_rms_ratio_db"] = float(20 * np.log10(rms(output[i]) / rms(target[i])))
                    row[f"{label}_target_projection_gain"] = float(np.dot(output[i].astype(float), target[i]) / np.dot(target[i].astype(float), target[i]))
                rows[method].append(row)
                if method == "after_consistency":
                    max_replay = max(max_replay, max(abs(row[k] - saved[recipe["mixture_id"]][k]) for k in FIELDS))
                    assert max_replay < 1e-5
    gradients = gradient_probe(model, sources)
    assert all(torch.equal(initial[k], v) for k, v in model.state_dict().items())
    assert sha256_file(checkpoint) == HASH
    summary = {"methods": {k: summarize(v) for k, v in rows.items()},
               "by_family": {k: grouped(v, "heart_family") for k, v in rows.items()},
               "by_level": {k: grouped(v, "relative_lung_to_heart_db") for k, v in rows.items()},
               "gradient_probes": gradients, "max_replay_db_error": max_replay,
               "max_consistency_commutation_error": max_equiv,
               "max_db_mixing_error": max_db_error,
               "consistency_worsened_conditions": {s: sum(b[f"{s}_si_sdri_db"] < a[f"{s}_si_sdri_db"]
                    for a, b in zip(rows["before_consistency"], rows["after_consistency"])) for s in ("heart", "lung")},
               "residual_pooled": {field: {"min": min(r[field] for r in residuals),
                    "median": float(np.median([r[field] for r in residuals])),
                    "max": max(r[field] for r in residuals)} for field in
                    ("rms_to_mixture", "heart_correlation", "lung_correlation", "mixture_correlation", "mse_before", "mse_after")},
               "elapsed_seconds": time.perf_counter() - tic, "failures": 0, "optimizer_updates": 0,
               "checkpoint_sha256": HASH, "validation_recipe_sha256": RECIPE_HASH,
               "eligible_manifest_sha256": sha256_file(RUN / "eligible_split.csv"),
               "script_sha256": sha256_file(Path(__file__)),
               "base_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "working_tree_note": "Analytical script uncommitted during execution; model/data/inference source unchanged",
               "python": sys.version, "torch": torch.__version__, "torchaudio": torchaudio.__version__,
               "test_access": False, "model_state_unchanged": True}
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in {**rows, "model_residuals": residuals}.items():
        write_json(OUT / f"{name}.json", data)
    write_json(OUT / "model_summary.json", summary)
    print(json.dumps({"done": True, "runtime_seconds": summary["elapsed_seconds"],
                      "methods": {k: v["selection_q_db"] for k, v in summary["methods"].items()},
                      "replay_db_error": max_replay}))


if __name__ == "__main__":
    main()
