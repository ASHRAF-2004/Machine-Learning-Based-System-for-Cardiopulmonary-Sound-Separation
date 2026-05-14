"""Business logic for creating and running separation jobs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ml.separation_engine import SeparationEngine
from app.models.db_models import SeparationJob, UploadedAudio
from app.services import model_service, result_service, storage_service
from app.services.model_strategy_resolver import ModelStrategyResolver


class SeparationError(Exception):
    pass


class UploadedAudioNotFoundError(SeparationError):
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


def get_uploaded_audio(db: Session, audio_id: int) -> UploadedAudio:
    uploaded_audio = db.get(UploadedAudio, audio_id)
    if uploaded_audio is None:
        raise UploadedAudioNotFoundError(f"Uploaded audio not found: {audio_id}")
    return uploaded_audio


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


class SeparationService:
    """Facade that coordinates the full upload-to-result separation workflow."""

    def __init__(
        self,
        strategy_resolver: type[ModelStrategyResolver] | None = None,
        engine_class: type[SeparationEngine] = SeparationEngine,
    ) -> None:
        self.strategy_resolver = strategy_resolver or ModelStrategyResolver
        self.engine_class = engine_class

    def separate_uploaded_audio(
        self,
        db: Session,
        audio_id: int,
        model_id: int | None = None,
    ) -> SeparationResponse:
        uploaded_audio = get_uploaded_audio(db, audio_id)
        model = model_service.get_model_for_separation(db, model_id)
        algorithm = self.strategy_resolver.resolve(model)
        engine = self.engine_class(algorithm=algorithm, device_name="cpu")

        input_path = storage_service.resolve_project_path(uploaded_audio.stored_path)
        if not input_path.is_file():
            raise FileNotFoundError(f"Uploaded WAV file is missing: {input_path}")

        model_path = storage_service.resolve_project_path(model.checkpoint_path)
        model_config_path = (
            storage_service.resolve_project_path(model.config_path)
            if model.config_path
            else None
        )

        job = create_running_job(
            db=db,
            uploaded_audio_id=uploaded_audio.uploaded_audio_id,
            model_id=model.model_id,
        )
        output_paths = storage_service.build_separation_output_paths(job.job_id)

        start_time = time.perf_counter()
        try:
            inference_result = engine.separate(
                input_wav_path=input_path,
                model_path=model_path,
                model_config_path=model_config_path,
                heart_output_path=output_paths.heart_file_path,
                lung_output_path=output_paths.lung_file_path,
            )
            processing_time_ms = int((time.perf_counter() - start_time) * 1000)

            result = result_service.create_separation_result(
                db=db,
                job_id=job.job_id,
                inference_result=inference_result,
            )
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


def separate_uploaded_audio(
    db: Session,
    audio_id: int,
    model_id: int | None = None,
) -> SeparationResponse:
    return SeparationService().separate_uploaded_audio(db, audio_id, model_id)
