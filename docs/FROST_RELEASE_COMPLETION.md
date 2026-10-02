# Frost Studio completion / release contract — 2 October 2026

## Authority and assumptions

The owner accepted continuation of the local feedback work (“Done”) and requested
remaining work, push/merge and deployment without further intermediate design
reviews. Keep the approved Frost/polish-v1 design. Earlier LOCAL-only STOP entries
are historical; release remains conditional on actual test, security and recovery
gates, not screenshots or a promise of completion. Never claim an unrun owner test.

Assumptions: existing FastAPI/SQLite/private filesystem, Firebase UID authority,
same pinned environments and existing Docker Compose/Restic release procedure.
No framework/dependency upgrade, new auth provider, routing redesign, ML change,
training, T9 access, patient acceptance data or Axora mutation.

## Capability map / order

| Capability | Responsibility | Depends on |
| --- | --- | --- |
| review-history | Bounded saved reviews under current exact assignment policy | Existing review/grant/account authority |
| workspace-insights | Honest own-recording activity aggregates | Existing durable recordings/jobs/results |
| profile-extensions | Approved avatar/settings backed by protected persistence | Existing identity/storage/session |
| account-lifecycle | Export/unlink/delete with explicit policy and recent auth | Confirmed retention/provider contract |
| release | Reviewed push/merge, backed-up migration/deploy/live proof | Validated capabilities and operational readiness |

This extends the existing handoff, not a new design. Owl flight is separately
asset-gated; no rejected atlas or translated static owl may be substituted.
Microphone/device qualification and clinical validation are not implied.

## First two slices: exact contract

`GET /api/reviews/history`: active verified Audio Analyst only, own saved reviews
whose exact review grant remains active/unexpired and whose owner is active and
verified. Latest saved review per assignment, not an invented version log.
Bounded page3/default, max20, integer offset. Count/page share a read snapshot.
Revoked/expired/unavailable records remain stored for owners/audit, but are not
redisclosed to the analyst. No new privilege or sibling media access. Plain text
notes, compact disclosure, existing review links and refresh/access cleanup.

`GET /api/insights`: active verified actor; own recordings only regardless of role.
Database aggregate counts/recorded duration/current states and fixed recent-day
activity; exact time zone/scope described. No titles/audio/notes from granted or
unrelated recordings, no inference quality score. Empty means zero; failed request
means unavailable. Same authorization as owner Library, no analysis of audio bytes.
Use existing primitives/materials, a compact summary and progressive detail.

## Implementation / verification conventions

Provider modules in `app/m1/`, real view adapters in `frontend/src/frost/`, tests
in `tests/` and existing `frontend/tests/`. Parameterized SQL and existing `_actor`
before all reads; no secret/token output or runtime fixture fallback. Reuse
abortable API client and hooks; stale/denied responses clear private view state.

Focused backend: pinned Python `-m pytest -q tests/test_m1_workspace_completion.py`
plus related existing review/identity suites. Browser: existing Playwright-core
local harness with fixed fictional SDK/verifier ONLY; real API/DB/private data.
No live account mutations. Use eligible recorded HLS-CMDS M0001 for listening,
never mathematical tones/T9/patient media. Save ignored runtime evidence.

Build separately in frontend: `npm run build`; then
`npx --no-install vite build --config ux-preview.vite.config.ts`. Record actual
exit codes. Five-axis review before merge; critical/required findings block it.

## Boundaries / unresolved gates

Always preserve current UID/ownership/exact grants/Admin privacy, source semantics,
audio graph, stored WAV bytes, model/spec hashes, private access and backups.
No silently enabled unavailable setting or fake success. A 403 is not a reason
to weaken policy. Schema/dependency needs must be identified before expansion.

The handoff expressly requires account retention/audit policy before deletion;
an asynchronous owner question is pending. No deletion/provider-unlink/username
proxy is authorized by inventing policy. Genuine flight needs usable approved
frames. Continue other safe work while these are resolved; report blockers exactly.

Production mutation starts only after reviewed clean code, effective deployment
configuration, verified recovery anchor, safe schema migration, and a concrete
StethoFuse-only rollback plan. Never repeat historical backup drills or T9.

## Executed read-only workspace slice

Implemented `WorkspaceStore`, shared review-scope SQL, bounded saved-history reader
and own-Library Insights; the approved Frost components now use both real routes.
Review history remains the latest saved version per *current* exact assignment.
Owner saved-feedback paging shares the same abortable hook; no review writer or
grant policy changed. Insights totals cover the whole owned Library (not its first
page); its two seven-day series use explicit UTC dates. Existing roles still share
upload/audio/analysis tools. The Analyst's meaningful distinction is assigned work,
saved observations and owner-visible feedback, not another separator or blanket
access. This role difference is appropriate for the current collaboration workflow.

The local launcher stop guard now resolves the invoked script against its actual
process working directory as well as matching PID birth time. A relative-path
launch previously failed closed with `PID identity mismatch`; the verified exact
launcher now stops normally without broad process matching or deleting review data.

| Check | Actual result |
|---|---|
| Focused new readers + existing review views/feedback | 29 passes, exit0 |
| Appropriate application/access/identity/sharing/processing/operator/token regression | 174 passes +26 subtests,4 optional ML cases skipped, exit0 |
| Actual TypeScript API client / MOCK token and transport | 8 checks pass, including bounded history query contract |
| Real isolated API/SQLite browser acceptance | 3 real workflow/security/layout groups +1 explicitly injected transport-failure group; exit0 |
| Read-only final responsive/theme correction check | Exit0; actual saved notes/activity, no grants/reviews/recordings/results changed |
| `npm run build` in frontend | Exit0, independent finite command after final CSS |
| `npx --no-install vite build --config ux-preview.vite.config.ts` | Exit0, independent finite command |

Regression uses existing `/tmp/stethofuse-m1-auth-bvIfFV/venv/bin/python` (Python
3.14.4, official SDK already installed). An initial run in the separate ML venv
had168 passes,6 missing-`firebase_admin` errors and4 skips; this was an environment
selection mistake, not an auth-code fix. No packages were installed/upgraded.
The browser's first attempt passed paging but timed out on a test matcher that
omitted the actual `offset=0` suffix. Corrected matcher/tied-save ordering; the
failed receipt remains under `workspace-completion/v1/`. Four temporary grants per
functional attempt were revoked; existing manual assignments/notes/profiles and
all model results were verified unchanged. Test-only saved annotations are retained
in owner history and clearly labelled. No owner's normal browser was automated.

Final inspected screenshots: ignored
`frontend/output/playwright/workspace-completion/final-v3/`, with desktop1440×900,
mobile390×844, tablet820×1000 and Frost/Midnight. Earlier v2 captures exposed a
cramped mobile title; only these new pages now stack the action below the heading.
Theme screenshots wait for actual material convergence, not arbitrary delays;
the initially dark-on-dark mid-transition button is not a changed token. All
approved palette/material/type/player/iris/perch declarations remain unchanged.
Fresh page loads have no JS errors. A dev Fast Refresh context invalidation during
editing was resolved by a clean local restart/full navigation, not an auth bypass.

Small evidence hashes (artifacts themselves remain ignored): real browser v2
receipt `921c14951e3e3ff4c5e7200d0968ff7075b0c2b3f43e23909e8155adede780f4`;
final read-only layout receipt
`e6efd9fdacd4749a991e57b94fa9d427a00b4bc706ab55abd1b06576e47411ca`;
MOCK client receipt
`cb8938b2f94d72b20358eb9e337c1de933fa0324ecbb51ebec4c3b3118cf2d3d`.

### Five-axis review (this slice)

Correctness: real count/page snapshots, deterministic ordering, server range
validation, current model's unique recording/job join; empty and unavailable are
distinct. Readability: named own-scope response, short fixture-free view adapters,
existing formatted dates/identity/disclosure. Architecture: one canonical assignment
scope and shared two-consumer paging hook; no queue/model/identity duplication.
Security: verified active actor first, role/exact-owner/expiry predicates preserved,
revoked notes hidden from reviewer, plain-text notes, no email/UID in history,
bounded numeric same-origin queries and abort/error cleanup. Performance: three
fixed aggregate queries, bounded3-row reads, seven-day plot, no audio decoding or
new dependency. Important mobile heading issue corrected; no outstanding Critical
or Important finding for this bounded slice. This is not a full penetration audit.

### Release readiness and still-gated work

The tested core/identity/sharing/analyst/history/Insights interface is a releasable
increment under the owner's explicit merge/deploy request. It is **not** a claim
that all later lifecycle or asset work is complete. Existing display-name, handle,
appearance/audio preferences and password recovery work. Avatar storage/validation,
real email notifications, export/unlink/delete and secure handle login remain
unavailable; deletion awaits the explicit retention answer and provider-security
contract. Flight remains **ASSET-GATED — NOT IMPLEMENTED**. Live microphone/device
qualification is separate and the owner's Coming soon lock stays in place. None
of these services may be simulated or silently enabled for release.

Production baseline read-only check: API200 with provider/storage/separation
enabled; one web/API/MLworker, all required service states healthy/ready; Axora200.
Database schema2/integrity ok:3 users,6 recordings,15 resources,3 grants,3 jobs,
3 results,1 saved review. Production model/spec hashes exactly match the frozen
values. Actual release execution/backup/migration/live acceptance must be recorded
separately after they occur; these preflight observations are not deployment proof.

## First release attempt / recovered packaging defect

Source10d07a9 was pushed and exported from clean Git. Pre-migration encrypted
snapshot `09f6d0ed6def14fad3de995d3f89513a173476e443a77cdcdfa0d1f92c14d7a5`
completed remotely at14:28+08. A focused restore of schema2 SQLite and frozen model
bundle into `/var/backups/stethofuse/frost-release-20261002.jkTawY/restored-pre`
proved integrity ok and both exact hashes. Existing helper quiesced/resumed all
three StethoFuse writers; pruning stayed disabled. Old images were preserved as
`:pre-frost-20261002`, root-only runtime copy retained, no SSH trust bypass.

The first new container startup failed closed: the Docker context allowlist had
not included `003_public_identity.sql`. Both API/worker reported a missing migration;
API became unhealthy and public API briefly502. No migration or generated result
was published: SQLite remained schema2,3 users/6 recordings/3 succeeded jobs intact.
Restored old image aliases/runtime/deploy symlink immediately; old services/public
API200 resumed. No DB restore/downgrade or data deletion was needed. Axora remained
200 throughout. This is an unsuccessful deployment attempt, not live acceptance.

Minimal correction: explicitly include003 beside002 in `.dockerignore`. Added one
operator regression requiring every source migration to be admitted by the runtime
context. It first failed on003 as expected; after the fix it passes. Before retry,
both corrected images must pass a filesystem presence check and isolated v2→v3
migration/preservation check. No auth, model, inference or frontend design change.
