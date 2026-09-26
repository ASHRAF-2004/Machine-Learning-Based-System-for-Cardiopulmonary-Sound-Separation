# Access foundation — historical preparation design

**M1 update, 26 September 2026:** the current `app/main.py` now mounts the protected
`app/m1/` API using these primitives. Legacy unowned content routes are retired, not
left publicly available. Read [M1 route audit](M1_ROUTE_AUDIT.md),
[API contract](M1_API_CONTRACT.md) and [security boundaries](M1_SECURITY_BOUNDARIES.md)
for the current behavior and test limits. Official Firebase SDKs/providers and restricted
keyless ADC are configured; the intended primary admin has now been verified and bootstrapped
locally. Full real-provider workflow acceptance remains open. See
[current account provisioning](ROLES_AND_ACCOUNT_PROVISIONING.md). M1 also permits an
exact original-audio review assignment, not only an exact result assignment.

The original preparation record below is retained to explain the starting state;
its unwired-route/dependency statements are **historical**, not current run instructions.

Status: isolated development scaffold, **not integrated with the legacy application**.

`app/access_foundation/` is a stdlib-only authorization and SQLite migration harness.
It adds no FastAPI routes/dependencies, changes no existing configuration, loads no
credentials on import, and stores no passwords or password hashes. It neither
initializes Firebase nor connects to any database until an explicit method is called.

## What is and is not protected

The new primitives require a trusted verified identity and freshly read local active,
verified account. Public-onboarding logic always creates `healthcare_staff`; it has
no role parameter. `audio_analyst` and `admin` are assigned by an authorized admin.
The staff workflow label does not verify professional licensure or authorize clinical use.

| Operation | Foundation policy |
| --- | --- |
| Own recording, files, results, context | All three roles, active and verified |
| Other user's private resource | An active, unexpired, owner-issued grant matching the recording and optional exact resource |
| Edit recording / issue or revoke shares | Owner only; a share never transfers ownership |
| Analyst review notes / decision | Audio analyst plus an active review assignment for that exact result |
| User role/status changes | Active verified admin, explicit target confirmation, atomic last-active-admin guard |
| Admin private-file access | No implicit permission; same owner/grant checks |
| First admin | Trusted setup only, confirmed existing verified provider UID and pre-existing local account |

`require_admin()` is a predicate for future user-management/safe-operational-metadata
handlers. It is not a license to return private data. No global directory, administrative
assignment/reassignment, review persistence or private-file transport is implemented here.
The conservative preparation policy allows only owners to issue/revoke access; a later
operational assignment workflow must explicitly preserve owner authorization and history.

All reads resolve the actor from stable provider UID, not email or a client role. Equal
email strings do not link accounts. ID-token custom role claims are not accepted as local
workflow authority. Grant recipient, recording/resource association and current account
state are checked in the database; arbitrary request dictionaries are not principals.

`authorize_resource()` is applied separately to original audio, heart/lung output,
waveform, spectrogram, context and result IDs. Download permission uses the corresponding
resource check. Result-scoped access does not automatically grant access to sibling
resources; integration must define an explicit bundle or issue individual grants.
`authorize_review()` checks assignment ID, recipient, role, result ID, expiry and status.
Grants are additive: revoking one ID removes only that grant's authority. A recipient may
still pass a resource check through another active explicit grant, including an overlapping
recording-wide grant. A future UI action labelled "revoke all access" must atomically revoke
all relevant grants for the recipient and intended scope; calling `revoke_grant()` once is
not that operation. Revocation cannot recall already-downloaded data. New grants receive
new IDs; old revoked IDs are never restored. Owner or recipient suspension denies access.

Role demotion from analyst denies review writes immediately but does not silently revoke
explicit read grants. In this scaffold, an active review grant also grants read access to
its exact result; that read authority remains after demotion until revoked or expired.
Any different production policy requires an explicit, tested role-change/grant contract.

Before frontend integration, define an explicit role/status mapping: current demo roles
`staff` / `analyst` / `admin` correspond to backend `healthcare_staff` / `audio_analyst` /
`admin`. Both have `active` and `disabled`, but backend `suspended` has no current frontend
status, and frontend `pending` has no backend status. Do not map `pending` to active or
treat it as provider verification. Specify separate verification/onboarding state and a
UI representation for suspension; reject unknown values rather than granting defaults.

**These checks are not wired into `app/main.py` or any existing router.** Existing
`/upload`, `/separate/{audio_id}`, `/models`, `/history`, `/result/{job_id}`,
`/download/{job_id}/heart`, `/download/{job_id}/lung` and the `/visualizations` static
mount retain their existing behavior. In particular, the inspected history, result,
download and static visualization paths have no account-scoped enforcement from this
module. Do not expose the legacy application to untrusted users or place private clinical
data in it on the assumption this scaffold secures it. Existing ML, storage, database,
routes and frontend were intentionally left unchanged.

## Identity boundary

The default `DisabledVerifier` rejects every request. `VerifiedIdentity` is an internal
adapter result, not a request schema. Never instantiate it from browser JSON, a supplied
UID/email/role, an unverified JWT payload, or an HTTP header claiming verified status.
Tests inject fictional identities at this trusted seam only.

The optional, unwired `FirebaseIdentityAdapter` requires an explicitly initialized app
whose project ID matches the expected project. It delegates token validation to the
official Admin SDK and checks the current provider user. It rejects emulator configuration,
unverified or disabled users, invalid/revoked tokens and provider errors. It does not
implement JWT cryptography or fall back to development identities. Roles come from the
local store. Production tenant support is not configured or claimed.

The adapter uses the documented `verify_id_token(..., app=app, check_revoked=True,
clock_skew_seconds=0)` and `get_user(uid, app=app)` interfaces. The SDK validates signature,
expiry and project; revocation checking also checks provider disablement. It is for client
ID tokens, not custom tokens. See the official [token verification guide](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
and [Python Admin auth reference](https://firebase.google.com/docs/reference/admin/python/firebase_admin.auth).

No Firebase SDK was installed, initialized or exercised against a real provider for this
work. Its optional dependency must be selected/pinned and approved in a later integration
task. Current adapter tests use mocks and prove the call contract, not live integration.
Credentials must remain outside source control and logs. Never return provider exception
details, tokens, passwords, reset links or action codes to application responses/audits.

## Isolated development database

`DevelopmentAccessStore` requires an explicit path; it never imports the legacy DB
configuration or infers `database/cardiopulmonary.db`. `initialize()` creates the namespaced
`af_*` schema only in an empty database, or checks the exact development schema/version.
It refuses a database with legacy/unrelated tables. Runtime connections use SQLite
`mode=rw`, so a typo does not silently create a new store. Import and construction do not
open a file. Use a restricted local directory; do not commit DB files, real email addresses,
UIDs, recordings or credentials. The harness is not encrypted and is not a production
migration tool. No private file content/path is stored in its resource fixtures.

Example of **offline fictional preparation**, from `implementation/`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from app.access_foundation import DevelopmentAccessStore, VerifiedIdentity

with TemporaryDirectory() as directory:
    store = DevelopmentAccessStore(Path(directory) / "fictional-access.sqlite")
    store.initialize()
    # TEST/LOCAL HARNESS ONLY. A real request must use the configured verifier.
    identity = VerifiedIdentity("fictional-uid", "person@example.invalid", True)
    account = store.register_verified_identity(identity)
    assert account.role.value == "healthcare_staff"
```

All state-changing operations re-resolve authority within `BEGIN IMMEDIATE`. The lock
serializes concurrent writers, including the last-admin count and role/status update.
The audit insertion is part of that transaction; an audit write failure rolls back the
change. Bootstrap similarly commits its role change, permanent singleton marker and safe
audit event together. Audit columns hold internal IDs/action/timestamp only, without free-
text payloads. This local table is not tamper-proof or an immutable production audit log;
denied-operation telemetry is a future integration concern.

Last-admin protection covers active, locally verified administrators in this trusted store.
It cannot prevent Firebase/infra operators deleting or disabling accounts, manual database
edits, or external changes to provider verification. Provider state and SQLite do not form
one distributed transaction. Start with the one approved primary administrator; consider a
verified backup only after explicit approval, never by automatic creation. Design an explicit
operator recovery procedure; do not reopen bootstrap automatically after provider failure.
No delete-account primitive is supplied. Future deletion/verification/status paths must
share the same invariant, not bypass it through generic ORM writes.

`require_owner()` / `authorize_resource()` / `authorize_review()` are check-only predicates,
not a transaction that persists a later caller mutation. Future review writes and file-open
operations must authorize at the operation boundary with a consistent transaction/stream
policy. A successful check is not a cacheable indefinite capability. A grant revoked during
an already-authorized stream cannot retroactively recall bytes already sent.

## Trusted first-admin setup contract

Bootstrap is deliberately an explicit service operation, **not** first-signup behavior,
an HTTP endpoint, a public role picker, an email allowlist or an automatically run command.
No live bootstrap CLI is provided in this preparation task.

1. An operator approves the intended provider project and existing UID out of band.
2. The real provider lookup must confirm that exact UID exists, is enabled and has verified
   email. No UID is looked up by email, and no account is created by bootstrap.
3. A verified onboarding step must already have created the local default-staff record.
4. Trusted server setup calls `bootstrap_first_admin(directory, provider_uid=uid,
   confirmed_uid=uid)`, with the explicit UID confirmation coming from the operator.
5. Exactly one initial admin is promoted. A retry of the same unchanged active admin returns
   `False` without another audit event. A different UID, a consumed marker with later
   demotion, missing user, unverified/disabled account, or pre-existing admin is refused.
6. Further administrator assignment uses authenticated account management with confirmation.

The identity directory and database file are trusted server dependencies; never let an
HTTP request choose either or inject its own identity adapter. Merely exposing two equal
client UID fields is **not** trusted bootstrap authorization.

## Focused checks and dependencies

From `implementation/`:

```sh
python3 -m unittest discover -s tests -p test_access_foundation.py -v
```

This suite uses only the Python standard library and temporary fictional databases.
It imports neither FastAPI/SQLAlchemy/ML nor the legacy application. It can also run with
the existing pytest dependency: `python3 -m pytest tests/test_access_foundation.py -q`.
No dependency install is necessary for the offline checks.

Coverage includes default role, UID isolation, verified/active checks, role boundaries,
resource ownership, cross-resource/cross-recording denial, revocation/expiry, exact review
assignments, audit rollback, confirmed/bootstrap idempotency, parallel bootstrap and parallel
last-admin demotion. Provider-seam tests check the official SDK call flags and fail-closed
errors with mocks. They are not live authentication, endpoint security, or full ML tests.

Next integration work is proposed separately in [ACCESS_FOUNDATION_MIGRATION.md](ACCESS_FOUNDATION_MIGRATION.md).
