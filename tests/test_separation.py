from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.ml.separation_algorithm import SeparationAlgorithmResult
from app.models.db_models import Model, SeparationJob, SystemLog, UploadedAudio
from app.services import separation_service, storage_service


class FakeAlgorithm:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def separate(
        self,
        input_wav_path: Path,
        model_path: Path,
        model_config_path: Path | None,
        heart_output_path: Path,
        lung_output_path: Path,
        device_name: str = "cpu",
    ) -> SeparationAlgorithmResult:
        heart_output_path.parent.mkdir(parents=True, exist_ok=True)
        lung_output_path.parent.mkdir(parents=True, exist_ok=True)
        heart_output_path.write_bytes(b"RIFFheart")
        lung_output_path.write_bytes(b"RIFFlung")
        self.calls.append(
            {
                "input_wav_path": input_wav_path,
                "model_path": model_path,
                "model_config_path": model_config_path,
                "device_name": device_name,
            }
        )
        return SeparationAlgorithmResult(
            heart_file_path=heart_output_path,
            lung_file_path=lung_output_path,
            sample_rate_hz=4000,
            duration_sec=1.0,
            heart_file_size_bytes=heart_output_path.stat().st_size,
            lung_file_size_bytes=lung_output_path.stat().st_size,
            input_shape=(1, 4000),
            output_shape=(1, 2, 4000),
        )


class FakeResolver:
    algorithm = FakeAlgorithm()
    model_ids: list[int] = []

    @classmethod
    def resolve(cls, model: Model) -> FakeAlgorithm:
        cls.model_ids.append(model.model_id)
        return cls.algorithm


@pytest.fixture()
def db_session(monkeypatch):
    runtime_dir = (Path("storage/uploads/temp/test_separation") / uuid.uuid4().hex).resolve()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    database_path = runtime_dir / "test_separation.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, future=True)

    db = TestingSession()
    monkeypatch.setattr(storage_service, "HEART_OUTPUT_DIR", runtime_dir / "heart")
    monkeypatch.setattr(storage_service, "LUNG_OUTPUT_DIR", runtime_dir / "lung")
    FakeResolver.algorithm = FakeAlgorithm()
    FakeResolver.model_ids = []
    monkeypatch.setattr(separation_service, "ModelStrategyResolver", FakeResolver)

    try:
        yield db, runtime_dir
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        shutil.rmtree(runtime_dir, ignore_errors=True)


def seed_uploaded_audio_and_model(db, runtime_dir: Path) -> tuple[UploadedAudio, Model]:
    input_path = runtime_dir / "mixed.wav"
    input_path.write_bytes(b"RIFFfakeWAVE")
    model_path = runtime_dir / "neossnet.pt"
    config_path = runtime_dir / "neossnet.yaml"
    model_path.write_bytes(b"weights")
    config_path.write_text("sample_rate: 4000", encoding="utf-8")

    uploaded_audio = UploadedAudio(
        original_filename="mixed.wav",
        stored_path=str(input_path),
        mime_type="audio/wav",
        sample_rate_hz=4000,
        channels=1,
        bit_depth=16,
        duration_sec=1.0,
        file_size_bytes=input_path.stat().st_size,
    )
    model = Model(
        model_name="NeoSSNet",
        version="1.0",
        architecture="NeoSSNet",
        framework="PyTorch",
        checkpoint_path=str(model_path),
        config_path=str(config_path),
        description="Current working model",
        is_active=1,
    )
    db.add_all([uploaded_audio, model])
    db.commit()
    db.refresh(uploaded_audio)
    db.refresh(model)
    return uploaded_audio, model


def test_separation_uses_active_model_by_default(db_session) -> None:
    db, runtime_dir = db_session
    uploaded_audio, model = seed_uploaded_audio_and_model(db, runtime_dir)

    response = separation_service.separate_uploaded_audio(
        db,
        uploaded_audio.uploaded_audio_id,
    )

    job = db.get(SeparationJob, response.job_id)
    logs = (
        db.query(SystemLog)
        .filter(SystemLog.job_id == response.job_id)
        .order_by(SystemLog.created_at.asc(), SystemLog.log_id.asc())
        .all()
    )
    assert response.status == "completed"
    assert job is not None
    assert job.model_id == model.model_id
    for timestamp in (job.requested_at, job.started_at, job.completed_at):
        parsed_timestamp = datetime.fromisoformat(timestamp)
        assert parsed_timestamp.tzinfo is not None
    assert FakeResolver.model_ids == [model.model_id]
    assert response.heart_file_path.endswith(f"{response.job_id}_heart.wav")
    assert response.lung_file_path.endswith(f"{response.job_id}_lung.wav")
    assert [log.event_type for log in logs] == [
        "separation_started",
        "separation_completed",
    ]


def test_separation_accepts_explicit_model_id(db_session) -> None:
    db, runtime_dir = db_session
    uploaded_audio, model = seed_uploaded_audio_and_model(db, runtime_dir)

    response = separation_service.separate_uploaded_audio(
        db,
        uploaded_audio.uploaded_audio_id,
        model_id=model.model_id,
    )

    job = db.get(SeparationJob, response.job_id)
    assert response.status == "completed"
    assert job is not None
    assert job.model_id == model.model_id
    assert FakeResolver.model_ids == [model.model_id]
