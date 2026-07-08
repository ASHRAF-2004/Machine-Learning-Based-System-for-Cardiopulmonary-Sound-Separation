"""Business logic for creating and running separation jobs."""

from __future__ import annotations

import time
import json
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.ml.separation_engine import SeparationEngine
from app.models.db_models import SeparationJob, SystemLog, UploadedAudio
from app.services import (
    evaluation_service,
    model_service,
    result_service,
    storage_service,
    visualization_service,
)
from app.services.model_strategy_resolver import ModelStrategyResolver
from app.services.separation_algorithm_factory import SeparationAlgorithmFactory
from app.services.time_service import current_time_text


class SeparationError(Exception):
    pass


class UploadedAudioNotFoundError(SeparationError):
    pass


class SeparationJobNotFoundError(SeparationError):
    pass


@dataclass(frozen=True)
class SeparationResponse:
    job_id: int
    status: str
    heart_file_path: str | None
    lung_file_path: str | None
    processing_time_ms: int
    model_id: int
    strategy_key: str


def get_uploaded_audio(db: Session, audio_id: int) -> UploadedAudio:
    uploaded_audio = db.get(UploadedAudio, audio_id)
    if uploaded_audio is None:
        raise UploadedAudioNotFoundError(f"Uploaded audio not found: {audio_id}")
    return uploaded_audio


def create_pending_job(
    db: Session,
    uploaded_audio_id: int,
    model_id: int,
    parameters_json: str | None = None,
) -> SeparationJob:
    requested_at = current_time_text()
    job = SeparationJob(
        uploaded_audio_id=uploaded_audio_id,
        model_id=model_id,
        status="pending",
        requested_at=requested_at,
        parameters_json=parameters_json,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_job_running(db: Session, job: SeparationJob) -> None:
    started_at = current_time_text()
    job.status = "running"
    job.started_at = started_at
    job.error_message = None
    add_system_log(
        db=db,
        job_id=job.job_id,
        event_type="separation_started",
        message=f"Separation job {job.job_id} started.",
    )
    db.commit()
    return job


def add_system_log(
    db: Session,
    job_id: int,
    event_type: str,
    message: str,
    log_level: str = "INFO",
    source_component: str = "api",
) -> None:
    db.add(
        SystemLog(
            job_id=job_id,
            log_level=log_level,
            source_component=source_component,
            event_type=event_type,
            message=message,
            created_at=current_time_text(),
        )
    )


def create_algorithm_from_factory(
    algorithm_factory: type[SeparationAlgorithmFactory],
    model,
):
    if hasattr(algorithm_factory, "create_algorithm"):
        return algorithm_factory.create_algorithm(model)
    return algorithm_factory.resolve(model)


def mark_job_failed(
    db: Session,
    job: SeparationJob,
    error: Exception,
    processing_time_ms: int,
) -> None:
    job.status = "failed"
    job.completed_at = current_time_text()
    job.processing_time_ms = processing_time_ms
    job.error_message = str(error)
    add_system_log(
        db=db,
        job_id=job.job_id,
        event_type="separation_failed",
        message=f"Separation job {job.job_id} failed: {error}",
        log_level="ERROR",
    )
    db.commit()


def mark_visualization_failed(
    db: Session,
    job_id: int,
    error: Exception,
) -> None:
    add_system_log(
        db=db,
        job_id=job_id,
        event_type="visualization_failed",
        message=f"Visualization generation failed for job {job_id}: {error}",
        log_level="WARNING",
        source_component="filesystem",
    )


class SeparationService:
    """Facade that coordinates the full upload-to-result separation workflow."""

    def __init__(
        self,
        algorithm_factory: type[SeparationAlgorithmFactory] | None = None,
        strategy_resolver: type[SeparationAlgorithmFactory] | None = None,
        engine_class: type[SeparationEngine] = SeparationEngine,
    ) -> None:
        self.algorithm_factory = (
            algorithm_factory or strategy_resolver or ModelStrategyResolver
        )
        self.engine_class = engine_class

    def separate_uploaded_audio(
        self,
        db: Session,
        audio_id: int,
        model_id: int | None = None,
    ) -> SeparationResponse:
        queued_job = self.create_pending_separation_job(db, audio_id, model_id)
        return self.process_separation_job(db, queued_job.job_id)

    def create_pending_separation_job(
        self,
        db: Session,
        audio_id: int,
        model_id: int | None = None,
    ) -> SeparationResponse:
        uploaded_audio = get_uploaded_audio(db, audio_id)
        model = model_service.get_model_for_separation(db, model_id)

        input_path = storage_service.resolve_project_path(uploaded_audio.stored_path)
        if not input_path.is_file():
            raise FileNotFoundError(f"Uploaded WAV file is missing: {input_path}")

        strategy_key = model_service.strategy_key_for_model(model)
        job = create_pending_job(
            db=db,
            uploaded_audio_id=uploaded_audio.uploaded_audio_id,
            model_id=model.model_id,
            parameters_json=json.dumps(
                {
                    "strategy_key": strategy_key,
                    "method_type": getattr(model, "method_type", None),
                    "display_name": model.display_name or model.model_name,
                }
            ),
        )
        return SeparationResponse(
            job_id=job.job_id,
            status=job.status,
            heart_file_path=None,
            lung_file_path=None,
            processing_time_ms=0,
            model_id=model.model_id,
            strategy_key=strategy_key,
        )

    def process_separation_job(
        self,
        db: Session,
        job_id: int,
    ) -> SeparationResponse:
        workflow_start = time.perf_counter()
        job = db.get(SeparationJob, job_id)
        if job is None:
            raise SeparationJobNotFoundError(f"Separation job not found: {job_id}")

        if job.status == "completed" and job.result is not None:
            strategy_key = model_service.strategy_key_for_model(job.model)
            return SeparationResponse(
                job_id=job.job_id,
                status=job.status,
                heart_file_path=job.result.heart_file_path,
                lung_file_path=job.result.lung_file_path,
                processing_time_ms=job.processing_time_ms or 0,
                model_id=job.model_id,
                strategy_key=strategy_key,
            )

        try:
            mark_job_running(db, job)
            db.refresh(job)
            uploaded_audio = job.uploaded_audio
            model = job.model
            if uploaded_audio is None:
                raise UploadedAudioNotFoundError(
                    f"Uploaded audio missing for job: {job_id}"
                )
            if model is None:
                raise model_service.ModelConfigurationError(
                    f"Separation method missing for job: {job_id}"
                )

            model_service.validate_model_for_separation(model)
            algorithm = create_algorithm_from_factory(self.algorithm_factory, model)
            engine = self.engine_class(algorithm=algorithm, device_name="cpu")
            strategy_key = model_service.strategy_key_for_model(model)
            input_path = storage_service.resolve_project_path(uploaded_audio.stored_path)
            if not input_path.is_file():
                raise FileNotFoundError(f"Uploaded WAV file is missing: {input_path}")

            model_path = (
                storage_service.resolve_project_path(model.checkpoint_path)
                if model_service.model_requires_checkpoint(model)
                else storage_service.resolve_optional_project_path(model.checkpoint_path)
            )
            model_config_path = storage_service.resolve_optional_project_path(
                model.config_path
            )
            output_paths = storage_service.build_separation_output_paths(job.job_id)

            inference_result = engine.separate(
                input_wav_path=input_path,
                model_path=model_path,
                model_config_path=model_config_path,
                heart_output_path=output_paths.heart_file_path,
                lung_output_path=output_paths.lung_file_path,
            )

            result = result_service.create_separation_result(
                db=db,
                job_id=job.job_id,
                inference_result=inference_result,
            )
            db.flush()
            metrics = evaluation_service.evaluate_and_store_result(
                db=db,
                result=result,
                uploaded_audio=uploaded_audio,
                input_path=input_path,
                heart_output_path=output_paths.heart_file_path,
                lung_output_path=output_paths.lung_file_path,
                sample_rate_hz=inference_result.sample_rate_hz,
            )
            try:
                visualization_service.generate_visualizations(
                    job_id=job.job_id,
                    mixed_input_path=input_path,
                    heart_output_path=output_paths.heart_file_path,
                    lung_output_path=output_paths.lung_file_path,
                )
            except Exception as visualization_error:
                mark_visualization_failed(db, job.job_id, visualization_error)

            processing_time_ms = int((time.perf_counter() - workflow_start) * 1000)
            job.status = "completed"
            job.completed_at = current_time_text()
            job.processing_time_ms = processing_time_ms
            add_system_log(
                db=db,
                job_id=job.job_id,
                event_type="separation_completed",
                message=(
                    f"Separation job {job.job_id} completed in "
                    f"{processing_time_ms} ms using {strategy_key}. "
                    f"Reference metrics stored: {len(metrics)}."
                ),
            )
            db.commit()
            db.refresh(job)
            db.refresh(result)

            return SeparationResponse(
                job_id=job.job_id,
                status=job.status,
                heart_file_path=result.heart_file_path,
                lung_file_path=result.lung_file_path,
                processing_time_ms=job.processing_time_ms or processing_time_ms,
                model_id=model.model_id,
                strategy_key=strategy_key,
            )
        except Exception as error:
            processing_time_ms = int((time.perf_counter() - workflow_start) * 1000)
            db.rollback()
            try:
                mark_job_failed(db, job, error, processing_time_ms)
            except SQLAlchemyError:
                db.rollback()
            raise

    def run_background_job(self, job_id: int) -> None:
        db = SessionLocal()
        try:
            self.process_separation_job(db, job_id)
        except Exception:
            pass
        finally:
            db.close()


def separate_uploaded_audio(
    db: Session,
    audio_id: int,
    model_id: int | None = None,
) -> SeparationResponse:
    return SeparationService().separate_uploaded_audio(db, audio_id, model_id)


def create_pending_separation_job(
    db: Session,
    audio_id: int,
    model_id: int | None = None,
) -> SeparationResponse:
    return SeparationService().create_pending_separation_job(db, audio_id, model_id)


def run_queued_separation_job(job_id: int) -> None:
    SeparationService().run_background_job(job_id)
