"""Shared WAV loading, preprocessing, STFT, and output helpers."""

from __future__ import annotations

import math
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np


EPS = 1e-10


@dataclass(frozen=True)
class AudioData:
    waveform: np.ndarray
    sample_rate_hz: int
    original_sample_rate_hz: int
    channels: int
    duration_sec: float


@dataclass(frozen=True)
class StftResult:
    spectrum: np.ndarray
    frequencies_hz: np.ndarray
    sample_rate_hz: int
    n_fft: int
    hop_length: int
    original_length: int


def _decode_pcm(raw_audio: bytes, sample_width: int) -> np.ndarray:
    if sample_width == 1:
        audio = np.frombuffer(raw_audio, dtype=np.uint8).astype(np.float32)
        return (audio - 128.0) / 128.0
    if sample_width == 2:
        return np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
    if sample_width == 3:
        audio_bytes = np.frombuffer(raw_audio, dtype=np.uint8).reshape(-1, 3)
        sign_byte = (audio_bytes[:, 2] >= 128).astype(np.uint8) * 255
        audio_32 = np.column_stack([audio_bytes, sign_byte]).reshape(-1, 4)
        return audio_32.view(np.int32).reshape(-1).astype(np.float32) / 8388608.0
    if sample_width == 4:
        return np.frombuffer(raw_audio, dtype=np.int32).astype(np.float32) / 2147483648.0
    raise ValueError(f"Unsupported WAV sample width: {sample_width} bytes")


def resample_linear(
    waveform: np.ndarray,
    original_sample_rate: int,
    target_sample_rate: int,
) -> np.ndarray:
    """Resample mono audio with deterministic linear interpolation."""

    if original_sample_rate == target_sample_rate:
        return waveform.astype(np.float32, copy=False)
    if original_sample_rate <= 0 or target_sample_rate <= 0:
        raise ValueError("Sample rates must be positive for resampling.")
    if waveform.size == 0:
        return waveform.astype(np.float32, copy=False)

    target_length = max(1, round(waveform.size * target_sample_rate / original_sample_rate))
    old_x = np.linspace(0.0, 1.0, num=waveform.size, endpoint=False)
    new_x = np.linspace(0.0, 1.0, num=target_length, endpoint=False)
    return np.interp(new_x, old_x, waveform).astype(np.float32)


def peak_normalize(waveform: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    max_abs = float(np.max(np.abs(waveform))) if waveform.size else 0.0
    if max_abs <= EPS:
        return waveform.astype(np.float32, copy=False)
    if max_abs <= target_peak:
        return waveform.astype(np.float32, copy=False)
    return (waveform / max_abs * target_peak).astype(np.float32)


def load_wav_mono(path: Path, target_sample_rate: int | None = None) -> AudioData:
    """Load a PCM WAV file as mono float32 in [-1, 1]."""

    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()
        raw_audio = wav_file.readframes(frame_count)

    if channels <= 0 or sample_rate <= 0:
        raise ValueError(f"Invalid WAV metadata in {path}.")

    audio = _decode_pcm(raw_audio, sample_width)
    waveform = audio.reshape(-1, channels).T
    mono = waveform.mean(axis=0).astype(np.float32)

    output_sample_rate = target_sample_rate or sample_rate
    mono = resample_linear(mono, sample_rate, output_sample_rate)
    mono = peak_normalize(mono)

    return AudioData(
        waveform=mono,
        sample_rate_hz=output_sample_rate,
        original_sample_rate_hz=sample_rate,
        channels=channels,
        duration_sec=mono.size / output_sample_rate,
    )


def save_wav_mono(path: Path, waveform: np.ndarray, sample_rate_hz: int) -> None:
    """Save mono float audio as playable 16-bit PCM WAV."""

    if sample_rate_hz <= 0:
        raise ValueError("Output sample rate must be positive.")

    path.parent.mkdir(parents=True, exist_ok=True)
    audio = np.asarray(waveform, dtype=np.float32).reshape(-1)
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    audio = peak_normalize(audio)
    audio = np.clip(audio, -1.0, 1.0)
    audio_i16 = (audio * 32767.0).astype(np.int16)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(audio_i16.tobytes())


def is_effectively_silent(waveform: np.ndarray, threshold: float = 1e-6) -> bool:
    if waveform.size == 0:
        return True
    return float(np.sqrt(np.mean(np.square(waveform)))) < threshold


def fit_length(waveform: np.ndarray, expected_length: int) -> np.ndarray:
    audio = np.asarray(waveform, dtype=np.float32).reshape(-1)
    if audio.size == expected_length:
        return audio
    if audio.size > expected_length:
        return audio[:expected_length]
    return np.pad(audio, (0, expected_length - audio.size))


def stft(
    waveform: np.ndarray,
    sample_rate_hz: int,
    n_fft: int = 1024,
    hop_length: int = 256,
) -> StftResult:
    audio = np.asarray(waveform, dtype=np.float32).reshape(-1)
    if audio.size == 0:
        raise ValueError("Cannot compute STFT for empty audio.")

    n_fft = min(n_fft, max(64, 2 ** int(math.ceil(math.log2(max(64, audio.size))))))
    hop_length = min(hop_length, max(1, n_fft // 2))
    frame_count = 1 if audio.size <= n_fft else math.ceil((audio.size - n_fft) / hop_length) + 1
    padded_length = (frame_count - 1) * hop_length + n_fft
    padded = np.pad(audio, (0, padded_length - audio.size))
    window = np.hanning(n_fft).astype(np.float32)

    frames = np.empty((frame_count, n_fft), dtype=np.float32)
    for frame_index in range(frame_count):
        start = frame_index * hop_length
        frames[frame_index] = padded[start : start + n_fft] * window

    spectrum = np.fft.rfft(frames, n=n_fft, axis=1).T
    frequencies = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate_hz)
    return StftResult(
        spectrum=spectrum,
        frequencies_hz=frequencies.astype(np.float32),
        sample_rate_hz=sample_rate_hz,
        n_fft=n_fft,
        hop_length=hop_length,
        original_length=audio.size,
    )


def istft(stft_result: StftResult, spectrum: np.ndarray | None = None) -> np.ndarray:
    spec = stft_result.spectrum if spectrum is None else spectrum
    frame_count = spec.shape[1]
    padded_length = (frame_count - 1) * stft_result.hop_length + stft_result.n_fft
    output = np.zeros(padded_length, dtype=np.float32)
    window_sum = np.zeros(padded_length, dtype=np.float32)
    window = np.hanning(stft_result.n_fft).astype(np.float32)
    frames = np.fft.irfft(spec.T, n=stft_result.n_fft, axis=1).astype(np.float32)

    for frame_index, frame in enumerate(frames):
        start = frame_index * stft_result.hop_length
        output[start : start + stft_result.n_fft] += frame * window
        window_sum[start : start + stft_result.n_fft] += window * window

    valid = window_sum > EPS
    output[valid] /= window_sum[valid]
    return output[: stft_result.original_length].astype(np.float32)


def logistic_mask(frequencies_hz: np.ndarray, center_hz: float, width_hz: float, invert: bool = False) -> np.ndarray:
    x = np.clip((frequencies_hz - center_hz) / max(width_hz, EPS), -60.0, 60.0)
    mask = 1.0 / (1.0 + np.exp(x))
    if invert:
        mask = 1.0 - mask
    return mask.astype(np.float32)


def frequency_mask_split(
    waveform: np.ndarray,
    sample_rate_hz: int,
    n_fft: int = 1024,
    hop_length: int = 256,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Split with smooth fixed frequency priors.

    This is a conventional baseline, not a trained model. The masks overlap in
    the low-mid region to avoid harsh musical artifacts.
    """

    transform = stft(waveform, sample_rate_hz, n_fft=n_fft, hop_length=hop_length)
    freqs = transform.frequencies_hz
    heart_prior = logistic_mask(freqs, center_hz=180.0, width_hz=35.0)
    lung_prior = logistic_mask(freqs, center_hz=130.0, width_hz=55.0, invert=True)
    total = heart_prior + lung_prior + EPS
    heart_mask = (heart_prior / total)[:, None]
    lung_mask = (lung_prior / total)[:, None]

    heart = istft(transform, transform.spectrum * heart_mask)
    lung = istft(transform, transform.spectrum * lung_mask)
    metadata = {
        "mask_type": "smooth_fixed_frequency_mask",
        "heart_transition_hz": 180.0,
        "lung_transition_hz": 130.0,
        "n_fft": transform.n_fft,
        "hop_length": transform.hop_length,
    }
    return heart, lung, metadata


def dominant_frequency_hz(waveform: np.ndarray, sample_rate_hz: int) -> float:
    audio = np.asarray(waveform, dtype=np.float32).reshape(-1)
    if audio.size == 0:
        return 0.0
    window = np.hanning(audio.size).astype(np.float32)
    magnitude = np.abs(np.fft.rfft(audio * window))
    frequencies = np.fft.rfftfreq(audio.size, d=1.0 / sample_rate_hz)
    if magnitude.size <= 1:
        return 0.0
    index = int(np.argmax(magnitude[1:]) + 1)
    return float(frequencies[index])
