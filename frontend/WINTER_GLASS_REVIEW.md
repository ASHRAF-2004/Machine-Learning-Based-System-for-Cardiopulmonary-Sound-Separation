# StethoFuse · winter-glass frontend

Implemented 24 September 2026 in the existing React frontend. This is a functional **local demonstration**, not deployed software or connected authentication/ML.

## Open the experience

- Local preview: <http://127.0.0.1:4180/app/dashboard>
- Choose a fictional account: <http://127.0.0.1:4180/login#demo-personas>
- Amina / Daniel: separate staff collections. Sofia: assigned analyst reviews. Elias: administrative metadata plus an empty personal collection.
- Run: `cd /home/ashraf/Documents/StethoFuse/implementation/frontend && npm run dev`
- Route inventory: [FRONTEND_ROUTE_MAP.md](FRONTEND_ROUTE_MAP.md). Service boundaries: [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md).

## Visual direction and implementation

Read all 20 supplied images by their visible content, not the sometimes-mismatched filenames. Adapted their large editorial serif, pale-blue scenery, transparent white glass rims, soft tinted shadows, precise sans-serif controls and restrained decorative details. The existing Cormorant/Manrope fonts and approved logo remain. The native-generated design concept informed composition; its fictional counts, progress percentage and inappropriate role links were **not** implemented.

The shared system was established before page delegation: `DESIGN_SYSTEM.md`, `src/winter-glass.css`, `src/components/ui.tsx` and `WinterArt.tsx`. Separate workers owned the workspace and account page pairs; the coordinator integrated them and handled public/auth/utility pages and final fixes. No separate themes or duplicate shared shells were introduced.

- Staff/personal dashboard: signal introduction, compact linked counts, recent recordings and current-work panel.
- Recordings/results/processing/history/sharing: scenic headings, frosted filters, readable milky tables, contextual illustrated empty states.
- Upload/device/detail/review: focused recording controls, structured metadata, provenance and timestamped notes; same visual family without decoration over waveforms.
- Administration: directory/filter groups, role overview, metadata-only tables, expert/provenance rows, audit trail and system integration boundaries.
- All six settings sections, profile, notifications and Help share the glass navigation/content hierarchy.
- Sign-in, signup/recovery/provider states, privacy/terms and 403/404/500/offline/maintenance screens now carry the same winter materials. Landing hero composition and owl interaction remain intact.
- Separate generated feather and frosted-folder illustrations, plus a lightweight decorative SVG signal. No replacement owl/logo, fake diagnostic visualizations or fake separation-quality claims.

Glass is lighter around scenery and more opaque behind text/data. Narrow layouts disable panel blur; high-contrast/reduced-transparency fallbacks use solid surfaces. Tables have keyboard-focusable scroll regions. Public CTAs remain **Get started / Sign in**; **New recording** stays inside the workspace.

## Functional corrections found during review

1. Shared recipients can access explicitly shared audio/results, but cannot enter owner-only processing-job details or navigate to owner job controls.
2. Reassignment revokes the previous grant and creates a fresh pending assignment ID. It preserves the old author/review, sends new links and never transfers prior private notes to the replacement reviewer. Same-recipient/duplicate grants are rejected.
3. Mobile processing rows now use an icon/text/action grid, with status on a second line. Text width at 360px increased from 56px to 199px.
4. Mobile user search spans the filter width (324px at a 390px viewport) instead of sharing an excessively narrow row.
5. Actual composited-background sampling caught faint small text over mountains/glass; headers/auth text were darkened and the auth footer received a translucent backing.

## Fresh verification

Chrome 151.0.7922.137 on Ubuntu; automated desktop/tablet/mobile **viewport emulation**, not physical-device testing. All results are under `evidence/winter-glass/`, separate from historical runs.

| Suite | Passed | Failed |
|---|---:|---:|
| Public/auth/recovery | 42 | 0 |
| Recording/processing/review workflows | 16 | 0 |
| Account-specific drafts | 6 | 0 |
| Shared state, revocation and keyboard behavior | 13 | 0 |
| Analyst responsive workflows | 13 | 0 |
| Normal production auth/demo boundary | 6 | 0 |
| General integration and approved owl regression | 29 | 0 |
| Admin/settings/reassignment/privacy | 29 | 0 |
| **Total functional assertions** | **154** | **0** |

Integration also checked all 28 expected route paths/headings, 1920/768/390/360 viewport containment, real continuous owl source loading/input, no asset requests during pointer movement, offscreen pause, reduced motion and missing-field poster fallback. No runtime/resource errors in the final integration/admin runs. Build/typecheck passes.

Earlier test-only failures are preserved in `integration-attempt-1` and `admin-attempt-1`: a backdrop click under the open drawer and an obsolete attempt to select the intentionally excluded current analyst. Neither was concealed as an app pass; the assertions were corrected to the actual UI and the full suites rerun.

### Visual review is separate

Desktop dashboard, recordings, authentication, utility and settings captures were opened directly; the live in-app dashboard was also inspected. Workers opened 13 workspace and 16 account/admin captures, including all settings subsections and narrow screens. Their initial findings remain in `visual-workspace/REVIEW.md` and `visual-account/REVIEW.md`; both minor mobile findings were subsequently fixed and re-captured in `mobile-corrections/`. Final mobile captures were opened and checked by the coordinator.

Actual rendered-background text sampling: **54 measurements, zero failures** after correction. `quality/contrast.json` uses glyph-hidden screenshot pixels within visible text rectangles (including glass/gradient/image composition); thresholds 4.5:1 ordinary text and 3:1 large text. This is a bounded sample, **not a full WCAG certification**. The earlier nine sampled failures remain in `quality-before-contrast/`.

### Local performance observations

`node tests/winter-quality.mjs` builds a separate production-optimized **demo** bundle and serves it on a temporary loopback port. Fresh isolated contexts, DPR1, no throttling, identity HTTP encoding; no production deployment change. One sample each, not field percentiles or hardware-GPU validation.

| Screen | FCP / LCP | CLS | Encoded response bodies | Scrolling frame median / p95 |
|---|---:|---:|---:|---:|
| Dashboard, 1440×1000 | 92 / 376ms | .0303 | 896,137B | 16.7 / 16.7ms |
| Ensemble, 1440×1000 | 84 / 372ms | .0351 | 924,272B | 16.7 / 33.3ms |
| Review, 390×844 emulation | 56 / 352ms | .0947 | 720,752B | 16.7 / 16.8ms |
| Sign-in, 1440×1000 | 364 / 364ms | .00024 | 894,713B | 16.7 / 16.8ms |

Three-second scripted scroll on the actual rendered pages; these are frame intervals, not guaranteed interaction FPS. Ensemble has observable dropped frames at p95. Resource transfer bytes, individual downloads, canvas sizes and errors are in `quality/metrics.json`. Encoded response bodies are not decoded image/GPU memory. Real mobile/network-constrained performance remains untested. Nothing here promises a 60fps result on every device.

## Artwork and owl preservation

- All 24 identity/controller/Canvas/source/brand checks pass: `python3 tools/verify_winter_preservation.py` → `preservation.json`.
- User-approved 18-view connected-neck field is now the default selector; no renderer-math, pointer-controller or source-image changes. A development-only legacy comparison is still available.
- Existing source-field payload: 3,650,100 bytes including body; decoded source RGBA 75,362,400 bytes plus other buffers. Mobile/coarse-pointer and reduced-motion users retain a static poster. No bulk frame processing performed.
- New support art: combined 1× WebP 37,042B, versus 3,142,728B PNG sources; combined 2× 115,704B. Separate lazy responsive copies, preserved transparency. Both were inspected directly and on the UI.
- Full prompts/sources: `assets/winter-glass/`; reproducible optimization: `tools/optimize_winter_art.py`; details: [ASSET_OPTIMIZATION.md](ASSET_OPTIMIZATION.md).

## Representative actual browser captures

- [Dashboard](evidence/winter-glass/quality/dashboard-desktop.png)
- [Ensemble configuration](evidence/winter-glass/quality/ensemble-desktop.png)
- [Sign-in](evidence/winter-glass/quality/login-desktop.png)
- [System preferences](evidence/winter-glass/visual-account/system-settings-1440.png)
- [Appearance settings](evidence/winter-glass/visual-account/settings-appearance-1440.png)
- [Recording detail, mobile corrected](evidence/winter-glass/mobile-corrections/recording-360.png)
- [User directory, mobile corrected](evidence/winter-glass/mobile-corrections/users-390.png)
- [Analyst review, mobile](evidence/winter-glass/quality/review-mobile.png)
- [Private access](evidence/winter-glass/visual/403.png)

## What is real, mocked and unchanged

Real frontend: routing, filters/forms, local WAV validation, synthetic audio playback/visualization, fictional account isolation and persistence, assignments/revocation, local review state, responsive/keyboard handling, loading/fallback states.

Mocked: identities/authentication, device capture, processing jobs/results, notifications and administration. No real emails, passwords/tokens in local storage, private audio uploads, ML inference or claims of clinical/ensemble superiority. Firebase/FastAPI adapters remain documented integration boundaries; backend authorization is required before live use.

Untouched: working backend/training/evaluation code, original website artwork, registered project title, DNS/domain, real authentication, deployment. The additive `frontend/` directory remains the inherited untracked git work; no resets/stashes/commits or deletion of unrelated edits.

Scoped reversible checkpoint: `evidence/winter-glass/checkpoint/frontend-before.tar.gz`. No generation, model, asset-processing or test jobs remain running. Only the local development preview is left available for review.
