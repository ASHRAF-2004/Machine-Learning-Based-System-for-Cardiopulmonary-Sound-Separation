"""Result, download, and history routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.services.result_service import (
    JobNotFoundError,
    OutputNotFoundError,
    get_download_file,
    get_history,
    get_result_details,
)


router = APIRouter(tags=["results"])


@router.get("/result/{job_id}")
def result_details(job_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return get_result_details(db, job_id)
    except JobNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.get("/download/{job_id}/heart")
def download_heart(job_id: int, db: Session = Depends(get_db)) -> FileResponse:
    try:
        file_info = get_download_file(db, job_id, "heart")
    except (JobNotFoundError, OutputNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return FileResponse(
        path=file_info.path,
        media_type=file_info.media_type,
        filename=file_info.filename,
    )


@router.get("/download/{job_id}/lung")
def download_lung(job_id: int, db: Session = Depends(get_db)) -> FileResponse:
    try:
        file_info = get_download_file(db, job_id, "lung")
    except (JobNotFoundError, OutputNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return FileResponse(
        path=file_info.path,
        media_type=file_info.media_type,
        filename=file_info.filename,
    )


@router.get("/history")
def history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return get_history(db, limit=limit)
