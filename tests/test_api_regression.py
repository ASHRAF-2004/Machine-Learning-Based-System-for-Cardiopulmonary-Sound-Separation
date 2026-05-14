from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.ml.separation_algorithm import SeparationAlgorithmResult
from app.models.db_models import Model, UploadedAudio
from app.routers.models import available_models
from app.routers.results import download_heart, history, result_details
from app.routers.separation import separate_audio
from app.services import separation_service, storage_service


class RouteFakeAlgorithm:
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


class RouteFakeResolver:
    model_ids: list[int] = []

    @classmethod
    def resolve(cls, model: Model) -> RouteFakeAlgorithm:
        cls.model_ids.append(model.model_id)
        return RouteFakeAlgorithm()


@pytest.fixture()
def api_db(monkeypatch):
    runtime_dir = (Path("storage/uploads/temp/test_api") / uuid.uuid4().hex).resolve()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    database_path = runtime_dir / "test_api.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, future=True)
    db = TestingSession()

    monkeypatch.setattr(storage_service, "HEART_OUTPUT_DIR", runtime_dir / "heart")
    monkeypatch.setattr(storage_service, "LUNG_OUTPUT_DIR", runtime_dir / "lung")
    monkeypatch.setattr(separation_service, "ModelStrategyResolver", RouteFakeResolver)
    RouteFakeResolver.model_ids = []

    try:
        yield db, runtime_dir
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        shutil.rmtree(runtime_dir, ignore_errors=True)


def seed_audio_and_model(db, runtime_dir: Path) -> tuple[UploadedAudio, Model]:
    input_path = runtime_dir / "mixed.wav"
    model_path = runtime_dir / "neossnet.pt"
    config_path = runtime_dir / "neossnet.yaml"
    input_path.write_bytes(b"RIFFfakeWAVE")
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


def test_models_and_separation_routes_keep_working(api_db) -> None:
    db, runtime_dir = api_db
    uploaded_audio, model = seed_audio_and_model(db, runtime_dir)

    models_payload = available_models(db)
    assert models_payload[0]["model_id"] == model.model_id

    default_payload = separate_audio(
        uploaded_audio.uploaded_audio_id,
        model_id=None,
        db=db,
    )
    assert default_payload["status"] == "completed"

    explicit_payload = separate_audio(
        uploaded_audio.uploaded_audio_id,
        model_id=model.model_id,
        db=db,
    )
    assert explicit_payload["status"] == "completed"
    assert RouteFakeResolver.model_ids == [model.model_id, model.model_id]

    result_payload = result_details(default_payload["job_id"], db)
    assert result_payload["heart_file_path"].endswith("_heart.wav")

    history_payload = history(limit=20, db=db)
    assert len(history_payload) == 2

    download_response = download_heart(default_payload["job_id"], db)
    assert Path(download_response.path).read_bytes() == b"RIFFheart"
