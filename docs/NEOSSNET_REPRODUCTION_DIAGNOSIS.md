# NeoSSNet reproduction diagnosis — 27 September 2026

**DEVELOPMENT DIAGNOSTIC / NOT FINAL. Outcome D for the present target-domain
expert qualification:** the released model's labelled heart/lung separation is
not qualified on these manikin sources, and a global swap does not repair both
sources. This is **not** proof that the published neonatal result is wrong.
Native reproduction remains blocked by unavailable neonatal reference/fold
artifacts and an unverified checkpoint-to-experiment correspondence.

**ENSEMBLE DESIGN MUST BE REVISITED at its conditional expert-qualification gate.**
The implemented 50/50 formula stays frozen; no replacement, weight tuning,
learned gate, fine-tuning, application integration or deployment is authorised by
this diagnosis. The weak expert must be resolved before optimising its fusion.

Baseline inspected: implementation `e42d5f7`, documentation `2ccab43`.
Graphify still indexed `559ddba2`; it located legacy ML paths but did not cover
the current ensemble. Only directly relevant current source was then inspected.
Production, held-out validation/test audio, FYP1 and external services were untouched.

## 1. Why the published numbers are not a like-for-like target

The [original paper, Table VII](https://doi.org/10.1109/OJEMB.2024.3401571)
labels the baseline's heart/lung SI-SDR as **16.00/14.46 dB**. Its **14.76 dB
entry is lung SDR**, not heart SI-SDR. Those headings must be cited accurately.

However, the author's [results notebook at the released revision](https://github.com/yangyipoh/Neonatal-Chest-Sound-Separation-using-Deep-Learning/blob/d97886b93bd2e71fd019c6b5073bb2dce2854ade/results.ipynb)
contains the exact displayed baseline row `8.42, 16.39, 14.76, 16.00, 14.46`.
Its `extract_result()` reads **SDR improvement / SI-SDR improvement** columns,
takes each noise category's median, then averages the three category medians
(NoNoise, general, respiratory support). Baseline points to `all1` in an external
model/results directory, not a published hash manifest. The CSVs are absent.
The paper-heading/notebook-calculation discrepancy needs author clarification;
we must not silently treat this row as mean absolute SI-SDR on arbitrary data.

There is a second concrete difference. Author `evaluate.py::signal_x_ratio_eval`
calls `fast_bss_eval.si_sdr(ref, est, return_perm=False)`. The official
[API documentation](https://fast-bss-eval.readthedocs.io/en/latest/#fast_bss_eval.si_sdr)
and installed 0.1.4 show that this still optimises a **per-record permutation**;
the flag only suppresses returning the permutation. Its SDR call separately
disables permutation. We do not reproduce that oracle reassignment in target
evaluation. A synthetic two-tone demonstration gives +40/+40 dB with the author
API versus −40/−40 dB under fixed source labels. No real development recording
was scored using per-record best permutation.

Finally, the paper's sources are manually annotated neonatal recordings from
71 chest recordings, with separate real-recording evaluations. HLS-CMDS is a
clinical-manikin dataset released in 2025, not those neonatal folds. Six
correlated, no-added-noise manikin probes cannot reproduce that population,
noise distribution or aggregation. The apparent ~19.48/28.30-dB difference
between the table headings and Phase-D absolute means is **not an established
matched-protocol performance gap**. Our negative SI-SDRi nevertheless remains
a real failure on our chosen development mixtures; comparison limits do not
excuse it.

## 2. Reproduction contract and remaining unknowns

| Item | Verified author contract / artifact | This diagnostic |
| --- | --- | --- |
| Source identity | Author repository revision `d97886b93bd2e71fd019c6b5073bb2dce2854ade` | Same existing artifacts; no replacement weights |
| Checkpoint | `models/model_best.pt`; SHA-256 `abf4f05321d7c0a9da0ee25bfe50f0dbb5736d5f855150787009b4221f947358` | Strict load, 132 state entries, no missing/unexpected keys, all finite |
| Configuration | SHA-256 `b7d82e7fb9cbcbd7382d6eadb69220fba5c7d25cafd5bbfdb83f714ca39d5096`; convolution encoder/decoder512, stride256, features512; mask features256, six conv layers/kernel3, four attention heads/four transformer layers; two individual masks | 8,422,144 parameters; config/model identity matches paper Table I. This alone does not identify the published trained run/fold |
| Mode | Author evaluation calls `eval()` and `no_grad()` | Zero training-mode modules; inference mode; repeated output and direct no-grad output exactly equal on first development input |
| Input/output | Mono 4 kHz; test crop10 s/40,000 samples; `(B,1,T)` → `(B,2,T)` | Batch1, exact output length, finite float32; no resampling |
| Labels | README and target concatenation: channel0 heart, channel1 lung | Retained. Global alternative measured, not adopted; no per-record swapping |
| Mixture | Heart + energy-scaled lung; lung-to-heart levels −10,−5,0,+5,+10 dB. Noise scaled relative to combined heart/lung, then final input unit-peak normalization | NoNoise subset algebra reproduced; bounded levels−10/0/+10 only; no invented neonatal/noise sources |
| Convolutive condition | Independently random three-tap positive L2-normalised filters, same padding, for test sources | Fixed seed42; instantaneous and three-tap cases; coefficients recorded |
| References | Post-filter/crop source waveforms; original loader returns unscaled references, despite gain-scaled mixture | Actual additive contributions retained; target scalar gain is immaterial to SI-SDR. No reference enters inference |
| Preprocessing | Artificial evaluator uses precomputed 4-kHz WAV mixtures; no inference bandpass. HR/BR evaluation has separate resampling/bandpass processing | In-memory float32; no disk re-quantization. Do not import real-recording HR/BR processing into artificial SI-SDR |
| Alignment | Right stride padding trimmed; no target-guided lag correction in artificial evaluator | Same; no scored delay correction or crop optimisation |
| Metric | Released SI-SDR API defaults to no mean subtraction and optimal permutation; author loss options differ | Fixed labels, mean-centred SI-SDR, independently verified; no-mean control also measured |
| Native data/split | `TrainHeart{fold}`, `TrainLung{fold}`, `TestHeart{fold}`, `TestLung{fold}` and noise folders; README exposes fold1–7 | Not supplied by the model repository or our approved local dataset. No authorised native reproduction fixtures/fold manifest identified |
| Training identity | Paper describes8-s crops,40 epochs, noise curriculum; README example says7-s crop and different mask settings | Published training settings are not a verified training log for this checkpoint. No retraining or configuration substitution |

All535 local HLS-CMDS WAVs already byte-matched the official archive in Phase D.
**The released archive inspected for this project contains 4-kHz WAV files.
Earlier acquisition/conversion provenance could not be established.** Its
22,050-Hz descriptive metadata is not evidence of a required local resampling
step. The NeoSSNet artificial loader also uses4 kHz, but different data; equal
sample rate does not establish equal population or reference semantics.

## 3. Concrete defects found, bounded fixes, and metric validation

1. **Model-forward mismatch:** local `TransformerEncoder.forward` used
   out-of-place positional addition, while the author uses in-place addition.
   The two individual mask branches share their input tensor, so the released
   forward gives the second branch accumulated positional encoding. Restored
   the original one-line behavior, without modifying weights or redesigning
   the network. All six local model Python files now byte-match the existing
   author snapshot. This compatibility restoration is inference-specific
   evidence, not a recommendation to repair/retrain the author's architecture.
   Heart scores were identical; mean lung changed only **−13.8446→−13.8051 dB**
   on the six probes. It is real, but **not the cause of the large gap**.
2. **Evaluator edge defects:** mean subtraction mutated float64 caller arrays;
   a zero estimate incorrectly received0 dB from epsilon/epsilon. Evaluation
   now copies inputs, validates finite one-dimensional nonempty arrays, and
   rejects silent estimates/references as undefined rather than counting a
   successful score. Existing float32, non-silent Phase-D scores were not
   caused by these defects. The projection/epsilon formula is otherwise unchanged.

Independent check: orthogonal equal-energy80/511-Hz tones, estimate=`target +
0.2×interference`, yield analytic **13.9794000867 dB**, fast-bss-eval fixed loss
13.9794000867, our evaluator13.9794000862. Scaling by−3 preserves the result;
identical gives113.01 dB; unrelated gives−113.01 dB; silent cases reject
deterministically. On18 actual diagnostic mixtures, maximum disagreement with
the independent fixed-label metric is **1.57e−7 dB**. Maximum difference from
not removing means is **5.42e−6 dB**. Neither explains the performance deficit.

SI-SDRi always subtracts SI-SDR of the **same original mixture against the same
target**. The six input baselines average−0.010505/−0.010503 dB. Symmetric
−5/0/+5-dB energy ratios and near-uncorrelated sources explain the nearly0-dB
mean, hence absolute SI-SDR and SI-SDRi being nearly equal. No baseline or
target substitution was made.

## 4. Bounded development results

Two existing source pairs only: `F_AF_A/F_N_LLA` and `F_ESM_LLSB/F_PR_LLA`.
The original six mixture hashes were reproduced exactly. Twelve additional
**author-protocol manikin surrogates** use the same two pairs × three levels
(−10/0/+10 dB) × instantaneous/convolutive modes. They are correlated development
cases, not twelve independent subjects or native neonatal reproduction.

All values below are **means in dB**, heart and lung kept separate:

| Cases / one fixed global mapping | Heart SI-SDR / SI-SDRi | Lung SI-SDR / SI-SDRi |
| --- | ---: | ---: |
| Historical Phase D6, documented labels, before compatibility fix | −3.48 / −3.47 | −13.84 / −13.83 |
| Same6, restored author forward, documented0H/1L | −3.48 / −3.47 | −13.81 / −13.79 |
| Same6, restored forward, global1H/0L alternative | −5.72 / −5.70 | +0.23 / +0.24 |
| Additional12, author-protocol **manikin surrogate**, documented0H/1L | −4.15 / −4.14 | −15.08 / −15.06 |
| Same12, global1H/0L alternative | −6.85 / −6.84 | −0.19 / −0.18 |
| True native neonatal / published-fold reproduction | **NOT RUN — artifacts unavailable** | **NOT RUN — artifacts unavailable** |

The global swap improves lung at the expense of already-poor heart scores; it
does not qualify a two-source expert. Keep the author's fixed0H/1L convention
for future reproducibility and label the expert **unqualified**, not repaired.
Confidence in the documented convention is high; confidence in target-domain
source applicability is insufficient. No new mapping was selected by example.

Of the12 surrogate cases, instantaneous means were−4.31/−14.63 dB and
convolutive means−4.00/−15.52 dB. The modest protocol extension did not rescue
performance. There were0 shape/non-finite/inference failures in18/18 cases.
CPU median inference ~13.3 ms per10-s input; whole diagnostic ~2.17 s,
peak process RSS531,456 KiB including both metrics/model/FFT allocations. These
are machine-specific warm probes, not production capacity claims. GPU untested.

The earlier Fixed Filter baseline remains the strongest **previously measured
fixed-label baseline on these six cases**, at−2.50 heart/−6.50 lung SI-SDR.
It too has negative SI-SDRi. NMF, VMD and the ensemble were not rerun or tuned;
their Phase-D results remain historical engineering evidence, not new results
under the restored model-forward version.

## 5. Alignment, gain, phase and reconstruction findings

- Development-only correlation search within±512 samples found its maximum
  absolute correlation at **zero lag for both mappings in all18 cases**.
  There is no evidence here for a fixed architectural delay. Dropping512
  samples at each boundary as a diagnostic changes the six documented means
  only to−3.06/−13.56 dB; that crop is not adopted for scoring.
- Correctly normalised Phase-D inputs differ from the author NoNoise mixing
  algebra by at most **7.16e−7 full scale**. Both use unit-peak input. Raw
  development source RMSs are low, but the model receives RMS0.078–0.154
  after peak scaling; source RMS equality at0 dB is intentional. No resampling,
  gain tuning, independent output normalization, padding mismatch or clipping
  correction was introduced. Unnormalised source peaks are below full scale;
  a sample at exactly1 after peak normalization is not evidence of clipping.
- Source correlations are near zero (six:−0.00357 to+0.00140). The0-dB pair
  spectra overlap substantially: heart77.7%/96.6% and lung91.7%/93.5% of energy
  lies below250 Hz. These are descriptive manikin statistics; native statistics
  are unavailable, so no numerical domain-shift effect is inferred from them.
- The lung output has negative signed reference correlation, but SI-SDR permits
  negative global projection gain. Synthetic sign testing confirms invariance;
  sign flipping cannot repair these scores. No per-example polarity selection.
- “Projected” here means magnitude-ratio masks from the **two estimates** applied
  to the **original mixture STFT/phase**, not projection onto ground-truth
  references. It is inference-available. Raw sums have relative L2 reconstruction
  error0.918–1.447 on the six cases; their architecture does not constrain the
  two waveforms' sum or arbitrary SI-SDR-trained gains/signs. Mask projection
  enforces the sum to within5.97e−8 full scale and produces−2.58/−12.88 dB
  after the compatibility restoration. Additivity is not proof of correct
  source assignment or better physiological reconstruction.

## 6. Reproduction ladder and ranked explanation

| Level | Result | Interpretation |
| --- | --- | --- |
| 1 Metric | PASS after bounded edge fixes | Independent fixed-label agreement; Phase-D numerical metric not responsible |
| 2 Model/checkpoint | PASS mechanically after forward restoration; training-run identity AMBIGUOUS | Strict keys,8.42M parameters, eval/inference, repeatability and author-code parity; published trained fold not established |
| 3 Channel mapping | Documented convention PASS; target applicability FAIL | Neither one global mapping provides useful separation of both sources |
| 4 Preprocessing | PASS for available NoNoise algebra |4k/10s/unit peak; no fixed lag; exact precomputed WAV/native lineage unavailable |
| 5 Mixing | PASS for bounded surrogate subset | Ratios/FIR rule reproduced, but only manikin references and no added native noises |
| 6 Native/paper evaluation | BLOCKED / NOT REPRODUCED | No authorised neonatal reference folds, raw result CSVs or checkpoint manifest |
| 7 Current target development | FAIL quality qualification |18 finite executions, negative two-source improvement; no final-set inspection |

Ranked by evidence, not by guessed percentage of lost dB:

1. **Established comparison mismatch:** table-heading versus notebook improvement
   aggregation, PIT-capable SI-SDR versus fixed labels, and different source/noise
   populations. This prevents treating16.00/14.46 as an absolute target for our probe.
2. **Established target failure:** documented labels do not separate these
   pathological/normal manikin pairs usefully. A globally swapped convention is
   not a defensible universal remedy.
3. **Plausible, not demonstrated causal domain shift:** neonatal annotated sources
   versus clinical-manikin AF/murmur/normal/pleural-rub sources; hardware, source
   construction and physiology differ. Native strong performance is not established
   in our environment, so this does **not** meet the owner's fine-tuning gate.
4. **Unresolved artifact/experiment correspondence:** the released parameterization
   matches, but which trained fold/curriculum/run produced these weights and whether
   it is the notebook's `all1` are not recorded in a public manifest.
5. **Ruled out as a large explanation on these cases:** local metric numerics,
   mean removal, fixed delay, peak normalization, training mode, random uninitialised
   state. The positional-encoding fix changes the mean by only0.04 dB in lung.

**Fine-tuning is NOT recommended yet.** Gate A (strong native-like reproduction)
has not passed; Gate B (measured deterioration under domain transfer) therefore
cannot be established. No optimizer/loss/epoch plan is chosen prematurely. Do
not claim outcome A or C: neither native success nor faithful native failure
has been demonstrated. Outcome D concerns admission to **our target ensemble**.

## 7. Official alternatives, rights, and exact next task

The original repository currently exposes one branch, no tags/releases, and one
checkpoint. A bounded check of the same author's
[SeparationApplication](https://github.com/yangyipoh/SeparationApplication/tree/0aa163450407b95110b702bb1764f760c0dd88a5)
found a later artifact (26 November2023), blob
`1e4dfd30abaf759349c4ac14ef060a81647fac5f`,36,405,953 bytes. Its
[`model.yaml`](https://github.com/yangyipoh/SeparationApplication/blob/0aa163450407b95110b702bb1764f760c0dd88a5/models/masknet/model.yaml)
uses kernel129, shared masks, eight transformer layers and stochastic output:
**not a corrected drop-in version of our kernel512 individual-mask checkpoint**.
It was not downloaded, substituted or benchmarked. No evidence establishes that
it generalises better. Ask its author which artifact is intended for reproduction.

Neither inspected top-level repository declares a code/checkpoint license.
Some individual source files carry Apache notices for upstream components;
that is not a blanket grant for the complete project or weights. Paper licensing
does not settle code/weight rights. Previously tracked artifacts were not newly
redistributed; no new third-party code/weights/dataset is included in this commit.
Rights remain **PENDING RIGHTS** before public deployment/distribution.

**Next task for Luna:** do not rerun the18 cases or start training. Help the owner
send the prepared request below if authorised, then record the author's response,
rights, artifact hash/config/run identity and a small legitimately accessible native
development fixture set with expected fixed-label outputs. With those artifacts,
run **one** bounded native comparison using the fixed and explicitly identified
author metric contracts separately. Keep final StethoFuse families sealed. Only
if native performance is strong and target transfer is poor should a separately
approved, source-family-isolated fine-tuning plan be designed. If artifacts/rights
cannot be obtained, return that concrete blocker for an expert-membership decision;
do not silently adopt the later application model or a replacement architecture.

### Prepared author request — NOT SENT

To the maintainer listed in the original README: `Yang.Poh@monash.edu`.

Subject: NeoSSNet checkpoint reproduction and academic reuse clarification

We are evaluating cardiopulmonary separation for the application-based StethoFuse
FYP, without clinical claims. Could you clarify:

1. Does released `model_best.pt` (SHA-256 `abf4f053…f947358`,8,422,144 parameters)
   correspond to Table VII's `all1` baseline? Which fold, training configuration,
   dependencies and checkpoint should be used for reproduction? Is the later
   SeparationApplication checkpoint recommended instead?
2. The results notebook's displayed16.00/14.46 values use the average of three
   category medians from SI-SDR-improvement columns. Is that the intended table
   interpretation? Is the optimal permutation in `fast_bss_eval.si_sdr` intentional?
3. Are small de-identified/licensed native development mixtures, their reference
   sources, generation/fold manifest and expected results available through an
   approved access process? We are not requesting identifiable patient data.
4. What licenses/permissions cover the complete code and released weights for
   academic inference, modification/fine-tuning, public demonstration and
   redistribution? What attribution/restrictions apply?

No email was sent and no new external permission was assumed.

## 8. Reproduction commands and checkpoint evidence

Use the existing ignored Phase-D environment, not the production environment:

```sh
uv pip install --python .local/ensemble/venv/bin/python fast-bss-eval==0.1.4
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .local/ensemble/venv/bin/python scripts/diagnose_neossnet_reproduction.py
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .local/ensemble/venv/bin/python -m pytest -q tests/test_ensemble_v1.py tests/test_neossnet_reproduction.py tests/test_baseline_strategies.py
```

The runner requires the existing ignored author snapshot and Phase-D manifest,
verifies development-only source hashes, and writes no source audio. Evidence:
`.local/ensemble/reproduction/diagnosis.json`, SHA-256
`cdbae401ae223b37fbab44b6073ca4b3ed1a2d97b728aba120e3ef1bca74caee` for this run.
It records script/manifest hashes, state/model parity, per-case statistics/scores,
global mapping alternatives, FIR coefficients and timings. `code_head` records
the baseline plus this sprint's then-uncommitted changes; the script hash pins
the executed runner. Rerun timing and report hashes will naturally differ.

Two new regression functions only: float64 metric immutability/undefined silence;
released shared positional-encoding semantics. Focused batch **8 passed**.
One nearby ML regression batch **15 passed** (ensemble, reproduction, baselines); no historical
application suite, training, full-dataset benchmark, PIT data evaluation, ensemble
weight search or production access was performed.
