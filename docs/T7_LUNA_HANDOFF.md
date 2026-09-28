# T7 execution handoff — one width variant, not a sweep

2026-09-28. **T7 EXECUTED / VALIDATION ONLY / FINAL TEST SEALED / NOT DEPLOYED.**
The approved one-width experiment and one confirmation seed are complete.
Decision, detailed family/level breakdowns and run evidence:
[`T7_TUNING_DECISION.md`](T7_TUNING_DECISION.md). This handoff preserves the
frozen execution contract; it does not authorize final-test evaluation or
deployment.

## Execution receipt

The small N64/B32/H64 profile passed its two-example development capacity gate
(100 updates, 8.17s; all source/case SI-SDRi >10dB and normalized-L1 reduction
66.3–67.1%). A fresh seed-20260928 full run completed 17 epochs, best epoch 8,
early-stopped, and scored H/L SI-SDRi 3.1011/3.1302dB (Q 3.1011, mean 3.1156;
zero validation failures). It exceeded the existing baseline control's Q by
0.0660dB and mean by 0.0587dB; this small difference is descriptive, not
statistical evidence of superiority.

The configuration was selected before exactly one fresh seed-20260929
confirmation. That run completed 16 epochs, best epoch 4, and scored H/L
SI-SDRi 3.3324/3.3275dB (Q 3.3275, mean 3.3300; zero failures). Differences
across the two family-pair groups and relative-level behavior make robustness
**UNCERTAIN**. Keep the selected canonical checkpoint at seed 20260928; do not
substitute the higher-scoring confirmation checkpoint or run another seed.
The measured profile is 171,313 parameters with pinned torchaudio, not the
earlier 170,545 estimate. Full hashes and summaries are in the decision record.

The subsequently authorized validation-only ensemble reconsideration is now
complete: [Decision B](FINAL_ENSEMBLE_RECONSIDERATION.md) retains the small
standalone waveform model. T8 freeze metadata/checklist is prepared; T9 remains
sealed pending full freeze and owner approval. No ensemble was evaluated in T7.

## 1. Exact experiment

Create `research/configs/stethofuse_tcn_v1_t7_small.yaml` as a copy of the
immutable baseline YAML. Its only scientific change is the existing smaller
**width profile**:

| YAML field | Baseline control | T7 variant 1 |
| --- | ---: | ---: |
| `model.enc_num_feats` | 128 | 64 |
| `model.msk_num_feats` | 64 | 32 |
| `model.msk_num_hidden_feats` | 128 | 64 |
| `model.parameter_count` (derived assertion) | 645681 | 171313 |
| `architecture_version` (identity) | `stethofuse-convtasnet-4k-v1` | `stethofuse-convtasnet-4k-small-v1` |

Give the copied config an honest T7 status; record the inherited `fallback`
section as historical, not permission for automatic substitution. The original
baseline file/status/hash must not change. **Variant 2: NONE.**

Everything else stays fixed: scratch seed **20260928**; heart/lung order;
4 kHz; 8-s training; 10-s/8-s-hop inference; consistency and shared gain;
576 family-balanced draws/epoch, independent crops, U[−10,+10] dB; batch 4;
AdamW LR 0.001, decay 0.0001, betas (0.9,0.999), eps 1e-8; clip 5; fixed-label
negative SI-SDR + **5×** normalized waveform L1; validation each epoch;
ReduceLROnPlateau max/factor 0.5/patience 4/absolute threshold 0.1/min LR 1e-5;
early stop 12 epochs without a significant 0.1-dB gain over its anchor; max 80.
Do not change optimizer, loss, gains, dropout, depth or receptive field.

## 2. Frozen inputs and environment

Run from the implementation repository. Use existing
`.local/ensemble/venv/bin/python`: Python 3.14.4, torch/torchaudio 2.11.0+cpu,
CPU fp32, two intra-op threads, one inter-op thread, loader workers 0,
deterministic algorithms. No installs, GPU/ROCm work, containers or paid compute.

Verify metadata/hash identity, not another T0 audit of test files:

| Artifact | SHA-256 |
| --- | --- |
| `research/manifests/hls_cmds_split_v1.csv` | `39d5456477b07772bdc24b86ee73dee17c44fd1e0837b62b96eab8c19a1b65e4` |
| Baseline `research/configs/stethofuse_tcn_v1.yaml` | `fe9d046e7c0a9c2b2a092bfdda817e9d4dec942f242c6a3ea1e0ddd49f038eaf` |
| Baseline `validation/frozen_recipes.json` | `b4cef517cd4a64c267d3645ea6b918b5dfb72945f7536c0245b73228f00fdc90` |
| Baseline `recipes/epoch-000.jsonl` | `790dcb8d06288ee3a93531274a9e0c10e01d6adb5c339c916acd3f79f8c5c0c7` |

The latter paths are relative to
`.local/training/stethofuse-tcn-v1/baseline-seed20260928/`. Reuse the exact
225-condition validation recipe, never regenerate it. Same-seed variant
training recipe hashes must match baseline for overlapping epochs; model width
must not affect the keyed generator. Save the new config hash separately.
Filter development/validation before opening WAV paths. **No test files,
headers, recipes, inference, listening, metrics or visualization.**

## 3. Small implementation prerequisite (Luna, not this decision sprint)

- `app/ml/stethofuse_tcn.py`: allow only the two named width profiles. Preserve
  default baseline behavior, source order, wrapper and all other parameters.
  Check actual parameter count; attach the correct instance architecture ID.
- `scripts/train_stethofuse_baseline.py`: currently hard-codes the config,
  constructor and baseline run-ID prefix. Add explicit config/profile support
  for the variant and one seed confirmation. Both fresh and resume paths must
  construct the specified profile and reject mismatched architecture/config/
  manifest/recipe hashes. Do not build a generic search framework.
- Preserve `training_data.py` and `training_objective.py`; no scientific changes.
  Log LR **used for the epoch** separately from post-scheduler/next-epoch LR.
  The old baseline log is retained unchanged; its reporting correction is in
  the decision record.
- Reuse existing training-contract tests; at most one focused small-profile
  contract for count, shape/finite gradients and checkpoint/profile identity.
  Check unchanged baseline seeded state digest against
  `dc688a996fe32969b3ba8a1b479221b8372eeaf713d1f3482d0cc12c9e9b1831`
  without retraining it. No broad application suite or repeat of baseline T4.
- Commit/push the reviewed runner/config changes as ASHRAF-2004 on the current
  branch. Record a **clean source commit** before gate/full-run initialization.

## 4. Bounded small-model capacity gate, then fresh T7

Reuse the existing two-example gate logic through the isolated
`scripts/run_stethofuse_t7_capacity_gate.py` entry point. **Do not rerun
`scripts/run_stethofuse_t0_t4.py` main:** it performs a manifest/audio-header
audit including test files and regenerates validation recipes. Do not do that.

Small-profile gate: fixed development pairs `F_AF_A/F_N_LLA` and
`F_ESM_LLSB/F_PR_LLA`, starts 0, 32,000 samples, level 0 dB; seed 20260928,
batch 2, AdamW LR 0.001, decay 0, no scheduler/augmentation, same loss and clip.
Evaluate every 20 updates. Every source/case must achieve SI-SDRi ≥10 dB and
normalized L1 reduction ≥50% from initialization. Limit **400 updates or
10 minutes, whichever first**. No easier replacement examples. Diagnose once
if it fails; one rerun only after a demonstrated implementation fix. Otherwise
stop before full training and report the blocker; do not enlarge/redesign.

On pass, initialize the small full run **afresh**, resetting all seeds and
optimizer state. Never load gate, T4, baseline or NeoSSNet weights. Record the
initial-state digest/config/source/recipe/environment hashes before update 1.

Commands after the narrow profile/config runner update:

```sh
nice -n 10 .local/ensemble/venv/bin/python scripts/run_stethofuse_t7_capacity_gate.py --config research/configs/stethofuse_tcn_v1_t7_small.yaml
nice -n 10 .local/ensemble/venv/bin/python scripts/train_stethofuse_baseline.py --config research/configs/stethofuse_tcn_v1_t7_small.yaml --run-id t7-small-seed20260928
```

After epoch 3 inspect finite loss/gradients, both validation sources, runtime
and memory; continue if healthy. Same frozen scheduler/stop policy, no manual
LR adjustment or stopping at an attractive score. Genuine invalidating defects
stop/preserve evidence; no endless retries. Guard projected runtime >8 hours
or RSS >4 GiB. Baseline measured 20.72 minutes/20 epochs, about 60–63 s/epoch;
small-profile runtime is unmeasured, not proportional to parameter count.

## 5. Comparison and the single seed confirmation

Validate each run's **best** checkpoint on all frozen conditions. Let H/L be
family-pair macro SI-SDRi; rank by Q=min(H,L), then M=(H+L)/2, tolerance 1e-6 dB
as already implemented. Earlier epoch wins within-run ties; retain baseline
on a complete between-config tie. Do not select by pooled score, one family,
one source, a gain subset, or the final test. Report both sources and all groups.

| Configuration / seed | Heart SI-SDR | Heart SI-SDRi | Lung SI-SDR | Lung SI-SDRi | Q | M | Failures | Best epoch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline / 20260928 | 3.031004 | 3.035050 | 3.074744 | 3.078790 | 3.035050 | 3.056920 | 0 | 8 |
| Small / 20260928 | 3.097049 | 3.101095 | 3.126111 | 3.130157 | 3.101095 | 3.115626 | 0 | 8 |
| Selected config / 20260929 | 3.328333 | 3.332379 | 3.323476 | 3.327522 | 3.327522 | 3.329950 | 0 | 4 |

Use full stored precision for ranking. Also report ΔQ, ΔM, per-family/source,
gain, median/IQR, negative-improvement counts, failures, duration and RSS. No
225-independent-sample inference. A tiny rank advantage is not established
superiority; explicitly report uncertainty or a source tradeoff. Baseline stays
eligible and wins if the variant does not improve the frozen ordering.

**Exactly one confirmation seed: 20260929**, of the selected configuration,
fresh initialization and unchanged protocol. Use run ID
`t7-confirm-baseline-seed20260929` or `t7-confirm-small-seed20260929` and pass
`--seed 20260929`. The runner writes the effective seed-adjusted config into
that run and records both its hash and the source config hash. This changes
keyed training draws as well as initial weights, not the validation recipe.
It is robustness evidence, not a
second configuration-selection opportunity. Report both seeds, keep the
selected **20260928** artifact; never substitute the better-scoring seed. If
either macro source improvement turns negative, failures occur, or group/level
behavior is materially unstable, report sensitivity and stop for owner review.
No new threshold, extra seed, re-tuning or automatic architecture switch.

## 6. Artifacts, checkpoint and later gates

Use distinct ignored `.local/training/stethofuse-tcn-v1/<run-id>/` directories;
never overwrite baseline. Keep config/run metadata, clean Git SHA, RNG/sampler/
optimizer/scheduler/early-stop resume state, initial digest, best/resume/final
checkpoints, per-epoch/component logs, all validation rows and SHA-256 receipts.
No checkpoints/audio/caches in Git. Document only actual results afterward.

**Execution order:** narrow code/config checks → small gate → fresh small T7
→ frozen-selector comparison with saved baseline → single seed confirmation
→ evidence/owner checkpoint and **STOP**. This decision allows at most three
full runs including the already-completed baseline, not a second variant.

Later, under separate approval: **validation-only ensemble reconsideration
(legacy phase T10, moved before T8/T9)** → final separation-system freeze T8
→ owner-authorized one-shot held-out evaluation T9. If ensemble is not selected
for that study, freeze that exclusion too. Never test the single model first
and then use its test result to design an ensemble. No application integration,
live recordings, production services, security, backups, Axora or deployment.
