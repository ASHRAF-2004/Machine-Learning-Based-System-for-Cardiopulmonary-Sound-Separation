"""New reads use real temp SQLite and fixed fictional identity injection only.

These zero-WAV API fixtures test storage/access, not separation quality/listening.
"""
import time

import pytest

from app.access_foundation import Role
from test_m1_api import auth, env, grant, upload


def saved_review(env, record, notes="Saved workflow observation"):
    assignment = grant(env, record, permission="review", resource_id=record["original_resource_id"])
    response = env.client.put(f"/api/assignments/{assignment['id']}/review", headers=auth("analyst"),
                              json={"decision": "accepted", "notes": notes})
    assert response.status_code == 200
    return assignment


def test_insights_empty_and_own_recording_aggregates(env):
    empty = env.client.get("/api/insights", headers=auth()).json()
    assert empty["scope"] == "owned_recordings"
    assert empty["counts"] == {"total": 0, "recorded": 0, "queued": 0, "processing": 0, "ready": 0, "failed": 0}
    assert empty["recorded_seconds"] == 0 and len(empty["days"]) == 7
    record = upload(env)
    data = env.client.get("/api/insights", headers=auth()).json()
    assert data["counts"] == {"total": 1, "recorded": 1, "queued": 0, "processing": 0, "ready": 0, "failed": 0}
    assert data["recorded_seconds"] == pytest.approx(0.1)
    assert sum(day["recordings"] for day in data["days"]) == 1
    assert all(set(day) == {"date", "recordings", "completed"} for day in data["days"])
    assert record["id"] not in str(data) and record["title"] not in str(data)


def test_insights_current_durable_states_and_completed_dates(env):
    records = [upload(env) for _ in range(4)]
    jobs = [env.store.request_separation(env.verifier.identities["owner"], record["id"]) for record in records]
    now = int(time.time())
    with env.store._connection(write=True) as db:
        for job, state in zip(jobs, ("queued", "processing", "failed", "succeeded")):
            db.execute("UPDATE m1_jobs SET status=?,completed_at=? WHERE id=?", (state, now if state in ("failed", "succeeded") else None, job["id"]))
    response = env.client.get("/api/insights", headers=auth())
    assert response.status_code == 200
    data = response.json()
    assert data["counts"] == {"total": 4, "recorded": 0, "queued": 1, "processing": 1, "ready": 1, "failed": 1}
    assert data["recorded_seconds"] == pytest.approx(0.4)
    assert sum(day["completed"] for day in data["days"]) == 1
    assert data["timezone"] == "UTC"


def test_insights_never_counts_shared_or_other_owner_even_for_admin(env):
    record = upload(env)
    grant(env, record, recipient="other", resource_id=record["original_resource_id"])
    grant(env, record, recipient="analyst", permission="review", resource_id=record["original_resource_id"])
    for outsider in ("other", "analyst", "admin"):
        data = env.client.get("/api/insights", headers=auth(outsider)).json()
        assert data["counts"]["total"] == 0 and data["recorded_seconds"] == 0
        assert sum(day["recordings"] for day in data["days"]) == 0
    assert env.client.get("/api/insights").status_code == 401
    with env.store._connection(write=True) as db:
        db.execute("UPDATE af_users SET status='suspended' WHERE id=?", (env.users["owner"]["id"],))
    assert env.client.get("/api/insights", headers=auth()).status_code == 403


def test_saved_review_history_is_current_exact_scope_and_plain_text(env):
    record = upload(env)
    assignment = saved_review(env, record, "<script>not markup</script>")
    pending = grant(env, record, permission="review", resource_id=record["original_resource_id"])
    response = env.client.get("/api/reviews/history", headers=auth("analyst"))
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 1 and page["limit"] == 3 and page["offset"] == 0
    row = page["items"][0]
    assert row["assignment_id"] == assignment["id"] and pending["id"] not in str(page)
    assert row["notes"] == "<script>not markup</script>"
    assert row["recording_title"] == record["title"] and row["resource_kind"] == "original_audio"
    assert "reviewer_id" not in row and "uid" not in row and "email" not in row
    assert env.client.get(f"/api/media/{record['original_resource_id']}", headers=auth("analyst")).status_code == 200


@pytest.mark.parametrize("actor", [None, "owner", "other", "admin"])
def test_history_rejects_non_analysts_before_private_read(env, actor):
    saved_review(env, upload(env), "Never disclose this")
    response = env.client.get("/api/reviews/history", headers=auth(actor) if actor else {})
    assert response.status_code == (401 if actor is None else 403)
    assert "Never disclose this" not in response.text


@pytest.mark.parametrize("cause", ["revoked", "expired", "owner_suspended", "owner_unverified", "demoted"])
def test_history_does_not_resurrect_revoked_or_unavailable_context(env, cause):
    record = upload(env)
    assignment = saved_review(env, record, "No longer available private notes")
    if cause == "revoked":
        assert env.client.delete(f"/api/grants/{assignment['id']}", headers=auth()).status_code == 204
    elif cause == "demoted":
        env.store.change_account(env.verifier.identities["admin"], env.users["analyst"]["id"],
                                 confirmed_target_id=env.users["analyst"]["id"], role=Role.HEALTHCARE_STAFF)
    else:
        with env.store._connection(write=True) as db:
            if cause == "expired":
                db.execute("UPDATE af_grants SET expires_at=? WHERE id=?", (int(time.time()) - 1, assignment["id"]))
            elif cause == "owner_suspended":
                db.execute("UPDATE af_users SET status='suspended' WHERE id=?", (env.users["owner"]["id"],))
            else:
                db.execute("UPDATE af_users SET email_verified=0 WHERE id=?", (env.users["owner"]["id"],))
    response = env.client.get("/api/reviews/history", headers=auth("analyst"))
    assert response.status_code == (403 if cause == "demoted" else 200)
    assert "No longer available" not in response.text and record["title"] not in response.text
    if cause != "demoted":
        assert response.json()["total"] == 0 and response.json()["items"] == []
    if cause in ("expired", "revoked", "demoted"):
        owner = env.client.get(f"/api/recordings/{record['id']}/reviews", headers=auth()).json()
        assert owner["items"][0]["notes"] == "No longer available private notes"


def test_history_bounded_page_has_real_total_and_latest_saved_only(env):
    record = upload(env)
    assignments = [saved_review(env, record, f"Observation {i}") for i in range(4)]
    page = env.client.get("/api/reviews/history?limit=3&offset=3", headers=auth("analyst")).json()
    assert page["total"] == 4 and len(page["items"]) == 1
    env.client.put(f"/api/assignments/{assignments[0]['id']}/review", headers=auth("analyst"),
                   json={"decision": "needs_attention", "notes": "Latest observation"})
    rows = env.client.get("/api/reviews/history?limit=20", headers=auth("analyst")).json()
    assert rows["total"] == 4 and len(rows["items"]) == 4
    assert next(row for row in rows["items"] if row["assignment_id"] == assignments[0]["id"])["notes"] == "Latest observation"
    for query in ("limit=0", "limit=21", "offset=-1", "offset=oops"):
        assert env.client.get("/api/reviews/history?" + query, headers=auth("analyst")).status_code == 422
