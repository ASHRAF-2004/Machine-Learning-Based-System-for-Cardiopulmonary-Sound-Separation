"""Offline preparation tests: stdlib unittest, temporary DBs, fictional identities.

No app.main/ML imports, Firebase SDK, provider calls or legacy DB access.
Run from implementation: python3 -m unittest discover -s tests -p test_access_foundation.py -v
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.access_foundation import (
    AccessDenied, AuthenticationDenied, DevelopmentAccessStore, DisabledVerifier,
    Role, Status, VerifiedIdentity,
)
from app.access_foundation.identity import FirebaseIdentityAdapter


class FakeDirectory:
    """Test-only trusted-provider stand-in. Never installed in an app dependency."""

    def __init__(self, *identities: VerifiedIdentity):
        self.identities = {identity.uid: identity for identity in identities}

    def lookup_existing(self, uid: str) -> VerifiedIdentity:
        if uid not in self.identities:
            raise AuthenticationDenied("Identity could not be verified.")
        return self.identities[uid]


class AccessFoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "isolated-access.sqlite"
        self.store = DevelopmentAccessStore(self.path)
        self.store.initialize()
        self.owner = VerifiedIdentity("fictional-owner", "owner@example.invalid", True)
        self.analyst = VerifiedIdentity("fictional-analyst", "analyst@example.invalid", True)
        self.admin = VerifiedIdentity("fictional-admin", "admin@example.invalid", True)
        self.other = VerifiedIdentity("fictional-other", "other@example.invalid", True)
        self.directory = FakeDirectory(self.owner, self.analyst, self.admin, self.other)
        self.accounts = {i.uid: self.store.register_verified_identity(i) for i in self.directory.identities.values()}
        self.store.bootstrap_first_admin(self.directory, provider_uid=self.admin.uid, confirmed_uid=self.admin.uid)
        self.change(self.analyst, role=Role.AUDIO_ANALYST)
        self.recording = self.store.create_recording(self.owner)
        self.result = self.store.create_resource(self.owner, self.recording, "result")
        self.original = self.store.create_resource(self.owner, self.recording, "original_audio")

    def change(self, target: VerifiedIdentity, **changes):
        user_id = self.accounts[target.uid].id
        return self.store.change_account(self.admin, user_id, confirmed_target_id=user_id, **changes)

    def grant(self, recipient=None, **kwargs):
        return self.store.grant_access(
            self.owner, self.recording, self.accounts[(recipient or self.analyst).uid].id, **kwargs,
        )

    def test_default_registration_never_grants_privileged_role(self):
        self.assertEqual(self.accounts[self.owner.uid].role, Role.HEALTHCARE_STAFF)
        with self.assertRaises(TypeError):
            self.store.register_verified_identity(self.other, role="admin")
        with self.assertRaises(AccessDenied):
            self.store.require_admin(self.owner)

    def test_equal_emails_do_not_merge_provider_uids(self):
        identity = VerifiedIdentity("different-provider-uid", self.owner.email, True)
        account = self.store.register_verified_identity(identity)
        self.assertNotEqual(account.id, self.accounts[self.owner.uid].id)
        self.assertEqual(account.role, Role.HEALTHCARE_STAFF)

    def test_missing_unverified_disabled_and_client_claims_fail_closed(self):
        identities = [
            VerifiedIdentity("absent-uid", "absent@example.invalid", True),
            VerifiedIdentity(self.owner.uid, self.owner.email, False),
            VerifiedIdentity(self.owner.uid, self.owner.email, True, True),
            VerifiedIdentity(self.owner.uid, self.owner.email, "true"),
            {"uid": self.owner.uid, "role": "admin", "email_verified": True},
        ]
        for identity in identities:
            with self.subTest(identity_type=type(identity).__name__), self.assertRaises(PermissionError):
                self.store.authorize_resource(identity, self.original)
        with self.assertRaises(AuthenticationDenied):
            DisabledVerifier().verify("not-a-token")

    def test_owner_can_access_every_resource_kind_but_admin_cannot(self):
        for kind in ("original_audio", "heart_audio", "lung_audio", "waveform", "spectrogram", "context", "result"):
            resource = self.store.create_resource(self.owner, self.recording, kind)
            self.store.authorize_resource(self.owner, resource)
            for outsider in (self.analyst, self.admin, self.other):
                with self.subTest(kind=kind, uid=outsider.uid), self.assertRaises(AccessDenied):
                    self.store.authorize_resource(outsider, resource)

    def test_admin_can_access_own_workspace_without_unrelated_privileges(self):
        recording = self.store.create_recording(self.admin)
        resource = self.store.create_resource(self.admin, recording, "original_audio")
        self.store.authorize_resource(self.admin, resource)
        with self.assertRaises(AccessDenied):
            self.store.authorize_resource(self.owner, resource)

    def test_explicit_scoped_share_does_not_leak_other_results_or_audio(self):
        self.grant(resource_id=self.result)
        self.store.authorize_resource(self.analyst, self.result)
        sibling = self.store.create_resource(self.owner, self.recording, "result")
        for resource in (self.original, sibling, "unknown-id"):
            with self.assertRaises(AccessDenied):
                self.store.authorize_resource(self.analyst, resource)

    def test_recording_share_does_not_grant_owner_mutations_or_resharing(self):
        self.grant()
        self.store.authorize_resource(self.analyst, self.original)
        with self.assertRaises(AccessDenied):
            self.store.require_owner(self.analyst, self.recording)
        with self.assertRaises(AccessDenied):
            self.store.create_resource(self.analyst, self.recording, "result")
        with self.assertRaises(AccessDenied):
            self.store.grant_access(self.analyst, self.recording, self.accounts[self.other.uid].id)

    def test_admin_cannot_self_grant_or_revoke_someone_elses_private_share(self):
        grant = self.grant()
        with self.assertRaises(AccessDenied):
            self.store.grant_access(self.admin, self.recording, self.accounts[self.admin.uid].id)
        with self.assertRaises(AccessDenied):
            self.store.revoke_grant(self.admin, grant)

    def test_cross_recording_resource_grant_is_denied(self):
        recording = self.store.create_recording(self.other)
        resource = self.store.create_resource(self.other, recording, "result")
        with self.assertRaises(AccessDenied):
            self.grant(resource_id=resource)

    def test_review_needs_analyst_active_assignment_and_exact_result(self):
        grant = self.grant(permission="review", resource_id=self.result)
        self.store.authorize_review(self.analyst, grant, self.result)
        for identity in (self.owner, self.admin, self.other):
            with self.assertRaises(AccessDenied):
                self.store.authorize_review(identity, grant, self.result)
        with self.assertRaises(AccessDenied):
            self.store.authorize_review(self.analyst, grant, self.original)
        read_grant = self.grant(resource_id=self.result)
        with self.assertRaises(AccessDenied):
            self.store.authorize_review(self.analyst, read_grant, self.result)

    def test_staff_admin_and_recording_wide_review_assignment_are_denied(self):
        for recipient in (self.owner, self.other, self.admin):
            with self.assertRaises(AccessDenied):
                self.grant(recipient=recipient, permission="review", resource_id=self.result)
        with self.assertRaises(AccessDenied):
            self.grant(permission="review")

    def test_revocation_is_immediate_and_new_assignment_keeps_old_id_revoked(self):
        grant = self.grant(permission="review", resource_id=self.result)
        self.store.revoke_grant(self.owner, grant)
        self.store.revoke_grant(self.owner, grant)  # harmless idempotent retry
        with self.assertRaises(AccessDenied):
            self.store.authorize_resource(self.analyst, self.result)
        with self.assertRaises(AccessDenied):
            self.store.authorize_review(self.analyst, grant, self.result)
        new_grant = self.grant(permission="review", resource_id=self.result)
        self.assertNotEqual(new_grant, grant)
        self.store.authorize_review(self.analyst, new_grant, self.result)
        with self.assertRaises(AccessDenied):
            self.store.authorize_review(self.analyst, grant, self.result)

    def test_expired_share_and_assignment_deny_access(self):
        expiry = int(time.time()) + 60
        grant = self.grant(permission="review", resource_id=self.result, expires_at=expiry)
        with patch("app.access_foundation.store.time.time", return_value=expiry):
            with self.assertRaises(AccessDenied):
                self.store.authorize_resource(self.analyst, self.result)
            with self.assertRaises(AccessDenied):
                self.store.authorize_review(self.analyst, grant, self.result)

    def test_revoking_one_overlapping_grant_preserves_other_explicit_read_access(self):
        review = self.grant(permission="review", resource_id=self.result)
        recording_read = self.grant(permission="read")
        self.store.revoke_grant(self.owner, review)
        self.store.authorize_resource(self.analyst, self.result)
        with self.assertRaises(AccessDenied):
            self.store.authorize_review(self.analyst, review, self.result)
        self.change(self.analyst, role=Role.HEALTHCARE_STAFF)
        self.store.authorize_resource(self.analyst, self.result)
        self.store.revoke_grant(self.owner, recording_read)
        with self.assertRaises(AccessDenied):
            self.store.authorize_resource(self.analyst, self.result)

    def test_local_suspension_applies_to_existing_identity_and_registration(self):
        self.grant()
        self.change(self.analyst, status=Status.SUSPENDED)
        for operation in (
            lambda: self.store.authorize_resource(self.analyst, self.original),
            lambda: self.store.create_recording(self.analyst),
            lambda: self.store.register_verified_identity(self.analyst),
        ):
            with self.assertRaises(AccessDenied):
                operation()

    def test_local_unverified_and_suspended_owner_deny_access(self):
        self.grant()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE af_users SET email_verified=0 WHERE provider_uid=?", (self.analyst.uid,))
        with self.assertRaises(AccessDenied):
            self.store.authorize_resource(self.analyst, self.original)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE af_users SET email_verified=1 WHERE provider_uid=?", (self.analyst.uid,))
        self.change(self.owner, status=Status.DISABLED)
        with self.assertRaises(AccessDenied):
            self.store.authorize_resource(self.analyst, self.original)

    def test_role_change_revokes_review_permission_without_stale_role_cache(self):
        grant = self.grant(permission="review", resource_id=self.result)
        self.change(self.analyst, role=Role.HEALTHCARE_STAFF)
        with self.assertRaises(AccessDenied):
            self.store.authorize_review(self.analyst, grant, self.result)
        # Review permission includes explicit result-read authority until revocation.
        self.store.authorize_resource(self.analyst, self.result)

    def test_last_admin_demotion_and_suspension_are_denied(self):
        for change in ({"role": Role.HEALTHCARE_STAFF}, {"status": Status.SUSPENDED}, {"status": Status.DISABLED}):
            with self.assertRaises(AccessDenied):
                self.change(self.admin, **change)
        self.store.require_admin(self.admin)

    def test_two_admins_can_change_one_but_confirmation_is_required(self):
        self.change(self.other, role=Role.ADMIN)
        target = self.accounts[self.other.uid].id
        with self.assertRaises(AccessDenied):
            self.store.change_account(self.admin, target, confirmed_target_id="different", role=Role.HEALTHCARE_STAFF)
        self.change(self.other, role=Role.HEALTHCARE_STAFF)
        with self.assertRaises(AccessDenied):
            self.store.require_admin(self.other)

    def test_non_admin_role_changes_and_unknown_values_are_denied(self):
        target = self.accounts[self.other.uid].id
        with self.assertRaises(AccessDenied):
            self.store.change_account(self.owner, target, confirmed_target_id=target, role=Role.ADMIN)
        with self.assertRaises(ValueError):
            self.store.change_account(self.admin, target, confirmed_target_id=target, role="super_admin")

    def test_concurrent_admin_demotions_leave_one_active_admin(self):
        self.change(self.other, role=Role.ADMIN)
        barrier = threading.Barrier(2)

        def demote(identity):
            store = DevelopmentAccessStore(self.path)
            target = self.accounts[identity.uid].id
            barrier.wait(timeout=5)
            try:
                store.change_account(identity, target, confirmed_target_id=target, role=Role.HEALTHCARE_STAFF)
                return "changed"
            except AccessDenied:
                return "denied"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(demote, (self.admin, self.other)))
        self.assertCountEqual(outcomes, ["changed", "denied"])
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM af_users WHERE role='admin' AND status='active'").fetchone()[0], 1)

    def test_bootstrap_is_idempotent_and_cannot_bootstrap_a_second_uid(self):
        self.assertFalse(self.store.bootstrap_first_admin(self.directory, provider_uid=self.admin.uid, confirmed_uid=self.admin.uid))
        with self.assertRaises(AccessDenied):
            self.store.bootstrap_first_admin(self.directory, provider_uid=self.other.uid, confirmed_uid=self.other.uid)
        with self.assertRaises(AccessDenied):
            self.store.bootstrap_first_admin(self.directory, provider_uid=self.admin.uid, confirmed_uid="wrong")

    def test_bootstrap_requires_provider_verified_existing_and_local_user(self):
        cases = [
            (FakeDirectory(), "missing"),
            (FakeDirectory(VerifiedIdentity("unverified", "x@example.invalid", False)), "unverified"),
            (FakeDirectory(VerifiedIdentity("disabled", "x@example.invalid", True, True)), "disabled"),
            (FakeDirectory(VerifiedIdentity("no-local", "x@example.invalid", True)), "no-local"),
        ]
        for directory, uid in cases:
            with self.assertRaises(PermissionError):
                self.store.bootstrap_first_admin(directory, provider_uid=uid, confirmed_uid=uid)

    def test_consumed_bootstrap_cannot_restore_demoted_first_admin(self):
        self.change(self.other, role=Role.ADMIN)
        self.change(self.admin, role=Role.HEALTHCARE_STAFF)
        with self.assertRaises(AccessDenied):
            self.store.bootstrap_first_admin(self.directory, provider_uid=self.admin.uid, confirmed_uid=self.admin.uid)

    def test_atomic_bootstrap_race_has_exactly_one_winner(self):
        path = Path(self.temp.name) / "bootstrap-race.sqlite"
        store = DevelopmentAccessStore(path)
        store.initialize()
        store.register_verified_identity(self.owner)
        store.register_verified_identity(self.other)
        barrier = threading.Barrier(2)

        def bootstrap(identity):
            barrier.wait(timeout=5)
            try:
                return DevelopmentAccessStore(path).bootstrap_first_admin(
                    self.directory, provider_uid=identity.uid, confirmed_uid=identity.uid,
                )
            except AccessDenied:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(bootstrap, (self.owner, self.other))), [True, False])
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM af_bootstrap").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM af_audit WHERE action='admin.bootstrap'").fetchone()[0], 1)

    def test_audit_failure_rolls_back_account_change(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER deny_audit BEFORE INSERT ON af_audit BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.change(self.other, role=Role.ADMIN)
        self.assertEqual(self.store.resolve_account(self.other).role, Role.HEALTHCARE_STAFF)

    def test_bootstrap_audit_failure_rolls_back_role_and_consumption_marker(self):
        path = Path(self.temp.name) / "bootstrap-rollback.sqlite"
        store = DevelopmentAccessStore(path)
        store.initialize()
        store.register_verified_identity(self.owner)
        with sqlite3.connect(path) as db:
            db.execute("CREATE TRIGGER deny_audit BEFORE INSERT ON af_audit BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            store.bootstrap_first_admin(self.directory, provider_uid=self.owner.uid, confirmed_uid=self.owner.uid)
        self.assertEqual(store.resolve_account(self.owner).role, Role.HEALTHCARE_STAFF)
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM af_bootstrap").fetchone()[0], 0)

    def test_bootstrap_refuses_existing_admin_even_without_bootstrap_marker(self):
        path = Path(self.temp.name) / "preexisting-admin.sqlite"
        store = DevelopmentAccessStore(path)
        store.initialize()
        store.register_verified_identity(self.owner)
        store.register_verified_identity(self.other)
        # Deliberately construct a migrated/externally managed fixture, not a public API.
        with sqlite3.connect(path) as db:
            db.execute("UPDATE af_users SET role='admin' WHERE provider_uid=?", (self.other.uid,))
        with self.assertRaises(AccessDenied):
            store.bootstrap_first_admin(self.directory, provider_uid=self.owner.uid, confirmed_uid=self.owner.uid)

    def test_no_implicit_database_creation_for_runtime_use(self):
        absent = Path(self.temp.name) / "never-initialized.sqlite"
        with self.assertRaises(sqlite3.OperationalError):
            DevelopmentAccessStore(absent).resolve_account(self.owner)
        self.assertFalse(absent.exists())

    def test_initializer_is_idempotent_and_refuses_legacy_database(self):
        self.store.initialize()
        legacy = Path(self.temp.name) / "fictional-legacy.sqlite"
        with sqlite3.connect(legacy) as db:
            db.execute("CREATE TABLE uploaded_audio (id INTEGER PRIMARY KEY)")
        with self.assertRaises(ValueError):
            DevelopmentAccessStore(legacy).initialize()
        with sqlite3.connect(legacy) as db:
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [("uploaded_audio",)])

    def test_safe_audit_schema_does_not_contain_secrets_or_content(self):
        with sqlite3.connect(self.path) as db:
            columns = [r[1] for r in db.execute("PRAGMA table_info(af_audit)")]
            self.assertEqual(columns, ["id", "actor_id", "action", "target_id", "created_at"])
            user_columns = [r[1] for r in db.execute("PRAGMA table_info(af_users)")]
            self.assertFalse(any("password" in c or "token" in c for c in user_columns))


class FirebaseSeamTests(unittest.TestCase):
    """Verifies SDK call contract using mocks; NOT a live Firebase integration test."""

    def setUp(self):
        self.app = SimpleNamespace(project_id="fictional-project")
        self.user = SimpleNamespace(uid="fictional-uid", email="x@example.invalid", email_verified=True, disabled=False)
        self.auth = SimpleNamespace(
            get_user=Mock(return_value=self.user),
            verify_id_token=Mock(return_value={"uid": self.user.uid, "email_verified": True, "role": "admin"}),
        )
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.modules = patch.dict("sys.modules", {"firebase_admin": SimpleNamespace(auth=self.auth)})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def adapter(self):
        return FirebaseIdentityAdapter(app=self.app, expected_project_id="fictional-project")

    def test_calls_official_verifier_with_revocation_check_and_ignores_role(self):
        identity = self.adapter().verify("fictional-id-token")
        self.auth.verify_id_token.assert_called_once_with(
            "fictional-id-token", app=self.app, check_revoked=True, clock_skew_seconds=0,
        )
        self.auth.get_user.assert_called_once_with(self.user.uid, app=self.app)
        self.assertEqual(identity.uid, self.user.uid)
        self.assertFalse(hasattr(identity, "role"))

    def test_provider_errors_fail_closed_without_secret_echo(self):
        self.auth.verify_id_token.side_effect = RuntimeError("secret-example-do-not-echo")
        with self.assertRaises(AuthenticationDenied) as error:
            self.adapter().verify("fictional-id-token")
        self.assertNotIn("secret-example", str(error.exception))

    def test_current_disabled_or_unverified_provider_record_is_denied(self):
        for field in ("disabled", "email_verified"):
            self.user.disabled = field == "disabled"
            self.user.email_verified = field != "email_verified"
            with self.assertRaises(AuthenticationDenied):
                self.adapter().verify("fictional-id-token")

    def test_unverified_token_and_provider_uid_mismatch_are_denied(self):
        self.auth.verify_id_token.return_value = {"uid": self.user.uid, "email_verified": False}
        with self.assertRaises(AuthenticationDenied):
            self.adapter().verify("fictional-id-token")
        self.auth.verify_id_token.return_value = {"uid": "other-uid", "email_verified": True}
        with self.assertRaises(AuthenticationDenied):
            self.adapter().verify("fictional-id-token")

    def test_project_mismatch_and_emulator_are_denied(self):
        with self.assertRaises(AuthenticationDenied):
            FirebaseIdentityAdapter(app=self.app, expected_project_id="another-project")
        with patch.dict(os.environ, {"FIREBASE_AUTH_EMULATOR_HOST": "127.0.0.1:9099"}):
            with self.assertRaises(AuthenticationDenied):
                self.adapter()


if __name__ == "__main__":
    unittest.main()
