# Frost Studio — local owner feedback, 1 October 2026

Status: owner approved the local feedback UI on1October2026 ("looks good. go to
next step"). Not deployed. Starting
implementation `c807bb5624b9a9aed54426b94df5ee718b552f69`. The approved visual
system is retained. No new backend, authentication, model or database changes.

## Three requested changes

1. **Before & after:** the real authorized Original, Heart and Lung samples now
   populate one comparison of RMS/peak dBFS, crest factor, clipped samples,
   near-silence and duration. Missing/denied values are unavailable, not zero or
   passed. Measurements are memoized and use unboosted samples. The panel explains
   that crest factor is peak minus RMS, and neither higher nor lower proves better
   separation. Level/clipping flags are transparent technical checks, not an
   accuracy, diagnosis or clinical-validity score. Matching clean references are
   required to measure separation quality; listening remains useful review.
2. **Separation feedback:** immediately after Separate, a disabled Starting…
   button and animated stage panel acknowledge the pending request. Backend
   queued/processing states show Queued…/Separating… and a restrained five-bar
   activity indicator. No fictitious completion percentage or artificial delay.
   Existing polling/idempotency/failure behavior is unchanged. Reduced motion
   disables animation while preserving the visible state.
3. **Recording locked:** New recording keeps Upload WAV as the available primary
   action. Record audio has a generated closed-microphone-padlock illustration
   and Coming soon badge. The direct legacy recording route also presents Coming
   soon; it does not activate a microphone. The existing capture implementation
   is retained for a later authorized milestone, not deleted or qualified here.

## Actual recording, not a procedural listening substitute

Listening reviews must use eligible raw recorded HLS-CMDS files from
`datasets/hls_cmds/`, never mathematical-tone fixtures. The owner's persistent
review copy `.local/manual-review/raw-hls/M0001.wav` is byte-identical to
`datasets/hls_cmds/raw/Mix/M0001.wav`: 15s, mono, 4kHz, PCM16. Its manifest entry
is eligible non-test. This is manikin audio, not patient audio. It is not assumed
to have valid clean paired references. The earlier procedural fixture tested
application mechanics only; it was not used for the frozen ML training or T9.

Source SHA-256:
`8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616`.

Read-only checks reused the owner's already-completed local result:

| Measurement | Original | Heart | Lung |
|---|---:|---:|---:|
| RMS dBFS | -40.3 | -45.6 | -46.7 |
| Peak dBFS | -26.1 | -31.0 | -31.7 |
| Crest factor dB | 14.2 | 14.6 | 14.9 |
| Clipped samples | 0 | 0 | 0 |
| Near-silence % | 0.0 | 1.7 | 8.3 |
| Duration s | 15.0 | 15.0 | 15.0 |

All three fall below the existing -35dBFS low-level review threshold. This is
not evidence of failed separation. Zero clipping is not proof of correct source
separation. Thresholds/analysis math are unchanged: clipping |sample| ≥0.999,
near-silence 250ms windows below -50dBFS.

## Focused evidence and limits

`frontend/tests/frost-owner-feedback.mjs`: 6/6 groups, exit0. Four groups use real
existing local artifacts and UI; two deliberately mock pending/queued/processing
responses and media revocation **inside a separate browser context**. They verify
presentation/clearing, not a new worker or authorization experiment. Only the
existing fictional test-only Firebase SDK/verifier seam is used; no runtime bypass.
No upload, new job, inference, grant or database mutation is performed by checks.
The owner's visible browser and running services are not navigated/restarted.

Ignored final receipts/screenshots: `frontend/output/playwright/owner-feedback/v5/`.
Receipt SHA-256:
`9eb7cbbd14eddc2fc922af3d7d7523ac7cbaa1a87dee41613badd2c126b3d275`.
Desktop1440×900, mobile390×844, Frost/Midnight, keyboard150/200%, no horizontal
overflow, reduced motion and denied comparison clearing pass. Images were
visually inspected; one scoped fix lets mobile table sublabels wrap.
Earlier harness failures are retained in v1–v3: obsolete TypeScript JS API,
incorrect selector, and test initialization on an opaque blank document. None
was an application/model defect. Final browser page exceptions: zero.

Standalone `npm run build` and
`npx --no-install vite build --config ux-preview.vite.config.ts`: both exit0.
Five-axis review: no Critical/Important finding remains. Protected-source authority,
object-URL/audio cleanup, audio graph, owl and approved preview remain unchanged.

## Illustration receipt

Generated with the built-in image generator, transparent PNG:
`frontend/src/frost/assets/recording-locked-v1.png`.
SHA-256: `085db947e22ca5db93e414daca77ac6606a5daecf36d3fe30bee0896afce5df8`.
Brief: restrained premium closed padlock, deep-pine enamel, satin-silver closed
shackle, engraved microphone, one small green leaf, calm winter material palette;
no text, logo, glow, owl or background. It is a UI illustration, not an audio file.
No existing owl/branch asset was regenerated or modified.

Frozen checkpoint/spec SHA-256 remain
`1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658` /
`2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b`.
No training/tuning/T9 access, production, Axora, provider/security changes or data
cleanup. Review data remains persistent. This approval covers the local UX/core,
not clinical/device validation or a production rollout. The next bounded LOCAL
identity foundation is tracked in `LOCAL_IDENTITY_FOUNDATION.md`.
