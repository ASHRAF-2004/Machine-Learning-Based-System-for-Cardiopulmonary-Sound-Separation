"""NeoSSNet inference wrapper used by the backend service."""

from __future__ import annotations

import sys
import wave
from dataclasses import dataclass
from pathlib import Path

from app.database.db import PROJECT_ROOT


NEOSSNET_SOURCE_DIR = PROJECT_ROOT / "external" / "neossnet_source"
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
            raise FileNotFoundError(f"Required NeoSSNet file is missing: {path}")

    if model_path.stat().st_size == 0:
        raise ValueError(f"NeoSSNet checkpoint is empty: {model_path}")


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
) -> NeoSSNetInferenceResult:
    ensure_required_files(model_path, model_config_path)
    add_neossnet_source_to_path()

    import torch
    from utils import generate_output

    input_wav, sample_rate = load_wav_for_neossnet(input_wav_path)
    device = torch.device(device_name)

    with torch.inference_mode():
        heart_wav, lung_wav = generate_output(
            input_wav=input_wav,
            model_path=str(model_path),
            model_config=str(model_config_path),
            device=device,
        )

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
        output_shape=(1, 2, frame_count),
    )
