"""Operator-only ADC Firebase lookup for the explicit first-admin CLI.

This provider is not used by the API runtime. It requires a separately
authorized local ADC session and never copies those credentials into Docker.
"""
import os
from uuid import uuid4

from app.access_foundation.identity import FirebaseIdentityAdapter, ProviderUnavailable


def configured_bootstrap_directory(settings):
    if os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
        raise ProviderUnavailable("Emulator mode is not configured for bootstrap.")
    try:
        import firebase_admin
        app = firebase_admin.initialize_app(
            options={"projectId": settings.firebase_project, "httpTimeout": 10},
            name=f"stethofuse-bootstrap-{uuid4().hex}",
        )
        return FirebaseIdentityAdapter(app=app, expected_project_id=settings.firebase_project)
    except Exception:
        raise ProviderUnavailable("Trusted Firebase bootstrap verification is unavailable.") from None
