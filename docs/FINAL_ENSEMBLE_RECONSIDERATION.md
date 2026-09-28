# Final ensemble reconsideration — validation only

**Later pre-test review:** [plateau diagnosis](PRE_T9_PLATEAU_DIAGNOSIS.md) retains
this standalone/no-projection decision and the T8 artifact. One future family-
qualified refit is designed, not executed; T9 is on hold for owner review.

2026-09-28. T7 COMPLETE / VALIDATION-ONLY ENSEMBLE DECISION COMPLETE /
T8 SYSTEM FROZEN / T9 PROTOCOL PREDECLARED / FINAL TEST SEALED / NOT DEPLOYED.

## Decision B — freeze the selected small Conv-TasNet standalone

Keep the **171,313-parameter N64/B32/H64 model, seed 20260928, best epoch 8**, with
its existing waveform inference and equal-residual consistency layer. No second
expert, fusion weight, confidence rule, mask projection or source-specific
weight is selected for the final separator. The confirmation checkpoint never
replaces it. The existing NeoSSNet/NMF ensemble remains an offline research
comparison with its previously reported poor development results; those scores
are not comparable to this validation table and are not rewritten as final FYP
results. No new TCN ensemble score is claimed.

Fixed Filter and Generic NMF are reproducible, but are worse in most conditions,
have much larger, positively correlated residual errors, and offer localized
oracle-routing gains. This does not justify spending more of the two-group
validation set on fusion selection. It is **not a proof that every possible
ensemble would underperform**. No combined-output experiment or weight search
was executed. Application integration/deployment and the held-out test remain
separate gates.

## Measured standalone validation evidence

All rows use the same 225 frozen conditions, entire 15-s references, fixed
heart/lung labels, 4-kHz rate, shared gain, 10-s/8-s-hop inference, and audited
SI-SDR. Group means are averaged equally across the two family pairs. There
are zero execution/metric failures for each method. These are correlated
manikin remixes, not 225 independent subjects or clinical examples.

| Method | Heart SI-SDR | Heart SI-SDRi | Lung SI-SDR | Lung SI-SDRi | Q | Balanced mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Selected TCN waveform (control/final choice) | 3.097 | 3.101 | 3.126 | 3.130 | 3.101 | 3.116 |
| TCN magnitude-mask projection (diagnostic only) | 3.347 | 3.351 | 3.367 | 3.371 | 3.351 | 3.361 |
| Existing Fixed Filter | −0.826 | −0.822 | −2.757 | −2.753 | −2.753 | −1.787 |
| Existing Generic NMF | −3.429 | −3.425 | −3.615 | −3.611 | −3.611 | −3.518 |

Saved T7 control scores replay within **6.20e−14 dB**. No metric, scale, crop,
source order or checkpoint changed. Pooled heart/lung SI-SDRi medians (IQR):
TCN 2.987/3.178 (3.833/4.269), Fixed Filter −1.259/−3.718 (4.592/7.524),
NMF −2.867/−3.890 (7.722/7.520). Pooled summaries weight 150 versus 75 rows;
they are descriptive and are not the equal-family selector.

### Family and relative-level complementarity

| Heart family × Fine Crackles | TCN H / L SI-SDRi | Projected TCN H / L | Fixed Filter H / L | NMF H / L |
| --- | ---: | ---: | ---: | ---: |
| Late Diastolic Murmur (150 conditions) | 3.702 / 3.664 | 3.852 / 3.956 | −2.397 / −3.913 | −5.551 / −4.728 |
| Tachycardia (75 conditions) | 2.501 / 2.596 | 2.851 / 2.786 | 0.752 / −1.592 | −1.299 / −2.493 |

Secondary wins mean a per-condition SI-SDRi increase over the control, without
altering labels. Fixed Filter wins **21/225 heart, 17/225 lung**; NMF wins
**9/225 each**. All 21 filter heart wins are Tachycardia, 19 using `F_T_RC`;
13/17 lung wins are Tachycardia, 11 using `F_T_RC`. Every NMF win uses
`F_T_RC`. Filter wins 11/24 control-negative heart cases and 2/33 control-negative
lung cases; NMF wins 8/24 and 0/33. Some localized complementarity exists, but
the second experts do not consistently rescue both sources or both families.

Five pre-existing relative levels, **equal-family macro means at each level**:

| Lung/heart dB | TCN H / L SI-SDRi | Projected TCN H / L | Fixed Filter H / L | NMF H / L |
| ---: | ---: | ---: | ---: | ---: |
| −10 | −0.132 / 4.959 | 0.488 / 4.834 | −3.487 / 0.230 | −7.878 / −1.308 |
| −5 | 2.280 / 4.723 | 2.610 / 4.727 | −1.311 / −0.337 | −4.345 / −1.176 |
| 0 | 3.837 / 3.925 | 3.986 / 4.059 | −0.163 / −1.674 | −2.964 / −2.942 |
| +5 | 4.677 / 2.313 | 4.752 / 2.699 | 0.331 / −4.166 | −1.889 / −5.018 |
| +10 | 4.843 / −0.269 | 4.920 / 0.536 | 0.518 / −7.816 | −0.050 / −7.610 |

Fixed Filter heart-win counts at these levels are 7/5/3/3/3, lung 7/7/2/1/0;
NMF heart 3/3/1/1/1, lung 4/3/2/0/0 (45 conditions per level). Neither expert
offers a credible remedy for the dominant-lung +10dB weakness. The T7 receipt's
level numbers were pooled condition means; this table explicitly uses equal
family weighting. Control per-condition scores are identical; no result changed.

### Residual, phase and alignment findings

Compute Pearson correlation between centered errors `TCN_s − target_s` and
`expert_s − target_s` at the same physical scale. No fitted reference gain or
alignment is applied to outputs. The secondary/TCN residual-energy ratio is
also calculated before any reference-assisted correction.

| Secondary | Residual correlation min / median / max | Median error-energy ratio | Correlation median, LDM / Tachycardia |
| --- | ---: | ---: | ---: |
| Fixed Filter | 0.440 / 0.764 / 0.925 | 2.519 | 0.810 / 0.670 |
| Generic NMF | 0.372 / 0.729 / 0.918 | 2.612 | 0.727 / 0.732 |

Heart/lung residual correlations are essentially identical because additive
two-source estimates have equal-and-opposite errors. Correlation alone cannot
prove or disprove a useful convex fusion; error magnitude and localized wins
also matter. Large positive correlated errors do not establish a strong second
expert. No validation labels enter an inference rule.

On the ten predeclared pair/level conditions, both TCN representations peak at
zero target-relative lag for all 20 source comparisons. Filter heart peaks are
zero in 7/10, +1 in 2/10, +2 in 1/10; NMF heart zero in 9/10 and +1 in 1/10.
All secondary lung peaks are zero. No negative zero-lag or peak correlation
was seen in these diagnostics. This provides no evidence of a shared fixed
delay/sign defect; no correction was applied. It does not establish local
phase agreement everywhere. STFT methods use mixture phase by construction.

Maximum samplewise `|heart+lung−mixture|`: **1.19e−7** for TCN, projected TCN
and Fixed Filter; **2.44e−5** for NMF (its epsilon denominator slightly attenuates
the sum). NMF is approximately additive, not exact at 1e−6 tolerance; a future
combination would need an explicit target-free consistency correction, but no
such adaptation is selected here.

### Oracle upper bound — not deployable

This is a generous source-wise hard-routing bound on choosing either expert's
complete output for each condition. It uses reference scores, can choose
different experts for heart and lung, and need not preserve mixture consistency.
It is **not** an upper bound on arbitrary convex waveform combinations and is
neither an ensemble result nor a final-system metric.

| Control + optional expert | Oracle H / L SI-SDRi | Oracle Q | Q gain | Balanced mean gain |
| --- | ---: | ---: | ---: | ---: |
| Fixed Filter | 3.332 / 3.392 | 3.332 | +0.231 | +0.247 |
| Generic NMF | 3.174 / 3.275 | 3.174 | +0.073 | +0.109 |

Filter oracle H/L gains by family are **0.000/0.019 dB** for Late Diastolic
Murmur and **0.463/0.505 dB** for Tachycardia. NMF gives **0.000/0.000** and
**0.146/0.290** respectively. Gains are concentrated, and real target-free
selection has no demonstrated way to realize even this modest routing benefit.
No formal significance or dB acceptance threshold is inferred from two groups.

### TCN waveform versus magnitude-mask projection

Projection **does not materially damage aggregate performance here**: macro
H/L improvements rise +0.250/+0.241dB, Q +0.250, mean +0.245. Both family-pair
means improve, but 53 heart and 62 lung conditions worsen (of 225); largest
drops −0.396/−0.632dB. The lung macro score at −10dB falls by 0.125dB while
dominant-source endpoint scores improve. This is one-model postprocessing,
not evidence of information from a second expert.

The result removes “projection necessarily loses the model's advantage” as an
explanation. It does not qualify a mask ensemble. Preserve the already-selected
waveform output contract: this allowed diagnostic is not automatically promoted
to an extra tuned final-system variant based on the same two validation groups.
No additional projection tuning/confirmation is selected by this decision.

## Ensemble formulations considered

| Family | Compatibility and reason for decision |
| --- | --- |
| Shared static waveform convex combination | No systematic delay/polarity blocker was found. For additive experts, a shared weight preserves additivity algebraically. However, second-expert quality, positively correlated large errors and localized wins do not justify a new weight experiment. Rejected for this milestone; not claimed mathematically impossible. |
| Complementary TF-mask fusion | Mechanically feasible, and projection cost is favorable in aggregate. Still lacks a qualified complementary partner; any uplift could be the TCN projection alone. Rejected; do not mechanically reuse the NeoSSNet/NMF 50/50 engine. |
| Source-specific fixed weights | Adds degrees of freedom; different weights generally break mixture consistency. No consistent two-family rescue supports this. Rejected. |
| Deterministic confidence routing/weighting | No existing validated target-free feature predicts these localized wins. Fitting a rule to `F_T_RC`, family labels or known relative reference level would be oracle leakage. Rejected. |

No other registered deterministic method is already qualified: VMD retains the
no-fallback qualification gap; NMCF/DAE-NMF-VMD are not valid available choices.
No new expert, model training, seed or weight was introduced. The existing
confirmation seed was not loaded or rescored: no ensemble formulation was
selected, so its use would add a selection surface. T7's previously reported
robustness uncertainty remains unresolved; it neither validates nor overturns
this secondary-expert decision.

## Compute, provenance and checks

Diagnostic execution used clean implementation commit
`656a79e677bed198b119abbf008e21392d14ef92`, Python3.14.4,
torch/torchaudio2.11.0+cpu, NumPy2.4.4, SciPy1.17.0, two CPU/BLAS threads.
No installs. All 225 conditions took **15.01s**, process peak RSS **455.6MiB**.
Measured method calls (exclude source/checkpoint loading and diagnostic scoring):

| Method | Total for 225 × 15s records | Mean per record |
| --- | ---: | ---: |
| TCN waveform | 4.447s | 19.8ms |
| TCN projected, including TCN | 5.683s | 25.3ms |
| Fixed Filter | 0.821s | 3.65ms |
| Generic NMF | 3.311s | 14.7ms |

An added filter or NMF would add roughly 18% or 74% of this measured TCN compute,
plus fusion; these are bounded CPU observations, not production latency promises.
The standalone decision adds no inference overhead.

Artifacts are ignored under `.local/ensemble/final_reconsideration/primary-validation-v1/`:
per-condition rows, source-wise oracle rows, residuals, alignment, summary and
source/environment manifest. No generated audio or weights were written.
Summary SHA-256: `eb3f20ea83b401b86cb7c74c623255f6802eab138de4e13044f46f63e9ff3039`.
Diagnostic script SHA-256: `8f5db516e704f6b9c10f876742c170d99a86bc1f19284d028981d87be9a9bf53`.

Only a synthetic shape/finite/reconstruction and zero-lag smoke check plus
Python compile/document checks were run. Zero optimizer updates, no new unit
tests or broad application suite. The validation replay checks every control
row; failures abort rather than exclude conditions. No source/model/evaluator
production implementation changed. Graphify required OAuth reauthentication;
one attempt was followed by narrow reads of known paths.

## T8 freeze receipt and predeclared T9 protocol

The frozen machine-readable system specification is
[`research/configs/final_separator_v1.json`](../research/configs/final_separator_v1.json),
SHA-256 `3780292ae6ff1ea6415fc1bd9b4b045bb91d5443068e806b08e9cb39735a1e34`.
It identifies the selected checkpoint SHA
`89f8d66134c0a49aa2a05971720cdffbdd1e501ebce99bb83119e6683d58ac93`, the
N64/B32/H64 model (171,313 parameters), configuration SHA
`3edf8ad6f7e286478b02a827191ac2b44bfe9e9391f8ff4aa819aa5f15612ee8`, source
manifest SHA `39d5456477b07772bdc24b86ee73dee17c44fd1e0837b62b96eab8c19a1b65e4`,
validation recipe SHA
`b4cef517cd4a64c267d3645ea6b918b5dfb72945f7536c0245b73228f00fdc90`, and
17-file development recipe-set index SHA
`9ab9fc26a68d5974c43519f349dd377745ac6608683bcce588582e7da31208c9`.
The development recipe digest is an SHA-256 over sorted `sha256sum` entries,
including each epoch-recipe digest and relative path. The spec freezes CPU
execution, Python 3.14.4, torch/torchaudio 2.11.0+cpu, float32, mono 4-kHz
PCM16 decoding, shared amplitude convention, heart/lung output order, 10-s
windows / 8-s hop / 2-s overlap, right padding/exact trim, equal-residual
consistency, finite-output contract, strict checkpoint loading and fail-closed
behavior. Its status is frozen for held-out evaluation, **not deployed or
clinically validated**.

Before T9, the model was loaded strictly into the frozen 171,313-parameter
architecture on CPU. A synthetic 40,037-sample mono waveform exercised window
inference and tail trimming: output `[2, 40037]`, finite values, maximum
`|heart+lung−mixture|` `2.98e−8`. No reference signal was involved. Checkpoint
file SHA and all frozen metadata hashes matched. This is an integrity smoke
check, not a quality evaluation.

The exact T9 recipe is fixed in the JSON. After separate explicit owner
authorization only, take the 5 frozen test heart sources × 9 lung sources,
sorted by `(family, source ID)` with heart outermost, and evaluate all 45 pairs
at `[-10,-5,0,5,10]` dB (225 conditions). Use each source's full 60,000 samples
from start 0. Apply the existing `make_mixture` equation, the frozen RMS-defined
lung/heart gain and one common peak scale, and write/hash an immutable recipe
manifest before inference. T8 generated no test recipes and copied no test IDs
into the freeze spec.

Frozen methods, in order: original-mixture baseline, selected standalone TCN,
Fixed Filter (existing 1024/256 STFT; 180/35-Hz heart and 130/55-Hz lung
transitions), and Generic NMF (6 components, 80 iterations, seed 42 per
inference window). VMD is excluded without strict no-fallback qualification;
NeoSSNet is excluded as a target-domain-unqualified research-only model. Use
identical condition mixtures, fixed semantic labels, shared whole-record gain,
and 10/8-s inference windows. Metrics are heart/lung SI-SDR and SI-SDRi using
the frozen zero-mean implementation and epsilon `1e-8`; improvement subtracts
the same-condition mixture score against the same reference. Report every
condition, per-method failure count, source-specific family-pair macro means
(equal weighting of groups after averaging conditions within each group), and
pooled median/IQR descriptively. Also report family/relative-level breakdowns
and per-method inference time plus total run time. The 225 remixes are not
independent subjects.

Write recipes, per-condition metrics/failures, summary and environment/code/spec
hashes under ignored `.local/training/stethofuse-tcn-v1/t9/`; no audio mixtures
or checkpoints. Record failures without dropping conditions or substituting a
method; a metric aggregate is valid only if that method has all conditions.
After opening the test, do not change model, checkpoint, seed, preprocessing,
windowing, consistency, source mapping, projection, experts, weights or
comparators based on scores. A concrete software defect requires stopping and
preserving partial evidence; a correction rerun needs explicit owner approval
and must be identified as a correction, never tuning. Report results only for
the frozen manikin/source-family domain, without clinical, patient-level or
subject-independent claims.

**T8 complete. Stop for explicit owner T9 approval.** No T9 recipe, audio,
inference or score was accessed or created here.

The old unqualified NeoSSNet/NMF ensemble is retained as historical research
evidence and excluded from the final deployment candidate. No cross-protocol
score table should present its six development probes as final comparators.
FYP2 must state that an ensemble was investigated but useful target-domain
complementarity was insufficient here. No final Chapter6 conclusion, clinical,
real-patient/device generalization or statistical superiority claim follows.

## Scientific context

The original [Conv-TasNet paper](https://arxiv.org/abs/1809.07454) motivates
learned waveform decoding and discusses magnitude-mask limitations for speech;
it does not prove a phase advantage for this manikin model. The measured
projection result above, not that expectation, informs this decision.
[Wisdom et al.](https://arxiv.org/abs/1811.08521) distinguish STFT and mixture
consistency and describe differentiable consistency layers. Existing APA7
entries are retained in FYP2's `provenance/ensemble-references.bib`; no new
architecture literature campaign or license investigation occurred.

## Predeclared diagnostic protocol

One pass over the existing 225 correlated validation conditions (two family
pairs). Selected small Conv-TasNet seed 20260928, epoch 8, checkpoint SHA-256
`89f8d66134c0a49aa2a05971720cdffbdd1e501ebce99bb83119e6683d58ac93` is the control.
The seed 20260929 checkpoint is not inspected for expert/weight selection.

Compare only the control waveform, its target-free complementary magnitude
mask projection, the existing Fixed Filter, and existing Generic NMF
(6 components, 80 multiplicative-update iterations, seed 42 per inference
window). NMF fits its existing unsupervised per-input decomposition; no new
trained model, bases, settings or neural optimizer steps are introduced.
VMD remains excluded because its no-fallback path has not been qualified;
NeoSSNet and the large TCN are excluded as final ensemble experts.

Use the unchanged TCN 10-second / 8-second-hop window, overlap, whole-record
shared gain, padding and trimming for every method. “TCN waveform/raw” includes
the already-trained target-free equal-residual mixture-consistency layer; it
does not mean the unconstrained decoder before that layer. Projection means
`m_h=|STFT(h)|/(|STFT(h)|+|STFT(l)|)`, stable epsilon with a 0.5 silent-bin
default, `m_l=1-m_h`, applied to the mixture's complex STFT; n_fft1024/hop256
and the existing centered periodic-Hann implementation. It uses no reference.
Both masks are computed per canonical window, then the same overlap-add is used.

Reuse the validated SI-SDR and weaker-source family-pair macro selector. Replay
control scores against saved T7 rows (tolerance 1e-5dB). Measure per-condition,
family and five frozen relative levels, residual correlations at shared scale,
consistency error and method runtime. A per-source max-over-experts diagnostic
is **ORACLE UPPER BOUND — NOT DEPLOYABLE**, only for hard expert routing, not an
upper bound on every possible mixture of outputs. It may violate pairwise
mixture consistency and cannot select outputs in deployment.

Alignment diagnostic is fixed in advance: first frozen-recipe pair from each
validation family, at all five levels; cross-correlation within ±128 samples
(32ms) against references, with no shifts, sign corrections or oracle output
changes applied. No final-test audio, metadata labels, recipes or metrics are
used. Only the eligible training-run metadata and validation recipe are parsed.

`scripts/diagnose_final_ensemble.py` is an offline analytical entry point with
no fusion weights/search, no training function calls, and no application DB or
job writes. It refuses to overwrite prior results. Outputs remain ignored in
`.local/ensemble/final_reconsideration/primary-validation-v1/`.

Decide from these diagnostics whether to predeclare one simple future fusion
experiment or retain standalone TCN. No ensemble score will be calculated in
this diagnostic pass. No additional seed training is authorized.
