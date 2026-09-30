# Frost Studio — isolated four-screen design proof

Local design review only; not the production application or a second auth system.
No datasets, model calls, Firebase session, live grants or production endpoints.

From `frontend/`:

```sh
npx vite --config ux-preview.vite.config.ts
# http://127.0.0.1:4193/ux-preview.html#overview
# Other design routes: #library, #recording, #settings
node tests/ux-preview.mjs
node tools/ux-previews.mjs
npm run build
```

The normal build uses the existing app entry and excludes this preview. An
explicit optimized **local review** build is available for performance evidence:

```sh
npx vite build --config ux-preview.vite.config.ts
npx vite preview --config ux-preview.vite.config.ts
# http://127.0.0.1:4194/ux-preview.html#recording
```

Do not deploy `output/ux-preview-build`. This explicit configuration enables the
preview guard only for local review. Runtime preferences use `sf-design-*` keys;
audio is generated deterministically as M0001/H0001/L0001, not model output.
401/403 fixtures prove presentation/cleanup behaviour, not live authorization.
Every fixture row opens the one representative ready detail. Capture, grants,
notifications, export/delete and identity services are design-only boundaries.

Theme/gain/name/one-handle-change persist locally. Avatar crop lasts this preview
session only. Gain up to200% uses Web Audio and a compressor above100%; not a
true-peak guarantee and never changes the WAV. Analysis is sample-derived;
spectrogram columns are bounded and no clinical/accuracy score is calculated.

Approved owl renderer/assets are reused. Local green-eye material and transparent
leafy perch apply only here. Cursor tracking uses the whole viewport, without
an idle animation loop. Reduced motion uses a poster. Real fly-in is asset-gated;
the rejected generated atlases are not shipped.

Normative design/approval/handoff: `docs/UX_REDESIGN_SPEC.md`, `UX_LAWS_AUDIT.md`,
`UX_DESIGN_REVIEW.md`, `UX_LUNA_HANDOFF.md`. Stop for owner visual approval.
