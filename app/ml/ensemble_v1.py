"""Offline-only, fixed-weight two-expert separation qualification.

No API or production job path imports this module. The source adapters return
raw float arrays; they deliberately bypass the legacy per-file WAV gain cap.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.ml.audio_utils import AudioData, frequency_mask_split, istft, stft
from app.ml.strategies.base import SeparatedWaveforms, StrategyContext
from app.ml.strategies.nmf_strategy import NmfSeparationStrategy

SAMPLE_RATE = 4000
PROJECT_ROOT = Path(__file__).resolve().parents[2]
NEOSSNET_SOURCE_DIR = PROJECT_ROOT / "app/ml/neossnet_source"
WINDOW = 40000
HOP = 32000
OVERLAP = WINDOW - HOP
VERSION = "stethofuse-tfmask-v1"
PREPROCESSING_VERSION = "hls-4k-pcm-original-v1"
WEIGHTS_SHA256 = "abf4f05321d7c0a9da0ee25bfe50f0dbb5736d5f855150787009b4221f947358"
CONFIG_SHA256 = "b7d82e7fb9cbcbd7382d6eadb69220fba5c7d25cafd5bbfdb83f714ca39d5096"


class EnsembleError(RuntimeError):
    """The required two-expert run failed; no fallback is permitted."""

    def __init__(self, code: str, provenance: dict[str, object] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.provenance = provenance or {}


@dataclass(frozen=True)
class EnsembleRun:
    heart: np.ndarray
    lung: np.ndarray
    controls: dict[str, tuple[np.ndarray, np.ndarray]]
    provenance: dict[str, object]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonicalize(waveform: np.ndarray, sample_rate: int) -> np.ndarray:
    """Mono digital-full-scale float32; anti-aliased rate conversion if needed."""
    audio = np.asarray(waveform)
    if audio.ndim == 2:
        audio = audio.astype(np.float64).mean(axis=0)
    if audio.ndim != 1 or audio.size == 0 or sample_rate <= 0:
        raise EnsembleError("invalid_input_shape_or_rate")
    if not np.all(np.isfinite(audio)):
        raise EnsembleError("nonfinite_input")
    original_length = audio.size
    if sample_rate != SAMPLE_RATE:
        from scipy.signal import resample_poly

        divisor = math.gcd(sample_rate, SAMPLE_RATE)
        audio = resample_poly(
            audio.astype(np.float64), SAMPLE_RATE // divisor, sample_rate // divisor,
            window=("kaiser", 5.0), padtype="constant",
        )
        expected = math.ceil(original_length * SAMPLE_RATE / sample_rate)
        if audio.size != expected:
            raise EnsembleError("resample_length_mismatch")
    return np.asarray(audio, dtype=np.float32)


def _validate_output(output: SeparatedWaveforms, length: int, expert: str) -> None:
    if output.sample_rate_hz != SAMPLE_RATE:
        raise EnsembleError(f"{expert}_wrong_sample_rate")
    for label, component in (("heart", output.heart), ("lung", output.lung)):
        if not isinstance(component, np.ndarray) or component.ndim != 1 or component.size != length:
            raise EnsembleError(f"{expert}_{label}_wrong_shape")
        if not np.all(np.isfinite(component)):
            raise EnsembleError(f"{expert}_{label}_nonfinite")
    if max(float(np.max(np.abs(output.heart))), float(np.max(np.abs(output.lung)))) < 1e-8:
        raise EnsembleError(f"{expert}_both_outputs_silent")


class NeoSSNetExpert:
    id = "neossnet_released"

    def __init__(self, device: str = "cpu") -> None:
        import torch
        import yaml

        weights = PROJECT_ROOT / "storage/ml_models/model_best.pt"
        config_path = PROJECT_ROOT / "storage/ml_models/model.yaml"
        if _sha256(weights) != WEIGHTS_SHA256 or _sha256(config_path) != CONFIG_SHA256:
            raise EnsembleError("neossnet_checkpoint_or_config_mismatch")
        if str(NEOSSNET_SOURCE_DIR) not in sys.path:
            sys.path.insert(0, str(NEOSSNET_SOURCE_DIR))
        from models import MaskNet

        self.torch = torch
        self.device = device
        with config_path.open() as stream:
            config = yaml.safe_load(stream)
        self.model = MaskNet(**config).to(device)
        state = torch.load(weights, map_location=device, weights_only=True)
        self.model.load_state_dict(state, strict=True)
        self.model.eval()

    def separate(self, window: np.ndarray) -> SeparatedWaveforms:
        torch = self.torch
        tensor = torch.from_numpy(window.copy()).view(1, 1, -1).to(self.device)
        with torch.inference_mode():
            output = self.model(tensor)
        if tuple(output.shape) != (1, 2, window.size):
            raise EnsembleError("neossnet_wrong_shape")
        arrays = output[0].detach().cpu().numpy().astype(np.float32, copy=False)
        return SeparatedWaveforms(arrays[0], arrays[1], SAMPLE_RATE, {"checkpoint_sha256": WEIGHTS_SHA256})


class GenericNMFExpert:
    id = "generic_nmf"

    def __init__(self) -> None:
        self.strategy = NmfSeparationStrategy(n_components=6, iterations=80, random_seed=42)

    def separate(self, window: np.ndarray) -> SeparatedWaveforms:
        audio = AudioData(window, SAMPLE_RATE, SAMPLE_RATE, 1, window.size / SAMPLE_RATE)
        return self.strategy.separate_waveform(audio, StrategyContext(None, None, "cpu"))


def _expert_mask(heart: np.ndarray, lung: np.ndarray) -> np.ndarray:
    ah = np.abs(stft(heart, SAMPLE_RATE).spectrum)
    al = np.abs(stft(lung, SAMPLE_RATE).spectrum)
    denominator = ah + al
    epsilon = max(1e-12, 1e-8 * float(np.max(denominator)))
    mask = np.full(denominator.shape, 0.5, dtype=np.float64)
    np.divide(ah, denominator, out=mask, where=denominator > epsilon)
    if not np.all(np.isfinite(mask)) or float(np.min(mask)) < 0 or float(np.max(mask)) > 1:
        raise EnsembleError("invalid_expert_mask")
    return mask


def fuse_window(
    mixture: np.ndarray,
    neo: SeparatedWaveforms,
    nmf: SeparatedWaveforms,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Project raw expert magnitudes and their equal-weight mask onto mixture phase."""
    transform = stft(mixture, SAMPLE_RATE, n_fft=1024, hop_length=256)
    neo_mask = _expert_mask(neo.heart, neo.lung)
    nmf_mask = _expert_mask(nmf.heart, nmf.lung)
    fused_mask = 0.5 * neo_mask + 0.5 * nmf_mask

    def project(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return istft(transform, mask * transform.spectrum), istft(transform, (1.0 - mask) * transform.spectrum)

    return {
        "neossnet_raw": (neo.heart, neo.lung),
        "neossnet_projected": project(neo_mask),
        "nmf_raw": (nmf.heart, nmf.lung),
        "nmf_projected": project(nmf_mask),
        "ensemble": project(fused_mask),
    }


def _window_weights(start: int, size: int, total: int) -> np.ndarray:
    weights = np.ones(size, dtype=np.float64)
    if start > 0:
        weights[:OVERLAP] = 0.5 - 0.5 * np.cos(np.pi * np.arange(OVERLAP) / OVERLAP)
    if start + size < total:
        weights[-OVERLAP:] = 0.5 + 0.5 * np.cos(np.pi * np.arange(OVERLAP) / OVERLAP)
    return weights


class EnsembleEngine:
    """Single-run offline engine; both qualified experts are mandatory."""

    def __init__(self, neo: NeoSSNetExpert, nmf: GenericNMFExpert) -> None:
        self.neo = neo
        self.nmf = nmf

    def separate(self, mixture: np.ndarray, *, recording_id: str = "offline") -> EnsembleRun:
        x = canonicalize(mixture, SAMPLE_RATE)
        if x.size > 120 * SAMPLE_RATE:
            raise EnsembleError("processing_duration_cap")
        if float(np.sqrt(np.mean(np.square(x.astype(np.float64))))) < 1e-6:
            raise EnsembleError("silent_input")
        gain = float(np.max(np.abs(x)))
        u = x / gain
        # Fixed-hop windows and known zero padding, including a final short window.
        starts = list(range(0, x.size, HOP))
        if len(starts) > 1 and starts[-1] + OVERLAP >= x.size:
            starts.pop()
        names = ("neossnet_raw", "neossnet_projected", "nmf_raw", "nmf_projected", "fixed_filter", "ensemble")
        sums = {name: (np.zeros(x.size, dtype=np.float64), np.zeros(x.size, dtype=np.float64)) for name in names}
        coverage = np.zeros(x.size, dtype=np.float64)
        timings = {"neossnet_ms": 0.0, "nmf_ms": 0.0}
        silent_windows = 0
        completed_windows = 0
        started = time.perf_counter()
        started_at_utc = datetime.now(timezone.utc).isoformat()
        try:
            for start in starts:
                end = min(x.size, start + WINDOW)
                valid = end - start
                window = np.pad(u[start:end], (0, WINDOW - valid))
                weights = _window_weights(start, WINDOW, x.size)[:valid]
                if float(np.sqrt(np.mean(window.astype(np.float64) ** 2))) < 1e-6:
                    outputs = {name: (np.zeros(WINDOW, dtype=np.float32), np.zeros(WINDOW, dtype=np.float32)) for name in names}
                    silent_windows += 1
                else:
                    tic = time.perf_counter()
                    neo = self.neo.separate(window)
                    timings["neossnet_ms"] += 1000 * (time.perf_counter() - tic)
                    _validate_output(neo, WINDOW, self.neo.id)
                    tic = time.perf_counter()
                    nmf = self.nmf.separate(window)
                    timings["nmf_ms"] += 1000 * (time.perf_counter() - tic)
                    _validate_output(nmf, WINDOW, self.nmf.id)
                    outputs = fuse_window(window, neo, nmf)
                    fixed_heart, fixed_lung, _ = frequency_mask_split(window, SAMPLE_RATE)
                    outputs["fixed_filter"] = (fixed_heart, fixed_lung)
                coverage[start:end] += weights
                for name in names:
                    sums[name][0][start:end] += np.asarray(outputs[name][0][:valid], dtype=np.float64) * weights
                    sums[name][1][start:end] += np.asarray(outputs[name][1][:valid], dtype=np.float64) * weights
                completed_windows += 1
        except Exception as exc:
            code = exc.code if isinstance(exc, EnsembleError) else type(exc).__name__
            failure = {"schema_version": 1, "ensemble_version": VERSION,
                       "recording_id": recording_id, "status": "failed_offline",
                       "failure_events": [{"code": code}], "fallback_events": [],
                       "completed_windows": completed_windows}
            raise EnsembleError(f"required_expert_or_fusion_failed:{code}", failure) from exc
        if np.any(coverage <= 0):
            raise EnsembleError("window_coverage_gap")
        results = {
            name: ((heart / coverage * gain).astype(np.float32), (lung / coverage * gain).astype(np.float32))
            for name, (heart, lung) in sums.items()
        }
        for name, (heart, lung) in results.items():
            if not np.all(np.isfinite(heart)) or not np.all(np.isfinite(lung)):
                raise EnsembleError(f"{name}_nonfinite_result")
        config = {"version": VERSION, "weights": [0.5, 0.5], "fft": 1024, "hop": 256,
                  "window": WINDOW, "window_hop": HOP, "nmf_components": 6,
                  "nmf_iterations": 80, "seed": 42}
        code_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        provenance = {
            "schema_version": 1, "ensemble_version": VERSION, "preprocessing_version": PREPROCESSING_VERSION,
            "recording_id": recording_id, "sample_rate_hz": SAMPLE_RATE, "length": x.size,
            "input_sha256": hashlib.sha256(x.tobytes()).hexdigest(),
            "input_gain": gain, "window_count": len(starts), "silent_windows": silent_windows,
            "config": config, "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
            "checkpoint_sha256": WEIGHTS_SHA256, "model_config_sha256": CONFIG_SHA256,
            "experts": [
                {"id": self.neo.id, "adapter_version": 1, "upstream_commit": "d97886b93bd2e71fd019c6b5073bb2dce2854ade",
                 "checkpoint_sha256": WEIGHTS_SHA256, "config_sha256": CONFIG_SHA256},
                {"id": self.nmf.id, "adapter_version": 1, "components": 6, "iterations": 80, "seed": 42},
            ],
            "code_commit": code_commit, "engine_source_sha256": _sha256(Path(__file__)),
            "requirements_sha256": _sha256(PROJECT_ROOT / "requirements.txt"),
            "device": self.neo.device, "library_versions": {"numpy": np.__version__,
                "torch": self.neo.torch.__version__ if hasattr(self.neo, "torch") else "controlled_test"},
            "timings_ms": timings, "started_at_utc": started_at_utc,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_runtime_ms": 1000 * (time.perf_counter() - started),
            "failure_events": [], "fallback_events": [], "output_artifact_ids": [],
            "status": "succeeded_offline",
        }
        return EnsembleRun(results["ensemble"][0], results["ensemble"][1],
                           {name: results[name] for name in names if name != "ensemble"}, provenance)
