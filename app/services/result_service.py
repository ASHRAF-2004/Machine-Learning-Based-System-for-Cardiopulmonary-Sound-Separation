"""Result, download, and history lookup logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from app.database.db import PROJECT_ROOT
from app.ml.separation_algorithm import SeparationAlgorithmResult
from app.models.db_models import EvaluationMetric, SeparationJob, SeparationResult
from app.services import model_service, visualization_service
from app.services.storage_service import relative_project_path
from app.services.time_service import current_time_text


class ResultServiceError(Exception):
    pass


class JobNotFoundError(ResultServiceError):
    pass


class OutputNotFoundError(ResultServiceError):
    pass


@dataclass(frozen=True)
class DownloadFileInfo:
    path: Path
    filename: str
    media_type: str = "audio/wav"


def resolve_project_path(path_value: str | None) -> Path:
    if not path_value:
        raise OutputNotFoundError("Output path is missing.")

    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def get_job_or_raise(db: Session, job_id: int) -> SeparationJob:
    job = (
        db.query(SeparationJob)
        .options(
            joinedload(SeparationJob.uploaded_audio),
            joinedload(SeparationJob.model),
            joinedload(SeparationJob.result).joinedload(SeparationResult.metrics),
            joinedload(SeparationJob.result),
        )
        .filter(SeparationJob.job_id == job_id)
        .first()
    )
    if job is None:
        raise JobNotFoundError(f"Separation job not found: {job_id}")
    return job


def format_uploaded_audio(job: SeparationJob) -> dict[str, object] | None:
    uploaded_audio = job.uploaded_audio
    if uploaded_audio is None:
        return None

    return {
        "uploaded_audio_id": uploaded_audio.uploaded_audio_id,
        "original_filename": uploaded_audio.original_filename,
        "stored_path": uploaded_audio.stored_path,
        "sample_rate_hz": uploaded_audio.sample_rate_hz,
        "channels": uploaded_audio.channels,
        "duration_sec": uploaded_audio.duration_sec,
        "uploaded_at": uploaded_audio.uploaded_at,
    }


def format_metric(metric: EvaluationMetric) -> dict[str, object]:
    return {
        "metric_name": metric.metric_name,
        "metric_scope": metric.metric_scope,
        "metric_value": metric.metric_value,
        "metric_unit": metric.metric_unit,
        "reference_type": metric.reference_type,
        "recorded_at": metric.recorded_at,
    }


def format_separation_method(job: SeparationJob) -> dict[str, object] | None:
    if job.model is None:
        return None
    return model_service.format_model(job.model)


def get_result_details(db: Session, job_id: int) -> dict[str, object]:
    job = get_job_or_raise(db, job_id)
    result = job.result
    method = format_separation_method(job)
    heart_file_path = result.heart_file_path if result else None
    lung_file_path = result.lung_file_path if result else None

    return {
        "job_id": job.job_id,
        "status": job.status,
        "uploaded_audio": format_uploaded_audio(job),
        "separation_method": method,
        "selected_method_name": method["display_name"] if method else None,
        "method_name": method["display_name"] if method else None,
        "strategy_key": method["strategy_key"] if method else None,
        "method_type": method["method_type"] if method else None,
        "method_type_label": method["method_type_label"] if method else None,
        "heart_file_path": heart_file_path,
        "lung_file_path": lung_file_path,
        "heart_output_path": heart_file_path,
        "lung_output_path": lung_file_path,
        "heart_output_url": f"/download/{job.job_id}/heart" if result else None,
        "lung_output_url": f"/download/{job.job_id}/lung" if result else None,
        "created_at": result.created_at if result else None,
        "output_sample_rate_hz": result.output_sample_rate_hz if result else None,
        "output_duration_sec": result.output_duration_sec if result else None,
        "metrics": [format_metric(metric) for metric in result.metrics] if result else [],
        "visualizations": visualization_service.existing_visualizations(job.job_id),
        "processing_time_ms": job.processing_time_ms,
        "requested_at": job.requested_at,
        "completed_at": job.completed_at,
        "error_message": job.error_message,
    }


def get_download_file(db: Session, job_id: int, output_type: str) -> DownloadFileInfo:
    job = get_job_or_raise(db, job_id)
    result: SeparationResult | None = job.result
    if result is None:
        raise OutputNotFoundError(f"No separation result found for job: {job_id}")

    if output_type == "heart":
        output_path = resolve_project_path(result.heart_file_path)
    elif output_type == "lung":
        output_path = resolve_project_path(result.lung_file_path)
    else:
        raise OutputNotFoundError(f"Unknown output type: {output_type}")

    if not output_path.is_file():
        raise OutputNotFoundError(f"Output file is missing: {output_path}")

    return DownloadFileInfo(
        path=output_path,
        filename=output_path.name,
    )


def create_separation_result(
    db: Session,
    job_id: int,
    inference_result: SeparationAlgorithmResult,
) -> SeparationResult:
    result = SeparationResult(
        job_id=job_id,
        heart_file_path=relative_project_path(inference_result.heart_file_path),
        lung_file_path=relative_project_path(inference_result.lung_file_path),
        output_sample_rate_hz=inference_result.sample_rate_hz,
        output_duration_sec=inference_result.duration_sec,
        heart_file_size_bytes=inference_result.heart_file_size_bytes,
        lung_file_size_bytes=inference_result.lung_file_size_bytes,
        created_at=current_time_text(),
    )
    db.add(result)
    return result


def get_history(db: Session, limit: int = 20) -> list[dict[str, object]]:
    jobs = (
        db.query(SeparationJob)
        .options(
            joinedload(SeparationJob.uploaded_audio),
            joinedload(SeparationJob.model),
            joinedload(SeparationJob.result),
        )
        .order_by(SeparationJob.requested_at.desc(), SeparationJob.job_id.desc())
        .limit(limit)
        .all()
    )

    history: list[dict[str, object]] = []
    for job in jobs:
        result = job.result
        uploaded_audio = job.uploaded_audio
        method = format_separation_method(job)
        history.append(
            {
                "job_id": job.job_id,
                "status": job.status,
                "original_filename": (
                    uploaded_audio.original_filename if uploaded_audio else None
                ),
                "requested_at": job.requested_at,
                "completed_at": job.completed_at,
                "processing_time_ms": job.processing_time_ms,
                "heart_file_path": result.heart_file_path if result else None,
                "lung_file_path": result.lung_file_path if result else None,
                "separation_method": method,
                "strategy_key": method["strategy_key"] if method else None,
                "method_type": method["method_type"] if method else None,
                "method_name": method["display_name"] if method else None,
            }
        )

    return history
