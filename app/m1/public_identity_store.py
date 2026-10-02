"""Additive M1 metadata, filled in the existing write transaction before commit."""
from __future__ import annotations

import time
from contextlib import contextmanager

from .public_identity import IdentityError, handle_candidate, normalize_handle, public_reference

REFERENCE_TABLES = {
    "af_users": {"USR"}, "af_recordings": {"REC"}, "m1_jobs": {"JOB"},
    "af_resources": {"MED", "RES"}, "af_grants": {"GRT", "ASN"},
}


class PublicIdentityStore:
    @contextmanager
    def _connection(self, *, write=False):
        # Parent controls schema validation, BEGIN IMMEDIATE, commit and rollback.
        with super()._connection(write=write) as db:
            yield db
            if write:
                self._backfill_public_fields(db)

    @staticmethod
    def _new_public_id(db, table, prefix, column="public_id"):
        if prefix not in REFERENCE_TABLES.get(table, set()) or column not in {"public_id", "assignment_public_id"}:
            raise ValueError("Unsupported public reference allocation.")
        for _ in range(16):
            candidate = public_reference(prefix)
            if not db.execute(f"SELECT 1 FROM {table} WHERE {column}=?", (candidate,)).fetchone():
                return candidate
        raise IdentityError("identity_unavailable", "A public reference could not be assigned. Please retry.", 503)

    @staticmethod
    def _new_handle(db):
        for attempt in range(16):
            candidate = handle_candidate(suffix=attempt >= 8)
            if not db.execute("SELECT 1 FROM af_users WHERE normalized_handle=?", (candidate,)).fetchone():
                return candidate
        raise IdentityError("identity_unavailable", "A handle could not be assigned. Please retry.", 503)

    def _backfill_public_fields(self, db):
        # Indexed NULL lookups are cheap when metadata is already present. This
        # also covers inherited AF creation methods without changing their policy.
        for table, prefix in (("af_users", "USR"), ("af_recordings", "REC"), ("m1_jobs", "JOB")):
            for (entity_id,) in db.execute(f"SELECT id FROM {table} WHERE public_id IS NULL").fetchall():
                value = self._new_public_id(db, table, prefix)
                db.execute(f"UPDATE {table} SET public_id=? WHERE id=? AND public_id IS NULL", (value, entity_id))
        for entity_id, kind in db.execute("SELECT id,kind FROM af_resources WHERE public_id IS NULL").fetchall():
            value = self._new_public_id(db, "af_resources", "RES" if kind == "result" else "MED")
            db.execute("UPDATE af_resources SET public_id=? WHERE id=? AND public_id IS NULL", (value, entity_id))
        for (entity_id,) in db.execute("SELECT id FROM m1_results WHERE public_id IS NULL").fetchall():
            row = db.execute("SELECT public_id FROM af_resources WHERE id=? AND kind='result'", (entity_id,)).fetchone()
            if row is None or not row[0]:
                raise IdentityError("identity_unavailable", "Result reference metadata is unavailable.", 503)
            db.execute("UPDATE m1_results SET public_id=? WHERE id=? AND public_id IS NULL", (row[0], entity_id))
        for (entity_id,) in db.execute("SELECT id FROM af_grants WHERE public_id IS NULL").fetchall():
            value = self._new_public_id(db, "af_grants", "GRT")
            db.execute("UPDATE af_grants SET public_id=? WHERE id=? AND public_id IS NULL", (value, entity_id))
        for (entity_id,) in db.execute("SELECT id FROM af_grants WHERE permission='review' AND assignment_public_id IS NULL").fetchall():
            value = self._new_public_id(db, "af_grants", "ASN", "assignment_public_id")
            db.execute("UPDATE af_grants SET assignment_public_id=? WHERE id=? AND assignment_public_id IS NULL", (value, entity_id))
        for entity_id, handle in db.execute("SELECT id,handle FROM af_users WHERE handle IS NULL OR normalized_handle IS NULL").fetchall():
            normalized = normalize_handle(handle) if handle else self._new_handle(db)
            db.execute("UPDATE af_users SET handle=?,normalized_handle=? WHERE id=?", (normalized, normalized, entity_id))

    def _change_handle(self, db, actor, value):
        normalized = normalize_handle(value)
        if normalized == actor["normalized_handle"]:
            return
        if actor["handle_change_count"] >= 1:
            raise IdentityError("handle_change_used", "Your one self-service handle change has already been used.", 409)
        if db.execute("SELECT 1 FROM af_users WHERE normalized_handle=? AND id<>?", (normalized, actor["id"])).fetchone():
            raise IdentityError("handle_unavailable", "That handle is already in use. Try another name.", 409)
        db.execute("UPDATE af_users SET handle=?,normalized_handle=?,handle_change_count=1,handle_changed_at=? WHERE id=?",
                   (normalized, normalized, int(time.time()), actor["id"]))
        self._audit(db, actor["id"], "handle.changed", actor["id"])
