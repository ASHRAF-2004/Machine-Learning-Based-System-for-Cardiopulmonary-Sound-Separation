"""Production Firebase identity checks split across local and Google trust boundaries."""
from __future__ import annotations

import json
from urllib.parse import urlsplit

from app.access_foundation.identity import (
    AuthenticationDenied,
    EmailVerificationRequired,
    ProviderAccountDisabled,
    ProviderUnavailable,
    VerifiedIdentity,
)
from app.access_foundation.firebase_token import FirebaseIdTokenVerifier

_MAX_RESPONSE_BYTES = 4096


def _validate_verifier_url(url: str) -> str:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname
            or parsed.hostname == "run.app"
            or not parsed.hostname.endswith(".run.app")
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
        raise ValueError("Firebase verifier must be an exact HTTPS Cloud Run service URL.")
    return url.rstrip("/") + "/v1/verify"


class CloudRunFirebaseIdentityVerifier:
    """Locally verify JWT integrity, then ask Cloud Run only for current Auth state."""

    def __init__(self, *, project_id: str, service_url: str, client=None,
                 token_verifier: FirebaseIdTokenVerifier | None = None):
        self.endpoint = _validate_verifier_url(service_url)
        self._token_verifier = token_verifier or FirebaseIdTokenVerifier(project_id)
        if client is None:
            try:
                import httpx
                client = httpx.Client(
                    # Cloud Run may need two sequential Firebase Auth reads: token
                    # revocation validation and a fresh current-user check.
                    timeout=httpx.Timeout(38.0, connect=4.0),
                    follow_redirects=False,
                    trust_env=False,
                    limits=httpx.Limits(max_connections=16, max_keepalive_connections=8),
                    headers={"Accept": "application/json"},
                )
            except Exception:
                raise ProviderUnavailable("Firebase verifier transport is unavailable.") from None
        self._client = client

    def close(self):
        close = getattr(self._client, "close", None)
        if close:
            close()

    def verify(self, id_token: str) -> VerifiedIdentity:
        claims = self._token_verifier.verify(id_token)
        if claims.get("email_verified") is False:
            raise EmailVerificationRequired("Email verification required.")
        try:
            with self._client.stream(
                "POST", self.endpoint, json={"id_token": id_token},
                headers={"Content-Type": "application/json"},
            ) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > _MAX_RESPONSE_BYTES:
                        raise ProviderUnavailable("Firebase verifier response is invalid.")
                try:
                    payload = json.loads(body) if body else {}
                except (ValueError, TypeError):
                    payload = {}
                status_code = response.status_code
        except ProviderUnavailable:
            raise
        except Exception:
            raise ProviderUnavailable("Firebase verifier is unavailable.") from None

        # Only service-generated, bounded error envelopes are trusted. A Cloud Run
        # IAM/platform rejection or unexpected body is an outage, never token proof.
        if status_code in (401, 403) and isinstance(payload, dict):
            error = payload.get("error")
            if status_code == 401 and error == "invalid_identity":
                raise AuthenticationDenied("Identity could not be verified.")
            if status_code == 403 and error == "email_verification_required":
                raise EmailVerificationRequired("Email verification required.")
            if status_code == 403 and error == "account_disabled":
                raise ProviderAccountDisabled("Account disabled.")
        if status_code != 200:
            raise ProviderUnavailable("Firebase verifier is unavailable.")
        if (not isinstance(payload, dict)
                or set(payload) != {"uid", "email", "email_verified"}
                or payload.get("uid") != claims.get("sub")
                or not isinstance(payload.get("email"), str)
                or not payload["email"]
                or payload.get("email_verified") is not True):
            if isinstance(payload, dict) and payload.get("email_verified") is False:
                raise EmailVerificationRequired("Email verification required.")
            raise ProviderUnavailable("Firebase verifier returned an invalid response.")
        return VerifiedIdentity(payload["uid"], payload["email"], True, False)
