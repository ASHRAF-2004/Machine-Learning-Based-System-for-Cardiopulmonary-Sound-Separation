"""Small source-family-disjoint engineering probe; NOT final FYP evaluation.

Uses byte-verified released HLS-CMDS 4-kHz isolated sources already present
locally. Writes only ignored .local research manifests/results, never audio.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
import wave
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.ensemble_v1 import EnsembleEngine, GenericNMFExpert, NeoSSNetExpert

DATA = ROOT / "datasets/hls_cmds"
OUT = ROOT / ".local/ensemble/qualification"
SEED = 42
PROBE_HEART = {"Late Systolic Murmur", "S3", "Atrial Fibrillation"}
PROBE_LUNG = {"Rhonchi", "Normal"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources(kind: str) -> list[dict[str, object]]:
    family_field = "Heart Sound Type" if kind == "HS" else "Lung Sound Type"
    id_field = "Heart Sound ID" if kind == "HS" else "Lung Sound ID"
    with (DATA / "metadata" / f"{kind}.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    result = []
    for row in rows:
        metadata_id = row[id_field].strip()
        resolved_id = metadata_id
        path = DATA / "raw" / kind / f"{resolved_id}.wav"
        if kind == "LS" and not path.is_file():
            # Published LS.csv uses older C/G abbreviations for the released
            # FC/CC filenames. Resolve only by the declared sound type.
            code = {"Fine Crackles": "FC", "Coarse Crackles": "CC"}.get(row[family_field])
            parts = metadata_id.split("_")
            if code and len(parts) == 3 and parts[1] in ("C", "G"):
                resolved_id = f"{parts[0]}_{code}_{parts[2]}"
                path = DATA / "raw" / kind / f"{resolved_id}.wav"
        if not path.is_file():
            raise RuntimeError(f"Missing released source {kind}/{metadata_id}")
        with wave.open(str(path)) as wav:
            if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (4000, 1, 2):
                raise RuntimeError("Unexpected source format")
        result.append({"kind": kind, "id": resolved_id, "metadata_id": metadata_id,
                       "family": row[family_field],
                       "gender": row["Gender"], "location": row["Location"],
                       "sha256": sha(path), "path": path})
    if len(result) != 50 or len({item["sha256"] for item in result}) != 50:
        raise RuntimeError("Missing or exact-duplicate released source")
    return result


def assign_splits(items: list[dict[str, object]], kind: str) -> dict[str, str]:
    families = sorted({str(item["family"]) for item in items})
    forced = PROBE_HEART if kind == "HS" else PROBE_LUNG
    if not forced <= set(families):
        raise RuntimeError("Recorded probe families absent from dataset")
    remaining = sorted(set(families) - forced)
    random.Random(SEED + (0 if kind == "HS" else 1)).shuffle(remaining)
    development_count = 6 if kind == "HS" else 4
    validation_count = 2 if kind == "HS" else 1
    development = set(forced) | set(remaining[: development_count - len(forced)])
    validation = set(remaining[development_count - len(forced):][:validation_count])
    result = {family: ("development" if family in development else
                       "validation" if family in validation else "test") for family in families}
    return result


def read_first_ten_seconds(item: dict[str, object]) -> np.ndarray:
    with wave.open(str(item["path"])) as wav:
        frames = wav.readframes(40000)
    audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if audio.size != 40000:
        raise RuntimeError("Source shorter than frozen 10-second crop")
    return audio


def controlled_mix(heart: np.ndarray, lung: np.ndarray, ratio_db: int):
    rms_h = float(np.sqrt(np.mean(heart.astype(np.float64) ** 2)))
    rms_l = float(np.sqrt(np.mean(lung.astype(np.float64) ** 2)))
    if min(rms_h, rms_l) < 1e-6:
        raise RuntimeError("Silent controlled source")
    lung_gain = 10 ** (ratio_db / 20) * rms_h / rms_l
    preliminary = heart.astype(np.float64) + lung.astype(np.float64) * lung_gain
    common_gain = min(1.0, 0.95 / float(np.max(np.abs(preliminary))))
    h = (heart.astype(np.float64) * common_gain).astype(np.float32)
    l = (lung.astype(np.float64) * lung_gain * common_gain).astype(np.float32)
    mixture = h + l
    return mixture, h, l, lung_gain, common_gain


def si_sdr(estimate: np.ndarray, reference: np.ndarray) -> float:
    target = np.asarray(reference, dtype=np.float64)
    output = np.asarray(estimate, dtype=np.float64)
    if target.shape != output.shape or not np.all(np.isfinite(output)):
        raise RuntimeError("SI-SDR shape/finite mismatch")
    target -= np.mean(target)
    output -= np.mean(output)
    energy = float(np.dot(target, target))
    if energy / target.size < 1e-12:
        raise RuntimeError("Undefined SI-SDR for silent reference")
    projection = np.dot(output, target) / energy * target
    residual = output - projection
    epsilon = 1e-8
    return float(10 * np.log10((np.dot(projection, projection) + epsilon) /
                                (np.dot(residual, residual) + epsilon)))


def main() -> None:
    heart_sources = sources("HS")
    lung_sources = sources("LS")
    all_sources = heart_sources + lung_sources
    if len({item["sha256"] for item in all_sources}) != len(all_sources):
        raise RuntimeError("Cross-source exact duplicate requires family merge")
    split_by_kind = {kind: assign_splits(items, kind) for kind, items in
                     (("HS", heart_sources), ("LS", lung_sources))}
    manifest_sources = []
    for item in all_sources:
        entry = {key: value for key, value in item.items() if key != "path"}
        entry["split"] = split_by_kind[str(item["kind"])][str(item["family"])]
        manifest_sources.append(entry)

    # Two independent development-family pairs only: shape/numerical qualification,
    # not a held-out performance study. All three frozen mixing ratios are exercised.
    chosen = {}
    for kind, items in (("HS", heart_sources), ("LS", lung_sources)):
        groups: dict[str, list[dict[str, object]]] = defaultdict(list)
        for item in items:
            if split_by_kind[kind][str(item["family"])] == "development":
                groups[str(item["family"])].append(item)
        selected_families = sorted(groups)[:2]
        chosen[kind] = [sorted(groups[family], key=lambda x: str(x["id"]))[0]
                        for family in selected_families]
    engine = EnsembleEngine(NeoSSNetExpert("cpu"), GenericNMFExpert())
    rows = []
    mixtures = []
    run_provenance = []
    for index, (hsrc, lsrc) in enumerate(zip(chosen["HS"], chosen["LS"]), start=1):
        heart = read_first_ten_seconds(hsrc)
        lung = read_first_ten_seconds(lsrc)
        for ratio in (-5, 0, 5):
            mix, href, lref, lung_gain, common_gain = controlled_mix(heart, lung, ratio)
            mix_id = f"qualification-{index}-{ratio:+d}dB"
            mixtures.append({"id": mix_id, "split": "development", "heart_id": hsrc["id"],
                             "lung_id": lsrc["id"], "heart_sha256": hsrc["sha256"],
                             "lung_sha256": lsrc["sha256"], "crop_start": 0,
                             "crop_samples": 40000, "ratio_db": ratio,
                             "lung_gain": lung_gain, "common_gain": common_gain,
                             "mixture_sha256": hashlib.sha256(mix.tobytes()).hexdigest(),
                             "additive_max_error": float(np.max(np.abs(mix - (href + lref))))})
            run = engine.separate(mix, recording_id=mix_id)
            run_provenance.append(run.provenance)
            baseline = {"heart": si_sdr(mix, href), "lung": si_sdr(mix, lref)}
            methods = {"ensemble": (run.heart, run.lung), **run.controls}
            for name, (hest, lest) in methods.items():
                for source, estimate, reference in (("heart", hest, href), ("lung", lest, lref)):
                    score = si_sdr(estimate, reference)
                    rows.append({"mixture_id": mix_id, "method": name, "source": source,
                                 "si_sdr_db": score, "si_sdri_db": score - baseline[source],
                                 "runtime_ms": run.provenance["total_runtime_ms"],
                                 "expert_timings_ms": run.provenance["timings_ms"]})
            print(f"{mix_id}: methods={len(methods)}, runtime_ms={run.provenance['total_runtime_ms']:.1f}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"classification": "DEVELOPMENT-ONLY ENGINEERING QUALIFICATION; NOT HELD-OUT FYP RESULT",
                "created_utc": datetime.now(timezone.utc).isoformat(), "seed": SEED,
                "release": "HLS-CMDS Zenodo record 15376628; official ZIP and local WAV bytes matched before this run",
                "source_family_rule": "sound type across gender/location; three recorded probe families forced to development",
                "preprocessing": "original released 4-kHz PCM16, first 10 s, no resampling; additive digital mixing",
                "source_splits": manifest_sources, "mixtures": mixtures}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUT / "per_record.json").write_text(json.dumps(rows, indent=2) + "\n")
    (OUT / "run_provenance.json").write_text(json.dumps(run_provenance, indent=2) + "\n")
    summary = []
    for name in sorted({row["method"] for row in rows}):
        for source in ("heart", "lung"):
            subset = [row for row in rows if row["method"] == name and row["source"] == source]
            summary.append({"method": name, "source": source, "n_mixtures": len(subset),
                            "mean_si_sdr_db": float(np.mean([row["si_sdr_db"] for row in subset])),
                            "median_si_sdr_db": float(np.median([row["si_sdr_db"] for row in subset])),
                            "mean_si_sdri_db": float(np.mean([row["si_sdri_db"] for row in subset])),
                            "failures": 0})
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"mixtures": len(mixtures), "pairs": 2, "rows": len(rows),
                      "manifest": str(OUT / "manifest.json"), "summary": summary}, sort_keys=True))


if __name__ == "__main__":
    main()
