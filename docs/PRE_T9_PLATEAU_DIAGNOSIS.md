# Pre-T9 plateau diagnosis — 28 September 2026

**DIAGNOSTIC RESULT / INTERVENTION DESIGNED, NOT EXECUTED / T9 SEALED / NOT DEPLOYED.**
The owner authorized this final pre-test review after T8. The T8 checkpoint,
specification and inference implementation remain unchanged. T9 is on hold for
review of this diagnosis, not authorized by the previous readiness statement.

## Decision

**PLATEAU CLASSIFICATION: DATA-LIMITED. Confidence: MEDIUM.**

The most supported limitation is insufficient diversity of learned source
patterns for a difficult, overlapping, fixed-semantic separation task—not lack
of local fitting capacity. Repeated crops/remixes expose the same small set of
manikin styles many times. Specific periodicity/overlap differences, recording
heterogeneity and a narrow validation population matter. This is an inference
from several diagnostics, **not a causally proven attribution of every lost dB**.
Window/local-level distribution differences remain a credible secondary factor.

**ONE SELECTED INTERVENTION:** family-held-out budget qualification followed,
only if its predeclared gate passes, by one fresh all-non-test refit of the
unchanged small Conv-TasNet. Five short grouped folds use the same model, seed,
loss and mixture policy; they select only a bounded fixed update budget. They
are not five architecture variants. No second intervention is recommended.
See [exact Luna handoff](PRE_T9_LUNA_HANDOFF.md) and the machine-readable
[plan](../research/configs/pre_t9_family_refit_plan_v1.json).

All-non-test refit afterward: **YES, conditional on qualification**. Expected
mechanism: add two heart families and one lung family to the learned prior,
then stop at a budget justified across more than the current two family pairs.
Expected benefit is uncertain and may be modest; no +10/+15-dB promise follows.
If the gate fails, retain T8 and stop for review, without another variant.

## 1. What the apparent gap does—and does not—measure

OBSERVED: the large-model T4 gate fitted two fixed development crops at 0 dB
after 100 updates: H/L SI-SDRi 11.95/12.08 and 11.51/11.78 dB. The small-model
gate separately passed the same criteria at 100 updates. These prove local
capacity and pipeline correctness. Those weights did not initialize full runs.

They do **not** establish a measured 9-dB train–validation gap for the selected
checkpoint. T4 repeatedly fits two targets, with a different gate batch/decay
protocol. Full training sees changing pairs, crops and levels. At their best
epochs, online mean training absolute SI-SDR was 4.313 dB (large), 3.910 dB
(small primary), and 3.313 dB (small confirmation)—not 12 dB. Even these online
means use changing model states/8-s crops and are not a matched training-set
evaluation to subtract from full-record validation.

| Saved run | Best / stopped epoch | Updates to best | Validation H / L SI-SDRi | Q / balanced mean |
| --- | ---: | ---: | ---: | ---: |
| Large, seed 20260928 | 8 / 20 | 1,152 | 3.035 / 3.079 | 3.035 / 3.057 |
| Small, seed 20260928, selected | 8 / 17 | 1,152 | 3.101 / 3.130 | 3.101 / 3.116 |
| Small, seed 20260929, confirmation only | 4 / 16 | 576 | 3.332 / 3.328 | 3.328 / 3.330 |

All have zero validation failures. The small-width gain over the large model is
only 0.066 dB Q; it is not evidence that capacity reduction solved generalization.

## 2. Independent information, not synthetic volume

MEASURED from the saved **86-source non-test allowlist only**:

| Population | Heart | Lung | Recorded material |
| --- | --- | --- | --- |
| Development | 36 files, 6 families | 36 files, 4 families | 18 min total |
| Current validation | 9 files, 2 families | 5 files, 1 family | 3.5 min total |
| All non-test | 45 files, 8 families | 41 files, 5 families | 21.5 min total |

Every file is 15-s mono 4-kHz PCM16, with a distinct recorded hash. Development
heart families: AF4, Early Systolic Murmur6, Late Systolic Murmur5, Mid Systolic
Murmur7, Normal9, S3=5. Lung: Normal12, Pleural Rub9, Rhonchi8, Wheezing7.
Current validation adds Late Diastolic Murmur6, Tachycardia3 and Fine Crackles5.
These are sound-family/location/manikin labels, **not verified subjects or
independent acquisition sessions**. No precise effective sample size is claimed.

The 225 validation rows are 45 file pairs at five levels. Both heart-family
groups reuse the **same five lung recordings**, so even the two family-pair
groups are not statistically independent replicates. No row bootstrap, IID
standard error, p-value or two-group confidence interval was calculated.

Welch PSD descriptors used 1,024-sample Hann segments, 512 overlap, nfft2,048,
DC removal and normalized spectral mass. Bands: 0–50, 50–100, 100–200, 200–400,
400–800, 800–1,200 and 1,200–2,000 Hz. RMS/peak/crest, centroid, flatness,
20-ms RMS-envelope autocorrelation and three fixed 8-s crops were also measured.

- Within-family median PSD Bhattacharyya similarity: heart 0.902, lung 0.893;
  between-family: 0.803/0.769. Stable family/style spectra are a plausible shortcut.
- No pair reached 0.8 normalized waveform cross-correlation within ±2 s; maximum
  0.624. This is **no near-duplicate evidence under this bounded diagnostic**,
  not proof of independence or absence of shared manikin templates.
- Training at best epoch already used 1,230/1,296 possible file pairs (94.9%),
  4,608 mixtures, and 128 appearances per source on average (heart83–192,
  lung96–167). Each source still supplies only 15 s of recorded information.
- Two uniformly placed 8-s crops from a 15-s file share at least 1 s and an
  expected `8 − 7/3 = 5.667 s` (70.83%). Distinct offsets do not create subjects.
- By the selected run's stop: 9,792 draws, 1,289 distinct pairs, 272 mean source
  appearances. More mixing had largely exhausted pair identities, not added
  independent physiology.

All-non-test refit adds only 210 s of audio, but heart families rise 6→8, lung
families4→5 and possible family-pair types24→40. Those new patterns are the
reason to consider refit; 45×41 synthetic pair count is not its evidence size.

## 3. Family distance, overlap and shortcut hypotheses

MEASURED: seven interpretable spectral/temporal descriptors were standardized
using **development-only** means/SD by source type. Distances are Euclidean
norm divided by sqrt(dimension), descriptive and feature-dependent.

| Family | Distance to nearest development-family centroid | Development leave-family-out range |
| --- | ---: | ---: |
| Tachycardia | 0.608 | Heart0.371–1.243 |
| Late Diastolic Murmur | 0.787 | Heart0.371–1.243 |
| Fine Crackles | 0.302 | Lung0.422–0.656 |

Thus **broad descriptor out-of-support shift is NOT demonstrated**. Low-order
features can miss separation-relevant morphology; they do not prove identical
distributions either. No PCA/embedding was needed to reach this bounded result.

Specific differences are meaningful. Tachycardia's median envelope-ACF peak lag
is 0.40 s, versus development heart-family medians0.84–0.88 s. These are manikin
pattern proxies, not verified clinical heart rates. Normalized PSD intersection
for Tachycardia×Fine Crackles is 0.462 versus 0.327 for Late Diastolic
Murmur×Fine Crackles; Bhattacharyya similarity0.735 versus0.627. Greater overlap
is consistent with harder identifiability and the lower Tachycardia scores,
but does not establish an information-theoretic recovery ceiling.

Selected H/L SI-SDRi is3.702/3.664 for Late Diastolic Murmur and2.501/2.596 for
Tachycardia. Within Fine Crackles, family-balanced H/L scores by lung recording
range1.066/1.061 (`F_FC_LUA`) to6.052/5.511 (`M_FC_LUA`). Recording-level
heterogeneity is substantial even inside one family. Sensor/location spectra,
periodic templates and envelope signatures could be shortcuts; the available
metadata cannot isolate their causal effects. Normalization removes a global
amplitude cue, not spectral style. No diagnostic classifier was trained.

Single-channel additive audio admits many decompositions; learned source priors
must resolve overlapping regions. Neither PSD overlap nor these results prove
that double-digit separation is impossible, or that an unrelated paper's score
is achievable here.

## 4. Mixing, levels, amplitude and window context

AUDITED equation, with RMS measured in float64 on each actual training crop:

`a = RMS(h)/RMS(l) * 10^(d/20)`;
`c = .95/max(peak(h), peak(a*l), peak(h+a*l))`;
`targets=(c*h, c*a*l); x=targets[0]+targets[1]`.

Consequently `20log10(RMS(l')/RMS(h'))=d`, equivalently10log10(power ratio).
Shared input/target peak normalization preserves that ratio. The “power level”
docstring is not a10-versus20log bug. Crop RMS<1e−6 is rejected; saved full runs
show no silent-crop retries. Replay maximum gain error is **4.90e−7 dB**. No
clipping, source-order or mixture-additivity defect was found.

| Nominal lung/heart dB | Selected H SI-SDRi | Selected L SI-SDRi |
| ---: | ---: | ---: |
| −10 | −0.132 | 4.959 |
| −5 | 2.280 | 4.723 |
| 0 | 3.837 | 3.925 |
| +5 | 4.677 | 2.313 |
| +10 | 4.843 | −0.269 |

These are equal-family means. At extremes the **dominant** source has slightly
negative improvement against an already ~+10-dB mixture; the **weak** source
improves ~5dB but remains near−5dB absolute SI-SDR. Calling both a weak-source
collapse in SI-SDRi would be incorrect. Relative difficulty is real, not a gain
convention error.

Training's continuous uniform dB range gave19.42% of draws at |d|≥8; validation
puts40% exactly at±10. This changes evaluation emphasis, not support/range.
There is no clinical level-frequency distribution supporting a new sampler.
Do not change the frozen metric or range to make the number larger.

Physical-amplitude diagnostics after consistency: at0dB pooled median H/L
RMS-ratio errors−1.235/−1.893dB; target-projection gains0.763/0.663; normalized
L1≈0.380 each. At−10dB median L1H/L0.205/0.649; at+10,0.706/0.223. These reveal
imperfect amplitude/morphology, not good waveforms spoiled solely by output
gain. SI-SDR already permits a reference projection *inside the metric*; no
reference correction enters inference. These are diagnostic, not new headline
test metrics.

Eight-second crop RMS max/min across offsets0/3.5/7s has median1.19dB for
development heart,1.52dB lung. One validation lung recording varies14.27dB,
but is not the worst-scoring source. Crop variation is useful but correlated.
Measured lung envelope peaks around5.4s imply only~1.5 repeated patterns in8s;
they are uncertain proxies, not proof that the crop is physiologically invalid.

There is a genuine context-contract difference: training uses unpadded8s;
15s validation uses0–10s and8–18s windows, with3s zeros in the latter. Gains are
defined over15s, so local10s/7s valid-region ratios differ from nominal. Source-
only replay found first-window deviations−1.075..+4.247dB and tail deviations
−13.702..+0.812dB;45/225 and63/225 window ratios lie outside[-10,+10]. This is
a secondary distribution concern, not an incorrect RMS formula. Regional
scores are recorded separately in the analytical receipt; source content,
length and local levels confound attributing a tail score to padding alone.
No alternative window, padding or level policy was tested/selected.

MEASURED regional replay of the **same** current inference on all225conditions:

| Region | H SI-SDRi macro | L SI-SDRi macro |
| --- | ---: | ---: |
| 0–8s early | 3.243 | 2.606 |
| 8–10s overlap | 0.387 | 2.381 |
| 10–15s tail | 2.404 | 4.263 |
| Full15s | 3.101 | 3.130 |

No universal padded-tail failure appears: lung improves in the tail, heart
varies by recording. The initial10-condition, metadata-first-pair probe had
poor tails, but both pairs shared the weakest Fine Crackles recording. It was
therefore checked against all existing conditions instead of being promoted
to a padding diagnosis. Both receipts are preserved. Region SI-SDR uses that
region's own target/mixture and is not additive across time; these figures
cannot isolate padding from source content or justify a new window rule.

## 5. Exact temporal support and encoder resolution

AUDITED installed torchaudio code and selected profile: kernel3 temporal
blocks, dilations1..128 repeated3 times, encoder32/stride16, decoder32/stride16.
The sum of dilation radii is `3*(1+2+...+128)=765` latent frames:

- Mask convolutional support: `1+2*765=1531` frames.
- Encoder plus one mask frame: `32+16*(1531−1)=24512` samples =6.128s.
- One decoder sample combines two neighboring latent frames; their union is
  **24,528 samples =6,132ms =6.132s** for interior theoretical convolutional
  support (clipped at window boundaries).

For sample `t=16q+r`,0≤r<16, the full convolutional union is
`[16q−12256,16q+12271]`, inclusive. Crucially,49 GroupNorm(1,C) layers use
channel×time statistics, so **actual computational dependence reaches the
whole8s/10s window**. Global statistics are not arbitrary temporal reasoning.
This derivation is not a measured gradient-based effective receptive field.

Encoder basis8ms; hop4ms;250 latent frames/s;64 learned channels. This is a
multichannel filterbank, not scalar audio downsampling with a125-Hz low-pass.
The model combines many frames to represent low-frequency/periodic structure.
The support spans many observed heart-pattern periods and roughly one common
lung-envelope period; it is not an obvious tiny fraction of the relevant
context. No demonstrated severe context mismatch justifies architecture change.
The original [Conv-TasNet paper](https://arxiv.org/abs/1809.07454) provides the
architecture rationale for speech, not a cardiopulmonary guarantee; the
[official implementation](https://docs.pytorch.org/audio/main/_modules/torchaudio/models/conv_tasnet.html)
and installed pinned code establish the layers used here.

## 6. Loss mathematics and measured gradients

For centered estimatev/reference t, `p=<v,t>/||t||²*t`, `e=v−p`,
`D=10log10((||p||²+1e−8)/(||e||²+1e−8))`.
For uncentered waveforms, `A=mean|estimate−target|/(RMS(target)+1e−6)`.
The implemented loss is **mean over batch and sources of−D +5*mean(A)**,
not an unaveraged two-source SI-SDR sum. No PIT.

Ideal SI-SDR optimizes centered waveform direction; L1 constrains amplitude/DC
as well. Reference reconstruction is compatible with those ideal objectives.
The implemented additive epsilons break exact scale invariance near perfect
reconstruction, so a universal common-minimizer claim is not made. Away from
silence, the negative-D gradient is
`−20/ln(10) * [p/(||p||²+eps) − e/(||e||²+eps)]`, with the centering Jacobian.
Scalar values alone cannot quantify gradient influence.

MEASURED, selected checkpoint, no optimizer steps: two predeclared T4 source
pairs (`F_AF_A/F_N_LLA`, `F_ESM_LLSB/F_PR_LLA`), first8s, three two-example
batches at−10/0/+10dB. Same shared peak scaling; gradients over all parameters.

| Level | Norm−SI gradient | Norm5×L1 gradient | L1/SI norm | SI vs L1 cosine | H vs L total-loss cosine |
| ---: | ---: | ---: | ---: | ---: | ---: |
| −10 | 7.407 | 4.397 | 0.594 | 0.708 | 0.345 |
| 0 | 5.397 | 1.163 | 0.215 | 0.804 | 0.818 |
| +10 | 10.331 | 6.377 | 0.617 | 0.593 | 0.508 |

All finite. Individual-case H/L cosines0.200..0.945; no observed opposing
gradients or persistent one-source domination. This small probe cannot rule
out conflict on other batches, but does **not** justify changing coefficient5.
At0dB, scalar5L1=2.344 exceeds |−SI|=1.928 while its gradient norm is only21.5%
of SI's: scalar dominance is not gradient dominance.

For exactly additive targets and consistent outputs, errors are e and−e. The
two per-example normalized-L1 parameter gradients are positive scalar multiples
of the same error gradient, weighted by inverse source RMS. At±10dB, the weak
source receives~3.162×L1 weight; this does not inherently cause semantic conflict.

## 7. Consistency is essential to this trained checkpoint

Let decoder estimates be z_h,z_l and `r=x−z_h−z_l`:
`y_h=z_h+r/2=x/2+(z_h−z_l)/2`, `y_l=x−y_h`.
This target-free layer was applied **during every training forward**. Adding
any common waveform to both z outputs leaves y unchanged, so raw decoder common
mode is unidentifiable by the objective. Removing the layer exposes outputs
that were not trained to satisfy the semantic/amplitude contract independently.

| Representation, same225 validation conditions | H SI-SDRi | L SI-SDRi |
| --- | ---: | ---: |
| Decoder before equal-residual consistency | −7.079 | −6.769 |
| Selected waveform after consistency | 3.101 | 3.130 |

Before→after family H/L: LDM−2.563/−10.715→3.702/3.664;
Tachy−11.595/−2.822→2.501/2.596. Every level's aggregate improves; only7 heart
and6 lung individual conditions worsen. Current scores replay saved T7 within
6.20e−14dB. Thus removing consistency is strongly contraindicated.

Raw residual RMS/mixture RMS: median0.865, range0.726..0.960. Centered residual
correlation with mixture median0.863, heart0.609, lung0.609. Much common signal
is carried through the explicit mixture path; it is not unexplained noise that
an energy heuristic can safely redistribute. Median physical MSE across sources
falls0.003293→0.001189. Raw residual magnitude is not proof of a decoder bug.

For raw errors e_h,e_l, corrected errors are `(e_h−e_l)/2` and its negative.
Summed squared error falls by `0.5*||e_h+e_l||²≥0`. Source-wise SI-SDR/L1 need
not improve monotonically, but exact additive references remain fully feasible:
the projection imposes no intrinsic recovery ceiling. This is different from
the rejected magnitude-mask/mixture-phase diagnostic. Its +0.25dB observation
is not reopened. See [differentiable consistency](https://arxiv.org/abs/1811.08521)
for context; the checkpoint-specific null-space argument above is direct algebra.

## 8. Dynamics, source exposure and seeds

| Run / epoch | Training total | −SI component | 5×L1 component | Validation Q |
| --- | ---: | ---: | ---: | ---: |
| Large8(best) | −2.215 | −4.313 | 2.098 | 3.035 |
| Large20 | −3.706 | −5.535 | 1.829 | 2.508 |
| Small8(best) | −1.718 | −3.910 | 2.192 | 3.101 |
| Small17 | −2.995 | −4.922 | 1.927 | 2.839 |
| Confirmation4(best) | −0.978 | −3.313 | 2.334 | 3.328 |
| Confirmation16 | −3.039 | −4.967 | 1.928 | 2.605 |

Post-best scalar improvement is81.95%,79.25%,80.26% from SI-SDR respectively.
Both terms improve while held-family Q deteriorates. This supports overfit/
finite-data pressure, not specifically L1 optimizing against the selector.

Actual LR used (baseline log's next-epoch field was interpreted correctly):
large .001epochs1–7,.0005epochs8–13,.00025epochs14–18,.000125epochs19–20;
small .001epochs1–10,.0005epochs11–15,.00025epochs16–17;
confirmation .001epochs1–9,.0005epochs10–14,.00025epochs15–16.
Both small optima precede reductions. Later reductions do not rescue Q. Early
stopping preserves best weights; it does not prove that epoch8 is a universal
optimum. A fixed useful update range576–1152 is better supported than extending
training to80epochs. No optimizer explosion/nonfinite failure was observed.

Confirmation minus primary Q≈+0.226dB, balanced mean+0.214dB. But family H/L
changes are LDM+0.160/+0.534 and Tachy+0.303/−0.139. At−10dB, H/L+1.062/+1.222;
at+10dB,−0.446/−1.135. Two seeds reveal redistribution, not an estimable seed
variance distribution. Do not select the higher seed, ensemble seeds, or average
checkpoints post hoc. Within-condition, between-file/family and between-seed
variations are different; none supports225-row IID inference.

**More epochs alone: NO supported reason to expect improvement.** More remixes
can still diversify interference/crops, but they do not expand recorded source
support. More independent non-test family diversity is the highest-priority
available opportunity. New acquisition diversity would be stronger still, but
is outside this bounded plan. No arbitrary noise/EQ/time/pitch augmentation is
justified by a demonstrated missing acquisition invariance; global gain would
largely cancel in the frozen normalization. Architecture change is lower priority.

## 9. Ranked hypotheses and alternatives

Ranks concern the plausible recoverable limitation, not a decomposition of dB.

| Rank / hypothesis | Evidence for | Evidence against / uncertainty | Confidence; likely impact |
| --- | --- | --- | --- |
| 1 A: data-limited source-prior generalization | Only6H/4L training families; periodicity/overlap and recording heterogeneity; extra exposure fits training without better transfer | No causal extra-data experiment; low-order validation descriptors overlap development; no measured9dB gap | Medium; highest expected value, magnitude unknown |
| 2 H: pseudoreplication | 95%pair coverage/128uses per source bybest; overlapping crops; shared validation lung files | Remixes genuinely vary interference; files are not demonstrated duplicates | High as a limitation; benefit requires new family information, not more rows |
| 3 B: mixture/window-distribution mismatch | Discrete endpoints vs continuous levels; local ratios/tailpadding differ | Correct mixing; content/locallevel confound tail effects; no causal alternate-window trial | Medium secondary; possibly meaningful, unquantified |
| 4 I: narrow evaluation/model-selection coverage | Only2shared-lung family groups; seed/family/level redistribution; mean train loss vs weaker-source selector | Valid metric; balanced positive source means; no evaluator defect | High uncertainty limitation, not proof physical quality is only3dB |
| 5 J: learned-prior/inductive-bias difficulty | Overlap and fast repeated structure require useful priors | Small model fits two examples; no structural impossibility; no matched alternate architecture | Low–medium; architecture change unqualified |
| 6 G: optimizer/schedule sensitivity | Best epochs4/8 differ; seed redistribution | Continued training/laterLR drops fail to improve Q; finite healthy gradients | Low as dominant; longer training unsupported |
| 7 F: normalization/source-level issue | Weak-source amplitude errors; crop/full-record locallevels differ | 20log equation, common scaling and gains verified; mean/DC conventions intentional | Low as software defect; no gain correction selected |
| 8 C: objective mismatch | Mean loss differs from maximin selector; amplitude-sensitive L1 | Aligned measured gradients, compatible ideal objectives,79–82%SI contribution | Low dominant support; no loss change |
| 9 E: insufficient temporal support | Long lung periods and padded tails | 6.132s conv support plusglobalnormalization; manyheartcycles; no severe mismatch proved | Low; no RF change |
| 10 D: consistency ceiling | Equal residual can hurt an individual source | Trained layer, additive truth feasible; removingloses~10dBaggregate | Very low; retain unchanged |

Considered interventions: (A) grouped-family qualification→all-non-test refit,
**selected**; (B) remove/energy-weight consistency, rejected by math/replay;
(C) level/crop sampler change, genuine secondary hypothesis but no isolated
evidence or intended-population level distribution; (D) objective change,
unsupported by bounded gradients; (E) RF adjustment, no demonstrated structural
defect. No combinations, averaging scheme or new ensemble are selected.

## 10. Evidence integrity and boundaries

Base implementation `bfb44a61664a017bc538a2c07629032511f30fed`; documentation
`ea6244237f46a9fcfe6aa2bfbffc43bd7dcf0fe9`; both initially clean. Selected
checkpoint SHA `89f8d66134c0a49aa2a05971720cdffbdd1e501ebce99bb83119e6683d58ac93`;
T8 spec SHA `3780292ae6ff1ea6415fc1bd9b4b045bb91d5443068e806b08e9cb39735a1e34`.
Neither changed. Non-test allowlist SHA
`82e677af9f27256aa163b8aa80ca096874bc5cc37da10f29d029f7fee93999dd`.
Frozen validation recipes and source manifest retain the T8 hashes.

Analytical entry points: `scripts/diagnose_plateau_{history,sources,model,context}.py`.
Only the saved non-test allowlist is parsed for audio. No whole-dataset traversal
or test audit helper is called. CPU environment remains Python3.14.4,
torch/torchaudio2.11.0+cpu, two threads, no installs. Probes ran from the above
base with new analytical scripts uncommitted; individual script/evidence hashes
are retained. This is disclosed, not represented as a clean-source training run.
Any future training must begin from a clean committed implementation.

Ignored evidence: `.local/diagnosis/pre_t9_plateau/v1/`, including source rows,
full historical curves/exposure,225before/after metric rows, residuals, gradients
and context receipts. A compact committed
[evidence index](../research/evidence/pre_t9_plateau_v1.json) freezes all9artifact
hashes, script hashes, numerical checks and the planned-intervention hash.
Source statistics took4.04s;225-condition consistency
replay plus gradient probes10.82s. Model state and checkpoint bytes were unchanged.
All-condition regional replay took4.55s.
No optimizer was created by the diagnostic; **zero optimizer updates**.
Checks: strict hash/load/171,313parameters, finite outputs/gradients, saved-score
replay, dB/additivity math, analytical-script compilation and diff/JSON consistency.
No broad unit/application suite, training, CV, final refit or T9 was run.

Graphify connection failed once with OAuth refresh-token error; known current ML
files were read narrowly. No NeoSSNet/license/email research, new projection,
ensemble experiment, test recipe, test statistics, production recording/service,
Axora or submitted FYP1 was accessed/changed. **Stop for owner approval.**
