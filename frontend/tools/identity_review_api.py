"""LOCAL identity review only; reuse the established fixed test verifier.

Never imported by the product API entry point. No arbitrary tokens accepted.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / ".local/identity-review"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend/tests/m1"))

from ml_fixture import TestVerifier
from app.m1.api import create_app
from app.m1.config import Settings
from app.m1.store import M1Store
import uvicorn


if __name__ == "__main__":
    settings = Settings(REVIEW / "data/review.sqlite3", REVIEW / "private", separation_enabled=True)
    settings.validate()
    assert settings.database.resolve().is_relative_to(REVIEW)
    assert settings.private_storage.resolve().is_relative_to(REVIEW)
    verifier = TestVerifier()
    store = M1Store(settings.database)
    store.initialize()
    store.register_verified_identity(verifier.lookup_existing("alice"))
    assert store.me(verifier.lookup_existing("alice"))["role"] == "healthcare_staff"
    uvicorn.run(create_app(settings, verifier=verifier), host="127.0.0.1", port=8197,
                access_log=False, log_level="warning")
