from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.main import health_check
from app.models.db_models import Model, SeparationJob, SeparationResult, UploadedAudio
from app.services.result_service import (
    JobNotFoundError,
    get_download_file,
    get_history,
    get_result_details,
)


@pytest.fixture()
def db_session():
    runtime_dir = Path("storage/uploads/temp/test_results") / uuid.uuid4().hex
    runtime_dir.mkdir(parents=True, exist_ok=True)

    database_path = runtime_dir / "test_results.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, future=True)

    db = TestingSession()
    try:
        yield db, runtime_dir
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        shutil.rmtree(runtime_dir, ignore_errors=True)


def seed_completed_job(db, runtime_dir: Path) -> int:
    heart_path = runtime_dir / "1_heart.wav"
    lung_path = runtime_dir / "1_lung.wav"
    heart_path.write_bytes(b"RIFFheart")
    lung_path.write_bytes(b"RIFFlung")

    uploaded_audio = UploadedAudio(
        original_filename="mixed.wav",
        stored_path="storage/uploads/raw/mixed.wav",
        mime_type="audio/wav",
        sample_rate_hz=4000,
        channels=1,
        bit_depth=16,
        duration_sec=15.0,
        file_size_bytes=120044,
    )
    model = Model(
        model_name="NeoSSNet",
        version="1.0",
        checkpoint_path="storage/ml_models/model_best.pt",
        config_path="storage/ml_models/model.yaml",
    )
    db.add_all([uploaded_audio, model])
    db.commit()
    db.refresh(uploaded_audio)
    db.refresh(model)

    job = SeparationJob(
        uploaded_audio_id=uploaded_audio.uploaded_audio_id,
        model_id=model.model_id,
        status="completed",
        completed_at="2026-04-28T06:00:00+00:00",
        processing_time_ms=1234,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    result = SeparationResult(
        job_id=job.job_id,
        heart_file_path=str(heart_path),
        lung_file_path=str(lung_path),
        output_sample_rate_hz=4000,
        output_duration_sec=15.0,
        heart_file_size_bytes=heart_path.stat().st_size,
        lung_file_size_bytes=lung_path.stat().st_size,
    )
    db.add(result)
    db.commit()
    return job.job_id


def test_health_check_reports_ok() -> None:
    response = health_check()

    assert response["status"] == "ok"
    assert isinstance(response["database_exists"], bool)


def test_get_result_details_returns_job_and_output_paths(db_session) -> None:
    db, runtime_dir = db_session
    job_id = seed_completed_job(db, runtime_dir)

    result = get_result_details(db, job_id)

    assert result["job_id"] == job_id
    assert result["status"] == "completed"
    assert result["uploaded_audio"]["original_filename"] == "mixed.wav"
    assert result["heart_file_path"].endswith("1_heart.wav")
    assert result["lung_file_path"].endswith("1_lung.wav")
    assert result["processing_time_ms"] == 1234


def test_get_download_file_returns_existing_heart_file(db_session) -> None:
    db, runtime_dir = db_session
    job_id = seed_completed_job(db, runtime_dir)

    file_info = get_download_file(db, job_id, "heart")

    assert file_info.path.is_file()
    assert file_info.filename == "1_heart.wav"
    assert file_info.media_type == "audio/wav"


def test_get_history_returns_recent_jobs(db_session) -> None:
    db, runtime_dir = db_session
    job_id = seed_completed_job(db, runtime_dir)

    history = get_history(db, limit=5)

    assert len(history) == 1
    assert history[0]["job_id"] == job_id
    assert history[0]["original_filename"] == "mixed.wav"
    assert history[0]["status"] == "completed"
    assert history[0]["heart_file_path"].endswith("1_heart.wav")


def test_get_result_details_missing_job_raises_404_service_error(db_session) -> None:
    db, _runtime_dir = db_session
    with pytest.raises(JobNotFoundError):
        get_result_details(db, 999)
