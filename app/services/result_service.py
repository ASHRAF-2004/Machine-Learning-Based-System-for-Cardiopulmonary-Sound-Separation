"""Result, download, and history lookup logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from app.database.db import PROJECT_ROOT
from app.models.db_models import SeparationJob, SeparationResult


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


def get_result_details(db: Session, job_id: int) -> dict[str, object]:
    job = get_job_or_raise(db, job_id)
    result = job.result

    return {
        "job_id": job.job_id,
        "status": job.status,
        "uploaded_audio": format_uploaded_audio(job),
        "heart_file_path": result.heart_file_path if result else None,
        "lung_file_path": result.lung_file_path if result else None,
        "created_at": result.created_at if result else None,
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


def get_history(db: Session, limit: int = 20) -> list[dict[str, object]]:
    jobs = (
        db.query(SeparationJob)
        .options(
            joinedload(SeparationJob.uploaded_audio),
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
            }
        )

    return history
