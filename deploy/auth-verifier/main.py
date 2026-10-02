"""Minimal Cloud Run service for current Firebase Auth state.

Only POST /v1/verify is useful, and it requires a locally valid Firebase ID
token. Application roles and StethoFuse data never leave the self-hosted API.
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

MAX_BODY_BYTES = 18_000
MAX_TOKEN_CHARS = 16_384


class InvalidIdentity(Exception):
    pass


class EmailUnverified(Exception):
    pass


class AccountDisabled(Exception):
    pass


class IdentityProviderUnavailable(Exception):
    pass


def firebase_current_user(token: str, *, auth_module=None, app=None) -> dict:
    """Verify signature, revocation, deletion/disabled state and fresh email state."""
    if auth_module is None:
        from firebase_admin import auth as auth_module
    try:
        claims = auth_module.verify_id_token(
            token, app=app, check_revoked=True, clock_skew_seconds=0,
        )
        uid = claims.get("uid") or claims.get("sub")
        if not isinstance(uid, str) or not 1 <= len(uid) <= 128 or uid != uid.strip():
            raise InvalidIdentity()
        user = auth_module.get_user(uid, app=app)
    except InvalidIdentity:
        raise
    except Exception as error:
        if isinstance(error, getattr(auth_module, "UserDisabledError", ())):
            raise AccountDisabled() from None
        if isinstance(error, (ValueError, KeyError)) or any(
            isinstance(error, getattr(auth_module, name, ()))
            for name in ("InvalidIdTokenError", "ExpiredIdTokenError", "RevokedIdTokenError", "UserNotFoundError")
        ):
            raise InvalidIdentity() from None
        raise IdentityProviderUnavailable() from None
    if user.uid != uid:
        raise InvalidIdentity()
    if user.disabled:
        raise AccountDisabled()
    if user.email_verified is not True or not isinstance(user.email, str) or not user.email:
        raise EmailUnverified()
    # Only fields needed by the self-hosted API's identity sync are returned.
    return {"uid": user.uid, "email": user.email, "email_verified": True}


def _new_firebase_runtime():
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
    if project_id != "stethofuse-c18cd-3cca0":
        raise RuntimeError("Firebase project configuration is missing or unexpected.")
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        raise RuntimeError("Cloud Run must use its configured service identity, not a credential file.")
    if os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
        raise RuntimeError("The production verifier must not use the Auth emulator.")
    import firebase_admin
    from firebase_admin import auth

    app = firebase_admin.initialize_app(options={"projectId": project_id, "httpTimeout": 15})
    return lambda token: firebase_current_user(token, auth_module=auth, app=app)


def create_app(*, verify_identity: Callable[[str], dict] | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.verify_identity = verify_identity or _new_firebase_runtime()
        yield
        app.state.verify_identity = None

    app = FastAPI(title="StethoFuse Firebase Revocation Verifier", version="1.0.0",
                  docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    @app.middleware("http")
    async def bounded_private_response(request: Request, call_next):
        if request.url.path != "/health" and request.headers.get("content-length"):
            try:
                if int(request.headers["content-length"]) > MAX_BODY_BYTES:
                    return JSONResponse(status_code=413, content={"error": "request_too_large"})
            except ValueError:
                return JSONResponse(status_code=400, content={"error": "invalid_request"})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    async def bounded_json(request: Request):
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            return None
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_BODY_BYTES:
                raise OverflowError()
        try:
            value = json.loads(data)
        except (ValueError, TypeError):
            return None
        if (not isinstance(value, dict) or set(value) != {"id_token"}
                or not isinstance(value["id_token"], str)
                or not 1 <= len(value["id_token"]) <= MAX_TOKEN_CHARS):
            return None
        return value["id_token"]

    @app.get("/health")
    async def health():
        # Static liveness only. It does not reveal project, identity or user state.
        return {"status": "ok"}

    @app.post("/v1/verify")
    async def verify(request: Request):
        try:
            token = await bounded_json(request)
        except OverflowError:
            return JSONResponse(status_code=413, content={"error": "request_too_large"})
        if token is None:
            return JSONResponse(status_code=400, content={"error": "invalid_request"})
        try:
            result = await run_in_threadpool(request.app.state.verify_identity, token)
        except InvalidIdentity:
            return JSONResponse(status_code=401, content={"error": "invalid_identity"})
        except EmailUnverified:
            return JSONResponse(status_code=403, content={"error": "email_verification_required"})
        except AccountDisabled:
            return JSONResponse(status_code=403, content={"error": "account_disabled"})
        except IdentityProviderUnavailable:
            return JSONResponse(status_code=503, content={"error": "identity_provider_unavailable"})
        except Exception:
            # Never log exception text: SDK diagnostics may contain private data.
            return JSONResponse(status_code=503, content={"error": "identity_provider_unavailable"})
        if (not isinstance(result, dict) or set(result) != {"uid", "email", "email_verified"}
                or not isinstance(result.get("uid"), str) or not result["uid"]
                or not isinstance(result.get("email"), str) or not result["email"]
                or result.get("email_verified") is not True):
            return JSONResponse(status_code=503, content={"error": "identity_provider_unavailable"})
        return result

    # Make unsupported methods/routes uniformly uninformative and avoid auto-docs.
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
    async def not_found(path: str):
        return JSONResponse(status_code=404, content={"error": "not_found"})

    return app


app = create_app()
