"""Database connection helpers for the FastAPI app."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_DIR = PROJECT_ROOT / "database"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
SEED_PATH = DATABASE_DIR / "seed.sql"
DATABASE_PATH = DATABASE_DIR / "cardiopulmonary.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

REQUIRED_RUNTIME_DIRECTORIES = (
    DATABASE_DIR,
    PROJECT_ROOT / "storage" / "uploads" / "raw",
    PROJECT_ROOT / "storage" / "uploads" / "temp",
    PROJECT_ROOT / "storage" / "outputs" / "heart",
    PROJECT_ROOT / "storage" / "outputs" / "lung",
    PROJECT_ROOT / "storage" / "visualizations",
    PROJECT_ROOT / "storage" / "logs",
    PROJECT_ROOT / "storage" / "ml_models",
)

MODEL_REGISTRY_COLUMN_MIGRATIONS = {
    "display_name": "ALTER TABLE model ADD COLUMN display_name TEXT",
    "strategy_key": "ALTER TABLE model ADD COLUMN strategy_key TEXT",
    "method_type": (
        "ALTER TABLE model ADD COLUMN method_type TEXT "
        "NOT NULL DEFAULT 'deep_learning'"
    ),
    "requires_checkpoint": (
        "ALTER TABLE model ADD COLUMN requires_checkpoint INTEGER "
        "NOT NULL DEFAULT 1"
    ),
    "is_default": (
        "ALTER TABLE model ADD COLUMN is_default INTEGER "
        "NOT NULL DEFAULT 0"
    ),
}

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    future=True,
)

Base = declarative_base()


def ensure_runtime_directories() -> None:
    """Create folders that are required before upload or inference can run."""

    for directory in REQUIRED_RUNTIME_DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)


def _execute_sql_file(connection: sqlite3.Connection, sql_path: Path) -> None:
    sql_text = sql_path.read_text(encoding="utf-8").strip()
    if sql_text:
        connection.executescript(sql_text)


def _existing_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _ensure_model_registry_columns(connection: sqlite3.Connection) -> None:
    columns = _existing_columns(connection, "model")
    for column_name, statement in MODEL_REGISTRY_COLUMN_MIGRATIONS.items():
        if column_name not in columns:
            connection.execute(statement)

    connection.execute(
        """
        UPDATE model
        SET
            display_name = COALESCE(display_name, model_name),
            strategy_key = COALESCE(
                strategy_key,
                LOWER(REPLACE(architecture, ' ', ''))
            ),
            method_type = COALESCE(
                method_type,
                CASE
                    WHEN LOWER(architecture) = 'neossnet' THEN 'deep_learning'
                    ELSE 'baseline'
                END
            ),
            requires_checkpoint = COALESCE(
                requires_checkpoint,
                CASE
                    WHEN LOWER(architecture) = 'neossnet' THEN 1
                    ELSE 0
                END
            )
        """
    )


def _table_sql(connection: sqlite3.Connection, table_name: str) -> str:
    row = connection.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row[0] if row and row[0] else ""


def _ensure_pending_job_status(
    connection: sqlite3.Connection,
    schema_path: Path,
) -> None:
    table_sql = _table_sql(connection, "separation_job")
    if not table_sql or "'pending'" in table_sql:
        return

    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.executescript(
        """
        CREATE TABLE separation_job_new (
            job_id INTEGER PRIMARY KEY,
            uploaded_audio_id INTEGER NOT NULL,
            model_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'pending',
                    'queued',
                    'running',
                    'completed',
                    'failed',
                    'cancelled'
                )
            ),
            requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            completed_at TEXT,
            processing_time_ms INTEGER CHECK (
                processing_time_ms IS NULL OR processing_time_ms >= 0
            ),
            parameters_json TEXT,
            error_message TEXT,
            FOREIGN KEY (uploaded_audio_id)
                REFERENCES uploaded_audio(uploaded_audio_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (model_id)
                REFERENCES model(model_id)
                ON DELETE RESTRICT
        );

        INSERT INTO separation_job_new (
            job_id,
            uploaded_audio_id,
            model_id,
            status,
            requested_at,
            started_at,
            completed_at,
            processing_time_ms,
            parameters_json,
            error_message
        )
        SELECT
            job_id,
            uploaded_audio_id,
            model_id,
            status,
            requested_at,
            started_at,
            completed_at,
            processing_time_ms,
            parameters_json,
            error_message
        FROM separation_job;

        DROP TABLE separation_job;
        ALTER TABLE separation_job_new RENAME TO separation_job;
        """
    )
    connection.commit()
    connection.execute("PRAGMA foreign_keys = ON")
    _execute_sql_file(connection, schema_path)


def initialize_database(
    database_path: Path = DATABASE_PATH,
    schema_path: Path = SCHEMA_PATH,
    seed_path: Path | None = SEED_PATH,
) -> None:
    """Create the SQLite database, schema, seed row, and runtime folders."""

    ensure_runtime_directories()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if not schema_path.is_file():
        raise FileNotFoundError(f"Database schema file is missing: {schema_path}")

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _execute_sql_file(connection, schema_path)
        _ensure_pending_job_status(connection, schema_path)
        _ensure_model_registry_columns(connection)
        if seed_path is not None and seed_path.is_file():
            _execute_sql_file(connection, seed_path)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
