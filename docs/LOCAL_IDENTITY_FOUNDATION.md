# LOCAL identity foundation — bounded next milestone

## Objective and authorization

1 October 2026: the owner approved the real local Frost core and feedback revision
("looks good. go to next step"), then asked continuation until a working review
is needed. This authorizes the next LOCAL L0 foundation and its profile/core-view
connections, not production or the full L0–L12 programme. Existing approved
`UX_LUNA_HANDOFF.md` handle/public-ID rules remain the design contract.

## Implementation contract

- Extend existing records with nullable public references and user handle fields
  through additive `app/m1/migrations/003_public_identity.sql`, M1 schema3. Keep
  existing UID, PK/FK values, AF policy schema/version, grants/jobs/files/results.
- Missing-only backfill is in the same database transaction. Generate at account/
  entity creation; never rotate existing references on login/restart. Use the M1
  metadata layer; AF authorization decisions remain untouched. Explicit insert
  column lists preserve the standalone AF schema's compatibility.
- Public IDs: USR/REC/JOB/RES/MED/GRT/ASN + ten cryptographic Crockford symbols,
  PREFIX-4-6, unique and immutable through APIs. A result's RES ID matches its
  result resource; an existing review grant gets its own ASN reference, no new
  assignment entity. EXP is reserved for a future real export, not a dummy row.
- Canonical handles: lowercase without @,3–20 ASCII chars, starts letter, ends
  alphanumeric, no consecutive separators; exact approved reserved names. Safe
  adjective/noun assignment, bounded collision retries then two safe suffix chars;
  no email/PII derivation. Automatic assignment counts0; one normalized self-service
  change sets count1/timestamp. Display name remains independently editable.
- Existing PATCH `/api/auth/me` is the sole self-profile mutation; no arbitrary
  target UID, role/count/public-ID setters, public handle lookup or login alias.
  Backend enforces format, uniqueness and remaining change inside BEGIN IMMEDIATE.
- Profile uses approved Frost primitives/layout, initials avatar for now, real
  handle/reference, clear one-change warning/used state. Core shell/greeting/list/
  detail show real available references unobtrusively; internal routes stay stable.
  No preview identity/data imports or invented IDs on an older backend.
- Preserve existing settings/security actions. No fake notification toggle,
  avatar upload, export/delete/unlink completion or sharing-by-handle claim.

## Commands and structure

From implementation root:
Use the existing application/verifier test environment for the combined regression;
the CPU ML environment does not include the Firebase Admin SDK tests.
Use focused migration-only processing regression without model execution.
From frontend: `npm run build`; separately
`npx --no-install vite build --config ux-preview.vite.config.ts`.
Browser evidence will use the existing installed Playwright/Chrome and test-only
fictional SDK/verifier seam with the REAL local API/SQLite/private files. Not live
Firebase/emulator/provider evidence. No new authentication runtime bypass.

Source follows existing parameterized SQLite/explicit transaction patterns;
identity validation/generation stays in a focused M1 module, not an auth/UI shim.
Frontend uses existing LiveAppProvider/API and approved Frost tokens/components.
Task list: `tasks/todo.md`; existing completed prototype plan remains preserved.

## Success criteria and safety

Verify fresh/v1/v2 migration, missing-only stable references, unchanged legacy
row identities/foreign keys and file hashes; valid safe assignment, case-insensitive
collision/race/one-change behavior, malicious profile fields denied, unchanged
owner/unrelated/admin and exact-resource authorization. Focused browser profile
save/reload and title/public-ID search; actual desktop/mobile/Midnight visual review.
Mock error checks identified separately. Both standalone build exit codes recorded.

Always preserve the running manual-review DB/storage/browser at4196/8196. Use a
different ignored persistent LOCAL namespace for the next review; never migrate
production or overwrite an existing local DB. No production/Axora/infrastructure,
Firebase/provider/rule change, ML/model/inference modification, training or T9.
Use raw eligible non-test HLS-CMDS audio if a listening check is needed, not tones.
Next stop: working local profile/identity flow for owner review. Production rollout
and destructive account/data services remain separately gated.

## Completed local execution — 1 October 2026

**LOCAL IDENTITY FOUNDATION COMPLETE — READY FOR OWNER REVIEW. NOT DEPLOYED.**
Core/feedback UI approval is recorded; this new identity/profile slice still needs
hands-on owner review. Backend source: `ebedc053e16b21e39aad9d056d1874c2fae101e1`.
Final interface/evidence SHA is in root `PAUSE_NOTES.md`. Starts: implementation
0735309, documentation376bd2f, root841642a1. Existing branches/PRs #9/#2, owner
ASHRAF-2004; no reset, merge, force push or assistant attribution.

Migration003/version3 adds metadata only. Existing UID/PK/FK, role/grant policy,
resource relationships, provenance and stored audio remain unchanged. Missing-only
public references/handles are transactional and stable after login/reinitialization.
Public references use50 cryptographically random Crockford bits, not truncated
UUIDs. RES matches the existing result resource; ASN represents the existing review
grant, not a duplicate assignment table. EXP remains reserved, without dummy rows.
Strict PATCH `/api/auth/me` accepts display name and optional handle only. Format,
reserved names, uniqueness and one-change count are enforced under BEGIN IMMEDIATE.
Invalid/colliding/second-change requests roll back. Automatic assignment counts0;
display name remains editable. UID/role/count/public-ID client mutations are denied.

Fixture-free `frost/Account.tsx` connects the approved profile/appearance/audio
layout, actual @handle/USR reference, confirmation and used state. The shell/core
views show actual references unobtrusively; real Library search includes REC IDs.
Internal routes and independent media authorization are unchanged. Old API responses
show honest identity-unavailable states. Legacy sharing ID stays in Account details.
No handle lookup/login, avatar upload or simulated export/delete/notification feature.
Existing provider recovery/sign-out/preferences are retained, not newly qualified.

### Persistent local review and preservation

The new visible Chrome/terminal uses127.0.0.1:4197 → API127.0.0.1:8197, under
`implementation/.local/identity-review/`: DB`data/review.sqlite3`, private`private/`,
lock`data/review.sqlite3.worker.lock`. Startup uses the source SQLite backup API in
read-only mode and copies bytes only into a new namespace. Existing target data is
never overwritten. The original4196/8196 session stays running on schema2, unmigrated.
The new schema3 copy preserves4 recordings,10 files,3 jobs/results and6 result-file
links. All10 private artifact hashes match; foreign-key check is clean.

Identity mode is the existing fixed **TEST ONLY** verifier/Firebase SDK stand-in,
fictional Alice/Healthcare Staff. API, SQLite, private files and frozen CPU worker
are real; browser APIs are not mocked. Not live Firebase/emulator. Only fictional
Bob consumes his test change; Alice's owner-review change remains available.
The dedicated browser is required; an unrelated Brave tab will not inherit that
test setup. No real password should be entered. Owner interaction is not automated.

Start/restart: `node frontend/tools/local-identity-review.mjs` from implementation.
Stop only this namespace: same command with `--stop`, or Ctrl+C in the
**STETHOFUSE IDENTITY REVIEW — keep open** terminal. No data cleanup. The original
review launcher is separate and unchanged. New launcher verifies both frozen
hashes, binds loopback, loads one worker and refuses copied unfinished jobs.
Raw listening fixture: `.local/identity-review/raw-hls/M0001.wav`, unchanged eligible
non-test HLS-CMDS Mix/M0001, SHA
`8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616`.
Existing separated outputs are reused, not regenerated. Tiny silence/derived
metadata in isolated HTTP tests exercises policy only, not listening/model quality.

### Checks, visual evidence and review

| Check | Actual result |
|---|---|
| Focused identity + v1 migration, existing CPU environment |19 passed, exit0 |
| Existing app/verifier environment regression |109 passed +26 subtests, exit0 |
| `node tests/frost-identity.mjs`, final v3 |6 groups:5 real browser/API +1 client validation, exit0 |
| `node tests/frost-identity-layout.mjs` |3 real read-only follow-up groups, exit0 |
| `npm run build` |Final separate finite TypeScript/Vite exit0 |
| `npx --no-install vite build --config ux-preview.vite.config.ts` |Separate finite exit0 |
| Launcher syntax / Git whitespace |Exit0 |

Combined pytest used the existing `/tmp/stethofuse-m1-auth-bvIfFV/venv/bin/python`:
`-m pytest -q tests/test_m1_identity.py tests/test_m1_api.py tests/test_access_foundation.py tests/test_m1_processing.py::test_v1_migration_is_transactional_and_preserves_existing_data`.
Python3.14.4; worker remains in the existing torch2.11.0+cpu environment. No install
or upgrade. Initial combined run in ML venv had103 passes/6 missing-SDK failures;
the existing app environment resolved them. Starlette's existing warning is non-failing.

Coverage: stable references/migration rollback, UID authority, format/case collision,
one-change concurrency, actual profile saves/new session, real REC search/deep links,
existing3-source automatic playback, gain100/150/200,1440×900/390×844/1024px,
Frost/Midnight, focus/reduced motion and honest API2 compatibility. Follow-up fixes
unsaved edits across legacy query-section navigation. Existing backend authorization
regression covers anonymous/outsider/Admin denial, exact resources and revocation.

Final ignored screenshots were inspected visually:
`frontend/output/playwright/identity-foundation/v3/` (10 images), plus
`final-layout-v1/` (3). Main examples:01-profile-frost-desktop.png,
02-profile-frost-mobile.png,03-profile-frost-tablet.png,
05-profile-midnight-desktop.png,08-library-real-public-ids.png,
09-one-change-confirmation.png. Follow-up includes mobile Library/detail and old
API2 unavailable profile. Receipt SHA-256:

- v3:37c62f3c41d5804c56dcd0d041747f4c5392b69d90d835be65a5b496a1f7a2f4.
- final-layout-v1:7f9b1732f433b43a25e66f1473e83bfb3037fe9000e12baca15db74853be66a7.

Earlier v1 harness incorrectly sent a profile field to strict onboarding (correct422);
v2 exposed missing safe client409 copy. Onboarding was not broadened; error-code
copy was added and v3 passed. Earlier artifacts are retained, no spent change reset.

Five-axis review: correctness/architecture/security tests pass; section routing
uses an explicit switch; metadata is separate from policy; values are parameterized,
internal allocation identifiers fixed; indexed missing-only work and existing
collection fetches stay bounded. Required findings fixed:409 copy, legacy unsaved
navigation and exclusive reservation of a new snapshot file. No unresolved
Critical/Important finding. Not a complete security/accessibility certification.

Both frozen SHA-256 values reverified unchanged:
`1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658` /
`2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b`.
No model inference/training/T9 experiment, patient audio, production migration or
deployment, auth/provider/rule change, Axora change or review-data deletion.
Pending: avatar backend, handle sharing/login, export/delete/unlink, notifications,
global Insights and genuine owl flight (**ASSET-GATED — NOT IMPLEMENTED**).
STOP for owner review of the working local identity/profile flow.
