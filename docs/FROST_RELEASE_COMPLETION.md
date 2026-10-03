# Frost Studio completion / release contract — 2 October 2026

## Current status — live acceptance and backup verified, 3 October 2026

**PRODUCTION ML DEPLOYMENT COMPLETE — LIVE ACCEPTANCE AND BACKUP VERIFIED.**
This dated completion supersedes the pending Staff/Analyst/backup checkpoints
preserved below. Actual deployed source remains
`b6ee625abe0f4d8d5b2b136398656b4c810e8f83`; this completion changes evidence only,
not the frontend, backend, authorization, frozen separator or deployment.

### Real-account collaboration and privacy

The owner entered credentials in separate ordinary Brave windows for the existing
Staff `@ivoryfinch`, Analyst `@blueheron` and Admin `@bluefox`. Real Firebase is used;
no fictional SDK/verifier, token extraction, browser-security bypass or provider
change. Native window-scoped screenshots were personally inspected. DevTools
request-status capture was unavailable; the authenticated observations below are
actual protected-request UI behavior, not invented HTTP status measurements.

| Focused live case | Actual result |
|---|---|
| Owner workflow | Earlier current-run upload/Ready/three-source playback/download/refresh proof retained |
| Anonymous Heart/Lung | Both protected endpoints returned 401 |
| Exact Heart read | Analyst automatically loads Heart audio and its measured waveform/spectrogram; Original/Lung are not exposed |
| Exact result review | Assignment `ASN-133J-S0Q42V` permits metadata/notes, not sibling audio authority |
| Saved observations/history | Analyst saves the explicitly nonclinical acceptance note as Reviewed; SQLite and `review.updated` audit persist; current saved history reloads |
| Owner feedback | Staff sees the saved note and real author before revocation |
| Heart revocation | Subsequent protected request denied; audio, plots, metrics and download clear; independently granted review metadata remains usable without audio |
| Review revocation | Explicit Refresh access denied; title/result/notes/audio/analysis clear; Analyst saved history becomes empty |
| Unassigned authenticated Analyst | Fresh post-revocation access remains denied; no extra account needed |
| Admin without grant | Direct `/app/results/d714c18abf274a8d80e6fb7f77fb5239` shows permission denial and no private content |
| Owner/audit retention | Full refresh retains the saved Reviewed note marked Access revoked; both `grant.revoked` audits persist |

Only the two acceptance grants were revoked through the owner UI: Heart
`GRT-67DT-NTPQ1F` at1790986075, exact review `GRT-46T1-XX9Z6J` at1790986165.
All five historical/current grants are now revoked; no active temporary permission
remains. Original recordings, outputs and earlier saved reviews were retained.
Revocation protects subsequent requests; it cannot recall already downloaded bytes.
No authorization defect was found or security semantics changed.

### Focused post-acceptance recovery proof

Existing encrypted Restic/B2 `stethofuse-backup.service` ran once, on 3 October at
08:22:30–08:22:51+08; Result=success, ExecMainStatus=0. It quiesced only StethoFuse
web/API/one ML worker, then resumed web/API healthy and worker ready. Axora was
not stopped or modified. Worker startup model-load observation after resume:
0.428080s, not a job-latency/SLA measurement. Backup timer and StethoFuse tunnel
remain active; public StethoFuse API and actual Axora host both return 200.

Remote snapshot **`31779753cf3e23348e7f05a6713428d11ce1388479a0ff9a20604ec05453809d`**
(snapshot timestamp 08:22:32+08) contains data/private/models/runtime configuration.
Read-only remote listing verified 15 private files, including the new original and
both outputs. Remote content hashes match the stored original, Heart and Lung
hashes in the preceding Staff evidence, plus both complete frozen artifact hashes:

- Checkpoint: `1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658`.
- Separator specification: `2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b`.

Small restore of SQLite/model bundle to root-only
`/var/backups/stethofuse/frost-release-20261002.jkTawY/restored-live-20261003.B5HyeT`
proved schema 3/integrity ok, zero foreign-key errors, 3 users/7 recordings/
19 resources/5 grants/4 jobs/4 results/2 reviews. The completed acceptance job,
saved reviewed note, both revoked grants, source provenance and exact model hashes
are present. Remote verification exited 0. Live data was never overwritten; old
recovery anchors retained, pruning still disabled, no snapshot deleted. Backup
credentials stayed in existing root-protected systemd credentials, never in Git
or printed output. No SSH connection/trust bypass was needed for this local-host
backup invocation.

Immutable ignored partial receipts remain unchanged. Final ignored receipt
`frontend/output/playwright/frost-production-live-v1/completion-receipt.json`,
SHA-256 `07ca30f68c27749e3c7948fcb8e68f32960dc0642a969a729906abf0b538ad7e`,
references them, the personally inspected Admin-denial capture and backup proof.
No broad tests/builds/research were rerun for this evidence-only completion.
Five-axis evidence review: assertions match observed UI/audits/remote hashes;
dated partial checkpoints remain explicit; no runtime coupling, secrets, binary
artifacts or performance changes; no outstanding Critical/Required finding.

This is agent-operated live acceptance with owner-entered sign-ins, not a newly
reported owner hands-on approval, patient evaluation or clinical validation.
Avatar persistence, real notifications, export/unlink/delete and secure handle
login remain unavailable. Deletion/retention/provider policy still requires owner
direction; flight remains **ASSET-GATED — NOT IMPLEMENTED**. Physical microphone/
stethoscope qualification remains separate. No training, T9 reuse, model/inference
change, new algorithm, owl/design alteration or Axora mutation occurred.

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

## Corrected production release / recovery receipt

Deployed source **b6ee625abe0f4d8d5b2b136398656b4c810e8f83** from a clean Git
archive. The correction's operator/identity checks passed20 cases, exit0. Both
runtime images contain002/003; a network-disabled, read-only API container with
only temporary fixture storage migrated schema2→3, preserved every old row,
passed integrity/foreign-key checks and retained identical generated identities
on repeated startup. It mounted no production path. The web image was built as
a separate finite command, exit0; its normal-app payload is the tested interface,
not the isolated preview. No package or image-base upgrade.

Only the StethoFuse deploy symlink, reviewed image set and runtime code-SHA field
changed. All other runtime/provider/storage values compare byte-for-byte with the
pre-release copy. Production initialization applied003 transactionally once;
schema3, integrity ok, zero FK errors. Before authenticated live interaction, all
old fields compare exactly with the pre-release receipt:3 users,6 recordings,
15 resources,3 grants,3 jobs/results,1 review,1 preference and12 private files.
Original/generated WAV bytes and previously recorded provenance were not changed.

The public API returns200; anonymous Insights/history return401. One web/API is
healthy and exactly one restricted CPU worker is ready (network none, read-only,
10001:10001,2 CPU/2GiB limit). First model load0.383867s; after backup restart
0.361318s. These are startup observations, not job/clinical-performance claims.
The worker runtime code SHA matches the deployed source. Frozen checkpoint/spec
hashes match both live and restored copies; permissions remain root:10001,
bundle0750/files0440, private/data10001:10001 mode0700. Models are mounted only
by the worker, never web/API. Axora's actual public host `https://axora.management`
returns200; an assumed alternative hostname failed DNS and is not health evidence.
No Axora/provider/routing/auth-policy/ML/T9 mutation occurred.

Post-release encrypted B2 snapshot
**a32d8b1e6896a58217b16cb947858e5a6734125d319d65d5314502a4ceda001d**,
2October15:02:41+08, covers data/private/models/runtime config. Existing quiescence
stopped only StethoFuse web/API/worker at15:02:39 and resumed all healthy/ready;
service result success/exit0 at15:02:59. A remote listing proved12 private files
and expected model paths. Small isolated restore at the root-only recovery
directory's `restored-post/` proved schema3/integrity ok, zero FK errors, expected
counts and both exact artifact hashes. Live paths were never overwritten.
Backup timer remains active; pruning remains disabled; no snapshots deleted.

**At the release checkpoint, signed-in Frost acceptance was PENDING.** A dedicated visible
Chrome window rendered the official production login with real Firebase and no
test SDK, transport interception or fixture fallback. Staff sign-in was requested
from the owner, without requesting/reading credentials. The older completed live
ML/privacy acceptance is preserved but is not counted as a new signed-in Frost
test. This receipt establishes operational deployment/recovery, not unrun live
upload/playback/analyst checks or completion of gated account services.

Rollback before003 failed was simply the preserved old images/env/symlink. After
successful003, old schema2 code cannot be started against schema3: preserve new
data first and use a matching protected DB/private recovery set if an actual
rollback is required. Never manually downgrade/drop schema or overwrite newer
user data. Keep the pre/post recovery anchors and old image tags available.

## Live Staff acceptance / remaining Analyst sign-in gate

On2October the owner completed real Google/Firebase sign-in in the existing
ordinary Brave profile. Google had refused the dedicated automated Chrome
session; no browser-security workaround, profile/cookie copying, Firebase change
or authentication-code change was used. Normal Brave rendered the actual signed-in
Frost Overview as the existing Healthcare Staff `@ivoryfinch`.

Uploaded the dataset's **recorded** `datasets/hls_cmds/raw/Mix/M0001.wav`, not
mathematical tones. The existing native-triplet manifest marks M0001 eligible
non-test, with no exclusion reasons; complete SHA-256
`8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616` agrees
with the uploaded original. This is a non-patient manikin workflow fixture, not
training, native-triplet supervision, T9 or a new accuracy evaluation.

| Live observation | Actual result |
|---|---|
| Recording | `REC-GCD3-P6HBEG`, labelled raw-HLS/non-patient/no-T9 acceptance |
| Request / durable job | Visible Starting indicator; DB queued then succeeded, `JOB-6SB3-VQNK8F`, one attempt |
| Result | `RES-8H8V-J0VREG`; automatic private Original/Heart/Lung loading |
| Worker | CPU inference0.145538s; processing0.256122s; actual code SHA remainsb6ee625 |
| Artifacts | Both finite4-kHz mono float32 outputs,60,000 samples; original hash unchanged |
| Playback | Heart seek to7s, source switching, keyboard100/150/200% and Boost; restored initial100% |
| Download | Heart WAV hash `d2a1fa541116b634455c8e1ce1b502b7628e7e69ee93443b6e3d69cfbfa0f1da` matches stored output |
| Measured before/after | Original/Heart/Lung crest14.2/14.6/14.9dB, with levels/duration/clipping; not an accuracy judgment |
| Persistence / Insights | Full refresh restores Ready; Library/Insights and DB agree:5 owned recordings,4 Ready |
| Integrity | Schema3/integrity ok, zero FK errors, both frozen model hashes unchanged |
| Owner sharing | Exact-handle lookup `@blueheron`; successful narrow grants and `grant.created` audits |

Only two temporary scopes were created on this new acceptance recording:
Heart read `GRT-67DT-NTPQ1F` and exact result review `GRT-46T1-XX9Z6J` /
`ASN-133J-S0Q42V`. Neither grants Original or Lung. Older grants remain revoked;
older recordings/results are not removed. These grants are **active pending the
live Analyst check and deliberate revocation**, not a permanent sharing change.

The separate ordinary Brave login window is ready for the owner to sign in as
the existing Analyst `@blueheron`. Analyst access/sibling isolation, saved review/
history, owner feedback, revocation/denial and final post-acceptance encrypted
backup are **PENDING**, not inferred from the Staff view or earlier local tests.
The verifieda32d8b1 post-release snapshot predates this new recording/grants.
No new repeat-POST latency or HTTP latency claim is made; earlier idempotency
evidence remains historical. This is not owner hands-on or clinical acceptance.

Ignored local receipt: `frontend/output/playwright/frost-production-live-v1/staff-receipt.json`,
SHA-256 `42fe75cdb2896b8079020669c0796a3a810ceef243c1ada7d230f7d0622298da`.
The receipt lists personally inspected window captures and the authorized download.
No model, inference, source, frontend, auth policy, routing or Axora change occurred.
