"""Exact owner-context handle sharing; never a public user directory or login alias."""
from __future__ import annotations

import time

from .public_identity import IdentityError, normalize_handle

LOOKUP_PER_MINUTE = 10
LOOKUP_PER_HOUR = 100


class HandleSharingStore:
    @staticmethod
    def _recipient_by_handle(db, actor, handle):
        normalized = normalize_handle(handle.strip().removeprefix("@"))
        return db.execute(
            "SELECT id,display_name,handle,public_id FROM af_users WHERE normalized_handle=? "
            "AND status='active' AND email_verified=1 AND id<>? "
            "AND role IN ('healthcare_staff','audio_analyst','admin') AND public_id IS NOT NULL",
            (normalized, actor["id"]),
        ).fetchone()

    def sharing_recipient(self, identity, recording_id, handle):
        with self._connection(write=True) as db:
            actor = self._actor(db, identity)
            self._owner(db, actor, recording_id)
            now = int(time.time())
            counts = db.execute(
                "SELECT COUNT(*),COALESCE(SUM(created_at>?),0) FROM af_audit "
                "WHERE actor_id=? AND action='sharing.lookup' AND created_at>?",
                (now - 60, actor["id"], now - 3600),
            ).fetchone()
            if counts[0] >= LOOKUP_PER_HOUR or counts[1] >= LOOKUP_PER_MINUTE:
                raise IdentityError("sharing_lookup_limited", "Please wait before looking up another person.", 429)
            recipient = self._recipient_by_handle(db, actor, handle)
            # Persist misses too. No searched handles, emails or tokens in audit.
            self._audit(db, actor["id"], "sharing.lookup", recording_id)
            value = {key: recipient[key] for key in ("display_name", "handle", "public_id")} if recipient else None
        if value is None:
            raise IdentityError("recipient_unavailable", "No available person matches that exact handle.", 404)
        return value

    def grant_by_handle(self, identity, recording_id, recipient_handle, recipient_public_id, **scope):
        with self._connection(write=True) as db:
            actor = self._actor(db, identity)
            self._owner(db, actor, recording_id)
            recipient = self._recipient_by_handle(db, actor, recipient_handle)
            if recipient is None or recipient["public_id"] != recipient_public_id:
                raise IdentityError("recipient_unavailable", "Find and confirm the recipient again before sharing.", 404)
            # Resolve AND authorize in the same BEGIN IMMEDIATE transaction. A
            # renamed/reassigned handle cannot redirect a confirmed grant.
            return self._grant_access(db, identity, recording_id, recipient["id"], **scope)

    @staticmethod
    def _sharing_grant_dto(row):
        value = dict(row)
        recipient = {key: value.pop("recipient_" + key) for key in ("display_name", "handle", "public_id")}
        return {**value, "recipient": recipient}
