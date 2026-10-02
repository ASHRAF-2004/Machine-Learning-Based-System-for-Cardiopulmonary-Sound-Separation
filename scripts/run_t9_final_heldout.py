"""One-shot, frozen T9 evaluation. No training and no automatic reruns."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
import wave
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torchaudio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.audio_utils import AudioData, frequency_mask_split
from app.ml.ensemble_v1 import GenericNMFExpert
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_data import DATA_ROOT, MANIFEST_SHA256, make_mixture
from scripts.evaluate_ensemble_qualification import si_sdr

RUN_ID = "t9-final-heldout-v1"
BASE_SHA = "dbb2218513c7d2516ceddf9d03dfb81d2a42a51e"
DOC_START_SHA = "944a646e09da466040d22b6de0af6e05fe3b0d77"
SPEC_REL = "research/configs/final_separator_v2.json"
MANIFEST_REL = "research/manifests/hls_cmds_split_v1.csv"
OUT = ROOT / ".local/training/stethofuse-tcn-v1/t9" / RUN_ID
SAMPLE_RATE, LENGTH, WINDOW, HOP, OVERLAP = 4000, 60000, 40000, 32000, 8000
LEVELS = (-10, -5, 0, 5, 10)
METHODS = ("mixture_baseline", "final_t8_v2_convtasnet", "fixed_filter", "generic_nmf")
EXPECTED = {
    "spec": "2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b",
    "checkpoint": "1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658",
    "manifest": MANIFEST_SHA256,
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_create(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()


def load_frozen_model() -> tuple[dict, StethoFuseConvTasNet, float]:
    spec_path = ROOT / SPEC_REL
    checkpoint_path = ROOT / ".local/training/stethofuse-tcn-v1/pre-t9-family-refit-v1/refit-all-nontest-seed20260928/checkpoints/endpoint.pt"
    if sha_file(spec_path) != EXPECTED["spec"] or sha_file(checkpoint_path) != EXPECTED["checkpoint"]:
        raise RuntimeError("Frozen v2 specification/checkpoint hash mismatch")
    spec = json.loads(spec_path.read_text())
    if spec["t9_protocol"]["expected_conditions"] != 225:
        raise RuntimeError("Frozen T9 condition count changed")
    started = time.perf_counter()
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model_spec = spec["model"]
    model = StethoFuseConvTasNet(model_spec["architecture_version"]).cpu().eval()
    if model.parameter_count != 171313 or model.parameter_count != model_spec["parameter_count"]:
        raise RuntimeError("Frozen separator parameter count mismatch")
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    if checkpoint["architecture_version"] != model_spec["architecture_version"]:
        raise RuntimeError("Frozen checkpoint architecture mismatch")
    return spec, model, time.perf_counter() - started


def verify_environment(spec: dict) -> None:
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    actual = {"python": platform.python_version(), "torch": torch.__version__,
              "torchaudio": torchaudio.__version__, "numpy": np.__version__,
              "scipy": __import__("scipy").__version__, "device": "cpu",
              "torch_threads": torch.get_num_threads(),
              "interop_threads": torch.get_num_interop_threads(),
              "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()}
    if actual != spec["environment"]:
        raise RuntimeError(f"Pinned environment mismatch: {actual}")
    if torch.cuda.is_available():
        raise RuntimeError("Frozen run requires the pinned CPU path")


def make_preflight() -> None:
    if OUT.exists() or (OUT.parent.exists() and any(OUT.parent.iterdir())):
        raise FileExistsError(f"One-shot T9 artifact path already exists: {OUT}")
    impl_head = git(ROOT, "rev-parse", "HEAD")
    docs_root = ROOT.parent / "documentation"
    if git(ROOT, "branch", "--show-current") != "fyp2/application":
        raise RuntimeError("Implementation branch is not fyp2/application")
    if git(ROOT, "status", "--porcelain"):
        raise RuntimeError("Implementation worktree must be clean before run preparation")
    if git(docs_root, "rev-parse", "HEAD") != DOC_START_SHA or git(docs_root, "status", "--porcelain"):
        raise RuntimeError("Documentation starting SHA/worktree differs from frozen preflight")
    parents = git(ROOT, "show", "-s", "--format=%P", "HEAD").split()
    if parents != [BASE_SHA]:
        raise RuntimeError("T9 runner commit must be one clean child of the approved checkpoint")
    spec, _, init_s = load_frozen_model()
    verify_environment(spec)
    for frozen in spec["t9_protocol"]["frozen_code_sources"].values():
        if sha_file(ROOT / frozen["path"]) != frozen["sha256"]:
            raise RuntimeError(f"Frozen T9 evaluator dependency changed: {frozen['path']}")
    model_spec = spec["model"]
    if sha_file(ROOT / model_spec["configuration_path"]) != model_spec["configuration_sha256"]:
        raise RuntimeError("Frozen model configuration hash mismatch")
    manifest = ROOT / MANIFEST_REL
    if sha_file(manifest) != EXPECTED["manifest"]:
        raise RuntimeError("Frozen source manifest hash mismatch")
    protocol = spec["t9_protocol"]
    required = ["mixture_baseline", "selected standalone Conv-TasNet", "Fixed Filter", "Generic NMF"]
    if protocol["expected_conditions"] != 225 or protocol["test_pair_count"] != 45:
        raise RuntimeError("Frozen T9 design count mismatch")
    receipt = {
        "schema_version": 1, "status": "PREPARED_NOT_OPENED", "run_id": RUN_ID,
        "prepared_utc": utc_now(), "implementation_sha": impl_head,
        "implementation_branch": "fyp2/application", "documentation_start_sha": DOC_START_SHA,
        "separator_spec_sha256": EXPECTED["spec"], "checkpoint_sha256": EXPECTED["checkpoint"],
        "source_manifest_sha256": EXPECTED["manifest"],
        "test_protocol_sha256": canonical_hash(protocol), "expected_conditions": 225,
        "levels_lung_to_heart_db": list(LEVELS), "comparators": list(METHODS),
        "metric_source": "scripts/evaluate_ensemble_qualification.py::si_sdr",
        "metric_source_sha256": protocol["frozen_code_sources"]["metric"]["sha256"],
        "runtime_device": "cpu", "environment": spec["environment"],
        "model_initialization_seconds_pre_access": init_s,
        "test_audio_opened": False, "first_test_audio_access_utc": None,
        "test_results_created": False,
    }
    atomic_create(OUT / "run_preflight.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))


def _weights(start: int, total: int) -> np.ndarray:
    weights = np.ones(WINDOW, dtype=np.float32)
    fade = 0.5 - 0.5 * np.cos(np.pi * (np.arange(OVERLAP, dtype=np.float32) + 1) /
                                (OVERLAP + 1))
    if start > 0:
        weights[:OVERLAP] = fade
    if start + WINDOW < total:
        weights[-OVERLAP:] = 1.0 - fade
    return weights


def _window_starts(length: int) -> list[int]:
    starts = list(range(0, max(1, length - WINDOW + 1), HOP))
    if not starts:
        starts = [0]
    while starts[-1] + WINDOW < length:
        starts.append(starts[-1] + HOP)
    return starts


def fixed_or_nmf_windowed(x: np.ndarray, method: str, nmf: GenericNMFExpert) -> np.ndarray:
    peak = float(np.max(np.abs(x)))
    if not math.isfinite(peak) or peak <= 0:
        raise ValueError("invalid mixture peak")
    normalized = x / np.float32(peak)
    sums = np.zeros((2, x.size), dtype=np.float64)
    coverage = np.zeros(x.size, dtype=np.float64)
    for start in _window_starts(x.size):
        valid = min(WINDOW, x.size - start)
        window = normalized[start:start + valid]
        if valid < WINDOW:
            window = np.pad(window, (0, WINDOW - valid))
        if np.sqrt(np.mean(window.astype(np.float64) ** 2)) < 1e-6:
            estimates = np.zeros((2, WINDOW), dtype=np.float32)
        elif method == "fixed_filter":
            heart, lung, _ = frequency_mask_split(window, SAMPLE_RATE)
            estimates = np.stack((heart, lung))
        else:
            audio = AudioData(window, SAMPLE_RATE, SAMPLE_RATE, 1, WINDOW / SAMPLE_RATE)
            output = nmf.separate(window)
            estimates = np.stack((output.heart, output.lung))
        if estimates.shape != (2, WINDOW) or not np.isfinite(estimates).all():
            raise RuntimeError(f"{method} returned invalid shape or values")
        weight = _weights(start, x.size)[:valid].astype(np.float64)
        sums[:, start:start + valid] += estimates[:, :valid] * weight
        coverage[start:start + valid] += weight
    if np.any(coverage <= 0):
        raise RuntimeError("window coverage gap")
    result = (sums / coverage[None, :] * peak).astype(np.float32)
    if result.shape != (2, x.size) or not np.isfinite(result).all():
        raise RuntimeError(f"{method} produced invalid full-record output")
    return result


def metric_row(condition: dict, method: str, estimates: np.ndarray,
               mixture: np.ndarray, targets: np.ndarray, elapsed: float) -> dict:
    if estimates.shape != (2, LENGTH):
        raise ValueError("output must be [heart, lung, 60000]")
    h_sisdr = si_sdr(estimates[0], targets[0])
    l_sisdr = si_sdr(estimates[1], targets[1])
    h_base, l_base = si_sdr(mixture, targets[0]), si_sdr(mixture, targets[1])
    return {**condition, "method": method, "status": "ok", "runtime_seconds": elapsed,
            "heart_si_sdr_db": h_sisdr, "heart_si_sdri_db": h_sisdr - h_base,
            "lung_si_sdr_db": l_sisdr, "lung_si_sdri_db": l_sisdr - l_base,
            "failure": None}


def _decode_test_source(row: dict[str, str], first_access: dict) -> np.ndarray:
    key = f"{row['kind']}/{row['id']}"
    if first_access["first_source"] is None:
        first_access["first_source"] = key
        first_access["first_test_audio_access_utc"] = utc_now()
        atomic_create(OUT / "first_test_audio_access.json", first_access)
    path = DATA_ROOT / row["kind"] / f"{row['id']}.wav"
    if sha_file(path) != row["sha256"]:
        raise RuntimeError(f"Frozen test source hash mismatch: {key}")
    with wave.open(str(path), "rb") as wav:
        if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getnframes()) != (4000, 1, 2, LENGTH):
            raise RuntimeError(f"Frozen source WAV header mismatch: {key}")
        raw = wav.readframes(LENGTH)
    if len(raw) != 2 * LENGTH:
        raise RuntimeError(f"Short source read: {key}")
    values = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if not np.isfinite(values).all():
        raise RuntimeError(f"Nonfinite source waveform: {key}")
    return values


def _conditions(manifest: Path, first_access: dict) -> tuple[list[dict], dict]:
    if sha_file(manifest) != EXPECTED["manifest"]:
        raise RuntimeError("Frozen source manifest changed")
    with manifest.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    hearts = sorted((r for r in rows if r["kind"] == "HS" and r["split"] == "test"),
                    key=lambda r: (r["family"], r["id"]))
    lungs = sorted((r for r in rows if r["kind"] == "LS" and r["split"] == "test"),
                   key=lambda r: (r["family"], r["id"]))
    if (len(hearts), len(lungs)) != (5, 9):
        raise RuntimeError("Frozen test partition must be exactly five heart and nine lung sources")
    sources = {f"{r['kind']}/{r['id']}": _decode_test_source(r, first_access)
               for r in hearts + lungs}
    recipes = []
    for hi, heart in enumerate(hearts):
        for li, lung in enumerate(lungs):
            for level in LEVELS:
                x, targets, gains = make_mixture(sources[f"HS/{heart['id']}"],
                                                  sources[f"LS/{lung['id']}"], level,
                                                  crop_samples=LENGTH)
                item = {"heart_id": heart["id"], "heart_sha256": heart["sha256"],
                        "heart_family": heart["family"], "lung_id": lung["id"],
                        "lung_sha256": lung["sha256"], "lung_family": lung["family"],
                        "heart_start": 0, "lung_start": 0, "crop_samples": LENGTH,
                        "relative_lung_to_heart_db": level, "seed_key": [20260928, hi, li, level],
                        **gains, "network_shared_peak_scale": gains["mixture_peak"],
                        "network_normalization": "divide mixture and both targets by mixture peak",
                        "mixture_sha256": sha_bytes(x.astype("<f4", copy=False).tobytes())}
                item["condition_id"] = canonical_hash(item)[:20]
                recipes.append(item)
    if len(recipes) != 225 or len({r["condition_id"] for r in recipes}) != 225:
        raise RuntimeError("Expected exactly 225 unique frozen conditions")
    return recipes, sources


def execute_run() -> None:
    run_started_utc = utc_now()
    run_started = time.perf_counter()
    preflight_path = OUT / "run_preflight.json"
    if not preflight_path.is_file():
        raise RuntimeError("Run must first be prepared; T9 audio remains unopened")
    preflight = json.loads(preflight_path.read_text())
    if preflight["run_id"] != RUN_ID or preflight["implementation_sha"] != git(ROOT, "rev-parse", "HEAD"):
        raise RuntimeError("Prepared run provenance does not match current source")
    if any((OUT / name).exists() for name in ("first_test_audio_access.json", "recipes.json", "results.jsonl")):
        raise FileExistsError("This immutable one-shot run has already started; no retry")
    spec, model, model_init_seconds = load_frozen_model()
    verify_environment(spec)
    nmf = GenericNMFExpert()
    first_access = {"run_id": RUN_ID, "first_source": None, "first_test_audio_access_utc": None}
    recipes, sources = _conditions(ROOT / MANIFEST_REL, first_access)
    atomic_create(OUT / "recipes.json", {"schema_version": 1, "run_id": RUN_ID,
                                          "recipes": recipes})
    recipe_sha = sha_file(OUT / "recipes.json")
    result_path = OUT / "results.jsonl"
    runtimes = {name: [] for name in METHODS}
    count = 0
    with result_path.open("x", encoding="utf-8") as results:
        for condition in recipes:
            heart = sources[f"HS/{condition['heart_id']}"]
            lung = sources[f"LS/{condition['lung_id']}"]
            mixture, targets, gains = make_mixture(heart, lung,
                condition["relative_lung_to_heart_db"], crop_samples=LENGTH)
            mixture_hash = sha_bytes(mixture.astype("<f4", copy=False).tobytes())
            if mixture_hash != condition["mixture_sha256"]:
                raise RuntimeError("Deterministic mixture did not reproduce frozen recipe hash")
            common = {k: condition[k] for k in ("condition_id", "heart_id", "lung_id",
                "heart_family", "lung_family", "relative_lung_to_heart_db", "mixture_sha256")}
            for method in METHODS:
                started = time.perf_counter()
                try:
                    if method == "mixture_baseline":
                        estimates = np.stack((mixture, mixture))
                    elif method == "fixed_filter":
                        estimates = fixed_or_nmf_windowed(mixture, method, nmf)
                    elif method == "generic_nmf":
                        estimates = fixed_or_nmf_windowed(mixture, method, nmf)
                    else:
                        with torch.inference_mode():
                            tensor = torch.from_numpy(mixture.copy())
                            separated = model.separate_recording(tensor)
                        estimates = separated.cpu().numpy().astype(np.float32, copy=False)
                    elapsed = time.perf_counter() - started
                    row = metric_row(common, method, estimates, mixture, targets, elapsed)
                    runtimes[method].append(elapsed)
                except Exception as exc:
                    elapsed = time.perf_counter() - started
                    runtimes[method].append(elapsed)
                    row = {**common, "method": method, "status": "failed",
                           "runtime_seconds": elapsed, "heart_si_sdr_db": None,
                           "heart_si_sdri_db": None, "lung_si_sdr_db": None,
                           "lung_si_sdri_db": None,
                           "failure": {"type": type(exc).__name__, "message": str(exc)}}
                results.write(json.dumps(row, sort_keys=True) + "\n")
                results.flush()
                count += 1
    raw_sha = sha_file(result_path)
    summary = summarize(recipes, runtimes, count, raw_sha, recipe_sha, model_init_seconds)
    summary["run_started_utc"] = run_started_utc
    summary["completed_utc"] = utc_now()
    summary["overall_elapsed_seconds"] = time.perf_counter() - run_started
    summary["first_test_audio_access"] = json.loads((OUT / "first_test_audio_access.json").read_text())
    atomic_create(OUT / "summary.json", summary)
    atomic_create(OUT / "completion_receipt.json", {
        "run_id": RUN_ID, "status": summary["status"],
        "implementation_sha": git(ROOT, "rev-parse", "HEAD"),
        "recipe_manifest_sha256": recipe_sha, "raw_results_sha256": raw_sha,
        "summary_sha256": sha_file(OUT / "summary.json"),
        "completed_utc": summary["completed_utc"],
    })
    print(json.dumps(summary, indent=2, sort_keys=True))


def _aggregate(rows: list[dict], metric: str) -> float:
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        groups[(row["heart_family"], row["lung_family"])].append(float(row[metric]))
    return float(np.mean([np.mean(vals) for vals in groups.values()]))


def _spread(values: list[float]) -> dict[str, float]:
    q25, median, q75 = np.percentile(np.asarray(values, dtype=np.float64), [25, 50, 75])
    return {"median": float(median), "q1": float(q25), "q3": float(q75), "iqr": float(q75 - q25)}


def summarize(recipes: list[dict], runtimes: dict, count: int, raw_sha: str,
              recipe_sha: str, model_init_seconds: float) -> dict:
    rows = [json.loads(line) for line in (OUT / "results.jsonl").read_text().splitlines()]
    out = {"schema_version": 1, "run_id": RUN_ID,
           "status": "COMPLETE" if count == 900 and len(rows) == 900 and all(r["status"] == "ok" for r in rows)
           else "COMPLETE_WITH_FAILURES", "condition_count": len(recipes),
           "method_condition_rows": count, "failures": {}, "aggregates": {},
           "family_pairs": {}, "relative_levels": {}, "runtimes": {},
           "model_initialization_seconds": model_init_seconds,
           "recipe_manifest_sha256": recipe_sha, "raw_results_sha256": raw_sha}
    for method in METHODS:
        method_rows = [r for r in rows if r["method"] == method]
        failures = [r for r in method_rows if r["status"] != "ok"]
        out["failures"][method] = len(failures)
        if failures or len(method_rows) != len(recipes):
            out["aggregates"][method] = None
            out["family_pairs"][method] = None
            out["relative_levels"][method] = None
        else:
            metrics = ("heart_si_sdr_db", "heart_si_sdri_db", "lung_si_sdr_db", "lung_si_sdri_db")
            agg = {key: _aggregate(method_rows, key) for key in metrics}
            for key in metrics:
                agg[key + "_spread"] = _spread([float(r[key]) for r in method_rows])
            agg["balanced_mean_si_sdri_db"] = (agg["heart_si_sdri_db"] + agg["lung_si_sdri_db"]) / 2
            out["aggregates"][method] = agg
            pairs = {}
            by_pair: dict[tuple[str, str], list] = defaultdict(list)
            for row in method_rows:
                by_pair[(row["heart_family"], row["lung_family"])].append(row)
            for pair, items in sorted(by_pair.items()):
                entry = {k: float(np.mean([r[k] for r in items])) for k in metrics}
                entry["balanced_mean_si_sdri_db"] = (entry["heart_si_sdri_db"] + entry["lung_si_sdri_db"]) / 2
                entry["condition_count"] = len(items)
                pairs[f"{pair[0]} × {pair[1]}"] = entry
            out["family_pairs"][method] = pairs
            levels = {}
            for level in LEVELS:
                items = [r for r in method_rows if r["relative_lung_to_heart_db"] == level]
                h = float(np.mean([r["heart_si_sdri_db"] for r in items]))
                l = float(np.mean([r["lung_si_sdri_db"] for r in items]))
                levels[str(level)] = {"heart_si_sdri_db": h, "lung_si_sdri_db": l,
                                      "balanced_mean_si_sdri_db": (h + l) / 2,
                                      "condition_count": len(items)}
            out["relative_levels"][method] = levels
        elapsed = float(np.sum(runtimes[method]))
        out["runtimes"][method] = {"completed_calls_seconds": elapsed,
                                   "mean_seconds_per_completed_condition":
                                   elapsed / len(runtimes[method]) if runtimes[method] else None,
                                   "median_seconds_per_completed_condition":
                                   float(np.median(runtimes[method])) if runtimes[method] else None,
                                   "completed_calls": len(runtimes[method])}
    out["strongest_tcn_pair"] = None
    out["hardest_tcn_pair"] = None
    tcn_pairs = out["family_pairs"]["final_t8_v2_convtasnet"]
    if tcn_pairs:
        out["strongest_tcn_pair"] = max(tcn_pairs, key=lambda k: tcn_pairs[k]["balanced_mean_si_sdri_db"])
        out["hardest_tcn_pair"] = min(tcn_pairs, key=lambda k: tcn_pairs[k]["balanced_mean_si_sdri_db"])
    levels = out["relative_levels"]["final_t8_v2_convtasnet"]
    if levels:
        out["hardest_heart_level_db"] = min(levels, key=lambda k: levels[k]["heart_si_sdri_db"])
        out["hardest_lung_level_db"] = min(levels, key=lambda k: levels[k]["lung_si_sdri_db"])
    return out


def smoke() -> None:
    spec, model, _ = load_frozen_model()
    verify_environment(spec)
    t = np.arange(LENGTH, dtype=np.float32) / SAMPLE_RATE
    h = (.2 * np.sin(2 * np.pi * 72 * t)).astype(np.float32)
    l = (.1 * np.sin(2 * np.pi * 330 * t)).astype(np.float32)
    x, targets, _ = make_mixture(h, l, 0, crop_samples=LENGTH)
    outputs = {"mixture_baseline": np.stack((x, x)),
               "fixed_filter": fixed_or_nmf_windowed(x, "fixed_filter", GenericNMFExpert()),
               "generic_nmf": fixed_or_nmf_windowed(x, "generic_nmf", GenericNMFExpert())}
    with torch.inference_mode():
        outputs["final_t8_v2_convtasnet"] = model.separate_recording(torch.from_numpy(x.copy())).numpy()
    results = {}
    for method, estimate in outputs.items():
        row = metric_row({"condition_id": "synthetic-only"}, method, estimate, x, targets, 0.0)
        results[method] = {"finite": bool(np.isfinite(estimate).all()),
                           "shape": list(estimate.shape), "metric_finite":
                           all(math.isfinite(row[k]) for k in ("heart_si_sdr_db", "heart_si_sdri_db",
                                                               "lung_si_sdr_db", "lung_si_sdri_db"))}
    if not all(v["finite"] and v["shape"] == [2, LENGTH] and v["metric_finite"] for v in results.values()):
        raise RuntimeError("Synthetic-only T9 runner smoke failed")
    print(json.dumps({"status": "PASS", "test_audio_opened": False, "optimizer_updates": 0,
                      "synthetic_only": True, "methods": results}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        smoke()
    elif args.prepare:
        make_preflight()
    else:
        try:
            execute_run()
        except Exception as exc:
            if (OUT / "first_test_audio_access.json").exists() and not (OUT / "run_invalid.json").exists():
                processed = 0
                result_path = OUT / "results.jsonl"
                if result_path.exists():
                    processed = sum(1 for _ in result_path.open(encoding="utf-8"))
                atomic_create(OUT / "run_invalid.json", {
                    "run_id": RUN_ID, "status": "INVALID_STOPPED_NO_RERUN",
                    "timestamp_utc": utc_now(), "implementation_sha": git(ROOT, "rev-parse", "HEAD"),
                    "exception_type": type(exc).__name__, "message": str(exc),
                    "method_condition_rows_written": processed,
                })
            raise


if __name__ == "__main__":
    main()
