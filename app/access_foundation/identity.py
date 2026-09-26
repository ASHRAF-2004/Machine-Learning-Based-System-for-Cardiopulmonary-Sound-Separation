"""Trusted identity boundary. Never construct identities from request JSON/headers.

No JWT decoding, credential loading, network access or SDK initialization occurs
on import. The optional Firebase adapter must be explicitly configured by trusted
server code; no live provider is configured by this preparation package.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


class AuthenticationDenied(PermissionError):
    """Generic failure; never include provider exceptions or tokens in responses."""


@dataclass(frozen=True)
class VerifiedIdentity:
    """Internal adapter result, NOT a request schema or client-supplied principal."""

    uid: str
    email: str
    email_verified: bool
    disabled: bool = False


def require_verified(identity: VerifiedIdentity) -> None:
    if (
        not isinstance(identity, VerifiedIdentity)
        or not isinstance(identity.uid, str)
        or not 1 <= len(identity.uid) <= 128
        or identity.uid != identity.uid.strip()
        or not isinstance(identity.email, str)
        or not identity.email
        or identity.email_verified is not True
        or identity.disabled is not False
    ):
        raise AuthenticationDenied("Verified active identity required.")


class IdentityVerifier(Protocol):
    def verify(self, id_token: str) -> VerifiedIdentity: ...


class IdentityDirectory(Protocol):
    def lookup_existing(self, uid: str) -> VerifiedIdentity: ...


class DisabledVerifier:
    """Safe default until provider integration is explicitly approved/configured."""

    def verify(self, id_token: str) -> VerifiedIdentity:
        raise AuthenticationDenied("Authentication provider is not configured.")

    def lookup_existing(self, uid: str) -> VerifiedIdentity:
        raise AuthenticationDenied("Authentication provider is not configured.")


class FirebaseIdentityAdapter:
    """Optional seam around the official Admin SDK, not an initialized integration.

    An explicit, already-initialized Firebase app and its expected project ID are
    required. Roles/custom claims are deliberately ignored: the local store owns
    workflow roles. Emulator credentials are rejected by this adapter.
    """

    def __init__(self, *, app: object, expected_project_id: str):
        if (
            not expected_project_id
            or app is None
            or getattr(app, "project_id", None) != expected_project_id
            or os.environ.get("FIREBASE_AUTH_EMULATOR_HOST")
        ):
            raise AuthenticationDenied("Explicit production identity configuration required.")
        # Optional dependency: never installed or imported by core/offline tests.
        try:
            from firebase_admin import auth
        except ImportError:
            raise AuthenticationDenied("Firebase Admin SDK is not installed.") from None
        self._auth = auth
        self._app = app

    def lookup_existing(self, uid: str) -> VerifiedIdentity:
        try:
            if os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
                raise AuthenticationDenied("Emulator identities are not accepted.")
            user = self._auth.get_user(uid, app=self._app)
            identity = VerifiedIdentity(
                uid=user.uid, email=user.email,
                email_verified=user.email_verified, disabled=user.disabled,
            )
            require_verified(identity)
            if identity.uid != uid:
                raise AuthenticationDenied("Identity mismatch.")
            return identity
        except Exception:
            # Includes absent/disabled users and provider outages. No fail-open.
            raise AuthenticationDenied("Identity could not be verified.") from None

    def verify(self, id_token: str) -> VerifiedIdentity:
        try:
            if not isinstance(id_token, str) or not id_token.strip():
                raise AuthenticationDenied("ID token required.")
            if os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
                raise AuthenticationDenied("Emulator identities are not accepted.")
            claims = self._auth.verify_id_token(
                id_token, app=self._app, check_revoked=True, clock_skew_seconds=0,
            )
            if claims.get("email_verified") is not True:
                raise AuthenticationDenied("Verified identity required.")
            # Current provider record also checks disabled/deleted/unverified state.
            return self.lookup_existing(claims["uid"])
        except Exception:
            raise AuthenticationDenied("Identity could not be verified.") from None
