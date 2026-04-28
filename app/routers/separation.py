"""Separation routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.services.separation_service import (
    ActiveModelNotFoundError,
    UploadedAudioNotFoundError,
    separate_uploaded_audio,
)


router = APIRouter(tags=["separation"])


@router.post("/separate/{audio_id}")
def separate_audio(audio_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        result = separate_uploaded_audio(db, audio_id)
    except UploadedAudioNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ActiveModelNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NeoSSNet inference failed: {error}",
        ) from error

    return {
        "job_id": result.job_id,
        "status": result.status,
        "heart_file_path": result.heart_file_path,
        "lung_file_path": result.lung_file_path,
        "processing_time_ms": result.processing_time_ms,
    }
