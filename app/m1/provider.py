"""Explicit production identity-verifier configuration.

The API container performs public-key JWT verification locally and calls the
small public Cloud Run verifier for revocation/current Firebase user state. It
does not load Google ADC or developer credentials.
"""
import os

from app.access_foundation import DisabledVerifier
from app.access_foundation.identity import ProviderUnavailable
from .firebase_remote import CloudRunFirebaseIdentityVerifier


def configured_verifier(settings):
    if os.environ.get("STETHOFUSE_FIREBASE_ENABLED") != "1":
        return DisabledVerifier()
    if os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
        raise ProviderUnavailable("Emulator mode is not configured for this application.")
    service_url = os.environ.get("STETHOFUSE_FIREBASE_VERIFIER_URL", "")
    if not service_url:
        raise ProviderUnavailable("Firebase current-user verifier is not configured.")
    try:
        return CloudRunFirebaseIdentityVerifier(
            project_id=settings.firebase_project,
            service_url=service_url,
        )
    except Exception:
        raise ProviderUnavailable("Firebase verifier configuration is invalid.") from None
