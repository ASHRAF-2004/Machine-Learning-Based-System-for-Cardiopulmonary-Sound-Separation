"""One frozen validation-only complementarity pass; no fusion search or training.

No test Source is constructed. The only neural artifact accepted is the selected
T7 primary-seed checkpoint. JSON metrics are written under ignored .local/.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
import scipy
from scipy.signal import correlate, correlation_lags
import torch
import torchaudio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.audio_utils import frequency_mask_split, istft, stft
from app.ml.ensemble_v1 import GenericNMFExpert, _expert_mask
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_data import (DATA_ROOT, DEFAULT_MANIFEST, MANIFEST_SHA256,
                                  Source, read_source, sha256_file, write_json)
from app.ml.training_objective import selection_score
from scripts.evaluate_ensemble_qualification import si_sdr
from scripts.train_stethofuse_baseline import get_mix_target, aggregate_absolute

RUN = ROOT / ".local/training/stethofuse-tcn-v1/t7-small-seed20260928"
OUT = ROOT / ".local/ensemble/final_reconsideration/primary-validation-v1"
CHECKPOINT_HASH = "89f8d66134c0a49aa2a05971720cdffbdd1e501ebce99bb83119e6683d58ac93"
RECIPE_HASH = "b4cef517cd4a64c267d3645ea6b918b5dfb72945f7536c0245b73228f00fdc90"
NAMES = ("tcn_waveform", "tcn_mixture_phase", "fixed_filter", "generic_nmf")
FIELDS = tuple(f"{s}_{m}_db" for s in ("heart", "lung") for m in ("si_sdr", "si_sdri"))


class WindowDiagnostic(torch.nn.Module):
    """Reuse the unchanged TCN window/gain/trim policy for every representation."""
    inference_window_samples = StethoFuseConvTasNet.inference_window_samples
    inference_hop_samples = StethoFuseConvTasNet.inference_hop_samples
    overlap_samples = StethoFuseConvTasNet.overlap_samples
    separate_recording = StethoFuseConvTasNet.separate_recording

    def __init__(self, kind: str, model: StethoFuseConvTasNet):
        super().__init__()
        self.kind = kind
        self.model = model
        self.nmf = GenericNMFExpert() if kind == "generic_nmf" else None

    def forward(self, mixture: torch.Tensor) -> torch.Tensor:
        if mixture.shape[:2] != (1, 1):
            raise ValueError("Diagnostic window requires one mono CPU example")
        x = mixture[0, 0].numpy()
        if self.kind == "tcn_mixture_phase":
            output = self.model(mixture)[0].numpy()
            mask = _expert_mask(output[0], output[1])
            tf = stft(x, 4000, n_fft=1024, hop_length=256)
            pair = (istft(tf, mask * tf.spectrum), istft(tf, (1 - mask) * tf.spectrum))
        elif self.kind == "fixed_filter":
            heart, lung, _ = frequency_mask_split(x, 4000)
            pair = (heart, lung)
        elif self.kind == "generic_nmf":
            output = self.nmf.separate(x)
            if output.sample_rate_hz != 4000:
                raise ValueError("NMF sample-rate mismatch")
            pair = (output.heart, output.lung)
        else:
            raise ValueError(self.kind)
        result = np.stack(pair).astype(np.float32)
        if result.shape != (2, x.size) or not np.isfinite(result).all():
            raise ValueError("Invalid diagnostic output")
        return torch.from_numpy(result).unsqueeze(0)


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64) - np.mean(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64) - np.mean(b, dtype=np.float64)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator <= 1e-20:
        raise ValueError("Uninformative correlation")
    return float(np.dot(a, b) / denominator)


def lag_diagnostic(estimate: np.ndarray, reference: np.ndarray) -> dict:
    a, b = estimate.astype(np.float64), reference.astype(np.float64)
    a -= a.mean()
    b -= b.mean()
    values = correlate(a, b, mode="full", method="fft")
    lags = correlation_lags(a.size, b.size)
    keep = np.abs(lags) <= 128  # +/-32 ms, diagnostic only; never shift output.
    values, lags = values[keep], lags[keep]
    index = int(np.argmax(np.abs(values)))
    return {"absolute_peak_lag_samples": int(lags[index]),
            "peak_signed_correlation": float(values[index] / (np.linalg.norm(a) * np.linalg.norm(b))),
            "zero_lag_correlation": pearson(a, b)}


def summarize(rows: list[dict]) -> dict:
    result = {"conditions": len(rows), **selection_score(rows)}
    for field in FIELDS:
        values = np.array([r[field] for r in rows])
        result[field] = {"macro_mean": aggregate_absolute(rows, field),
                         "pooled_median": float(np.median(values)),
                         "pooled_iqr": float(np.quantile(values, .75) - np.quantile(values, .25)),
                         "negative_conditions": int(np.sum(values < 0))}
    return result


def grouped(rows: list[dict], field: str) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return {key: summarize(values) for key, values in sorted(groups.items())}


def main() -> None:
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    if torch.__version__ != "2.11.0+cpu" or torchaudio.__version__ != "2.11.0+cpu":
        raise RuntimeError("Pinned CPU environment required")
    if OUT.exists():
        raise RuntimeError("Diagnostic output already exists; refuse to repeat/overwrite")
    if subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True).strip():
        raise RuntimeError("Commit the diagnostic source before execution")
    checkpoint = RUN / "checkpoints/best.pt"
    recipe_path = RUN / "validation/frozen_recipes.json"
    if (sha256_file(checkpoint) != CHECKPOINT_HASH or sha256_file(recipe_path) != RECIPE_HASH or
            sha256_file(DEFAULT_MANIFEST) != MANIFEST_SHA256):
        raise RuntimeError("Frozen artifact mismatch")
    # Read only the prior eligible manifest (which contains no test rows), then
    # filter validation before constructing paths or inspecting any source bytes.
    metadata = list(csv.DictReader((RUN / "eligible_split.csv").open(newline="")))
    if any(row["split"] == "test" for row in metadata):
        raise RuntimeError("Unexpected test row in eligible metadata")
    sources = [Source(r["kind"], r["id"], r["family"], r["split"], r["sha256"],
                      DATA_ROOT / r["kind"] / f"{r['id']}.wav")
               for r in metadata if r["split"] == "validation"]
    if len(sources) != 14:
        raise RuntimeError("Expected 14 frozen validation source files")
    for source in sources:
        if sha256_file(source.path) != source.sha256:
            raise RuntimeError("Validation source bytes changed")
    cache = {(s.kind, s.id): read_source(s) for s in sources}
    source_map = {(s.kind, s.id): s for s in sources}
    payload = json.loads(recipe_path.read_text())
    recipes = payload["recipes"]
    if len(recipes) != 225 or payload["source_manifest_sha256"] != MANIFEST_SHA256:
        raise RuntimeError("Frozen recipe contract mismatch")
    for recipe in recipes:
        for kind, label in (("HS", "heart"), ("LS", "lung")):
            source = source_map[(kind, recipe[f"{label}_id"])]
            if (source.sha256 != recipe[f"{label}_sha256"] or
                    source.family != recipe[f"{label}_family"] or recipe[f"{label}_start"] != 0):
                raise RuntimeError("Recipe metadata mismatch")
    saved = {r["mixture_id"]: r for r in map(json.loads,
        (RUN / "validation/best_checkpoint_per_condition.jsonl").read_text().splitlines())}
    if len(saved) != 225:
        raise RuntimeError("Saved control rows missing")
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model = StethoFuseConvTasNet("stethofuse-convtasnet-4k-small-v1").eval()
    if state["architecture_version"] != model.architecture_version or state["epoch"] != 8:
        raise RuntimeError("Selected checkpoint identity mismatch")
    model.load_state_dict(state["state_dict"], strict=True)
    methods = {"tcn_waveform": model, **{name: WindowDiagnostic(name, model).eval() for name in NAMES[1:]}}
    rows = {name: [] for name in NAMES}
    oracles = {name: [] for name in NAMES[2:]}
    residuals, alignment = [], []
    timings = {name: 0.0 for name in NAMES}
    consistency = {name: 0.0 for name in NAMES}
    replay_error = 0.0
    # First manifest-order pair in each family, all five levels: selected before scoring.
    first_pairs = {}
    for recipe in recipes:
        first_pairs.setdefault(recipe["heart_family"], (recipe["heart_id"], recipe["lung_id"]))
    started = time.perf_counter()
    OUT.mkdir(parents=True)
    manifest = {"classification": "VALIDATION DIAGNOSTIC ONLY; NO ENSEMBLE EVALUATED",
                "started_at_utc": datetime.now(timezone.utc).isoformat(),
                "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "script_sha256": sha256_file(Path(__file__)), "checkpoint_sha256": CHECKPOINT_HASH,
                "source_manifest_sha256": MANIFEST_SHA256, "validation_recipe_sha256": RECIPE_HASH,
                "python": sys.version, "torch": torch.__version__, "torchaudio": torchaudio.__version__,
                "numpy": np.__version__, "scipy": scipy.__version__, "device": "cpu",
                "thread_environment": {key: os.environ.get(key) for key in
                                       ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
                "alignment_predeclared_pairs": first_pairs, "alignment_max_lag_samples": 128,
                "test_access": "NONE", "training": False, "production_touched": False,
                "method_source_sha256": {p: sha256_file(ROOT / p) for p in (
                    "app/ml/stethofuse_tcn.py", "app/ml/ensemble_v1.py", "app/ml/audio_utils.py",
                    "app/ml/strategies/nmf_strategy.py", "app/ml/training_data.py",
                    "scripts/train_stethofuse_baseline.py", "scripts/evaluate_ensemble_qualification.py")}}
    write_json(OUT / "manifest.json", manifest)
    with torch.inference_mode():
        for index, recipe in enumerate(recipes):
            mixture, target = get_mix_target(recipe, cache)
            info = {k: recipe[k] for k in ("mixture_id", "heart_id", "lung_id", "heart_family",
                                         "lung_family", "relative_lung_to_heart_db")}
            outputs = {}
            for name, method in methods.items():
                tic = time.perf_counter()
                outputs[name] = method.separate_recording(torch.from_numpy(mixture)).numpy()
                timings[name] += time.perf_counter() - tic
                estimated = outputs[name]
                if estimated.shape != target.shape or not np.isfinite(estimated).all():
                    raise RuntimeError("Invalid output; no fallback or condition exclusion")
                consistency[name] = max(consistency[name], float(np.max(np.abs(estimated.sum(0) - mixture))))
                row = dict(info)
                for s, label in enumerate(("heart", "lung")):
                    score = si_sdr(estimated[s], target[s])
                    row[f"{label}_si_sdr_db"] = score
                    row[f"{label}_si_sdri_db"] = score - si_sdr(mixture, target[s])
                rows[name].append(row)
                if name == "tcn_waveform":
                    error = max(abs(row[k] - saved[recipe["mixture_id"]][k]) for k in FIELDS)
                    replay_error = max(error, replay_error)
                    if error > 1e-5:
                        raise RuntimeError(f"Control does not replay: {error}")
                if (recipe["heart_id"], recipe["lung_id"]) == first_pairs[recipe["heart_family"]]:
                    for s, label in enumerate(("heart", "lung")):
                        alignment.append({**info, "method": name, "source": label,
                                          **lag_diagnostic(estimated[s], target[s])})
            control = rows["tcn_waveform"][-1]
            for name in NAMES[2:]:
                secondary = rows[name][-1]
                # Reference-assisted hard routing bound, not a deployable result
                # or a mathematical upper bound on all possible waveform fusions.
                oracles[name].append({**info, **{k: max(control[k], secondary[k]) for k in FIELDS}})
                residual = {**info, "expert": name}
                for s, label in enumerate(("heart", "lung")):
                    a = outputs["tcn_waveform"][s].astype(np.float64) - target[s]
                    b = outputs[name][s].astype(np.float64) - target[s]
                    residual[f"{label}_residual_pearson"] = pearson(a, b)
                    residual[f"{label}_residual_energy_ratio_secondary_to_tcn"] = float(np.dot(b, b) / np.dot(a, a))
                    residual[f"{label}_secondary_win"] = secondary[f"{label}_si_sdri_db"] > control[f"{label}_si_sdri_db"] + 1e-6
                    residual[f"{label}_tcn_negative_improvement"] = control[f"{label}_si_sdri_db"] < 0
                residuals.append(residual)
            if (index + 1) % 75 == 0:
                print(json.dumps({"validation_conditions_complete": index + 1}), flush=True)
    summary = {"methods": {name: summarize(values) for name, values in rows.items()},
               "by_heart_family": {name: grouped(values, "heart_family") for name, values in rows.items()},
               "by_level": {name: grouped(values, "relative_lung_to_heart_db") for name, values in rows.items()},
               "oracle_hard_routing_not_deployable": {name: summarize(values) for name, values in oracles.items()},
               "method_runtime_seconds": timings, "max_abs_reconstruction_error": consistency,
               "control_replay_max_abs_db_error": replay_error, "failures": 0,
               "elapsed_seconds": time.perf_counter() - started,
               "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
    for name, values in {**rows, **{f"oracle_{k}": v for k, v in oracles.items()},
                         "residuals": residuals, "alignment": alignment}.items():
        (OUT / f"{name}.jsonl").write_text("".join(json.dumps(v, sort_keys=True) + "\n" for v in values))
    write_json(OUT / "summary.json", summary)
    print(json.dumps({"status": "COMPLETE", "output": str(OUT),
                      "control_replay_error_db": replay_error, "runtime_seconds": summary["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
