"""Friendly review context is derived only from the current exact assignment.

Fictional identities/temp SQLite/HTTP fixture bytes; no model/provider/listening test.
"""
import time

import pytest

from test_m1_api import auth, env, grant, upload


def assigned(env, recording):
    return grant(env, recording, permission="review", resource_id=recording["original_resource_id"])


def test_assignment_context_is_friendly_current_and_has_no_private_notes(env):
    record = upload(env)
    assignment = assigned(env, record)
    response = env.client.get("/api/assignments", headers=auth("analyst"))
    assert response.status_code == 200
    row = response.json()["items"][0]
    assert row["id"] == assignment["id"]
    assert row["recording_title"] == record["title"]
    assert row["recording_public_id"] == record["public_id"]
    assert row["resource_kind"] == "original_audio"
    assert row["review_decision"] == "pending" and row["review_updated_at"] is None
    assert "notes" not in row and "email" not in row and "uid" not in row
    path = f"/api/assignments/{assignment['id']}/review"
    initial = env.client.get(path, headers=auth("analyst")).json()
    assert initial["recording_title"] == record["title"]
    assert initial["recording_public_id"] == record["public_id"]
    saved = env.client.put(path, headers=auth("analyst"), json={"decision": "accepted", "notes": "Non-diagnostic local review."})
    assert saved.status_code == 200 and saved.json()["notes"] == "Non-diagnostic local review."
    env.client.patch(f"/api/recordings/{record['id']}", headers=auth(), json={"title": "Updated actual title"})
    row = env.client.get("/api/assignments", headers=auth("analyst")).json()["items"][0]
    assert row["recording_title"] == "Updated actual title" and row["review_decision"] == "accepted"
    assert isinstance(row["review_updated_at"], int) and "notes" not in row
    assert env.client.get(path, headers=auth("analyst")).json()["notes"] == "Non-diagnostic local review."


def test_list_and_detail_keep_role_recipient_and_sibling_boundaries(env):
    record = upload(env)
    assignment = assigned(env, record)
    path = f"/api/assignments/{assignment['id']}/review"
    assert env.client.get("/api/assignments").status_code == 401
    assert env.client.get(path).status_code == 401
    for actor in ("owner", "other", "admin"):
        assert env.client.get("/api/assignments", headers=auth(actor)).status_code == 403
        assert env.client.get(path, headers=auth(actor)).status_code == 403
    unrelated = upload(env)
    assert env.client.get(f"/api/recordings/{unrelated['id']}", headers=auth("analyst")).status_code == 403
    heart = env.store.create_resource(env.verifier.identities["owner"], record["id"], "heart_audio")
    assert env.client.get(f"/api/media/{heart}", headers=auth("analyst")).status_code == 403
    assert len(env.client.get("/api/assignments", headers=auth("analyst")).json()["items"]) == 1


@pytest.mark.parametrize("cause", ["revoked", "expired", "owner_suspended", "owner_unverified"])
def test_invalid_assignment_hides_context_and_blocks_saved_review(env, cause):
    record = upload(env)
    assignment = assigned(env, record)
    path = f"/api/assignments/{assignment['id']}/review"
    assert env.client.put(path, headers=auth("analyst"), json={"decision": "needs_attention", "notes": "Private review text"}).status_code == 200
    if cause == "revoked":
        assert env.client.delete(f"/api/grants/{assignment['id']}", headers=auth()).status_code == 204
    else:
        with env.store._connection(write=True) as db:
            if cause == "expired":
                db.execute("UPDATE af_grants SET expires_at=? WHERE id=?", (int(time.time()) - 1, assignment["id"]))
            elif cause == "owner_suspended":
                db.execute("UPDATE af_users SET status='suspended' WHERE id=?", (env.users["owner"]["id"],))
            else:
                db.execute("UPDATE af_users SET email_verified=0 WHERE id=?", (env.users["owner"]["id"],))
    assert env.client.get("/api/assignments", headers=auth("analyst")).json() == {"items": []}
    denied = env.client.get(path, headers=auth("analyst"))
    assert denied.status_code == 403 and "Private review text" not in denied.text
    assert env.client.put(path, headers=auth("analyst"), json={"decision": "accepted", "notes": "Should not save"}).status_code == 403
