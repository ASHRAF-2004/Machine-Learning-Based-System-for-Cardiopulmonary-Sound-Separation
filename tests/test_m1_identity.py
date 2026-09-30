"""Local identity metadata: real SQLite/API, fictional verified identities.

No provider account changes, model execution, T9 access or listening fixtures.
Derived-resource metadata in one test is explicitly not separation evidence.
"""
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from app.access_foundation import AccessDenied
from app.m1.config import PROJECT_ROOT
from app.m1.public_identity import IdentityError, handle_candidate, normalize_handle, public_reference
from app.m1.store import M1Store
from test_m1_api import auth, env, grant, upload


def reference(value, prefix):
    assert re.fullmatch(prefix + r"-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{6}", value)


@pytest.mark.parametrize("value", ["xy", "1owl", "owl_", ".owl", "blue..owl", "blue_.owl",
                                   "owl@home", "a" * 21, "admin", "SUPPORT", "stethofuse"])
def test_invalid_or_reserved_handles(value):
    with pytest.raises(IdentityError):
        normalize_handle(value)


def test_canonical_and_generated_identity():
    assert normalize_handle(" Winter.Owl_27 ") == "winter.owl_27"
    for _ in range(24):
        for suffix in (False, True):
            candidate = handle_candidate(suffix=suffix)
            assert normalize_handle(candidate) == candidate
    for prefix in ("USR", "REC", "JOB", "RES", "MED", "GRT", "ASN", "EXP"):
        reference(public_reference(prefix), prefix)


def test_user_identity_is_stable_and_uid_remains_authoritative(env):
    before = env.client.get("/api/auth/me", headers=auth()).json()["user"]
    reference(before["public_id"], "USR")
    assert before["handle_change_count"] == 0 and before["handle_changed_at"] is None
    assert before["uid"] == "fictional-owner" and before["role"] == "healthcare_staff"
    assert normalize_handle(before["handle"]) == before["handle"]
    env.store.initialize()
    again = env.client.post("/api/auth/session", headers=auth(), json={}).json()["user"]
    assert again == before
    assert env.client.get("/api/auth/me", headers=auth(before["handle"])).status_code == 401
    assert env.client.get("/api/auth/me", headers=auth(before["public_id"])).status_code == 401
    for field, value in (("uid", "fictional-admin"), ("role", "admin"), ("public_id", "USR-ABCD-123456"),
                         ("handle_change_count", 0)):
        assert env.client.patch("/api/auth/me", headers=auth(), json={"display_name": "Owner", field: value}).status_code == 422


def test_one_change_validation_collision_and_editable_display_name(env):
    old = env.users["owner"]
    other = env.users["other"]
    same = env.client.patch("/api/auth/me", headers=auth(), json={"display_name": "Owner", "handle": old["handle"].upper()})
    assert same.status_code == 200 and same.json()["user"]["handle_change_count"] == 0
    for handle, status in (("admin", 422), ("bad..name", 422), (other["handle"].upper(), 409)):
        denied = env.client.patch("/api/auth/me", headers=auth(), json={"display_name": "Must roll back", "handle": handle})
        assert denied.status_code == status
        current = env.client.get("/api/auth/me", headers=auth()).json()["user"]
        assert current["display_name"] == "Owner" and current["handle_change_count"] == 0
    changed = env.client.patch("/api/auth/me", headers=auth(), json={"display_name": "Local reviewer", "handle": "Review.Owl"})
    assert changed.status_code == 200
    current = changed.json()["user"]
    assert current["handle"] == "review.owl" and current["handle_change_count"] == 1 and current["handle_changed_at"]
    assert current["uid"] == old["uid"] and current["public_id"] == old["public_id"] and current["id"] == old["id"]
    denied = env.client.patch("/api/auth/me", headers=auth(), json={"display_name": "Must roll back", "handle": "second.owl"})
    assert denied.status_code == 409 and denied.json()["detail"]["code"] == "handle_change_used"
    renamed = env.client.patch("/api/auth/me", headers=auth(), json={"display_name": "Updated display name"})
    assert renamed.status_code == 200 and renamed.json()["user"]["handle"] == "review.owl"
    assert env.client.patch("/api/auth/me", json={"display_name": "No", "handle": "third.owl"}).status_code == 401
    events = env.client.get("/api/admin/audit", headers=auth("admin")).json()["items"]
    assert len([event for event in events if event["action"] == "handle.changed" and event["actor_id"] == old["id"]]) == 1


def test_concurrent_handle_updates_are_transactional(env):
    identity = env.verifier.identities["owner"]

    def change(value):
        try:
            env.store.update_profile(identity, "Concurrent reviewer", value)
            return "saved"
        except IdentityError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(change, ("first.owl", "second.owl")))
    assert sorted(outcomes) == ["handle_change_used", "saved"]
    assert env.store.me(identity)["handle_change_count"] == 1


def test_public_resources_jobs_grants_and_existing_exact_scope(env):
    # Existing small HTTP fixture tests durability/authorization, not listening.
    recording = upload(env)
    reference(recording["public_id"], "REC")
    reference(recording["resources"][0]["public_id"], "MED")
    job = env.store.request_separation(env.verifier.identities["owner"], recording["id"])
    reference(job["public_id"], "JOB")
    assert env.store.request_separation(env.verifier.identities["owner"], recording["id"]) == job
    claimed = env.store.claim_job()
    # Publish metadata only to cover result/derived public IDs. No audio accuracy claim.
    outputs = {kind: {"relative_path": kind + ".wav", "size": 0, "sha256": "0" * 64}
               for kind in ("heart", "lung")}
    env.store.complete_job(claimed, outputs, {"input_artifact_sha256": "0" * 64, "test_metadata_only": True})
    result = env.store.results(env.verifier.identities["owner"], claimed["result_id"])
    reference(result["public_id"], "RES")
    for resource in result["resources"]:
        reference(resource["public_id"], "MED")
    heart = next(resource for resource in result["resources"] if resource["kind"] == "heart_audio")
    exact = grant(env, recording, resource_id=heart["id"])
    reference(exact["public_id"], "GRT")
    assert exact["assignment_public_id"] is None
    permitted = env.store.recording(env.verifier.identities["analyst"], recording["id"])
    assert [resource["id"] for resource in permitted["resources"]] == [heart["id"]]
    assert permitted["original_resource_id"] is None
    with pytest.raises(AccessDenied):
        env.store.results(env.verifier.identities["analyst"], result["id"])
    for actor in ("other", "admin"):
        assert env.client.get(f"/api/recordings/{recording['id']}", headers=auth(actor)).status_code == 403
    assert env.client.get(f"/api/recordings/{recording['public_id']}", headers=auth()).status_code == 403
    assignment = grant(env, recording, resource_id=result["id"], permission="review")
    reference(assignment["assignment_public_id"], "ASN")
    review = env.store.review(env.verifier.identities["analyst"], assignment["id"])
    assert review["assignment_public_id"] == assignment["assignment_public_id"]
    assert env.client.delete(f"/api/grants/{exact['id']}", headers=auth()).status_code == 204
    assert env.store.results(env.verifier.identities["analyst"], result["id"])["resources"] == []


def test_identity_allocator_failure_rolls_back_new_entity(env):
    existing = env.users["owner"]["public_id"]
    with patch("app.m1.public_identity_store.public_reference", return_value=existing):
        with pytest.raises(IdentityError):
            env.store.register_verified_identity(env.verifier.identities["new"])
    assert not env.store.account_exists(env.verifier.identities["new"])


def test_v2_migration_preserves_internal_keys_grants_and_preferences(tmp_path):
    path = tmp_path / "identity.sqlite3"
    with sqlite3.connect(path) as db:
        for source in (PROJECT_ROOT / "app/access_foundation/schema.sql", PROJECT_ROOT / "app/m1/schema.sql",
                       PROJECT_ROOT / "app/m1/migrations/002_processing.sql"):
            for statement in source.read_text().split(";"):
                if statement.strip():
                    db.execute(statement)
        db.execute("INSERT INTO af_users VALUES ('owner','uid-owner','a@example.invalid','Old name','healthcare_staff','active',1,1,1)")
        db.execute("INSERT INTO af_users VALUES ('analyst','uid-analyst','b@example.invalid','Reviewer','audio_analyst','active',1,1,1)")
        db.execute("INSERT INTO af_recordings VALUES ('record','owner',1)")
        db.execute("INSERT INTO af_resources VALUES ('original','record','original_audio')")
        db.execute("INSERT INTO af_grants VALUES ('grant','record','original','owner','analyst','review','active',NULL,1,NULL)")
        db.execute("INSERT INTO m1_preferences VALUES ('owner','{\"snow\":false}')")
    store = M1Store(path)
    store.initialize()
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version FROM m1_meta").fetchone() == (3,)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT id,provider_uid,display_name FROM af_users WHERE id='owner'").fetchone() == ("owner", "uid-owner", "Old name")
        assert db.execute("SELECT resource_id,recipient_id,status FROM af_grants").fetchone() == ("original", "analyst", "active")
        before = db.execute("SELECT public_id,handle,normalized_handle,handle_change_count FROM af_users ORDER BY id").fetchall()
        assert db.execute("SELECT preferences_json FROM m1_preferences").fetchone() == ('{"snow":false}',)
        reference(db.execute("SELECT public_id FROM af_recordings").fetchone()[0], "REC")
        reference(db.execute("SELECT assignment_public_id FROM af_grants").fetchone()[0], "ASN")
    store.initialize()
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT public_id,handle,normalized_handle,handle_change_count FROM af_users ORDER BY id").fetchall() == before
