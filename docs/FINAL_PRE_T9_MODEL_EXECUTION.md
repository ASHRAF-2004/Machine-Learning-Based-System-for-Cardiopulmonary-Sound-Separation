# Final pre-T9 model comparison — execution record

29 September 2026. **COMPARISON COMPLETE · CONTROL SELECTED · T8 V2 RETAINED ·
T9 SEALED · NOT DEPLOYED.** Both frozen treatments were executed under the
predeclared grouped-family protocol. Neither passed the complete adoption gate.
No rescue experiment, final refit, or T9 run is authorized by this result.

## Integrity and protocol

Starting implementation/documentation HEADs were `c582159e80540a83197ba57071f1468b276f721b`
and `8c4d176176a4c1490c8a1987689fb8189224ac4a`. Required MCP/auth checks and
GitHub identity `ASHRAF-2004` passed. Graphify was reachable but its index was
stale for the current ML paths; narrow source inspection followed. No login,
environment, dependency, driver, or production change was made. Treatment code
was committed and pushed before scored runs as implementation commit
`7d18f010b6ac247aab9f6b36b9daa379d2485536`.

The machine plan is `research/configs/final_pre_t9_model_plan_v1.json`
(SHA-256 `6776e53c1d53c66d39c8882169b6de729bc05358f337e26a91257fd74dce8103`).
It binds the five folds, eight held-out family-pair groups, 1,775 correlated
conditions, 20260928 seed, exact synthetic-HLS recipes, environment, and gate.
All treatment folds were fresh initializations with exactly 576 updates,
batch 4, AdamW at constant 0.001, weight decay 0.0001, and gradient clipping 5.
Only the exact synthetic HLS stream was used. The saved matched control was
verified and reused; it was not retrained. Python 3.14.4, torch 2.11.0+cpu,
torchaudio 2.11.0+cpu; CPU only.

The authoritative machine-readable decision is
`research/evidence/final_model_comparison_decision_v1.json` (SHA-256
`09890e6bfd714fef5583280318fde13d51bd0228310685bd9051f04c5e09428e`). It
contains the per-fold and per-pair metrics, gates, run provenance and endpoint
hashes. Run artifacts/checkpoints are local and ignored, not committed.

## Treatment definitions and execution checks

Treatment A was the specified 390,450-parameter complex-mask TF U-Net: STFT
256/256/64, periodic Hann, centered zero padding, 129 bins, four specified
mixture-only features, 8/16/32/64 encoder, 96-channel bottleneck, mirrored
decoder, complementary complex masks, ISTFT and unchanged equal-residual
consistency. The fixed development-only capacity gate passed at update 180
(13.957 s; peak RSS 620.47 MiB). All four case/source pairs exceeded +10 dB
SI-SDRi and 50% normalized waveform-L1 reduction:

| Pair | Heart SI-SDRi / L1 reduction | Lung SI-SDRi / L1 reduction |
|---|---:|---:|
| F_AF_A / F_N_LLA | +10.782 dB / 68.58% | +10.785 dB / 68.63% |
| F_ESM_LLSB / F_PR_LLA | +10.011 dB / 68.02% | +10.035 dB / 67.72% |

The gate endpoint hash is recorded in the decision JSON; this checkpoint did
not initialize any grouped fold. Focused checks also passed for parameter
count, STFT/ISTFT length and reconstruction, finite forward/backward, zero
input, mask complementarity, consistency, semantics, and deterministic seeded
initialization.

Treatment B kept the 171,313-parameter Conv-TasNet unchanged and added exactly
`6.0 * L_sp`, where `rho=RMS(target)+1e-6`,
`A(z)=abs(STFT(z/rho))/sqrt(96)`, and `L_sp` is mean absolute difference of
`log1p(A(prediction))` and `log1p(A(target))` over batch/source/frequency/time.
The one-step synthetic-only loss/gradient/optimizer sanity check passed; model
parameter count, semantic order, and mixture consistency were unchanged. Five
focused tests passed. No broad application suite was run.

## Matched grouped-family results

All rows below are equal-weight means across the same eight family-pair groups;
1,775 mixture conditions are correlated and are not treated as IID subjects.
`Q=min(Heart SI-SDRi,Lung SI-SDRi)`; balanced mean is the arithmetic mean of
the two source macros.

| Arm | Heart SI-SDR | Heart SI-SDRi | Lung SI-SDR | Lung SI-SDRi | Q | Balanced mean | Failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| Matched control | 2.021 | 2.013 | 1.922 | 1.913 | 1.913 | 1.963 | 0 |
| A: complex TF | 2.513 | 2.504 | 2.408 | 2.399 | 2.399 | 2.452 | 0 |
| B: spectral TCN | 2.090 | 2.082 | 2.026 | 2.017 | 2.017 | 2.049 | 0 |

| Arm | Δ Heart macro | Δ Lung macro | ΔQ | Δ balanced | Pairs with balanced gain | Folds with Q gain | Worst pair/source Δ | Negative-rate Δ H/L (pp) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | +0.492 | +0.485 | +0.485 | +0.489 | 8/8 | 5/5 | +0.114 | −5.13 / −4.73 |
| B | +0.069 | +0.104 | +0.104 | +0.086 | 5/8 | 4/5 | −0.109 | −1.75 / −1.30 |

The detailed family-pair outcomes (treatment Heart/Lung SI-SDRi and change in
pair balanced mean relative to control) were:

| Held-out family pair | Control H/L | A H/L (Δ pair mean) | B H/L (Δ pair mean) |
|---|---:|---:|---:|
| Atrial Fibrillation × Wheezing | 2.984 / 2.739 | 3.623 / 2.858 (+0.379) | 2.875 / 2.639 (−0.104) |
| Early Systolic Murmur × Rhonchi | 1.246 / 0.807 | 1.599 / 1.041 (+0.294) | 1.336 / 0.883 (+0.083) |
| Late Diastolic Murmur × Fine Crackles | 2.836 / 2.609 | 3.180 / 3.570 (+0.652) | 3.022 / 2.965 (+0.271) |
| Late Systolic Murmur × Wheezing | 0.476 / 0.985 | 1.535 / 1.610 (+0.842) | 0.371 / 0.945 (−0.073) |
| Mid Systolic Murmur × Normal | 1.890 / 1.436 | 2.113 / 1.587 (+0.187) | 1.899 / 1.446 (+0.010) |
| Normal × Pleural Rub | 1.220 / 1.444 | 2.142 / 2.224 (+0.851) | 1.504 / 1.589 (+0.214) |
| S3 × Fine Crackles | 3.539 / 3.528 | 3.707 / 4.428 (+0.534) | 3.774 / 3.975 (+0.341) |
| Tachycardia × Rhonchi | 1.909 / 1.759 | 2.134 / 1.873 (+0.169) | 1.870 / 1.696 (−0.051) |

Fold Q deltas (f1–f5) were A `+0.151,+0.923,+0.174,+0.504,+0.375 dB` and B
`+0.011,+0.284,+0.006,−0.107,+0.330 dB`. All arms covered all 1,775 conditions
with zero numerical/execution failures. Condition-level medians/IQRs and exact
fold/source values are in the JSON receipt; no IID confidence interval or
significance claim is made.

## Frozen gate and final selection

The predeclared gate required *all* clauses: ΔQ≥0.50 dB; Δ balanced mean≥0.50;
each source macro gain≥0.25; balanced pair gain in≥6/8; fold-Q gain in≥4/5;
no pair/source loss below−0.50; negative-condition-rate increase≤5 pp per
source; zero failures; each absolute source macro≥1 dB; and every held-out
pair/source mean≥0 dB. It was applied unchanged.

- **A FAIL:** only two required aggregate margins were missed: ΔQ `+0.4855`
  and Δ balanced `+0.4886` dB. All other clauses passed, including 8/8 pair,
  5/5 fold, and zero failures. These near misses do not authorize relaxing the
  gate.
- **B FAIL:** Δ Heart `+0.069`, Δ Lung `+0.104`, ΔQ `+0.104`, and Δ balanced
  `+0.086` dB missed their frozen margins; balanced pair gains were 5/8.
  Remaining clauses passed, with 4/5 folds and zero failures.

Therefore the frozen rule selects **CONTROL / HLS-only T8 v2**. No final
all-non-test refit was authorized or performed; no v3 was created. V1 and v2
specifications/checkpoints remain preserved. Active v2 specification SHA-256
is `2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b` and its
checkpoint SHA-256 is
`1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658`.
**Model development under this final comparison ends.**

## Runtime, provenance and safety

Treatment A's five folds took 635.059 CPU seconds total (121.538–129.447 s per
fold); peak RSS was 943.266 MiB. Treatment B took 525.005 seconds total
(101.955–107.351 s/fold); peak RSS was 1,044.559 MiB. Together the ten scored
folds took 1,160.064 seconds (19.33 minutes), excluding the 13.957-second
capacity gate and focused checks. Per-fold endpoint checkpoint SHA-256, run ID,
configuration, recipe, runtime and environment are in the machine receipt and
ignored run artifacts.

No T9 audio, T9 mixtures, T9 descriptors or T9 metrics were accessed/generated.
No external/native data, new seed, extra treatment, tuning, final refit,
deployment, production system, or frontend was touched. This is grouped
non-test validation evidence only, not a final-test performance claim.

**Status: READY FOR T9 WITH HLS-ONLY T8 V2, subject to the separate owner
authorization for T9. STOP.**
