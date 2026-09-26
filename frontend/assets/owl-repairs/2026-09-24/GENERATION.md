# Focused diagonal repair sources

The original 17 assembled PNGs are unchanged. Two accepted, generated **candidate** head crops supplement them; acceptance by the user is still pending. These are not video frames, a 3D reconstruction, or 1,200 independently generated poses.

Tool actually used: the session's built-in image-generation/edit tool. No paid API configuration, external asset purchase, or dependency was added.

## Input and edit briefs

Both accepted edits used the actual broken intermediate head crop as the edit target and `source-audit/original-head-reference.png` as the identity reference. The framing is native `[180,0,820,560]` on the 1163×1353 original owl canvas. The briefs below summarize the requests; they are not presented as verbatim tool-call transcripts.

- Up-right, nominal yaw +7.5 / pitch +4.5: keep the exact intermediate direction, crop, head scale, lighting, owl identity and texture. Repair the grey wedge/duplicated contour in the screen-right far eye. Preserve a blue iris, black pupil, natural eyelid coverage and reflections; no white sclera. Maintain a coherent head/neck and transparent background. Do not change the body or pose.
- Down-left, nominal yaw −7.5 / pitch −4.5: keep the exact direction and crop, original identity and texture. Repair compressed/stretched throat feather bands and the far-eye ghost; retain natural feather overlap, head scale, lighting and transparency. Do not redesign the owl or turn the body.

Two earlier trials were rejected: a full-body edit changed the angle/body too much; another edit did not sufficiently repair the far eye. They were not included in the runtime assets.

Accepted tool output files retained without modification:

- `up-right-generated.png` (1341×1173), tool output `exec-786b8c93-e553-4629-9345-42331b9a4ba2.png`.
- `down-left-generated.png` (1341×1173), tool output `exec-2206a147-64d1-4c5b-bb54-3daa2d31386e.png`.

`python3 tools/prepare_owl_repairs.py` reproduces the single resampling/registration into the original canvas. `manifest.json` records hashes, intended nominal angles, crop and detected landmarks. The current field builder uses manually inspected eye/beak/throat landmarks in addition to these initial detections. The renderer always keeps the original shoulder/lower body fixed; it does not display the generated full crop over an unmasked second head.

Newly generated feather microstructure is an estimate, not an exact recovery of hidden anatomy. Image generation alone did not fix correspondence errors; the assembled intermediate frames require separate review.
