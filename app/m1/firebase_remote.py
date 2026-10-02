"""Self-hosted Firebase identity checks using public JWT keys and Auth REST."""
from __future__ import annotations

import json
import re

from app.access_foundation.identity import (
    AuthenticationDenied,
    EmailVerificationRequired,
    ProviderAccountDisabled,
    ProviderUnavailable,
    VerifiedIdentity,
)
from app.access_foundation.firebase_token import FirebaseIdTokenVerifier

_LOOKUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:lookup"
_MAX_RESPONSE_BYTES = 4096
_INVALID_TOKEN_ERRORS = {
    "INVALID_ID_TOKEN", "TOKEN_EXPIRED", "USER_NOT_FOUND", "USER_DISABLED",
    "INVALID_LOGIN_CREDENTIALS",
}
_ERROR_CODE = re.compile(r"^([A-Z][A-Z0-9_]*)")


class FirebaseRestIdentityVerifier:
    """Verify Firebase JWT locally, then check live user/revocation state via REST.

    The API key identifies the Firebase project; it is not an authorization
    credential. The same user ID token is sent in the body over HTTPS. No role,
    account listing, or Firebase mutation API is exposed by this adapter.
    """

    def __init__(self, *, project_id: str, api_key: str, client=None,
                 token_verifier: FirebaseIdTokenVerifier | None = None):
        if not isinstance(api_key, str) or not api_key.strip() or len(api_key) > 256:
            raise ValueError("A Firebase Web API key is required.")
        self._api_key = api_key.strip()
        self._token_verifier = token_verifier or FirebaseIdTokenVerifier(project_id)
        if client is None:
            try:
                import httpx
                client = httpx.Client(
                    timeout=httpx.Timeout(8.0, connect=3.0),
                    follow_redirects=False,
                    trust_env=False,
                    limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
                    headers={"Accept": "application/json"},
                )
            except Exception:
                raise ProviderUnavailable("Firebase Auth transport is unavailable.") from None
        self._client = client

    def close(self):
        close = getattr(self._client, "close", None)
        if close:
            close()

    @staticmethod
    def _provider_error(status_code: int, body: bytes) -> None:
        try:
            value = json.loads(body) if body else {}
            message = value.get("error", {}).get("message", "") if isinstance(value, dict) else ""
            match = _ERROR_CODE.match(message) if isinstance(message, str) else None
            code = match.group(1) if match else ""
        except (ValueError, TypeError):
            code = ""
        if code == "USER_DISABLED":
            raise ProviderAccountDisabled("Account disabled.")
        if code in _INVALID_TOKEN_ERRORS:
            raise AuthenticationDenied("Identity could not be verified.")
        # Unknown 4xx responses may indicate API-key restrictions/configuration;
        # upstream failures are not misreported as a user's permission denial.
        raise ProviderUnavailable("Firebase Auth current-user check is unavailable.")

    def verify(self, id_token: str) -> VerifiedIdentity:
        claims = self._token_verifier.verify(id_token)
        if claims.get("email_verified") is False:
            raise EmailVerificationRequired("Email verification required.")
        try:
            with self._client.stream(
                "POST", _LOOKUP_URL,
                params={"key": self._api_key},
                json={"idToken": id_token},
                headers={"Content-Type": "application/json"},
            ) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > _MAX_RESPONSE_BYTES:
                        raise ProviderUnavailable("Firebase Auth response is invalid.")
                status_code = response.status_code
        except ProviderUnavailable:
            raise
        except Exception:
            # Never propagate httpx diagnostics: they can contain request URLs.
            raise ProviderUnavailable("Firebase Auth current-user check is unavailable.") from None

        if status_code != 200:
            self._provider_error(status_code, bytes(body))
        try:
            payload = json.loads(body) if body else None
            users = payload.get("users") if isinstance(payload, dict) else None
            user = users[0] if isinstance(users, list) and len(users) == 1 else None
            if not isinstance(user, dict):
                raise ValueError
            uid = claims.get("sub")
            local_id = user.get("localId")
            # Firebase may omit this boolean when false (JSON default-value
            # omission). Default only an absent field; null/strings/numbers
            # still fail the strict boolean check below.
            disabled = user.get("disabled", False)
            valid_since = user.get("validSince")
            email = user.get("email")
            email_verified = user.get("emailVerified")
            issued_at = claims.get("iat")
            if (local_id != uid or not isinstance(uid, str)
                    or not isinstance(disabled, bool)
                    or not isinstance(valid_since, str)
                    or not valid_since.isdecimal()
                    or isinstance(issued_at, bool) or not isinstance(issued_at, (int, float))
                    or not isinstance(email, str) or not email
                    or not isinstance(email_verified, bool)):
                raise ValueError
            valid_since_seconds = int(valid_since)
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            raise ProviderUnavailable("Firebase Auth returned an invalid current-user record.") from None

        if disabled:
            raise ProviderAccountDisabled("Account disabled.")
        # Firebase Admin compares iat * 1000 with tokens_valid_after_timestamp_ms;
        # REST validSince is documented in seconds. Equality is accepted, matching
        # the Admin SDK's strict less-than comparison.
        if issued_at < valid_since_seconds:
            raise AuthenticationDenied("Identity could not be verified.")
        if not email_verified:
            raise EmailVerificationRequired("Email verification required.")
        return VerifiedIdentity(uid, email, True, False)
