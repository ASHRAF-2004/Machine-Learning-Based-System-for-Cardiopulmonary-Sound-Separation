from __future__ import annotations

import shutil
import sqlite3
import uuid
from pathlib import Path

import pytest

from app.database.db import REQUIRED_RUNTIME_DIRECTORIES, initialize_database


REQUIRED_TABLES = {
    "uploaded_audio",
    "model",
    "separation_job",
    "separation_result",
    "evaluation_metric",
    "system_log",
}


@pytest.fixture()
def runtime_database_path():
    runtime_dir = (
        Path("storage/uploads/temp/test_database") / uuid.uuid4().hex
    ).resolve()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    try:
        yield runtime_dir / "cardiopulmonary.db"
    finally:
        shutil.rmtree(runtime_dir, ignore_errors=True)


def test_initialize_database_creates_database_tables_and_default_model(
    runtime_database_path,
) -> None:
    database_path = runtime_database_path

    initialize_database(database_path=database_path)

    assert database_path.is_file()

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        model_row = connection.execute(
            """
            SELECT checkpoint_path, config_path, is_active
            FROM model
            WHERE model_name = 'NeoSSNet'
              AND version = '1.0'
            """
        ).fetchone()

    assert REQUIRED_TABLES <= tables
    assert model_row == (
        "storage/ml_models/model_best.pt",
        "storage/ml_models/model.yaml",
        1,
    )


def test_initialize_database_creates_required_runtime_directories(
    runtime_database_path,
) -> None:
    initialize_database(database_path=runtime_database_path)

    missing_directories = [
        directory.as_posix()
        for directory in REQUIRED_RUNTIME_DIRECTORIES
        if not directory.is_dir()
    ]

    assert missing_directories == []
