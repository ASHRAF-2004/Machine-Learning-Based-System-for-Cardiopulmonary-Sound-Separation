"""Bounded PCM upload and checked file-open; never serves a public static directory."""
from __future__ import annotations

import os
import hashlib
import re
import wave
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException


def failure(status, code, message):
    return HTTPException(status, detail={"code": code, "message": message})


async def persist_upload(upload, title, identity, store, settings):
    filename = Path((upload.filename or "").replace("\\", "/")).name
    if not filename.lower().endswith(".wav") or len(filename) > 200:
        raise failure(422, "invalid_audio", "Upload a PCM WAV file.")
    relative_path = uuid4().hex + ".wav"
    target = settings.private_storage / relative_path
    size = 0
    sha256 = hashlib.sha256()
    created = False
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise failure(413, "upload_too_large", "Maximum upload size is 25 MiB.")
                output.write(chunk)
                sha256.update(chunk)
            output.flush()
            os.fsync(output.fileno())
        try:
            with wave.open(str(target), "rb") as wav:
                channels, sample_rate, frames = wav.getnchannels(), wav.getframerate(), wav.getnframes()
                width = wav.getsampwidth()
                if wav.getcomptype() != "NONE" or channels not in (1, 2) or width not in (1, 2, 3, 4) or not 1000 <= sample_rate <= 192000 or frames <= 0:
                    raise ValueError("Unsupported WAV.")
                expected = frames * channels * width
                if expected > settings.max_upload_bytes or len(wav.readframes(frames)) != expected:
                    raise ValueError("Truncated WAV.")
                duration = frames / sample_rate
                if duration > 1800:
                    raise ValueError("WAV is too long.")
        except (wave.Error, EOFError, ValueError):
            raise failure(422, "invalid_audio", "Use a complete mono/stereo PCM WAV, up to 30 minutes.") from None
        directory = os.open(settings.private_storage, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return store.add_upload(identity, title=title or filename, original_filename=filename,
                                relative_path=relative_path, duration_sec=duration,
                                sample_rate_hz=sample_rate, channels=channels, file_size_bytes=size,
                                sha256=sha256.hexdigest())
    except BaseException:
        # Only the exact UUID file created for this failed upload is removed.
        if created:
            target.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def open_authorized_media(store, identity, resource_id, root):
    """Check current authority and open the FD in one database snapshot.

    Later revocation prevents new requests; cannot recall an already-open stream.
    File replacement is not exposed through the API; UUID files are immutable.
    """
    with store._connection() as db:
        actor = store._actor(db, identity)
        resource = db.execute("SELECT recording_id FROM af_resources WHERE id=?", (resource_id,)).fetchone()
        if resource is None or resource_id not in {r["id"] for r in store._visible_resources(db, actor, resource[0])}:
            from app.access_foundation import AccessDenied
            raise AccessDenied("Access denied.")
        row = db.execute("SELECT * FROM m1_files WHERE resource_id=?", (resource_id,)).fetchone()
        if row is None or not re.fullmatch(r"[0-9a-f]{32}\.(wav|png)", row["relative_path"]):
            raise failure(404, "media_unavailable", "Media unavailable.")
        path = root / row["relative_path"]
        if not path.resolve().is_relative_to(root.resolve()):
            raise failure(404, "media_unavailable", "Media unavailable.")
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            stream = os.fdopen(descriptor, "rb")
        except OSError:
            raise failure(404, "media_unavailable", "Media unavailable.") from None
        return stream, dict(row), os.fstat(stream.fileno()).st_size


def byte_range(value, size):
    if not value:
        return 0, size - 1, False
    match = re.fullmatch(r"bytes=([0-9]{0,20})-([0-9]{0,20})", value)
    if not match or not any(match.groups()):
        raise failure(416, "invalid_range", "A single valid byte range is required.")
    first, last = match.groups()
    if first:
        start, end = int(first), min(int(last), size - 1) if last else size - 1
    else:
        start, end = max(0, size - int(last)), size - 1
        if int(last) == 0:
            raise failure(416, "invalid_range", "Byte range is unavailable.")
    if start > end or start >= size:
        raise failure(416, "invalid_range", "Byte range is unavailable.")
    return start, end, True


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        count = 0
        headers = dict(scope.get("headers", []))
        declared = headers.get(b"content-length", b"")
        if declared.isdigit() and (len(declared) > 12 or int(declared) > self.max_bytes):
            from starlette.responses import JSONResponse
            response = JSONResponse({"detail": {"code": "upload_too_large", "message": "Request exceeds the upload limit."}}, status_code=413)
            return await response(scope, receive, send)

        async def limited_receive():
            nonlocal count
            message = await receive()
            if message["type"] == "http.request":
                count += len(message.get("body", b""))
                if count > self.max_bytes:
                    raise failure(413, "upload_too_large", "Request exceeds the upload limit.")
            return message

        return await self.app(scope, limited_receive, send)
