"""Audio validation products and creator for upload handling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol

from fastapi import UploadFile


class AudioValidator(Protocol):
    """Product interface for upload audio validators."""

    async def validate(self, upload_file: UploadFile) -> None:
        """Validate an uploaded audio file before it is saved."""


class WavAudioValidator:
    """Concrete product that validates WAV extension and RIFF/WAVE header."""

    async def validate(self, upload_file: UploadFile) -> None:
        filename = Path(upload_file.filename or "").name.strip()
        if Path(filename).suffix.lower() != ".wav":
            raise ValueError("Only .wav audio files are accepted.")

        await upload_file.seek(0)
        header = await upload_file.read(12)
        if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise ValueError("Uploaded file is not a valid WAV file.")

        await upload_file.seek(0)


class AudioValidatorFactory(ABC):
    """Creator that declares the factory method for upload validators."""

    @abstractmethod
    def create_validator(self, filename: str | None) -> AudioValidator:
        """Create an audio validator for the uploaded filename."""


class WavAudioValidatorFactory(AudioValidatorFactory):
    """Concrete creator that creates WAV upload validators."""

    def create_validator(self, filename: str | None) -> AudioValidator:
        suffix = Path(filename or "").suffix.lower()
        if suffix == ".wav":
            return WavAudioValidator()

        raise ValueError("Only .wav audio files are accepted.")
