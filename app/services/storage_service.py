"""File storage and WAV validation helpers."""

from __future__ import annotations

import re
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from app.database.db import PROJECT_ROOT


RAW_UPLOAD_DIR = PROJECT_ROOT / "storage" / "uploads" / "raw"
CHUNK_SIZE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class StoredAudio:
    original_filename: str
    stored_path: str
    absolute_path: Path
    mime_type: str
    sample_rate_hz: int
    channels: int
    bit_depth: int
    duration_sec: float
    file_size_bytes: int


def clean_filename(filename: str) -> str:
    base_name = Path(filename).name.strip()
    if not base_name:
        base_name = "upload.wav"

    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", base_name)
    return safe_name or "upload.wav"


def validate_wav_filename(filename: str) -> None:
    if Path(filename).suffix.lower() != ".wav":
        raise ValueError("Only .wav audio files are accepted.")


def validate_wav_header(header: bytes) -> None:
    if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
        raise ValueError("Uploaded file is not a valid WAV file.")


def relative_project_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def read_wav_metadata(path: Path) -> tuple[int, int, int, float]:
    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_rate_hz = wav_file.getframerate()
            bit_depth = wav_file.getsampwidth() * 8
            frames = wav_file.getnframes()
    except wave.Error as error:
        raise ValueError(f"Uploaded file is not a readable WAV file: {error}") from error

    duration_sec = frames / sample_rate_hz if sample_rate_hz else 0.0
    return sample_rate_hz, channels, bit_depth, duration_sec


def remove_saved_file(path: Path) -> None:
    if path.is_file():
        path.unlink()


async def save_uploaded_wav(upload_file: UploadFile) -> StoredAudio:
    original_filename = clean_filename(upload_file.filename or "")
    validate_wav_filename(original_filename)

    await upload_file.seek(0)
    validate_wav_header(await upload_file.read(12))
    await upload_file.seek(0)

    RAW_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    stored_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{original_filename}"
    destination = RAW_UPLOAD_DIR / stored_filename

    with destination.open("wb") as output_file:
        while True:
            chunk = await upload_file.read(CHUNK_SIZE_BYTES)
            if not chunk:
                break
            output_file.write(chunk)

    try:
        sample_rate_hz, channels, bit_depth, duration_sec = read_wav_metadata(
            destination
        )
    except ValueError:
        remove_saved_file(destination)
        raise

    return StoredAudio(
        original_filename=original_filename,
        stored_path=relative_project_path(destination),
        absolute_path=destination,
        mime_type=upload_file.content_type or "audio/wav",
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        bit_depth=bit_depth,
        duration_sec=duration_sec,
        file_size_bytes=destination.stat().st_size,
    )
