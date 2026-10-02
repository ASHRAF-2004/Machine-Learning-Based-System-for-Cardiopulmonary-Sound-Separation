"""Persistent M1 repository extending the tested foundation in one transaction domain.

Only the explicit separate M1 DB is initialized. Legacy uploaded_audio IDs are not
accepted or mapped automatically. No demo data is inserted.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from uuid import uuid4

from app.access_foundation import AccessDenied, DevelopmentAccessStore, VerifiedIdentity
from app.access_foundation.store import TABLES
from .processing_store import ProcessingStore
from .public_identity_store import PublicIdentityStore
from .sharing_store import HandleSharingStore
from .workspace_store import WorkspaceStore

M1_TABLES = {"m1_meta", "m1_recording_data", "m1_files", "m1_jobs", "m1_results",
             "m1_result_files", "m1_reviews", "m1_preferences"}


class M1Store(PublicIdentityStore, HandleSharingStore, WorkspaceStore, ProcessingStore, DevelopmentAccessStore):
    @staticmethod
    def _check_schema(db, *, allow_v1=False):
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if names != TABLES | M1_TABLES:
            raise ValueError("Not an isolated M1 database; legacy data is quarantined.")
        if [r[0] for r in db.execute("SELECT version FROM af_meta")] != [1] or [r[0] for r in db.execute("SELECT version FROM m1_meta")] not in ([[1], [2], [3]] if allow_v1 else [[3]]):
            raise ValueError("Unsupported M1 schema.")

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if names:
                self._check_schema(db, allow_v1=True)
            else:
                schemas = [Path(__file__).parents[1] / "access_foundation" / "schema.sql", Path(__file__).with_name("schema.sql")]
                for schema in schemas:
                    for statement in schema.read_text().split(";"):
                        if statement.strip():
                            db.execute(statement)
            if db.execute("SELECT version FROM m1_meta").fetchone()[0] == 1:
                migration = Path(__file__).with_name("migrations") / "002_processing.sql"
                for statement in migration.read_text().split(";"):
                    if statement.strip():
                        db.execute(statement)
            if db.execute("SELECT version FROM m1_meta").fetchone()[0] == 2:
                migration = Path(__file__).with_name("migrations") / "003_public_identity.sql"
                for statement in migration.read_text().split(";"):
                    if statement.strip():
                        db.execute(statement)
            self._backfill_public_fields(db)
            self._check_schema(db)
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
        self.path.chmod(0o600)

    @staticmethod
    def user_dto(row):
        return {"id": row["id"], "uid": row["provider_uid"], "email": row["email"],
                "display_name": row["display_name"], "role": row["role"],
                "status": row["status"], "email_verified": bool(row["email_verified"]),
                "public_id": row["public_id"], "handle": row["handle"],
                "handle_change_count": row["handle_change_count"], "handle_changed_at": row["handle_changed_at"]}

    def me(self, identity):
        with self._connection() as db:
            return self.user_dto(self._actor(db, identity))

    def account_exists(self, identity):
        with self._connection() as db:
            return db.execute("SELECT 1 FROM af_users WHERE provider_uid=?", (identity.uid,)).fetchone() is not None

    def update_profile(self, identity, display_name, handle=None):
        with self._connection(write=True) as db:
            actor = self._actor(db, identity)
            if handle is not None:
                self._change_handle(db, actor, handle)
            db.execute("UPDATE af_users SET display_name=?,updated_at=? WHERE id=?", (display_name, int(time.time()), actor["id"]))
            self._audit(db, actor["id"], "profile.changed", actor["id"])
        return self.me(identity)

    def preferences(self, identity, changes=None):
        with self._connection(write=changes is not None) as db:
            actor = self._actor(db, identity)
            row = db.execute("SELECT preferences_json FROM m1_preferences WHERE user_id=?", (actor["id"],)).fetchone()
            preferences = json.loads(row[0]) if row else {}
            if changes is not None:
                preferences.update(changes)
                db.execute("INSERT INTO m1_preferences VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET preferences_json=excluded.preferences_json", (actor["id"], json.dumps(preferences)))
                self._audit(db, actor["id"], "preferences.changed", actor["id"])
            return preferences

    def add_upload(self, identity, *, title, original_filename, relative_path, duration_sec, sample_rate_hz, channels, file_size_bytes, sha256=None):
        with self._connection(write=True) as db:
            actor = self._actor(db, identity)
            recording_id, resource_id = uuid4().hex, uuid4().hex
            db.execute("INSERT INTO af_recordings(id,owner_id,created_at) VALUES (?,?,?)", (recording_id, actor["id"], int(time.time())))
            db.execute("INSERT INTO af_resources(id,recording_id,kind) VALUES (?,?,?)", (resource_id, recording_id, "original_audio"))
            db.execute("INSERT INTO m1_recording_data VALUES (?,?,?,?,?,?,?,?)", (recording_id, title, original_filename, duration_sec, sample_rate_hz, channels, file_size_bytes, resource_id))
            db.execute("INSERT INTO m1_files(resource_id,relative_path,media_type,file_size_bytes,sha256) VALUES (?,?,?,?,?)", (resource_id, relative_path, "audio/wav", file_size_bytes, sha256))
            self._audit(db, actor["id"], "recording.uploaded", recording_id)
        return self.recording(identity, recording_id)

    def _visible_resources(self, db, actor, recording_id):
        owner = db.execute("SELECT owner_id FROM af_recordings WHERE id=?", (recording_id,)).fetchone()
        if owner is None:
            raise AccessDenied("Access denied.")
        self._active_user(db, owner[0])
        return db.execute(
            "SELECT r.*,f.media_type FROM af_resources r LEFT JOIN m1_files f ON f.resource_id=r.id "
            "WHERE r.recording_id=? AND (?=? OR EXISTS(SELECT 1 FROM af_grants g "
            "WHERE g.recording_id=r.recording_id AND g.recipient_id=? AND g.grantor_id=? "
            "AND g.status='active' AND g.permission IN ('read','review') "
            "AND (g.resource_id IS NULL OR g.resource_id=r.id) AND (g.expires_at IS NULL OR g.expires_at>?)))",
            (recording_id, actor["id"], owner[0], actor["id"], owner[0], int(time.time())),
        ).fetchall()

    @staticmethod
    def _resource_dto(row):
        return {"id": row["id"], "public_id": row["public_id"], "kind": row["kind"], "media_type": row["media_type"],
                "url": f"/api/media/{row['id']}" if row["media_type"] else None}

    def _recording(self, db, actor, recording_id):
        row = db.execute("SELECT d.*,o.owner_id,o.created_at,o.public_id FROM m1_recording_data d JOIN af_recordings o ON o.id=d.recording_id WHERE d.recording_id=?", (recording_id,)).fetchone()
        if row is None:
            raise AccessDenied("Access denied.")
        resources = self._visible_resources(db, actor, recording_id)
        if not resources:
            raise AccessDenied("Access denied.")
        dto = dict(row)
        dto["id"] = dto.pop("recording_id")
        dto["is_owner"] = dto["owner_id"] == actor["id"]
        dto["resources"] = [self._resource_dto(r) for r in resources]
        if dto["original_resource_id"] not in {r["id"] for r in resources}:
            dto["original_resource_id"] = None
            dto["original_filename"] = None
        return dto

    def recording(self, identity, recording_id):
        with self._connection() as db:
            return self._recording(db, self._actor(db, identity), recording_id)

    def recordings(self, identity):
        with self._connection() as db:
            actor = self._actor(db, identity)
            ids = db.execute(
                "SELECT DISTINCT o.id FROM af_recordings o JOIN af_users u ON u.id=o.owner_id "
                "WHERE u.status='active' AND u.email_verified=1 AND (o.owner_id=? OR EXISTS "
                "(SELECT 1 FROM af_grants g WHERE g.recording_id=o.id AND g.recipient_id=? AND g.grantor_id=o.owner_id "
                "AND g.status='active' AND (g.expires_at IS NULL OR g.expires_at>?))) ORDER BY o.created_at DESC",
                (actor["id"], actor["id"], int(time.time())),
            ).fetchall()
            return [self._recording(db, actor, r[0]) for r in ids]

    def update_recording(self, identity, recording_id, title):
        with self._connection(write=True) as db:
            actor = self._actor(db, identity)
            self._owner(db, actor, recording_id)
            db.execute("UPDATE m1_recording_data SET title=? WHERE recording_id=?", (title, recording_id))
            self._audit(db, actor["id"], "recording.updated", recording_id)
        return self.recording(identity, recording_id)

    def media(self, identity, resource_id):
        # Reuse the exact foundation policy. Immediately rechecked by API before open.
        self.authorize_resource(identity, resource_id)
        with self._connection() as db:
            row = db.execute("SELECT * FROM m1_files WHERE resource_id=?", (resource_id,)).fetchone()
            if row is None:
                raise AccessDenied("Access denied.")
            return dict(row)

    def grants(self, identity, recording_id):
        with self._connection() as db:
            actor = self._actor(db, identity)
            self._owner(db, actor, recording_id)
            return [self._sharing_grant_dto(r) for r in db.execute(
                "SELECT g.*,u.display_name AS recipient_display_name,u.handle AS recipient_handle,u.public_id AS recipient_public_id "
                "FROM af_grants g JOIN af_users u ON u.id=g.recipient_id WHERE g.recording_id=? ORDER BY g.created_at DESC,g.id",
                (recording_id,))]

    def grant_dto(self, identity, grant_id):
        with self._connection() as db:
            actor = self._actor(db, identity)
            row = db.execute(
                "SELECT g.*,u.display_name AS recipient_display_name,u.handle AS recipient_handle,u.public_id AS recipient_public_id "
                "FROM af_grants g JOIN af_users u ON u.id=g.recipient_id WHERE g.id=?", (grant_id,)).fetchone()
            if row is None or actor["id"] not in {row["grantor_id"], row["recipient_id"]}:
                raise AccessDenied("Access denied.")
            return self._sharing_grant_dto(row)

    def revoke_all(self, identity, recording_id, recipient_id, confirmed_recording_id):
        if recording_id != confirmed_recording_id:
            raise AccessDenied("Explicit recording confirmation required.")
        with self._connection(write=True) as db:
            actor = self._actor(db, identity)
            self._owner(db, actor, recording_id)
            grants = db.execute("SELECT id FROM af_grants WHERE recording_id=? AND recipient_id=? AND status='active'", (recording_id, recipient_id)).fetchall()
            for grant in grants:
                db.execute("UPDATE af_grants SET status='revoked',revoked_at=? WHERE id=?", (int(time.time()), grant[0]))
                self._audit(db, actor["id"], "grant.revoked", grant[0])
            return len(grants)

    def assignments(self, identity):
        with self._connection() as db:
            joins, values = self._review_scope(db, identity)
            return [dict(r) for r in db.execute(
                "SELECT g.*,d.title AS recording_title,o.public_id AS recording_public_id,r.kind AS resource_kind,"
                "COALESCE(v.decision,'pending') AS review_decision,v.updated_at AS review_updated_at "
                + joins +
                "ORDER BY CASE COALESCE(v.decision,'pending') WHEN 'pending' THEN 0 ELSE 1 END,g.created_at,g.id",
                values,
            )]

    def review(self, identity, grant_id, *, decision=None, notes=None):
        with self._connection(write=decision is not None) as db:
            actor = self._actor(db, identity)
            grant = db.execute("SELECT resource_id,assignment_public_id FROM af_grants WHERE id=?", (grant_id,)).fetchone()
            if grant is None:
                raise AccessDenied("Access denied.")
            self._authorize_review(db, identity, grant_id, grant[0])
            if decision is not None:
                db.execute("INSERT INTO m1_reviews VALUES (?,?,?,?,?,?) ON CONFLICT(assignment_id) DO UPDATE SET decision=excluded.decision,notes=excluded.notes,updated_at=excluded.updated_at", (grant_id, grant[0], actor["id"], decision, notes, int(time.time())))
                self._audit(db, actor["id"], "review.updated", grant_id)
            row = db.execute("SELECT * FROM m1_reviews WHERE assignment_id=?", (grant_id,)).fetchone()
            context = db.execute(
                "SELECT r.kind AS resource_kind,d.title AS recording_title,o.public_id AS recording_public_id "
                "FROM af_resources r JOIN af_recordings o ON o.id=r.recording_id "
                "LEFT JOIN m1_recording_data d ON d.recording_id=o.id WHERE r.id=?", (grant[0],)).fetchone()
            value = dict(row) if row else {"assignment_id": grant_id, "resource_id": grant[0], "reviewer_id": actor["id"], "decision": "pending", "notes": "", "updated_at": None}
            return {**value, **dict(context), "assignment_public_id": grant["assignment_public_id"]}

    def recording_reviews(self, identity, recording_id, *, limit=3, offset=0):
        """Owner's saved feedback/current assignments, not reviewer drafts or media authority.

        Revocation prevents future reviewer access; saved observations remain part of
        the owner's recording history. Both count and page use the same read snapshot.
        """
        if not 1 <= limit <= 20 or offset < 0:
            raise ValueError("Invalid feedback page.")
        with self._connection() as db:
            actor = self._actor(db, identity)
            self._owner(db, actor, recording_id)
            now = int(time.time())
            joins = (
                "FROM af_grants g JOIN af_recordings o ON o.id=g.recording_id "
                "JOIN af_resources r ON r.id=g.resource_id AND r.recording_id=o.id "
                "JOIN af_users u ON u.id=g.recipient_id "
                "LEFT JOIN m1_reviews v ON v.assignment_id=g.id "
                "AND v.resource_id=g.resource_id AND v.reviewer_id=g.recipient_id "
                "WHERE g.recording_id=? AND g.grantor_id=o.owner_id "
                "AND g.permission='review' AND r.kind IN ('original_audio','result') "
                "AND (v.assignment_id IS NOT NULL OR (g.status='active' "
                "AND (g.expires_at IS NULL OR g.expires_at>?) AND u.role='audio_analyst' "
                "AND u.status='active' AND u.email_verified=1)) "
            )
            total = db.execute("SELECT COUNT(*) " + joins, (recording_id, now)).fetchone()[0]
            rows = db.execute(
                "SELECT g.id AS assignment_id,g.assignment_public_id,g.resource_id,"
                "r.kind AS resource_kind,u.display_name AS reviewer_display_name,"
                "u.handle AS reviewer_handle,u.public_id AS reviewer_public_id,"
                "COALESCE(v.decision,'pending') AS decision,COALESCE(v.notes,'') AS notes,"
                "v.updated_at,g.created_at AS assigned_at,"
                "CASE WHEN g.status='revoked' THEN 'revoked' "
                "WHEN g.expires_at IS NOT NULL AND g.expires_at<=? THEN 'expired' "
                "WHEN u.role!='audio_analyst' OR u.status!='active' OR u.email_verified!=1 "
                "THEN 'reviewer_unavailable' ELSE 'active' END AS assignment_state "
                + joins + "ORDER BY v.updated_at IS NULL,v.updated_at DESC,g.created_at DESC,g.id LIMIT ? OFFSET ?",
                (now, recording_id, now, limit, offset),
            ).fetchall()
            return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    def results(self, identity, result_id=None):
        with self._connection() as db:
            actor = self._actor(db, identity)
            rows = db.execute("SELECT * FROM m1_results WHERE (? IS NULL OR id=?) ORDER BY created_at DESC", (result_id, result_id)).fetchall()
            results = []
            for row in rows:
                try:
                    resources = self._visible_resources(db, actor, row["recording_id"])
                except AccessDenied:
                    continue
                allowed = {r["id"] for r in resources}
                if row["id"] not in allowed:
                    continue
                file_ids = {r[0] for r in db.execute("SELECT resource_id FROM m1_result_files WHERE result_id=?", (row["id"],))}
                owner = db.execute("SELECT owner_id FROM af_recordings WHERE id=?", (row["recording_id"],)).fetchone()[0]
                value = dict(row)
                value["provenance"] = json.loads(value.pop("provenance_json") or "null")
                results.append({**value, "resources": [self._resource_dto(r) for r in resources if r["id"] in file_ids], "is_owner": owner == actor["id"]})
            if result_id:
                if not results:
                    raise AccessDenied("Access denied.")
                return results[0]
            return results

    def jobs(self, identity, job_id=None):
        with self._connection() as db:
            actor = self._actor(db, identity)
            # Jobs expose owner operational state; scoped-result recipients use result DTOs.
            rows = db.execute("SELECT j.* FROM m1_jobs j JOIN af_recordings o ON o.id=j.recording_id WHERE o.owner_id=? AND (? IS NULL OR j.id=?) ORDER BY j.created_at DESC", (actor["id"], job_id, job_id)).fetchall()
            if job_id:
                if not rows:
                    raise AccessDenied("Access denied.")
                return self._public_job(rows[0])
            return [self._public_job(r) for r in rows]

    def users(self, identity):
        with self._connection() as db:
            self._admin(db, identity)
            return [self.user_dto(r) for r in db.execute("SELECT * FROM af_users ORDER BY created_at,id")]

    def audit(self, identity):
        with self._connection() as db:
            self._admin(db, identity)
            return [dict(r) for r in db.execute("SELECT * FROM af_audit ORDER BY created_at DESC,id LIMIT 200")]
