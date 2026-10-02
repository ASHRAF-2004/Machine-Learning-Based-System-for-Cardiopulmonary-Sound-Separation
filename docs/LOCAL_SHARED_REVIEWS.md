# Frost Studio — bounded LOCAL Shared & assigned slice

1 October 2026. The owner approved the concise-details/handle-sharing refinement
with “ok good next”. Preserve that approval and follow the existing L5 contract;
do not reopen the visual direction or execute destructive account-data services.

## Objective and established contract

One Shared & assigned destination, with Shared with you and analyst-only Assigned
reviews. Reuse actual authorized collections, the current exact review grants and
existing review submission. Titles and subtle public references replace primary
raw IDs. Show three important assignments first; disclose more/less. A real review
decision/notes must save and survive refresh. These are non-diagnostic reviews.

| Component | Actual data | Authority / adapter |
|---|---|---|
| Shared recordings | GET `/api/recordings`, `/api/jobs`, `/api/results` | Existing authorized collection and approved Library; no new source permission |
| Assigned reviews | GET `/api/assignments` | Current analyst + active exact review grant; additive joined title/reference/kind/decision, no per-row fetch |
| Exact review | GET/PUT `/api/assignments/{id}/review` | Existing review predicate and audit; additive friendly context, unchanged notes/decision rules |
| Assigned audio/result | Existing protected media/result endpoints | Exact assigned resource only; result metadata is not sibling audio permission |

Deep links `/app/reviews/{id}` retain identity. Old queue aliases redirect to
`/app/shared?view=assigned` without an owner-only recording fetch. Existing role
guards remain. No new grant semantics, schema, dependency, token layer or processing
system; local acceptance creates only ordinary exact review grants.

## Plan / source boundaries

1. Add safe joined list/detail context in `app/m1/store.py`; focused API tests in
   `tests/test_m1_review_views.py`, proving unrelated/Admin/expired/revoked denials.
2. Add `frontend/src/frost/SharedReviews.tsx`; reuse existing Library, panels,
   buttons, status/source/player and unsaved guard. Connect routes/types; consolidate
   the redundant queue navigation while preserving deep links and access guards.
3. Focused real-local review save/refresh/revocation and disclosure checks through
   a new copied isolated review namespace. Preserve the owner's existing windows,
   profiles, handles, data and all frozen artifacts. Inspect desktop/mobile/Midnight.
4. Separate normal/preview builds, five-axis review, evidence/FYP2/PAUSE checkpoint;
   leave a visible manual review and stop for the owner.

Style: existing Python parameterized SQLite transactions and React authenticated
API/session lifecycle; approved Frost variables and accessible native controls.
Do not substitute preview identities/content or permission fallbacks in product
source. Missing title/status is unavailable, not invented. Abort obsolete saves,
preserve drafts during focus refresh, clear denied data and stop sensitive views
when access is lost. Do not persist private review notes in browser storage.

## Commands / focused verification

- Implementation: `/tmp/stethofuse-m1-auth-bvIfFV/venv/bin/python -m pytest -q tests/test_m1_review_views.py tests/test_m1_api.py tests/test_m1_sharing.py`
- Frontend: `node tests/frost-shared-reviews.mjs` (real local API/files, fixed fictional identity only).
- Frontend app build: `npm run build`.
- Isolated preview build: `npx --no-install vite build --config ux-preview.vite.config.ts`.

## Acceptance / stop

The shared/assigned page has truthful empty/error states and no primary raw IDs.
Pending assignments come first; three visible initially, more/less works by keyboard.
Actual reviews persist, result-only assignments do not expose audio, revoked access
blocks subsequent reads/writes and the UI removes the sensitive view on learning
the denial. Old links, role checks, mobile clearance and approved themes remain.

Always preserve source data, UID/owner/role/exact-resource policy and audit.
Ask first for a schema/dependency/security-architecture change. Never deploy,
modify production/Axora/providers, retrain/change ML or touch consumed T9. No new
listening audio; existing eligible raw non-test HLS recordings only. Avatar/data
services, secure handle login, global Insights and genuine owl flight remain gated.

## Completed execution — ready for hands-on review

Starts: implementation fc126340e19617812cf01b82cf22a34f06c486cd, documentation
7fbb9e57d8ec4eef568aa7839134c4dd3cad967c, root
463e960539cc204fe10374d1cc7e28ad8d1b1d7d. Git/CLI actor ASHRAF-2004. Graphify
was configured but not exposed to this session; known relevant paths were read
without reconnecting providers, re-indexing memory or repeating design research.
The existing UI/browser/code-review skills kept the approved components, accessible
native controls, focused evidence and five-axis review; no design/dependency reset.

Backend source: 9deda6b1d75c250852f6537d07dace7b0991022d. One authorized joined
assignment query supplies current title/REC/exact source and persisted review
status; list responses contain no private review notes. GET/PUT review adds friendly
context only after the unchanged review predicate. No migration, new endpoint,
owner/role/expiry/revocation policy or processing-pipeline change.

SharedReviews.tsx and AssignedReview.tsx connect the canonical page and actual
editor. Pending/older work first, three rows then See more / See less, real search
and two filters. Existing protected player, result view, real analysis, download,
theme and unsaved guard are reused. Notes/outcome persist through the existing PUT,
refresh and new session. Dirty drafts survive access refresh; denied saves clear
the draft and unmount protected content. Aborted obsolete saves cannot publish
stale state. Notes are not saved to browser storage. Old analyst aliases redirect
without losing exact review IDs or bypassing role guards. Historical notes remain
stored; a complete historical-review retrieval page remains pending.

| Actual check | Result |
|---|---|
| New review-context tests + existing API/sharing tests | 69 passed, exit 0 |
| Real-local browser/API groups | 4 passed, exit 0 |
| Separately labelled assignments transport failure | 1 passed; truthful unavailable state, not demo rows |
| Read-only final manual-assignment layout checks | PASS, exit 0; 9 captures, notes 14px |
| Normal app: npm run build | Standalone finite command, exit 0 |
| Isolated preview: npx --no-install vite build --config ux-preview.vite.config.ts | Separate finite command, exit 0 |

Permission evidence: Original-only assignment exposes exactly Original; result-only
review exposes metadata but no Heart/Lung player or audio. Anonymous, unrelated
Staff, Admin and non-assigned analysts remain denied. Saved notes cannot be read
or written after expiry/revocation or owner suspension/unverification. Actual
owner revocation returns 403 on a dirty review save; UI clears the form/audio.
Keyboard more/less retains focus, responsive screens have no horizontal overflow,
reduced-motion and existing mobile navigation clearance remain, no JS exceptions.
Four Original test scopes exercised list disclosure; one subsequent result scope
exercised sibling isolation. All five temporary functional-test grants were revoked;
audit and test notes remain. They were not five recordings or independent patients.

Earlier failures are retained, not hidden: pre-change TDD found missing joined
title (1 failed/5 passed); the first browser run caught helper copy polluting the
Review notes accessible name. Separate label/aria-describedby fixed it before the
passing v2 run; its temporary grants were revoked. A first local startup refused
an incorrect assumption that copied Bob was an analyst. Bob remains Staff; no role
was weakened to pass. The final visual check found inherited 12px notes text;
the editor now uses approved operational sans at 14px, verified in final-layout-v2.

Final images personally inspected at 1440×900, 390×844 and 820×1000, Frost/Midnight:
frontend/output/playwright/shared-reviews/final-layout-v2/ contains
01-shared-desktop.png, 02-assigned-desktop.png, 03-original-review-desktop.png,
04-review-notes-desktop.png, 05-assigned-mobile.png, 06-review-notes-mobile.png,
07-assigned-tablet.png, 08-assigned-midnight.png and 09-result-only-review.png.
Functional/denied/unavailable images remain under shared-reviews/v2/.
All earlier v1 evidence is retained; images/audio/DBs are ignored, not committed.

- Functional receipt SHA-256:
  0caca89c543b7b22bd9ea82cb4951299f3627c4893a8b2d6564d996486080d31.
- Final layout receipt SHA-256:
  e6e4a1573b5d054a429169e3e8c1e89c48c879e1a28a11b4da0c1d1a79aeb867.
- Assigned desktop image SHA-256:
  1ba3c753692aafa4c603b98182096e5e358d60dad704645e5526eb004590790d.
- Notes mobile image SHA-256:
  efd2632463adbcedf30a98cff23ccd0b187fe39280a04fb647eb6dc48c310c3b.

Five-axis review: correctness (actual save/deny/persistence), readability
(small named components, labels/helpers), architecture (same client/views/policy,
one joined list), security (exact scope/denial/abort, no notes cache or provider
change), performance (no per-row fetch/new dependency/model execution). No unresolved
Critical/Important finding. This is focused local acceptance, not clinical evidence.

## Retained owner session / reproducibility

The NEW headed Chrome LOCAL SHARED REVIEW and visible STETHOFUSE SHARED REVIEW —
keep open terminal are running at http://127.0.0.1:4199; proxy/API loopback8199.
Both returned 200 after verification. Dedicated persistent namespace:
implementation/.local/shared-review/, database data/review.sqlite3, private/,
DB-adjacent worker lock, guarded session.json. Source copy handle-sharing-review
is read-only and never overwrites an existing review DB; earlier4196/4197/4198
services, browser windows and owner data remain intact.

Identity ONLY reuses the existing fixed TestVerifier/SDK, NOT live Firebase/emulator.
Never enter real credentials. In this new copy only, the established fixture's
fixed fictional admin and analyst were missing: normal register/bootstrap and
existing Admin role-change methods created them; unexpected existing roles fail
closed. Alice/Bob roles, handles and profiles are unchanged. Analyst is Local
Audio Analyst / @snowowl. All recording/media/review APIs and private files are real.
No arbitrary token or product runtime auth bypass was introduced.

Explicit one-time helper frontend/tools/shared-review-assignments.mjs left two
ordinary owner-created review grants for hands-on use: Original audio only and
Result details only. No Heart/Lung grant; pending decisions/blank notes are yours
to edit. A receipt prevents recreating grants if you revoke them. This dev helper
is not imported by product code. Functional tests deliberately refuse to run over
these manual assignments; final captures were read-only and did not edit notes.

Click Shared & assigned → Assigned reviews → Review. Change Review outcome,
enter Review notes, Save review, refresh and revisit All assignments. Existing
raw eligible non-test HLS-CMDS Mix/M0001.wav (not generated tones/patient/T9) is
the listening source. Four recordings, three results, all ten private file hashes
and zero foreign-key failures match the read-only source copy. Frozen worker
verified/loaded once in 0.288944 seconds; no new optimizer or inference ran.
Checkpoint/spec hashes remain exactly the frozen values; no DSP/ML/T9 change.

Start/restart from implementation:
node frontend/tools/local-identity-review.mjs --shared-review
Stop ONLY this namespace: append --stop, or Ctrl+C in its named terminal.
Guarded process IDs/start times prevent broad kills. Stop preserves SQLite/private
files, grants/results and review notes. Automation has stopped; leave the owner's
window and terminal available. Owner acceptance of THIS slice is pending.

Remaining: avatar/account-data/export/delete/unlink, secure handle login,
notifications/global Insights, complete historical-review retrieval and genuine
owl flight (ASSET-GATED — NOT IMPLEMENTED). Microphone remains Coming soon;
upload works. No production rollout or next milestone is authorized by this record.
