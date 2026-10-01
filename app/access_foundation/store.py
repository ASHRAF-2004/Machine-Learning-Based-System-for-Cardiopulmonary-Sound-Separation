"""Stdlib-only, explicit-path SQLite development authorization harness.

No legacy DB imports, automatic migration, passwords, private files or HTTP routes.
All mutations re-resolve the actor and authorize within BEGIN IMMEDIATE, including
the last-admin count and update. The DB file/process are a trusted boundary.
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from .identity import IdentityDirectory, VerifiedIdentity, require_verified


class AccessDenied(PermissionError):
    pass


class Role(str, Enum):
    HEALTHCARE_STAFF = "healthcare_staff"
    AUDIO_ANALYST = "audio_analyst"
    ADMIN = "admin"


class Status(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


RESOURCE_KINDS = frozenset({
    "original_audio", "heart_audio", "lung_audio", "waveform",
    "spectrogram", "context", "result",
})
TABLES = frozenset({
    "af_meta", "af_users", "af_recordings", "af_resources", "af_grants",
    "af_bootstrap", "af_audit",
})


@dataclass(frozen=True)
class Account:
    id: str
    provider_uid: str
    role: Role
    status: Status


class DevelopmentAccessStore:
    """Not a production database adapter. No default path; no implicit init."""

    def __init__(self, path: Path):
        self.path = Path(path).resolve()

    @contextmanager
    def _connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        # mode=rw refuses to silently create an uninitialized database on a typo.
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            self._check_schema(db)
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _check_schema(db: sqlite3.Connection) -> None:
        names = {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )}
        if names != TABLES:
            raise ValueError("Not an isolated access-foundation development database.")
        versions = [r[0] for r in db.execute("SELECT version FROM af_meta")]
        if versions != [1]:
            raise ValueError("Unsupported development schema version.")

    def initialize(self) -> None:
        """Explicitly initialize an empty standalone file, never a legacy schema."""
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("BEGIN IMMEDIATE")
            names = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )}
            if names:
                self._check_schema(db)
            else:
                # Individual execute preserves the encompassing transaction;
                # executescript would implicitly commit before the migration.
                for statement in Path(__file__).with_name("schema.sql").read_text().split(";"):
                    if statement.strip():
                        db.execute(statement)
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _account(row: sqlite3.Row) -> Account:
        return Account(row["id"], row["provider_uid"], Role(row["role"]), Status(row["status"]))

    @staticmethod
    def _active_user(db: sqlite3.Connection, user_id: str) -> sqlite3.Row:
        row = db.execute("SELECT * FROM af_users WHERE id=?", (user_id,)).fetchone()
        if row is None or row["status"] != "active" or row["email_verified"] != 1:
            raise AccessDenied("Access denied.")
        if row["role"] not in {r.value for r in Role}:
            raise AccessDenied("Access denied.")
        return row

    def _actor(self, db: sqlite3.Connection, identity: VerifiedIdentity) -> sqlite3.Row:
        require_verified(identity)
        row = db.execute("SELECT id FROM af_users WHERE provider_uid=?", (identity.uid,)).fetchone()
        if row is None:
            raise AccessDenied("Access denied.")
        return self._active_user(db, row["id"])

    def _admin(self, db: sqlite3.Connection, identity: VerifiedIdentity) -> sqlite3.Row:
        actor = self._actor(db, identity)
        if actor["role"] != Role.ADMIN.value:
            raise AccessDenied("Access denied.")
        return actor

    @staticmethod
    def _audit(db: sqlite3.Connection, actor: str, action: str, target: str) -> None:
        # No free-form payloads: never tokens, email, reset URLs, audio or notes.
        db.execute("INSERT INTO af_audit VALUES (?,?,?,?,?)", (
            uuid4().hex, actor, action, target, int(time.time()),
        ))

    def register_verified_identity(self, identity: VerifiedIdentity, *, display_name: str = "") -> Account:
        """Trusted post-verification onboarding; cannot accept a requested role.

        Stable UID is the sole lookup key. Equal email strings never merge users.
        Existing suspended users are not reactivated by logging in again.
        """
        require_verified(identity)
        if not isinstance(display_name, str) or len(display_name) > 200:
            raise ValueError("Invalid display name.")
        with self._connection(write=True) as db:
            row = db.execute("SELECT * FROM af_users WHERE provider_uid=?", (identity.uid,)).fetchone()
            if row is None:
                now, user_id = int(time.time()), uuid4().hex
                db.execute("INSERT INTO af_users(id,provider_uid,email,display_name,role,status,email_verified,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", (
                    user_id, identity.uid, identity.email, display_name,
                    Role.HEALTHCARE_STAFF.value, Status.ACTIVE.value, 1, now, now,
                ))
                self._audit(db, user_id, "account.registered", user_id)
            return self._account(self._actor(db, identity))

    def resolve_account(self, identity: VerifiedIdentity) -> Account:
        with self._connection() as db:
            return self._account(self._actor(db, identity))

    def require_admin(self, identity: VerifiedIdentity) -> Account:
        with self._connection() as db:
            return self._account(self._admin(db, identity))

    def bootstrap_first_admin(
        self, directory: IdentityDirectory, *, provider_uid: str, confirmed_uid: str,
    ) -> bool:
        """Trusted operator ONLY. Existing verified provider AND local user required.

        Returns True once, False on an unchanged same-user retry. A permanent
        singleton marker prevents re-bootstrap after demotion/disablement. Never
        expose this method through signup, an HTTP endpoint, or client role data.
        """
        if not provider_uid or provider_uid != confirmed_uid:
            raise AccessDenied("Exact UID confirmation required.")
        identity = directory.lookup_existing(provider_uid)
        require_verified(identity)
        if identity.uid != provider_uid:
            raise AccessDenied("Identity mismatch.")
        with self._connection(write=True) as db:
            target = self._actor(db, identity)
            marker = db.execute("SELECT user_id FROM af_bootstrap WHERE singleton=1").fetchone()
            if marker:
                if marker[0] == target["id"] and target["role"] == Role.ADMIN.value:
                    return False
                raise AccessDenied("Bootstrap has already been consumed.")
            if db.execute("SELECT 1 FROM af_users WHERE role='admin' LIMIT 1").fetchone():
                raise AccessDenied("An administrator already exists; use authorized account management.")
            db.execute("UPDATE af_users SET role='admin',updated_at=? WHERE id=?", (
                int(time.time()), target["id"],
            ))
            db.execute("INSERT INTO af_bootstrap VALUES (1,?,?)", (target["id"], int(time.time())))
            self._audit(db, "trusted-bootstrap", "admin.bootstrap", target["id"])
            return True

    def change_account(
        self, identity: VerifiedIdentity, target_id: str, *, confirmed_target_id: str,
        role: Role | None = None, status: Status | None = None,
    ) -> Account:
        if target_id != confirmed_target_id or not target_id or (role is None and status is None):
            raise AccessDenied("Explicit target confirmation and a change are required.")
        if role is not None and not isinstance(role, Role):
            raise ValueError("Unknown role.")
        if status is not None and not isinstance(status, Status):
            raise ValueError("Unknown account status.")
        with self._connection(write=True) as db:
            actor = self._admin(db, identity)
            target = db.execute("SELECT * FROM af_users WHERE id=?", (target_id,)).fetchone()
            if target is None:
                raise AccessDenied("Access denied.")
            if actor["id"] == target["id"] and (role is not None or status is not None):
                raise AccessDenied("Administrators cannot change their own role or status.")
            if role is not None and target["email_verified"] != 1:
                raise AccessDenied("Role changes require an existing verified account.")
            new_role = role.value if role is not None else target["role"]
            new_status = status.value if status is not None else target["status"]
            was_active_admin = target["role"] == "admin" and target["status"] == "active" and target["email_verified"] == 1
            remains_active_admin = new_role == "admin" and new_status == "active" and target["email_verified"] == 1
            if was_active_admin and not remains_active_admin:
                count = db.execute(
                    "SELECT COUNT(*) FROM af_users WHERE role='admin' AND status='active' AND email_verified=1"
                ).fetchone()[0]
                if count <= 1:
                    raise AccessDenied("The last active administrator cannot be removed.")
            db.execute("UPDATE af_users SET role=?,status=?,updated_at=? WHERE id=?", (
                new_role, new_status, int(time.time()), target_id,
            ))
            self._audit(db, actor["id"], "account.changed", target_id)
            return self._account(db.execute("SELECT * FROM af_users WHERE id=?", (target_id,)).fetchone())

    def create_recording(self, identity: VerifiedIdentity) -> str:
        """Metadata-only fixture record. Owner is always resolved from identity."""
        with self._connection(write=True) as db:
            actor = self._actor(db, identity)
            recording_id = uuid4().hex
            db.execute("INSERT INTO af_recordings(id,owner_id,created_at) VALUES (?,?,?)", (recording_id, actor["id"], int(time.time())))
            return recording_id

    def _owner(self, db: sqlite3.Connection, actor: sqlite3.Row, recording_id: str) -> None:
        row = db.execute("SELECT owner_id FROM af_recordings WHERE id=?", (recording_id,)).fetchone()
        if row is None or row[0] != actor["id"]:
            raise AccessDenied("Access denied.")

    def require_owner(self, identity: VerifiedIdentity, recording_id: str) -> None:
        """Owner-only mutation predicate; integration must check in its write txn."""
        with self._connection() as db:
            self._owner(db, self._actor(db, identity), recording_id)

    def create_resource(self, identity: VerifiedIdentity, recording_id: str, kind: str) -> str:
        if kind not in RESOURCE_KINDS:
            raise ValueError("Unknown private resource kind.")
        with self._connection(write=True) as db:
            self._owner(db, self._actor(db, identity), recording_id)
            resource_id = uuid4().hex
            db.execute("INSERT INTO af_resources(id,recording_id,kind) VALUES (?,?,?)", (resource_id, recording_id, kind))
            return resource_id

    def grant_access(
        self, identity: VerifiedIdentity, recording_id: str, recipient_id: str, *,
        permission: str = "read", resource_id: str | None = None, expires_at: int | None = None,
    ) -> str:
        with self._connection(write=True) as db:
            return self._grant_access(db, identity, recording_id, recipient_id,
                                      permission=permission, resource_id=resource_id, expires_at=expires_at)

    def _grant_access(
        self, db: sqlite3.Connection, identity: VerifiedIdentity, recording_id: str, recipient_id: str, *,
        permission: str = "read", resource_id: str | None = None, expires_at: int | None = None,
    ) -> str:
        """One policy, reused inside the caller's existing write transaction."""
        if permission not in {"read", "review"}:
            raise ValueError("Unknown grant permission.")
        if expires_at is not None and (type(expires_at) is not int or expires_at <= int(time.time())):
            raise ValueError("Grant expiry must be a future UTC epoch second.")
        actor = self._actor(db, identity)
        self._owner(db, actor, recording_id)
        recipient = self._active_user(db, recipient_id)
        if recipient_id == actor["id"]:
            raise AccessDenied("Self-assignment is not supported.")
        resource = db.execute("SELECT * FROM af_resources WHERE id=? AND recording_id=?", (resource_id, recording_id)).fetchone()
        if resource_id is not None and resource is None:
            raise AccessDenied("Access denied.")
        if permission == "review" and (
            recipient["role"] != "audio_analyst" or resource is None or resource["kind"] not in {"original_audio", "result"}
        ):
            raise AccessDenied("Review requires an analyst and an explicitly scoped original or result.")
        grant_id = uuid4().hex
        db.execute("INSERT INTO af_grants(id,recording_id,resource_id,grantor_id,recipient_id,permission,status,expires_at,created_at,revoked_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (
            grant_id, recording_id, resource_id, actor["id"], recipient_id,
            permission, "active", expires_at, int(time.time()), None,
        ))
        self._audit(db, actor["id"], "grant.created", grant_id)
        return grant_id

    def revoke_grant(self, identity: VerifiedIdentity, grant_id: str) -> None:
        with self._connection(write=True) as db:
            actor = self._actor(db, identity)
            grant = db.execute("SELECT * FROM af_grants WHERE id=?", (grant_id,)).fetchone()
            if grant is None:
                raise AccessDenied("Access denied.")
            self._owner(db, actor, grant["recording_id"])
            if grant["status"] != "revoked":
                db.execute("UPDATE af_grants SET status='revoked',revoked_at=? WHERE id=?", (int(time.time()), grant_id))
                self._audit(db, actor["id"], "grant.revoked", grant_id)

    def authorize_resource(self, identity: VerifiedIdentity, resource_id: str) -> None:
        """Applies independently to each original/output/visualization/context ID.

        A result-scoped grant never grants sibling audio/visualizations implicitly.
        Downloads reuse the corresponding resource check, never a public file URL.
        """
        with self._connection() as db:
            actor = self._actor(db, identity)
            resource = db.execute(
                "SELECT r.*,o.owner_id FROM af_resources r JOIN af_recordings o ON o.id=r.recording_id WHERE r.id=?",
                (resource_id,),
            ).fetchone()
            if resource is None:
                raise AccessDenied("Access denied.")
            self._active_user(db, resource["owner_id"])
            if actor["id"] == resource["owner_id"]:
                return
            grant = db.execute(
                "SELECT 1 FROM af_grants WHERE recording_id=? AND recipient_id=? AND grantor_id=? "
                "AND status='active' AND permission IN ('read','review') "
                "AND (resource_id IS NULL OR resource_id=?) AND (expires_at IS NULL OR expires_at>?)",
                (resource["recording_id"], actor["id"], resource["owner_id"], resource_id, int(time.time())),
            ).fetchone()
            if grant is None:
                raise AccessDenied("Access denied.")

    def authorize_review(self, identity: VerifiedIdentity, grant_id: str, resource_id: str) -> None:
        """Review-note/decision predicate, NOT review persistence or an API endpoint."""
        with self._connection() as db:
            self._authorize_review(db, identity, grant_id, resource_id)

    def _authorize_review(self, db: sqlite3.Connection, identity: VerifiedIdentity, grant_id: str, resource_id: str) -> None:
        """Reusable predicate inside the caller's write transaction."""
        actor = self._actor(db, identity)
        if actor["role"] != Role.AUDIO_ANALYST.value:
            raise AccessDenied("Access denied.")
        row = db.execute(
            "SELECT o.owner_id,g.grantor_id FROM af_grants g "
            "JOIN af_recordings o ON o.id=g.recording_id "
            "JOIN af_resources r ON r.id=g.resource_id AND r.recording_id=g.recording_id "
            "WHERE g.id=? AND g.resource_id=? AND g.recipient_id=? AND g.permission='review' "
            "AND g.status='active' AND r.kind IN ('original_audio','result') AND (g.expires_at IS NULL OR g.expires_at>?)",
            (grant_id, resource_id, actor["id"], int(time.time())),
        ).fetchone()
        if row is None or row["owner_id"] != row["grantor_id"]:
            raise AccessDenied("Access denied.")
        self._active_user(db, row["owner_id"])
