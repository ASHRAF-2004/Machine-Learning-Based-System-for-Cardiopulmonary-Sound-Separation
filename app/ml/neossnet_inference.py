"""NeoSSNet inference wrapper used by the backend service."""

from __future__ import annotations

import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.database.db import PROJECT_ROOT


VENDORED_NEOSSNET_SOURCE_DIR = PROJECT_ROOT / "app" / "ml" / "neossnet_source"
EXTERNAL_NEOSSNET_SOURCE_DIR = PROJECT_ROOT / "external" / "neossnet_source"
REFERENCE_NEOSSNET_SOURCE_DIR = (
    PROJECT_ROOT
    / "external"
    / "Neonatal-Chest-Sound-Separation-using-Deep-Learning-main"
)
NEOSSNET_SOURCE_DIR = (
    VENDORED_NEOSSNET_SOURCE_DIR
    if VENDORED_NEOSSNET_SOURCE_DIR.is_dir()
    else (
        REFERENCE_NEOSSNET_SOURCE_DIR
        if REFERENCE_NEOSSNET_SOURCE_DIR.is_dir()
        else EXTERNAL_NEOSSNET_SOURCE_DIR
    )
)
MODEL_SAMPLE_RATE = 4000


@dataclass(frozen=True)
class NeoSSNetInferenceResult:
    heart_file_path: Path
    lung_file_path: Path
    sample_rate_hz: int
    duration_sec: float
    heart_file_size_bytes: int
    lung_file_size_bytes: int
    input_shape: tuple[int, ...]
    output_shape: tuple[int, ...]
    input_min: float
    input_max: float
    input_rms: float
    heart_min: float
    heart_max: float
    heart_rms: float
    lung_min: float
    lung_max: float
    lung_rms: float
    checkpoint_path: Path
    config_path: Path
    bandpass_enabled: bool


_MODEL_CACHE: dict[tuple[str, float, str, float, str], Any] = {}


def add_neossnet_source_to_path() -> None:
    source_dir = str(NEOSSNET_SOURCE_DIR)
    if source_dir not in sys.path:
        sys.path.insert(0, source_dir)


def ensure_required_files(model_path: Path, model_config_path: Path) -> None:
    required_paths = [
        NEOSSNET_SOURCE_DIR / "utils" / "__init__.py",
        NEOSSNET_SOURCE_DIR / "models" / "__init__.py",
        model_path,
        model_config_path,
    ]
    for path in required_paths:
        if not path.exists():
            try:
                display_path = path.relative_to(PROJECT_ROOT)
            except ValueError:
                display_path = path
            raise FileNotFoundError(
                f"Required NeoSSNet file is missing: {display_path}"
            )

    if model_path.stat().st_size == 0:
        try:
            display_path = model_path.relative_to(PROJECT_ROOT)
        except ValueError:
            display_path = model_path
        raise ValueError(f"NeoSSNet checkpoint is empty: {display_path}")


def _tensor_stats(waveform) -> dict[str, float]:
    import torch

    waveform = waveform.detach().cpu().to(dtype=torch.float32)
    return {
        "min": float(torch.min(waveform).item()) if waveform.numel() else 0.0,
        "max": float(torch.max(waveform).item()) if waveform.numel() else 0.0,
        "rms": float(torch.sqrt(torch.mean(torch.square(waveform))).item())
        if waveform.numel()
        else 0.0,
    }


def load_neossnet_model_cached(
    model_path: Path,
    model_config_path: Path,
    device_name: str,
):
    add_neossnet_source_to_path()

    import torch
    from utils import load_model

    model_path = model_path.resolve()
    model_config_path = model_config_path.resolve()
    device = torch.device(device_name)
    cache_key = (
        str(model_path),
        model_path.stat().st_mtime,
        str(model_config_path),
        model_config_path.stat().st_mtime,
        str(device),
    )
    model = _MODEL_CACHE.get(cache_key)
    if model is None:
        model = load_model(
            model_path=str(model_path),
            model_config=str(model_config_path),
            device=device,
        )
        model.eval()
        _MODEL_CACHE.clear()
        _MODEL_CACHE[cache_key] = model
    return model, device


def load_wav_for_neossnet(input_path: Path):
    """Load WAV as mono float32 tensor shaped (1, T), resampled to 4000 Hz.

    This mirrors the standalone inference test: WAV decoding uses Python's
    standard wave module, samples are normalized to [-1, 1], stereo audio is
    averaged to mono, and the model receives a single-channel waveform.
    """
    import numpy as np
    import torch

    with wave.open(str(input_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()
        raw_audio = wav_file.readframes(frame_count)

    if sample_width == 1:
        audio = np.frombuffer(raw_audio, dtype=np.uint8).astype(np.float32)
        audio = (audio - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32)
        audio = audio / 32768.0
    elif sample_width == 3:
        audio_bytes = np.frombuffer(raw_audio, dtype=np.uint8).reshape(-1, 3)
        sign_byte = (audio_bytes[:, 2] >= 128).astype(np.uint8) * 255
        audio_32 = np.column_stack([audio_bytes, sign_byte]).reshape(-1, 4)
        audio = audio_32.view(np.int32).reshape(-1).astype(np.float32)
        audio = audio / 8388608.0
    elif sample_width == 4:
        audio = np.frombuffer(raw_audio, dtype=np.int32).astype(np.float32)
        audio = audio / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width} bytes")

    waveform = torch.from_numpy(audio.reshape(-1, channels).T.copy())

    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    if sample_rate != MODEL_SAMPLE_RATE:
        target_length = round(waveform.shape[-1] * MODEL_SAMPLE_RATE / sample_rate)
        waveform = torch.nn.functional.interpolate(
            waveform.unsqueeze(0),
            size=target_length,
            mode="linear",
            align_corners=False,
        ).squeeze(0)
        sample_rate = MODEL_SAMPLE_RATE

    max_abs = torch.max(torch.abs(waveform))
    if max_abs > 0:
        waveform = waveform / max_abs

    return waveform.to(dtype=torch.float32), sample_rate


def save_mono_wav(path: Path, waveform, sample_rate: int) -> None:
    import numpy as np
    import torch

    path.parent.mkdir(parents=True, exist_ok=True)
    waveform = waveform.detach().cpu().to(dtype=torch.float32)
    waveform = torch.clamp(waveform, min=-1.0, max=1.0)

    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)

    max_abs = torch.max(torch.abs(waveform))
    if max_abs > 0.95:
        waveform = waveform / max_abs * 0.95

    audio = waveform.squeeze(0).numpy()
    audio_i16 = (audio * 32767.0).astype(np.int16)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_i16.tobytes())


def run_neossnet_inference(
    input_wav_path: Path,
    model_path: Path,
    model_config_path: Path,
    heart_output_path: Path,
    lung_output_path: Path,
    device_name: str = "cpu",
    bandpass: bool = False,
) -> NeoSSNetInferenceResult:
    ensure_required_files(model_path, model_config_path)

    import torch

    input_wav, sample_rate = load_wav_for_neossnet(input_wav_path)
    input_stats = _tensor_stats(input_wav)
    model, device = load_neossnet_model_cached(model_path, model_config_path, device_name)
    input_batch = input_wav.unsqueeze(0).to(device)
    if bandpass:
        from utils import bandpass_filter

        input_batch = bandpass_filter(input_batch, 0.0125, 0.25, 51)

    with torch.inference_mode():
        output = model(input_batch)[:, 0:2, :]
        heart_wav = output[0, 0, :].detach()
        lung_wav = output[0, 1, :].detach()

    heart_stats = _tensor_stats(heart_wav)
    lung_stats = _tensor_stats(lung_wav)

    save_mono_wav(heart_output_path, heart_wav, sample_rate)
    save_mono_wav(lung_output_path, lung_wav, sample_rate)

    frame_count = int(heart_wav.numel())
    return NeoSSNetInferenceResult(
        heart_file_path=heart_output_path,
        lung_file_path=lung_output_path,
        sample_rate_hz=sample_rate,
        duration_sec=frame_count / sample_rate if sample_rate else 0.0,
        heart_file_size_bytes=heart_output_path.stat().st_size,
        lung_file_size_bytes=lung_output_path.stat().st_size,
        input_shape=tuple(input_wav.shape),
        output_shape=tuple(output.shape),
        input_min=input_stats["min"],
        input_max=input_stats["max"],
        input_rms=input_stats["rms"],
        heart_min=heart_stats["min"],
        heart_max=heart_stats["max"],
        heart_rms=heart_stats["rms"],
        lung_min=lung_stats["min"],
        lung_max=lung_stats["max"],
        lung_rms=lung_stats["rms"],
        checkpoint_path=model_path,
        config_path=model_config_path,
        bandpass_enabled=bandpass,
    )
