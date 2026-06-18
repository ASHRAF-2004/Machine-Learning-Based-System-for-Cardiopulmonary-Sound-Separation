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
    PROJECT_ROOT / "storage" / "logs",
    PROJECT_ROOT / "storage" / "ml_models",
)

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
        if seed_path is not None and seed_path.is_file():
            _execute_sql_file(connection, seed_path)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
