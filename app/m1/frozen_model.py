"""Load the immutable T8 v2 once. No training, model selection, or fallback."""
from __future__ import annotations

import hashlib
import io
import json
import platform
import time
import wave
from pathlib import Path

import numpy as np
import scipy
import torch
import torchaudio

from app.ml.audio_utils import _decode_pcm
from app.ml.ensemble_v1 import canonicalize, PREPROCESSING_VERSION
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from .config import PROJECT_ROOT
from .ml_contract import (ARCHITECTURE_VERSION, CHECKPOINT_SHA256, MODEL_VERSION,
                          PARAMETER_COUNT, SPEC_SHA256, ProcessingError)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FrozenSeparator:
    def __init__(self, checkpoint: Path, specification: Path):
        started = time.perf_counter()
        try:
            spec_bytes = specification.read_bytes()
            checkpoint_bytes = checkpoint.read_bytes()
        except OSError:
            raise ProcessingError("model_artifact_unavailable") from None
        if digest(spec_bytes) != SPEC_SHA256 or digest(checkpoint_bytes) != CHECKPOINT_SHA256:
            raise ProcessingError("model_artifact_hash_mismatch")
        self.spec = json.loads(spec_bytes)
        # Protect the exact inference and approved canonicalization helpers too.
        for relative, expected in {
            "app/ml/stethofuse_tcn.py": self.spec["model"]["inference_source_sha256"],
            "app/ml/ensemble_v1.py": self.spec["t9_protocol"]["frozen_code_sources"]["generic_nmf"]["sha256"],
            "app/ml/audio_utils.py": self.spec["t9_protocol"]["frozen_code_sources"]["fixed_filter"]["sha256"],
        }.items():
            if digest((PROJECT_ROOT / relative).read_bytes()) != expected:
                raise ProcessingError("frozen_inference_source_mismatch")
        self.environment = {"python": platform.python_version(), "torch": torch.__version__,
                            "torchaudio": torchaudio.__version__, "numpy": np.__version__,
                            "scipy": scipy.__version__, "device": "cpu"}
        if any(self.environment[k] != self.spec["environment"][k] for k in self.environment):
            raise ProcessingError("model_environment_mismatch")
        torch.set_num_threads(2)
        if torch.get_num_interop_threads() != 1:
            torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        try:
            self.model = StethoFuseConvTasNet(ARCHITECTURE_VERSION)
            # This exact owner-produced artifact was verified above before deserialization.
            payload = torch.load(io.BytesIO(checkpoint_bytes), map_location="cpu", weights_only=False)
            if payload["architecture_version"] != ARCHITECTURE_VERSION or payload["parameter_count"] != PARAMETER_COUNT:
                raise ValueError("Unexpected architecture")
            self.model.load_state_dict(payload["state_dict"], strict=True)
            self.model.eval()
            self.model.requires_grad_(False)
            if self.model.parameter_count != PARAMETER_COUNT:
                raise ValueError("Unexpected parameter count")
        except Exception:
            raise ProcessingError("model_load_failed") from None
        self.load_seconds = time.perf_counter() - started
        self.load_count = 1

    @staticmethod
    def decode(payload: bytes) -> tuple[np.ndarray, dict]:
        try:
            with wave.open(io.BytesIO(payload), "rb") as wav:
                channels, rate, width, frames = (wav.getnchannels(), wav.getframerate(),
                                                 wav.getsampwidth(), wav.getnframes())
                if (wav.getcomptype() != "NONE" or channels not in (1, 2) or width not in (1, 2, 3, 4)
                        or not 1000 <= rate <= 192000 or frames <= 0 or frames / rate > 1800):
                    raise ValueError("Unsupported PCM")
                raw = wav.readframes(frames)
                if len(raw) != frames * channels * width:
                    raise ValueError("Truncated PCM")
            # Existing decoder and canonicalizer, without the legacy peak cap.
            samples = _decode_pcm(raw, width).reshape(-1, channels).T
            canonical = canonicalize(samples, rate)
            if not np.isfinite(canonical).all():
                raise ValueError("Nonfinite canonical input")
        except Exception:
            raise ProcessingError("invalid_audio") from None
        return canonical, {"original_sample_rate": rate, "original_channels": channels,
                           "original_pcm_bits": width * 8, "original_frames": frames,
                           "canonical_sample_count": len(canonical),
                           "canonical_input_sha256": digest(canonical.astype("<f4").tobytes()),
                           "preprocessing_version": PREPROCESSING_VERSION,
                           "resampling": "scipy.resample_poly; gcd ratio; Kaiser 5.0; constant padding; ceil length",
                           "channel_policy": "arithmetic mean; float32 mono; no gain cap"}

    def separate(self, canonical: np.ndarray) -> tuple[np.ndarray, float]:
        started = time.perf_counter()
        try:
            with torch.inference_mode():
                output = self.model.separate_recording(torch.from_numpy(canonical)).cpu().numpy()
            if output.shape != (2, len(canonical)) or not np.isfinite(output).all():
                raise ValueError("Invalid output")
        except Exception:
            raise ProcessingError("inference_failed") from None
        return output, time.perf_counter() - started

    def provenance(self) -> dict:
        return {"model_name": "Compact Conv-TasNet", "model_version": MODEL_VERSION,
                "architecture_version": ARCHITECTURE_VERSION, "parameter_count": PARAMETER_COUNT,
                "checkpoint_sha256": CHECKPOINT_SHA256, "separator_spec_sha256": SPEC_SHA256,
                "sample_rate": 4000, "inference_window_samples": 40000,
                "inference_window_seconds": 10, "inference_hop_samples": 32000,
                "inference_hop_seconds": 8, "inference_overlap_samples": 8000,
                "inference_overlap_seconds": 2, "output_semantic_order": ["heart", "lung"],
                "mixture_consistency_version": "equal-residual-per-window-v1",
                "amplitude_convention": self.spec["signal_and_inference"]["amplitude_convention"],
                "padding": self.spec["signal_and_inference"]["padding"],
                "projection": False, "ensemble": None, "runtime_device": "cpu",
                "output_format": "WAV IEEE float32 little-endian; mono; 4000 Hz; no clipping or output normalization",
                "environment": self.environment}
