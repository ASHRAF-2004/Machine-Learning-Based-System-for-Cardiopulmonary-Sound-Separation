# Public winter reference refresh

2026-09-24. Scope: home, shared authentication presentation, and isolated supporting artwork. Existing workspace, backend/ML, authentication adapters, brand settings and approved owl renderer are unchanged. Nothing deployed.

## Visual implementation

- `/login` follows the supplied 1536×1024 composition: 534px centered glass form at x501/y144, approximately739px high, top-left approved logo, upper-right editorial copy, original reference owl grounded on its snowy perch, and bottom navigation. Inputs/buttons/text remain live HTML.
- Matching authentication presentation carries through registration, recovery, verification, callback and account-state pages. Variable-height forms and errors remain scrollable. Mobile favors a readable form; the large decorative owl is omitted at narrow widths.
- Home retains the original background and approved live owl, with slate-blue glass CTAs, translucent navigation/panels, reference waveform/feather details, and italic gray-to-light-gray `signals within.` lettering.
- Design/reference-matching skills guided measured spacing and typography rather than a new theme. The user-supplied image superseded generic fresh-design guidance. Existing light-only brand and serif direction preserved.

## Artwork provenance and limitations

Original reference: `/home/ashraf/Documents/StethoFuse/ChatGPT Image Sep 24, 2026, 01_44_30 PM.png`.

`tools/prepare_public_reference.py` encodes a lossless RGB copy (asserts decoded pixel equality) and responsive background plates. `AuthScenery.tsx` frames only original owl pixels and a surrounding margin; no baked UI is displayed. The multicolor Google mark is also framed from the supplied reference. Original source untouched.

One built-in image-generation edit cleaned the reference background, removing UI and the owl to avoid duplication. Prompt: remove all logo/text/form/footer interface, remove only the owl silhouette while preserving its rocky perch, inpaint continuous snowy mountain/lake scenery, preserve framing/colors/lighting, no new subjects or text. Saved source: `assets/public-reference/login-backplate.png`. Full provenance/size/hash manifest: `assets/public-reference/manifest.json`.

The owl pixels are original, but hidden scenery is reconstructed, not pixel-identical. Font rendering is a close implementation with the existing local Cormorant Garamond and Arial UI font, not a claim to know the image's exact font. A visible rectangular blend in the first scene attempt was found in screenshots and removed before final capture.

| Asset | Encoded bytes | Dimensions |
|---|---:|---|
| Supplied PNG | 1,842,878 |1536×1024|
| Lossless reference WebP |1,209,210|1536×1024|
| Clean landscape WebP |132,632|1536×1024|
| Small landscape WebP |63,868|800×533|

Reference WebP is34.4% smaller with exact RGB pixel preservation. Its full decoded RGBA equivalent is6,291,456bytes; framing doesn't reduce decode memory. Desktop scene plus plate is1,341,842 encoded bytes, excluding UI/fonts. This favors precise source-owl fidelity over the earlier provisional500KB decorative target. Home's below-the-fold reference art reuses existing full atlases. No new dependencies or owl-frame processing.

## Behavior and verification

- Public suite:42PASS. Separate demo-disabled production suite:6PASS. Includes validation/recovery/reset/provider states, credential disposal, safe redirects and demo gating. `evidence/public-reference/functional/`.
- Final layout/keyboard capture checks:10PASS,390/768/1366/1536px emulated widths; no horizontal overflow, missing images or JS/HTTP errors. `evidence/public-reference/final/visual-checks.json`.
- Focused home owl regression:6PASS, approved18-view renderer ready, real pointer circle+hold changes yaw/pitch, reduced-motion and touch retain static poster without surface downloads, protected hashes match. Zero JS/resource errors. `evidence/public-reference/final/motion/results.json`.
- Build:PASS. Chrome151, localhost automation, not real-device certification. No claim of full contrast/Lighthouse certification in this bounded pass.
- Personally inspected final desktop login and mobile home/login/register/expired-reset screenshots, plus the live in-app sign-in page. Before images preserved under `evidence/public-reference/checkpoint/`.
- Remember checkbox is intentionally only in-memory UI while authentication is disconnected. Checking it explains that persistence is unavailable. It never saves credentials or creates an authenticated session. No real authentication or emails added.

## Reproduce

From `implementation/frontend`:

```sh
python3 tools/prepare_public_reference.py
npm run build
EVIDENCE_ROOT=evidence/public-reference/functional node tests/public.mjs
EVIDENCE_ROOT=evidence/public-reference/functional node tests/public-production.mjs
node tests/public-reference-visual.mjs
node tests/public-reference-motion.mjs
sha256sum -c evidence/public-reference/checkpoint/protected.sha256
```

Preview remains at `http://127.0.0.1:4180/login` and `/`. Existing development server reused. Scoped backup: `evidence/public-reference/checkpoint/public-before.tar.gz`. All source edits limited to `PublicPages.tsx`, new `public-reference.css`, new `AuthScenery.tsx`, asset preparation, tests and notes.
