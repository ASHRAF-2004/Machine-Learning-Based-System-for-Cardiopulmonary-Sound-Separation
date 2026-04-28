"""Upload routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.db_models import UploadedAudio
from app.services.storage_service import remove_saved_file, save_uploaded_wav


router = APIRouter(tags=["uploads"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_audio(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        stored_audio = await save_uploaded_wav(file)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    finally:
        await file.close()

    audio_record = UploadedAudio(
        original_filename=stored_audio.original_filename,
        stored_path=stored_audio.stored_path,
        mime_type=stored_audio.mime_type,
        sample_rate_hz=stored_audio.sample_rate_hz,
        channels=stored_audio.channels,
        bit_depth=stored_audio.bit_depth,
        duration_sec=stored_audio.duration_sec,
        file_size_bytes=stored_audio.file_size_bytes,
    )

    db.add(audio_record)
    try:
        db.commit()
        db.refresh(audio_record)
    except SQLAlchemyError as error:
        db.rollback()
        remove_saved_file(stored_audio.absolute_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Audio file was saved, but the database insert failed.",
        ) from error

    return {
        "message": "Upload saved successfully.",
        "audio_id": audio_record.uploaded_audio_id,
        "original_filename": audio_record.original_filename,
        "stored_path": audio_record.stored_path,
        "mime_type": audio_record.mime_type,
        "sample_rate_hz": audio_record.sample_rate_hz,
        "channels": audio_record.channels,
        "bit_depth": audio_record.bit_depth,
        "duration_sec": audio_record.duration_sec,
        "file_size_bytes": audio_record.file_size_bytes,
        "uploaded_at": audio_record.uploaded_at,
    }
