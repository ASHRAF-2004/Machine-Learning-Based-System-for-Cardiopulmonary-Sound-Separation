"""Initialize the SQLite database and required runtime folders."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.db import DATABASE_PATH, SessionLocal, initialize_database  # noqa: E402
from app.services.model_service import ensure_finetuned_model_record  # noqa: E402


def main() -> int:
    initialize_database()
    db = SessionLocal()
    try:
        ensure_finetuned_model_record(db)
    finally:
        db.close()
    print(f"Database ready: {DATABASE_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
