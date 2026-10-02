# Homepage polish · 25 September 2026

Reference: `/home/ashraf/Downloads/ChatGPT Image Sep 25, 2026, 12_08_55 AM.png`.

## Implemented

- Removed the homepage header background, dividing line and backdrop blur. The logo and navigation sit directly over the original scene. Reduced-transparency mode does not reintroduce the strip.
- Replaced the headline's inline line break with two controlled block lines. Tighter baseline spacing preserves the italic descender and feather-gray treatment. Responsive type keeps “signals within.” together at 320px.
- Larger frosted CTA controls with translucent blue fills, restrained highlights, inner edges, tinted shadows and visible keyboard focus. No extra animation or full-width glass sheet.
- Increased desktop supporting-copy readability. Existing lower-page glass panels, live links, FAQs and all auth/workspace screens remain intact.

Design-skill application: preserve-mode refinement using the supplied precise reference rather than new concept generation. Calm density 3 / variance 3 / additional motion 2; existing approved owl motion unchanged. Native CSS glass approximation, no new library or media assets.

## Verification

- `npm run build`: PASS.
- `node tests/home-polish.mjs`: five viewport cases PASS (1672×941, 1366×768, 768×1024, 390×844, 320×740). Includes transparent-header styles, overflow, single-line italic phrase, CTA visibility, keyboard order/focus, login/register navigation, section links, FAQ, and emulated reduced transparency.
- Existing focused motion suite: 6 PASS. Actual automated mouse circle changed yaw and pitch; reduced-motion and touch fallbacks retained. No runtime/resource errors reported.
- Login screenshot at 1536×1024 was byte-identical before/after. Six protected source/asset hashes unchanged; motion suite also verified its ten protected hashes.
- Visually inspected final desktop, laptop, tablet, 390px and revised 320px screenshots, plus the running in-app homepage. Corrected the initially observed 320px third-line wrap before final verification.

Browser tests used local Chrome151, DPR1, emulated widths/touch; not physical-device testing or a full accessibility/performance certification. Visual approval remains the user's decision.

## Evidence and scope

`output/playwright/home-polish/` contains `checkpoint/`, `before/`, `after/`, `responsive/` and `motion/`. Final responsive PNGs and results are in `responsive/`; unchanged-login comparison in `after/metrics.json`.

Application edits: only Welcome headline markup in `src/pages/PublicPages.tsx` and homepage-scoped rules in `src/pages/public-reference.css`. New regression script: `tests/home-polish.mjs`.

Owl controller/renderers, approved assets, auth behavior, backend/ML and workspace pages unchanged. No installation, image generation, service changes or deployment. Preview remains `http://127.0.0.1:4180/`.
