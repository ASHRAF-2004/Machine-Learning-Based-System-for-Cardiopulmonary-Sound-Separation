# StethoFuse — literal reference pass

24 September2026. Local development preview: http://127.0.0.1:4180/app/dashboard.

## What changed

The previous interpretation used a different owl and newly generated supporting illustrations. The current implementation uses the pictured snowy owl on its rocks, the pictured folder/forest, feather, circular forest and signal illustrations from the user's actual supplied PNGs. `ReferenceArt.tsx` frames decorative regions with an explicit SVG clip path; no screenshot button, form, table or navigation is substituted for working HTML. Overlays are decorative and excluded from accessibility trees.

The shared shell, typography sizing, palette, white glass rims, sidebar, header heights, content gutters, filters, tables, settings panes, dashboard columns and recovery card were measured against the1586×992 references. Data/permissions/disclosures remain those of the existing functional demo. Safety copy is not removed just to match image text. Pages absent from the references inherit the same shared system.

The image-to-code/design-taste workflow led to measurement, shared components, source-art reuse, browser captures and a corrective visual pass rather than independent page themes. The user’s explicit latest request superseded the previous instruction not to crop reference decorative artwork.

## Exact artwork versus reconstruction

- The8 full-source atlas copies are lossless WebP; the builder asserts identical decoded RGB pixels against each provided PNG. The SVG framing/masking does not repaint the owl, beak, eyes or feathers. These are static workspace illustrations, not another animation renderer.
- A bounded audit found no standalone assets matching this new owl and the new jagged mountain composition. The older `Owl.png` and `Background.png` are different and remain untouched.
- One built-in image-generation edit reconstructed scenery hidden by interface text/panels. It is explicitly **not** the exact original background. Its source, prompt and role are recorded in the manifest. There was no new owl generation. The403 outer scenery uses the actual reference pixels with the old center text masked under the new functional card.
- The flattened references do not identify a font binary. Existing local Cormorant Garamond and system Arial/Helvetica reproduce the editorial/compact hierarchy; exact original font metrics are not claimed.
- This is a close functional reproduction, not a certified pixel-perfect match. Cropped art has baked lighting/background; responsive framing, live text and unknown original fonts still cause differences. Complete source layers would remove the remaining reconstruction/compositing limitation.

## Scope and preservation

Changes: `src/components/ReferenceArt.tsx`, `WinterArt.tsx`, `ui.tsx`, `src/reference-match.css`, `main.tsx`, the workspace/account page pairs, public utility markup, source-art preparation, focused tests and documentation. No new package dependency. No backend, model training, Firebase, deployed domain, live authentication or deployment change.

The existing animation controller and renderer files, approved neck manifest and logo match their starting hashes. Original owl/background/logo files also match existing baselines. Evidence: `evidence/reference-match/functional/protected-assets.md`. Backup: `evidence/reference-match/checkpoint/frontend-before.tar.gz`. No reset, stash or unrelated commit was used.

## Verification

Functional:69 checks passed,0 failed in isolated fictional Chrome contexts: workflows16, shared/keyboard13, drafts6, administrator29, mobile containment5. These include account isolation, ID filtering, assignment/revocation and reassignment, owner-only job pages, retained reviewer history, settings persistence, upload validation, processing and synthetic audio, and keyboard/dialog behavior. After the final layout corrections, workflows16 passed again and mobile coverage was repeated and extended to6 cases including403. Build/typecheck passed.

Visual: desktop captures at1586×992/DPR1 in real headless Chrome151; mobile390×844 emulation; actual in-app browser dashboard inspected at its native wider viewport. Source images and browser captures were opened and inspected, including owl crop edges, main dashboard composition, settings, audit, ensemble, table pages and403. A SVG letterboxing leak, cropped waveform quote and mobile forest overlap were found and corrected. Screenshot inspection is distinct from automated functional checks and is not user approval.

Evidence:
- `evidence/reference-match/visual/`:16 labelled desktop routes. `metrics.json` records the latest selected rerun's layout measurements, resource timing and runtime/HTTP-error list; the other labelled captures remain from the full pass.
- `evidence/reference-match/functional/`: all focused test results and screenshots.
- `evidence/reference-match/final/mobile/`:6 post-fix390px captures and containment results; `final/workflows/`: repeated16-check final workflow run.

No physical mobile-device performance or exhaustive assistive-technology certification is claimed. Earlier154-pass reports belong to the previous design pass, not this one.

## Asset cost

8 lossless decorative atlases total8,955,940bytes on disk (25–26% smaller than the corresponding source PNGs), not all downloaded on each page. Each atlas is1586×992, approximately6.29MB of decoded RGBA if stored uncompressed; compressed transfer size is not decoded memory. The browser reuses a URL across multiple illustrations in a page. A full atlas is a fidelity-first tradeoff: isolated transparent source layers could reduce this further.

The reconstructed background copies are129,948bytes at800px and372,320bytes at1536px. Small-screen CSS uses the800px image. Original PNGs are preserved. The existing landing-animation optimized frame library, caching and reduced-motion behavior are unchanged. Resource timing from localhost is recorded by the visual harness; its navigation-to-network-idle interval is not LCP or a real-network benchmark.

## Reproduce

From `/home/ashraf/Documents/StethoFuse/implementation/frontend`:

```sh
npm run dev
npm run build
node tests/reference-match-visual.mjs
EVIDENCE_ROOT=evidence/reference-match/final node tests/reference-mobile.mjs
```

`python3 tools/prepare_reference_art.py` recreates the lossless copies from the named local input paths. It requires the existing Pillow environment; no installation is part of this pass. Preserve the archived background inpaint and supplied originals. Functional suite commands are listed in the evidence README. The administrator wrapper refuses to overwrite an existing evidence destination; use a new output root for later runs.

The local demo remains available for visual review. Nothing has been deployed.
