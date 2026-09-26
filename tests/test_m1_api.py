"""M1 HTTP integration using fictional injected identities and isolated temp storage.

No network, Firebase accounts, legacy DB, model weights or synthetic inference.
Derived-file fixtures below exercise authorization only, not ML correctness.
"""
import asyncio
import io
import sqlite3
import sys
import time
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.access_foundation import AuthenticationDenied, Role, VerifiedIdentity
from app.access_foundation.identity import EmailVerificationRequired, ProviderAccountDisabled, ProviderUnavailable
from app.m1.api import create_app
from app.m1.config import PROJECT_ROOT, Settings
from app.m1.media import persist_upload
from app.m1.store import M1Store


class FictionalVerifier:
    def __init__(self):
        self.identities = {name: VerifiedIdentity("fictional-" + name, name + "@example.invalid", True)
                           for name in ("owner", "other", "analyst", "admin", "new")}

    def verify(self, token):
        errors = {"unverified": EmailVerificationRequired, "disabled": ProviderAccountDisabled,
                  "outage": ProviderUnavailable}
        if token in errors:
            raise errors[token]("Never expose this private diagnostic")
        if token not in self.identities:
            raise AuthenticationDenied("Never expose token: " + token)
        return self.identities[token]

    def lookup_existing(self, uid):
        return next(i for i in self.identities.values() if i.uid == uid)


def auth(name="owner"):
    return {"Authorization": "Bearer " + name}


def wav_bytes():
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setparams((1, 2, 4000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\0\0" * 400)
    return output.getvalue()


@pytest.fixture
def env(tmp_path):
    settings = Settings(tmp_path / "database" / "m1.sqlite3", tmp_path / "private")
    verifier = FictionalVerifier()
    app = create_app(settings, verifier=verifier)
    with TestClient(app) as client:
        users = {}
        for name in ("owner", "other", "analyst", "admin"):
            response = client.post("/api/auth/session", json={}, headers=auth(name))
            assert response.status_code == 200, response.text
            users[name] = response.json()["user"]
        store = app.state.store
        store.bootstrap_first_admin(verifier, provider_uid="fictional-admin", confirmed_uid="fictional-admin")
        store.change_account(verifier.identities["admin"], users["analyst"]["id"],
                             confirmed_target_id=users["analyst"]["id"], role=Role.AUDIO_ANALYST)
        yield SimpleNamespace(client=client, app=app, store=store, verifier=verifier, settings=settings, users=users)


def upload(env):
    response = env.client.post("/api/recordings", headers=auth(), files={"file": ("fictional.wav", wav_bytes(), "audio/wav")}, data={"title": "Fictional research sample"})
    assert response.status_code == 201, response.text
    return response.json()


def grant(env, recording, recipient="analyst", **fields):
    response = env.client.post(f"/api/recordings/{recording['id']}/grants", headers=auth(),
                               json={"recipient_id": env.users[recipient]["id"], **fields})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("token,status,code", [
    (None, 401, "unauthenticated"), ("malformed", 401, "invalid_token"),
    ("expired", 401, "invalid_token"), ("revoked", 401, "invalid_token"),
    ("wrong-project", 401, "invalid_token"), ("unverified", 403, "email_verification_required"),
    ("disabled", 403, "account_disabled"), ("outage", 503, "provider_unavailable"),
])
def test_token_failure_mapping(env, token, status, code):
    response = env.client.get("/api/recordings", headers=auth(token) if token else {})
    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    assert "private diagnostic" not in response.text
    assert response.headers["cache-control"] == "private, no-store"


def test_identity_onboarding_no_get_mutation_or_client_privilege(env):
    assert env.client.get("/api/auth/me", headers=auth("new")).status_code == 404
    assert not env.store.account_exists(env.verifier.identities["new"])
    response = env.client.post("/api/auth/session", headers=auth("new"), json={"role": "admin", "secret": "never-echo-me"})
    assert response.status_code == 422 and "never-echo-me" not in response.text
    user = env.client.post("/api/auth/session", headers=auth("new"), json={}).json()["user"]
    assert user["role"] == "healthcare_staff"
    assert env.client.get("/api/auth/me", headers=auth("admin")).json()["capabilities"]["admin"] is True


def test_private_upload_is_durable_owner_derived_and_other_admin_denied(env):
    record = upload(env)
    assert record["owner_id"] == env.users["owner"]["id"] and record["duration_sec"] == 0.1
    assert "relative_path" not in str(record)
    for outsider in ("other", "admin", "analyst"):
        assert env.client.get("/api/recordings", headers=auth(outsider)).json() == {"items": []}
        assert env.client.get(f"/api/recordings/{record['id']}", headers=auth(outsider)).status_code == 403
        assert env.client.patch(f"/api/recordings/{record['id']}", headers=auth(outsider), json={"title": "No"}).status_code == 403
    with TestClient(create_app(env.settings, verifier=env.verifier)) as restarted:
        assert restarted.get("/api/recordings", headers=auth()).json()["items"][0]["id"] == record["id"]
        assert restarted.get(record["resources"][0]["url"], headers=auth()).content == wav_bytes()
    assert env.client.post("/api/recordings", headers=auth(), files={"file": ("f.wav", wav_bytes())}, data={"owner_id": env.users["admin"]["id"]}).status_code == 422


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_media_token_owner_scoped_grant_and_revocation(env, method):
    record = upload(env)
    url = record["resources"][0]["url"]
    assert env.client.request(method, url).status_code == 401
    assert env.client.request(method, url + "?token=owner").status_code == 401
    assert env.client.request(method, url, headers=auth("admin")).status_code == 403
    g = grant(env, record, resource_id=record["original_resource_id"])
    response = env.client.request(method, url, headers={**auth("analyst"), "Range": "bytes=0-9"})
    assert response.status_code == 206 and response.headers["content-length"] == "10"
    assert response.headers["content-range"].startswith("bytes 0-9/")
    assert env.client.get("/api/recordings", headers=auth("analyst")).json()["items"][0]["id"] == record["id"]
    assert env.client.delete(f"/api/grants/{g['id']}", headers=auth()).status_code == 204
    assert env.client.request(method, url, headers={**auth("analyst"), "Range": "bytes=0-9"}).status_code == 403


@pytest.mark.parametrize("value", ["bytes=0-1,5-6", "bytes=-0", "bytes=9999999-", "bytes=8-2", "bytes=-", "bytes=" + "9" * 5000 + "-"])
def test_invalid_ranges_safe_416(env, value):
    record = upload(env)
    response = env.client.get(record["resources"][0]["url"], headers={**auth(), "Range": value})
    assert response.status_code == 416


def test_original_audio_review_persists_and_scope_demotion_revoke_fail_closed(env):
    record = upload(env)
    g = grant(env, record, permission="review", resource_id=record["original_resource_id"])
    url = f"/api/assignments/{g['id']}/review"
    assert env.client.get("/api/assignments", headers=auth("analyst")).json()["items"][0]["id"] == g["id"]
    response = env.client.put(url, headers=auth("analyst"), json={"decision": "needs_attention", "notes": "Fictional reviewer-only notes"})
    assert response.status_code == 200 and response.json()["notes"] == "Fictional reviewer-only notes"
    for outsider in ("owner", "other", "admin"):
        assert env.client.get(url, headers=auth(outsider)).status_code == 403
    change = {"confirmed_target_id": env.users["analyst"]["id"], "role": "healthcare_staff"}
    assert env.client.patch(f"/api/admin/users/{env.users['analyst']['id']}", headers=auth("admin"), json=change).status_code == 200
    assert env.client.put(url, headers=auth("analyst"), json={"decision": "accepted", "notes": "No"}).status_code == 403
    assert env.client.get(record["resources"][0]["url"], headers=auth("analyst")).status_code == 200
    assert env.client.delete(f"/api/grants/{g['id']}", headers=auth()).status_code == 204
    assert env.client.get(record["resources"][0]["url"], headers=auth("analyst")).status_code == 403
    audit = env.client.get("/api/admin/audit", headers=auth("admin")).text
    assert "Fictional reviewer-only notes" not in audit


def test_overlapping_grants_one_revoke_versus_atomic_all(env):
    record = upload(env)
    g = grant(env, record, permission="review", resource_id=record["original_resource_id"])
    grant(env, record)
    env.client.delete(f"/api/grants/{g['id']}", headers=auth())
    assert env.client.get(record["resources"][0]["url"], headers=auth("analyst")).status_code == 200
    body = {"recipient_id": env.users["analyst"]["id"], "confirmed_recording_id": record["id"]}
    response = env.client.post(f"/api/recordings/{record['id']}/revoke-access", headers=auth(), json=body)
    assert response.json() == {"revoked": 1}
    assert env.client.get(record["resources"][0]["url"], headers=auth("analyst")).status_code == 403


def test_admin_capabilities_and_last_admin_guard(env):
    target = env.users["admin"]["id"]
    for path in ("/api/admin/users", "/api/admin/audit", "/api/admin/methods", "/methods", "/models"):
        assert env.client.get(path).status_code == 401
        assert env.client.get(path, headers=auth()).status_code == 403
        assert env.client.get(path, headers=auth("admin")).status_code == 200
    for change in ({"status": "disabled"}, {"status": "suspended"},
                   {"role": "healthcare_staff"}, {"role": "audio_analyst"}):
        response = env.client.patch(f"/api/admin/users/{target}", headers=auth("admin"),
                                    json={**change, "confirmed_target_id": target})
        assert response.status_code == 403 and response.json()["detail"]["code"] == "forbidden"
    assert env.store.bootstrap_first_admin(env.verifier, provider_uid="fictional-admin", confirmed_uid="fictional-admin") is False


def test_admin_can_change_other_verified_roles_but_not_self(env):
    admin_id = env.users["admin"]["id"]
    target_id = env.users["other"]["id"]
    target_path = f"/api/admin/users/{target_id}"
    self_path = f"/api/admin/users/{admin_id}"

    promoted = env.client.patch(target_path, headers=auth("admin"), json={
        "role": "admin", "confirmed_target_id": target_id,
    })
    assert promoted.status_code == 200 and promoted.json()["role"] == "admin"

    demoted = env.client.patch(target_path, headers=auth("admin"), json={
        "role": "healthcare_staff", "confirmed_target_id": target_id,
    })
    assert demoted.status_code == 200 and demoted.json()["role"] == "healthcare_staff"

    disabled = env.client.patch(target_path, headers=auth("admin"), json={
        "status": "disabled", "confirmed_target_id": target_id,
    })
    assert disabled.status_code == 200 and disabled.json()["status"] == "disabled"

    for change in ({"role": "healthcare_staff"}, {"status": "disabled"}):
        response = env.client.patch(self_path, headers=auth("admin"), json={
            **change, "confirmed_target_id": admin_id,
        })
        assert response.status_code == 403


def test_admin_promotion_demotion_verified_target_and_audit(env):
    target = env.users["other"]["id"]
    path = f"/api/admin/users/{target}"
    body = {"role": "admin", "confirmed_target_id": target}
    with patch.object(env.verifier, "lookup_existing", wraps=env.verifier.lookup_existing) as lookup:
        assert env.client.patch(path, headers=auth(), json=body).status_code == 403
        lookup.assert_not_called()
        response = env.client.patch(path, headers=auth("admin"), json=body)
        assert response.status_code == 200 and response.json()["role"] == "admin"
        lookup.assert_called_once_with("fictional-other")
    assert env.client.get("/api/admin/users", headers=auth("other")).status_code == 200
    body["role"] = "healthcare_staff"
    assert env.client.patch(path, headers=auth("admin"), json=body).status_code == 200
    assert env.client.get("/api/admin/users", headers=auth("other")).status_code == 403
    events = env.client.get("/api/admin/audit", headers=auth("admin")).json()["items"]
    changes = [e for e in events if e["target_id"] == target and e["action"] == "account.changed"]
    assert len(changes) == 2
    assert all(e["actor_id"] == env.users["admin"]["id"] for e in changes)


@pytest.mark.parametrize("failure_kind", ["unverified", "disabled", "deleted", "mismatch", "outage"])
@pytest.mark.parametrize("demotion", [False, True])
def test_admin_role_change_rechecks_current_provider_target(env, failure_kind, demotion):
    target = env.users["other"]["id"]
    identity = env.verifier.identities["other"]
    if demotion:
        env.store.change_account(env.verifier.identities["admin"], target,
                                 confirmed_target_id=target, role=Role.ADMIN)
    with env.store._connection() as db:
        before = db.execute("SELECT COUNT(*) FROM af_audit").fetchone()[0]
    if failure_kind == "unverified":
        replacement = {"return_value": VerifiedIdentity(identity.uid, identity.email, False)}
    elif failure_kind == "disabled":
        replacement = {"return_value": VerifiedIdentity(identity.uid, identity.email, True, disabled=True)}
    elif failure_kind == "mismatch":
        replacement = {"return_value": env.verifier.identities["owner"]}
    else:
        error = ProviderUnavailable if failure_kind == "outage" else AuthenticationDenied
        replacement = {"side_effect": error("Private provider diagnostic must not escape")}
    with patch.object(env.verifier, "lookup_existing", **replacement):
        response = env.client.patch(f"/api/admin/users/{target}", headers=auth("admin"), json={
            "role": "healthcare_staff" if demotion else "admin", "confirmed_target_id": target})
    assert response.status_code == (503 if failure_kind == "outage" else 403)
    assert "Private provider" not in response.text
    with env.store._connection() as db:
        assert db.execute("SELECT role FROM af_users WHERE id=?", (target,)).fetchone()[0] == (
            "admin" if demotion else "healthcare_staff")
        assert db.execute("SELECT COUNT(*) FROM af_audit").fetchone()[0] == before


def test_admin_role_change_rejects_unverified_local_target_and_unknown_account(env):
    target = env.users["other"]["id"]
    with env.store._connection(write=True) as db:
        db.execute("UPDATE af_users SET email_verified=0 WHERE id=?", (target,))
    body = {"role": "admin", "confirmed_target_id": target}
    assert env.client.patch(f"/api/admin/users/{target}", headers=auth("admin"), json=body).status_code == 403
    with patch.object(env.verifier, "lookup_existing") as lookup:
        body["confirmed_target_id"] = "nonexistent"
        assert env.client.patch("/api/admin/users/nonexistent", headers=auth("admin"), json=body).status_code == 404
        lookup.assert_not_called()


def test_admin_role_change_audit_failure_rolls_back(env):
    target = env.users["other"]["id"]
    with patch.object(env.store, "_audit", side_effect=sqlite3.IntegrityError("Private diagnostic")):
        response = env.client.patch(f"/api/admin/users/{target}", headers=auth("admin"), json={
            "role": "admin", "confirmed_target_id": target})
    assert response.status_code == 503 and "Private diagnostic" not in response.text
    assert env.store.resolve_account(env.verifier.identities["other"]).role == Role.HEALTHCARE_STAFF


def test_disabled_and_suspended_accounts_refresh_immediately(env):
    record = upload(env)
    grant(env, record)
    target = env.users["owner"]["id"]
    env.client.patch(f"/api/admin/users/{target}", headers=auth("admin"), json={"status": "suspended", "confirmed_target_id": target})
    assert env.client.get("/api/auth/me", headers=auth()).status_code == 403
    assert env.client.post("/api/auth/session", headers=auth(), json={}).status_code == 403
    assert env.client.get(record["resources"][0]["url"], headers=auth("analyst")).status_code == 403


@pytest.mark.parametrize("path,method", [("/upload", "POST"), ("/separate/1", "POST"), ("/result/1", "GET"), ("/download/1/heart", "GET"), ("/download/1/lung", "GET"), ("/history", "GET"), ("/visualizations/1_heart_waveform.png", "GET")])
def test_legacy_aliases_retired_no_private_reads(env, path, method):
    response = env.client.request(method, path, headers={"Range": "bytes=0-9"})
    assert response.status_code == 410 and response.json()["detail"]["code"] == "legacy_route_retired"
    for other in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
        response = env.client.request(other, path, headers=auth())
        assert response.status_code in (405, 410)


def test_no_public_storage_docs_or_fake_ensemble(env):
    record = upload(env)
    for path in ("/docs", "/openapi.json", "/storage/1.wav", "/static/%2e%2e/database/cardiopulmonary.db"):
        assert env.client.get(path).status_code == 404
    assert env.client.get("/api/results", headers=auth()).json() == {"items": []}
    assert env.client.get("/api/jobs", headers=auth()).json() == {"items": []}
    response = env.client.post(f"/api/recordings/{record['id']}/jobs", headers=auth(), json={})
    assert response.status_code == 503 and response.json()["detail"]["code"] == "ensemble_unavailable"
    assert env.client.get("/api/jobs", headers=auth()).json() == {"items": []}
    assert env.client.post("/api/admin/benchmarks", headers=auth()).status_code == 403
    assert env.client.post("/api/admin/benchmarks", headers=auth("admin")).status_code == 503


def test_profile_preferences_are_own_persistent_and_safe_validation(env):
    response = env.client.patch("/api/auth/me", headers=auth(), json={"display_name": "Fictional name"})
    assert response.json()["user"]["display_name"] == "Fictional name"
    prefs = {"preferences": {"general": {"language": "en"}, "appearance": {"density": "comfortable"}}}
    assert env.client.patch("/api/preferences", headers=auth(), json=prefs).json() == prefs
    assert env.client.get("/api/preferences", headers=auth("other")).json() == {"preferences": {}}
    assert env.client.patch("/api/preferences", headers=auth(), json={"preferences": {"role": "admin"}}).status_code == 422
    response = env.client.patch("/api/auth/me", headers=auth(), json={"display_name": "Fine", "secret-field-name": "secret-value"})
    assert response.status_code == 422 and "secret" not in response.text


def test_unconfigured_app_fail_closed_and_no_ml_import():
    with TestClient(create_app()) as client:
        assert client.get("/api/auth/me").status_code == 401
        assert client.get("/api/auth/me", headers=auth()).status_code == 503
        assert client.get("/health").json()["provider_configured"] is False
    assert "torch" not in sys.modules and "app.services.separation_service" not in sys.modules


def test_legacy_schema_and_paths_are_rejected(tmp_path):
    dbpath = tmp_path / "old.sqlite3"
    with sqlite3.connect(dbpath) as db:
        db.execute("CREATE TABLE uploaded_audio(id INTEGER PRIMARY KEY)")
    with pytest.raises(ValueError):
        M1Store(dbpath).initialize()
    with sqlite3.connect(dbpath) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("uploaded_audio",)]
    with pytest.raises(ValueError):
        Settings(PROJECT_ROOT / "database" / "cardiopulmonary.db", tmp_path / "private").validate()


def test_upload_invalid_oversize_and_collision_preserves_existing(env):
    for filename, content in (("f.mp3", b"wrong"), ("f.wav", b"wrong"), ("f.wav", wav_bytes()[:60])):
        assert env.client.post("/api/recordings", headers=auth(), files={"file": (filename, content)}).status_code == 422
    assert list(env.settings.private_storage.iterdir()) == []
    response = env.client.post("/api/recordings", headers={**auth(), "Content-Length": str(30 * 1024 * 1024)}, content=b"tiny")
    assert response.status_code == 413
    from starlette.datastructures import UploadFile
    collision = SimpleNamespace(hex="a" * 32)
    path = env.settings.private_storage / (collision.hex + ".wav")
    path.write_bytes(b"existing immutable data")
    with patch("app.m1.media.uuid4", return_value=collision), pytest.raises(FileExistsError):
        asyncio.run(persist_upload(UploadFile(io.BytesIO(wav_bytes()), filename="test.wav"), "", env.verifier.identities["owner"], env.store, env.settings))
    assert path.read_bytes() == b"existing immutable data"


@pytest.mark.parametrize("kind,extension,mime", [("heart_audio", "wav", "audio/wav"), ("lung_audio", "wav", "audio/wav"), ("waveform", "png", "image/png"), ("spectrogram", "png", "image/png")])
def test_all_derived_media_kinds_use_same_exact_scope_policy(env, kind, extension, mime):
    record = upload(env)
    resource_id = env.store.create_resource(env.verifier.identities["owner"], record["id"], kind)
    relative = uuid4().hex + "." + extension
    fixture = wav_bytes() if extension == "wav" else b"\x89PNG\r\n\x1a\nFICTIONAL-AUTHORIZATION-FIXTURE"
    (env.settings.private_storage / relative).write_bytes(fixture)
    with sqlite3.connect(env.settings.database) as db:
        db.execute("INSERT INTO m1_files VALUES (?,?,?,?)", (resource_id, relative, mime, len(fixture)))
    url = "/api/media/" + resource_id
    assert env.client.get(url, headers=auth()).content == fixture
    assert env.client.get(url, headers=auth("admin")).status_code == 403
    g = grant(env, record, resource_id=resource_id)
    assert env.client.get(url, headers=auth("analyst")).content == fixture
    assert env.client.get(record["resources"][0]["url"], headers=auth("analyst")).status_code == 403
    shared = env.client.get(f"/api/recordings/{record['id']}", headers=auth("analyst")).json()
    assert shared["original_resource_id"] is None and shared["original_filename"] is None
    env.client.delete(f"/api/grants/{g['id']}", headers=auth())
    assert env.client.get(url, headers=auth("analyst")).status_code == 403


def test_chunked_oversize_is_413_not_parser_500(env):
    from dataclasses import replace
    with TestClient(create_app(replace(env.settings, max_upload_bytes=128), verifier=env.verifier)) as client:
        boundary = "fictional-boundary"
        start = f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"f.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode()
        chunks = iter([start, b"x" * 40000, b"x" * 40000, f"\r\n--{boundary}--\r\n".encode()])
        response = client.post("/api/recordings", headers={**auth(), "Content-Type": f"multipart/form-data; boundary={boundary}"}, content=chunks)
        assert response.status_code == 413, response.text
        assert response.headers["cache-control"] == "private, no-store"


def test_expired_scope_and_context_do_not_leak_original_or_result(env):
    record = upload(env)
    result_id = env.store.create_resource(env.verifier.identities["owner"], record["id"], "result")
    context_id = env.store.create_resource(env.verifier.identities["owner"], record["id"], "context")
    job_id = uuid4().hex
    with sqlite3.connect(env.settings.database) as db:
        # Test-only persisted historical rows. The production API creates no fake job/result.
        db.execute("INSERT INTO m1_jobs VALUES (?,?,?,?,?,?,?)", (job_id, record["id"], env.users["owner"]["id"], "completed", int(time.time()), int(time.time()), None))
        db.execute("INSERT INTO m1_results VALUES (?,?,?,?,?)", (result_id, record["id"], job_id, int(time.time()), "TEST FIXTURE — not inference"))
    g = grant(env, record, resource_id=context_id)
    assert env.client.get(f"/api/results/{result_id}", headers=auth("analyst")).status_code == 403
    assert env.client.get(f"/api/jobs/{job_id}", headers=auth("analyst")).status_code == 403
    assert env.client.get(f"/api/media/{context_id}", headers=auth("analyst")).status_code == 404  # no context bytes stored
    grant(env, record, permission="review", resource_id=result_id)
    result = env.client.get(f"/api/results/{result_id}", headers=auth("analyst"))
    assert result.status_code == 200 and result.json()["resources"] == []
    assert env.client.get(record["resources"][0]["url"], headers=auth("analyst")).status_code == 403
    with sqlite3.connect(env.settings.database) as db:
        db.execute("UPDATE af_grants SET expires_at=1 WHERE recording_id=?", (record["id"],))
    assert env.client.get(f"/api/results/{result_id}", headers=auth("analyst")).status_code == 403
    assert env.client.get("/api/assignments", headers=auth("analyst")).json() == {"items": []}


def test_private_file_symlink_and_path_injection_refused(env, tmp_path):
    record = upload(env)
    resource = record["original_resource_id"]
    with sqlite3.connect(env.settings.database) as db:
        relative = db.execute("SELECT relative_path FROM m1_files WHERE resource_id=?", (resource,)).fetchone()[0]
    target = env.settings.private_storage / relative
    outside = tmp_path / "outside-private.txt"
    outside.write_bytes(b"must never be served")
    target.unlink()
    target.symlink_to(outside)
    assert env.client.get(f"/api/media/{resource}", headers=auth()).status_code == 404
    with sqlite3.connect(env.settings.database) as db:
        db.execute("UPDATE m1_files SET relative_path='../outside-private.txt' WHERE resource_id=?", (resource,))
    assert env.client.get(f"/api/media/{resource}", headers=auth()).status_code == 404


def test_bootstrap_cli_dry_run_never_calls_provider_or_mutates(env, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("bootstrap_m1_test", PROJECT_ROOT / "scripts" / "bootstrap_m1_admin.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("STETHOFUSE_M1_DATABASE", str(env.settings.database))
    monkeypatch.setenv("STETHOFUSE_M1_PRIVATE_STORAGE", str(env.settings.private_storage))
    with patch.object(module, "configured_verifier", side_effect=AssertionError("No network")):
        assert module.main(["--uid", "fictional-owner", "--confirm-uid", "fictional-owner"]) == 0
    assert env.store.resolve_account(env.verifier.identities["owner"]).role == Role.HEALTHCARE_STAFF
    with pytest.raises(SystemExit):
        module.main(["--uid", "fictional-owner", "--confirm-uid", "different"])


@pytest.mark.parametrize("error_name,status", [("InvalidIdTokenError", 401), ("ExpiredIdTokenError", 401),
    ("RevokedIdTokenError", 401), ("UserNotFoundError", 401), ("UserDisabledError", 403), ("outage", 503)])
def test_official_sdk_exception_types_are_mapped_without_network(env, error_name, status, monkeypatch):
    from firebase_admin import auth as sdk
    from app.access_foundation.identity import FirebaseIdentityAdapter
    monkeypatch.delenv("FIREBASE_AUTH_EMULATOR_HOST", raising=False)
    adapter = FirebaseIdentityAdapter(app=SimpleNamespace(project_id=env.settings.firebase_project), expected_project_id=env.settings.firebase_project)
    if error_name == "outage":
        error = RuntimeError("private-provider-diagnostic")
    elif error_name == "ExpiredIdTokenError":
        error = sdk.ExpiredIdTokenError("private-provider-diagnostic", None)
    else:
        error = getattr(sdk, error_name)("private-provider-diagnostic")
    env.app.state.verifier = adapter
    with patch.object(sdk, "verify_id_token", side_effect=error) as verify:
        response = env.client.get("/api/auth/me", headers=auth())
        assert response.status_code == status
        assert "private-provider-diagnostic" not in response.text
        verify.assert_called_once_with("owner", app=adapter._app, check_revoked=True, clock_skew_seconds=0)


def test_bootstrap_same_email_new_uid_does_not_escalate(env):
    env.verifier.identities["same-email"] = VerifiedIdentity("fictional-different-uid", "admin@example.invalid", True)
    response = env.client.post("/api/auth/session", headers=auth("same-email"), json={})
    assert response.status_code == 200 and response.json()["user"]["role"] == "healthcare_staff"
    assert env.client.post("/api/admin/bootstrap", headers=auth("same-email"), json={"role": "admin"}).status_code == 404
