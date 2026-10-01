"""LOCAL identity review only; reuse the established fixed test verifier.

Never imported by the product API entry point. No arbitrary tokens accepted.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARING_REVIEW = "--sharing-review" in sys.argv
SHARED_REVIEW = "--shared-review" in sys.argv
assert not (SHARING_REVIEW and SHARED_REVIEW), "Choose one local review mode"
REVIEW = ROOT / (".local/shared-review" if SHARED_REVIEW else ".local/handle-sharing-review" if SHARING_REVIEW else ".local/identity-review")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend/tests/m1"))

from ml_fixture import TestVerifier
from app.m1.api import create_app
from app.m1.config import Settings
from app.m1.store import M1Store
from app.access_foundation import Role
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
    if SHARED_REVIEW:
        # Reuse the established ml_fixture setup ONLY in this fixed local copy.
        # Never change the role/profile of an existing review account.
        admin_identity = verifier.lookup_existing("admin")
        if not store.account_exists(admin_identity):
            store.register_verified_identity(admin_identity)
            assert store.bootstrap_first_admin(verifier, provider_uid="admin", confirmed_uid="admin")
            store.update_profile(admin_identity, "Local Acceptance Administrator")
        assert store.me(admin_identity)["role"] == "admin", "Existing local admin role differs; review required"
        analyst_identity = verifier.lookup_existing("analyst")
        if not store.account_exists(analyst_identity):
            analyst_account = store.register_verified_identity(analyst_identity)
            store.change_account(admin_identity, analyst_account.id,
                                 confirmed_target_id=analyst_account.id, role=Role.AUDIO_ANALYST)
            store.update_profile(analyst_identity, "Local Audio Analyst")
        assert store.me(analyst_identity)["role"] == "audio_analyst", "Existing analyst role differs; review required"
    uvicorn.run(create_app(settings, verifier=verifier), host="127.0.0.1", port=8199 if SHARED_REVIEW else 8198 if SHARING_REVIEW else 8197,
                access_log=False, log_level="warning")
