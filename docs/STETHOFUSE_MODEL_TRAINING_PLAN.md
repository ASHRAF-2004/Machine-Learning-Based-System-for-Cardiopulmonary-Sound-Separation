# ADR T01 — Own StethoFuse separator training plan

**Current continuation:** [pre-T9 plateau diagnosis](PRE_T9_PLATEAU_DIAGNOSIS.md)
and [one-intervention handoff](PRE_T9_LUNA_HANDOFF.md). This is designed, not
executed. T8 bytes remain unchanged; T9 is on hold for owner review. The original
run design/evidence below remains historical and reproducible.

28 September 2026. **T7 COMPLETE; ENSEMBLE RECONSIDERATION COMPLETE;
SMALL TCN STANDALONE SELECTED; FINAL SEPARATOR FROZEN; FINAL TEST SEALED; NOT DEPLOYED.**
See [`T5_T6_BASELINE_EXECUTION.md`](T5_T6_BASELINE_EXECUTION.md) and
[`T7_TUNING_DECISION.md`](T7_TUNING_DECISION.md) for run receipts.
Original ADR T01 inspection: implementation `5d442be5`, documentation `a2fda968`.
This decision supersedes waiting for NeoSSNet permission/native reproduction
before developing **our own** model. It does not retrospectively qualify
NeoSSNet, fix its poor target scores, or authorise production changes.

## Execution status

T0–T4 passed; the frozen CPU T5 baseline completed and T6 selected epoch8 by
the predeclared weaker-source validation score. T7 then evaluated the single
approved smaller-width profile and one predeclared confirmation seed, all on
the frozen validation conditions. The seed-20260928 small profile narrowly
won the frozen selector and is the canonical candidate; its one confirmation
supports **uncertain**, not established, robustness because validation covers
only two family-pair groups. The baseline remains a valid comparator. All
models remain offline research candidates only. The final test is still sealed.
The subsequent validation-only reconsideration selected standalone small TCN
without extra mask projection or a second expert. T8 has now frozen this
separator and predeclared T9; see
[`FINAL_ENSEMBLE_RECONSIDERATION.md`](FINAL_ENSEMBLE_RECONSIDERATION.md) and
[`research/configs/final_separator_v1.json`](../research/configs/final_separator_v1.json).
T9 awaits separate explicit owner approval. No further fusion experiment,
application integration or deployment is authorized.
See [`T7_TUNING_DECISION.md`](T7_TUNING_DECISION.md) and
[`T7_LUNA_HANDOFF.md`](T7_LUNA_HANDOFF.md) for immutable run hashes, results,
limitations and completed execution contract.

## 1. Decision

**Train StethoFuse-ConvTasNet-4k-v1 from scratch:** a compact, non-causal,
fixed-label time-domain separator, using the BSD-2-Clause
`torchaudio.models.ConvTasNet` component, plus our waveform mixture-consistency
wrapper. **645,681 trainable parameters; channel 0 heart, channel 1 lung.**
No pretrained weights, PIT, oracle source swap, reference-based alignment,
NeoSSNet imports, or external author code/checkpoints in the production path.

This is the strongest *practical starting decision*, not a demonstrated best
model. A learned waveform basis avoids restricting recovery to the mixture's
STFT phase, the depthwise TCN supplies temporal context without attention, and
the measured compact configuration fits the current CPU. Those properties
justify an experiment; speech results do not prove cardiopulmonary quality.

The authoritative machine-readable starting settings are
[`research/configs/stethofuse_tcn_v1.yaml`](../research/configs/stethofuse_tcn_v1.yaml).
Luna must not silently substitute the much larger library default model.

### Serious alternatives considered

| Candidate | Evidence and trade-off | Decision |
| --- | --- | --- |
| Independently implemented NeoSSNet-inspired conv encoder/attention mask/decoder | Direct neonatal task relevance (Poh et al., 2024), but the released architecture has 8.42M parameters, unclear reusable weights, and unresolved native reproduction. A scratch reimplementation would add capacity and reproduction work without established manikin benefit. Published architecture ideas can inform research; do not copy unlicensed source. | Not the starting model. Released checkpoint remains research comparator only. |
| **Compact Conv-TasNet-style TCN** | Luo and Mesgarani (2019): waveform encoder, dilated depthwise separator, learned decoder. Permissively licensed maintained library implementation is available. Our 0.646M configuration is about 13 times smaller than the inspected NeoSSNet; synthetic forward/backward is CPU-feasible. Learns phase through waveform reconstruction. Risks: small-data overfit and speech-to-chest architectural transfer remain unproven. | **Selected**, with fixed heart/lung labels and no speech pretraining. |
| TF U-Net / magnitude masks | Jansson et al. (2017) demonstrate source-separation use of encoder/decoder skip connections; Ronneberger et al. (2015) establish U-Net. Fixed spectral representation and multiscale structure are attractive with limited data. However, bounded magnitude masks with unchanged mixture phase restrict cancellation/reconstruction; complex spectral mapping adds another design choice. Music/image success is not chest-sound evidence. No author cardiac checkpoint was verified. | Credible alternative, not another run in this first plan. No unverified third-party U-Net source is adopted. |

**Transfer choice:** scratch, not frozen speech encoders or NeoSSNet adaptation.
The torchaudio speech-separation bundles are not a verified 4-kHz, fixed-semantic
heart/lung initialization; their two-speaker pretraining and different waveform
basis would introduce confounds. Randomly initialized, fully trainable compact
layers give a cleaner first experiment. No external checkpoint is downloaded.

## 2. Data and rights: small, manikin, family-held-out

The [official Zenodo release](https://zenodo.org/records/15376628) contains 535
recordings. Its [record API](https://zenodo.org/api/records/15376628) explicitly
reports `metadata.license.id = cc-by-4.0` and open access. Record this license,
Torabi/Shirani/Reilly attribution, DOI, source hashes and our transformations
with training artifacts. Public access alone is not the permission basis.

Only the **50 standalone HS + 50 standalone LS** tracks are eligible here.
Do not use the 145 recorded mixtures or their separately recorded companion
tracks as additive supervised targets: prior diagnosis found that recorded
triples are not aligned sample-wise sums. Do not use them to enlarge the
training pool across unknown source/template lineage.

| Partition | Heart files / families | Lung files / families | Available source duration | Cartesian source pairs |
| --- | ---: | ---: | ---: | ---: |
| Development → training | 36 / 6 | 36 / 4 | 9 min heart + 9 min lung | 1,296 |
| Validation | 9 / 2 | 5 / 1 | 135 s heart + 75 s lung | 45 |
| Locked test | 5 / 2 | 9 / 1 | 75 s heart + 135 s lung | 45 |

Every file is 15 s. Remixes/crops are correlated reuse of **72 training source
recordings**, not 1,296 independent physiological samples. The grouping is
sound family, not verified subject/session/template. Manikin/device and source
filtering can create confounds. There is no established patient-, device- or
subject-independent generalisation, nor evidence that separated source tracks
are noise-free clinical truth.

### Frozen manifest and actual audit

[`research/manifests/hls_cmds_split_v1.csv`](../research/manifests/hls_cmds_split_v1.csv)
is now the versioned source of truth. SHA-256:
`39d5456477b07772bdc24b86ee73dee17c44fd1e0837b62b96eab8c19a1b65e4`.
It preserves every existing source assignment and source-byte hash from the
ignored Phase-D manifest (that manifest's SHA-256:
`baa88bb7b23480a44296b54ef747daf13c61ec6c1d430d375956dcf5392a4fb2`).
Metadata audit: **100 IDs, 100 distinct hashes, zero family spanning partitions**.
No split correction was supported by the available metadata; test IDs did not
change. Hash uniqueness excludes exact duplicates, not hidden shared templates.

- Train HS: Normal, Atrial Fibrillation, Early/Mid/Late Systolic Murmur, S3.
  Train LS: Normal, Pleural Rub, Rhonchi, Wheezing.
- Validation HS: Late Diastolic Murmur, Tachycardia; LS: Fine Crackles.
- Test HS: AV Block, S4; LS: Coarse Crackles. Exact IDs/hashes are in the CSV.

Load/filter the manifest **before opening any WAV**. Train and ordinary
validation entry points reject `test`; they must not call the old `sources()`
function that opens all partitions. Do not regenerate random file splits.
Final testing requires a frozen model/protocol manifest and explicit final-test
entry point. Before training, any newly discovered *metadata-proven* shared
template crossing partitions requires a documented split correction and owner
review, not a quiet reassignment. Never revise the split after seeing scores.

The earlier audit established that all535 local WAVs byte-match the release.
**The released archive inspected for this project contains 4 kHz WAV files.
Earlier acquisition/conversion provenance could not be established.** The
README's22,050-Hz description does not justify inventing resampling. Train at
4 kHz, mono, PCM16 decoded as float32 `/32768`; Nyquist is2 kHz. Do not upsample,
bandpass, denoise or independently normalize source files in v1.

This sprint opened **only the72 development WAVs** for format/energy summaries;
validation/test audio was neither opened nor scored. Development HS RMS
min/median/max:0.000926/0.003391/0.013372; LS:0.000458/0.003113/0.009576.
Maximum peaks0.1140/0.1917; no samples at PCM rails. These unequal recording
levels motivate RMS-defined relative mixing, not equal raw amplitude. They do
not establish an in-vivo heart/lung ratio distribution.

## 3. Exact model and signal contract

Instantiate the pinned library component with:

```python
ConvTasNet(num_sources=2, enc_kernel_size=32, enc_num_feats=128,
           msk_kernel_size=3, msk_num_feats=64, msk_num_hidden_feats=128,
           msk_num_layers=8, msk_num_stacks=3, msk_activate="relu")
```

- Linear learned encoder:128 filters,32 samples/8 ms, stride16/4 ms, padding16;
  global normalization then64-feature bottleneck.
- Three repeats of8 depthwise TCN blocks; dilations1,2,4,…128; kernel3;
  hidden128, residual/skip64, PReLU and affine single-group normalization
  (`eps=1e-8`), no BatchNorm or dropout. Last block needs no residual branch.
- Two ReLU latent masks, shared linear transposed-convolution decoder. Masks
  are on the learned representation, **not magnitude masks on a fixed STFT**.
- Nominal dilated-convolution span1531 encoder frames (about6.13 s including
  the encoder); global normalization also uses the whole supplied window.
  This is non-causal/offline, not a low-latency streaming medical device.
- Right-pad to encoder stride and crop exactly to input length. Training input
  `(B,1,32000)`; output `(B,2,32000)`. Inference accepts each10-s window and
  trims padded tails. Check malformed lengths/NaN/Inf, never silently swap.

For decoded waveforms `z_h,z_l` and input `u`, apply the equal residual
mixture-consistency projection (Wisdom et al., 2019):

`e = u − z_h − z_l;  h_hat = z_h + e/2;  l_hat = z_l + e/2`.

This is differentiable, target-free, in both training and inference. It ensures
additivity, **not correct separation**, and is not the historical ensemble's
STFT-magnitude projection. With two targets and no added noise it matches the
training equation. Real noise will be allocated to these outputs; v1 is not a
three-source denoiser. Store raw decoder diagnostics if useful, but score and
deploy only the same declared projected model. Never use references at inference.

### Windows and gains

Training: independent8-s/32,000-sample valid crops from each15-s source. This
balances temporal context and crop diversity; the range also aligns with the
8-s training duration documented for NeoSSNet, without claiming identical data.
Inference/validation:10-s windows,8-s hop,2-s complementary cosine overlap;
right zero-pad tails, trim exact length, divide accumulated window weights.
Use nonzero outer edges, as in the existing ensemble window contract.

One input peak `p=max(abs(x))` is shared with both targets. Network input is
`u=x/p`, targets are `[h/p,l/p]`; restore outputs by `p`. For long recordings,
compute `p` once for the entire recording, not separately for each window.
Outputs remain finite float32 and may exceed unit amplitude in normalized
coordinates; do not clip or independently peak-normalize them. A later audio
export must preserve gain metadata and prevent PCM clipping jointly, not alter
the evaluator. No global polarity flips or target-assisted delays.

Zero input returns two zero arrays without model execution; near-silent whole
input (`RMS<1e-6`) is rejected as uninformative. Training crops with centered
source RMS below1e-6 are retried at most3 times, then fail visibly; they are not
assigned fabricated SI-SDR scores. Validation/test invalidity stops the study
for documented investigation, not selective sample removal.

## 4. Reproducible mixture generation and augmentation

For each valid cropped source pair `h0,l0`, calculate RMS in float64. Sample
`r ~ Uniform[-10,+10] dB`, defined explicitly as **lung-to-heart energy level**:

`a = RMS(h0) / RMS(l0) * 10**(r/20)`

`P = max(peak(h0), peak(a*l0), peak(h0+a*l0))`

`c = 0.95/P;  h = c*h0;  l = c*a*l0;  x = h+l`.

Apply `c` to both contributions, then the shared network normalization above.
Keep contributions and sum in float32; check additivity within1e-6 after
conversion. No quantization/clipping or target-dependent inference operation.
Including both references in `P` prevents clipping of digital source artifacts
even where mixture cancellation occurs. `c` may amplify quiet recordings; it
does not change the relative level. Record `a,c,p`, not just the requested dB.

The **range**, not a population probability claim, is grounded in the original
NeoSSNet [author mixing specification](https://github.com/yangyipoh/Neonatal-Chest-Sound-Separation-using-Deep-Learning/blob/d97886b93bd2e71fd019c6b5073bb2dce2854ade/hlsdata.py):
continuous training levels across−10…+10 and five evaluation levels at5-dB
spacing. We independently implement that conventional energy equation; do not
reuse its loader, noise curriculum, source split or unscaled target behavior.
The chosen envelope contains the previous−5/0/+5 development cases. It is not
proof of robustness outside this range or on real co-recorded mixtures.

**Epoch =576 draws =144 optimizer steps at batch4**, not all1,296 pairs.
Construct24 occurrences of each of the24 train heart-family × lung-family
combinations, shuffle the576 schedule, and draw source files from independently
reshuffled cyclic queues within each family. Within a family, source usage
differs by at most one per epoch. Smaller families are deliberately oversampled
to prevent Normal dominating. Log realized file/family counts and repeat pairs.
For each draw choose independent integer crop starts uniformly in[0,28000]
and the relative level above. Independent starts vary alignment without wrap,
pitch changes or altered physiology.

Use NumPy `Generator(PCG64(SeedSequence(key)))`, epochs numbered0…79, and
sorted family/ID lists. Schedule key=`[seed,epoch,0]`: form the sorted24-family-
pair product, repeat it24 times, then shuffle. Queue key=
`[seed,epoch,kind_index,family_index,2]` (HS=0,LS=1): independently shuffle
each family's sorted file IDs, consuming/refilling its queue in schedule order.
Example key=`[seed,epoch,draw_index,1]`: draw heart start, lung start, then r
in that order. Save each realized epoch recipe before training it. These keyed
streams must replay on resume and with future worker-count changes. Pin NumPy
and save RNG states; do not seed from wall-clock time or worker completion order.

Only augment **pairing, valid crop/relative offset and relative level** in v1.
Do not add pitch shift, time stretch, arbitrary EQ, convolutive filters or
unjustified noise. Global gain augmentation is omitted because subsequent
shared peak normalization would cancel it. No massive WAV mixture store:
keep source cache (~17 MB for training float32 arrays) plus metadata recipes.

## 5. Loss and pre-registered model selection

For each fixed source, use the existing mean-centered SI-SDR definition:
`t=s−mean(s)`, `v=estimate−mean(estimate)`,
`q=<v,t>/<t,t>*t`,
`D=10*log10((sum(q²)+1e-8)/(sum((v−q)²)+1e-8))`.
Reject invalid/silent references before this computation. Keep the audited
float64 NumPy evaluator unchanged (agreement within1.57e−7 dB was already
established). Implement its differentiable float32 training equivalent once;
do not replace evaluation with PIT or a library's differently defined score.

**Loss:**

`L = mean_over_batch_and_sources(−D + 5*A)`

where `A=mean(abs(estimate−target))/(RMS(target)+1e-6)` on **uncentered**
waveforms at shared input scale. Negative SI-SDR optimizes the stated objective;
one normalized waveform-L1 regularizer preserves amplitude/DC information that
SI-SDR alone discards and gives weak sources equal consideration. Weight5 is a
pre-registered engineering starting choice, not a paper-optimal value. No other
spectral/mask/adversarial loss in baseline v1. Fixed labels, no PIT.

### Validation recipe and balanced selection

Use all45 validation source pairs × levels`[-10,-5,0,5,10]` = **225 correlated
conditions**, full15-s sources starting at0, no random crop or noise. Normalize
with the same single mixture gain, infer using10/8-s overlap windows, then score
the **entire15 s**. The test recipe is the same algorithm on its distinct45
pairs; freeze the recipe now but do not generate/read test waveforms.

For each source, calculate SI-SDRi against the same original mixture and target.
Average levels, then file pairs **within each heart-family × lung-family
group**, then average groups equally. Call the resulting source macro means
`H` and `L`. Validation has only2 such groups; report this limited support.

**Select by `Q=min(H,L)` (maximize the weaker source), tie-break by `(H+L)/2`.**
This deliberately rejects sacrificing one output to inflate a joint average.
Save a better checkpoint if Q improves by>1e-6 dB; within that tie tolerance,
prefer higher balanced mean, then earlier epoch. Save diagnostic best even if
negative, but never call it a qualified production model. Report pooled
mean/median/IQR and per-source/per-level scores as well; do not hide strong
source behavior behind Q or confuse macro selection with pooled reporting.

All225 conditions must produce finite, non-silent source estimates with exact
length; any failure invalidates that epoch for selection. A candidate needs
both source macro absolute SI-SDR and SI-SDRi positive, zero failures, and a
validation comparison to frozen baselines. Positive improvement alone is not
proof of useful absolute reconstruction or superiority. No promised dB target.

## 6. One baseline run, bounded tuning

| Setting | Frozen baseline |
| --- | --- |
| Initialization / seed | All layers library-default random initialization; seed20260928; no pretraining |
| CPU batch / precision | 4 ×8 s; fp32; no AMP/compile;2 Torch threads,1 interop; loader workers0 |
| Optimizer | AdamW; LR0.001; betas(0.9,0.999); eps1e-8; weight decay1e-4 on all parameters |
| Gradient control | Global L2 norm clip5.0; reject nonfinite loss/gradients before optimizer step |
| Schedule | ReduceLROnPlateau on Q, maximize, factor0.5, patience4, absolute threshold0.1 dB, minLR1e-5 |
| Duration | Max80 epochs/11,520 steps; early stop after12 consecutive epochs without ≥0.1-dB gain in Q over the last significant-improvement anchor |
| Validation | Every epoch, full fixed225-condition validation recipe, eval/inference mode, never test |
| Checkpoints | best by exact Q/tie rule; final last completed epoch; resumable state; no best-by-test |
| Reproducibility | Seed Python/NumPy/Torch; deterministic algorithms; benchmark disabled; record library/device versions; no silent device fallback |

Scheduler significance and early stopping are separate from saving every
strictly better best checkpoint. Resume restores optimizer, scheduler, epoch,
RNGs, sampler and early-stop anchor; restart-from-scratch is a different run.

**T7 complete (ADR T02):** the sole N64/B32/H64 profile (171,313 parameters in
the pinned torchaudio build; original design estimate 170,545) passed the
capacity gate and completed a fresh seed-20260928 run. All other scientific
settings remained fixed. It narrowly ranked ahead of the eligible baseline by
the predeclared Q/tie rule (+0.066 dB Q, +0.059 dB mean); this is descriptive,
not evidence of superiority with two family-pair validation groups. Exactly
one seed-20260929 confirmation was run after selecting the small profile. It
does not replace the canonical seed-20260928 checkpoint; robustness is
**uncertain** because family/level behavior differs. No second variant, extra
seed, test access or application work occurred. The original baseline remains
a valid comparator. Full evidence is in the T7 decision and handoff.

## 7. Hardware and bounded feasibility evidence

Read-only inspection: Ryzen5 9600X,6 cores/12 threads;29 GiB RAM, about22 GiB
available;374 GiB disk available; Ubuntu26.04/kernel7.0.0-31. Discrete Radeon
RX9060XT has approximately16 GiB VRAM; an integrated GPU has512 MiB. The current
isolated environment has Python3.14.4, Torch/torchaudio2.11.0+cpu, no CUDA/HIP
build and no usable Torch accelerator. No NVIDIA GPU or ROCm utility was found.

**CPU is the runnable baseline.** AMD's current official ROCm documentation
lists gfx1200/RX9060XT support, but that does not establish a working local
PyTorch stack. Do not install NVIDIA CUDA, replace host drivers or use an
undocumented device override. Optional isolated ROCm qualification can be a
later separately approved task; no paid cloud/GPU is required for this plan.

Reproducible retained probe:

```sh
nice -n 10 .local/ensemble/venv/bin/python scripts/probe_stethofuse_training_design.py
```

Synthetic signals only,2 threads, **zero optimizer steps**. Model parameter
fingerprint was unchanged. Exact train/inference/odd-tail shapes, finite loss
and gradients, repeat-identical inference passed. Count645,681. One final
probe measured batch4 ×8-s forward0.139 s; forward+loss+backward0.343 s;
warmed batch1 ×10-s inference0.0194 s; process peak RSS1155 MiB; projected
sum error1.19e−7. These are a few untrained synthetic executions, **not a
trained-model benchmark, training throughput guarantee or quality result**.

At144 steps/epoch, this suggests roughly50 s compute plus validation and I/O;
budget **1.5–4 hours** for an80-epoch CPU baseline as an estimate, with likely
early stopping. After3 real epochs, replace the estimate with measured elapsed
time; checkpoint/stop if projected runtime exceeds8 h or process RSS4 GiB.
Use low-priority offline execution with2 threads and no production mounts,
database credentials, GPU driver changes or workload in production containers.
The unchanged application must retain resources. No long job ran this sprint.

### One resource fallback, not an architecture search

If a measured resource blocker remains after reducing microbatch4→2→1 with
gradient accumulation preserving effective batch4, use **the same TCN with
N64/B32/H64**, keeping L32/X8/R3 and the rest fixed. T01 estimated170,545
parameters; the T7 construction check measured **171,313** in the pinned build.
This is a new named configuration/run, not an automatic mid-run substitution.
It must pass the same overfit gate. Do not activate it because of disappointing
test scores. If this also is impractical, checkpoint and request direction;
no automatic paid cloud, broader architecture sweep, or hours of retries.

ADR T02 additionally selects this same width profile as the **one capacity
tuning experiment** under the owner's later request. That is a documented
extension of its original resource-only purpose, not an automatic fallback or
change to the historical baseline YAML. It still requires the small-model
capacity gate; failure does not authorize another architecture.

## 8. Exact Luna execution phases

The T0–T6 rows retain the original design-phase paths/estimates for traceability;
actual executed entry points and results are in T0_T4_EXECUTION.md and
T5_T6_BASELINE_EXECUTION.md. In particular, the implemented trainer is
`scripts/train_stethofuse_baseline.py`, not `train_stethofuse_model.py`.
Use the T7 handoff for current exact paths. Do not repurpose DB-writing legacy
training commands. Runtime ranges are estimates, not implementation deadlines.

| Phase / likely files | Acceptance and focused check | Compute cap / checkpoint |
| --- | --- | --- |
| **T0 split/environment freeze** — `research/manifests/hls_cmds_split_v1.csv`, config, research dependency lock | Verify manifest hash, ID/hash/family disjointness, development/validation file hashes and exact format; test waveform paths remain unopened. Pin current environment. One metadata/partition-denial test. | Minutes, no model run; record freeze receipt. |
| **T1 mixture generator** — new `app/ml/training_data.py` | No DB imports. Filter partition first; balanced576 schedule and deterministic crops/gains; shared amplitude/additivity; save recipes. One focused replay/additivity/partition contract using synthetic arrays. | Minutes; inspect a few development mixtures, no test. |
| **T2 model wrapper** — new `app/ml/stethofuse_tcn.py` | Pinned torchaudio component, fixed semantics, consistency/gains/windowing, exact shapes/finite output, expected645,681 parameters. No factory/API registration yet. Reuse probe; one contract test. | Seconds per smoke; checkpoint architecture/config. |
| **T3 objective/evaluator** — new `app/ml/training_objective.py`, `scripts/evaluate_stethofuse_model.py` | Keep audited `si_sdr` formula; if extracted to `app/ml/metrics.py`, preserve old import compatibility unchanged. Differentiable fixed-label loss, same-mixture SI-SDRi, Q selection. One analytic metric-parity/selection check, not a new metric campaign. | Minutes; no training/test evaluation. |
| **T4 capacity gate** — new `scripts/train_stethofuse_model.py --stage overfit` | Two previously used development pairs F_AF_A/F_N_LLA and F_ESM_LLSB/F_PR_LLA; crop0:32000,0 dB; fixed recipe, batch2, no augmentation/scheduler/decay. Same model/loss/LR; evaluate every20 steps. Each of four source/case scores must gain≥10 dB over its mixture and mean normalized L1 drop≥50% from initialization. Finite gradients and exact additivity throughout. Never reuse these fitted weights for baseline. | ≤400 updates or10 min, whichever first; **checkpoint and inspect before T5**. Failure blocks full training. |
| **T5 baseline** — same trainer `--stage baseline` | Fresh seed/init; only train families; all configured settings; actual time/RSS and validation logged each epoch; atomic resumable checkpoints. One tiny interrupted/resumed-state contract test, not another training campaign. | Estimated1.5–4 h; audit at epoch3; stop≤80 epochs/early-stop or resource guard. |
| **T6 validation diagnosis** — evaluator and run report | All225 val conditions, heart/lung scores, failures, runtime, source-family/level breakdown. Compare frozen baselines; no superiority from training/overfit. | Model minutes; comparator cost measured first with a bounded development run; checkpoint results for owner. |
| **T7 bounded tuning — COMPLETE** — T7_TUNING_DECISION.md; T7_LUNA_HANDOFF.md | One smaller-width variant; selected by frozen Q/tie selector; one confirmation. Results are validation-only and robustness uncertain. | Completed at clean implementation source commit `1950fc0`; stop for owner review. |
| **Validation-only ensemble gate — COMPLETE** — FINAL_ENSEMBLE_RECONSIDERATION.md | Decision B: original small TCN waveform standalone. Weak localized filter/NMF complementarity does not justify a fusion experiment. | Complete; test remains sealed. |
| **T8 final freeze — COMPLETE** — `research/configs/final_separator_v1.json` | Locks model/checkpoint, source/config/recipe hashes, inference behavior, comparator set, failure rules and exact T9 reporting protocol. | Complete; T9 requires separate explicit owner approval. |
| **T9 one-shot final evaluation — PREDECLARED, NOT RUN** | Frozen manifest test partition: 5 heart × 9 lung sources =45 pairs; five fixed levels =225 conditions, full15-s references. Compare mixture, selected TCN, Fixed Filter, Generic NMF. Report per-condition failures, source metrics, equal-family macro and pooled median/IQR, runtime. | No test recipes/audio opened. One run only; no test-driven selection or tuning. |
| **T11 application integration** — existing strategy/job/private-result path | Later owner-approved local integration only after useful validation/evaluation and artifact/license qualification. Durable worker/security design remains unchanged. | Separate milestone; no auto-deploy. |

The original first execution handoff was **T0–T4**; it, T5/T6 and T7 have
completed. Do not repeat them. Ensemble reconsideration and T8 freeze are
complete; T9 is predeclared and awaits explicit owner approval. Reuse focused pipeline contracts; add
another only for a concrete changed contract or defect. No broad application
test suite merely for documentation. One nearby ML regression at the eventual
implementation milestone, not after every edit.

## 9. Failure and escalation rules

- **CUDA/HIP unavailable:** use the already specified CPU baseline; no silent
  GPU assumption, installation loop or host-driver change.
- **OOM/resource cap:** save state if safe, stop; one microbatch-reduction pass
  with accumulation, then the single width fallback if needed. Log actual
  batch/effective batch; never change it without provenance.
- **NaN/Inf:** abort before optimizer update; save recipe/config/last finite
  state, not a corrupted best checkpoint. Check input scale, silent crops and
  gradients once; one diagnosed repair/retry, then stop for review.
- **Tiny set will not overfit:** inspect additivity, labels, normalization,
  gradient/optimizer wiring and consistency once. One corrected retry at the
  same cap; do not launch baseline or simply increase epochs.
- **Validation never improves / one source collapses:** normal patience stop;
  show both sources and per-family/ratio breakdown. Do not deploy best-negative
  weights, relabel channels, tune test, or start an automatic model search.
- **Runtime impractical:** epoch3 estimate/resource guard stops the run. CPU
  fallback or separately qualified existing GPU, not paid services by default.
- **Final test poor:** report it. Only a documented genuine implementation bug
  can justify a transparent rerun; disappointing results cannot.

## 10. Reproducibility and artifact handling

Runs live outside source history under ignored
`.local/training/stethofuse-tcn-v1/<run-id>/`. Example contents:

```text
config.yaml                 immutable effective configuration
environment.json            Python/NumPy/Torch/torchaudio, OS/device, threads
run.json                    IDs/hashes/status/timestamps/duration
split.csv                   exact frozen metadata snapshot
recipes/epoch-000.jsonl      source hashes, starts, r/a/c/p, mixture hash/ID
metrics.csv                 epoch/loss/LR/H/L/Q and absolute source metrics
validation/per_record.jsonl all source/pair/level scores and failures
checkpoints/best.pt          model state_dict, architecture version
checkpoints/final.pt         last completed state_dict, not silently "best"
checkpoints/resume.pt        optimizer/scheduler/RNG/sampler/stop state
checksums.sha256            checkpoint/config/manifest/recipe hashes
freeze.json                 only after validation model/protocol selection
```

Run manifest fields: run ID, parent/run purpose, Git SHA and dirty status,
architecture and preprocessing versions, source-manifest hash and actual
train/val IDs, config hash, seeds, library/device/hardware, optimizer/scheduler/
loss, executed epochs/best epoch, training and validation durations, memory,
source-order, selected metrics, failed examples and checkpoint hashes.
Mixture ID derives from canonical serialized recipe; additionally hash generated
little-endian float32 arrays for replay. Record NumPy RNG details and floating-
point environment; do not promise cross-device bit identity. CPU repeatability
must be tested locally; ROCm results would carry separate device provenance.

Use state dictionaries, strict version/shape loading, atomic file replacement,
and SHA verification; do not load arbitrary external pickled model objects.
Keep model weights and full run logs out of Git. Commit compact manifests,
configs, source, model card and bounded result summaries only. Store best and
final checkpoints separately; never register them in the application database
from a training command. Later release packaging can take our selected artifact
by verified hash and include data attribution/library notices; it requires a
separate deployment gate and does not use the research directory as a public mount.

## 11. Evaluation, ensemble and production limits

Final methods: mixture, Fixed Filter, current generic NMF, our selected model;
VMD only if a strict no-fallback comparable4-kHz path is qualified **on
development first**; NeoSSNet only as a clearly labelled research comparator
where appropriate. Freeze exact code/config/checkpoint identities beforehand.
Existing VMD presets internally downsample and may fall back, so do not call
those executions a strict equal-rate VMD baseline without qualification.
Fixed Filter remains1024/256 STFT with existing180/35-Hz heart and130/55-Hz
lung transitions; NMF remains6 components/80 iterations/seed42. No quiet
comparator tuning. Run the common10/8-s window/gain wrapper, float outputs,
fixed labels and the same audited metrics; no independent peak normalization,
source swapping, reference alignment or historical FYP1 score reuse.

Report **heart and lung separately**: each condition's SI-SDR/SI-SDRi, pooled
mean/median/IQR, family/ratio breakdown, failure count and runtime. Explain
macro validation selection separately. Comparisons are paired on the same
mixtures, but225 conditions/45 pairs are not independent observations. With
only two held-out heart and one lung family, do not claim inferential
significance from naïve225-row tests or strong population confidence intervals.
Descriptive paired differences and transparent worst cases suffice for this FYP.

Only validation can later decide whether our expert complements a lawful NMF
expert or warrants replacement of the research-only NeoSSNet. Implementing NMF
ourselves is feasible: existing NumPy multiplicative updates already do so;
later supervised/source-labelled bases or a periodicity prior could be authored
from established equations with citations. That does **not** establish useful
separation, and needs its own bounded qualification. LingoNMF remains a possible
licensed comparator, not a new production dependency. Do not add/tune experts
or50/50 weights during this plan.

If a stronger ensemble is evaluated, choose it on validation and freeze before
the same single final test. If it degrades either source, do not degrade the
deployed choice merely to advertise an ensemble. Whether ensemble becomes a
research component or deployed default needs owner/FYP-requirement review;
it is not decided here. Production remains the working application with no
experimental ML integration. No clinical, neonatal, real-patient, noisy-world,
subject-independent, superiority, or double-digit performance claim is supported.

## 12. Code map and licensing boundaries

Graphify was attempted first but returned **MCP authentication required**; no
reauthentication/reindex loop. Known current files were inspected narrowly:

- `app/ml/strategy_factory.py`: legacy research strategy registry; no registration change now.
- `app/ml/ensemble_v1.py`: NeoSSNet/NMF raw adapters and frozen complementary-mask engine; stays unchanged.
- `app/ml/strategies/nmf_strategy.py`: own generic multiplicative-update baseline; no imported external NMF code required.
- `app/ml/audio_utils.py`: fixed centered STFT/ISTFT and comparator utilities; no boundary rewrite needed.
- `scripts/evaluate_ensemble_qualification.py`: audited metric and original family metadata; do not execute its all-source scan for training.
- `app/ml/hls_cmds_dataset.py`, `scripts/train_neossnet_hls.py`: obsolete paired-recording15-s loader, NeoSSNet dependency and database registration; **not the new trainer**.
- `scripts/train_model.py`: empty placeholder, not an existing functioning training pipeline.

The original naplab repository advertises CC-BY-NC-SA3.0-US; do not copy it
under an assumed permissive license. The selected component is specifically
the **torchaudio2.11.0 distribution under BSD-2-Clause**, with PyTorch's own
BSD-style notices retained. Our wrapper, recipes, labels and training are our
work; do not claim invention of Conv-TasNet. No NeoSSNet source/weights may enter
the production artifact or be required by its imports. Data and software
attribution are distinct. A deployment license/dependency manifest will include
the exact binary/source notices; this design is not a legal warranty.

## Sources used (primary records; APA 7 bibliographic metadata)

- Luo, Y., & Mesgarani, N. (2019). Conv-TasNet: Surpassing ideal time–frequency magnitude masking for speech separation. *IEEE/ACM Transactions on Audio, Speech, and Language Processing, 27*(8), 1256–1266. https://doi.org/10.1109/TASLP.2019.2915167
- Jansson, A., Humphrey, E., Montecchio, N., Bittner, R., Kumar, A., & Weyde, T. (2017). Singing voice separation with deep U-Net convolutional networks. In *Proceedings of the 18th International Society for Music Information Retrieval Conference* (pp.745–751). https://archives.ismir.net/ismir2017/paper/000171.pdf
- Ronneberger, O., Fischer, P., & Brox, T. (2015). U-Net: Convolutional networks for biomedical image segmentation. In *Medical Image Computing and Computer-Assisted Intervention—MICCAI 2015* (pp.234–241). https://doi.org/10.1007/978-3-319-24574-4_28
- Poh et al. (2024), Torabi et al. (2025), Le Roux et al. (2019), and Wisdom et al. (2019): complete verified entries remain in FYP2 `provenance/ensemble-references.bib`; see the existing diagnosis for NeoSSNet's incompatible published-metric aggregation. No author-email workflow continued.
- PyTorch contributors. (n.d.). [ConvTasNet, torchaudio2.11 API](https://docs.pytorch.org/audio/2.11.0/generated/torchaudio.models.ConvTasNet.html), [BSD-2-Clause license at the release](https://github.com/pytorch/audio/blob/v2.11.0/LICENSE), and [source](https://github.com/pytorch/audio/blob/v2.11.0/src/torchaudio/models/conv_tasnet.py). Accessed28 September2026; API/license facts, not evidence of chest-sound performance.
- AMD. (n.d.). [ROCm GPU specifications](https://rocmdocs.amd.com/en/develop/reference/gpu-specs.html) and [ROCm transition guide](https://rocm.docs.amd.com/en/latest/about/transition-guide-TheRock.html). Accessed28 September2026; local GPU training remains unverified.

**Checkpoint outcome:** a complete training decision, frozen metadata/config
and tiny synthetic design probe; zero training runs/optimizer steps, zero new
automated tests, no final-test access, no application or production change.
