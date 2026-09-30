# Frost Studio — owner-approved LOCAL core integration

Status: **COMPLETE LOCALLY — READY FOR OWNER REVIEW**. Owner approved polish-v1
on 30 September 2026. Newly integrated interface **NOT DEPLOYED**. Visual
decisions are frozen; this is application integration, not a redesign/deployment.
Starting implementation `287a9f753a36fca691ad481b37134d9ed20beb53`, documentation
`c08045c5179c09887579d5339f0cb0e143902425`, root `7b6c88abe834e715d6b912a58bd0fc4c2a27443e`.

## Contract mapping (before implementation)

| Component | Existing real endpoint/data | Authority | Adapter |
|---|---|---|---|
| Shell/identity | POST `/api/auth/session`, GET `/api/auth/me`, `/api/preferences` | Existing verified UID, active account, server role/capabilities | Existing LiveAppProvider; no new token store |
| Overview/Library | GET `/api/recordings`, `/api/jobs`, `/api/results` | Authorized recordings/resources; jobs owner-only; results separately granted | Join complete collections by recording ID; client search/sort/page; no per-row requests |
| Upload/capture | POST `/api/recordings` (PCM WAV/form) | Existing principal-derived owner | Reuse upload and AudioWorklet encoder; presentation only |
| Separate/status/history | POST `/api/recordings/{id}/jobs`, GET `/api/jobs/{id}` | Owner-only request and job state | Idempotent stage-based progress; bounded active polling; no new pipeline |
| Recording/result deep link | GET `/api/recordings/{id}`, `/api/results/{id}` | Existing independent scoped read/review grants | Preserve direct result view; never require owner job permission |
| Player/analysis/download | GET/HEAD `/api/media/{id}` | Every resource independently checked | Approved player + current API client; actual unboosted WAV; abort/URL/node cleanup |
| Sharing/settings/Help/Admin | Existing live routes | Existing role/owner/grant rules | Keep working features, never replace them with preview forms |

The current collection endpoints return their complete authorized sets, not a
first page. Counts will explicitly describe those sets. Client pagination is over
the actual fetched collection. No additional read API or schema is currently needed.
Public handles/IDs are absent from these contracts: no demo or truncated IDs will
be invented. Actual internal identities remain in technical details.

## Ordered local execution

1. Extract neutral approved components/materials; keep preview fixtures isolated.
2. Connect shell/Overview/Library and legacy navigation to existing LiveAppProvider.
3. Connect upload/capture/detail/job lifecycle and independent protected players.
4. Connect lazy actual-source analysis; prove denied/revoked cleanup and errors.
5. Real local acceptance, focused tests, one final application regression, separate
   finite app/preview builds, integrated visual review, evidence and owner stop.

## Completed implementation and actual routes

Implementation commit: `8174d54e723ae6fa878f83c935556ea1775db3cc`.
`frontend/src/frost/` contains fixture-free adaptations of the approved shell,
glass/button/status primitives, players, charts, material tokens and perched owl.
Token declarations are byte-identical after changing root scope to `.sf-app`.
The isolated preview, approved screenshots and assets are untouched.

| Application route | Implemented behavior |
|---|---|
| `/app/overview` | Current account, authorized recent/unfinished recordings, own last-seven-day counts, honest shared/empty states |
| `/app/library` | Complete authorized collection; title search, four filters, newest/oldest sort, six-row pagination |
| `/app/recordings/new`, `/upload`, `/record` | Existing upload/AudioWorklet capture → persisted recording; actual local-file review, not a simulated upload |
| `/app/recordings/{id}` | Recorded/queued/processing/ready/failed detail; original independent of outputs; real history/provenance and existing owner sharing under disclosure |
| `/app/results/{id}` | Direct independently authorized result, without an owner-only job/recording prerequisite |
| `/app/audio/{id}` | Exact protected source and its analysis only; source kind obtained from authorized metadata |
| `/app/dashboard`, `/app/recordings`, `/app/results`, `/app/processing`, `/app/history` | Overview/Library redirects; result list uses `filter=ready`, processing list `filter=processing` |
| `/app/processing/{id}` | Existing owner-authorized job lookup → original recording identity; denied stays denied |
| `/app/shared`, review/profile/settings/Help/Admin routes | Working existing functions retained; new shell, no preview-only replacements |

No backend runtime, API policy, schema or migration changed. The only API-client
addition is HEAD revalidation using the existing authenticated request function.
No new pipeline, token store or application state-management framework.
Collection joins use three requests, not per-row status requests. Active jobs poll
at two-second intervals, stop at terminal/error states, and abort on teardown.
No invented completion percentage or supported retry for a permanently failed job.

### Deliberate real-data differences from the preview

Missing display names use “Your account”; real accounts never receive demo handles
or REC IDs. Internal keys remain in technical/history/existing advanced sharing
controls. Search is by real title until public IDs exist. Global Insights and fake
notifications are absent. Existing settings/reviews/Admin stay functional rather
than adopting simulated account forms. Weekly counts explicitly cover the owner's
last seven days; pagination labels the complete authorized filtered collection.

Ready detail uses a Ready chip rather than a redundant completed progress panel.
Only queued/processing/failed work displays the stage panel. Long titles wrap.
The legacy global image max-width rule initially compressed the mobile branch;
a scoped override restores the exact approved 266px/158px perch dimensions.
Renderer, eyes, assets, claw anchors and page-wide tracking are unchanged.

## Local isolation and identity boundary

Use the existing `frontend/tests/m1/ml_fixture.py` setup: a newly created isolated
temporary SQLite DB/private directory, ephemeral loopback API port and its own
DB-adjacent worker lock. Inspect/record these before starting the worker. It uses
trusted **test-only verifier injection** and the existing browser Firebase SDK
stand-in with fictional identities; it is neither Firebase live auth nor an auth
emulator. Real API/database/private files and frozen CPU worker are required.
No test verifier or identity fallback is added to application runtime source.
Synthetic fixture name: `M0001.wav`. No production paths, patient audio or T9.

The final API bound `127.0.0.1:56651`; frontend bound `127.0.0.1:4194` and proxied
only to that API. DB/private storage/lock were under
`.local/frost-core-runtime/stethofuse-ml-browser-3fjelqcc/`, verified before the
worker started. Both temporary services and their temporary data are cleaned up
by the harness. Reload and a new test-authenticated browser context proved
persistence while the real local DB existed; this is not production acceptance.

Frozen worker provenance honestly records base SHA `287a9f7` and
`code_worktree_dirty=true`: acceptance preceded the implementation commit.
It is not falsely attributed to a clean later SHA. Only presentation/test-harness
changes followed; the final small contact correction had its own focused check.

Frozen checkpoint SHA-256:
`1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658`.
Frozen spec SHA-256:
`2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b`.

## Local acceptance and build receipts

| Check | Result / scope |
|---|---|
| `EVIDENCE_ROOT=output/playwright/frost-core/integration-v7 node tests/frost-core.mjs` | Exit0;17/17 groups, real API/SQLite/private artifacts/unchanged worker; identity test seam only |
| `FRONTEND_URL=http://127.0.0.1:4195 EVIDENCE_ROOT=output/playwright/frost-core/application-regression-v2 node tests/m1/browser.mjs` | Exit0;14/14 groups; existing SDK/API MOCK regression, including preserved account/review/settings guards; not real provider evidence |
| `EVIDENCE_ROOT=output/playwright/frost-core/contact-v1 node tests/frost-core.mjs --layout-only` | Exit0;2/2 focused groups, real empty local API + test identity; final branch dimensions/contact and reduced/normal-motion tracking, no inference |
| `npm run build` | Standalone exit0, TypeScript + normal Vite; repeated only after the scoped final CSS correction |
| `npx --no-install vite build --config ux-preview.vite.config.ts` | Separate finite command, exit0; unchanged isolated preview |
| `git diff --check`, normal bundle fixture/banner/test-token exclusion | Pass |

The real-local groups prove upload→Library→queued→processing→ready, duplicate job
reuse, refresh/new session, independent automatic media, seek/source switching,
keyboard100/150/200%, unboosted measurements, unchanged downloaded artifact hash,
actual finite mono4kHz/60,000-sample Heart/Lung files, title/filter/sort/page
behavior, legacy links, anonymous401/unrelated403, exact Heart-only access,
separate result grant, revocation removing audio/analysis, sign-out URL cleanup,
real persisted failure and honest API-unavailable state. Zero page exceptions or
external provider requests. Desktop1440×900, mobile390×844 and tablet900px checked.

Capture uses Chrome's **fake microphone** but the real AudioWorklet/PCM encoder
and real upload API. It is not physical-stethoscope qualification. The failure
case injects a **test-only inference exception** into the existing observation
barrier, then verifies the actual worker failure transaction; it is not a new
model experiment. Decoder checks cover PCM8, extensible PCM, silent crest as
unavailable, malformed WAV rejection and actual stored sample-rate labels.

Earlier artifacts remain preserved: v1 RIFF fixed-offset assumption, v2/v3
render/focus wait mistakes, v4 teardown promise, v5 capture-save wait race were
harness issues. The first application regression expected absent Firebase build
configuration but the local environment was configured; the final run explicitly
cleared only its own four public Vite configuration variables. No credentials,
provider settings or authentication code were changed to pass tests. Visible
primary-link contrast/mobile-nav class issues were fixed before final acceptance.

## Media privacy, analysis and five-axis review

Each source is fetched with the current existing API client; no autoplay, token
URL, persistent audio cache or fixture fallback. Old requests abort; decoded
samples/player state/object URLs clear on resource/account changes. HEAD checks
run on focus/visibility/manual refresh and every30s while mounted. Denial/network
failure clears bytes/plots and offers a fresh authorized request. Revocation
cannot recall already downloaded bytes. Downloads use the original protected
Blob, never playback-gain samples.

Analysis is lazy/memoized per source; gain changes do not recompute levels/STFT.
WAV parsing preserves stored sample rate and amplitudes, separate from browser
device resampling. Stereo is explicitly labelled as an arithmetic mean-mix for
playback/analysis; this is not a raw-channel clipping certification. Main waveform
uses an absolute±1 axis; player thumbnails scale visually for readability only.
STFT display is Hann256/hop64, bounded180 columns, calibrated magnitude dBFS.
Low RMS<−35dBFS; clipping|sample|≥0.999; near-silence250ms RMS<−50dBFS.
Silence displays the−160dBFS floor with unavailable crest, not a false pass.
No SI-SDR/accuracy/confidence/diagnosis is shown for ordinary recordings.

Five-axis review: correctness (real stages/sources/lengths), readability (typed
small adapters/contracts and isolated legacy functions), architecture (one API
client/worker, preview separate), security (independent resources, stale-response
guards, revocation/sign-out cleanup), performance (bounded polling/lazy charts,
no per-row requests). No Critical/Important finding remains. This is not a full
WCAG certification or production performance audit. No Lighthouse campaign.

## Integrated visual evidence

Ignored directory `frontend/output/playwright/frost-core/integration-v7/` contains
19 captures plus the hashed receipt. The actual integrated app, not the isolated
preview, was rendered. Required owner references:

- `01-overview-light-desktop.png`, `02-library-light-desktop.png`
- `03-upload-review-desktop.png`, `04-queued-desktop.png`, `05-processing-desktop.png`
- `06-ready-detail-frost-desktop.png`, `06b-ready-detail-frost-full.png`
- `07-ready-detail-boost150-desktop.png`, `08-ready-detail-midnight-desktop.png`
- `09-ready-detail-mobile.png`, `10-ready-detail-tablet.png`, `11-ready-detail-mobile-boost150.png`
- `12-overview-mobile.png`, `13-exact-heart-access.png`
- `00-overview-empty-desktop.png`, `14-service-unavailable.png`, `16-failed-job.png`
- `15-device-capture-review.png` (fake-microphone review, labelled accordingly).

The final contact correction's current Overview references are separately under
`frontend/output/playwright/frost-core/contact-v1/`:
`17-overview-contact-desktop.png`, `18-overview-contact-mobile.png`,
`owl-desktop-closeup.png`, `owl-mobile-closeup.png` (actual empty local Library).
Earlier populated Overview images remain evidence of real data, not the final
branch-width reference. Ready-detail/mobile/Midnight layouts are unaffected.
Screenshots were inspected visually, not accepted merely because generated.

Raw receipt hashes are in `FROST_CORE_EVIDENCE.json`; no WAVs/model/private files
or screenshots are committed. Final source commit maps to this evidence, with
the dirty-at-execution fact preserved. The existing polish-v1 comparison remains.

## Pending, not cancelled

Handles/public IDs/backfill, username login, handle sharing, avatar/profile backend
extensions, export/unlink/delete, global Insights, real flight. Existing production
ML deployment remains unchanged; this newly integrated interface is LOCAL ONLY.
Owner review is next. No deployment or next milestone execution is authorized.
**Owl flight: ASSET-GATED — NOT IMPLEMENTED.**
