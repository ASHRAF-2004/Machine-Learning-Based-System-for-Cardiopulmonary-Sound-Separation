# Qualified HLS native-release pilot: completed negative result

**FORENSIC AUDIT COMPLETE · ROLE A RESTRICTED SUBSET · PILOT FAILED ADOPTION ·
HLS-ONLY T8 V2 RETAINED · T9 SEALED · NOT DEPLOYED.**

The one authorized native-supervision treatment completed. It did not improve
held-out HLS-family transfer: lung performance deteriorated substantially,
especially on the Fine Crackles holdout. No rescue loss, weight, alignment,
role, architecture, seed, extended budget or final native refit was run.
This is a valid bounded negative result, not proof that every possible use of
HLS native recordings is ineffective. No plateau-breakthrough claim is made.

## Forensic decision, before training

[Full forensic audit](HLS_NATIVE_TRIPLET_AUDIT.md) and
[original-source evidence](HLS_NATIVE_SOURCE_EVIDENCE.md) distinguish the actual
release from assumed acquisition properties. The expanded release contains
535 WAVs: 50 standalone heart, 50 lung and 145 M/H/L triplets. Conservative
family exclusion left 100 triplets for analysis; 45/135 native WAVs remained
unopened. The 86 non-test standalone files were the only standalone audio used.

Of the 100 assessed triplets, 73 did not yield reliable waveform correspondence
after bounded lag/gain/global-transfer diagnostics. Twenty-seven had near-exact
zero-lag `M ≈ g(H+L)` closure; one exact duplicate was removed, leaving 26.
The retained subset adds 13 heart/13 lung unique reference hashes beyond the
standalone pool, but no new source families or established patients. Its
capture/generation history is undocumented; normalized digital addition is
consistent with the signals, not a verified acquisition fact.

The shared positive gain was estimated on 6–9 s and checked on untouched
0–6/9–15 s flanks. Worst residual was 0.004798 of weaker-source RMS, below the
pre-model 0.10 tolerance. Deterministic same-family/different-file substitutions
failed closure in all 27 cases. No target residual was redistributed and no
per-record FIR/warp was used. The separate cross-class hash-label contradiction
affected only already-excluded earlier triplets. Selected plus standalone
references had no exact-hash class/family conflict.

## Frozen matched protocol and provenance

- Audit/protocol committed as `d30cdb6`; code/checks committed and pushed before
  initialization as `ff2f09e85f3bf67587015971d0ef20fcffdbb5f8`.
- Protocol: `research/configs/hls_native_pilot_v1.json`, SHA-256
  `434506c52494d4473c8a1cf6664db67e211075e255f6f26ee893bdafa0954272`.
- Qualified manifest: `research/manifests/hls_native_qualified_v1.json`, SHA
  `5d1efc20f8ed9e33173824c4d19786d6ca10fcabf1ab50c00a4c2eb6bb7f2a19`.
- Model: unchanged N64/B32/H64 Conv-TasNet, 171,313 parameters. Every fold fresh
  seed 20260928; no T4/T7/external/v2 initialization and no optimizer carryover.
- CPU: Python 3.14.4, torch/torchaudio 2.11.0+cpu, two compute threads and one
  interop thread. No dependency, GPU or system-driver changes.
- Exactly 576 updates per fold; AdamW LR 0.001, decay 0.0001, clipping 5,
  constant LR, no scheduler/early stopping/checkpoint selection. Endpoint only.
- Preserve the exact control's 2,304 synthetic draws. Add 2,304 native draws:
  batch four per stream, `Lsynthetic + 0.25 Lnative`, both using unchanged
  fixed-label mean negative SI-SDR plus five times RMS-normalized L1. Extra
  compute is explicit. No weight or ratio search.
- Native hierarchy: heart family → available lung family → triplet → common
  eight-second crop. Original released M is input; targets are gH/gL; divide
  all by cropped mixture peak. Preserve released native levels, approximately
  −21.34…+13.26 dB; synthetic uniform −10…+10 dB remains unchanged. This is a
  data/supervision intervention, not an isolated test of any one level regime.
- Native counts by fold: 17/22/16/15/13. Both source families must be training
  families before any native WAV is opened by the training loader.
- Reused valid historical HLS-only controls at update 576, not the old narrow
  ~3.1 dB validation result. Fresh state hashes, exact synthetic receipt prefixes,
  optimizer/environment, folds and all validation recipes match. No control
  training was repeated.

Evaluation used the unchanged 1,775 synthetic conditions in five folds/eight
held-out family-pair groups. Macro source means average the eight pair means
equally; Q is their weaker source, M their balanced average. Neither 1,775 rows
nor eight pair groups establish independent-patient sampling. T9 is not among
these conditions.

## Completed target-domain validation

All values below are **NON-TEST GROUPED VALIDATION**, not final-test results.

| Metric, dB unless noted | Matched HLS control | Qualified-release treatment | Difference |
|---|---:|---:|---:|
| Heart SI-SDR | 2.021192 | 2.058859 | +0.037667 |
| Heart SI-SDRi | 2.012519 | 2.050186 | +0.037667 |
| Lung SI-SDR | 1.922089 | 0.840476 | −1.081613 |
| Lung SI-SDRi | 1.913416 | 0.831803 | −1.081613 |
| Weaker-source Q | 1.913416 | 0.831803 | −1.081613 |
| Balanced mean M | 1.962968 | 1.440995 | −0.521973 |
| Negative-heart-condition rate | 24.789% | 19.944% | −4.845 pp |
| Negative-lung-condition rate | 28.732% | 35.662% | +6.930 pp |
| Numerical failures | 0 | 0 | 0 |

Zero numerical failures does not mean successful separation of every condition.

| Held-out family pair | Δ Heart SI-SDRi | Δ Lung SI-SDRi | Δ balanced mean |
|---|---:|---:|---:|
| Atrial Fibrillation × Wheezing | −0.022 | −0.111 | −0.066 |
| Early Systolic Murmur × Rhonchi | +0.158 | +0.026 | +0.092 |
| Late Diastolic Murmur × Fine Crackles | −0.396 | −3.074 | −1.735 |
| Late Systolic Murmur × Wheezing | +0.142 | +0.098 | +0.120 |
| Mid Systolic Murmur × Normal | +0.087 | −0.137 | −0.025 |
| Normal × Pleural Rub | +0.888 | −0.028 | +0.430 |
| S3 × Fine Crackles | −0.502 | −5.075 | −2.789 |
| Tachycardia × Rhonchi | −0.053 | −0.353 | −0.203 |

Only 3/8 pair balanced means and 2/5 fold Q scores improved. Fine Crackles
treatment lung means were −0.465 dB with Late Diastolic Murmur and −1.547 dB
with S3. These are important regressions, not grounds for another tuning run.

## Predeclared adoption gate: FAIL

The frozen rule required **all** clauses: ΔQ/ΔM ≥0.5 dB; both source gains ≥0.25;
at least6/8 pair-M and4/5 fold-Q improvements; no pair/source regression over
0.5 dB; no numerical failures; negative-rate increase no more than5pp; absolute
source macro SI-SDRi ≥1 dB and every pair/source mean ≥0. The 0.5-dB engineering
margin reused the previous data programme and exceeded twice the observed
~0.227-dB seed-Q difference. It is not a statistical significance threshold.

Only the numerical-failure clause passed. Gate receipt:
`research/evidence/hls_native_pilot_decision_v1.json`, SHA-256
`7e6fccc082e669aad28de7a7db672d77c17de615fbfb2cb438b06ea73562ec8e`.
It retains full metrics, pair/fold differences, identity proof and artifact hashes.

## Runtime, artifacts and validity checks

Artifacts are ignored under `.local/training/stethofuse-native-v1/`.

| Run ID | Updates | Runtime, s | Endpoint SHA-256 |
|---|---:|---:|---|
| native-f1-seed20260928 | 576 | 166.605 | `819b764f6d8a49ba9e379016e0701a1291b4ec063ff43b52949bbb82355baed2` |
| native-f2-seed20260928 | 576 | 164.762 | `8b10c1186989640ef0a8fc073e4165ac2a13894cfe2ac38e1782ea4d019964a2` |
| native-f3-seed20260928 | 576 | 163.991 | `17467cdc87f24a56a62d76aa3720edab9a61315e1bc64a0b19077f25cc72e693` |
| native-f4-seed20260928 | 576 | 161.716 | `4272a71b0b0579c881367b1d004200cac43a7455ad2deba2e71871d094428fe1` |
| native-f5-seed20260928 | 576 | 158.435 | `72f3d155a6b61d86e1926ba4d20824372b360e55eb94b93a98ec57da273a5bab` |

Total treatment runtime **815.510 s (13.59 min)**, peak RSS **1,096.527 MiB**;
2,880 updates across five independent fresh fold models. These are five folds
of one treatment, not five searched configurations. All stopped at the fixed
endpoint. Model, optimizer, RNG, dual recipe cursor, history, resume/endpoint
checkpoints and hashes were retained; no crash/restart occurred.

Both training-stream losses improved from the first to final reporting interval
in every fold. Gradients and outputs stayed finite; clipping remained enabled.
The strongest validation loss was lung transfer in f5, not numerical divergence.
Recording diversity, fixed pair correlations and level/domain emphasis are
plausible mechanisms, but this single treatment does not isolate their causes.
No source-order, mixture-consistency or data-leakage implementation defect was
found. Therefore the negative result is retained rather than retrained.

Five focused tests passed (registry/guard and native-stream checks), plus synthetic
lag/PSD sanity and all11,520 planned crop materializations. Maximum crop residual
was0.003981 of weaker-source RMS. Native forward/backward was finite with zero
preflight optimizer updates. A new reporting path-comparison issue was fixed
before training (absolute versus relative artifact keys); it did not alter
metrics or invalidate any run. No broad application tests were run.

## Final separator and stopping boundary

**Retain HLS-only T8 v2. No v3 or native final refit exists.**

- Specification `research/configs/final_separator_v2.json`, unchanged SHA
  `2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b`.
- Checkpoint `.local/training/stethofuse-tcn-v1/pre-t9-family-refit-v1/refit-all-nontest-seed20260928/checkpoints/endpoint.pt`, unchanged SHA
  `1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658`.
- Existing171313-parameter, seed20260928, fresh HLS-only576-update endpoint;
  4kHz mono,10swindow/8shop/2soverlap, fixed heart/lung outputs, raw waveform
  plus target-free equal-residual consistency. No projection or ensemble.
- V1 remains preserved and previously superseded by v2; v2 was not superseded
  by this experiment. No post-pilot choice among fold checkpoints is allowed.

All configured MCP/auth checks passed without sign-in; see the N0 receipt.
Read-only Cloudflare preflight did not mutate infrastructure. T9 audio/recipes/
statistics/results, production, frontend, demographic classifiers and FYP1 were
not accessed or changed by this work. The already-frozen225-condition T9 protocol
and comparators remain unchanged. Separate owner authorization is still needed.

**READY FOR T9 WITH HLS-ONLY T8 V2. STOP.**
