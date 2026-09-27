"""Bounded DEVELOPMENT diagnosis, not neonatal/published-result reproduction.

Reuses only the four source files in the frozen Phase-D development manifest.
Six old mixtures + twelve author-protocol/no-noise manikin surrogates. No PIT,
per-record oracle alignment, weight tuning, training, or production access.
Outputs stay ignored; install fast-bss-eval==0.1.4 in the offline environment.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

import fast_bss_eval
import numpy as np
from scipy.signal import correlate, correlation_lags
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.audio_utils import istft, stft
from app.ml.ensemble_v1 import CONFIG_SHA256, WEIGHTS_SHA256, NeoSSNetExpert, _expert_mask
from scripts.evaluate_ensemble_qualification import controlled_mix, read_first_ten_seconds, si_sdr

OUT = ROOT / ".local/ensemble/reproduction"
MANIFEST = ROOT / ".local/ensemble/qualification/manifest.json"
AUTHOR = ROOT / "external/Neonatal-Chest-Sound-Separation-using-Deep-Learning-main"
SEED = 42


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independent_score(estimate, reference, zero_mean=True):
    # Loss variant fixes the source order. si_sdr() itself solves permutations.
    return float(-fast_bss_eval.si_sdr_loss(
        np.asarray(estimate, dtype=np.float64)[None],
        np.asarray(reference, dtype=np.float64)[None],
        zero_mean=zero_mean, pairwise=False,
    )[0])


def metric_audit():
    t = np.arange(4000, dtype=np.float64) / 4000
    ref, noise = np.sin(2 * np.pi * 80 * t), np.cos(2 * np.pi * 511 * t)
    estimate = ref + 0.2 * noise
    independent = independent_score(estimate, ref)
    # Orthogonal equal-energy sinusoids give an independent analytic 25:1 ratio.
    analytic = float(10 * np.log10(25))
    noisy = si_sdr(estimate, ref)
    assert abs(noisy - independent) < 1e-7 and abs(noisy - analytic) < 1e-7
    assert abs(si_sdr(-3 * estimate, ref) - noisy) < 1e-7
    assert si_sdr(ref, ref) > 100
    assert si_sdr(noise, ref) < -100
    before = ref.copy()
    si_sdr(estimate, ref)
    assert np.array_equal(ref, before)
    rejected = 0
    for est, target in ((np.zeros_like(ref), ref), (estimate, np.zeros_like(ref))):
        try:
            si_sdr(est, target)
        except RuntimeError:
            rejected += 1
    assert rejected == 2
    # Show library API semantics on SYNTHETIC tones only; never PIT-score data.
    targets = np.stack((ref, noise))
    reversed_estimates = np.stack((noise + 0.01 * ref, ref + 0.01 * noise))
    pit, permutation = fast_bss_eval.si_sdr(targets, reversed_estimates, return_perm=True)
    fixed = -fast_bss_eval.si_sdr_loss(reversed_estimates, targets, pairwise=False)
    return {"status": "PASS", "identical_db": si_sdr(ref, ref),
            "analytic_db": analytic, "independent_db": independent, "ours_db": noisy,
            "unrelated_db": si_sdr(noise, ref), "silent_cases": "rejected_as_undefined",
            "synthetic_only_library_pit_db": pit.tolist(),
            "synthetic_only_library_permutation": permutation.tolist(),
            "synthetic_only_library_fixed_db": fixed.tolist()}


def statistics(x):
    x = np.asarray(x, dtype=np.float64)
    power = np.abs(np.fft.rfft(x - x.mean())) ** 2
    freq = np.fft.rfftfreq(x.size, 1 / 4000)
    return {"peak": float(np.max(np.abs(x))), "rms": float(np.sqrt(np.mean(x ** 2))),
            "mean": float(x.mean()), "exact_zero_fraction": float(np.mean(x == 0)),
            "at_or_above_fullscale": int(np.count_nonzero(np.abs(x) >= 1)),
            "energy_fraction_below_250hz": float(power[freq < 250].sum() / power.sum())}


def lag_diagnostic(estimate, reference):
    a, b = estimate.astype(np.float64), reference.astype(np.float64)
    a, b = a - a.mean(), b - b.mean()
    corr = correlate(a, b, mode="full", method="fft")
    lags = correlation_lags(a.size, b.size, mode="full")
    keep = np.abs(lags) <= 512
    chosen = int(np.argmax(np.abs(corr[keep])))
    return {"peak_lag_samples_within_128ms": int(lags[keep][chosen]),
            "signed_correlation_at_peak": float(corr[keep][chosen] /
                                                (np.linalg.norm(a) * np.linalg.norm(b)))}


def author_no_noise(heart, lung, ratio, convolutive, generator):
    """Published loader algebra, not copied code; no neonatal-data claim."""
    h, l = torch.from_numpy(heart.copy()), torch.from_numpy(lung.copy())
    filters = []
    if convolutive:
        for signal in (h, l):
            kernel = torch.rand(3, generator=generator)
            kernel /= torch.linalg.vector_norm(kernel)
            filters.append(kernel.tolist())
        h = torch.nn.functional.conv1d(h[None, None], torch.tensor(filters[0])[None, None], padding="same")[0, 0]
        l = torch.nn.functional.conv1d(l[None, None], torch.tensor(filters[1])[None, None], padding="same")[0, 0]
    eps = torch.finfo(h.dtype).eps
    gain = torch.sqrt((h.square().sum() + eps) / (l.square().sum() + eps)) * 10 ** (ratio / 20)
    mixed = h + gain * l
    peak = mixed.abs().max()
    # Save scaled references for exact additivity; SI-SDR ignores their gains.
    return (mixed / peak).numpy(), (h / peak).numpy(), (gain * l / peak).numpy(), {
        "lung_gain": float(gain), "common_gain": float(1 / peak), "filters": filters,
        "noise": "none", "disk_quantization": "none_float32_in_memory",
    }


def main():
    started = time.perf_counter()
    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True)
    manifest = json.loads(MANIFEST.read_text())
    allowed = {(s["kind"], s["id"]): s for s in manifest["source_splits"] if s["split"] == "development"}
    cache = {}
    for m in manifest["mixtures"]:
        for kind, source_id in (("HS", m["heart_id"]), ("LS", m["lung_id"])):
            if (kind, source_id) not in allowed:
                raise RuntimeError("Not a frozen development source")
            path = ROOT / "datasets/hls_cmds/raw" / kind / (source_id + ".wav")
            if digest(path) != allowed[(kind, source_id)]["sha256"]:
                raise RuntimeError("Source bytes changed")
            cache[(kind, source_id)] = read_first_ten_seconds({"path": path})
    expert = NeoSSNetExpert("cpu")
    state = torch.load(ROOT / "storage/ml_models/model_best.pt", weights_only=True, map_location="cpu")
    loaded = expert.model.load_state_dict(state, strict=True)
    parity = {p.name: digest(p) == digest(AUTHOR / "models" / p.name)
              for p in (ROOT / "app/ml/neossnet_source/models").glob("*.py")}
    assert all(parity.values()), "Diagnosis requires the author model forward behavior"
    model_evidence = {"checkpoint_sha256": WEIGHTS_SHA256, "config_sha256": CONFIG_SHA256,
                      "parameters": sum(p.numel() for p in expert.model.parameters()),
                      "missing_keys": loaded.missing_keys, "unexpected_keys": loaded.unexpected_keys,
                      "state_entries": len(state), "all_state_finite": all(torch.isfinite(v).all().item() for v in state.values()),
                      "training_modules": sum(m.training for m in expert.model.modules()),
                      "author_model_source_parity": parity, "torch": torch.__version__,
                      "device": "cpu", "cuda_available": torch.cuda.is_available()}
    rows = []

    def evaluate(case_id, cohort, mix, refs, metadata):
        unit = mix / np.max(np.abs(mix))
        tic = time.perf_counter()
        result = expert.separate(unit)
        runtime_ms = (time.perf_counter() - tic) * 1000
        output = np.stack((result.heart, result.lung))
        if not rows:
            repeated = expert.separate(unit)
            tensor = torch.from_numpy(unit.copy())[None, None]
            with torch.no_grad():
                direct = expert.model(tensor)[0].numpy()
            model_evidence.update({"shape": list(output.shape), "repeat_max_abs": float(np.max(np.abs(output - np.stack((repeated.heart, repeated.lung))))),
                                   "adapter_vs_author_no_grad_max_abs": float(np.max(np.abs(output - direct)))})
        assert output.shape == (2, 40000) and np.isfinite(output).all()
        reference = np.stack(refs)
        scores = {"documented": [si_sdr(output[i], reference[i]) for i in range(2)],
                  "globally_swapped": [si_sdr(output[1 - i], reference[i]) for i in range(2)]}
        baseline = [si_sdr(mix, r) for r in refs]
        transform = stft(unit, 4000)
        mask = _expert_mask(output[0], output[1])
        projected = np.stack((istft(transform, mask * transform.spectrum),
                              istft(transform, (1 - mask) * transform.spectrum)))
        row = {"id": case_id, "cohort": cohort, **metadata,
               "input_sha256": hashlib.sha256(unit.tobytes()).hexdigest(),
               "input": statistics(unit), "sources": [statistics(r) for r in refs],
               "source_correlation": float(np.corrcoef(reference)[0, 1]),
               "baseline_si_sdr_db": baseline, "si_sdr_db": scores,
               "si_sdri_db": {k: (np.array(v) - baseline).tolist() for k, v in scores.items()},
               "independent_fixed_db": [independent_score(output[i], reference[i]) for i in range(2)],
               "no_mean_removal_fixed_db": [independent_score(output[i], reference[i], False) for i in range(2)],
               "interior_only_fixed_db": [si_sdr(output[i, 512:-512], reference[i, 512:-512]) for i in range(2)],
               "lag_diagnostic_only": {k: [lag_diagnostic(output[j], reference[i]) for i, j in enumerate(order)]
                                       for k, order in (("documented", (0, 1)), ("globally_swapped", (1, 0)))},
               "projected_fixed_db": [si_sdr(projected[i], reference[i]) for i in range(2)],
               "raw_sum_relative_l2": float(np.linalg.norm(output.sum(0) - unit) / np.linalg.norm(unit)),
               "projected_sum_max_abs": float(np.max(np.abs(projected.sum(0) - unit))),
               "additivity_max_abs": float(np.max(np.abs(mix - reference.sum(0)))),
               "runtime_ms": runtime_ms}
        rows.append(row)

    for m in manifest["mixtures"]:
        h, l = cache[("HS", m["heart_id"])], cache[("LS", m["lung_id"])]
        mix, hr, lr, lg, cg = controlled_mix(h, l, m["ratio_db"])
        assert hashlib.sha256(mix.tobytes()).hexdigest() == m["mixture_sha256"]
        amix, _, _, _ = author_no_noise(h, l, m["ratio_db"], False, None)
        evaluate(m["id"], "phase_d_six", mix, (hr, lr), {
            "heart_id": m["heart_id"], "lung_id": m["lung_id"], "ratio_db": m["ratio_db"],
            "lung_gain": lg, "common_gain": cg,
            "author_normalized_input_max_abs_difference": float(np.max(np.abs(mix / np.max(np.abs(mix)) - amix))),
        })
    pairs = sorted({(m["heart_id"], m["lung_id"]) for m in manifest["mixtures"]})
    generator = torch.Generator().manual_seed(SEED)
    for h_id, l_id in pairs:
        for conv in (False, True):
            for ratio in (-10, 0, 10):
                mix, hr, lr, meta = author_no_noise(cache[("HS", h_id)], cache[("LS", l_id)], ratio, conv, generator)
                evaluate(f"surrogate-{h_id}-{l_id}-{int(conv)}-{ratio:+d}",
                         "author_protocol_manikin_surrogate", mix, (hr, lr), {
                             "heart_id": h_id, "lung_id": l_id, "ratio_db": ratio,
                             "convolutive": conv, **meta,
                         })
    summary = {}
    for cohort in sorted({r["cohort"] for r in rows}):
        selected = [r for r in rows if r["cohort"] == cohort]
        summary[cohort] = {"count": len(selected), "mapping": {
            mapping: {"mean_si_sdr_db": np.mean([r["si_sdr_db"][mapping] for r in selected], 0).tolist(),
                      "mean_si_sdri_db": np.mean([r["si_sdri_db"][mapping] for r in selected], 0).tolist(),
                      "median_si_sdr_db": np.median([r["si_sdr_db"][mapping] for r in selected], 0).tolist()}
            for mapping in ("documented", "globally_swapped")}}
    report = {"classification": "DEVELOPMENT_DIAGNOSTIC_NOT_NATIVE_REPRODUCTION_NOT_FINAL",
              "manifest_sha256": digest(MANIFEST), "script_sha256": digest(Path(__file__)),
              "code_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_ids_only": [list(k) for k in cache], "seed": SEED,
              "metric": metric_audit(), "model": model_evidence, "summary": summary, "rows": rows,
              "inference_failures": 0, "total_seconds": time.perf_counter() - started,
              "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diagnosis.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"metric": report["metric"], "model": model_evidence, "summary": summary,
                      "inference_failures": 0, "evidence": str(OUT / "diagnosis.json")}, indent=2))


if __name__ == "__main__":
    main()
