# Account/ownership migration proposal — not executed

This document proposes a staged migration. It is **not** SQL to run against the current
database. The executable `app/access_foundation/schema.sql` is exclusively for an isolated
development harness. No current recordings, jobs, results or model rows were changed.

## Reconcile existing data first

The current SQLite/SQLAlchemy model has `uploaded_audio`, `model`, `separation_job`,
`separation_result`, `evaluation_metric`, and `system_log`. `uploaded_audio` has no owner.
Job/result IDs are related, but none implies a user identity. The report's original data
must not be silently assigned to the first account, first administrator, or current browser.

1. Inventory schema/version, legacy callers, storage paths, backups and real data separately
   from fixtures. Verify backup and restore on a copy before choosing a production migration.
2. Add stable internal users with unique provider UID, required role/status constraints,
   provider verification metadata and timestamps. No password/hash/reset-code columns.
   Use provider-authorized linking; do not deduplicate by matching email strings.
3. Add ownership as a initially-null foreign key on existing audio rows using reviewed
   versioned migration tooling. New authenticated uploads derive owner from the verified
   server identity and must always populate it. Preserve original file/run lineage.
4. Quarantine unowned legacy rows from account-scoped responses until an operator-approved,
   evidenced mapping or explicit research-fixture policy exists. Never infer ownership.
5. Resolve every job/result/audio/visualization identifier through its recording ownership.
   Add grants and assignments with checked recording/result scope, owner/grantor/recipient,
   permission, expiry/status/revocation timestamps. Maintain historical immutable assignment
   identity; new recipients get new assignments, not transferred notes or overwritten history.
6. Review records link to exact assignment/reviewer/result. Persist notes/decisions only after
   current analyst-role and active-assignment validation in the same trusted transaction.
7. Add safe operational audits with an explicit allowlisted payload contract and retention
   decision. Keep access/audit logs separate from private clinical notes and secrets.

## Close all access paths together

Implement future same-origin `/api` routes behind centralized verified-identity dependencies
and object checks. Do not add one protected route while leaving an equivalent old download
or static URL public. Inventory all original/output/waveform/spectrogram/download/context/
review paths, including range requests and historical runs.

The inspected `/history`, `/result/{job_id}`, `/download/{job_id}/heart`,
`/download/{job_id}/lung`, and `/visualizations` currently lack this new account boundary.
Define a caller migration/compatibility strategy before retiring or changing them. The
original request explicitly preserves existing routes in this preparation phase.

Move private outputs outside public asset/static directories only through an approved
file migration. Use opaque IDs resolved by server metadata, not user-supplied paths.
Validate real paths beneath an allowlisted private root and deliver files through checked
handlers. File location alone is not authorization. Define deletion/retention, backup,
restore, orphan cleanup and capacity behavior before claiming persistent private storage.

## Roles and first administrator

Keep initial bootstrap outside public registration and outside the HTTP API. The trusted
operator setup must confirm the existing provider UID, verified/enabled state and local
default account before the one-time transaction. Do not use first-signup escalation.
All later role/status changes and account deletion must use the same atomic invariant that
preserves at least one active local admin. On a different production database, replace
SQLite's `BEGIN IMMEDIATE` with the appropriate transaction/locking strategy and prove the
concurrency invariant there. Read-then-write in separate transactions is insufficient.

Administrative reassignment requires a separately approved owner-authorized workflow.
It must not let an admin assign private recordings to themselves or bypass content checks.
Until that contract is implemented and tested, owner-only grant/revoke is the safe limit.

Grants are additive. Specify single-grant revocation separately from effective-access
removal; a "revoke all access" action must revoke all relevant overlapping grants atomically.
Role demotion denies analyst review writes, not independent explicit read authority. Define
whether the read portion of an existing review grant persists (as in this scaffold) or is
explicitly revoked by the future production role-change transaction.

Agree and test frontend/backend role and account-state mapping before wiring: demo `staff`
and `analyst` map to `healthcare_staff` and `audio_analyst`; `admin` is unchanged. Backend
`suspended` and frontend `pending` have no direct counterpart. Model verification/onboarding
separately, represent suspension explicitly, and never treat an unknown/pending value as an
active verified account.

## Integration approval gates

- Approved provider project, credentials deployment, SDK dependency pin and account linking.
- Authorized test users and genuine token signature/audience/issuer/expiry/revocation/
  provider-disabled checks, verified email policy, outage handling and rate limiting.
- Explicit session/reauthentication/recovery/verification flows; no fake success or local
  password service. If cookies are selected, include CSRF and deployment-appropriate flags.
- Dry-run schema/backfill/file migration and recovery on copied data; no lost original runs.
- Route-level negative tests for every content type, user-ID tampering, owner-ID injection,
  stale roles, disabled/unverified users, revoked grants and concurrent admin changes.
- Protected-file response policy and concurrency checks covering check/use races and streams.
- Response shaping for account directory vs private metadata, logs without secrets, and
  edge deployment hardening. No clinical, zero-knowledge or end-to-end-encryption claim.

Only after these gates should the frontend stop using clearly labelled local fixtures.
This preparation does not alter its demo boundary or constitute full integration.
