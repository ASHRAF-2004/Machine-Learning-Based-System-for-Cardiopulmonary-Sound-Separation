from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.ml.audio_utils import save_wav_mono
from app.models.db_models import EvaluationMetric, Model, SeparationJob, SeparationResult, UploadedAudio
from app.services import evaluation_service


@pytest.fixture()
def db_session():
    runtime_dir = Path("storage/uploads/temp/test_evaluation") / uuid.uuid4().hex
    runtime_dir.mkdir(parents=True, exist_ok=True)

    database_path = runtime_dir / "test_evaluation.db"
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


def write_signal(path: Path, frequency_hz: float) -> None:
    sample_rate_hz = 4000
    time_axis = np.arange(sample_rate_hz, dtype=np.float32) / sample_rate_hz
    waveform = 0.5 * np.sin(2 * np.pi * frequency_hz * time_axis)
    save_wav_mono(path, waveform, sample_rate_hz)


def test_evaluate_and_store_result_uses_hls_references(db_session, monkeypatch) -> None:
    db, runtime_dir = db_session
    raw_mix = runtime_dir / "raw" / "Mix"
    raw_mix.mkdir(parents=True)
    monkeypatch.setattr(evaluation_service, "DATASET_MIX_DIR", raw_mix)

    input_path = runtime_dir / "M0001.wav"
    heart_ref = raw_mix / "H0001.wav"
    lung_ref = raw_mix / "L0001.wav"
    heart_output = runtime_dir / "heart.wav"
    lung_output = runtime_dir / "lung.wav"
    write_signal(heart_ref, 80.0)
    write_signal(lung_ref, 650.0)
    save_wav_mono(input_path, evaluation_service.load_wav_mono(heart_ref).waveform + evaluation_service.load_wav_mono(lung_ref).waveform, 4000)
    shutil.copy2(heart_ref, heart_output)
    shutil.copy2(lung_ref, lung_output)

    uploaded_audio = UploadedAudio(
        original_filename="M0001.wav",
        stored_path=str(input_path),
        mime_type="audio/wav",
        sample_rate_hz=4000,
        channels=1,
        bit_depth=16,
        duration_sec=1.0,
        file_size_bytes=input_path.stat().st_size,
    )
    model = Model(
        model_name="Fixed Filter Baseline",
        version="1.0",
        architecture="FixedFilter",
        framework="NumPy",
        checkpoint_path="builtin://fixed_filter",
        strategy_key="fixed_filter",
        method_type="baseline",
        requires_checkpoint=0,
    )
    db.add_all([uploaded_audio, model])
    db.commit()
    db.refresh(uploaded_audio)
    db.refresh(model)
    job = SeparationJob(
        uploaded_audio_id=uploaded_audio.uploaded_audio_id,
        model_id=model.model_id,
        status="completed",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    result = SeparationResult(
        job_id=job.job_id,
        heart_file_path=str(heart_output),
        lung_file_path=str(lung_output),
        output_sample_rate_hz=4000,
        output_duration_sec=1.0,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    metrics = evaluation_service.evaluate_and_store_result(
        db=db,
        result=result,
        uploaded_audio=uploaded_audio,
        input_path=input_path,
        heart_output_path=heart_output,
        lung_output_path=lung_output,
        sample_rate_hz=4000,
    )
    db.commit()

    stored_count = db.query(EvaluationMetric).filter_by(result_id=result.result_id).count()
    assert len(metrics) == 14
    assert stored_count == 14


def test_reference_metrics_record_alignment_lag(tmp_path: Path) -> None:
    sample_rate_hz = 4000
    time_axis = np.arange(sample_rate_hz, dtype=np.float32) / sample_rate_hz
    heart_ref_wave = 0.5 * np.sin(2 * np.pi * 80.0 * time_axis)
    lung_ref_wave = 0.3 * np.sin(2 * np.pi * 650.0 * time_axis)
    shifted_heart = np.pad(heart_ref_wave, (32, 0))[: heart_ref_wave.size]

    input_path = tmp_path / "mixed.wav"
    heart_ref = tmp_path / "heart_ref.wav"
    lung_ref = tmp_path / "lung_ref.wav"
    heart_output = tmp_path / "heart_output.wav"
    lung_output = tmp_path / "lung_output.wav"

    save_wav_mono(input_path, heart_ref_wave + lung_ref_wave, sample_rate_hz)
    save_wav_mono(heart_ref, heart_ref_wave, sample_rate_hz)
    save_wav_mono(lung_ref, lung_ref_wave, sample_rate_hz)
    save_wav_mono(heart_output, shifted_heart, sample_rate_hz)
    save_wav_mono(lung_output, lung_ref_wave, sample_rate_hz)

    metrics = evaluation_service.calculate_reference_metrics(
        input_path=input_path,
        heart_output_path=heart_output,
        lung_output_path=lung_output,
        reference_pair=evaluation_service.ReferencePair(
            heart_path=heart_ref,
            lung_path=lung_ref,
            reference_type="unit_test",
        ),
        sample_rate_hz=sample_rate_hz,
        max_alignment_lag_ms=20.0,
    )
    lookup = {
        (metric.metric_scope, metric.metric_name): metric.metric_value
        for metric in metrics
    }

    assert abs(lookup[("heart", "alignment_lag")]) > 0
    assert lookup[("lung", "alignment_lag")] == 0
