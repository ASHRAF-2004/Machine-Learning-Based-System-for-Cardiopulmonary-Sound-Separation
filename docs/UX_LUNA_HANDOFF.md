# Frost Studio v1 — exact Luna handoff, NOT STARTED

30 September 2026. **STOP until owner approves the screenshots and design.**
No automatic delegation, propagation, identity backfill or deployment is authorized
by this handoff. This is the contract for a later implementation turn.

## Invariants and normative sources

- Read AGENTS/PAUSE, rerun relevant MCP/auth/Git checks; ASHRAF-2004 only.
- Use existing branches/PRs #9/#2; no force push, main merge or AI trailers.
- `UX_REDESIGN_SPEC.md`, `UX_LAWS_AUDIT.md`, final browser screenshots and
  `frontend/src/ux-preview/tokens.css`/styles are the frozen design. Reuse components,
  not screenshot bitmaps. No new palette, typography, card sizes or navigation.
- Production remains release `c96c7cb147833daba88e99596dd71d3f814274e9` until a
  separately authorized rollout. Do not train, rerun T9, change inference or Axora.
- Preserve Firebase UID/internal keys, backend account state, ownership, exact
  grants, analyst assignments and Admin-without-grant denial. UI is not authority.
- Replace fixture adapters, not model/security implementations. Keep synthetic
  M0001/H0001/L0001 naming separate from historical research evidence.

## Local proof and reusable source map

Shell/navigation: `Shell.tsx`, `primitives.tsx`, `tokens.css`, `styles/*`.
Overview/Library: `Overview.tsx`, `Library.tsx`, `RecordingList.tsx`.
Detail/audio: `RecordingDetail.tsx`, `AudioPlayer.tsx`, `usePlayback.ts`,
`SignalChart.tsx`, `signal.ts`. Profile: `Settings.tsx`, `SettingsSections.tsx`,
`AvatarCrop.tsx`, `Identity.tsx`, `preferences.ts`. Sharing: `Sharing.tsx`.
Owl: `PreviewOwl.tsx`, `OwlEyeMaterial.tsx`, `assets/botanical-perch.webp`.
Everything lives under `frontend/src/ux-preview/`; real app remains unchanged.

No preview identity/auth context, `fixtureMedia`, synthetic metrics, closed
@wintercedar lookup, notification mock, export timer or deletion simulation may
reach a live route. All eight fixture Open actions point to one design detail;
that is a prototype boundary, not production navigation logic.

## Route contract after implementation

| Existing route | Frozen destination/behaviour |
|---|---|
| `/app`, `/app/dashboard` | `/app/overview` |
| `/app/recordings` | `/app/library` |
| `/app/results` | `/app/library?status=ready` |
| `/app/processing` | `/app/library?status=processing` |
| `/app/history` | `/app/library` |
| `/app/recordings/:id` | Same recording detail, encompassing permitted job/result states |
| `/app/results/:id`, `/app/processing/:id` | Resolve authorized parent via existing API, then recording detail; denied remains denied |
| `/app/shared`, `/app/review-queue`, `/app/assigned` | `/app/shared`, with existing role/capability checks |
| `/app/reviews/:id`, `/app/review-history` | Preserve review deep links/history access; nest workflow in Shared & assigned, not guessed redirects |
| `/app/profile` | `/app/settings?section=profile` |
| `/app/settings`, `/app/settings?section=...` | Combined six-section settings |
| `/app/recordings/new[/upload\|/record]` | Preserve existing capture/upload paths behind New recording |
| `/app/admin/*`, `/app/help` | Preserve existing server-gated functions; apply frozen shell only |

Primary navigation exactly Overview/Library/Shared & assigned/Insights. Personal
Profile & settings/Help. Administration is capability-gated, never inferred from
a cached client role. Signed-in logo→Overview; public logo→landing.

## L0 — identity/public references, local migration

Extend existing user/entity records; do not replace UID, primary keys or foreign
keys. Add immutable `public_id`; user fields `handle`, `normalized_handle`,
`handle_change_count` default0, `handle_changed_at`, avatar reference where needed.
Use the existing migration system **locally**, with additive nullable/backfill/
uniqueness steps; no production migration in this phase. Backfill missing values
only, never rotate assigned handles/IDs on each login.

Handle: trim/lowercase,3–20, starts a-z, a-z0-9_. only, ends alphanumeric, no
consecutive separators. Reserved list is exact `domain.ts` list; uniqueness is
case-insensitive and enforced transactionally. Initial assignment count0; one
self-service canonical change increments to1; display name remains editable.
Curated safe adjective words: blue/frost/silver/winter/quiet/pine/snow/fern/ivory;
nouns: owl/dragonfly/falcon/finch/robin/heron/otter/fox/cedar/willow. Choose with
cryptographic randomness; retry collision, then append two lower-case unambiguous
symbols while respecting20 chars. No email/PII derivation or numeric userNNN IDs.

Public IDs: USR/REC/JOB/RES/MED/GRT/ASN/EXP + ten crypto-random Crockford Base32
symbols (`0123456789ABCDEFGHJKMNPQRSTVWXYZ`), formatted PREFIX-4-6. Unique index,
bounded collision retry; immutable. IDs are references, not access secrets.
Pass: local migration/duplicate/race/one-change checks; existing authorization
keys unchanged. Stop if migration would rewrite UID or weaken access.

## L1 — shell/navigation

Port frozen shell/primitives, keeping existing live auth/provider/account states.
Frost default, System live OS, Midnight intentional tokens; persisted theme.
224px sidebar (208≤1200),64px header/58mobile,32px horizontal/24px top desktop,
20px mobile. At≤760, bottom quick links + native dialog drawer. No duplicate
top-level lifecycle links. Stop if auth/role guards are bypassed or live routes
can instantiate the synthetic provider.

## L2 — Library and redirects

Use existing authorized recording/job/result APIs. Combine by recording identity,
not one row per result/job. Four filters, title/public-ID search, newest/oldest
sort, six-row desktop pagination and mobile cards. Preserve recorded, queued,
processing, ready, failed; no fake percent or optimistic succeeded result.
Processing filter includes queued and processing, with truthful distinct chips.
Reuse existing durable POST job/idempotency semantics. Apply route table without
fetching an unauthorized original as a redirect prerequisite.

## L3 — detail/media

Bind actual backend-authorized resources to source labels. `api.media(id, signal)`
remains the transport; automatic fetch, no autoplay/manual load, no token URLs.
401 sign-in,403 denied,404 unavailable, no fixture fallback. Abort/revoke/pause
on teardown, logout, resource/access change. Exact Heart-only grants must not
expose Original/Lung/result metadata through UI assumptions. One AudioContext,
one active source; GainNode0–2 default1, compressor threshold−3/knee6/ratio20/
attack.003/release.15 above1 only; keyboard seeking/gain and touch44px.
Desktop three lanes; mobile one lane via source selector linked to analysis.
Stored files and frozen inference remain untouched. Stop on sibling exposure.

## L4 — analysis/Insights

Port actual sample-derived waveform/STFT and `measureSignal` equations/thresholds
unchanged. Bounded180-column display; common absolute analysis amplitude axis,
calibrated magnitude dBFS. Source/plot toggles and MetricCard language are frozen.
Insights uses these same chart/metric primitives and authorized recording counts;
no new chart theme or invented score. Permission-limited inputs stay limited.
No diagnosis, SI-SDR, confidence, accuracy, patient inference or model adaptation.
For large allowed WAVs, move equivalent analysis off main thread if necessary;
verify numeric parity, not a new DSP/preprocessing design.

## L5 — Shared & assigned

Reuse active grants/assignments and existing review submission endpoints. Exact
authenticated handle lookup only: return avatar/display name/@handle and internal
recipient ID for authorized sharing; no emails, UID presentation or directory.
Enforce active/verified recipients, ownership and rate limiting server-side.
Read scopes: default Heart only; Lung only; result details only; explicitly
labelled whole recording. Whole read maps to existing null resource scope; exact
reads never imply siblings. Review assignment remains analyst + explicit original/
result, separate from audio read. Show current scope/expiry/revoke; do not give
Admin blanket audio rights. Revocation blocks future fetch, not already downloads.

## L6 — Profile/settings

Six sections as proof; profile identity and subtle USR ID. Server saves display
name/one-change handle. Avatar PNG/JPEG/WebP≤2MiB, dimensions64–4096, square crop,
512px raster output, validated server-side; no arbitrary SVG. Durable protected
avatar reference, not a persisted Blob URL. Theme/gain are preferences; real
notification capability must exist before a toggle claims to persist server state.
User-safe errors and explicit handle-change allowance, no raw regex/UID/email header.

## L7 — export/unlink/delete, security gate

Keep the exact visual states. Do not connect prototype timers/confirmation to
destructive actions. Before enabling backend lifecycle work, owner must approve
retention/audit, dependency-safe provider unlink and account-removal policy.
Until supported, actions are clearly unavailable, not simulated production success.
Export owns user's account/owned data, not unrelated granted media by default;
durable preparing/ready, protected expiring download, notification with spam/junk
copy, no archive email attachment. Delete requires consequences/export suggestion,
recent Firebase authentication, typed canonical @handle, final destructive confirm;
server verifies all steps. Never delete on client-only confirmation. No production
user deletion/backfill/exports are authorized by the design approval alone.

## L8 — owl arrival and botanical scene, asset gate

Retain approved connected-neck renderer/poses. Green iris display material,
transparent leafy branch, claws contacting wood at desktop/mobile, no owl backdrop.
Whole-window pointer listener, yaw±30/pitch±18, eased settling, cleanup/no idle RAF.
Reduced motion/coarse pointer settled poster. Use `UX_REDESIGN_SPEC.md` exact
six-pose/gutter/anchor and1240ms arrival contract **only after owner approves usable
frames**. Rejected atlases cannot ship. Hard-load document latch, never SPA replay.
If frames remain unavailable, keep the good perched state; do not fake flight.

## L9 — username login, NOT APPROVED

Keep secure email/password + Google. Do not add anonymous handle→email lookup or
quiet Firebase auth proxy. Handle login is a separate security migration requiring
explicit approval and review of enumeration, rate limits, reauthentication,
provider/revocation parity. No fifth login screen is part of this design proof.

## L10 — responsive/accessibility

Prove1440×900,1024px,390×844, Frost/System/Midnight; no overflow or leaf clipping.
Reuse single-player mobile pattern,44px main targets, visible2px focus, labels,
one h1, skip link, dialog return/Escape, reduced motion/transparency. Body14px,
secondary/technical≥12px, no low-contrast helper loopholes. Preload existing fonts;
do not transfer hidden desktop photography on mobile. Contrast/check plots in
both themes, not CSS invert. No production routing/infrastructure changes here.

## L11 — focused browser acceptance

Extend the existing local acceptance flow, not a new huge backend campaign.
Use generated/non-T9 data: real owner capture/upload→Separate→queued/processing→
ready; refreshed persisted result; auto protected fetch; native200% playback;
unauthorized/anonymous/sibling/revoked cases; public-ID search/handle conflict and
one change; theme/reduced motion/mobile keyboard; supported avatar/privacy states.
Mock checks do not replace backend authorization evidence. Save updated seven
screenshots and one focused performance audit. One broader local regression only
after the full milestone. Never use T9/patient production audio.

## L12 — review/checkpoint/STOP

Five axes: correctness/readability/architecture/security/performance. Fix Critical
and Important, not endless cosmetic suggestions. Verify normal build has no
preview fixtures/providers. Commit/push meaningful changes as ASHRAF-2004 to
existing branches/PRs; synchronize FYP2/PAUSE honestly. Report local capability
versus pending lifecycle/auth/assets. Stop before deployment. Any production
migration, identity backfill, rollout or new security architecture needs separate
owner authorization; frozen ML/T9/Axora never enter this work.
