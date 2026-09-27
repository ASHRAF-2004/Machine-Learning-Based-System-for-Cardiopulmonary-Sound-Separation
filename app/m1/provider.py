"""Explicit production identity-verifier configuration."""
import os

from app.access_foundation import DisabledVerifier
from app.access_foundation.identity import ProviderUnavailable
from .firebase_remote import FirebaseRestIdentityVerifier


def configured_verifier(settings):
    if os.environ.get("STETHOFUSE_FIREBASE_ENABLED") != "1":
        return DisabledVerifier()
    if os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
        raise ProviderUnavailable("Emulator mode is not configured for this application.")
    api_key = os.environ.get("STETHOFUSE_FIREBASE_API_KEY", "")
    if not api_key:
        raise ProviderUnavailable("Firebase Auth API key is not configured.")
    try:
        return FirebaseRestIdentityVerifier(
            project_id=settings.firebase_project,
            api_key=api_key,
        )
    except Exception:
        raise ProviderUnavailable("Firebase Auth configuration is invalid.") from None
