"""Read-only workspace projections under the existing account/resource policy."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from app.access_foundation import AccessDenied
from .ml_contract import MODEL_VERSION


class WorkspaceStore:
    def _review_scope(self, db, identity):
        """One scope for current assignment lists and saved review history.

        No history route may resurrect revoked notes, titles or media access.
        This exactly preserves the existing assignment-list predicates.
        """
        actor = self._actor(db, identity)
        if actor["role"] != "audio_analyst":
            raise AccessDenied("Access denied.")
        joins = (
            "FROM af_grants g JOIN af_recordings o ON o.id=g.recording_id "
            "JOIN af_users u ON u.id=o.owner_id "
            "JOIN af_resources r ON r.id=g.resource_id AND r.recording_id=o.id "
            "LEFT JOIN m1_recording_data d ON d.recording_id=o.id "
            "LEFT JOIN m1_reviews v ON v.assignment_id=g.id "
            "WHERE g.recipient_id=? AND g.permission='review' AND g.status='active' "
            "AND g.grantor_id=o.owner_id AND u.status='active' AND u.email_verified=1 "
            "AND (g.expires_at IS NULL OR g.expires_at>?) "
        )
        return joins, (actor["id"], int(time.time()))

    def review_history(self, identity, *, limit=3, offset=0):
        if not 1 <= limit <= 20 or offset < 0:
            raise ValueError("Invalid review page.")
        with self._connection() as db:
            joins, values = self._review_scope(db, identity)
            joins += "AND v.resource_id=g.resource_id AND v.reviewer_id=g.recipient_id "
            total = db.execute("SELECT COUNT(*) " + joins, values).fetchone()[0]
            rows = db.execute(
                "SELECT g.id AS assignment_id,g.assignment_public_id,g.resource_id,"
                "d.title AS recording_title,o.public_id AS recording_public_id,"
                "r.kind AS resource_kind,v.decision,v.notes,v.updated_at " + joins +
                "ORDER BY v.updated_at DESC,g.id LIMIT ? OFFSET ?", (*values, limit, offset),
            ).fetchall()
            return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    def insights(self, identity):
        """Whole own Library counts, not a grantee/global-admin audio aggregate.

        Three fixed aggregate queries; never one query per recording. Day buckets
        are the last seven UTC calendar dates through this response timestamp.
        """
        now = int(time.time())
        today = datetime.fromtimestamp(now, timezone.utc).date()
        first = today - timedelta(days=6)
        start = int(datetime.combine(first, datetime.min.time(), timezone.utc).timestamp())
        with self._connection() as db:
            actor = self._actor(db, identity)
            own = (
                "WITH own AS (SELECT o.created_at,d.duration_sec,j.status,j.completed_at "
                "FROM af_recordings o JOIN m1_recording_data d ON d.recording_id=o.id "
                "LEFT JOIN m1_jobs j ON j.recording_id=o.id AND j.model_version=? "
                "WHERE o.owner_id=?) "
            )
            values = (MODEL_VERSION, actor["id"])
            row = db.execute(own +
                "SELECT COUNT(*) AS total,COALESCE(SUM(duration_sec),0) AS recorded_seconds,"
                "COALESCE(SUM(status IS NULL),0) AS recorded,"
                "COALESCE(SUM(status='queued'),0) AS queued,"
                "COALESCE(SUM(status='processing'),0) AS processing,"
                "COALESCE(SUM(status='succeeded'),0) AS ready,"
                "COALESCE(SUM(status='failed'),0) AS failed FROM own", values).fetchone()
            added = dict(db.execute(own +
                "SELECT CAST(created_at/86400 AS INTEGER),COUNT(*) FROM own "
                "WHERE created_at>=? AND created_at<=? GROUP BY 1", (*values, start, now)))
            completed = dict(db.execute(own +
                "SELECT CAST(completed_at/86400 AS INTEGER),COUNT(*) FROM own "
                "WHERE status='succeeded' AND completed_at>=? AND completed_at<=? GROUP BY 1",
                (*values, start, now)))
            days = []
            for index in range(7):
                date = first + timedelta(days=index)
                epoch_day = start // 86400 + index
                days.append({"date": date.isoformat(), "recordings": added.get(epoch_day, 0),
                             "completed": completed.get(epoch_day, 0)})
            return {"scope": "owned_recordings", "timezone": "UTC", "as_of": now,
                    "counts": {key: row[key] for key in ("total", "recorded", "queued", "processing", "ready", "failed")},
                    "recorded_seconds": row["recorded_seconds"], "days": days}
