# T5/T6 frozen CPU baseline execution receipt — 2026-09-28

Status: **T5 BASELINE TRAINED; T6 VALIDATION CHECKPOINT SELECTED. NOT FINAL TEST;
NOT DEPLOYED.** No test audio/recipes/metrics were accessed. Production,
Axora, live users/data, Firebase, Cloudflare, Caddy and Backblaze were untouched.

## Reproducibility record

- Environment: existing isolated `implementation/.local/ensemble/venv`, Python
  3.14.4 (uv 0.11.31), `torch==2.11.0+cpu`, `torchaudio==2.11.0+cpu`; CPU only.
- Clean implementation commit before initialization and first optimizer step:
  `bfe879f6dfcc5032d4350537eafe9369e9d8e4f3` (`fyp2/application`, remote SHA
  matched at run start).
- Frozen source manifest SHA-256:
  `39d5456477b07772bdc24b86ee73dee17c44fd1e0837b62b96eab8c19a1b65e4`.
- Frozen validation recipes: 225 validation-only conditions; SHA-256
  `b4cef517cd4a64c267d3645ea6b918b5dfb72945f7536c0245b73228f00fdc90`.
- Config SHA-256:
  `fe9d046e7c0a9c2b2a092bfdda817e9d4dec942f242c6a3ea1e0ddd49f038eaf`.
- Seed `20260928`; 645,681 parameters; CPU; no T4 checkpoint loaded. Fresh
  seeded initialization state SHA-256:
  `dc688a996fe32969b3ba8a1b479221b8372eeaf713d1f3482d0cc12c9e9b1831`.
- First epoch's 576-draw deterministic training recipe SHA-256, recorded before
  its first optimizer update:
  `790dcb8d06288ee3a93531274a9e0c10e01d6adb5c339c916acd3f79f8c5c0c7`.

The frozen training configuration was unchanged: AdamW, LR 0.001, weight decay
0.0001, batch 4, gradient clipping 5, fixed-label negative SI-SDR plus
5×RMS-normalized waveform L1, configured ReduceLROnPlateau and 12-epoch
significant-improvement early stopping. T5 used development draws only;
validation used the same 225 frozen conditions each epoch.

## Result

Training completed 20 epochs and stopped by the approved early-stopping rule.
The best checkpoint is epoch 8. Both source SI-SDRi values are positive and
closely balanced, but the validation set contains only two family-pair groups
and has substantial condition-level spread; these are limited validation
results, not final held-out or subject-independent evidence.

| Best validation metric (family-pair macro mean) | Heart | Lung |
| --- | ---: | ---: |
| SI-SDR | 3.0310 dB | 3.0747 dB |
| SI-SDRi | 3.0350 dB | 3.0788 dB |

- Weaker-source selector `Q=min(H,L)`: **3.0350 dB**; tie-break mean:
  **3.0569 dB**.
- Validation: 225 conditions, 2 family-pair groups, 0 failures.
- LR: 0.001 through epoch 6; 0.0005 epochs 7–12; 0.00025 epochs 13–17;
  0.000125 epochs 18–20.
- Training loss moved from 1.3973 (epoch 1) to −3.7061 (epoch 20), while the
  validation selector peaked at epoch 8 and fluctuated afterward. This is
  consistent with validation plateau/overfit pressure; do not infer broad
  generalization from it.
- Runtime 1,243.49 seconds (20.72 minutes); process peak RSS 2,078.2 MiB.
  All 20 epochs reported finite loss/gradients and zero nonfinite counts.
- Best checkpoint SHA-256:
  `2eb0c19fc27b7587eca2087da2ad7e9fb943d74268defb67de3470a91a960db9`.
  Resume/final artifacts and full per-condition history remain outside Git in
  `.local/training/stethofuse-tcn-v1/baseline-seed20260928/`.

No software defect was found. No new automated tests were added. The existing
focused training contract suite passed: **6 passed**. An additional one-step
synthetic CPU smoke check validated model shape/finite gradients, objective,
optimizer/scheduler construction and an optimizer update; it was not baseline
training. No application-wide suite was run.

Recommendation for owner review: **KEEP BASELINE** as the first trained
candidate; do not tune or promote it automatically. Review the small number of
validation family-pair groups and condition-level spread before authorizing any
validation-driven variants. Final test remains sealed and model deployment is
not authorized by this receipt.
