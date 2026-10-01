"""Exact handle adapters reuse existing UID/owner/exact-resource policy.

Isolated SQLite and fictional verifier only. No model, real provider or T9.
"""
import time
from uuid import uuid4

import pytest

from app.access_foundation import AccessDenied
from app.m1.store import M1Store
from test_m1_api import auth, env, upload


def lookup(env, recording, handle, actor="owner"):
    return env.client.post(f"/api/recordings/{recording['id']}/sharing-recipient",
                           headers=auth(actor), json={"handle": handle})


def share(env, recording, person, **scope):
    return env.client.post(f"/api/recordings/{recording['id']}/grants", headers=auth(),
                           json={"recipient_handle": person["handle"], "recipient_public_id": person["public_id"], **scope})


def test_exact_lookup_exposes_only_confirmable_public_identity(env):
    record = upload(env)
    person = lookup(env, record, " @" + env.users["other"]["handle"].upper() + " ")
    assert person.status_code == 200
    assert set(person.json()) == {"display_name", "handle", "public_id"}
    assert person.json()["handle"] == env.users["other"]["handle"]
    assert person.json()["public_id"] == env.users["other"]["public_id"]
    assert "example.invalid" not in person.text and "fictional-other" not in person.text
    assert lookup(env, record, env.users["other"]["handle"][:-1]).status_code == 404
    assert lookup(env, record, "missing.person").status_code == 404
    assert lookup(env, record, env.users["owner"]["handle"]).status_code == 404
    assert lookup(env, record, "invalid..handle").status_code == 422


def test_lookup_and_handle_grants_are_owner_only_not_admin_override(env):
    record = upload(env)
    target = env.users["other"]
    endpoint = f"/api/recordings/{record['id']}/sharing-recipient"
    assert env.client.post(endpoint, json={"handle": target["handle"]}).status_code == 401
    for actor in ("other", "analyst", "admin"):
        assert lookup(env, record, target["handle"], actor).status_code == 403
        denied = env.client.post(f"/api/recordings/{record['id']}/grants", headers=auth(actor),
                                json={"recipient_handle": target["handle"], "recipient_public_id": target["public_id"]})
        assert denied.status_code == 403
    assert lookup(env, {"id": "unknown-recording"}, target["handle"]).status_code == 403
    assert env.client.get("/api/users", headers=auth()).status_code == 404


@pytest.mark.parametrize("field,value", [("status", "suspended"), ("status", "disabled"), ("email_verified", 0)])
def test_unavailable_accounts_are_not_disclosed_or_granted(env, field, value):
    record = upload(env)
    target = env.users["other"]
    with env.store._connection(write=True) as db:
        # Fixed test-only field whitelist, never interpolated request data.
        db.execute(f"UPDATE af_users SET {field}=? WHERE id=?", (value, target["id"]))
    missing = lookup(env, record, "missing.person")
    denied = lookup(env, record, target["handle"])
    assert missing.status_code == denied.status_code == 404 and missing.json() == denied.json()
    assert share(env, record, target).status_code == 404
    assert env.client.get(f"/api/recordings/{record['id']}/grants", headers=auth()).json()["items"] == []


def test_confirmed_handle_and_public_reference_cannot_redirect_a_grant(env):
    record = upload(env)
    person = lookup(env, record, env.users["other"]["handle"]).json()
    changed = env.store.update_profile(env.verifier.identities["other"], "Updated name", "updated.person")
    # The old handle can now belong to another account. Confirmation must still
    # reject it, not silently grant that other account.
    env.store.update_profile(env.verifier.identities["analyst"], "Analyst", person["handle"])
    assert share(env, record, person).status_code == 404
    assert share(env, record, {**changed, "public_id": env.users["owner"]["public_id"]}).status_code == 404
    assert env.client.get(f"/api/recordings/{record['id']}/grants", headers=auth()).json()["items"] == []
    correct = lookup(env, record, "@updated.person").json()
    grant = share(env, record, correct)
    assert grant.status_code == 201
    assert grant.json()["recipient_id"] == changed["id"]
    assert grant.json()["recipient"] == correct


def test_exact_scope_review_restrictions_audit_and_revocation_unchanged(env):
    record = upload(env)
    owner = env.verifier.identities["owner"]
    heart = env.store.create_resource(owner, record["id"], "heart_audio")
    lung = env.store.create_resource(owner, record["id"], "lung_audio")
    person = lookup(env, record, env.users["analyst"]["handle"]).json()
    granted = share(env, record, person, resource_id=heart).json()
    analyst = env.verifier.identities["analyst"]
    env.store.authorize_resource(analyst, heart)
    for resource in (lung, record["original_resource_id"]):
        with pytest.raises(AccessDenied):
            env.store.authorize_resource(analyst, resource)
    assert share(env, record, person, permission="review", resource_id=heart).status_code == 403
    assert share(env, record, person, permission="review").status_code == 403
    other = lookup(env, record, env.users["other"]["handle"]).json()
    assert share(env, record, other, permission="review", resource_id=record["original_resource_id"]).status_code == 403
    second = upload(env)
    assert share(env, record, person, resource_id=second["original_resource_id"]).status_code == 403
    assignment = share(env, record, person, permission="review", resource_id=record["original_resource_id"])
    assert assignment.status_code == 201 and assignment.json()["assignment_public_id"].startswith("ASN-")
    assert env.client.delete(f"/api/grants/{granted['id']}", headers=auth()).status_code == 204
    with pytest.raises(AccessDenied):
        env.store.authorize_resource(analyst, heart)
    events = env.client.get("/api/admin/audit", headers=auth("admin")).json()["items"]
    assert any(event["action"] == "sharing.lookup" and event["target_id"] == record["id"] for event in events)
    assert any(event["action"] == "grant.created" and event["target_id"] == granted["id"] for event in events)
    assert any(event["action"] == "grant.revoked" and event["target_id"] == granted["id"] for event in events)


def test_recipient_contract_is_strict_and_legacy_id_still_works(env):
    record = upload(env)
    target = env.users["other"]
    endpoint = f"/api/recordings/{record['id']}/grants"
    for body in ({}, {"recipient_handle": target["handle"]},
                 {"recipient_id": target["id"], "recipient_handle": target["handle"]},
                 {"recipient_handle": target["handle"], "recipient_public_id": target["public_id"], "role": "admin"}):
        assert env.client.post(endpoint, headers=auth(), json=body).status_code == 422
    assert env.client.post(endpoint, headers=auth(), json={"recipient_id": target["id"]}).status_code == 201


def test_lookup_limit_covers_misses_recordings_and_restart(env):
    record = upload(env)
    other_record = upload(env)
    for _ in range(10):
        assert lookup(env, record, "missing.person").status_code == 404
    assert lookup(env, other_record, env.users["other"]["handle"]).status_code == 429
    env.app.state.store = M1Store(env.settings.database)
    assert lookup(env, record, env.users["other"]["handle"]).status_code == 429
    with env.store._connection(write=True) as db:
        now = time.time()
        db.execute("UPDATE af_audit SET created_at=? WHERE action='sharing.lookup'", (int(now) - 120,))
        db.executemany("INSERT INTO af_audit VALUES (?,?,?,?,?)",
                       [(uuid4().hex, env.users["owner"]["id"], "sharing.lookup", record["id"], int(now) - 120) for _ in range(90)])
    assert lookup(env, record, env.users["other"]["handle"]).status_code == 429
