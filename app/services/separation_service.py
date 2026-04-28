"""Business logic for creating and running separation jobs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.db import PROJECT_ROOT
from app.ml.neossnet_inference import run_neossnet_inference
from app.models.db_models import Model, SeparationJob, SeparationResult, UploadedAudio


HEART_OUTPUT_DIR = PROJECT_ROOT / "storage" / "outputs" / "heart"
LUNG_OUTPUT_DIR = PROJECT_ROOT / "storage" / "outputs" / "lung"


class SeparationError(Exception):
    pass


class UploadedAudioNotFoundError(SeparationError):
    pass


class ActiveModelNotFoundError(SeparationError):
    pass


@dataclass(frozen=True)
class SeparationResponse:
    job_id: int
    status: str
    heart_file_path: str | None
    lung_file_path: str | None
    processing_time_ms: int


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_project_path(path_value: str | None) -> Path:
    if not path_value:
        raise FileNotFoundError("Path value is missing.")

    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def relative_project_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def get_uploaded_audio(db: Session, audio_id: int) -> UploadedAudio:
    uploaded_audio = db.get(UploadedAudio, audio_id)
    if uploaded_audio is None:
        raise UploadedAudioNotFoundError(f"Uploaded audio not found: {audio_id}")
    return uploaded_audio


def get_active_model(db: Session) -> Model:
    model = (
        db.query(Model)
        .filter(Model.is_active == 1)
        .order_by(Model.model_id.desc())
        .first()
    )
    if model is None:
        raise ActiveModelNotFoundError("No active NeoSSNet model is configured.")
    if not model.checkpoint_path or not model.config_path:
        raise ActiveModelNotFoundError(
            "Active model must have checkpoint_path and config_path."
        )
    return model


def create_running_job(db: Session, uploaded_audio_id: int, model_id: int) -> SeparationJob:
    job = SeparationJob(
        uploaded_audio_id=uploaded_audio_id,
        model_id=model_id,
        status="running",
        started_at=utc_now_text(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_job_failed(
    db: Session,
    job: SeparationJob,
    error: Exception,
    processing_time_ms: int,
) -> None:
    job.status = "failed"
    job.completed_at = utc_now_text()
    job.processing_time_ms = processing_time_ms
    job.error_message = str(error)
    db.commit()


def separate_uploaded_audio(db: Session, audio_id: int) -> SeparationResponse:
    uploaded_audio = get_uploaded_audio(db, audio_id)
    model = get_active_model(db)

    input_path = resolve_project_path(uploaded_audio.stored_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Uploaded WAV file is missing: {input_path}")

    model_path = resolve_project_path(model.checkpoint_path)
    model_config_path = resolve_project_path(model.config_path)

    job = create_running_job(
        db=db,
        uploaded_audio_id=uploaded_audio.uploaded_audio_id,
        model_id=model.model_id,
    )

    HEART_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LUNG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    heart_output_path = HEART_OUTPUT_DIR / f"{job.job_id}_heart.wav"
    lung_output_path = LUNG_OUTPUT_DIR / f"{job.job_id}_lung.wav"

    start_time = time.perf_counter()
    try:
        inference_result = run_neossnet_inference(
            input_wav_path=input_path,
            model_path=model_path,
            model_config_path=model_config_path,
            heart_output_path=heart_output_path,
            lung_output_path=lung_output_path,
            device_name="cpu",
        )
        processing_time_ms = int((time.perf_counter() - start_time) * 1000)

        result = SeparationResult(
            job_id=job.job_id,
            heart_file_path=relative_project_path(inference_result.heart_file_path),
            lung_file_path=relative_project_path(inference_result.lung_file_path),
            output_sample_rate_hz=inference_result.sample_rate_hz,
            output_duration_sec=inference_result.duration_sec,
            heart_file_size_bytes=inference_result.heart_file_size_bytes,
            lung_file_size_bytes=inference_result.lung_file_size_bytes,
        )
        db.add(result)
        job.status = "completed"
        job.completed_at = utc_now_text()
        job.processing_time_ms = processing_time_ms
        db.commit()
        db.refresh(job)
        db.refresh(result)

        return SeparationResponse(
            job_id=job.job_id,
            status=job.status,
            heart_file_path=result.heart_file_path,
            lung_file_path=result.lung_file_path,
            processing_time_ms=job.processing_time_ms or processing_time_ms,
        )
    except Exception as error:
        processing_time_ms = int((time.perf_counter() - start_time) * 1000)
        db.rollback()
        try:
            mark_job_failed(db, job, error, processing_time_ms)
        except SQLAlchemyError:
            db.rollback()
        raise
