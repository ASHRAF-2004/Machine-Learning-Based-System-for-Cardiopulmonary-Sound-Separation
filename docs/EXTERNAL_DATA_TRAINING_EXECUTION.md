# External-data programme: completed pre-test decision

**EXTERNAL PILOT REJECTED / HLS-ONLY FINAL REFIT COMPLETE / REPLACEMENT T8 FROZEN /
HELD-OUT T9 NOT EXECUTED / NOT DEPLOYED.** Date: 29 September 2026.

## Decision

**Strategy C — HLS-only fallback is selected.** The bounded CirCor/SPRSound
pretraining strategy did not improve target-domain family transfer. Its frozen
adoption gate failed; no full external download/pretraining, capacity comparison,
additional seed, augmentation or tuning rescue followed. This is evidence about
this particular imperfect-source pilot, not proof that all external data fail.

The original HLS-only grouped-family gate passed. Accordingly, one fresh model
was refit on all 45 heart and 41 lung non-test sources at the preselected
576-update endpoint. It supersedes original T8 **before T9**, without modifying
the original specification/checkpoint. This programme does **not** establish
that the approximately +3 dB plateau was broken. The new endpoint has no held-out
score until separately authorized T9; the broader grouped-CV scores below are
not directly comparable with the original two-pair validation result.

## Preflight and acquisition

The complete read-only tool/auth inventory is
`research/evidence/external_m0_preflight_v1.json`. All ten CLI-configured servers
passed cheap checks: cloudflare-api, cloudflare-bindings, cloudflare-builds,
cloudflare-docs, cloudflare-observability, cua_repl, graphify, node_repl,
openaiDeveloperDocs and resend. Hosted GitHub, Figma, Gmail, Drive, Notion, Canva,
Zapier, codex_tui and web checks also completed; Zapier had no enabled apps and
CUA no attached browser, not authentication failures. GitHub CLI/MCP identity was
ASHRAF-2004. Normal HTTPS and external Brave launch were verified. No sign-in,
package installation, GPU/driver change or production mutation occurred.
Graphify was queried first; its old index did not cover current ML paths, so only
required current source files were read. No Graphify Memory population.

Seventeen serious candidates and original-source/APA references are in
`EXTERNAL_DATASET_AUDIT.md` and
`research/datasets/external_dataset_catalog_v1.json`. No acquired external corpus
qualified as Tier A isolated or simultaneous clean heart/lung references.
The selected **pilot** sources were [CirCor 1.0.3](https://physionet.org/content/circor-heart-sound/1.0.3/)
and [SPRSound](https://github.com/SJTU-YONGFU-RESEARCH-GRP/SPRSound), pinned release
commit `bca1e51422a42a042441010081519610ef3845d0`. These are Tier B source-dominated
clinical recordings, not physiologically clean separation targets. ODC-By 1.0
and CC BY 4.0 lineage/attribution remain attached. No external weights enter the
final candidate, so the failed pilot creates no final external-data dependency.

Initial representative qualification used 40 subject groups per source, max two
records each. The frozen pilot expanded once to 160 metadata-selected groups
per source, without replacing difficult examples after waveform inspection.
613 originals (304 heart, 309 lung; 2.928 hours) were acquired, approximately
112.3 MB including metadata, with 519 GiB initially available. Originals are
immutable in ignored `.local/datasets/`; derived arrays are separate.

| Eligible partition | Heart records / linked groups | Lung records / subjects | Eligible duration |
|---|---:|---:|---:|
| External training | 115 / 74 | 240 / 133 | 0.5644 h heart; 0.7407 h lung |
| External subject holdout | 12 / 8 | 31 / 16 | 0.0600 h heart; 0.1015 h lung |

398 accepted records and 215 explicit exclusions account for all 613 candidates.
Heart eligibility requires contiguous accepted cardiac annotations ≥8 seconds;
lung excludes Poor Quality and requires ≥8 seconds. No concatenation of people,
fabricated clean targets or source denoising. Screening covered finite/readable
audio, rate/channels, silence/clipping, duration, annotation validity and
duplicates. SPRSound's exact malformed mono-PCM16 blockAlign header pattern is
corrected in memory only; one CirCor invalid label-28 annotation was excluded.
Zero-duration unannotated end markers contribute no eligible samples.
There were no exact duplicate clusters or near-copy flags in the pilot's 5,429
fingerprint-shortlisted comparisons; this is not exhaustive global proof.
A known external SPRSound challenge train/test duplicate is documented and was
not in this pilot. HLS-derived mirrors were excluded by provenance, without
opening T9 for fingerprinting.

Original CirCor 4 kHz and SPRSound 8 kHz recordings become deterministic 4 kHz
mono float32; anti-aliased `resample_poly` with Kaiser 8.6 is recorded with hashes.
CirCor linked Additional IDs and SPRSound subject IDs cannot cross the hash-based
external split. Registry schema, exclusions and source-purity uncertainty remain
explicit. The source-class/device confound (heart Littmann 3200 versus lung
Yunting II), pediatric predominance and clinical-to-manikin shift are substantial.
Spectrogram review was bounded/deterministic, not clinician purity certification.

Accepted registry: `.local/datasets/pilot-acquisition-v1/accepted-registry-v1.json`,
SHA `09b2aefca4c957ea0346039f7ca8d4d5c553f49bf109f6b0da02a390e733328d`.
Tracked metadata: `research/manifests/external_pilot_registry_v1.json`,
SHA `c922d58bf1cf2b0daae0acdfc110199c55f70c5b1cf5120c2eb0dc04372ffae6`.

## Diversity, purity and product implications

Shared training ages are Infant/Child/Adolescent: heart record counts 10/58/47,
lung 26/196/18. Unknown/unshared domains were not assigned invented ages.
Heart sex counts are 47 female/68 male, lung 124/116; no demographic inference.
Heart murmur labels Absent/Present are 61/54; these are not disease diagnoses.
Lung released record labels Normal/DAS/CAS&DAS/CAS are 169/40/17/14; disease
diagnosis remains null where not linked. Four cardiac sites and four pulmonary
positions are represented, but only one selected device domain per source class.
These distributions support source diversity, not broad adult coverage or causal
age/sex performance conclusions. External sanity subgroup counts are too small
and confounded to establish conditioning benefits.

**UX DECISION A: NO DEMOGRAPHIC INPUT REQUIRED.** Neither age nor sex is a model
input. No frontend modification, demographic classifier or automatic routing.

## Frozen experiment and observed result

`EXTERNAL_PRETRAINING_PILOT.md` and the immutable pilot config define the rules
before treatment results. Small N64/B32/H64 Conv-TasNet, 171,313 parameters,
seed 20260928, AdamW LR .001/decay .0001, batch 4, clip 5, fixed-label mean
negative SI-SDR + 5 RMS-normalized L1. Constant LR; no scheduler/early stopping
for this fixed-update protocol. Eight-second crops, family/subject balancing,
crop-RMS lung/heart uniform −10 to +10 dB and shared scaling. No model redesign.

Five HLS control folds ran 1,152 updates with 576/864/1,152 observations.
Eight held-out family pairs receive equal weight, not five unequal folds or
1,775 correlated rows treated as IID. No held-out fold family receives optimizer
exposure. The ranked best 1,152 endpoint had Q=1.933253, M=1.992900; **576** was
the earliest within 0.10 dB on both (Q=1.913416, M=1.962968). Its absolute gate
passed: both macro source improvements ≥1, every pair/source mean ≥0, zero failures.

External pretraining used the frozen 355 training recordings, hierarchical
age → dataset → released label → subject → record → crop sampling. Exactly
2,304 updates (9,216 draws), endpoint only, **295.962 s**, peak **1,022.844 MiB**.
The 32 subject-heldout imperfect-target sanity conditions scored H/L SI-SDRi
8.771/9.636 dB. This is not physiological clean-source truth, HLS evidence, or
32 independent subjects; it selected no checkpoint. Pretrain endpoint SHA:
`546e7ec4cbd0f246250f3c9d224eaafbd48034a32790b3c1694dd3f183467bce`.

Five HLS treatments used that single endpoint with reset optimizer and the same
576-update recipe prefix as controls. No treatment duration/seed search.

| At 576 HLS updates | Heart SI-SDR | Heart SI-SDRi | Lung SI-SDR | Lung SI-SDRi | Q | M |
|---|---:|---:|---:|---:|---:|---:|
| HLS-only control | 2.021 | 2.013 | 1.922 | 1.913 | 1.913 | 1.963 |
| External-pretrained | 1.869 | 1.860 | 1.594 | 1.586 | 1.586 | 1.723 |
| Difference | −0.152 | −0.152 | −0.328 | −0.328 | −0.328 | −0.240 |

| Held-out family pair | Control H/L SI-SDRi | Treatment H/L SI-SDRi | Δ balanced mean |
|---|---:|---:|---:|
| Atrial Fibrillation × Wheezing | 2.984 / 2.739 | 1.852 / 2.739 | −0.566 |
| Early Systolic Murmur × Rhonchi | 1.246 / 0.807 | 1.272 / 0.916 | +0.068 |
| Late Diastolic Murmur × Fine Crackles | 2.836 / 2.609 | 2.808 / 0.906 | −0.866 |
| Late Systolic Murmur × Wheezing | 0.476 / 0.985 | −0.124 / 1.434 | −0.076 |
| Mid Systolic Murmur × Normal | 1.890 / 1.436 | 2.164 / 1.351 | +0.095 |
| Normal × Pleural Rub | 1.220 / 1.444 | 0.825 / 1.439 | −0.200 |
| S3 × Fine Crackles | 3.539 / 3.528 | 4.160 / 2.078 | −0.415 |
| Tachycardia × Rhonchi | 1.909 / 1.759 | 1.924 / 1.823 | +0.039 |

The predeclared gate required ΔQ and ΔM ≥0.50 dB, each source ≥0.25 gain,
≥6/8 pair-M gains, ≥4/5 fold-Q gains, no pair/source regression >0.50 dB,
zero new numerical failure, ≤5 percentage-point negative-rate increase, plus
absolute utility. Actual gains occurred in **3/8 pairs and 1/5 folds**, and one
pair/source was negative. **FAIL**, with no post-hoc relaxation.
Both arms had zero numerical failures, but negative SI-SDRi condition rates
were control H/L 24.789%/28.732% versus treatment 26.986%/31.211%.
Thus failure-free execution does not mean every mixture benefited.

The matched comparison is descriptive negative transfer. Purity, device and
clinical/manikin mismatch are plausible mechanisms, not isolated causal findings.
Old T8 is valid on its original validation; it is not a leakage-safe comparator
on new folds containing its former training families. No claim of improvement
over its ~3.1 dB score follows from this different grouped protocol.

## Final HLS-only refit and T8 v2

Authorization `research/configs/hls_final_refit_authorization_v1.json` bound the
passed HLS control gate and failed external gate before initialization.
Run `refit-all-nontest-seed20260928` started from clean commit
`7eefa37100bb40d878d48b84b3811557ce98512b`, fresh library-default seed 20260928,
zero optimizer state, **no external/T4/T7 checkpoint loaded**. All 45 heart/41
lung sources (8/5 families, 21.5 minutes) came from the frozen non-test allowlist.
Exactly **576 updates / 2,304 draws**, constant LR .001, endpoint only; no
validation-based stopping or absorbed-validation checkpoint selection.
Runtime **75.179 s**, peak **1,012.695 MiB**, zero numerical failures.

Final artifact (ignored):
`.local/training/stethofuse-tcn-v1/pre-t9-family-refit-v1/refit-all-nontest-seed20260928/checkpoints/endpoint.pt`.
SHA: `1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658`.
Specification: `research/configs/final_separator_v2.json`.
SHA: `2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b`.
Original v1 bytes/hash and old checkpoint are preserved; v2 records
`SUPERSEDED_BEFORE_T9`. This is a new HLS-only T8, **not external-data-trained**.

Inference is unchanged: 4 kHz mono float32, 10-second windows/8-second hop/
2-second overlap, right padding and exact trim, whole-record shared peak scale,
raw waveform estimates plus target-free equal-residual consistency, fixed
heart/lung order. No projection, permutation, oracle, ensemble or model routing.
Environment: Python 3.14.4, torch/torchaudio 2.11.0+cpu, NumPy 2.4.4, SciPy 1.17.0,
two torch threads/one interop thread. No GPU/environment changes.

## Evidence, checks and provenance caveats

`research/evidence/external_program_execution_v1.json` preserves all run manifests,
code/data/recipe/endpoint hashes and individual runtime/RSS. Control runs and
pretraining started clean `328b38c79e4261c0226067cb54403ace2442cedc`; treatments
started clean `9b0664a96ea865d237f157fe6d7ad0199d0d0596`.
Controls took 1,046.2 s including process overhead; treatment campaign 475.4 s.
Maximum run RSS was 1,029.5 MiB; CPU was practical. No capacity variants were run.

Tracked decision receipts are now byte-identical to their original local
receipts, correcting an intermediate JSON reserialization/hash ambiguity without
changing values, gates, authorization or history. Control SHA:
`0d8893d61d9ed9517d0227781f33b3357b1c41f85d4ee80228f1691545d47dbe`;
treatment SHA:
`596859fdaa6456369e8b6d876bfc18ba813e837f2844d4e06771a5cb79a34e41`.
The original receipt phrase “contaminated oldT8” refers only to ineligibility on
these new folds, not invalidity of the original training/validation experiment.

Nine focused external-audio/registry/pretraining/family-runner tests passed;
no application regression campaign. All 9,216+32 frozen external crops passed
finite/additivity preflight. Final synthetic smoke strictly loaded the hash-
verified 171,313-param endpoint, produced finite `[2,60001]`, zero-input zeros,
and maximum mixture-consistency error 5.96e−8. No audio files were opened by
this smoke. Its receipt records metadata worktree edits honestly; every actual
training run began clean. No test recipes or test evaluation were generated.

## Frozen next action — stop before T9

The **identical** original T9 protocol object is carried into v2: 45 source pairs
at five predeclared levels = 225 conditions; mixture baseline, selected standalone
TCN, Fixed Filter and Generic NMF. Fixed-label SI-SDR/SI-SDRi, family-pair macro,
descriptive median/IQR, failures and CPU runtime; no VMD/NeoSSNet or retuning.
Actual test recipes/audio remain unopened. Separate explicit owner approval is
required. A genuine invalidating bug requires preserved evidence, documented
correction and explicit rerun approval, never silent test-driven optimization.

**READY FOR T9 WITH ORIGINAL/HLS-ONLY T8 — selected HLS-only version 2.**
No clinical, patient-independent or broader superiority claim. T9, production,
application integration, frontend, Axora and submitted FYP1 remain untouched.
