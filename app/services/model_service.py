"""Model lookup helpers for separation model selection."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.db_models import Model


class ModelServiceError(Exception):
    pass


class ActiveModelNotFoundError(ModelServiceError):
    pass


class ModelNotFoundError(ModelServiceError):
    pass


class ModelConfigurationError(ModelServiceError):
    pass


def list_models(db: Session) -> list[Model]:
    return (
        db.query(Model)
        .order_by(Model.is_active.desc(), Model.model_name.asc(), Model.version.asc())
        .all()
    )


def get_active_model(db: Session) -> Model:
    model = (
        db.query(Model)
        .filter(Model.is_active == 1)
        .order_by(Model.model_id.desc())
        .first()
    )
    if model is None:
        raise ActiveModelNotFoundError("No active separation model is configured.")
    return model


def get_model_by_id(db: Session, model_id: int) -> Model:
    model = db.get(Model, model_id)
    if model is None:
        raise ModelNotFoundError(f"Separation model not found: {model_id}")
    return model


def validate_model_for_separation(model: Model) -> None:
    if not model.checkpoint_path:
        raise ModelConfigurationError(
            f"Model {model.model_id} must have checkpoint_path."
        )

    if (model.architecture or "").strip().lower() == "neossnet" and not model.config_path:
        raise ModelConfigurationError(
            f"NeoSSNet model {model.model_id} must have config_path."
        )


def get_model_for_separation(db: Session, model_id: int | None = None) -> Model:
    model = get_model_by_id(db, model_id) if model_id is not None else get_active_model(db)
    validate_model_for_separation(model)
    return model


def format_model(model: Model) -> dict[str, object]:
    return {
        "model_id": model.model_id,
        "model_name": model.model_name,
        "version": model.version,
        "architecture": model.architecture,
        "framework": model.framework,
        "description": model.description,
        "is_active": bool(model.is_active),
    }
