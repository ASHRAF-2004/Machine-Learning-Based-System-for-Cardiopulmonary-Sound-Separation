# StethoFuse UX direction: Frost Studio

Status: **FROST STUDIO v1.1 / polish-v1 — OWNER APPROVED**, 30 September 2026.
The owner explicitly approved the polished previews and authorized local core
integration only: real upload/capture, Overview/Library/lifecycle, protected
playback and per-recording analysis. No redesign or production deployment.
The later1October continuation implements LOCAL identity/profile foundations only;
account/data services, global Insights and genuine flight remain pending.
Production backfill/deployment remain separately authorized gates.

1 October owner feedback additionally authorizes the bounded LOCAL exact-handle
sharing refinement in `LOCAL_SHARING_REFINEMENT.md`. Compact key technical facts
precede full receipts under See more / See less. Sharing confirms a real name/
@handle, not an entered application ID; only 3 active permissions appear initially,
with additional/history entries disclosed. The existing backend authorization,
UID identity and approved Frost visual system remain unchanged. No production
or full account-management milestone is implied.

The bounded core is now **implemented/tested locally** in `frontend/src/frost/`;
execution and intentional real-data transitions are in `FROST_CORE_INTEGRATION.md`.
The design preview remains unchanged. Public IDs/handles are not synthesized for
real users in the frontend; the LOCAL identity foundation now allocates actual
metadata transactionally in the backend (`LOCAL_IDENTITY_FOUNDATION.md`). Existing
functional account/review/Admin routes are preserved, not
replaced with their preview prototypes. Owner review precedes any deployment.

## v1.1 polish delta

Only shared glass depth, iris chroma, the Overview rail, Appearance copy, playback
boost discoverability and preview-banner ownership changed. Typography, palette,
IA, owl/perch registration, tracking, audio graph and protected-media contract
remain the approved v1 baseline. Evidence: `UX_DESIGN_REVIEW.md`, ignored
`frontend/output/playwright/ux-review/polish-v1/`. No new flight assets.

## Objective and scope

Make private recording capture, separation and review feel like one coherent
audio workspace. Prove Overview, Library, ready Recording detail, and Profile &
settings with reusable React components, functioning synthetic audio, real signal
measurements, two themes and responsive screenshots. No medical interpretation.

Assumptions: this is the existing React web application; the backend remains
authoritative for Firebase UID, roles, account state and every resource grant.
All preview identities and public IDs are explicitly fictional/local. No live
account or production media is used. Existing model, auth and approved owl
renderer/pose sources stay unchanged. The authenticated logo goes to Overview,
not the public landing page.

## Capability boundaries and build order

| Module | Responsibility | Depends on |
|---|---|---|
| visual-foundation | Tokens, shell, primitives, local preview entry | Existing fonts/logo/assets |
| recording-workspace | Overview, Library, lifecycle and detail presentation | visual-foundation |
| audio-review | Auto-load media, playback gain and objective analysis | visual-foundation, existing API contract |
| personal-settings | Identity/appearance/audio/privacy flow prototypes | visual-foundation |
| review-evidence | Screenshots, focused checks, freeze and Luna handoff | All four preview modules |

Build in that order. These are presentation modules, not new production services.

## Product principles

1. Recording is the primary object. Processing and result are states/details.
2. One dominant action per context, familiar controls, progressive disclosure.
3. Title first, friendly public ID second. No UUIDs or email headers.
4. Glass is a selective material, not an excuse for low contrast.
5. Measured signal properties are not model accuracy or clinical diagnosis.
6. Backend permission errors are explicit. Never substitute demo media in live mode.

## Information architecture

Approved full IA: Overview, Library, Shared & assigned, Insights. Current core
navigation omits global Insights until implemented; no dead placeholder item.
Personal: Profile & settings, Help. Administration only from server role.
Library filters: All, Ready, Processing, Shared. Recorded/failed remain in All.
Recorded → Queued → Processing → Ready, or Failed. Never invent percent complete
when the worker reports only a state. Original remains safe on failure.

Application core routes: `/app/overview`, `/app/library`,
`/app/recordings/:id`, `/app/shared`, `/app/insights`, `/app/settings?section=...`.
Old `/app/dashboard` → Overview; recordings list → Library; results list →
Library?filter=ready; processing/history lists → Library?filter=processing/all.
Job detail resolves its owner-authorized parent recording through the existing API.
Result detail stays directly result-authorized, with no owner-only job or original
recording prerequisite. Keep deep links and exact-resource permissions; never infer
access to the original or sibling outputs from a result grant.

## Frozen visual contract, version 1.1

Name: Frost Studio. Dials: variance 5, motion 3, density 6. Calm professional
composition, not a marketing hero or ornamental analytics dashboard.

| Token | Frost | Midnight |
|---|---|---|
| background | #eef2ed | #101e21 |
| glass-1 | rgba(250,252,249,.70) | rgba(29,45,48,.82) |
| glass-2 | #f4f7f3 | #223438 |
| glass-strong | rgba(251,252,249,.94) | rgba(27,43,47,.96) |
| glass-highlight | rgba(255,255,255,.75) | rgba(230,247,239,.10) |
| control-surface | #fbfcf9 | #1b2b2f |
| workspace-veil | rgba(238,242,237,.90) | rgba(16,30,33,.94) |
| glass-border | #d8e1d9 | #405458 |
| control-border | #7d9082 | #6f8586 |
| text-primary | #19372f | #edf5ee |
| text-secondary | #53665c | #b7c9c4 |
| accent | #245d4c | #9bd5ba |
| accent-hover | #194c3d | #b7e2cf |
| on-accent | #ffffff | #163329 |
| success | #28654b | #9bd5ba |
| warning | #815819 | #edc485 |
| danger | #a03e49 | #f1a0a8 |
| focus | #416ba8 | #a9c9ff |

Editorial: existing self-hosted Cormorant Garamond. Operational: existing
self-hosted Manrope. Major headings 44–48/1.05 desktop, 36–39 mobile. Section
headings 26–30. Body14–15/1.5; helper12–13, never tiny low-contrast paragraphs.
Spacing scale4/8/12/16/20/24/32/40/48. Panels radius16, controls10, chips fully
rounded. Sidebar224 (208 below1200), header64 (58 mobile), desktop gutters32
horizontally and24 above content, content max1200. Mobile20.
Ordinary panels allow restrained background bleed; strong audio/attention panels
remain almost opaque. A shared inset upper-edge highlight and soft shadow define
depth. Inputs/secondary controls remain solid on `control-surface`.
Blur20px navigation,12px selected panels; no nested blurred cards. Shadows soft
pine, not neon. Reduced transparency uses opaque surfaces.

Buttons: Primary pine, Secondary bordered surface, Ghost text, Danger outlined
red, Icon named and44px minimum. Hover elevation1px, press0; no bouncing.
Micro motion160ms, panels240ms, easing cubic-bezier(.2,.7,.2,1).
Reduced motion removes arrival/transform/continuous motion.

## Four screen contracts

### Overview

Identity greeting and one New recording CTA. One compact unfinished-recording
strip with three explicit lifecycle steps; no fake completion percentage.
Recent recordings occupy the main column; one shared attention item and a small
textual activity summary occupy one strong-glass side rail, separated by a20px
gap and a rule. At tablet widths the same sections sit side by side; on mobile
they follow recent recordings. Keep the two existing facts, no extra widgets.
Approved owl is a restrained
editorial brand moment, not a giant empty-space filler.

### Library

Search title/public recording ID, four small filters, one list/table hybrid.
Rows show title, publicID/copy, date/duration, lifecycle status, private/shared
state and Open. No bulk checkboxes or repeated primary buttons without a need.
Mobile cards preserve title/status/action; secondary details wrap. Six desktop
rows per page with previous/next and total count. Search/filter reset pagination.

### Ready recording detail

Title, secondary ID/date/Ready/private badge and Share. Three custom lanes
Original/Heart/Lung with automatic loading and no autoplay. Play/pause, waveform
seek, time/duration, per-source semantic colour and persisted0–200% gain.
Keep the current percentage, visible0/100/200% scale and100% midpoint tick.
The above100% half has a subtle accent tint; a reserved-width Boost label becomes
visible above100% without resizing the control. Shared helper:
"Playback volume up to 200%. Saved files stay unchanged."
Accessible source-labelled sliders expose e.g. "150 percent, boost enabled".
One lane plays at a time. Mobile has a source selector and one visible player,
linked to analysis; desktop shows all three lanes. Space activates a focused
play button; arrows move
native seek/gain sliders. Download only where existing backend capability permits.

Analysis uses actual decoded local WAV samples: waveform or STFT spectrogram,
source tabs, RMS/peak/crest and transparent clipping/low-level checks. Spectrogram
uses Hann256/hop64 at4kHz,0–2kHz, with a calibrated displayed magnitude scale.
These display parameters are NOT model preprocessing. Source-independent
thresholds must be documented before presenting Good/Review labels.
Share-by-handle prototype uses a closed fixture lookup, exact named scope and
access explanation. Production lookup requires authenticated rate-limited exact
handle search, no browse-all-user directory and no emails/UIDs. Technical
provenance stays collapsed and cannot invent job-specific hashes or accuracy.

### Profile & settings

Six section navigation: Profile, Appearance, Audio, Notifications, Privacy &
data, Security. Profile identity + editable display name + one handle change.
Appearance heading is exactly "Appearance", supported by "Choose how StethoFuse
looks on this device." System/Frost/Midnight and preference behavior are unchanged;
audio gain and grouped notification controls retain the existing structure.
Avatar upload/crop accepts PNG/JPEG/WebP, <=2MiB and bounded decoded dimensions.
Export prototype: Prepare → Preparing → Ready → Download explanation, with
spam/junk note. No fabricated archive or email sent. Delete prototype explicitly
suggests export, lists consequences, requires recent authentication then typed
@handle and final destructive confirmation; no real deletion is implemented.

## Identity and authorization design

Firebase UID remains immutable backend security ID. Public handle canonical
lowercase,3–20 characters, starts letter, a-z0-9_. only, no trailing/repeated
separators; reserved admin/administrator/root/system/support/stethofuse/official/
security/api/help/staff. Curated safe words, no email/PII-derived assignment;
collision retry. Automatic assignment count0; one self-service change with
handle/normalized_handle/change_count/changed_at. Server enforces uniqueness and
change count transactionally. IDs use prefix +10 random Crockford Base32 symbols
formatted4-6, immutable unique, generated server-side with collision retry;
not access secrets. No production migration in this sprint.

Login stays Email + password/Google. Do NOT add anonymous handle→email lookup.
Username login is a separately approved security migration, not a fake visual
promise. Handles can be used for authenticated sharing before login changes.

## Media and signal implementation contract

Reuse `createApiClient().media(resource.id, AbortSignal)`, protected `/api/media/:id`.
Do not use response URLs, query tokens, public storage or permission heuristics.
Fixture adapter serves deterministic generated15s/4kHz WAVs named M0001.wav,
H0001.wav,L0001.wav. These are not actual model outputs or research evidence.
Abort pending loads, revoke Blob URLs, stop/disconnect on unmount, session change
or access loss. 401 sign-in state,403 denied state,404 unavailable, retry only
for recoverable transport errors. GainNode controls0–2; above1 route through
DynamicsCompressor(-3dB threshold, knee6, ratio20, attack.003, release.15).
This reduces clipping risk, is not a guaranteed true-peak limiter; stored audio
unchanged. Start AudioContext on user gesture, not page load.

## Owl boundary

Keep existing approved `Owl.tsx`, `owlSurface.ts` and connected-neck assets.
Arrival requires genuine wing-up/down/approach/braking/landing/settle frames.
If the current head-pose set lacks those, do NOT translate a static poster and
claim flight. Document an asset-gated entrance design, preserve current follow
behaviour in the local preview, and require owner-approved new frames before
Luna wires a single hard-load arrival. Never replay arrival on SPA navigation.

## Responsive and accessible

Desktop1440×900 and normal1024 laptop. At<=760, sidebar becomes accessible mobile
navigation drawer and bottom quick links; focus trap/return/Escape/inert backdrop.
Overview and detail390×844 must not overflow. Detail uses a single-player source
selector and stacked analysis; important touch controls>=44px. Midnight has
intentional green-charcoal materials, visible
semantic colours and chart palette, not inversion. System tracks OS live.
One h1, labelled controls, semantic table/list, visible focus, skip link, dialog
focus management, polite loading/state messages,4.5:1 ordinary text contrast.

## Structure, commands and verification

Existing React19/TypeScript/Vite/Phosphor; no new frontend dependency. Isolated
`frontend/ux-preview.html` + `src/ux-preview/`, excluded from production entry.
`npx vite --config ux-preview.vite.config.ts` then
`http://127.0.0.1:4193/ux-preview.html#overview`. Preview entry must
fail closed in a normal production build. Build `npm run build`; focused browser
checks only. Source uses named typed components and token CSS, e.g.
`<GlassPanel><AudioPlayer source={source} loadMedia={provider.media}/></GlassPanel>`.
Screenshot → inspect → critique → fix → screenshot, max2–3 iterations/screen.

Always: preserve unrelated edits, local-only fixtures, inspect screenshots,
keyboard/contrast/responsive checks, honest evidence, verify Git identity.
Ask first: full-app implementation, production rollout, identity migration,
new owl assets approval or auth security migration. Never: train/T9/production
mutation, new diagnosis or invented confidence/accuracy, broaden grants, Axora.

Success: seven final previews, functioning custom player/analysis, intentional
Frost/Midnight, focused checks/build, five-axis review, frozen exact tokens and
Luna phases. Owner visual approval remains mandatory before implementation
propagation. The freeze and measured review deltas are in `UX_DESIGN_REVIEW.md`.

## Exact final implementation rules

`frontend/src/ux-preview/tokens.css` and the six stylesheets imported by
`preview.css` are authoritative; do not reinterpret component spacing or colours.
Original/Heart/Lung colours are slate/rose/pine. Frost values are
#597588/#9c5b69/#326d59; Midnight values are #9dbdcc/#dda9b2/#99ceb8.
Chart colours are retained on a charcoal field in both themes. Shadow levels are
`0 8px 28px rgba(29,55,41,.06)` and `0 16px 48px rgba(20,43,32,.14)`;
Midnight substitutes black alpha. Sidebar is deep pine with a restrained winter
texture, not another floating card.

Default theme is **Frost**, default gain100%. System follows OS changes live.
Persist preferences; do not store private audio, auth tokens, or production
identity in the preview's `sf-design-*` namespace. Help/technical labels are at
least12px; primary operational text14px. Font preloading avoids late font swaps.
Native dialogs contain/return focus and support Escape; focus outline2px,
offset4px. Reduced motion removes transforms and owl tracking; reduced
transparency replaces glass with opaque surfaces. Mobile omits the large,
otherwise-hidden background photograph without changing the Frost colour.

Overview keeps one New recording CTA, unfinished-work strip, four recent rows,
one shared attention item and two textual activity facts. Library keeps exactly
four filters, title/public-ID search, one sort and one row action. Ready detail
puts audio before analysis and keeps technical provenance collapsed. Settings
uses six sections; Profile also previews appearance/audio, while Privacy & data
has a distinct danger zone and content-sized surface, not forced empty height.

The player loads through the typed protected-media contract, never a public URL.
One gesture-created AudioContext is reused; GainNode0–2 is shared across sources.
Above100%, route through the documented compressor; at/below100%, bypass it.
No gain modifies stored WAV bytes. Permission denial never triggers fixture
fallback. In live implementation, the backend resource list—not client roles—
determines which lanes can attempt fetching. On logout/access loss/resource
change, stop nodes, abort loads and revoke URLs. Already downloaded files cannot
be recalled by revocation; never claim otherwise.

Display analysis is independent of frozen inference. Exact measurements:
RMS `20log10(max(1e-8,sqrt(mean(x²))))`; peak `20log10(max(1e-8,max|x|))`;
crest=peak−RMS; DC=mean(x); clipping=count(|x|>=.999); near-silence=fraction of
250ms segments with RMS<−50dBFS; low-level review=whole-source RMS<−35dBFS.
Thresholds are technical display rules, not clinical validation. No clipping
means zero threshold crossings, not proof the original acquisition never clipped.
The seek waveform is shape-normalized; the analysis waveform uses absolute±1.
STFT: periodic Hann256/hop64,129 bins at4kHz, single-sided magnitude
`abs(FFT)/sum(window)`, doubled for non-DC/non-Nyquist bins; display−80…−20dBFS.
At most180 uniformly selected frames cover the complete file. These selected
columns are a bounded visual summary, not a full-resolution diagnostic transform.

The four preview routes are `#overview`, `#library`, `#recording`, `#settings`.
All list Open actions deliberately demonstrate the **one** representative ready
recording; eight fixture rows do not imply eight completed detail screens.
`App.tsx` owns both preview safety labels and passes them through the optional
`environmentNotice` slot. `PreviewShell` contains no unconditional preview copy.
Do not port fixture contexts or prototype providers into the real product shell.
Shared & assigned, Insights and Help remain navigation/interaction boundaries,
not newly implemented fifth/sixth screens. Capture/upload, real grants,
notifications, avatar storage, export/delete and production identity remain
unwired prototypes. Name/handle/theme/gain persist locally; cropped avatar lasts
for the preview session only and revokes its URL when replaced/unmounted.

Current backend grants remain unchanged: owner creates grants for active,
verified recipients; read without a resource is whole-recording access; exact
Heart/Lung/result read grants do not confer sibling access; review requires an
Audio Analyst and explicit original/result resource. Admin alone is not a grant.
Share defaults to Heart only. Whole-recording access is explicitly labelled and
never silently selected. Handle resolution must return the existing recipient
identifier only to authorized authenticated callers.

No username login is approved: retain email/password and Google. Export/delete/
provider unlink backend capabilities need separate lifecycle/security gates
before destructive actions become active. Prototype success does not imply
those services already exist.

## Botanical owl and arrival asset gate

The owner added a botanical perch, green irises and whole-page cursor response
on30 September. Overview uses a transparent natural branch with small green
leaves and no separate landscape behind the owl. Desktop/mobile close-ups show
claws meeting the wood without a visible gap. Approved renderer/pose textures
are unchanged; a selective display filter shifts blue iris chroma into shaded
pine green. The v1.1 iris matrix blends12% toward the material's own luminance,
reducing chroma without a whole-owl filter or changing pupil/highlights/mask.
Global `window.pointermove` works over sidebar and content, with
bounded yaw±30/pitch±18 and eased settling. No continuous idle loop.

Two generated six-pose flight atlases were rejected: wings crossed cell bounds
and scale/centres varied. A green-eye generated image is a colour reference only,
not a replacement for connected-neck textures. The tracked transparent
`assets/botanical-perch.webp` is the new scene material.

Required arrival assets: six genuine transparent poses, each512×512 with32px
clear gutter, stable character scale and documented body/head/foot anchors:
wing up, wing down, approach/glide, braking, landing, settle. No clipped wing
tips, baked backdrop, different owl identity or disconnected head/body.
Landing must meet existing perch/claw registration at every breakpoint.
Owner approves frames before use. Do not translate a static poster as flight
or integrate the rejected atlases.

Choreography design:0–450ms two wing phases approaching from upper left;
450–700ms glide;700–900ms braking above perch;900–1080ms foot contact;
1080–1240ms small settle;1250ms onward existing connected-neck follow. Positions
derive from the perch anchor, not fixed screen pixels. One root-document latch:
only initial load/refresh of an owl-bearing screen may play; later SPA visits
show the perched owl directly. Interrupted arrival never replays. Reduced
motion/coarse-pointer users get a settled poster without tracking or flight.

## Freeze and approval boundary

Internally reviewed four screens + Frost/Midnight + mobile + owl contact proof.
The owner approved the direction; final v1.1 polish review is outstanding.
Owl flight remains **ASSET-GATED — NOT IMPLEMENTED**. `UX_LUNA_HANDOFF.md` is a prepared
contract, not permission to start Luna or the remaining app. Production and
ML evaluation remain completely unchanged.
