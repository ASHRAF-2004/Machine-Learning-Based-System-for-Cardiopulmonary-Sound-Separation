"""Validate project folders, SQLite tables, and HLS-CMDS dataset hygiene."""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "database" / "cardiopulmonary.db"
DATASET_ROOT = PROJECT_ROOT / "datasets" / "hls_cmds"

REQUIRED_FOLDERS = [
    "app",
    "app/routers",
    "app/services",
    "app/database",
    "app/models",
    "app/ml",
    "app/static",
    "database",
    "datasets",
    "datasets/hls_cmds",
    "storage",
    "storage/uploads",
    "storage/uploads/raw",
    "storage/uploads/temp",
    "storage/outputs",
    "storage/outputs/heart",
    "storage/outputs/lung",
    "storage/ml_models",
    "storage/logs",
    "scripts",
    "tests",
]

DATASET_FOLDERS = [
    "datasets/hls_cmds/raw",
    "datasets/hls_cmds/raw/HS",
    "datasets/hls_cmds/raw/LS",
    "datasets/hls_cmds/raw/Mix",
    "datasets/hls_cmds/metadata",
    "datasets/hls_cmds/processed",
    "datasets/hls_cmds/processed/train",
    "datasets/hls_cmds/processed/train/heart",
    "datasets/hls_cmds/processed/train/lung",
    "datasets/hls_cmds/processed/train/mixed",
    "datasets/hls_cmds/processed/val",
    "datasets/hls_cmds/processed/val/heart",
    "datasets/hls_cmds/processed/val/lung",
    "datasets/hls_cmds/processed/val/mixed",
    "datasets/hls_cmds/processed/test",
    "datasets/hls_cmds/processed/test/heart",
    "datasets/hls_cmds/processed/test/lung",
    "datasets/hls_cmds/processed/test/mixed",
]

REQUIRED_TABLES = {
    "uploaded_audio",
    "model",
    "separation_job",
    "separation_result",
    "evaluation_metric",
    "system_log",
}


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str = ""


def project_path(relative_path: str) -> Path:
    return PROJECT_ROOT / Path(relative_path)


def format_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def check_folders(title: str, folders: list[str]) -> list[CheckResult]:
    results: list[CheckResult] = []

    for folder in folders:
        path = project_path(folder)
        results.append(
            CheckResult(
                name=f"{title}: {folder}",
                passed=path.is_dir(),
                details="" if path.is_dir() else "missing folder",
            )
        )

    return results


def check_database_file() -> CheckResult:
    return CheckResult(
        name="Database file: database/cardiopulmonary.db",
        passed=DATABASE_PATH.is_file(),
        details="" if DATABASE_PATH.is_file() else "missing database file",
    )


def fetch_database_tables() -> set[str]:
    db_uri = f"file:{DATABASE_PATH.as_posix()}?mode=ro"
    with sqlite3.connect(db_uri, uri=True) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    return {row[0] for row in rows}


def check_database_tables() -> CheckResult:
    if not DATABASE_PATH.is_file():
        return CheckResult(
            name="Database tables",
            passed=False,
            details="database file missing, cannot inspect tables",
        )

    try:
        existing_tables = fetch_database_tables()
    except sqlite3.Error as error:
        return CheckResult(
            name="Database tables",
            passed=False,
            details=f"SQLite error: {error}",
        )

    missing_tables = sorted(REQUIRED_TABLES - existing_tables)
    if missing_tables:
        return CheckResult(
            name="Database tables",
            passed=False,
            details="missing tables: " + ", ".join(missing_tables),
        )

    return CheckResult(
        name="Database tables",
        passed=True,
        details="found required tables: " + ", ".join(sorted(REQUIRED_TABLES)),
    )


def find_dataset_junk() -> list[Path]:
    if not DATASET_ROOT.is_dir():
        return []

    junk_paths: list[Path] = []
    for path in DATASET_ROOT.rglob("*"):
        if path.name == ".DS_Store" or path.name.startswith("._"):
            junk_paths.append(path)
        elif path.is_dir() and path.name == "__MACOSX":
            junk_paths.append(path)

    return sorted(junk_paths, key=lambda item: format_path(item).lower())


def check_dataset_junk() -> CheckResult:
    junk_paths = find_dataset_junk()
    if not junk_paths:
        return CheckResult(
            name="Dataset junk files",
            passed=True,
            details="no .DS_Store, ._* files, or __MACOSX folders found",
        )

    preview = ", ".join(format_path(path) for path in junk_paths[:5])
    if len(junk_paths) > 5:
        preview += f", ... ({len(junk_paths)} total)"

    return CheckResult(
        name="Dataset junk files",
        passed=False,
        details=preview,
    )


def print_result(result: CheckResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    message = f"[{status}] {result.name}"
    if result.details:
        message += f" - {result.details}"
    print(message)


def main() -> int:
    results: list[CheckResult] = []
    results.extend(check_folders("Required folder", REQUIRED_FOLDERS))
    results.append(check_database_file())
    results.append(check_database_tables())
    results.extend(check_folders("Dataset folder", DATASET_FOLDERS))
    results.append(check_dataset_junk())

    for result in results:
        print_result(result)

    passed_count = sum(1 for result in results if result.passed)
    failed_count = len(results) - passed_count

    print()
    print("Project check summary")
    print(f"PASS: {passed_count}")
    print(f"FAIL: {failed_count}")
    print(f"TOTAL: {len(results)}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
