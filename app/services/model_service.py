"""Model lookup helpers for separation model selection."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.database.db import PROJECT_ROOT
from app.models.db_models import Model


class ModelServiceError(Exception):
    pass


class ActiveModelNotFoundError(ModelServiceError):
    pass


class ModelNotFoundError(ModelServiceError):
    pass


class ModelConfigurationError(ModelServiceError):
    pass


FINETUNED_MODEL_NAME = "NeoSSNet HLS Fine-tuned"
FINETUNED_MODEL_VERSION = "1.0"
FINETUNED_CHECKPOINT_PATH = "storage/ml_models/neossnet_hls_finetuned.pt"
FINETUNED_CONFIG_PATH = "storage/ml_models/neossnet_hls_finetuned.yaml"


def _resolve_project_model_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def ensure_finetuned_model_record(
    db: Session,
    checkpoint_path: str | Path = FINETUNED_CHECKPOINT_PATH,
    config_path: str | Path = FINETUNED_CONFIG_PATH,
) -> Model | None:
    """Enable the HLS fine-tuned NeoSSNet registry row when files exist."""

    checkpoint_text = (
        str(checkpoint_path).replace("\\", "/")
        if not Path(checkpoint_path).is_absolute()
        else str(checkpoint_path)
    )
    config_text = (
        str(config_path).replace("\\", "/")
        if not Path(config_path).is_absolute()
        else str(config_path)
    )
    checkpoint_abs = _resolve_project_model_path(checkpoint_path)
    config_abs = _resolve_project_model_path(config_path)

    model = (
        db.query(Model)
        .filter(
            Model.model_name == FINETUNED_MODEL_NAME,
            Model.version == FINETUNED_MODEL_VERSION,
        )
        .first()
    )
    files_exist = checkpoint_abs.is_file() and config_abs.is_file()
    if not files_exist:
        if model is not None and model.is_active:
            model.is_active = 0
            model.is_default = 0
            db.commit()
        return model

    if model is None:
        model = Model(
            model_name=FINETUNED_MODEL_NAME,
            display_name=FINETUNED_MODEL_NAME,
            version=FINETUNED_MODEL_VERSION,
            architecture="NeoSSNet",
            framework="PyTorch",
            checkpoint_path=checkpoint_text,
            config_path=config_text,
            strategy_key="neossnet",
            method_type="deep_learning",
            requires_checkpoint=1,
            is_active=1,
            is_default=0,
            description=(
                "NeoSSNet checkpoint fine-tuned on the processed HLS-CMDS "
                "train/validation split."
            ),
        )
        db.add(model)
    else:
        model.display_name = FINETUNED_MODEL_NAME
        model.architecture = "NeoSSNet"
        model.framework = "PyTorch"
        model.checkpoint_path = checkpoint_text
        model.config_path = config_text
        model.strategy_key = "neossnet"
        model.method_type = "deep_learning"
        model.requires_checkpoint = 1
        model.is_active = 1
        model.is_default = 0
        model.description = (
            "NeoSSNet checkpoint fine-tuned on the processed HLS-CMDS "
            "train/validation split."
        )

    db.commit()
    db.refresh(model)
    return model


def list_models(db: Session) -> list[Model]:
    return (
        db.query(Model)
        .order_by(
            Model.is_default.desc(),
            Model.is_active.desc(),
            Model.method_type.asc(),
            Model.model_name.asc(),
            Model.version.asc(),
        )
        .all()
    )


def get_default_model(db: Session) -> Model:
    model = (
        db.query(Model)
        .filter(Model.is_active == 1)
        .order_by(Model.is_default.desc(), Model.model_id.desc())
        .first()
    )
    if model is None:
        raise ActiveModelNotFoundError("No active separation method is configured.")
    return model


def get_active_model(db: Session) -> Model:
    return get_default_model(db)


def get_model_by_id(db: Session, model_id: int) -> Model:
    model = db.get(Model, model_id)
    if model is None:
        raise ModelNotFoundError(f"Separation method not found: {model_id}")
    return model


def strategy_key_for_model(model: Model) -> str:
    strategy_key = (getattr(model, "strategy_key", None) or "").strip().lower()
    if strategy_key:
        return strategy_key
    return (model.architecture or "").strip().replace(" ", "").lower()


def model_requires_checkpoint(model: Model) -> bool:
    requires_checkpoint = getattr(model, "requires_checkpoint", None)
    if requires_checkpoint is not None:
        return bool(requires_checkpoint)
    return strategy_key_for_model(model) == "neossnet"


def validate_model_for_separation(model: Model) -> None:
    if not model.is_active:
        raise ModelConfigurationError(
            f"Separation method {model.model_id} is disabled."
        )

    if model_requires_checkpoint(model) and not model.checkpoint_path:
        raise ModelConfigurationError(
            f"Separation method {model.model_id} must have checkpoint_path."
        )

    if strategy_key_for_model(model) == "neossnet" and not model.config_path:
        raise ModelConfigurationError(
            f"NeoSSNet method {model.model_id} must have config_path."
        )


def get_model_for_separation(db: Session, model_id: int | None = None) -> Model:
    model = get_model_by_id(db, model_id) if model_id is not None else get_default_model(db)
    validate_model_for_separation(model)
    return model


def format_model(model: Model) -> dict[str, object]:
    method_type = getattr(model, "method_type", None) or "deep_learning"
    strategy_key = strategy_key_for_model(model)
    return {
        "model_id": model.model_id,
        "model_name": model.model_name,
        "display_name": model.display_name or model.model_name,
        "version": model.version,
        "architecture": model.architecture,
        "strategy_key": strategy_key,
        "method_type": method_type,
        "method_type_label": {
            "baseline": "Conventional baseline",
            "decomposition": "Decomposition baseline",
            "deep_learning": "Deep learning model",
        }.get(method_type, method_type),
        "framework": model.framework,
        "description": model.description,
        "is_active": bool(model.is_active),
        "is_default": bool(getattr(model, "is_default", 0)),
        "requires_checkpoint": model_requires_checkpoint(model),
    }
