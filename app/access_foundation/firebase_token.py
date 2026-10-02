"""Local, non-privileged verification of Firebase ID-token JWTs.

This validates the signed token and Firebase's documented claims using the
official google-auth verifier and Google's public signing certificates. It does
not read Firebase user records, roles, or account state; callers must perform a
separate current-user/revocation check before trusting the identity.
"""
from __future__ import annotations

import base64
import json
import math
import re
import time
from functools import lru_cache
from typing import Callable

from .identity import AuthenticationDenied, ProviderUnavailable

_CERTS_URL = (
    "https://www.googleapis.com/robot/v1/metadata/x509/"
    "securetoken@system.gserviceaccount.com"
)
_SEGMENT = re.compile(r"^[A-Za-z0-9_-]+$")
_MAX_TOKEN_CHARS = 16_384


@lru_cache(maxsize=1)
def _public_cert_request():
    """Cache Google public certs according to their HTTP Cache-Control headers."""
    try:
        import cachecontrol
        import requests
        from google.auth.transport.requests import Request

        session = cachecontrol.CacheControl(requests.Session())
        request = Request(session=session)
    except Exception:
        raise ProviderUnavailable("Firebase public keys are unavailable.") from None

    class BoundedRequest:
        def __call__(self, url, **kwargs):
            # The verifier only requests this fixed public certificate URL.
            if url != _CERTS_URL:
                raise ValueError("Unexpected certificate URL.")
            kwargs.setdefault("timeout", 5)
            return request(url, **kwargs)

    return BoundedRequest()


class FirebaseIdTokenVerifier:
    """Signature + required Firebase claims; no ADC or privileged API access."""

    def __init__(self, project_id: str, *, verify: Callable | None = None,
                 request=None, clock: Callable[[], float] = time.time):
        if not isinstance(project_id, str) or not project_id:
            raise ValueError("A Firebase project ID is required.")
        self.project_id = project_id
        self._verify = verify
        self._request = request
        self._clock = clock

    @staticmethod
    def _header(token: str) -> dict:
        parts = token.split(".")
        if len(parts) != 3 or any(not _SEGMENT.fullmatch(part) for part in parts):
            raise AuthenticationDenied("Invalid Firebase ID token.")
        try:
            raw = base64.urlsafe_b64decode(parts[0] + "=" * (-len(parts[0]) % 4))
            header = json.loads(raw)
        except (ValueError, TypeError, json.JSONDecodeError):
            raise AuthenticationDenied("Invalid Firebase ID token.") from None
        if not isinstance(header, dict) or header.get("alg") != "RS256" or not isinstance(header.get("kid"), str) or not header["kid"]:
            raise AuthenticationDenied("Invalid Firebase ID token.")
        return header

    def verify(self, token: str) -> dict:
        if not isinstance(token, str) or not token or len(token) > _MAX_TOKEN_CHARS:
            raise AuthenticationDenied("Invalid Firebase ID token.")
        self._header(token)
        try:
            if self._verify is None:
                from google.oauth2 import id_token
                verifier = id_token.verify_firebase_token
            else:
                verifier = self._verify
            claims = verifier(
                token,
                self._request if self._request is not None else _public_cert_request(),
                audience=self.project_id,
                clock_skew_in_seconds=0,
            )
        except AuthenticationDenied:
            raise
        except Exception as error:
            try:
                from google.auth.exceptions import GoogleAuthError, TransportError
                if isinstance(error, TransportError):
                    raise ProviderUnavailable("Firebase public keys are unavailable.") from None
                if isinstance(error, GoogleAuthError):
                    raise AuthenticationDenied("Invalid Firebase ID token.") from None
            except ImportError:
                pass
            if isinstance(error, (ValueError, TypeError, KeyError)):
                raise AuthenticationDenied("Invalid Firebase ID token.") from None
            raise ProviderUnavailable("Firebase token verification is unavailable.") from None

        if not isinstance(claims, dict):
            raise AuthenticationDenied("Invalid Firebase ID token.")
        now = self._clock()
        if claims.get("aud") != self.project_id:
            raise AuthenticationDenied("Invalid Firebase ID token.")
        if claims.get("iss") != f"https://securetoken.google.com/{self.project_id}":
            raise AuthenticationDenied("Invalid Firebase ID token.")
        uid = claims.get("sub")
        if not isinstance(uid, str) or not 1 <= len(uid) <= 128 or uid != uid.strip():
            raise AuthenticationDenied("Invalid Firebase ID token.")
        for name, must_be_future in (("exp", True), ("iat", False), ("auth_time", False)):
            value = claims.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise AuthenticationDenied("Invalid Firebase ID token.")
            if (must_be_future and value <= now) or (not must_be_future and value > now):
                raise AuthenticationDenied("Invalid Firebase ID token.")
        return claims
