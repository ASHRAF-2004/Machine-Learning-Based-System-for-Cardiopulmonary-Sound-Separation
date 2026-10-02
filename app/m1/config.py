"""Explicit isolated development paths. No implicit legacy database migration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIREBASE_PROJECT = "stethofuse-c18cd-3cca0"


@dataclass(frozen=True)
class Settings:
    database: Path
    private_storage: Path
    firebase_project: str = FIREBASE_PROJECT
    max_upload_bytes: int = 25 * 1024 * 1024
    separation_enabled: bool = False

    def validate(self) -> None:
        database, storage = self.database.resolve(), self.private_storage.resolve()
        if not self.database.is_absolute() or not self.private_storage.is_absolute():
            raise ValueError("M1 paths must be explicit absolute paths.")
        forbidden = [PROJECT_ROOT / "database", PROJECT_ROOT / "storage",
                     PROJECT_ROOT / "frontend", PROJECT_ROOT / "app" / "static"]
        if any(database.is_relative_to(p.resolve()) or storage.is_relative_to(p.resolve())
               or p.resolve().is_relative_to(storage) for p in forbidden):
            raise ValueError("M1 paths must be separate from legacy/private/public source paths.")
        if storage == Path(storage.anchor) or database.is_relative_to(storage):
            raise ValueError("Private media must not contain the database or a filesystem root.")
        if self.firebase_project != FIREBASE_PROJECT:
            raise ValueError("Unexpected Firebase project.")

    @classmethod
    def from_environment(cls) -> Settings | None:
        database = os.environ.get("STETHOFUSE_M1_DATABASE")
        storage = os.environ.get("STETHOFUSE_M1_PRIVATE_STORAGE")
        if not database or not storage:
            return None
        settings = cls(Path(database), Path(storage), os.environ.get("STETHOFUSE_FIREBASE_PROJECT", FIREBASE_PROJECT),
                       separation_enabled=os.environ.get("STETHOFUSE_SEPARATION_ENABLED") == "1")
        settings.validate()
        return settings
