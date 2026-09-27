# ADR E01 — StethoFuse ensemble v1

**28 September 2026, superseding next step:** our own production-capable expert
is now designed in [ADR T01](STETHOFUSE_MODEL_TRAINING_PLAN.md): compact
fixed-label Conv-TasNet, scratch training, licensed library/data, locked test
families. Not yet trained/evaluated. NeoSSNet remains a research comparator;
the50/50 fusion below stays unchanged/frozen, not qualified or integrated.
Do not resume author email or Phase E in place of the new T0–T4 handoff.

27 September 2026. **Original design decision. Phase A–D is now implemented and
tested offline on a small development qualification set; not deployed or finally
evaluated.** See [offline qualification evidence](ENSEMBLE_OFFLINE_QUALIFICATION.md)
for the later, superseding status and measured limitations.
The subsequent [reproduction diagnosis](NEOSSNET_REPRODUCTION_DIAGNOSIS.md)
fails target-domain NeoSSNet expert qualification. Revisit that membership gate
before proceeding; the50/50 formula is unchanged, not vindicated or tuned.
Baseline: `319e0e39cb2dff95897808ae16728cb60066efd6`.
See [source audit](ENSEMBLE_SOURCE_AUDIT.md) and [bounded Luna plan](ENSEMBLE_LUNA_HANDOFF.md).
This is an internal separation subsystem, not a clinical diagnostic system or
an application actor. Production remains unchanged; ordinary users get one
ensemble operation, never an algorithm selector. Federated Learning is excluded.

## 1. Decision

**SELECTED ENSEMBLE: fixed, equal-weight complementary time-frequency magnitude-mask
fusion (`stethofuse-tfmask-v1`).** Two heterogeneous experts contribute to every
successful non-silent window: released NeoSSNet + local unsupervised NMF.
Weights are exactly `(0.5, 0.5)`, frozen before evaluation. No gate training,
stacker, checkpoint fine-tuning, reference-dependent selection or test-set tuning.
This is a genuine combination, not a menu or an alias for a single strategy.

**Membership is conditional:** NeoSSNet must pass dependency/load/shape/source-order
qualification and code/weights permission review; NMF must pass corrected-STFT
qualification. If either fails, do not silently swap in another method or call a
single output an ensemble. Retain `ensemble_unavailable` until both qualify.
Fixed Filter and qualified VMD remain internal comparators, not v1 members.
NMCF, DAE–NMF–VMD and the missing fine-tuned checkpoint are not admitted.

Why: existing neural and factorisation outputs offer different inductive biases;
neither diversity nor improvement is yet demonstrated. Pooling bounded masks on
the input STFT avoids destructive cross-expert phase/polarity interference and
independent WAV gain artifacts. Equal weights deliberately avoid learning from
unverified/small calibration splits. The design is interpretable, versionable,
CPU-capable in principle, and only needs two existing methods. It does not promise
better quality, noise removal, faithful morphology, or generalisation to patients.

| Option | Relevant advantage | Reason not selected for v1 / decision |
| --- | --- | --- |
| Static waveform averaging | Cheapest combiner | Current outputs have different gain/clipping/phase; even aligned signals can cancel. Keep native outputs as comparators, do not average saved WAVs. |
| Complementary TF mask fusion | Common phase, bounded weights, two-source reconstruction | **Selected.** Loses expert phase benefits; shared mixture phase and residual noise are explicit limitations. |
| Segment-wise winner selection | Could exploit changing conditions | No validated reference-free winner score; switching risks audible seams and hidden oracle use. |
| Learned mixture-of-experts gate | Input-dependent weights | Insufficient verified independent training/validation data; extra model, calibration and deployment burden. |
| Stacking / learned waveform combiner | Could learn scale/phase corrections | Needs leakage-safe out-of-fold expert predictions and substantially more labelled data; excessive scope. |
| Reliability/confidence weights | Could downweight weak experts | Energy/entropy/reconstruction consistency are not validated separation-quality confidence. Use validity checks, not invented confidence. |

A validation-tuned scalar was considered but rejected for this version because
the existing split/reference provenance cannot support even modest tuning safely.
Future learned weights require a new version and a fresh locked evaluation plan.

## 2. Canonical signal and adapter contract

Input is the immutable uploaded mixed recording; retain its original bytes/hash.
Canonical analysis: mono, 4,000 Hz, finite float32 samples in digital full-scale
units, shape `(N,)`, heart/lung both `(N,)`. 4 kHz is a **StethoFuse analysis
choice**. The HLS-CMDS README states 22,050 Hz, but the official released ZIPs
and all byte-identical local WAVs actually contain 4-kHz PCM; pre-release
acquisition/conversion lineage is unknown. Information above 2 kHz is unavailable;
never present 4-kHz output as full-band recovery.

- Decode permitted integer PCM WAV 8/16/24/32-bit explicitly; reject unsupported
  encodings rather than reinterpreting float bytes. The existing intake validator
  remains authoritative. For stereo use arithmetic mean; record original channels
  and detect cancellation/silence after downmix. Never treat channels as sources.
- For non-4-kHz input, use pinned `scipy.signal.resample_poly`, ratio reduced by
  gcd, `window=('kaiser', 5.0)`, `padtype='constant'`; length is
  `ceil(original_N * 4000 / original_rate)`. No linear-interpolation downsampling.
  Already-4-kHz data is not resampled. No additional bandpass/DC removal in v1;
  evaluation alone mean-centres estimates and references.
- Compute one recording peak `g=max(abs(x))`; for active input experts receive
  `u=x/g`. Invert that **same** gain on both raw outputs before storage/comparison.
  Reject empty/global RMS below `1e-6` full scale. Individual silent windows are
  copied as two zeros with a provenance flag; do not run unstable normalisation.
- Process 40,000-sample (10 s) windows, hop 32,000 (8 s); zero-pad the final short
  window and trim only that known padding. This is a StethoFuse windowing adaptation,
  not an exact reproduction claim. Paper training used 8-s crops; author inference
  examples use 10 s. Overlap-add final estimates with complementary raised-cosine
  8,000-sample fades; first/last edges have nonzero coverage; divide by accumulated
  weights and trim to N. Apply identical windowing to adapted comparators.
- Proposed initial processing cap: 120 s, distinct from the existing 1,800-s upload
  cap. Reject longer processing requests explicitly, keep the original, never
  silently truncate. Freeze the cap after Phase A resource measurement; it is an
  operational limit, not measured throughput. This does not change upload policy.

Reuse `AudioData`, `StrategyContext`, `SeparatedWaveforms` and the outer
`SeparationAlgorithmResult` rather than creating a second model registry.
Adapters return raw labelled arrays + immutable expert/config/hash metadata.
NeoSSNet must expose inference arrays **before** its current WAV clamp/peak-cap;
NMF must bypass `BaseSeparationStrategy.postprocess/save_outputs` for fusion.
Legacy adapters remain intact for historical reproducibility.

| Compatibility dimension | Required rule |
| --- | --- |
| Rate / channel / shape | Exactly 4 kHz mono, identical original time grid and window length; model stride padding is explicitly removed by its adapter. Unexpected mismatch fails, not arbitrary truncate/pad. |
| Delay / alignment | Expected zero physical offset. Qualify on controlled synthetic envelopes and source-labelled development fixtures; only a fixed documented architecture delay can be compensated. No per-record/reference-optimised shift. |
| Polarity / phase | No polarity flipping against reference. Magnitude masks ignore absolute polarity; reconstruct both sources from original mixture phase. This does not repair time misalignment. |
| Scale | Single input gain; same inverse gain for both sources. No per-source peak normalisation, fitted gains against references, or clipping before fusion. |
| Labels / permutation | NeoSSNet channel 0=heart, 1=lung; NMF grouping remains centroid <=220 Hz vs >220 Hz with recorded half-order fallback. No test-reference permutation/oracle. The heuristic may misassign overlapping spectra. |
| Invalid / silence | Reject NaN/Inf, invalid rank, wrong sample rate/length and two silent outputs on an active window. A single near-silent source is a flagged possible result, not automatic failure. No `nan_to_num` concealment. |

## 3. Exact fusion

Use one analysis/synthesis convention for all expert outputs and mixture:
1024-point real STFT, hop 256, **periodic Hann**, 512 zero samples on the left
and at least 512 on the right, extend right padding to a complete hop grid.
Inverse uses window-squared overlap-add normalisation and removes explicit padding.
Require round-trip max absolute error <=`1e-5` on unit-range boundary/impulse/tone
fixtures. Do not reuse the legacy unpadded STFT unchanged: its first sample is lost.

For each active window and expert e:

```
X = STFT(u)
Ae_h = abs(STFT(raw_expert_heart))
Ae_l = abs(STFT(raw_expert_lung))
De = Ae_h + Ae_l
epsilon_e = max(1e-12, 1e-8 * max(De))
Me_h = Ae_h / De where De > epsilon_e; otherwise 0.5
M_h = 0.5 * Mneoss_h + 0.5 * Mnmf_h
M_l = 1 - M_h
h = ISTFT(M_h * X)
l = ISTFT(M_l * X)
```

Use float64 for STFT arithmetic/normalisation and float32 for model input and
canonical output. Verify finite masks in [0,1]; neutral bins are explicit, not
confidence weighting. Restore input gain, then window overlap-add. The linear
reconstruction gives `h+l≈x` to numerical tolerance, **not** proof of correct
separation. This is magnitude-ratio pooling, not squared-energy Wiener estimation.
Do not mix latent NeoSSNet masks directly with FFT masks: they inhabit different bases.

Evaluate float estimates before export. Playback/download PCM16 uses one shared
attenuation `q=min(1,0.95/max(abs(h),abs(l)))`, applied to both files; record q,
quantisation format and hashes. Never independently normalise the two files.
Offline experiments may retain float arrays in ignored research output; production
need not add an unprotected float-file route. Account for q when validating exported
reconstruction (quantisation tolerance, not exact bitwise equality).

Mixture consistency is motivated by [Wisdom et al. (2019)](https://doi.org/10.1109/ICASSP.2019.8682783),
but this is a simple fixed-mask StethoFuse adaptation, not that paper's trained
projection network or a transfer of its speech results. With only two outputs,
all input noise is allocated to heart/lung. No clean-denoising claim is justified.

## 4. Failure, compute and reproducibility

- Missing checkpoint/dependency/hash or fewer than two qualified experts: engine
  not ready, submit returns `503 ensemble_unavailable`, no phantom queued job.
- Expert exception, invalid output, deadline or OOM: fail the **whole job**, no
  public partial result; retain safe error/provenance, delete only its staging files.
  No automatic Fixed Filter substitution or silent renormalisation to one expert.
- CPU is the reference/default device. GPU is optional and must pass parity/resource
  qualification. If GPU is absent before a run, explicitly select CPU and record it.
  If a running GPU job OOMs, fail; a later explicit retry is a new run, not a hidden
  within-run algorithm/device change. Single concurrent ML job initially.
- One small worker process owns model execution; a supervisor enforces per-job
  deadline and can terminate/restart a stuck process. No unbounded in-HTTP inference.
  Provisional 300-s hard deadline must be checked against the processing cap before
  release; queued age is separate from execution time. No measured SLA yet.
- `eval()`/`inference_mode()`, NumPy seed42, Torch seed42, deterministic algorithms
  where supported, fixed dependency lock, bounded BLAS/Torch threads, batch size1.
  Exact CPU/GPU bitwise equality is not promised. Record hardware/library versions.
- Local checkpoint is 34,973,929 bytes; runtime RSS/activations are **not** 35 MB.
  No Torch/VMD inference or GPU measurement was possible in the inspected local
  lightweight environment. Do not expand the 1-GB API container to run ML blindly.
  Measure cold/warm time, peak RSS/VRAM and real-time factor at 10/30/120 s before
  choosing worker resource limits. Keep API healthy during a single-worker stress check.
  Two PCM16 outputs use about 16,000 bytes/s plus headers (1.92 MB at 120 s).

Each run stores a versioned JSON provenance record, attached to its existing job/result:

```
schema_version, ensemble_version, weights=[0.5,0.5], weights_version,
input_recording_id, input_sha256, original_audio_attributes,
canonical_sample_rate, canonical_length, preprocessing_version,
input_gain, stft_parameters, chunk_and_padding_parameters,
experts[{id, code_commit, upstream_commit, config_sha256, checkpoint_sha256,
         adapter_version, seed, status, elapsed_ms, warnings}],
code_commit, environment_lock_sha256, device, library_versions,
started_at_utc, completed_at_utc, runtime_ms, export_shared_gain,
status, safe_failure_code, fallback_events=[],
outputs[{resource_id, component, sha256, bytes, format}]
```

Pin/check hashes at worker startup, never download models per request. Provenance
contains no tokens, Firebase profiles or public absolute storage paths. Source-audit
records carry literature/licenses; normal users only need method/version/status.

## 5. Existing application integration — implementation contract only

`app/m1/api.py` already has owner-only `POST /api/recordings/{recording_id}/jobs`,
currently returning503. Preserve its authentication/`store.require_owner` boundary.
Use current `m1_jobs`, `m1_results`, `m1_result_files`, `m1_files`, `af_resources`
and `af_recordings` in the M1 database. Do **not** call legacy separation-service
database code or reactivate disabled legacy routes/static media.

Proposed additive, versioned migration (not run here): extend `m1_jobs` with
`started_at`, `heartbeat_at`, `worker_id`, `attempt`, `ensemble_version`,
`provenance_json`, optional client `request_key`; unique `(requester_id, request_key)`
for supplied keys. Version the M1 migrator; current `m1_meta` enforces version=1
and exact-table checks, so adding a parallel queue table ad hoc is unsafe.

1. Check active actor, owner, engine readiness, processing limits and queue capacity;
   atomically create `queued` job, return202 + existing job DTO/Location. No method
   field. Repeated request key returns its existing job, not another charge/run.
2. One dedicated worker on the **existing isolated StethoFuse network**, no exposed
   port, polls SQLite and claims oldest queued job with a short conditional
   transaction. Recheck owner/account/recording state, then commit `running` before
   inference. Do not hold a database transaction during ML. No Redis/Celery required.
3. Write both output files in job-specific private staging; validate, hash and
   atomically rename into final private paths. In one DB transaction register
   `m1_results` + `af_resources`/`m1_files`/`m1_result_files`, provenance and
   `succeeded`. Result is visible only after complete publication. Startup reconciles
   only abandoned job staging/orphans; never deletes existing originals.
4. Stale `running` job after process loss becomes `failed`/`worker_interrupted`;
   explicit retry creates a new ID. No invisible success, duplicated publication,
   invented progress percentage or automatic retry loop. Worker heartbeat and
   supervisor timeout protect against a permanently stuck running state.
5. Existing `GET /api/jobs[/id]` stays owner-only. Existing results/media/download
   routes re-check owner/explicit resource grants on every request. Register result
   metadata, heart and lung as separate resources: a grant for original audio does
   **not** auto-grant new derived files, and a metadata grant does not grant audio.
   Analyst review remains attached to an explicitly granted existing resource.
6. No reference metrics for ordinary uploads: provider has no ground truth. Return
   `metrics unavailable: no_reference`, never a fabricated accuracy/confidence score.

Worker mounts private/data paths with existing restricted IDs and a read-only model
directory; no Firebase/Cloudflare/B2 credential is needed by the ML worker. Future
Compose worker changes require separate implementation/deployment review. Backend
authorisation, backup, owl and other roles remain unchanged. Frontend later reuses
its current request/job/result workflow; no redesign.

## 6. Evaluation and leakage contract

**Primary quantitative task:** controlled digital heart+lung mixtures formed from
approved, provenance-checked isolated manikin sources. **Secondary realism task:**
the recorded HLS-CMDS mixtures, without samplewise source scores until a defensible
synchronised-reference contract is established. Three inspected recorded triples
are not same-time additive targets; a ref-oracle lag search is not a general repair.

Before any evaluation, produce a hashed manifest: source bytes/original release,
transform history, source identity/family, pair, gains, canonical length, split,
and all duplicated/derived relationships. Subsequent Phase-A verification found
all 535 local WAVs byte-identical to the official released 4-kHz ZIP members;
the README's 22,050-Hz statement is inconsistent with the downloadable release.
No local conversion is needed for these files. Pre-release lineage remains unknown;
never overwrite historical local data. The small development-only manifest is
documented in [offline qualification](ENSEMBLE_OFFLINE_QUALIFICATION.md).

- Reserve development, validation and final test **by source family before mixing,
  cropping or augmentation**. No subject IDs exist in current manikin metadata;
  do not invent patient-level separation. Conservatively group all occurrences of
  each heart sound type and each lung sound type across sites/gender/modes unless
  finer manufacturer-template independence can be evidenced. Merge discovered
  exact/near duplicates across labels. Keep the three probe triples and any related
  family out of a claimed untouched test set.
- Default group allocation is seeded60/20/20 development/validation/test within each
  source family class (heart vs lung), documented with exact resulting counts.
  The few sound types can make test diversity very small; do not weaken grouping
  just to enlarge n. If too few independent groups remain, report descriptive
  engineering results only and flag broader generalisation evidence as blocked.
- Construct mixtures **within** a split only. Use deterministic disjoint source
  pairs where possible, at most20 base pairs per split, three lung-to-heart RMS
  power ratios `-5,0,+5 dB`. Scale lung by
  `10^(ratio/20)*RMS(heart)/RMS(lung)`, then apply one shared anti-clipping gain to
  mixture **and both references**. Fixed offsets/crops/seeds are in the manifest;
  targets are exactly the signals actually summed. Do not generate test mixtures
  repeatedly while tuning. No new dataset/training/download occurred in this sprint.
- Released NeoSSNet stays frozen; absent fine-tuned model is excluded because its
  split/history cannot be certified. NMF fits each input without reference labels.
  Validation qualifies adapters/limits; weights stay0.5. After a failed final test,
  changed parameters require a new declared version/evaluation, not rewritten history.

Comparisons: unchanged unprocessed mixture; adapted raw NeoSSNet; adapted raw NMF;
each expert's **single projected mask output**; selected 50/50 ensemble. Fixed Filter
is a useful additional baseline. VMD only after runnable strict no-fallback
qualification; label its precise fast/quality bandwidth/settings. Do not count
fixed-filter fallback as a VMD result. Native-author runs with different windows
are secondary, clearly labelled, not the primary matched-pipeline comparison.

All primary methods use the same manifest, canonical input/windows, fixed source
labels, sample positions and evaluation code. No reference-based delay/gain fitting,
per-method truncation, best-of-source permutation or cherry-picked successful subset.

Primary per-source metric: mean-centred **SI-SDR** and **SI-SDR improvement over the
same unprocessed mixture**, following [Le Roux et al. (2019)](https://doi.org/10.1109/ICASSP.2019.8683855).
Use float64 projection, one documented numerical floor, mark silent/undefined
references explicitly rather than making EPS look like a score. Secondary: mean/
median/IQR of heart and lung separately; paired per-record differences; worst cases;
failure counts; runtime/RTF, peak memory; reconstruction residual as a constraint
check, not separation accuracy. The legacy `snr_improvement` is a change in simple
scale-dependent reconstruction ratio, **not** an independently established SNR.
PESQ/STOI, diagnosis, heart-rate or clinical outcomes are not v1 metrics.

Aggregate the three ratios per base pair before uncertainty calculations; repeated
sources are not independent samples. Primary comparison is ensemble minus each
constituent (and best validation-selected single comparator), for heart/lung
separately. Define independent blocks by joining all pairs that share either
heart or lung source family; do not bootstrap overlapping pairs independently.
With at least10 such blocks, report paired cluster-bootstrap95% intervals
(seed42,2,000 resamples) on block-aggregated deltas, preserving both sources,
conditions and methods together in each draw. This is a conservative reporting
rule, not a guarantee of statistical power. Otherwise show paired descriptive
distributions only; the current manikin grouping may yield very few blocks.
List every failed run; scored pairs and their denominators must be explicit,
and a successful-subset advantage is not overall superiority. No battery of
p-values. A superiority claim requires positive held-out improvement for **both**
heart and lung against the stated comparator, uncertainty and failure-rate reporting,
and clear dataset scope. If one source worsens, say so; a macro-average cannot hide it.

## 7. Explicit limits / release gates

No full expert loadability, licensed redistribution, domain generalisation, quality
gain, latency SLA, real-time processing, patient safety, diagnosis or clinical
benefit is established. The fixed-weight ensemble may be worse. NeoSSNet can create
artifacts; spectral centroid labels can confuse murmurs/lung sounds; mixture phase
cannot recover unavailable phase or remove all noise. Supervisor discussion must
cover the FYP2 ensemble refinement, controlled-mixture evaluation and limited
manikin scope; an owner design agreement is not academic approval.

Luna must qualify **two** experts, data lineage, signal contract and worker resource
budget before enabling execution. Keep current production unavailable until a
later explicitly approved release. This ADR is the selected design, not permission
to deploy or start another milestone automatically.
