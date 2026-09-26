"""Explicit Firebase runtime setup; uses approved project and external ADC only."""
import os
from uuid import uuid4

from app.access_foundation import DisabledVerifier
from app.access_foundation.identity import FirebaseIdentityAdapter, ProviderUnavailable


def configured_verifier(settings):
    if os.environ.get("STETHOFUSE_FIREBASE_ENABLED") != "1":
        return DisabledVerifier()
    if os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
        raise ProviderUnavailable("Emulator mode is not configured for this application.")
    try:
        import firebase_admin
        app = firebase_admin.initialize_app(
            options={"projectId": settings.firebase_project, "httpTimeout": 10},
            name=f"stethofuse-m1-{uuid4().hex}",
        )
        return FirebaseIdentityAdapter(app=app, expected_project_id=settings.firebase_project)
    except Exception:
        raise ProviderUnavailable("Firebase server credentials/configuration unavailable.") from None
