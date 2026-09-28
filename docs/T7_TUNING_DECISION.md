# ADR T02 — One capacity experiment after the first baseline

2026-09-28. **BASELINE AND T7 TRAINED / VALIDATION EVALUATED / FINAL TEST
SEALED / NOT DEPLOYED.** The baseline remains a valid control and candidate.
The tuning decision first analyzed saved T5/T6 metrics; offline execution
results are recorded below. No test audio/recipes or production data/services
were touched.

## Decision

**T7 variant 1: the already-designed smaller Conv-TasNet**, N64/B32/H64,
171,313 parameters under pinned torchaudio, scratch seed 20260928. Change only
the width profile from
N128/B64/H128 (645,681 parameters); preserve depth, temporal context, loss,
data, optimizer, scheduler, stopping, labels and validation selector.

**T7 variant 2: NONE.** Do not spend another validation-selection opportunity
without evidence for a specific intervention. In particular, do not reduce
L1 weight, increase decay, add dropout, or alter gain sampling now.

**Seed confirmation: COMPLETED exactly once, seed 20260929, for the selected
small profile.** Retain the selected seed-20260928 checkpoint as canonical.
The confirmation changed initialization and keyed training draws together;
validation was unchanged. Its score does not replace the primary checkpoint or
select another configuration.

The smaller width was originally a resource fallback. The owner's current
tuning-decision request explicitly permits evaluating it as a capacity
hypothesis. This ADR makes that change of purpose explicit; it does not change
the historical baseline config or imply that smaller is already better.

The original estimate was 170,545 parameters. A construction-only check with
pinned torchaudio 2.11.0+cpu and the exact approved N64/B32/H64, L32/X8/R3
settings produced **171,313** (768 more; about 0.45%). The baseline profile
remains exactly 645,681 and its saved checkpoint loads strictly. This corrects
the small-profile count estimate, not its architecture or the baseline; the T7
configuration records the measured count. Width reduction is about 73.5%.

## Evidence and aggregation

Inspected implementation HEAD `e256c79025dd00c5379f7fd9e55b1ab45027d948` and
documentation HEAD `ede21f68b8dcc6497fc45f5c27b55f4730db677e`, both clean.
Baseline ran at clean code commit `bfe879f6dfcc5032d4350537eafe9369e9d8e4f3`.
All numbers below come from ignored
`.local/training/stethofuse-tcn-v1/baseline-seed20260928/`: `history.jsonl`,
`validation/best_checkpoint_per_condition.jsonl`, frozen validation recipes,
saved per-epoch validation rows and training recipe metadata. Their relevant
SHA-256 entries matched the existing `checksums.sha256`.

There are 9 heart files (6 Late Diastolic Murmur, 3 Tachycardia), 5 Fine
Crackles lung files, 45 file pairs and five levels: **225 correlated conditions
in just two family-pair groups**. Family-macro means give each group half the
weight; pooled statistics weight its 150 versus 75 conditions. Medians and IQR
below are descriptive condition statistics using NumPy linear quantiles, not
independent-replicate confidence bounds. No significance test is warranted.

### Best-checkpoint distribution (epoch 8)

Each row is one source within a family pair. `negative i` counts negative
SI-SDRi, not runtime failures; runtime failures were zero.

| Heart family × Fine Crackles | Source | Conditions | Mean SI-SDR | Mean SI-SDRi | Median SI-SDRi | IQR SI-SDRi | Negative i |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Late Diastolic Murmur | Heart | 150 | 3.891 | 3.847 | 3.202 | 3.324 | 5/150 |
| Late Diastolic Murmur | Lung | 150 | 3.757 | 3.713 | 3.507 | 4.518 | 19/150 |
| Tachycardia | Heart | 75 | 2.171 | 2.223 | 2.104 | 5.651 | 23/75 |
| Tachycardia | Lung | 75 | 2.393 | 2.445 | 2.052 | 4.270 | 16/75 |

All scores are dB. Both groups improve both sources on average and remain
fairly balanced *within their group averages*. Tachycardia is weaker and
contains 23 of the 28 negative heart-improvement conditions despite having
one-third of pooled rows. This is meaningful heterogeneity, not justification
to remove/reweight a family. Its equal macro weight is already intentional.

Overall macro H/L SI-SDRi is 3.035/3.079; Q 3.035; average 3.057. Pooled H/L
SI-SDRi medians are 2.973/2.848, IQR 3.877/4.581. Pooled absolute SI-SDR medians
are 3.701/4.212 with IQR 9.458/7.909: gains make absolute-score spread much wider.

### Relative-level dependence

Positive level means lung is louder. Means below use the same equal-family
macro weighting at each level; all 45 file pairs occur at each level.

| Lung/heart dB | Heart SI-SDR | Heart SI-SDRi | Lung SI-SDR | Lung SI-SDRi | Negative i, H/L (of 45 each) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| −10 | 9.733 | −0.267 | −4.768 | 5.245 | 17 / 2 |
| −5 | 7.129 | 2.129 | −0.165 | 4.840 | 4 / 1 |
| 0 | 3.734 | 3.735 | 3.821 | 3.823 | 3 / 2 |
| +5 | −0.367 | 4.638 | 7.002 | 2.003 | 2 / 8 |
| +10 | −5.073 | 4.940 | 9.483 | −0.517 | 2 / 22 |

| Lung/heart dB | Pooled heart SI-SDRi median (IQR) | Pooled lung SI-SDRi median (IQR) |
| ---: | ---: | ---: |
| −10 | 0.697 (2.030) | 5.735 (5.380) |
| −5 | 2.215 (2.590) | 5.185 (4.400) |
| 0 | 3.209 (3.466) | 4.028 (3.505) |
| +5 | 4.112 (4.025) | 2.003 (3.239) |
| +10 | 4.721 (3.963) | 0.093 (4.083) |

The quieter source generally gains SI-SDRi while remaining poor in absolute
SI-SDR at the extremes. The already-dominant source sometimes loses quality
relative to its much stronger mixture baseline. Overall H/L balance therefore
does **not** imply per-condition balance or universally useful reconstruction.
Endpoints contain 19/28 heart and 24/35 lung negative-improvement conditions.

At −10 dB, Tachycardia heart mean improvement is −1.953 versus +1.418 for Late
Diastolic Murmur; the former has 12/15 negative cases. At +10 dB, dominant-lung
mean improvement is negative in both groups (−0.460/−0.574 respectively).
This is an interaction of source family and level, not exclusively one endpoint.

Training metadata shows 11,520 draws across 20 epochs with equal-width gain-bin
counts 2317/2363/2283/2281/2276 over [−10,−6,−2,2,6,10]; 2268 draws (19.7%) have
|level| ≥8 dB. No silent-crop retries occurred. There is no demonstrated missing
gain range or sampling defect. Oversampling validation endpoints now risks
specializing to this very small validation set; keep the generator frozen.

### Persistent low conditions

The three worst file pairs by the smaller of their five-level mean H/L
improvements all use heart `F_T_RC`:

| Heart / lung pair | Heart mean SI-SDRi | Lung mean SI-SDRi |
| --- | ---: | ---: |
| F_T_RC / M_FC_RLA | −2.394 | −1.378 |
| F_T_RC / F_FC_LUA | −2.251 | −0.749 |
| F_T_RC / F_FC_RLA | −1.104 | 0.157 |

Across all 25 conditions with `F_T_RC`, mean H/L improvement is −0.097/+0.355;
other Tachycardia files differ materially (`F_T_A`: 1.885/1.924;
`M_T_LUSB`: 4.883/5.055). Sound-family averages hide file-level difficulty too.

Worst heart improvement: F_T_RC/F_FC_LUA at −10 dB,
condition `0a9fcd323d5e3262d5dd`: H SI-SDR 4.977, improvement −5.073;
L SI-SDR −9.570, improvement −0.040. Worst lung improvement:
F_T_RC/M_FC_RLA at +10 dB, `80507980b6c48db6bfb4`: H SI-SDR −10.806,
improvement −1.469; L SI-SDR 5.719, improvement −4.352. Retain every condition.
Scores alone do not prove corrupt data, a label error, or a physiological cause.

All validation recipes use the same full 15 seconds and source starts (0,0).
There is no variable validation crop to diagnose. The logs do not contain
per-window outputs; no claim about local boundary artifacts is supported.

## Training dynamics and loss contribution

`N` is the recorded mean negative SI-SDR; `A` is unweighted normalized L1.
Total loss = N+5A. `H_i,L_i,Q` are full-record validation macro scores.
Training uses changing 8-s draws and evolving parameters within each epoch;
its online loss is not a matched full-record training evaluation.

| Epoch | Total | N | A | 5A | H_i | L_i | Q | LR used for updates |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1.397 | −1.302 | .540 | 2.700 | 2.150 | 1.666 | 1.666 | .001 |
| 2 | −.404 | −2.838 | .487 | 2.435 | 2.968 | 2.810 | 2.810 | .001 |
| 3 | −.840 | −3.200 | .472 | 2.360 | 2.867 | 2.920 | 2.867 | .001 |
| 4 | −1.128 | −3.462 | .467 | 2.334 | 2.718 | 2.588 | 2.588 | .001 |
| 5 | −1.399 | −3.678 | .456 | 2.279 | 2.870 | 2.810 | 2.810 | .001 |
| 6 | −1.488 | −3.741 | .451 | 2.254 | 2.682 | 2.496 | 2.496 | .001 |
| 7 | −1.761 | −3.976 | .443 | 2.216 | 2.668 | 1.767 | 1.767 | .001 |
| 8 | −2.215 | −4.313 | .420 | 2.098 | 3.035 | 3.079 | 3.035 | .0005 |
| 9 | −2.226 | −4.314 | .418 | 2.088 | 2.695 | 2.350 | 2.350 | .0005 |
| 10 | −2.546 | −4.574 | .406 | 2.028 | 1.609 | 2.748 | 1.609 | .0005 |
| 11 | −2.654 | −4.662 | .402 | 2.008 | 2.720 | 2.013 | 2.013 | .0005 |
| 12 | −2.725 | −4.726 | .400 | 2.001 | 2.929 | 3.132 | 2.929 | .0005 |
| 13 | −2.833 | −4.811 | .396 | 1.978 | 2.561 | 3.195 | 2.561 | .0005 |
| 14 | −3.159 | −5.089 | .386 | 1.931 | 2.449 | 2.757 | 2.449 | .00025 |
| 15 | −3.262 | −5.173 | .382 | 1.911 | 2.283 | 2.619 | 2.283 | .00025 |
| 16 | −3.384 | −5.276 | .378 | 1.892 | 2.945 | 1.716 | 1.716 | .00025 |
| 17 | −3.271 | −5.168 | .379 | 1.896 | 2.963 | 3.077 | 2.963 | .00025 |
| 18 | −3.622 | −5.473 | .370 | 1.851 | 2.486 | 2.762 | 2.486 | .00025 |
| 19 | −3.722 | −5.555 | .367 | 1.833 | 2.259 | 2.720 | 2.259 | .000125 |
| 20 | −3.706 | −5.535 | .366 | 1.829 | 2.688 | 2.508 | 2.508 | .000125 |

**Reporting correction:** the runner calls `scheduler.step(q)` after validation
and stores `new_lr` as `learning_rate`. Reductions after epochs 7,13,18 take
effect for updates in 8,14,19. Earlier receipt prose interpreted logged LR as
the just-completed epoch's LR. The table above corrects that one-epoch label;
no computation/run/checkpoint is changed. Epoch 8 is the first reduced-LR epoch.

- 5A exceeds |N| in epoch 1 (2.700 versus 1.302). From epoch 2 onward |N| is
  larger; at 8 the ratio 5A/|N| is 0.486, at 20 it is 0.330. Comparing to the signed
  total near cancellation would misleadingly suggest domination.
- From 8→20, training SI-SDR improves from 4.313 to 5.535 dB and A declines from
  .4196 to .3658. Of the 1.4907 total loss reduction, 1.2216 (82%) comes from the
  SI-SDR term and .2691 (18%) from 5A. Both terms generally improve, with normal
  late-epoch fluctuations. This does **not** support SI-SDR being sacrificed
  to L1. Validation SI-SDRi plateaus while *both* training terms improve.
- Scalar magnitudes are not gradient attribution. Separate loss gradients,
  held-fixed training evaluations and validation L1 were not logged, so the
  evidence cannot prove either gradient dominance or absence of all conflict.
  Do not infer a need to lower the coefficient from these logs.
- Post-best variation is real despite fixed validation recipes. Q at 12 and 17
  returns to 2.929 and 2.963, near best 3.035. Narrow family coverage and changing
  training draws/weights are relevant; this is not re-randomized validation.
  From 8→20 Tachycardia heart improvement falls 2.223→1.623, while the other
  heart group changes 3.847→3.752. Lung declines in both (3.713→2.656 and
  2.445→2.361). No single monotonic group-collapse explanation fits all epochs.
- All 20 epochs report finite gradients/loss and zero validation failures.
  Logged preclip maxima range 19.05–75.58; clipping at 5 was active. Maxima do
  not give clipping frequency or per-loss gradient magnitudes. There is no
  demonstrated divergence requiring a new LR.

## Ranked diagnosis and experiment rationale

| Hypothesis | What the existing evidence supports | Decision |
| --- | --- | --- |
| Narrow validation and family/level heterogeneity | Directly observed: two groups, persistent F_T_RC difficulty, ratio-dependent losses and non-monotonic checkpoint scores. Limits all causal/generalization claims. | Preserve split and all 225 conditions; one variant only. |
| Capacity/generalization pressure | Training improves beyond epoch 8 while validation stalls. 645,681 parameters, 72 unique training files/18 min combined audio, 10 training families; remixes do not add independent sources. The large model fitting two examples at T4 rules out that capacity failure, but proves neither excess capacity nor small-model sufficiency. | Test the existing 171,313-parameter width profile, a 73.5% parameter reduction, after a bounded capacity gate. |
| L1 objective mismatch | Both training objectives improve; 82% of post-best loss decrease is from SI-SDR. Gradient conflict unmeasured. | Keep coefficient 5. No loss variant. |
| Too little explicit regularization | Compatible with the same plateau, but no weight-norm/decay ablation evidence selects a decay value; dropout is absent and would add a mechanism. | Keep decay 0.0001; no dropout. Capacity test is the one selected intervention. |
| Gain/crop defect or missing range | Realized gain bins are near-uniform, no silent retries; full validation crops fixed. Endpoint weakness is real but not proof of a generator error or missing training conditions. | Keep sampling/augmentation exactly frozen; no endpoint over-weighting or source exclusion. |
| LR instability | Finite training and improving components; a single improvement after a scheduled drop is not an LR experiment. | Keep initial 0.001 and existing scheduler. |

The most defensible conclusion is **generalization pressure with substantial
validation uncertainty**, not a proven cause. The smaller model is an
interpretable experiment to test capacity sensitivity, not a predicted winner.
It may underfit or leave the same source-specific weaknesses; then keep baseline.

## Future order and limits

Baseline → one T7 width variant → original-seed configuration selection by
unchanged Q/tie rule → one seed confirmation → **validation-only ensemble
decision** → freeze the entire separation system → owner-authorized one-shot
held-out test. Ensemble is neither selected nor executed here. A post-test
ensemble-selection loop on the same test data is not allowed.

Execution details, exact deltas and stop points are in
[`T7_LUNA_HANDOFF.md`](T7_LUNA_HANDOFF.md). Maximum full training runs in this
decision: existing baseline + one width variant + one confirmation = three.
No automatic second variant, seed retry, warm start, expanded test suite or
production work. A small validation advantage is descriptive, not statistical
superiority or proof of patient/device generalization.

## T7 offline execution result — validation only

The small profile passed the fixed two-example development gate after **100
updates / 8.17s**, peak RSS 687.1 MiB. Every one of the four source/case
SI-SDRi scores exceeded +10 dB (minimum +10.378); normalized-L1 reductions were
67.1% and 66.3%. Gate checkpoint SHA-256:
`7c82ff806c5b59beca6dddc0b4f92ba9c1fb46a7d7c8c6d43fed404792acd0c1`. The gate
weights were not used for T7 training.

| Run | Params | Epochs / best | Heart SI-SDR / SI-SDRi | Lung SI-SDR / SI-SDRi | Q | Mean | Runtime | Peak RSS | Failures | Best checkpoint SHA-256 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline seed 20260928 | 645,681 | 20 / 8 | 3.0310 / 3.0350 | 3.0747 / 3.0788 | 3.0350 | 3.0569 | 1,243.5s | 2,078.2 MiB | 0 | `2eb0c19fc27b7587eca2087da2ad7e9fb943d74268defb67de3470a91a960db9` |
| Small seed 20260928 (selected) | 171,313 | 17 / 8 | 3.0970 / 3.1011 | 3.1261 / 3.1302 | 3.1011 | 3.1156 | 570.8s | 1,396.1 MiB | 0 | `89f8d66134c0a49aa2a05971720cdffbdd1e501ebce99bb83119e6683d58ac93` |
| Small seed 20260929 (confirmation) | 171,313 | 16 / 4 | 3.3283 / 3.3324 | 3.3235 / 3.3275 | 3.3275 | 3.3300 | 533.0s | 1,410.4 MiB | 0 | `e59219731e36998231419cf08febb48e13eb3cbea473e4577ec4311def31a978` |

The configured plateau scheduler reduced LR as follows (LR used for optimizer
updates): primary run 0.001 in epochs 1–10, 0.0005 in 11–15, 0.00025 in 16–17;
confirmation 0.001 in epochs 1–9, 0.0005 in 10–14, 0.00025 in 15–16. Both
runs stopped by the frozen 12-epoch early-stopping rule, not by failure.

The seed-20260928 small profile wins the **predeclared** comparison by Q
**+0.0660 dB** and balanced mean **+0.0587 dB**. Both source improvements are
positive; these small margins are descriptive only. The confirmation's higher
Q does not replace the selected primary-seed checkpoint.

| Family pair | Baseline H / L SI-SDRi | Small 20260928 H / L | Small 20260929 H / L |
| --- | ---: | ---: | ---: |
| Late Diastolic Murmur × Fine Crackles | 3.847 / 3.713 | 3.702 / 3.664 | 3.861 / 4.198 |
| Tachycardia × Fine Crackles | 2.223 / 2.445 | 2.501 / 2.596 | 2.803 / 2.457 |

Both small runs reduce the heart-family gap versus baseline. The confirmation
seed's family-level lung scores shift in opposite directions. By relative
level, seed 20260928 vs 20260929 heart/lung SI-SDRi means are: −10 dB
0.265/5.292 vs 1.167/6.687; −5 dB 2.490/5.005 vs 3.065/6.012; 0 dB
3.949/4.116 vs 4.145/4.575; +5 dB 4.794/2.398 vs 4.611/2.144; +10 dB
5.007/−0.270 vs 4.556/−1.329. Negative lung improvements at +10 dB occur in
23/45 versus 30/45 conditions. These correlated counts are descriptive.

**Seed robustness: UNCERTAIN.** Both seeds produce positive, fairly balanced
family-macro improvements around 3.1–3.3 dB, with no failures; aggregate seed
deltas are +0.2313 dB heart, +0.1974 dB lung, +0.2264 dB Q, +0.2143 dB mean.
However, their family-level lung and +10 dB behavior differs enough that the
two-family validation cannot support a robustness claim. Stop here; no third
seed, retuning or seed substitution.

Both full runs used clean source commit
`1950fc0f45b646e4fd1729ebb617d37c6ebfc1d7`, CPU / Python 3.14.4 /
torch and torchaudio 2.11.0+cpu, seed-specific fresh initialization, the same
manifest (`39d5456477b07772bdc24b86ee73dee17c44fd1e0837b62b96eab8c19a1b65e4`)
and frozen validation recipe (`b4cef517cd4a64c267d3645ea6b918b5dfb72945f7536c0245b73228f00fdc90`).
The small-run first-epoch training-recipe hash equals the baseline's
`790dcb8d06288ee3a93531274a9e0c10e01d6adb5c339c916acd3f79f8c5c0c7`; all 17
primary-run recipe hashes match the baseline. Effective confirmation config
hash: `ca572c327410678e8b80c16bfd582beccc3dead67ebd1ac8167f0d9d3b521230`;
source config hash: `3edf8ad6f7e286478b02a827191ac2b44bfe9e9391f8ff4aa819aa5f15612ee8`.

Six existing focused contract tests passed; no new tests or broad regression
were added/run. The small profile's smoke forward/backward and baseline
checkpoint compatibility check passed. Final test files/recipes/metrics remain
sealed. Production and Axora remain untouched. Full local run records and the
pre-confirmation selection receipt are under ignored
`.local/training/stethofuse-tcn-v1/`.

## Analysis provenance

The initial tuning diagnosis read JSON/JSONL recipe and metric files only. Its
baseline input hashes remain in [`T5_T6_BASELINE_EXECUTION.md`](T5_T6_BASELINE_EXECUTION.md);
the execution above used only the authorized two development gate mixtures and
the fixed development/validation recipe paths. It did not access test audio.
Analysis input SHA-256:

- `history.jsonl`: `cb8d24ec8a8e3082293d74f6bf396afaace5c31fe01a2db81fa0925b6040af26`
- `validation/best_checkpoint_per_condition.jsonl`: `d7079e07c8f4de45d1561bbed3e463c9c40c4f54860ca9fc70e6e29de4ef90f7`
- `validation/best_checkpoint_summary.json`: `b2c1d91c88862f8fbac7b43d89b81bed080a882cc18521acef14fd37057f423f`
- `run.json`: `ec24b1cf1a4e9d1ba07e4dd248b93559a60460cb1ccaa02b2b516518a41a0eb1`

Reproduction: group saved rows by `(heart_family,lung_family)`, source metric,
and numeric `relative_lung_to_heart_db`; use ordinary means within a group and
equal group weights for macro. `median`/`quantile(.75)-quantile(.25)` apply to
the indicated pooled rows; count values <0. Average the five levels for file-
pair diagnostics; retain all rows. For epoch objectives compare N+5A with the
saved total (agreement within 1e-5). No WAV or checkpoint was read for the
initial diagnosis; execution model loading/training is covered by the run
records above.
Graphify returned an OAuth reauthentication error; one connection check only,
then narrow reads of the known wrapper, objective and runners.
