# T9 final held-out evaluation

29 September 2026. **T9 VALID AND COMPLETE · FINAL T8 V2 EVALUATED · TEST
CONSUMED · MODEL SELECTION CLOSED · NOT DEPLOYED.** The first T9 waveform was
opened only after the final model, specification, runner, and one-shot protocol
were frozen and the runner commit was pushed. The complete 225-condition run
finished with all four methods and zero failures. No model, comparator,
preprocessing, metric, or condition was changed in response to results.

## Frozen run identity

Run ID: `t9-final-heldout-v1`. The exact implementation SHA that opened T9 was
`e343102692efa0187d1c2e0b75e53c318b579f85` on `fyp2/application`; its worktree
was clean and the commit was remote-matched before the run. Documentation
starting SHA was `944a646e09da466040d22b6de0af6e05fe3b0d77`, also clean. First
waveform access: `2026-09-28T21:42:52.641041+00:00` (first source `HS/M_AVB_A`).
Protocol SHA-256: `c2c884211a2a7361aedcea7eaadb2ab752a853200b10e6ca244c4dee3692822c`;
source-manifest SHA-256:
`39d5456477b07772bdc24b86ee73dee17c44fd1e0837b62b96eab8c19a1b65e4`.

The model was HLS-only T8 v2, compact Conv-TasNet N64/B32/H64, 171,313
parameters, seed 20260928, 576 updates, checkpoint
`1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658`; frozen
specification `research/configs/final_separator_v2.json`, SHA-256
`2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b`.
Strict loading, pinned environment, 171,313 parameter count, 4-kHz CPU
inference, 10-second windows/8-second hop/2-second overlap, output order
heart/lung, and target-free equal-residual mixture consistency were verified
before access. No projection or ensemble.

T9 used 5 heart × 9 lung sources × levels −10, −5, 0, +5, +10 dB = 225 full
15-second conditions. All four methods received the same generated mixture
for each condition: mixture baseline, selected Conv-TasNet, Fixed Filter, and
Generic NMF. The execution order follows the frozen specification. NMF used
six components, 80 iterations, seed 42 per inference window. Metrics were the
frozen zero-mean SI-SDR (epsilon 1e-8) and same-condition mixture-baseline
SI-SDRi. Aggregation averaged within each family pair, then weighted family
pairs equally; condition medians/IQR are descriptive, not IID uncertainty.

## Aggregate results

All scores are dB. Mixture SI-SDRi is zero by definition under the frozen
same-mixture comparison.

| Method | Heart SI-SDR | Heart SI-SDRi | Lung SI-SDR | Lung SI-SDRi | Failures | Inference total |
|---|---:|---:|---:|---:|---:|---:|
| Original mixture baseline | −0.037 | 0.000 | −0.037 | 0.000 | 0 | 0.003 s |
| Fixed Filter | 0.325 | 0.362 | −2.484 | −2.447 | 0 | 1.077 s |
| Generic NMF | −2.503 | −2.466 | −3.444 | −3.407 | 0 | 4.180 s |
| Final T8 v2 Conv-TasNet | 1.813 | 1.849 | 2.296 | 2.333 | 0 | 11.140 s |

For the final Conv-TasNet, pooled condition medians and IQRs were Heart
SI-SDRi **2.146 dB (IQR 3.332)** and Lung SI-SDRi **1.691 dB (IQR 4.975)**.
The median/IQR describes the 225 fixed correlated remix conditions only.

## Family-pair and relative-level results

The test partition contains only **two** observed family-pair groups, so the
225 remix conditions do not imply 225 independent families or subjects.
Final Conv-TasNet family-pair macro results:

| Heart × lung family | Heart SI-SDR | Heart SI-SDRi | Lung SI-SDR | Lung SI-SDRi | Balanced SI-SDRi | Conditions | Failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| AV Block × Coarse Crackles | 0.742 | 0.784 | 1.068 | 1.111 | 0.947 | 135 | 0 |
| S4 × Coarse Crackles | 2.884 | 2.915 | 3.523 | 3.555 | 3.235 | 90 | 0 |

Strongest pair by balanced SI-SDRi was **S4 × Coarse Crackles**; hardest was
**AV Block × Coarse Crackles**. This is descriptive of the frozen partition,
not evidence of patient-level or broad family generalization.

| Lung-to-heart level | Heart SI-SDRi | Lung SI-SDRi | Balanced mean | Conditions |
|---:|---:|---:|---:|---:|
| −10 dB | −1.744 | 3.862 | 1.059 | 45 |
| −5 dB | 0.982 | 3.602 | 2.292 | 45 |
| 0 dB | 2.627 | 2.950 | 2.788 | 45 |
| +5 dB | 3.205 | 1.402 | 2.303 | 45 |
| +10 dB | 3.112 | −1.374 | 0.869 | 45 |

The hardest descriptive level was −10 dB for heart and +10 dB for lung. The
aggregate source gains are both positive and differ by about 0.483 dB, but the
extreme-level pattern is asymmetric: the weaker heart is difficult at −10 dB,
and the weaker lung is difficult at +10 dB.

## Comparisons and interpretation

The final separator's Heart and Lung SI-SDRi were both positive. Against Fixed
Filter, its macro gains were +1.487 dB Heart and +4.779 dB Lung; against
Generic NMF, +4.315 dB Heart and +5.740 dB Lung. These comparisons apply only
to this frozen HLS-CMDS evaluation and comparator configuration.

Prior grouped non-test fold control macros were Heart/Lung SI-SDRi
2.013/1.913 dB. T9 v2 results were 1.849/2.333 dB (descriptive differences
−0.163/+0.419 dB). These are not paired estimates of a common population: the
fold model scores summarize training-fold endpoints, whereas T9 evaluates the
final all-non-test endpoint on two held-out family-pair groups. No uncertainty
or statistical-significance claim is made. This is the first held-out
performance evidence for the exact final v2 endpoint.

This remains a controlled HLS-CMDS held-out-source evaluation on manikin
recordings. It does not establish clinical effectiveness, diagnostic
accuracy, patient-/subject-independent generalization, or superiority beyond
these tested conditions. The limited family-pair coverage is a key limitation.

Treatment A remains a **promising non-test research result, not selected for
T9**: it improved all 8/8 grouped family-pair means and 5/5 fold Q values, but
missed the predeclared +0.50 dB ΔQ and balanced-mean gates (+0.4855/+0.4886
dB). Those gates were not relaxed; Treatment A was not evaluated on T9.

## Runtime, artifacts, and stop boundary

CPU inference time over 225 conditions: Fixed Filter 1.077 s (mean 0.00479 s,
median 0.00467 s/condition); Generic NMF 4.180 s (mean 0.01858 s, median
0.01822 s); Conv-TasNet 11.140 s (mean 0.04951 s, median 0.04870 s). Model
initialization was 0.034 s; overall run wall time was 18.842 s. These are
offline measurements, not production latency.

Ignored/local run directory:
`.local/training/stethofuse-tcn-v1/t9/t9-final-heldout-v1/`. It contains the
immutable preflight, first-access marker, recipe manifest, per-condition
JSONL, summary, and completion receipt. SHA-256 values:

- Recipe manifest: `1de947075c1feb73376f131c7a76284df9f5e945b02428e750bb88cc51c59f28`
- Raw 900-row results: `b4491f1443cff869353cfde0c798d6d50c8065f6714b927b77ec14ecef65749c`
- Summary: `c2f91be43ca607fd920477008179553377c10d4b2a2dd45577f49b5651966221`
- Completion receipt: `a67501d11e1030021a194cd7d33d2c3a2ea5c7925152b36c267d653421cd846b`

No rerun, extra method, TF U-Net test, training, tuning, or deployment follows.
T9 is consumed. Model selection and pre-test tuning are closed. The owner
should review these results before any separate application-integration work.
**T9 VALID AND COMPLETE — READY FOR OWNER REVIEW. STOP.**
