"""Bounded, read-only design probe; not a separation-quality benchmark.

Run from the implementation root with a Python environment containing NumPy:
    python scripts/probe_ensemble_contract.py
Uses one synthetic signal and the first three existing manikin triples only.
No DB, model checkpoint, output audio, training, network or production access.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ml.audio_utils import AudioData, istft, stft
from app.ml.strategies.base import StrategyContext
from app.ml.strategies.fixed_filter_strategy import FixedFilterSeparationStrategy
from app.ml.strategies.nmf_strategy import NmfSeparationStrategy


def pcm16(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 4000)
        return np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float64) / 32768


def main() -> None:
    t = np.arange(8000, dtype=np.float32) / 4000
    x = (0.2 * np.cos(2 * np.pi * 80 * t) + 0.1 * np.cos(2 * np.pi * 500 * t)).astype(np.float32)
    audio = AudioData(x, 4000, 4000, 1, 2.0)
    context = StrategyContext(None, None, "cpu")
    report = {"classification": "OFFLINE SYNTHETIC / MANIKIN DESIGN PROBE", "numpy": np.__version__}
    report["synthetic"] = {}
    for strategy in (FixedFilterSeparationStrategy(), NmfSeparationStrategy()):
        start = time.perf_counter()
        output = strategy.separate_waveform(audio, context)
        report["synthetic"][strategy.strategy_key] = {
            "shape": [len(output.heart), len(output.lung)],
            "finite": bool(np.isfinite(output.heart).all() and np.isfinite(output.lung).all()),
            "sample_rate": output.sample_rate_hz,
            "elapsed_seconds_one_uncontrolled_run": round(time.perf_counter() - start, 6),
            "reconstruction_max_abs": float(np.max(np.abs(output.heart + output.lung - x))),
        }
    transform = stft(x, 4000)
    reconstructed = istft(transform, transform.spectrum)
    report["legacy_stft_roundtrip"] = {
        "first_input": float(x[0]), "first_output": float(reconstructed[0]),
        "max_abs_error": float(np.max(np.abs(reconstructed - x))),
    }
    root = ROOT / "datasets/hls_cmds"
    with (root / "metadata/Mix.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))[:3]
    report["manikin_triples_not_quality_scores"] = []
    for row in rows:
        ids = [row[k] for k in ("Mixed Sound ID", "Heart Sound ID", "Lung Sound ID")]
        paths = [root / "raw/Mix" / f"{key}.wav" for key in ids]
        mixed, heart, lung = map(pcm16, paths)
        # A same-time least-squares check is a diagnostic, NOT an alignment repair.
        sources = np.column_stack((heart, lung))
        gains = np.linalg.lstsq(sources, mixed, rcond=None)[0]
        residual = mixed - sources @ gains
        report["manikin_triples_not_quality_scores"].append({
            "ids": ids,
            "sha256": [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths],
            "samples": len(mixed),
            "relative_residual_norm_after_two_gain_fit": float(np.linalg.norm(residual) / np.linalg.norm(mixed)),
        })
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
