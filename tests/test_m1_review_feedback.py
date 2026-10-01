"""Owner feedback reader; fictional identities and isolated HTTP/SQLite only."""
import time

import pytest

from app.access_foundation import Role, Status
from test_m1_api import auth, env, grant, upload


def assigned(env, record, **extra):
    return grant(env, record, permission="review", resource_id=record["original_resource_id"], **extra)


def save(env, assignment, notes="Low signal level; review the source recording."):
    response = env.client.put(f"/api/assignments/{assignment['id']}/review", headers=auth("analyst"),
                              json={"decision": "needs_attention", "notes": notes})
    assert response.status_code == 200, response.text
    return response.json()


def test_owner_reads_real_saved_feedback_and_pending_without_private_identity(env):
    record = upload(env)
    assignment = assigned(env, record)
    url = f"/api/recordings/{record['id']}/reviews"
    pending = env.client.get(url, headers=auth()).json()
    assert pending["total"] == 1
    item = pending["items"][0]
    assert item["decision"] == "pending" and item["updated_at"] is None and item["notes"] == ""
    assert item["assignment_state"] == "active"
    assert item["resource_kind"] == "original_audio"
    saved = save(env, assignment, "<script>not HTML</script>")
    response = env.client.get(url, headers=auth())
    item = response.json()["items"][0]
    assert item["notes"] == saved["notes"] and item["updated_at"] == saved["updated_at"]
    assert item["decision"] == "needs_attention"
    assert item["assignment_public_id"] == assignment["assignment_public_id"]
    assert item["reviewer_public_id"] == env.users["analyst"]["public_id"]
    assert item["reviewer_handle"] == env.users["analyst"]["handle"]
    assert "reviewer_id" not in item and "recipient_id" not in item
    assert "provider_uid" not in response.text and "example.invalid" not in response.text
    assert response.headers["cache-control"] == "private, no-store"
    # The reviewer endpoint does NOT acquire a new owner/Staff privilege.
    assert env.client.get(f"/api/assignments/{assignment['id']}/review", headers=auth()).status_code == 403


@pytest.mark.parametrize("actor", [None, "other", "admin", "analyst"])
def test_nonowner_cannot_read_feedback_even_with_recording_or_exact_media_grant(env, actor):
    record = upload(env)
    assignment = assigned(env, record)
    save(env, assignment)
    grant(env, record, recipient="other")
    url = f"/api/recordings/{record['id']}/reviews"
    response = env.client.get(url, headers=auth(actor) if actor else {})
    assert response.status_code == (403 if actor else 401)
    assert "Low signal" not in response.text
    assert env.client.get("/api/recordings/not-a-recording/reviews", headers=auth()).status_code == 403


def test_revoked_and_expired_saved_reviews_remain_owner_history_not_reviewer_access(env):
    record = upload(env)
    first = assigned(env, record)
    save(env, first)
    assert env.client.delete(f"/api/grants/{first['id']}", headers=auth()).status_code == 204
    second = assigned(env, record, expires_at=int(time.time()) + 3600)
    save(env, second, "Saved before expiry.")
    third = assigned(env, record)
    assert env.client.delete(f"/api/grants/{third['id']}", headers=auth()).status_code == 204
    with env.store._connection(write=True) as db:
        db.execute("UPDATE af_grants SET expires_at=? WHERE id=?", (int(time.time()) - 1, second["id"]))
    page = env.client.get(f"/api/recordings/{record['id']}/reviews", headers=auth()).json()
    assert page["total"] == 2  # Cancelled, never-reviewed assignment is not feedback.
    assert {i["assignment_state"] for i in page["items"]} == {"revoked", "expired"}
    for assignment in (first, second):
        url = f"/api/assignments/{assignment['id']}/review"
        assert env.client.get(url, headers=auth("analyst")).status_code == 403
        assert env.client.put(url, headers=auth("analyst"), json={"decision": "accepted", "notes": "No"}).status_code == 403


def test_feedback_is_bounded_and_owner_account_status_rechecked(env):
    record = upload(env)
    for _ in range(4):
        assigned(env, record)
    url = f"/api/recordings/{record['id']}/reviews"
    first = env.client.get(url, headers=auth()).json()
    rest = env.client.get(url + "?limit=3&offset=3", headers=auth()).json()
    assert first["total"] == rest["total"] == 4
    assert len(first["items"]) == 3 and len(rest["items"]) == 1
    assert not {i["assignment_id"] for i in first["items"]} & {i["assignment_id"] for i in rest["items"]}
    for query in ("limit=0", "limit=21", "offset=-1"):
        assert env.client.get(url + "?" + query, headers=auth()).status_code == 422
    env.store.change_account(env.verifier.identities["admin"], env.users["owner"]["id"],
                             confirmed_target_id=env.users["owner"]["id"], status=Status.SUSPENDED)
    assert env.client.get(url, headers=auth()).status_code == 403


def test_owner_authority_is_ownership_not_staff_role(env):
    record = upload(env)
    env.store.change_account(env.verifier.identities["admin"], env.users["owner"]["id"],
                             confirmed_target_id=env.users["owner"]["id"], role=Role.AUDIO_ANALYST)
    assert env.client.get(f"/api/recordings/{record['id']}/reviews", headers=auth()).status_code == 200


def test_saved_feedback_survives_reviewer_demotion_but_unverified_owner_denied(env):
    record = upload(env)
    assignment = assigned(env, record)
    save(env, assignment)
    env.store.change_account(env.verifier.identities["admin"], env.users["analyst"]["id"],
                             confirmed_target_id=env.users["analyst"]["id"], role=Role.HEALTHCARE_STAFF)
    url = f"/api/recordings/{record['id']}/reviews"
    item = env.client.get(url, headers=auth()).json()["items"][0]
    assert item["assignment_state"] == "reviewer_unavailable"
    assert item["notes"].startswith("Low signal")
    assert env.client.get(f"/api/assignments/{assignment['id']}/review", headers=auth("analyst")).status_code == 403
    with env.store._connection(write=True) as db:
        db.execute("UPDATE af_users SET email_verified=0 WHERE id=?", (env.users["owner"]["id"],))
    assert env.client.get(url, headers=auth()).status_code == 403
