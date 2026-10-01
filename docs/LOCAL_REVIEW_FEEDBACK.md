# LOCAL review feedback — bounded L5 continuation

1 October 2026. Owner confirmed the analyst queue works (“ok working and good”)
and requested continuation, with a final assessment of whether role differences
are sufficient. The approved Frost system remains closed to redesign.

## Objective / assumptions / contract before implementation

Close Staff-owner → exact analyst assignment → saved technical review → owner
feedback. Analyst Overview should prioritize its ACTUAL assigned work; owners
retain New recording as their primary action. Shared audio/analysis/model remain
common capabilities. No artificial privilege or clinical qualification is added.

Saved reviews are observations for the recording owner, not private draft notes.
Make that publication explicit before saving. Unsaved edits remain local state.
Revocation ends further reviewer access; it does not erase saved feedback/audit.
Owner-facing history is each assignment's latest saved review, NOT version history.

| View | Existing authority / minimal adapter |
|---|---|
| Assign a review | Existing owner-only exact @handle/grant flow; open existing sharing controls |
| Analyst Overview | Existing GET /api/assignments; role-gated component, true pending/current-assignment activity |
| Analyst save | Existing GET/PUT /api/assignments/{id}/review; unchanged role/exact-grant policy |
| Owner feedback | NEW GET /api/recordings/{id}/reviews; existing active/verified actor + recording-owner predicate ONLY |
| Audio/analysis | Existing exact media/result authorization, unchanged; feedback permission does not confer audio |

Owner reader is parameterized and bounded: limit1–20 (default3), offset≥0,
actual total. Return saved reviews and current assignments, latest saved feedback
first; cancelled/expired unreviewed grants stay in existing sharing history.
Return actual reviewer display name/handle/public reference, source kind, decision,
notes, saved timestamp and assignment state, never Firebase UID/email. Other
Staff, ordinary grantees, analysts and nonowner Admin cannot read owner feedback.
An owner of any role retains the existing ownership rule, not a blanket Staff right.
Missing/denied/error data is unavailable, never preview rows or zero-valued success.

## Plan / files / commands

1. tests/test_m1_review_feedback.py → app/m1/store.py and api.py: prove owner-only,
   pagination, saved/revoked/expired notes, unchanged writer/sibling denial.
2. frontend/src/frost/OwnerReviewFeedback.tsx → recording detail/sharing/types:
   approved compact panel, Request review opens real controls, real saved feedback,
   bounded See more / See less, abort/refresh/session cleanup, publication copy.
3. Existing Overview/SharedReviews: reuse assignment rows, real role-focused
   primary action/priority queue and scoped activity. No new page/theme/statistic.
4. New isolated LOCAL review namespace and owner/analyst headed windows; preserve
   existing DBs/windows/data. Focused real local request/save/read/revoke checks,
   separate finite builds, desktop/mobile/tablet/Midnight visual inspection.
5. Five-axis review, implementation/FYP2/PAUSE, owner-authored commits/push; STOP.

Existing Python3.14/SQLite/FastAPI and React authenticated API/hooks; no dependency
or migration. Follow existing parameterized style: self._owner(db, actor, id)
BEFORE selecting protected feedback. React renders notes as text, never HTML.
Commands from implementation: existing venv python -m pytest -q
tests/test_m1_review_feedback.py tests/test_m1_review_views.py tests/test_m1_api.py
tests/test_m1_sharing.py. Frontend node tests/frost-review-feedback.mjs.
Builds separately from frontend: npm run build; npx --no-install vite build
--config ux-preview.vite.config.ts.

## Acceptance / boundaries

Actual owner can assign, reviewer can save, owner can read the persisted outcome
and notes after refresh/new session. Nonowners/anonymous deny; old review writer
remains analyst-only. Revoked/expired reviewer cannot read/write; owner feedback
and original/output hashes remain intact. Role-specific Overview is true and
usable at1440×900/390×844/tablet/Midnight, keyboard labels/focus/reduced motion.

Always: approved components/tokens, truthfulness, existing authority, focused tests.
Ask first: schema/dependency changes, new roles/privacy semantics or deployment.
Never: production/provider/account/backup/Axora mutation, ML change/training/T9,
new listening tones, account-data/Insights/flight work, deleting review evidence.
Use eligible RAW non-test HLS M0001 only; fixed fictional local identity mode
is clearly labelled, no live Firebase claim or runtime authentication bypass.

Execution evidence follows only after actual checks. New owner review pending.

## Execution — 2 October 2026, LOCAL only

Starts: implementation61ea07e64c26235a1749eb5811d02fec346eecd8,
documentation7dd717c777c37bad98185cafb60e1dcdc696cec4,
root4f5181431e5e9c4331d14ec4ba7919d771c20cc7. Previous Shared & assigned / saved
notes were owner-approved (“ok working and good”). THIS follow-up still needs
hands-on approval. Git/CLI actor ASHRAF-2004. Graphify tools were not exposed;
known relevant paths were used. Installed specification/planning/UI/browser/review
skills kept the work contract-first and bounded. Missing companion guides/DevTools
were reported; existing Playwright and focused tests used. No install/research reset.

Backend commit d9d9200ddffc552525ad637feb978469b1f9ba53 adds the bounded reader
after canonical actor/ownership checks. Count/page share one SQLite read snapshot;
limit≤20, parameterized SQL, actual total, no email/UID. Saved review observations
survive revoke/expiry/demotion as owner history. Unsaved drafts never enter this
endpoint; each assignment has its latest saved version only. Reviewer GET/PUT,
exact grant creation, independent media/result authority and schema3 are unchanged.
Unverified/suspended owners and all nonowners fail closed.

OwnerReviewFeedback shows3 rows / See more / See less and long notes / Read more
notes / Read less. Actual author, source, decision, saved time and permission state.
Request review opens/focuses EXISTING @handle sharing: choose Analyst review and
an exact original/result. Saving/revoking refreshes feedback. Focus/new-session
refresh retrieves persisted data. Client/recording owns responses; obsolete
requests abort and errors clear private rows. React escapes notes; no browser
notes cache. The API client allows numeric pagination ONLY for this endpoint;
raw query/URL/traversal/token-in-query paths remain rejected before token lookup.

Analyst Overview prioritizes actual pending-first assignments and Open assigned
reviews, with New recording secondary. Staff retains recording-first activity.
AssignmentRows is shared with the queue, no circular page dependency or per-row
fetch. Review activity explicitly covers CURRENT active assignments, not a global
history count. Role is not a clinical credential, extra model or blanket permission.
Result-only reviews still do not authorize sibling audio/owner feedback.

| Actual command / scope | Result |
|---|---|
| Listed pytest command: new owner-reader + existing review/API/sharing tests | 78 passed, exit0; existing Starlette/httpx deprecation only |
| EVIDENCE_ROOT=output/playwright/review-feedback/v1/client node tests/m1/client.mjs | 8 mock transport/token-source client checks, exit0; not provider evidence |
| node tests/frost-review-feedback.mjs | 6 real-local groups +1 explicitly labelled transport fault, PASS exit0 |
| node tests/frost-review-feedback.mjs --layout-only | Recording/review/grant read-only final captures, PASS exit0 |
| npm run build | Separate finite normal-app build, exit0 |
| npx --no-install vite build --config ux-preview.vite.config.ts | Separate finite isolated-preview build, exit0 |

Actual owner UI assigns fixed @snowowl an exact Original review; actual Analyst
saves outcome/notes; owner feedback survives refresh/new session. Keyboard note/
page disclosure works. Anonymous/unrelated Staff/nonowner Admin/reviewer cannot
read owner feedback. Exact Original review does not expose Heart/Lung. Revocation
denies reviewer GET/PUT and unmounts private content; owner retains saved history.
Copied manual assignments/notes, account profiles and all results were compared
and preserved. Four functional-run grants were revoked; audits and clearly labelled
LOCAL workflow-acceptance annotations retained. No new upload/inference was needed.

Initial TDD failure proved the absent reader. First UI run caught unsupported raw
query paths in the strict client; typed bounded pagination fixed the adapter, not
token/URL policy. Next run expected wrong denial wording; test corrected to actual
safe copy, no authorization change. Visual review corrected Frost reviewer-name
contrast, View all wrapping, and compact NEW mobile/tablet rows/action spacing.
Early Midnight images were mid-transition, not broken theme colours; final capture
waits for actual control colour with a3-second bound. An overbroad animation wait
was stopped only in its own headless capture process; partial files retained.
No owner browser/service was stopped. No palette/font/renderer redesign.

Five-axis review: real persistence/page/error/role correctness; small readable
components; one store/predicate/client and shared rows; owner-before-SELECT,
escaping/no-store/abort/denial clearing/independent media; bounded3-row pages and
two SQL queries/page, no N+1 or analysis recomputation. No outstanding Critical/
Important finding. Focused evidence, not a complete accessibility/clinical audit.

Final8 screenshots personally inspected at1440×900/390×844/820×1000, Frost/Midnight:
frontend/output/playwright/review-feedback/final-layout-v6/. 01 Staff Overview,
02 Analyst Overview,03 owner feedback,05 feedback mobile,06 Analyst mobile,
07 tablet,08 feedback Midnight,09 Analyst Midnight. Earlier v1/v2/layout-v1…v5
captures remain, not final settled-theme evidence. No horizontal overflow/JS
exceptions; keyboard/reduced-motion/44px controls/mobile-nav clearance preserved.

Receipt SHA256: functional b02970dbea213e387352e4cd6d0da6c2ef8d87765cecdbc7f493348743d66d2f;
client6b03b77fb0f12b08cade28c574a77ed7604425ebc7af8aba64cdc95653305d96;
final layout751aaec17ff8556908ad4c0fe66754150411dc30e600c164f3bcd26607ce6430.

## Hands-on review / stop

Visible terminal STETHOFUSE REVIEW FEEDBACK — LOCAL ONLY and TWO dedicated headed
Chrome role windows remain running. Frontend http://127.0.0.1:4200 → loopback API8200;
isolated .local/review-feedback/data/review.sqlite3, private/, DB.worker.lock and
session.json. Source shared-review copied using SQLite read-only backup API; no
overwrite/old restart. Fictional owner Ahmed @dragonfighter and Local Audio Analyst
@snowowl use the EXISTING fixed test-only SDK/verifier, NOT Firebase or an emulator.
NEVER enter real credentials. Recording/grant/review/private-file APIs/DB/worker
are real. Worker ready, both frozen hashes verified, one model load0.318182s.
RAW eligible non-test HLS M0001 provenance/output hashes remain intact.

Owner: Library → nm → Analyst feedback → Refresh feedback / Request review.
Analyst: Overview → Open assigned reviews → Review / Open review → Save review.
Return to owner and refresh feedback. Audio still requires independent grants.
Existing manual reviews and clearly labelled non-diagnostic test annotations remain.

From implementation: node frontend/tools/local-identity-review.mjs --feedback-review.
Stop ONLY this namespace: append --stop or Ctrl+C in its named terminal. Restart
same command; guarded PID/start-time checks retain DB/private files/notes. Earlier
4196/4197/4198/4199 sessions/windows untouched. Automation has stopped; owner review
pending. Do not start the remaining handoff or deploy.

Role assessment: shared player/separation/analysis tools are appropriate; the useful
distinction is owner requests/receives feedback versus analyst reviews assigned
resources/publishes observations. The missing loop is now real and local. No
different algorithm, blanket access or clinical claims are needed to differentiate it.

No production/Axora/Firebase-provider/ML/DSP/T9/user-data mutation or deployment.
Checkpoint/spec hashes retain the known1f7e…2658 /2573…10b1b values. Pending:
full review-history/version UI, notifications, avatar/account-data/export/delete/
unlink, secure handle login, global Insights and asset-gated owl flight.
