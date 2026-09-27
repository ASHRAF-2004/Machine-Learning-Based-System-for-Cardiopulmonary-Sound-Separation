# T0–T4 execution receipt — 2026-09-28

Status: **T0–T3 IMPLEMENTED OFFLINE; T4 TINY OVERFIT GATE PASSED. T5 BASELINE
NOT STARTED.** This is a pipeline/capacity check on two fixed development
mixtures, not a trained separator result or evidence of generalization. No test
waveform was decoded/scored. Production, application jobs, Axora and live data
were untouched.

## T0–T3 evidence

- Frozen manifest SHA-256:
  `39d5456477b07772bdc24b86ee73dee17c44fd1e0837b62b96eab8c19a1b65e4`.
  100 IDs, 100 unique file hashes, 16 sound families, zero family/split overlap;
  counts match HS36/9/5 and LS36/5/9. Every file hash and WAV header matched;
  all files report mono, PCM16, 4 kHz, 60,000 frames. Only development and
  validation samples were decoded and checked finite. The 14 test files remain
  locked/unopened as waveform data.
- Training recipe: 576 deterministic draws (24 occurrences per each of 24
  family pairs), independently selected valid crops and lung/heart level
  uniformly sampled over −10…+10 dB; family-balanced reshuffled source cycles.
  The first epoch recipes and source/mixture hashes are under ignored
  `.local/training/stethofuse-tcn-v1/<run-id>/recipes/`.
- Frozen validation recipe: 45 validation-only file pairs × five fixed levels
  = 225 recipe IDs; full 15-s sources, zero crop offsets, gains/seeds/source
  hashes recorded. No validation recordings overlap training families.
- Model: pinned torchaudio `2.11.0+cpu` Conv-TasNet, 645,681 parameters;
  `[2,1,32001] → [2,2,32001]`, finite output and gradients. Target-free equal
  residual correction maximum additivity error on synthetic smoke input:
  `2.38e−7`.
- Objective/evaluator: fixed-label differentiable mean negative SI-SDR plus
  `5×` source-RMS-normalized waveform L1; audited NumPy SI-SDR reused. Focused
  checks cover exact-output loss, swapped-label penalty, silent-reference
  rejection and weaker-source family-balanced validation selection.

## T4 gate

Predeclared pairs (0-dB relative level, 8-s crop at offset zero):

| Case | Heart | Lung | Mixture ID |
|---|---|---|---|
| 1 | `F_AF_A` | `F_N_LLA` | `cc5c31db20bb9255cfd1` |
| 2 | `F_ESM_LLSB` | `F_PR_LLA` | `ab255e2d1bcd5b4806a6` |

| Case/source | Initial SI-SDR | Initial SI-SDRi | Final SI-SDR | Final SI-SDRi | Normalized-L1 reduction |
|---|---:|---:|---:|---:|---:|
| 1 heart | −6.90 dB | −6.76 dB | 11.81 dB | 11.95 dB | 74.8% |
| 1 lung | −6.76 dB | −6.61 dB | 11.93 dB | 12.08 dB | 74.8% |
| 2 heart | −6.04 dB | −6.11 dB | 11.58 dB | 11.51 dB | 74.4% |
| 2 lung | −5.88 dB | −5.95 dB | 11.84 dB | 11.78 dB | 74.4% |

Every case/source meets SI-SDRi≥+10 dB and normalized-L1 reduction≥50%;
**T4 PASS at100 updates** (limit400), 13.90 s elapsed. Maximum observed
mixture-consistency error across final cases was `8.94e−8`. The start-to-end
gate throughput including periodic evaluation was approximately0.139 s/update.
Process peak RSS was approximately1,014 MiB (whole preparation/gate process).
CPU only, two Torch threads, low-priority process. No CUDA/ROCm changes.

Artifacts (including the fitted two-example state, logs and frozen recipe
manifests) are ignored and stored beneath
`.local/training/stethofuse-tcn-v1/t0-t4-20260927T204454Z/`; checkpoint
SHA-256: `73dc02384135b2cc0709ebca6e80ea7e84bfa26899802fb3f79742808eeef1bc`.
These overfit weights **must not** be reused to initialize T5. The baseline must
start with a fresh seeded initialization.

Focused tests: `tests/test_stethofuse_training_contract.py` — 5 passed. No
application regression suite was run. A test assertion typo was corrected
before this passing run; no data/model defect required a gate retry.

## Next authorization boundary

T0–T4 are complete. **Do not start T5 baseline until owner review.** The tiny
gate proves the implementation can fit the two selected examples; it says
nothing about held-out quality. Preserve the locked test set, frozen plan and
production baseline.
