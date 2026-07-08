from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.models.db_models import Model
from app.routers.models import available_methods, available_models
from app.services.model_service import (
    ensure_finetuned_model_record,
    get_model_for_separation,
    list_models,
)


@pytest.fixture()
def db_session():
    runtime_dir = Path("storage/uploads/temp/test_models") / uuid.uuid4().hex
    runtime_dir.mkdir(parents=True, exist_ok=True)

    database_path = runtime_dir / "test_models.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, future=True)

    db = TestingSession()
    try:
        yield db, runtime_dir
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        shutil.rmtree(runtime_dir, ignore_errors=True)


def seed_model(db, runtime_dir: Path, is_active: int = 1) -> Model:
    model_path = runtime_dir / "neossnet.pt"
    config_path = runtime_dir / "neossnet.yaml"
    model_path.write_bytes(b"weights")
    config_path.write_text("sample_rate: 4000", encoding="utf-8")

    model = Model(
        model_name="NeoSSNet",
        display_name="NeoSSNet",
        version="1.0",
        architecture="NeoSSNet",
        framework="PyTorch",
        checkpoint_path=str(model_path),
        config_path=str(config_path),
        strategy_key="neossnet",
        method_type="deep_learning",
        requires_checkpoint=1,
        description="Current working model",
        is_active=is_active,
        is_default=1,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def test_list_models_returns_available_models(db_session) -> None:
    db, runtime_dir = db_session
    model = seed_model(db, runtime_dir)

    models = list_models(db)

    assert len(models) == 1
    assert models[0].model_id == model.model_id
    assert models[0].architecture == "NeoSSNet"


def test_get_model_for_separation_defaults_to_active_model(db_session) -> None:
    db, runtime_dir = db_session
    model = seed_model(db, runtime_dir)

    selected = get_model_for_separation(db)

    assert selected.model_id == model.model_id


def test_models_route_returns_safe_model_payload(db_session) -> None:
    db, runtime_dir = db_session
    model = seed_model(db, runtime_dir)

    payload = available_models(db)

    assert payload == [
        {
            "model_id": model.model_id,
            "model_name": "NeoSSNet",
            "display_name": "NeoSSNet",
            "version": "1.0",
            "architecture": "NeoSSNet",
            "strategy_key": "neossnet",
            "method_type": "deep_learning",
            "method_type_label": "Deep learning model",
            "framework": "PyTorch",
            "description": "Current working model",
            "is_active": True,
            "is_default": True,
            "requires_checkpoint": True,
        }
    ]


def test_methods_route_alias_returns_same_payload(db_session) -> None:
    db, runtime_dir = db_session
    seed_model(db, runtime_dir)

    assert available_methods(db) == available_models(db)


def test_finetuned_neossnet_registry_row_is_added_when_files_exist(db_session) -> None:
    db, runtime_dir = db_session
    seed_model(db, runtime_dir)
    checkpoint = runtime_dir / "neossnet_hls_finetuned.pt"
    config = runtime_dir / "neossnet_hls_finetuned.yaml"
    checkpoint.write_bytes(b"weights")
    config.write_text("num_sources: 2", encoding="utf-8")

    fine_tuned = ensure_finetuned_model_record(
        db,
        checkpoint_path=checkpoint,
        config_path=config,
    )

    models = list_models(db)
    names = {model.model_name for model in models}
    assert fine_tuned is not None
    assert "NeoSSNet" in names
    assert "NeoSSNet HLS Fine-tuned" in names
    assert fine_tuned.strategy_key == "neossnet"
    assert fine_tuned.method_type == "deep_learning"
    assert fine_tuned.is_active == 1
    assert fine_tuned.is_default == 0
