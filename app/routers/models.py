"""Model selection routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.services.model_service import format_model, list_models


router = APIRouter(tags=["models"])


@router.get("/models")
def available_models(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return [format_model(model) for model in list_models(db)]


@router.get("/methods")
def available_methods(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return available_models(db)
