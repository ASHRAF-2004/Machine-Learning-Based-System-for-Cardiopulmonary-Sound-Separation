"""Bounded, non-test source diagnostics for the pre-T9 plateau review.

Reads only the saved run's development/validation allowlist; never enumerates
the full split or dataset. Descriptors are diagnostic, not deployed features.
No learning, reference fitting, test access, or model selection occurs here.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
import time

import numpy as np
from scipy.signal import correlate, find_peaks, welch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.training_data import DATA_ROOT, Source, read_source, sha256_file

ALLOWLIST = ROOT / ".local/training/stethofuse-tcn-v1/t7-small-seed20260928/eligible_split.csv"
OUT = ROOT / ".local/diagnosis/pre_t9_plateau/v1"
SR = 4000
BANDS = ((0, 50), (50, 100), (100, 200), (200, 400), (400, 800),
         (800, 1200), (1200, 2001))
FEATURES = ("log_centroid", "log_flatness", "log_low_mid", "log_high_mid",
            "log_top_mid", "envelope_acf_peak", "envelope_acf_lag_seconds")


def summary(values):
    x = np.asarray(values, dtype=np.float64)
    return {"min": float(x.min()), "q25": float(np.quantile(x, .25)),
            "median": float(np.median(x)), "q75": float(np.quantile(x, .75)),
            "max": float(x.max()), "mean": float(x.mean())}


def spectral(x):
    f, p = welch(x.astype(np.float64), SR, nperseg=1024, noverlap=512,
                 nfft=2048, detrend="constant")
    p[0] = 0
    p /= p.sum()
    bands = [float(p[(f >= low) & (f < high)].sum()) for low, high in BANDS]
    positive = p[1:]
    flat = float(np.exp(np.mean(np.log(positive + 1e-20))) / np.mean(positive))
    return p, float(np.dot(f, p)), flat, bands


def acf_peak(x, low, high, rate):
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    a = correlate(x, x, method="fft", mode="full")[x.size - 1:]
    if a[0] <= 1e-20:
        return 0., 0.
    a /= a[0]  # Biased finite-record ACF; no claim of physiological rate.
    lo, hi = int(low * rate), min(int(high * rate), a.size - 1)
    peaks, _ = find_peaks(a[lo:hi + 1])
    index = int(lo + peaks[np.argmax(a[lo + peaks])]) if peaks.size else int(lo + np.argmax(a[lo:hi + 1]))
    return float(a[index]), float(index / rate)


def describe(x, kind):
    p, centroid, flatness, bands = spectral(x)
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
    peak = float(np.max(np.abs(x)))
    # 20-ms RMS envelope, 50 Hz. Heart window .2-3s; lung .5-6s.
    envelope = np.sqrt(np.mean(x.reshape(-1, 80).astype(np.float64) ** 2, axis=1))
    lo, hi = (.2, 3.) if kind == "HS" else (.5, 6.)
    envpeak, envlag = acf_peak(envelope, lo, hi, 50)
    rawpeak, rawlag = acf_peak(x, lo, hi, SR)
    mid = bands[2] + bands[3]
    feature = [np.log(centroid + 1e-12), np.log(flatness + 1e-12),
               np.log((bands[0] + bands[1] + 1e-12) / (mid + 1e-12)),
               np.log((bands[4] + 1e-12) / (mid + 1e-12)),
               np.log((bands[5] + bands[6] + 1e-12) / (mid + 1e-12)), envpeak, envlag]
    crop_rms, crop_centroid, crop_distance, crop_envelope_peak = [], [], [], []
    for start in (0, 14000, 28000):
        crop = x[start:start + 32000]
        cp, cc, _, _ = spectral(crop)
        crop_rms.append(float(np.sqrt(np.mean(crop.astype(np.float64) ** 2))))
        crop_centroid.append(cc)
        crop_distance.append(float(np.sqrt(max(0., 1 - np.sqrt(p * cp).sum()))))
        ce = np.sqrt(np.mean(crop.reshape(-1, 80).astype(np.float64) ** 2, axis=1))
        crop_envelope_peak.append(acf_peak(ce, lo, min(hi, 3.9), 50)[0])
    return {"duration_seconds": x.size / SR, "rms": rms, "peak": peak,
            "crest_factor": peak / rms, "dc_to_rms": float(abs(x.mean()) / rms),
            "spectral_centroid_hz": centroid, "spectral_flatness": flatness,
            "band_energy_fractions": bands, "envelope_acf_peak": envpeak,
            "envelope_acf_lag_seconds": envlag, "waveform_acf_peak": rawpeak,
            "waveform_acf_lag_seconds": rawlag, "descriptor": feature,
            "crop_rms_max_min_db": float(20 * np.log10(max(crop_rms) / min(crop_rms))),
            "crop_centroid_max_min_hz": max(crop_centroid) - min(crop_centroid),
            "crop_psd_hellinger_max": max(crop_distance),
            "crop_envelope_acf_peaks": crop_envelope_peak}, p


def main():
    started = time.monotonic()
    rows = list(csv.DictReader(ALLOWLIST.open(newline="")))
    if len(rows) != 86 or any(r["split"] not in {"development", "validation"} for r in rows):
        raise ValueError("Expected the fixed 86-source non-test allowlist only")
    counts = Counter((r["kind"], r["split"]) for r in rows)
    if counts != {("HS", "development"): 36, ("HS", "validation"): 9,
                  ("LS", "development"): 36, ("LS", "validation"): 5}:
        raise ValueError("Unexpected non-test counts")
    data, psds, waveforms = [], [], []
    for row in rows:
        source = Source(row["kind"], row["id"], row["family"], row["split"],
                        row["sha256"], DATA_ROOT / row["kind"] / f"{row['id']}.wav")
        if sha256_file(source.path) != source.sha256:
            raise ValueError(f"Changed allowed source {source.id}")
        x = read_source(source)
        if x.size != 60000 or not np.isfinite(x).all():
            raise ValueError(f"Invalid allowed source {source.id}")
        description, psd = describe(x, source.kind)
        data.append({**row, **description})
        psds.append(psd)
        waveforms.append(x.astype(np.float64))
    psds = np.asarray(psds)
    groups = defaultdict(list)
    for i, row in enumerate(data):
        groups[(row["kind"], row["split"], row["family"])].append(i)
    numeric = ("rms", "peak", "crest_factor", "dc_to_rms", "spectral_centroid_hz", "spectral_flatness",
               "envelope_acf_peak", "envelope_acf_lag_seconds", "waveform_acf_peak",
               "waveform_acf_lag_seconds", "crop_rms_max_min_db", "crop_centroid_max_min_hz", "crop_psd_hellinger_max")
    family_summary = []
    for (kind, split, family), indices in sorted(groups.items()):
        family_summary.append({"kind": kind, "split": split, "family": family, "n": len(indices),
                               **{key: summary([data[i][key] for i in indices]) for key in numeric},
                               "mean_band_energy_fractions": np.mean([data[i]["band_energy_fractions"] for i in indices], axis=0).tolist()})
    # Similar PSD does not establish waveform duplication. Add separately a
    # bounded +/-2-second cross-correlation diagnostic, normalized by full energy.
    pairs = []
    for i, a in enumerate(data):
        for j in range(i + 1, len(data)):
            b = data[j]
            if a["kind"] != b["kind"]:
                continue
            bc = float(np.sqrt(psds[i] * psds[j]).sum())
            x, y = waveforms[i] - waveforms[i].mean(), waveforms[j] - waveforms[j].mean()
            cc = correlate(x, y, mode="full", method="fft")
            center = x.size - 1
            cc = cc[center - 8000:center + 8001] / np.sqrt(np.dot(x, x) * np.dot(y, y))
            k = int(np.argmax(np.abs(cc)))
            pairs.append({"kind": a["kind"], "source_a": a["id"], "source_b": b["id"],
                          "family_a": a["family"], "family_b": b["family"],
                          "same_family": a["family"] == b["family"], "psd_bhattacharyya": bc,
                          "waveform_max_abs_xcorr": float(abs(cc[k])), "lag_seconds": (k - 8000) / SR})
    pair_summary = {}
    for kind in ("HS", "LS"):
        for same in (True, False):
            chosen = [p for p in pairs if p["kind"] == kind and p["same_family"] == same]
            pair_summary[f"{kind}_{'within' if same else 'between'}_family"] = {
                "n_pairs": len(chosen),
                **{field: summary([p[field] for p in chosen]) for field in ("psd_bhattacharyya", "waveform_max_abs_xcorr")},
                "count_waveform_corr_ge_0_95": sum(p["waveform_max_abs_xcorr"] >= .95 for p in chosen),
                "count_waveform_corr_ge_0_8": sum(p["waveform_max_abs_xcorr"] >= .8 for p in chosen)}
    # Development-only mean/std, separately by source kind. No validation fit.
    distances = []
    for kind in ("HS", "LS"):
        dev = [i for i, r in enumerate(data) if r["kind"] == kind and r["split"] == "development"]
        values = np.asarray([r["descriptor"] for r in data])
        mean, std = values[dev].mean(axis=0), values[dev].std(axis=0)
        z = (values - mean) / np.maximum(std, 1e-8)
        for dimensions, name in ((5, "spectral_shape"), (7, "spectral_temporal")):
            centroids = {family: np.mean(z[ids, :dimensions], axis=0) for (k, split, family), ids in groups.items() if k == kind}
            dev_names = sorted({data[i]["family"] for i in dev})
            for (k, split, family), ids in sorted(groups.items()):
                if k != kind:
                    continue
                comparison = [f for f in dev_names if f != family]
                d = {f: float(np.linalg.norm(centroids[family] - centroids[f]) / np.sqrt(dimensions)) for f in comparison}
                nearest = min(d, key=d.get)
                nearest_source = []
                for i in ids:
                    candidates = [j for j in dev if data[j]["family"] != family]
                    nearest_source.append(min(float(np.linalg.norm(z[i, :dimensions] - z[j, :dimensions]) / np.sqrt(dimensions)) for j in candidates))
                distances.append({"kind": kind, "split": split, "family": family, "descriptor": name,
                                  "nearest_development_family": nearest, "family_centroid_distance": d[nearest],
                                  "all_development_family_distances": d, "nearest_cross_family_source_distance": summary(nearest_source)})
    overlaps = []
    for (hk, hs, hf), hi in sorted(groups.items()):
        if hk != "HS":
            continue
        for (lk, ls, lf), li in sorted(groups.items()):
            if lk != "LS":
                continue
            bc = [float(np.sqrt(psds[h] * psds[l]).sum()) for h in hi for l in li]
            overlap = [float(np.minimum(psds[h], psds[l]).sum()) for h in hi for l in li]
            overlaps.append({"heart_family": hf, "heart_split": hs, "lung_family": lf, "lung_split": ls,
                             "source_pair_count": len(bc), "psd_bhattacharyya": summary(bc),
                             "psd_histogram_intersection": summary(overlap)})
    result = {"status": "DIAGNOSTIC_ONLY_NON_TEST", "allowlist_sha256": sha256_file(ALLOWLIST),
              "script_sha256": sha256_file(Path(__file__)), "source_count": len(data),
              "duration_total_seconds": sum(r["duration_seconds"] for r in data),
              "unique_audio_hashes": len({r["sha256"] for r in data}),
              "counts": {f"{k}_{s}": n for (k, s), n in counts.items()},
              "feature_definition": {"welch": "Hann,1024 samples,512 overlap,nfft2048,detrend constant,normalized PSD excludes DC",
                                     "bands_hz": BANDS, "distance_features": FEATURES,
                                     "distance_scaling": "development-only mean/std by kind; Euclidean/sqrt(dimensions)",
                                     "acf": "biased finite-record; strongest local peak in HS .2-3s or LS .5-6s, not validated physiological rate",
                                     "crop_offsets_samples": [0, 14000, 28000], "crop_length_samples": 32000},
              "families": family_summary, "pair_similarity": pair_summary,
              "highest_waveform_correlations": sorted(pairs, key=lambda p: p["waveform_max_abs_xcorr"], reverse=True)[:20],
              "family_distances": distances, "heart_lung_spectral_overlap": overlaps,
              "runtime_seconds": time.monotonic() - started,
              "test_audio_opened": False, "training_performed": False,
              "caveats": ["Files are manikin/location/sex-labelled recordings, not verified independent subjects.",
                          "Feature similarity neither establishes duplication nor quantifies effective sample size.",
                          "Distances are descriptive and depend on these interpretable feature choices; no inferential p-values.",
                          "ACF peaks are finite-record repeated-pattern proxies, not clinical heart/respiratory rates.",
                          "Pooled spectral overlap does not prove instantaneous identifiability or irreducible error."]}
    OUT.mkdir(parents=True, exist_ok=True)
    for name, obj in (("sources_summary.json", result), ("sources_rows.json", data)):
        path = OUT / name
        path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"source_count": len(data), "runtime_seconds": result["runtime_seconds"], "output": str(OUT / 'sources_summary.json')}))


if __name__ == "__main__":
    main()
