from __future__ import annotations

import asyncio
import io
import shutil
import uuid
import wave
from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.models.db_models import UploadedAudio
from app.routers.upload import upload_audio
from app.services import storage_service
from app.services.audio_validation import (
    AudioValidatorFactory,
    WavAudioValidator,
)


def build_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(4000)
        wav_file.writeframes(b"\x00\x00" * 16)
    return buffer.getvalue()


@pytest.fixture()
def upload_db(monkeypatch):
    runtime_dir = (Path("storage/uploads/temp/test_upload") / uuid.uuid4().hex).resolve()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    database_path = runtime_dir / "test_upload.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, future=True)
    db = TestingSession()

    monkeypatch.setattr(storage_service, "RAW_UPLOAD_DIR", runtime_dir / "raw")

    try:
        yield db, runtime_dir
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        shutil.rmtree(runtime_dir, ignore_errors=True)


def test_audio_validator_factory_returns_wav_validator() -> None:
    validator = AudioValidatorFactory.create("sample.wav")

    assert isinstance(validator, WavAudioValidator)


def test_wav_audio_validator_accepts_valid_wav() -> None:
    upload = UploadFile(filename="valid.wav", file=io.BytesIO(build_wav_bytes()))

    asyncio.run(WavAudioValidator().validate(upload))


def test_audio_validator_factory_rejects_invalid_file_type() -> None:
    with pytest.raises(ValueError, match="Only .wav"):
        AudioValidatorFactory.create("invalid.mp3")


def test_wav_audio_validator_rejects_invalid_header() -> None:
    upload = UploadFile(filename="fake.wav", file=io.BytesIO(b"not a wav file"))

    with pytest.raises(ValueError, match="valid WAV"):
        asyncio.run(WavAudioValidator().validate(upload))


def test_upload_route_saves_valid_wav(upload_db) -> None:
    db, _runtime_dir = upload_db
    upload = UploadFile(filename="mixed.wav", file=io.BytesIO(build_wav_bytes()))

    payload = asyncio.run(upload_audio(file=upload, db=db))

    audio_record = db.get(UploadedAudio, payload["audio_id"])
    assert audio_record is not None
    assert audio_record.original_filename == "mixed.wav"
    assert storage_service.resolve_project_path(audio_record.stored_path).is_file()
