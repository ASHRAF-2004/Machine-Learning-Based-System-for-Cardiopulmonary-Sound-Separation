# Approved-artwork and owl-frame optimization

## Current winter-glass continuation — 2026-09-24

The user approved the connected-neck owl and authorized frontend design. The normal renderer now selects the existing 18-source `neck-candidate` field; no artwork/controller/math was regenerated. Payload including manifest/body: 3,650,100 bytes over 142 files. Source RGBA decoded memory: 75,362,400 bytes, plus 373,368 flow bytes, 301,024 geometry bytes, body/canvas/render targets. This is a bounded source-view set, not a 1,200-frame initial download. Poster, reduced-motion/coarse-pointer fallback and hidden/offscreen pausing remain. Fresh verification: `evidence/winter-glass/integration/results.json`.

Separate supporting feather and frozen-folder art was generated with the available native image tool, inspected, then optimized with `python3 tools/optimize_winter_art.py`. Sources/full prompts: `assets/winter-glass/`; copy hashes/alpha information: `public/assets/winter/manifest.json`.

| Supporting art | Source PNG | 1× WebP | 2× WebP | Decoded RGBA 1× / 2× |
|---|---:|---:|---:|---:|
| Feather | 1,916,510 B · 1024×1536 | 21,136 B · 240×360 | 65,338 B · 480×720 | 345,600 / 1,382,400 B |
| Frosted collection | 1,226,218 B · 1774×887 | 15,906 B · 360×180 | 50,366 B · 720×360 | 259,200 / 1,036,800 B |

WebP quality 90, preserved alpha. Combined 1× delivery 37,042 B versus 3,142,728 B source PNGs (~98.8% smaller, with deliberate resize); 2× totals 115,704 B (~96.3% smaller). These are responsive choices, not all downloaded together. Dimensions reserved, images lazy-loaded. Derivatives were opened directly and inspected on the actual glass UI: fine feather barbs/markings, folder edges and embossed signal remain visible. Decoration is not measured audio or an owl replacement.

`python3 tools/verify_winter_preservation.py` verifies 24 identity/source/controller/brand checks against prior hashes and this task's checkpoint. All pass. Logo is byte-identical; original owl/background assets unchanged. The older frame-library report below is historical provenance, not the current renderer.

---

This report covers the **existing 1,200-frame sequence and identity-asset derivatives** used for the new frontend. It does not approve a new owl renderer or claim that the ongoing full-direction/circular-pointer enhancement works. The asset work described here is copy-only resizing/re-encoding: no new owl generation, eye/beak replacement, sharpening, feather painting or source-frame regeneration.

## Source of truth and preservation

Appearance assets remain in `/home/ashraf/Documents/StethoFuse/StethoFuse-codex-package/website/`. Animation input is the existing lab export:

`/home/ashraf/Documents/StethoFuse/StethoFuse-codex-package/owl-3d-lab/frame-study/feather-continuity/rife-exports/sequence.json`

The input sequence manifest SHA-256 recorded by the builder is `53663565f21015b2a7c3699c559220b4be1244bb5f6654dc219cad3c257ab29f`. The optimized copies live only under `frontend/public/assets/`; the originals remain available at their original paths. Current hashes of the three identity sources were reread and agree with `evidence/assets/optimization.json`:

| Original | Dimensions / format | Original bytes | SHA-256 |
|---|---|---:|---|
| `website/Owl.png` | 1163 × 1353, RGBA PNG | 1,434,704 | `9215004380eca970bdcaa0f831e3b0b64e7805812afdfd29dd677019ad747d8e` |
| `website/Background.png` | 1774 × 887, RGB PNG | 1,821,223 | `70221ce03354be2499a99b279fe3a6c6d48bc756bd037279960151cba526cb87` |
| `website/StethoFuse_owl_logo.svg` | Original SVG, embedded wordmark retained | 25,874 | `e8724f1a8606604e412f420f3ba769cd175e1a60644633f4dcf4053018170e5a` |

`public/assets/logo.svg` is a byte-identical copy of the original logo: **25,874 bytes and the same SHA-256**, verified again for this report. It is not a redrawn or recolored mark.

## Delivered responsive images

The owl remains transparent. All three owl posters and the body derivative decode as RGBA with alpha extrema 0–255. Backgrounds are intentionally opaque RGB. Poster widths are selected through `srcset`/`sizes`; dimensions are reserved in markup so the static owl appears before any interactive assets.

| Derivative in `public/assets/` | Dimensions | File bytes | Encoding |
|---|---:|---:|---|
| `owl-poster-420.webp` | 420 × 489 | 55,614 | WebP Q94, method 6, exact transparent RGB handling |
| `owl-poster-720.webp` | 720 × 838 | 125,390 | WebP Q94, method 6, exact transparent RGB handling |
| `owl-poster-1163.webp` | 1163 × 1353 | 260,358 | WebP Q94, method 6, exact transparent RGB handling |
| `background-800.webp` | 800 × 400 | 43,324 | WebP Q88, method 6 |
| `background-1200.webp` | 1200 × 600 | 73,632 | WebP Q88, method 6 |
| `background-1800.webp` | 1800 × 900 | 112,692 | WebP Q88, method 6 |
| `owl/body.webp` | 1163 × 753 | 152,282 | WebP Q94, method 6, exact transparent RGB handling |

The unchanged body source is `owl-3d-lab/frame-study/exports/body-from-row600.png`: **1163 × 753 RGBA, 850,098 bytes**. The head/body split remains at source row 600. The nominal 1800px background derivative is a small upscale of the 1774px original, not newly recovered detail.

Responsive assets exist, but delivery is also checked rather than inferred from filenames: in the measured production samples, both desktop 1440px/DPR1 and mobile 390px/DPR2 selected the **720px owl poster**. Both welcome-page samples fetched the **1800px background**; the current CSS does not switch the welcome background to 800px on phones. The 1200px derivative is used on authentication artwork. No claim is made that every provided background variant is currently selected at runtime.

## Existing animation sequence: measured size

| Item | Source | Optimized copy |
|---|---:|---:|
| Head frame count | 1,200 | 1,200 |
| Each head frame | 1163 × 600 RGBA | 1163 × 600 RGBA |
| Total head-frame file bytes | 422,950,092 | 101,035,364 |
| Total in MiB | 403.36 | 96.35 |

The copies save **321,914,728 bytes (76.11%)**. The output-directory count and byte total were checked against the report: 1,200 files, 101,035,364 bytes. Individual optimized files range from **68,190 to 106,968 bytes**, averaging **84,196 bytes**. The sequence is a collection of on-demand files, not a 96.35 MiB initial download.

The production copies use WebP **quality 94**, `method=6`, `exact=True`, at native head resolution. `public/assets/owl/sequence.json` is a 224,784-byte provenance/index manifest containing frame hashes, dimensions and route labels; the baseline renderer does not fetch that entire manifest on initial page load. These totals cover `owl/frames/` only, not experimental `field*` outputs created during the separate, still-in-progress direction enhancement.

## Why retain native head resolution?

`tools/compare_variants.py` compared frames 36, 199 and 549 at 480px, 720px and 1163px widths. The source and decoded variants were cropped and displayed at a matching enlarged scale. The actual comparison sheet was opened and inspected.

| Frame | 480px WebP bytes | 720px WebP bytes | 1163px comparison WebP bytes |
|---|---:|---:|---:|
| 36 | 23,962 | 41,456 | 74,980 |
| 199 | 23,822 | 40,668 | 75,230 |
| 549 | 24,098 | 42,046 | 79,764 |

In the inspected crops, 480px visibly softens the small dark feather tips and merges fine white feather strands; 720px is better but still loses some separation at the enlarged view. Native resolution retains the most useful definition. The desktop owl can display around 590 CSS pixels wide, so DPR2 approaches the 1163px source width. That makes native head frames a deliberate fidelity choice rather than an arbitrary oversized export. Mobile/coarse-pointer users use the responsive static poster rather than decoding animated native frames.

These comparison sizes are **not** the production frame-size records: the comparison encoder resizes and omits the production builder's `exact=True` argument. `optimization.json` and the actual output files are authoritative for deployed-copy bytes. No tiny per-frame target was enforced.

AVIF encoding was attempted for all three sample frames but the available Pillow encoder reported `'AVIF'` unavailable. No AVIF derivative was produced or visually validated. The empty fourth column of the comparison sheet is not an AVIF quality result. WebP was selected from the working, actually inspected path; this is not a claim that AVIF is inherently inferior.

## Transparency and feather checks: actual scope

The builder compared these **13 frames**, not every one of the 1,200 frames:

`0, 36, 74, 101, 199, 224, 349, 424, 549, 674, 824, 974, 1124`

- Alpha arrays were pixel-identical between source and optimized output for **all 13 sampled complete head frames**.
- RGB PSNR on source pixels with alpha > 200 ranged from **43.12 to 43.92 dB**. This is a limited compression comparison, not a perceptual-motion score or proof of anatomical realism.
- The side-by-side native-resolution crown/feather strips in `frame-quality-comparison.jpg` were actually opened and inspected. Fine dark markings and pale feather strands remain close in these sampled source/copy strips, without an obvious new hard alpha edge.
- The separate 480/720/native resolution sheet was also actually inspected. Its enlarged head/eye-area crops support the native-resolution choice.

The sheets emphasize crown/head-feather regions, and RGB metrics exclude most partially transparent edge pixels. **This is not a frame-by-frame visual audit of the whole head, every interpolation frame, or every dark-background alpha edge.** Alpha identity is verified for the 13 sampled full frames only. Poster/body alpha presence is confirmed, but exact full-array alpha equality was not separately claimed for those derivatives. Existing source motion or fine-feather interpolation defects cannot be repaired by compression, and are not declared fixed by this report.

Evidence:

- `evidence/assets/optimization.json`
- `evidence/assets/frame-quality-comparison.jpg`
- `evidence/assets/resolution-format-comparison.json`
- `evidence/assets/resolution-format-comparison.png`

## Loading, cache and fallback baseline

This section describes the **baseline renderer inspected and measured before the pending full-circle direction enhancement**. It must be rechecked against that enhancement before claiming the new directional behavior works.

- The responsive static poster loads immediately. Animation head/body images begin on pointer interaction, not from a preload of all frames.
- The renderer uses `createImageBitmap`, reuses decoded images and keeps a **12-head-frame LRU cache**. Evicted bitmaps are closed. A body bitmap is separate, and the baseline serializes its next-frame request.
- Nominal pixel storage for 12 RGBA head frames is `12 × 1163 × 600 × 4 = 33,494,400 bytes` (31.94 MiB). The body adds 3,502,956 bytes; a maximum 1163 × 1353 RGBA canvas adds 6,294,156 bytes per backing surface. **These are pixel-buffer calculations, not measured total browser/GPU memory.** Browser caches, transient decode buffers and duplicate graphics surfaces can add overhead.
- The drawing width is capped at 1163px and uses device-pixel-ratio scaling up to 2. Pointer movement updates a target and the animation uses `requestAnimationFrame`; the original body remains anchored.
- Offscreen intersection, hidden documents and window blur pause or return attention appropriately. Cleanup cancels animation, aborts pending work and closes retained bitmaps.
- Coarse pointer, reduced motion, the saved motion preference, reduced-data hints/very slow connections, and frame failures fall back to the static owl. No decorative device-motion permission is requested.

The normal production performance test made **zero initial requests for animation head frames or the body** in desktop, mobile-emulated and throttled initial-load samples. No pointer interaction was sent in those samples. This is evidence for initial loading only, not proof of full-circle pointer quality, cache behavior during a long interaction, or correctness of the in-progress pose-field enhancement.

## Fonts and measured initial artwork transfer

The approved pairing is self-hosted:

| Font file | Bytes | License retained |
|---|---:|---|
| `fonts/manrope-latin.woff2` | 24,836 | Manrope SIL Open Font License 1.1 |
| `fonts/cormorant-latin.woff2` | 37,640 | Cormorant SIL Open Font License 1.1 |

Together the fonts are **62,476 bytes**. Both corresponding OFL text files are included beside them. No Google Fonts request is necessary at runtime. The existing logo is used unchanged in the site and as the icon source.

The measured public initial-load image response bodies total **254,540 bytes**, including the 720px owl poster, 1800px background and two observed SVG-logo requests (site image and icon). The original SVG file is 25,874 bytes; the preview server transferred each gzip-encoded logo response body as 8,229 bytes. Those transport measurements are distinct from source/optimized file sizes. See `PERFORMANCE.md` and `evidence/performance/results.json` for exact requests, compression, viewport and DPR. Measurements should be rerun after the ongoing renderer build is finalized.

## Reproduce without modifying originals

```bash
cd /home/ashraf/Documents/StethoFuse/implementation/frontend
python3 tools/compare_variants.py
python3 tools/optimize_assets.py

# After a normal production build and preview server on port 4181:
node tests/performance.mjs
```

The existing Python environment supplies Pillow and NumPy; no additional encoder was installed for this report. `optimize_assets.py` reads the source package, copies the logo, creates image/body derivatives and processes the supplied sequence. It does not create new poses or touch the source files. Font files are packaged assets, not regenerated by this script.

Frame outputs are cached by filename: existing `owl/frames/head-*.webp` files are skipped. If the source or encoding parameters change, first preserve a scoped backup of the output frame directory and regenerate into a fresh output directory/path arrangement; simply rerunning the cached builder does not recompress existing frames. `--samples-only` is useful for a targeted trial but rewrites `optimization.json` with the sample count/total; run the complete builder when producing a full-sequence report. Keep source hashes, sample scope and generated comparison evidence together.

## Remaining verification boundaries

The original identity files and logo are preserved; the native-resolution WebP copies materially reduce file size with explicit sampled quality checks. This does **not** certify every frame's feather continuity, newly generated field transitions, every transparency background, long-session frame decoding performance, or the complete new owl interaction. The full-direction enhancement is separate work and must earn its own functional and visual evidence. No final owl-visual approval is inferred from the optimization results.
