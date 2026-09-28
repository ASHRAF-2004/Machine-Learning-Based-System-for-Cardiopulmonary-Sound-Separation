# HLS-CMDS native-triplet forensic audit

Status: **ROLE A QUALIFIED SUBSET; PILOT NOT YET EXECUTED.** T9 SEALED. NOT DEPLOYED. This is correspondence/data evidence, not separator performance. The existing v1/v2 separator specifications and external-data negative-transfer evidence remain intact.

## 1. Decision and scope

Select **ROLE A: direct waveform supervision**, restricted to 26 nonduplicate, non-test, common-gain additive release triplets. Their targets are `g H` and `g L`, input is the original released `M`, and one positive common gain is calibrated offline. No delay, FIR, time warp, reference-residual redistribution, or inference-time reference is required. This is **not** permission to train on the other 73 assessed nonadditive triplets or the 45 excluded/unassessed triplets.

The decisive finding is heterogeneous release structure. All 27 eligible rows with numerical IDs above 110 have near-exact same-time shared-gain closure on untouched temporal flanks; none of the earlier 73 does. One full duplicate (`M0126`, retain `M0111`) leaves 26. An experiment on these files tests additional release-source examples and recorded/released level relationships. It must not claim to have learned previously unmodeled real acoustic mixing: digital normalized addition is consistent with their measured structure, but its provenance is undocumented.

## 2. Reproducible evidence and release inventory

Primary-source acquisition review: [HLS_NATIVE_SOURCE_EVIDENCE.md](HLS_NATIVE_SOURCE_EVIDENCE.md). Machine-readable evidence:

- Registry/mapping: `research/manifests/hls_native_triplets_v1.json`; SHA-256 `56f958996682fd61e598efc07c1084c8d41a2d5fdf8c453802dc27d8109fb0ae`.
- Conservative exclusions: `research/manifests/hls_native_triplet_exclusions_v1.json`.
- Predeclared signal analysis: `research/configs/hls_native_forensics_v1.json`.
- Waveform correspondence: `research/evidence/hls_native_correspondence_v1.json`.
- PSD/counterfactual/stationarity results: `research/evidence/hls_native_spectra_v1.json`.
- Replay, duplication and domain descriptors: `research/evidence/hls_native_fingerprints_v1.json`.
- Qualified selection and pilot: `research/manifests/hls_native_qualified_v1.json` and `research/configs/hls_native_pilot_v1.json` (authoritative execution settings; no treatment result yet).

The local ZIP central directories and extracted filenames agree: 50 standalone heart WAVs, 50 standalone lung WAVs, and 435 Mix WAVs = 145 numbered `M/H/L` triplets, **535 total WAVs**. Resource-fork entries are not recordings. The actual local inventory is the expanded 535-file release, matching the author repository's Dataset.v2; its official source is [Zenodo record 15376628](https://zenodo.org/records/15376628). Repository v1 had 110 mixtures and 210 total files. Zenodo's displayed Version v1 and Mendeley DOI `.3` are distribution-specific labels, not interchangeable with GitHub Dataset.v2.

For every eligible member, local bytes were checked against the archive, SHA-256 recorded, and header verified: **4,000 Hz, mono PCM16, 60,000 samples, 15 s**. Counts/paths for excluded members came from metadata/central directory only; their audio bytes were not opened. Exact IDs, names, family labels, site labels, hashes and fold eligibility are in the registry; missing subject/playback IDs and per-file filter modes remain null.

## 3. Acquisition evidence and unknowns

The [final original paper](https://doi.org/10.1109/IEEEDATA.2025.3566012), pp. 136–140, describes CAE Juno/Maestro repeated prerecorded sounds and Littmann CORE/Eko acquisition. Both sources are enabled for mixture recording; isolated references are recorded separately without changing stethoscope position. Replay is the authors' reason for correspondence, not evidence of simultaneous three-channel sampling. The reported roles are heart/Bell, lung/Diaphragm, mixture/Midrange; cardiac/ventilation synchronization concerns simulator playback, not WAV sample-zero alignment. The paper mentions post-recording bandpass filtering but does not disclose coefficients. Its 22,050 Hz statement does not match released 4 kHz headers; no undocumented resampling history is invented.

Per-triplet acquisition order, recording gaps, playback phase reset, filter state, gain settings, AGC/compression and noise-reduction state are **unknown**. The paper reports fixed placement, but the Mix CSV is a row-level site/manikin-gender annotation: byte-identical references sometimes carry different standalone site/gender metadata. Do not assign those labels as independently verified per-reference acquisition facts.

The [official Littmann CORE documentation](https://www.littmann.com/en-us/home/core-digital-stethoscope/) says volume controls affect earpiece loudness, not Eko recording volume; contact pressure changes frequency emphasis and ANC is switchable. Current Wide/Cardiac/Pulmonary app labels do not identify historical Bell/Diaphragm/Midrange coefficients. The official second-generation manual specifies 4 kHz A/D and 20–2,000 Hz response. No manufacturer claim establishes the recordings' actual gain/AGC state. Thinklabs is not the reported device.

Targeted release-history review found no documented digital-addition procedure for IDs 111–145. The chronology (110 then 145) and measured affine-additive subgroup are facts; digital generation is an **inference**, not an accusation or verified author-protocol fact. The eight excluded IDs in the late range were not inspected.

## 4. Leakage protection and independent information

The frozen non-test allowlist has **45 heart and 41 lung recordings**. Native eligibility requires **both** constituent families to be permitted. T9-associated families are excluded conservatively using frozen metadata; no test fingerprint, descriptor or audio decoding was used. This leaves **100 eligible triplets/300 files**, covering eight heart families, five lung families and all 40 permitted family pairs. Forty-five triplets/135 files remain unassessed and sealed.

| Source family | Standalone non-test files | Eligible native triplets containing family |
|---|---:|---:|
| Heart: Atrial Fibrillation | 4 | 13 |
| Heart: Early Systolic Murmur | 6 | 11 |
| Heart: Late Diastolic Murmur | 6 | 10 |
| Heart: Late Systolic Murmur | 5 | 14 |
| Heart: Mid Systolic Murmur | 7 | 13 |
| Heart: Normal | 9 | 12 |
| Heart: S3 | 5 | 13 |
| Heart: Tachycardia | 3 | 14 |
| Lung: Fine Crackles | 5 | 17 |
| Lung: Normal | 12 | 23 |
| Lung: Pleural Rub | 9 | 21 |
| Lung: Rhonchi | 8 | 17 |
| Lung: Wheezing | 7 | 22 |

**Zero new family categories and zero new pair categories** beyond the permitted standalone Cartesian pool were found. These are manikin examples, not 100 independent patients. The 26 retained additive triplets span 19 family pairs and contain 23 unique heart and 22 unique lung file hashes. Thirteen heart and thirteen lung hashes are absent from the standalone 86: **26 new reference files**, not 26 proven new physiological sources.

The wider 100-triplet pool contains 44 heart-reference rows and 43 lung-reference rows that are exact standalone copies (28 unique standalone heart IDs and 24 lung IDs). Sixteen triplets reuse both standalone references exactly. Native heart references have 66 unique hashes and lung references 56; one hash appears across source classes, so the combined count is 121, not 122. Specifically, `M0031` lung and `M0055` lung (Fine Crackles) are byte-identical to `M0108` heart (Late Systolic Murmur), SHA-256 `342460fdffa6f463168e1030380076eedc429c974548aaf0309aec26721a4a69`. This is an explicit released source-label contradiction, not physiological cross-source evidence. All three are among the unqualified earlier 73 and none enters training. No label is silently corrected. Exact mixture/reference duplication identifies `M0111/M0126` as a full duplicate.

Bounded center-segment/lag fingerprinting found no additional nonexact reference with absolute same-family correlation >=0.95: the nonexact maxima were approximately 0.591 heart and 0.787 lung. Low correlation does not prove independence: filtered, differently phased, outside-window or time-varied playback remains possible. High normalized PSD similarity likewise does not establish identity or purity.

Eleven heart-hash and fourteen lung-hash clusters cross the correspondence fit/holdout pair split. Therefore that split tests **unseen combinations**, not independent-reference or unseen-family transfer. Model evaluation instead uses the existing five grouped-family folds; a native training row is allowed only when both families are in that fold's training pool. Qualified triplet counts are f1=17, f2=22, f3=16, f4=15, f5=13. A renamed/filtered replay cannot bypass this family guard.

## 5. Waveform additivity, alignment and drift

The predeclared procedure fits on 6–9 s, searches independent source lags within ±4 s without circular wrap, and tests untouched valid temporal support. The same-time shared-gain model is the nested restriction of the declared two-gain diagnostic:

`g = <M, H+L> / ||H+L||²` on 6–9 s; `H_target=gH`, `L_target=gL`.

It was added after heterogeneous two-gain closure was observed, before any neural treatment, and checked separately on the complete 0–6 s and 9–15 s flanks. This analysis revision is recorded; the original waveform label tolerance (residual RMS <=0.10 times weaker corrected-source RMS) was not relaxed. It is a reference-assisted **offline label-preparation check**, never separator performance or an inference rule.

| Descriptive median, not IID estimate | Earlier 73 eligible IDs | Later 27 eligible IDs |
|---|---:|---:|
| Raw `M-(H+L)` RMS / mixture RMS | 1.706 | 0.944 |
| Raw sum vs mixture SI-SDR | −42.683 dB | 75.636 dB |
| Raw sum/mixture correlation | 0.00273 | 0.999999986 |
| Aligned/two-gain held-out residual / mixture RMS | 1.036 | 0.000167 |
| Shared-gain same-time held-out residual / mixture RMS | 1.00024 | 0.000166 |
| Shared-gain same-time held-out residual / weaker source RMS | 105.374 | 0.000451 |

The late raw residual is predominantly an amplitude mismatch: SI-SDR is scale-invariant and already detects almost identical morphology. Shared gains range **3.484–135.389**, median 17.711. Across all 54 untouched late flanks, residual/weaker-source RMS ranges **0.000118–0.004798**, far below the 0.10 label tolerance. Retaining the no-shift common-gain identity is more constrained and better supported than a flexible correction.

Late reference lung/heart RMS levels span **−21.343 to +13.262 dB**, with quartiles −8.314/−2.790/+3.007 dB. The pilot preserves these intrinsic levels; the unchanged synthetic stream remains uniform −10 to +10 dB. The added examples therefore change both observed waveform exposure and release-level relationships as one data intervention, not a clean causal experiment isolating physiology from level distribution.

Earlier-triplet heart-lag candidates span −3.9145 to +3.99125 s (median −0.051 s); lung candidates span −3.993 to +3.990 s (median +0.153 s). Their weak/ambiguous correlation and poor held-out closure do not identify a fixed device latency. Three-window local lag ranges have medians 707 heart samples and 481 lung samples (177 and 120 ms). They are **instability/ambiguity indicators, not reliable clock-drift estimates**; periodic-peak switches and low correspondence prevent a physically justified time warp. No DTW target transformation is selected.

All late heart global lag estimates are zero; the unrestricted search selects misleading nonzero weak-lung peaks in a few examples, whereas the restricted zero-lag shared model closes every late case across both flanks. Do not infer real drift from those spurious candidates. The calibrated gain is positive; no late polarity flip is required. Negative fitted gains in weakly corresponding earlier records are not evidence of true acquisition polarity inversions.

## 6. Amplitude, clipping and noise

No assessed reference or earlier mixture has a full-scale sample. Every late mixture peaks at `32767/32768`, with 28 full-scale samples across 27 files. This is consistent with peak-normalized release preparation; a peak-code occurrence alone is not evidence of extended clipping. Quantization-scale closure argues against severe clipping/nonlinearity in the additive subset. Maximum absolute DC is about 6.16e−6 in the early group and 9.76e−5 in the late group; no DC-repair step is introduced.

The 50 ms block-RMS 10th percentile is used only as a low-energy proxy. Its median relative to record RMS is 0.344 for native/released mixtures versus 0.394 for descriptor-matched synthetic examples. These intervals may contain quiet physiology, not noise-only recordings. Independent background noise, AGC and nonlinear filtering cannot be isolated from these recordings alone. For the early group, residual energy near mixture energy is too large to claim a small additive noise-floor discrepancy; its cause is not uniquely identified. For the late subgroup, the tiny residual is consistent with PCM quantization, not a newly measured independent recording-noise process.

## 7. Global waveform/filter correction

The fixed global two-input correction uses 257-tap centered FIRs, fitted on the 74 triplets/32 fitting pairs and 6–9 s only, equal pair then recording weight, with ridge/smoothing/gain limits frozen in the analysis config. The 26 triplets/eight held-out pairs do not fit global coefficients.

For the earlier 73, global-FIR held-out temporal residual/mixture RMS median is **1.035**, versus 1.036 after alignment/two gains; it does not solve correspondence. For the late 27 it is **0.0941**, much worse than the identity plus shared gain (~0.000166). The pooled global method has zero passes under the weaker-source error tolerance. This rejects that correction, **not** the independently qualified additive subset. No per-record arbitrary FIR, inverse device curve or further filter search is justified.

Published nominal modes motivate `M≈Gm(H+L)`, `Href≈Gh(H)`, `Lref≈Gl(L)` but do not identify these functions. The held-out evidence does not establish a family-independent correction for the nonadditive population. The late common-gain identity empirically supplies a compatible target domain without requiring any claimed physical filter inverse.

## 8. PSD correspondence and why the pooled result is insufficient

The fixed spectral diagnostic uses Hann Welch 2048/1024, 20–1,800 Hz, two nonnegative gains per frequency, ridge 0.01×Gram trace, nine-bin smoothing, gain cap 100. All three PSDs use the same per-triplet mixture-variance normalization; there is no per-record gain fit. Fit74/32pairs and held-out26/8pairs match the registry. Synthetic known-map and independent NNLS-equivalence checks passed before interpreting audio results.

Held-out eight-pair macro error worsens after the global PSD map: Hellinger **0.3227→0.4297**, total variation **0.3682→0.4792**, mean absolute log-PSD error **7.904→12.713 dB**. Relative PSD-RMSE falls by shrinking outputs, but mapped band power is **18.64 dB below** the mixture; that is not improved physical fidelity.

The following descriptive stratification reuses those stored outputs and the identical pooled fit; **no subgroup refit was performed**:

| Held-out subgroup | Rows / pairs | Raw → mapped Hellinger | Raw → mapped log-PSD MAE |
|---|---:|---:|---:|
| Early nonadditive | 23 / 8 | 0.3805 → 0.4578 | 4.852 → 8.213 dB |
| Late additive | 3 / 3 | 0.0295 → 0.3470 | 24.848 → 35.143 dB |

Late raw PSD shape is already close; large amplitude error is explained by variable common gains. A single absolute pooled transfer cannot represent those gains. Consequently the global PSD failure is **not evidence against Role A for the additive subset**, nor proof that all native source spectra lack correspondence. The tiny late held-out stratum and post-hoc regime discovery are limitations, not a new independent validation claim.

Metadata-selected controls used wrong-heart, wrong-lung, both-wrong and same-family alternative fit-partition references; same site was preferred, stable seed-20260928 hashes broke ties, and no signal score chose controls. The correct references had lower Hellinger error in respectively **13, 15, 16 and 8 of 26** held-out conditions. The pooled mapped diagnostic thus provides weak discrimination, especially against same-family alternatives. It does not qualify a general spectral-supervision role for the rejected 73.

For actual sample-aligned sums, `P(H+L)=P(H)+P(L)+2 Re C_HL`; the numerical cross-spectral identity was checked. Median absolute cross-term mass is 4.71% of summed reference PSD mass. Ignoring it explains some remaining PSD-shape discrepancy even for waveform-additive data. The cross-spectrum between separately recorded references is not automatically the cross-spectrum between unknown simultaneous components, so PSD matching alone cannot identify clean component targets. First/second-half Hellinger medians are H=0.154, L=0.198, M=0.170: stationarity is imperfect and whole-record spectra discard timing.

## 9. Native/released versus synthetic domain descriptors

Five frozen relative levels were used for same-family, site-first deterministic synthetic descriptor controls—not to estimate native gains. Across 40 family-pair means, released-minus-synthetic differences were centroid **+7.85 Hz**, crest factor **+2.26**, envelope 90th/10th-percentile dynamic range **+1.33 dB**, and peak-normalized RMS **−0.0129**. These pooled differences have substantial between-pair spread and mix the two release regimes; absolute RMS also reflects explicit synthetic scaling. They demonstrate heterogeneity, not a uniquely identified acquisition mechanism or proof that real-mixture adaptation will improve T9.

## 10. Quality tiers and target compatibility

| Category | Count | Decision |
|---|---:|---|
| N1: high-confidence same-time waveform correspondence after shared amplitude calibration | 27 | 26 retained after one exact full-triplet duplicate; raw unit-gain targets are not selected |
| N2: qualified lag/transfer-corrected correspondence | 0 | No such correction qualified |
| N3: qualified spectral-only supervision | 0 | No reliable general spectral target map established |
| Assessed but correspondence-unqualified | 73 | No training role; preserve evidence |
| Duplicate | 1 | `M0126` excluded, retain `M0111` |
| T9-associated/unassessed | 45 | Excluded before audio access; no quality label inferred |

Tiering precedes neural treatment and uses the fixed weaker-source residual tolerance, not future model scores or family difficulty. Full accounting is 26 selected +1 duplicate +73 unqualified +45 sealed =145. Selecting the additive regime narrows the claim: it does not rehabilitate all 145 nominal native triplets.

With uncorrected nonadditive targets, consistency creates a conflict: if outputs sum to `M`, their target errors must sum to `M-H-L`. At least one error is therefore unavoidable, even for an otherwise perfect model; the squared-error sum is bounded below by half the residual energy. The selected targets `gH,gL` remove that conflict to the measured tiny tolerance. The residual is **not** divided into targets to manufacture exact closure. Targets mean the empirically shared-gain components of the released mixture, not anatomically pure latent sources beyond what the recording labels justify.

## 11. One matched pilot, predeclared before optimizer steps

The authoritative protocol is `hls_native_pilot_v1.json`. It preserves the 171,313-parameter N64/B32/H64 Conv-TasNet, fresh seed20260928, AdamW0.001/weight-decay0.0001, batch4 synthetic, clip5, existing fixed-label negative SI-SDR +5×RMS-normalized L1, CPU environment and the exact synthetic stream/evaluator.

Treatment uses **576 updates**, constant LR, endpoint checkpoint only, and adds a separate batch4 of qualified native examples to every unchanged synthetic batch: `Lsynthetic + 0.25 Lnative`. Thus example counts are equal but objective stream weights are 4:1; extra compute is disclosed. Native sampling is heart-family balanced, then available lung family, then triplet, then uniform aligned 8 s crop. Original mixture and gain-corrected references receive the same crop/common peak scaling; no relative-level augmentation, independent source normalization or recomputed input sum. This conservative one-weight intervention preserves exact synthetic supervision; there is no ratio search.

The matched historical grouped control may be reused only after verifying fresh initial state hash, folds, optimizer, first2,304 synthetic recipes and evaluator. Each held-out family receives zero native or standalone optimizer exposure. Evaluation is the existing **1,775 frozen synthetic conditions / eight held-out family pairs across five folds**, never the old two-pair score. Source/family labels and output order remain fixed.

All adoption clauses must pass: macro H/L SI-SDRi each>=1 dB, every held-out pair/source mean>=0, zero numerical failures; treatment-control **Q>=+0.5 dB**, balanced mean>=+0.5 dB, H and L each>=+0.25 dB; balanced mean improves in >=6/8 pairs and Q in >=4/5 folds; no pair/source regression worse than0.5dB; either pooled negative-condition rate rises by no more than5percentage points. This reuses the prior data-expansion engineering gate;0.5dB exceeds twice the observed~0.227dB seed-Q difference but is not a significance claim. There will be no rescue loss, weight, seed, role or capacity after a valid failure.

If FAIL, retain unchanged v2 and stop before T9. If PASS, train fresh seed20260928 on all45H+41L and the same26 eligible triplets, identical combined objective, constantLR0.001 for exactly576updates, endpoint only. No target validation remains after full non-test absorption. Then freeze v3 while preserving v1/v2 history and perform synthetic-only strict-load/finite/shape/consistency/zero checks. T9's predeclared225conditions and comparators are unchanged and not executed.

## 12. Risks and honest interpretation

The extra files supply some new observed waveforms but no established new independent families/patients. Only26triplets qualify, with source reuse and fixed level patterns. Pilot gains may be small or absent; that is a valid result. Offline reference gain estimation prepares training labels and is absent at deployment. Shared-gain calibration does not establish general physical stethoscope response. A valid pilot gain would support **improved non-test family transfer from qualified HLS release supervision**, not a solved plateau, clinical utility, patient-independent generalization or verified real-acoustic-mixture learning.

No treatment training result is claimed in this audit. T9 audio, production, frontend and FYP1 remain untouched. No demographic inference input is needed.
