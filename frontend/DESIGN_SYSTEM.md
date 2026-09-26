# Shared StethoFuse visual contract

## Current: literal screenshot matching, 2026-09-24

The user rejected the interpretation below and explicitly requested the same owl and assets as the supplied20 images. This section supersedes the previous styling/asset rules; safety, role and data boundaries remain.

- Workspace art now uses the actual decorative pixels in the supplied reference images, framed by explicit SVG clip paths in `ReferenceArt.tsx`. This is not a screenshot used instead of a functioning page. Forms, tables, headings, navigation and actions remain semantic React/HTML.
- Exact standalone artwork was not found in the bounded project/download audit. Lossless full-image WebP atlases preserve the source pixels. The mountain scenery hidden by reference UI is a documented generated reconstruction, not a recovered original. Do not misrepresent it as pixel-identical.
- The pictured round snowy owl is a static workspace illustration, separate from the unchanged approved animated landing owl. Do not replace or regenerate landing frames/controllers.
- Native reference measurement:240px sidebar,58px topbar,32px demo strip,30px content gutters; route-specific headers and panel proportions. Shared final tokens/rules are in `src/reference-match.css`, loaded after the previous styling. Existing Cormorant Garamond provides the editorial headings; Arial/Helvetica provides the compact UI. The flattened images do not establish an exact original font file.
- Reuse the same source owl, folder, feather, forest and signal artworks. Do not reintroduce the independently generated winter icons from the previous interpretation. Preserve contrast, mobile overflow containment, keyboard controls and reduced-motion handling.
- Asset provenance: `assets/reference-match/manifest.json`; reproducible format conversion: `tools/prepare_reference_art.py`; review and limitations: `REFERENCE_MATCH_REVIEW.md`.

## Previous interpretation (rejected visually; kept as history)

## Approved continuation: winter glass, 2026-09-24

The user explicitly approved the owl animation and authorized frontend work. Preserve the approved18-view neck-candidate without altering its motion/artwork. Promote that existing selection to the normal preview; no new owl experiments. The historical opaque-workspace direction below is superseded by the supplied20 winter-glass reference images.

Design read: preserve-brand redesign of a research application, using an editorial winter-glass aesthetic, not a generic dashboard. Variance5, motion2 (working controls only), density5. Keep the approved light theme, logo, Cormorant Garamond serif / Manrope sans pair. User references override skill defaults against glass or serif dashboards. No redesign of landing hero composition. Native CSS with existing React/Phosphor components; no framework or UI-kit migration.

Visual extraction: references use a240px sidebar,64px topbar,32px workspace gutters,48-56px serif page titles,26-32px serif panel titles,13-14px UI text,44px controls. Glass has a white1px rim, pale blue depth, restrained tinted shadow and snowy scenery showing through; text/data rows have a stronger milky backing. Avoid the references' pale low-contrast text, decorative health claims, fake percentages and incorrect role menus. Preserve existing copy, permissions and fixture values.

Shared tokens live in `src/winter-glass.css`: ink#17344e, secondary#4b6680, paleice#e9f3fc, translucent white surfaces. Radius16px panels,10px inputs/buttons, circular icon medallions. Sidebar/nav may blur14px; panel blur8px, never nested multiple heavy full-screen filters. Static existing background with a readable white veil. Solid-fill fallback for reduced transparency/high contrast and lower-cost mobile styling.

Shared components remain coordinator-owned: Shell, ui, styles, winter-glass.css, WinterArt.tsx. `PageHeading` supplies scenic framing and a decorative static approved owl or feather by route; no per-page duplicate heroes. `Empty` gets reusable transparent collection art. `WinterArt` provides feather/collection/signal decorative assets with empty alt and pointer-events:none. `WinterNote` may provide one concise contextual note, never a diagnostic claim. Tables stay semantic and horizontally contained; do not hide data columns on mobile.

Generated concept: `assets/winter-glass/dashboard-concept.png`. Visual hierarchy: scenic header, broad signal introduction, slim counts, readable recent-recordings table plus narrower active-work panel. Do NOT copy its fictional42% progress, mislabeled staff admin menu or invented clinical copy. Supporting artwork: `/assets/winter/feather-240.webp` and480, `/assets/winter/collection-360.webp` and720. Reuse unchanged `/assets/background-1800.webp`, `/assets/background-800.webp`, `/assets/owl-poster-420.webp`, `/assets/logo.svg`. Do not crop the supplied dashboard screenshots into production artwork.

Page ownership: coordinator owns shared system/public pages, store fixes and integration; workspace worker owns WorkspacePages.tsx + workspace-pages.css; account worker owns AccountPages.tsx + account-pages.css. Workers must not edit shell/global CSS/brand/owl/data. Use existing components, no independent themes, no new dependencies. Preserve routes/form labels and functional flows. Any necessary behavior fixes must be explicitly scoped and tested.

## Historical contract (superseded styling, retained safety boundaries)

Preserve the supplied snowy background, original owl, existing animation and unchanged logo. No replacement identity or new generated artwork. Use local approved Manrope for UI and Cormorant Garamond for expressive headings. Ink #26394b, secondary #617588, winter #edf5fb, snow #fbfdff, line #d9e3eb. Public surfaces are editorial and spacious. Workspaces are quiet, opaque, precise and readable. No heavy navy or green theme. Status accents are small and always accompanied by text.

One shell, one component library: src/components/ui.tsx and src/styles.css are coordinator-owned. Pages use PageHeading, Button, Badge, Notice, Empty, Field, Modal, Tabs and Table. Use Phosphor icons only, 18–22px with 1.5px-equivalent regular weight. Interface numbers/IDs use tabular numerals. Desktop sidebar 240px; workspace max-width 1240px; mobile drawer below 900px. Fields and controls minimum 44px high. Focus ring visible. Opaque tables with subtle row separators; do not turn every sentence into a card.

All pages consume src/data/store.tsx through useApp(), src/data/types.ts, and one brand config. All mutations go through store functions and must enforce demo ownership/role scopes, even when UI hides an action. Synthetic samples and mock processing are explicitly marked. No real password, token or audio data is persisted. Demo persona tools only appear when import.meta.env.DEV or an explicit demo build flag is true. This is not backend authorization.

Page owners may add their own page-group file only. Do not change shared components, CSS, shell, state contracts or asset pipeline without coordinator agreement. No backend changes.

Design read: serene winter research workspace. Public variance 5, motion 3, density 3; authenticated density 6. Marketing-layout guidance does not apply to data tables. Reduced motion removes snow, owl tracking and nonessential transitions. No new dark theme.
