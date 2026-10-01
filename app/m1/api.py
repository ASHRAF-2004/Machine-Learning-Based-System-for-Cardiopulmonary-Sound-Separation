"""M1 FastAPI routes: verified identity, persisted ownership, protected media."""
from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.background import BackgroundTask
from starlette.datastructures import UploadFile

from app.access_foundation import AccessDenied, AuthenticationDenied, DisabledVerifier, Role, Status
from app.access_foundation.identity import EmailVerificationRequired, ProviderAccountDisabled, ProviderUnavailable
from .config import PROJECT_ROOT, Settings
from .media import BodyLimitMiddleware, byte_range, failure, open_authorized_media, persist_upload
from .provider import configured_verifier
from .store import M1Store
from .public_identity import IdentityError


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SessionBody(StrictBody):
    pass


class ProfileBody(StrictBody):
    display_name: str = Field(min_length=1, max_length=200)
    handle: str | None = Field(default=None, max_length=20)


class TitleBody(StrictBody):
    title: str = Field(min_length=1, max_length=200)


class GrantBody(StrictBody):
    recipient_id: str | None = Field(default=None, min_length=1, max_length=128)
    recipient_handle: str | None = Field(default=None, min_length=3, max_length=21)
    recipient_public_id: str | None = Field(default=None, min_length=1, max_length=32)
    permission: Literal["read", "review"] = "read"
    resource_id: str | None = Field(default=None, max_length=128)
    expires_at: int | None = None

    @model_validator(mode="after")
    def exact_recipient(self):
        if self.recipient_id is not None:
            if self.recipient_handle is not None or self.recipient_public_id is not None:
                raise ValueError("Use one recipient contract.")
        elif self.recipient_handle is None or self.recipient_public_id is None:
            raise ValueError("Find and confirm an exact handle.")
        return self


class RecipientBody(StrictBody):
    handle: str = Field(min_length=3, max_length=21)


class RevokeBody(StrictBody):
    recipient_id: str = Field(min_length=1, max_length=128)
    confirmed_recording_id: str = Field(min_length=1, max_length=128)


class ReviewBody(StrictBody):
    decision: Literal["pending", "accepted", "needs_attention"]
    notes: str = Field(max_length=10000)


class UserChangeBody(StrictBody):
    confirmed_target_id: str = Field(min_length=1, max_length=128)
    role: Role | None = None
    status: Status | None = None


class PreferencesBody(StrictBody):
    preferences: dict = Field(default_factory=dict)


def envelope(user, separation=False):
    return {"user": user, "mode": "live", "capabilities": {
        "recordings": True, "sharing": True, "reviews": user["role"] == "audio_analyst",
        "admin": user["role"] == "admin", "ensemble": False, "separation": separation,
    }}


def create_app(settings: Settings | None = None, *, verifier=None) -> FastAPI:
    """verifier injection is trusted server/test setup, never a request option."""
    if settings is not None:
        settings.validate()

    @asynccontextmanager
    async def lifespan(app):
        if settings is not None:
            settings.private_storage.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Do not chmod an unrelated existing directory after a config typo.
            # Operators must deliberately select a private directory; fail closed.
            if settings.private_storage.stat().st_mode & 0o077:
                raise ValueError("Existing M1 media directory must be private (0700).")
            store = M1Store(settings.database)
            store.initialize()
            app.state.store = store
            if verifier is None:
                try:
                    app.state.verifier = configured_verifier(settings)
                except ProviderUnavailable:
                    app.state.verifier = DisabledVerifier()
        try:
            yield
        finally:
            current = getattr(app.state, "verifier", None)
            close = getattr(current, "close", None)
            if callable(close):
                close()

    app = FastAPI(title="StethoFuse M1 API", version="0.2.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = None
    app.state.verifier = verifier or DisabledVerifier()
    app.state.settings = settings
    app.add_middleware(BodyLimitMiddleware, max_bytes=(settings.max_upload_bytes if settings else 25 * 1024 * 1024) + 65536)

    @app.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, _error):
        # Never echo supplied values, arbitrary field names, or parser context.
        return JSONResponse(status_code=422, content={"detail": {
            "code": "invalid_request", "message": "Request fields are missing, unexpected, or invalid."}})

    @app.exception_handler(AccessDenied)
    async def denied(_request, error):
        code = "last_admin" if "last active administrator" in str(error) else "forbidden"
        return JSONResponse(status_code=409 if code == "last_admin" else 403,
                            content={"detail": {"code": code, "message": "The last active administrator cannot be removed." if code == "last_admin" else "Access denied."}})

    @app.exception_handler(sqlite3.Error)
    async def database_error(_request, _error):
        return JSONResponse(status_code=503, content={"detail": {"code": "storage_unavailable", "message": "Application storage is unavailable."}})

    @app.exception_handler(IdentityError)
    async def identity_error(_request, error):
        return JSONResponse(status_code=error.status, content={"detail": {"code": error.code, "message": error.message}})

    def database(request: Request):
        if request.app.state.store is None:
            raise failure(503, "backend_not_configured", "Local API storage is not configured.")
        return request.app.state.store

    def identity(request: Request, authorization: str | None = Header(default=None)):
        if not authorization:
            raise HTTPException(401, {"code": "unauthenticated", "message": "A Firebase ID token is required."}, headers={"WWW-Authenticate": "Bearer"})
        scheme, separator, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token or " " in token or len(token) > 16384:
            raise failure(401, "invalid_token", "Invalid authentication token.")
        provider = request.app.state.verifier
        if isinstance(provider, DisabledVerifier):
            raise failure(503, "provider_not_configured", "Authentication provider is not configured.")
        try:
            return provider.verify(token)
        except EmailVerificationRequired:
            raise failure(403, "email_verification_required", "Verify your email before accessing the workspace.") from None
        except ProviderAccountDisabled:
            raise failure(403, "account_disabled", "This account is disabled.") from None
        except ProviderUnavailable:
            raise failure(503, "provider_unavailable", "Authentication provider is unavailable.") from None
        except AuthenticationDenied:
            raise failure(401, "invalid_token", "Invalid authentication token.") from None

    def principal(who=Depends(identity), store=Depends(database)):
        if not store.account_exists(who):
            raise failure(404, "account_missing", "Sync your verified account before accessing the workspace.")
        try:
            store.resolve_account(who)
        except AccessDenied:
            raise failure(403, "account_disabled", "This account is not active.") from None
        return who

    def admin(who=Depends(principal), store=Depends(database)):
        store.require_admin(who)
        return who

    @app.get("/")
    def root():
        return {"service": "StethoFuse API", "frontend": "separate same-origin SPA", "api_base": "/api"}

    @app.get("/health")
    @app.get("/api/health")
    def health(request: Request):
        return {"status": "ok", "storage_configured": request.app.state.store is not None,
                "provider_configured": not isinstance(request.app.state.verifier, DisabledVerifier), "ensemble_available": False,
                "separation_enabled": bool(settings and settings.separation_enabled)}

    @app.post("/api/auth/session")
    def session(_body: SessionBody, who=Depends(identity), store=Depends(database)):
        store.register_verified_identity(who)
        return envelope(store.me(who), settings.separation_enabled)

    @app.get("/api/auth/me")
    def me(who=Depends(principal), store=Depends(database)):
        return envelope(store.me(who), settings.separation_enabled)

    @app.patch("/api/auth/me")
    def profile(body: ProfileBody, who=Depends(principal), store=Depends(database)):
        return envelope(store.update_profile(who, body.display_name, body.handle), settings.separation_enabled)

    @app.get("/api/preferences")
    def preferences(who=Depends(principal), store=Depends(database)):
        return {"preferences": store.preferences(who)}

    @app.patch("/api/preferences")
    def update_preferences(body: PreferencesBody, who=Depends(principal), store=Depends(database)):
        allowed = {"general", "appearance", "notifications", "recording", "privacy", "accessibility"}
        if set(body.preferences) - allowed or len(json.dumps(body.preferences)) > 16000:
            raise failure(422, "invalid_preferences", "Unknown preference section or oversized preferences.")
        return {"preferences": store.preferences(who, body.preferences)}

    @app.get("/api/recordings")
    def recordings(who=Depends(principal), store=Depends(database)):
        return {"items": store.recordings(who)}

    @app.post("/api/recordings", status_code=201)
    async def upload(request: Request, who=Depends(principal), store=Depends(database)):
        async with request.form(max_files=1, max_fields=1, max_part_size=settings.max_upload_bytes) as form:
            if set(form.keys()) - {"file", "title"} or len(form.getlist("file")) != 1 or len(form.getlist("title")) > 1:
                raise failure(422, "invalid_upload", "Only file and optional title are accepted.")
            file, title = form.get("file"), form.get("title", "")
            if not isinstance(file, UploadFile) or not isinstance(title, str) or len(title.strip()) > 200:
                raise failure(422, "invalid_upload", "Supply a WAV file and a title up to 200 characters.")
            return await persist_upload(file, title.strip(), who, store, settings)

    @app.get("/api/recordings/{recording_id}")
    def recording(recording_id: str, who=Depends(principal), store=Depends(database)):
        return store.recording(who, recording_id)

    @app.patch("/api/recordings/{recording_id}")
    def update_recording(recording_id: str, body: TitleBody, who=Depends(principal), store=Depends(database)):
        return store.update_recording(who, recording_id, body.title)

    @app.get("/api/recordings/{recording_id}/reviews")
    def recording_reviews(recording_id: str, limit: int = Query(default=3, ge=1, le=20),
                          offset: int = Query(default=0, ge=0), who=Depends(principal), store=Depends(database)):
        return store.recording_reviews(who, recording_id, limit=limit, offset=offset)

    @app.api_route("/api/media/{resource_id}", methods=["GET", "HEAD"])
    def media(resource_id: str, request: Request, download: bool = False, who=Depends(principal), store=Depends(database)):
        stream, info, size = open_authorized_media(store, who, resource_id, settings.private_storage)
        try:
            start, end, partial = byte_range(request.headers.get("range"), size)
            length = end - start + 1
            headers = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
                       "Accept-Ranges": "bytes", "Content-Length": str(length),
                       "Content-Disposition": f"{'attachment' if download else 'inline'}; filename=\"{resource_id}.{info['relative_path'].rsplit('.', 1)[1]}\""}
            if partial:
                headers["Content-Range"] = f"bytes {start}-{end}/{size}"
            if request.method == "HEAD":
                stream.close()
                return Response(status_code=206 if partial else 200, media_type=info["media_type"], headers=headers)
            stream.seek(start)

            def chunks():
                remaining = length
                try:
                    while remaining:
                        data = stream.read(min(65536, remaining))
                        if not data:
                            break
                        remaining -= len(data)
                        yield data
                finally:
                    stream.close()

            return StreamingResponse(chunks(), status_code=206 if partial else 200, media_type=info["media_type"],
                                     headers=headers, background=BackgroundTask(stream.close))
        except BaseException:
            stream.close()
            raise

    @app.get("/api/jobs")
    def jobs(who=Depends(principal), store=Depends(database)):
        return {"items": store.jobs(who)}

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str, who=Depends(principal), store=Depends(database)):
        return store.jobs(who, job_id)

    @app.post("/api/recordings/{recording_id}/jobs", status_code=202)
    def start_job(recording_id: str, _body: SessionBody, who=Depends(principal), store=Depends(database)):
        store.require_owner(who, recording_id)
        if not settings.separation_enabled:
            raise failure(503, "separation_unavailable", "Separation is not enabled. No job was created.")
        return store.request_separation(who, recording_id)

    @app.get("/api/results")
    def results(who=Depends(principal), store=Depends(database)):
        return {"items": store.results(who)}

    @app.get("/api/results/{result_id}")
    def result(result_id: str, who=Depends(principal), store=Depends(database)):
        return store.results(who, result_id)

    @app.get("/api/recordings/{recording_id}/grants")
    def grants(recording_id: str, who=Depends(principal), store=Depends(database)):
        return {"items": store.grants(who, recording_id)}

    @app.post("/api/recordings/{recording_id}/grants", status_code=201)
    def create_grant(recording_id: str, body: GrantBody, who=Depends(principal), store=Depends(database)):
        try:
            scope = body.model_dump(include={"permission", "resource_id", "expires_at"})
            if body.recipient_handle is not None:
                grant_id = store.grant_by_handle(who, recording_id, body.recipient_handle, body.recipient_public_id, **scope)
            else:
                grant_id = store.grant_access(who, recording_id, body.recipient_id, **scope)
        except IdentityError:
            raise
        except ValueError:
            raise failure(422, "invalid_grant", "Invalid permission or expiry.") from None
        return store.grant_dto(who, grant_id)

    @app.post("/api/recordings/{recording_id}/sharing-recipient")
    def sharing_recipient(recording_id: str, body: RecipientBody, who=Depends(principal), store=Depends(database)):
        return store.sharing_recipient(who, recording_id, body.handle)

    @app.delete("/api/grants/{grant_id}", status_code=204)
    def revoke(grant_id: str, who=Depends(principal), store=Depends(database)):
        store.revoke_grant(who, grant_id)
        return Response(status_code=204)

    @app.post("/api/recordings/{recording_id}/revoke-access")
    def revoke_all(recording_id: str, body: RevokeBody, who=Depends(principal), store=Depends(database)):
        return {"revoked": store.revoke_all(who, recording_id, body.recipient_id, body.confirmed_recording_id)}

    @app.get("/api/assignments")
    def assignments(who=Depends(principal), store=Depends(database)):
        return {"items": store.assignments(who)}

    @app.get("/api/assignments/{grant_id}/review")
    def review(grant_id: str, who=Depends(principal), store=Depends(database)):
        return store.review(who, grant_id)

    @app.put("/api/assignments/{grant_id}/review")
    def update_review(grant_id: str, body: ReviewBody, who=Depends(principal), store=Depends(database)):
        return store.review(who, grant_id, **body.model_dump())

    @app.get("/api/admin/users")
    def users(who=Depends(admin), store=Depends(database)):
        return {"items": store.users(who)}

    @app.patch("/api/admin/users/{user_id}")
    def update_user(user_id: str, body: UserChangeBody, who=Depends(admin), store=Depends(database)):
        target = next((u for u in store.users(who) if u["id"] == user_id), None)
        if target is None:
            raise failure(404, "user_missing", "Account not found.")
        # The current-user verifier deliberately accepts only an ID token and
        # exposes no arbitrary-UID lookup. A target must already be a trusted,
        # locally registered provider-verified account. The store rechecks its
        # verified flag and applies the role/status/audit change transactionally.
        account = store.change_account(who, user_id, **body.model_dump())
        return {**target, "role": account.role.value, "status": account.status.value}

    @app.get("/api/admin/audit")
    def audit(who=Depends(admin), store=Depends(database)):
        return {"items": store.audit(who)}

    @app.get("/api/admin/methods")
    @app.get("/models")
    @app.get("/methods")
    def methods(_who=Depends(admin)):
        return {"items": [], "availability": "benchmark_executor_not_connected",
                "message": "Legacy strategies are preserved; no runtime catalog is configured in the isolated M1 database."}

    @app.post("/api/admin/benchmarks")
    def benchmark(_who=Depends(admin)):
        raise failure(503, "benchmark_unavailable", "The isolated M1 runtime does not load legacy inference dependencies.")

    def retired():
        raise failure(410, "legacy_route_retired", "This unowned legacy route is retired. Use the authenticated /api workspace.")

    for path, methods_allowed in (
        ("/upload", ["POST"]), ("/separate/{audio_id}", ["POST"]), ("/result/{job_id}", ["GET", "HEAD"]),
        ("/download/{job_id}/{component}", ["GET", "HEAD"]), ("/history", ["GET", "HEAD"]),
        ("/visualizations/{path:path}", ["GET", "HEAD"]),
    ):
        app.add_api_route(path, retired, methods=methods_allowed, include_in_schema=False)
    app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "app" / "static"), name="static")
    return app
