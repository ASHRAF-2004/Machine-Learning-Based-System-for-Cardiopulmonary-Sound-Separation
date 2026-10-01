# Local owner feedback: concise details and handle sharing

1 October 2026. The owner explicitly requested two refinements to the working
Frost interface: key recording facts first with **See more / See less**, and
sharing through an exact **@handle**, not an application identifier. Approved
visual direction and all existing authorization rules remain normative.

## Contract before implementation

| Slice | Existing contract | Minimal adapter |
|---|---|---|
| Recording details | Authorized recording/job/result DTOs and unchanged provenance | Compact facts; optional full references/provenance with accessible disclosure |
| Find recipient | Schema3 canonical unique handle + existing owner predicate | Authenticated owner-only, exact-match lookup for this recording; name/handle/public reference only |
| Share | Existing owner-only grant, read/review and exact-resource scope | Confirm recipient public reference and current handle in the grant transaction; reuse foundation grant validation |
| Existing grants | Owner-only grant list and existing revoke endpoints | Real name/@handle; meaningful resource labels; compact active-first list with disclosure |

No new schema, public directory, anonymous lookup, prefix search, handle login,
role/ownership override, sibling authorization, fake recipient or frontend grant
authority. Lookup is explicit, not keystroke autocomplete, and bounded per owner
using safe audit events (10/minute, 100/hour, across recordings/restarts). Unknown,
inactive and self recipients share the same unavailable response. Confirmation
must prevent a changed/reassigned handle from granting a different account.
Legacy authenticated recipient-ID requests stay compatible; the normal UI no
longer asks users to enter those identifiers.

## Implementation / verification plan

1. Extract concise technical details from RecordingDetail; preserve every original
   provenance value under See more, with keyboard and mobile/Midnight checks.
2. Add exact recipient resolver and handle grant adapter; retain one shared grant
   policy implementation. Test owner/anonymous/nonowner/Admin, wrong confirmation,
   inactive recipients, bounds, exact scope and revocation in isolated SQLite.
3. Connect approved sharing components through the existing authenticated client;
   abort obsolete lookups and reset confirmation on input/session changes.
4. Real local browser share/revoke checks on a separate copied test namespace;
   retain the owner's existing review data/window. Run affected tests only and
   separate finite normal/preview builds, then hand over the local refinement.

Commands (implementation root unless noted):

- `/tmp/stethofuse-m1-auth-bvIfFV/venv/bin/python -m pytest -q tests/test_m1_sharing.py tests/test_m1_api.py tests/test_access_foundation.py`
- Frontend: `node tests/frost-sharing.mjs`
- Frontend normal build: `npm run build`
- Frontend isolated preview build: `npx --no-install vite build --config ux-preview.vite.config.ts`

Source follows existing FastAPI/M1Store, React state and approved Frost tokens.
No dependencies, second auth/session layer or processing pipeline. No production,
Firebase account/provider changes, training/inference changes or T9 access.
Existing eligible raw non-test HLS artifacts are reused; no fabricated listening
fixtures. Review data is retained. Owl flight and account-data services stay gated.

## Execution evidence

**IMPLEMENTED / TESTED LOCALLY — READY FOR OWNER REVIEW. NOT DEPLOYED.**
Subsequent owner feedback: **APPROVED LOCALLY** — “ok good next”, 1 October 2026.
The next bounded Shared & assigned slice is recorded in `LOCAL_SHARED_REVIEWS.md`;
this approval does not authorize production deployment or destructive data services.

Starts: implementation `74142e966d8da0f576c6cebe37ecd854f2d04abc`;
documentation `ea7f58588da84ee092856c5209f8b089fba9fec0`;
root `c2a913ee95d38797e59a3e475332af8d89089611`.
Backend commit: `5b819c57e95e16b637c5177d4344e8578cfaf5d8`.

`frost/TechnicalDetails.tsx` shows applicable key facts in a compact 3-column
desktop / 2-column mobile summary. Internal identifiers, full environment/hashes
and every original provenance entry remain under keyboard-operable See more /
See less. Missing facts are omitted, not zero-filled. Recording/result deep links
and all stored receipts are unchanged; only their presentation changes.

`frost/Sharing.tsx` replaces the recipient-ID form with real exact-handle Find
person → name/@handle confirmation → explicit permission/resource → Share access.
Recipient name/handle/public reference come from the indexed backend, never a
demo fallback. The public reference is confirmed again alongside the current
handle inside the same write transaction as the original grant policy. Whole
recording access remains an explicit option; narrow Heart access is the ready
recording default. Review still requires an analyst and exact original/result.
Only 3 active permissions appear initially; inactive history/additional permissions
are behind See more. With none active, the primary state correctly says private.
Revoke / Revoke all access retain existing endpoints, confirmation and semantics.

HTTP: POST `/api/recordings/{id}/sharing-recipient`; existing POST grants now
accepts either legacy `recipient_id`, or `recipient_handle` + confirmed
`recipient_public_id`, never both. GET grants adds only name/handle/public
reference using one join. No emails/provider UIDs in recipient lookup, no list,
prefix or anonymous search. Roles, verification, ownership, exact resources,
expiry and audit remain backend-authoritative. No schema/dependency change.

| Verification | Actual result |
|---|---|
| Focused sharing + existing API/AF | 99 passed + 26 subtests; exit 0 |
| Existing identity regression | 18 passed; exit 0 |
| Real-local browser/API checks | 4 real groups + 1 authorized-response transport-delay check; exit 0 |
| Read-only final history/layout | 2 groups; exit 0 |
| Normal app `npm run build` | Standalone exit 0 |
| Isolated preview Vite build | Separate finite command; exit 0 |

Tests cover exact/case-normalized lookup, uniform unavailable/self/inactive
response, owner-only/anonymous/Admin denials, durable lookup limits, strict bodies,
renamed/reassigned handle confirmation, analyst review/sibling restrictions and
revocation. Actual private raw HLS output plays under a Heart-only grant; Original,
Lung and result metadata return 403. Real revocation clears subsequent access in
the recipient view. All four temporary test grants per browser run were revoked;
their audit/history is preserved, not deleted. Owner/recipient profiles were not
renamed/reset. No model accuracy score or new inference result was generated.

Seven functional screenshots: ignored `frontend/output/playwright/handle-sharing/v5/`.
Seven read-only final screenshots: `handle-sharing/final-layout-v2/`, same parent.
Desktop 1440×900, mobile 390×844, tablet 820×1000, Frost/Midnight visually inspected.
Native keyboard disclosure/focus, sensible source controls and no horizontal
overflow/page exceptions. Obsolete recipient lookup is cancelled on input change;
route/session cleanup uses the existing authenticated client and component lifecycle.
The delay check reuses an actual authorized response, not simulated permissions.

SHA-256 receipts: functional v5
`0054d1b2a64255f042ed85f1108b87c7cbcfbb363c9eeb99164ac7a355d46e20`;
final read-only layout
`60b346dd42f11f63732fcfd28e4a996e478b28f0114c6bf413047f06f60bb049`.
The latter receipt records checks, not image bytes. Key image SHA-256 values:
final `02-details-desktop.png`
`ab1a48657d9fa86ead97bffeb10f3907c453e9c841c61b98b8ede7869ed3850c`;
v5 `02-handle-match-desktop.png`
`0d8b06db9a7cbb1790bd759426587f9ce72988c5f124c26460a81be7ffb819d7`.

Earlier evidence remains in v1–v4: v1 had an incorrectly nested test locator;
v2 exposed a real accessible-name issue in the new lookup field, fixed by a
separate label/id; v3 had an asynchronous list assertion; v4 expected the wrong
revoked-media copy. Harness timing/history selectors were corrected, not backend
permissions or acceptance gates. Final visual pass moved inactive grants behind
disclosure and framed captures below the sticky header. Existing Starlette test
deprecation/npm update notices are harmless; no dependencies were changed.

Five-axis review: policy validation is shared, not copied; parameterized exact
lookup and confirmed immutable recipient reference fail closed; safe audited
limits survive restart; grant-list metadata is joined once, not N+1. Components
reuse approved Frost tokens and existing session/API ownership. Obsolete recipient
confirmation is cleared on edit/unmount. No unresolved Critical/Important findings.

## Available hands-on local review

Visible **STETHOFUSE SHARING REVIEW — keep open** terminal and dedicated headed
Chrome; 127.0.0.1:4198 → real local API 8198. The existing 4196/4197 sessions were
not stopped, navigated or overwritten. New ignored `.local/handle-sharing-review/`
is a read-only-source copy of the current identity review and private files.
Both copies retain 4 recordings, 10 valid hashed files, 3 jobs/results, no unfinished
job or foreign-key error. The new namespace reuses the same frozen worker (one
per isolated namespace); startup hash checks/load succeeded in 0.292s, no jobs ran.
Identity remains the established fictional fixed verifier/SDK, not live Firebase
or emulator. Never enter real credentials. Recording/media/grants/database are real.

Start/restart from implementation:
`node frontend/tools/local-identity-review.mjs --sharing-review`.
Stop only this namespace: add `--stop`, or Ctrl+C in its terminal. PID/start-time
guards remain; all review data is retained. Original review namespaces are separate.
Use Profile & settings for real local handles; fictional recipient is @review.owl27.
The owner-chosen local @dragonfighter is preserved; self-sharing is intentionally
not supported. No production accounts were searched or changed.

Frozen checkpoint/spec SHA reverified unchanged:
1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658 /
2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b.
No production/Axora/provider/rule/data migration, ML training/tuning/T9 access,
playback graph/analysis/model change, new listening tones, owl/assets or data deletion.
Handle login, avatars, export/delete/unlink, notifications, global Insights and
genuine flight remain pending (**ASSET-GATED — NOT IMPLEMENTED** for flight).
STOP for owner review; this does not authorize deployment or the next milestone.
