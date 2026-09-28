# Bounded external-data transfer experiment

**HISTORICAL PREDECLARATION / EXECUTED / EXTERNAL TRANSFER REJECTED / T9 SEALED.**
The frozen rule below was committed before treatment results. See
`EXTERNAL_DATA_TRAINING_EXECUTION.md` for results and the selected HLS-only refit;
do not execute the conditional external scale-up branch after its failed gate.
Normative configuration: `research/configs/external_pretraining_pilot_v1.json`.

## Decision and risk

Select strategy A: **external pretraining → HLS target-domain fine-tuning**.
Keep the 171,313-parameter model, objective, gain range, consistency and inference.
Joint training is not selected: it adds a target/external mixing weight and risks
allowing the larger clinical domain to dominate the manikin target. HLS-only
grouped training remains the control/fallback. No capacity or LR variant is
preauthorized by this concrete protocol, despite the program's broader ceiling.

CirCor and SPRSound are selected for bounded qualification, not called pure
references. CirCor expert-accepted continuous cycle intervals and SPRSound
non-Poor-Quality respiratory annotations support **imperfect-source Tier B
pretraining**, not clinical separation truth. The representative sample retained
35/73 heart records from23/40groups and70/77lung records from38/40groups after
annotation/technical criteria. Spectrogram inspection of three deterministically
chosen candidates and one excluded control per source shows cardiac impulses
and respiratory structure, but also broadband clinical background and device
bandwidth differences. No clinician listening/purity certification is claimed.
Source/dataset/device confounding remains a major risk; the grouped HLS transfer
gate, not an external reconstruction score, decides adoption.

SPRSound's redundant WAV block-align field is inconsistent with mono PCM16 and
byte rate. The exact known pattern is corrected only in memory; original hashes
remain immutable. A synthetic regression protects the correction. No filtering
or denoising is applied to manufacture clean targets. Three zero-duration
CirCor unannotated end markers are ignored; they add no eligible sample.

## Data freeze before training

Qualification used40subject groups/dataset, max2records/group, stratified without
waveform cherry-picking and including poor/unknown controls. Pilot acquisition
expands once to160metadata-selected groups/dataset, max2recordings/group. Same
source-quality criteria; no replacements after waveform inspection. CirCor
Additional-ID components are merged. SPRSound's known repeated Git blobs are
deduplicated, with normalized waveform fingerprint checks after canonicalization.
Do not download/count HLS mirrors or derived challenge task folders as diversity.

Hold out approximately10%of external patient groups using the fixed hash rule
before quality filtering. Dataset-group namespaces (`circor`, `sprsound`) and
linked-patient components remain invariant across release versions. Required
pilot training coverage:≥64subjects per source **after** quality, duplicate,
duration, shared-age and patient-holdout exclusions. SPR ages in years map to
Infant≤1, Child>1 and<12, Adolescent≥12 and≤18, matching released CirCor domains.
Unknown/unshared age domains do not enter age-compatible supervised
mixtures; their metadata remain in the registry, not fabricated. Pair known
shared age domains uniformly, then dataset, released sound label, subject,
recording and valid crop. This is population balancing, not demographic routing.
Use one model with no age/sex inference input. Keep original disease/event labels
distinct; murmur status is not a disease diagnosis.

### Pilot qualification receipt (before optimizer exposure)

The frozen 613-record candidate acquisition yielded 398 eligible imperfect-source
records and 215 explicit exclusions. Training: 115 heart records/74 linked subject
groups (2,031.835 eligible seconds), 240 lung records/133 subjects (2,666.496 s).
External holdout: 12 heart/8 subjects and31 lung/16 subjects. Infant, Child and
Adolescent domains occur in both partitions; unknown/neonatal unshared domains
are excluded from these synthetic pairs, not assigned invented ages.

No exact duplicate cluster or near-copy flag was found in5,429 fingerprint-
shortlisted comparisons. This is a bounded screen, not proof of global uniqueness.
One invalid CirCor annotation (`50782_MV_1`, label28 at zero duration) is excluded,
not repaired into a cardiac label. Candidate selection was not redrawn after the
age12 pairing-boundary correction. Original acquisition strata remain recorded.

Accepted registry SHA-256:
`09b2aefca4c957ea0346039f7ca8d4d5c553f49bf109f6b0da02a390e733328d`.
Tracked metadata: `research/manifests/external_pilot_registry_v1.json`.
All9,216 training and32 external sanity recipes materialize finite, non-silent
eight-second crops; maximum normalized additivity error1.1921e−7. This was a
no-model/no-optimizer preflight, not a pretraining result. Nine focused tests
passed; no application regression campaign was run.

Freeze the accepted registry, split/duplicate exclusions, 9,216training draw
recipes and32external-heldout sanity conditions before optimizer step1.
External sanity seed20260929 is a recipe seed, **not another model seed**.
Canonical4kmono float32; eight-second crops, crop-RMS±10dB mixing and shared
normalization unchanged. No unrelated-source concatenation, tiling, new EQ/noise.

## Matched target-domain control and treatment

First execute the pre-existing five-family-fold control protocol at1152updates,
with snapshots576/864/1152. Determine the control budget by its predeclared
earliest-within0.10dB Q-and-mean rule. Persist this decision before treatment.
Eight family-pair means have equal weight; not1775IIDconditions or five equally
weighted folds. Old T8 is not a leakage-safe comparator on these new grouped
holdouts because it trained on many of them. Its original ~3.101 dB validation
remains valid historical evidence, **not** this experiment's matched control.

External pilot: fresh seed20260928,2304updates, AdamW0.001/decay1e-4, batch4,
clip5, existing fixed-label −SI-SDR+5normalizedL1. Constant LR, endpoint checkpoint,
CPU pinned environment. No external early stopping/checkpoint search.

Treatment: initialize each HLS fold from this single external endpoint; reset
optimizer, same seed/recipes/settings as control; run exactly the control-selected
budget. No HLS held-out family gets optimizer exposure. One endpoint evaluation
per treatment fold; no treatment-specific choice among576/864/1152.

## Adoption rule (frozen before treatment results)

Require all: macroQ and balanced mean each improve≥0.50dB; macroheart and lung
each improve≥0.25dB; balanced mean improves in≥6/8family pairs; Q improves in≥4/5
folds; no family/source mean loses>0.50dB; zero new numerical failures; pooled
negative-SI-SDRi rate for either source rises by no more than5percentage points.
The treatment must also pass the original absolute utility gate: heart and lung
macro SI-SDRi each≥1dB, every family-pair/source mean≥0dB, zero numerical failures.
Use failures as failures, not dropped rows. These are conservative engineering
guards, not significance tests. The0.50dB margin exceeds twice the previously
observed0.226dB between-seed macroQ gap; two seeds cannot estimate seed variance
reliably. Correlated folds/family pairs remain descriptive.

If FAIL, stop external training; apply the already-frozen HLS-only gate to its
control result. If that passes, its conditional all-non-test refit is the fallback;
if not, preserve originalT8 and report. No further data/loss/model rescue search.

If PASS, acquire the full qualified original pools (CirCor public1.0.3 and
canonical SPRSound2022–2025), maintaining exclusions/subject holdout. Full pretrain
is one fresh9216-update run (4×pilotdrawbudget for larger subject coverage), same
settings; no selected pilot-only shortcut. Repeat the same HLS treatment folds
at the already-selected budget and require the same gate against control.
If full strategy passes, fine-tune its endpoint once on all45H/41LHLSnon-test
sources, seed20260928, new optimizer, exact fixed budget, endpoint only. Do not
score absorbed HLS validation to pick a checkpoint. If full strategy fails,
return to HLS-only fallback; do not tune or choose pilot weights post hoc.

Expected CPU: pilot minutes, paired five-fold comparison tens of minutes, full
pretraining tens of minutes; measure rather than promise. Caps30minpilot,
120minfull,8GiBpretrain; existing15min/4GiBHLSfold limits. NoGPUinstallation.

## Final freeze and stop

Every real run starts from clean committed source and records code/config/data/
recipe/environment/checkpoint hashes. Originals, derivedcaches and weights stay
ignored. Preserve final_separator_v1.json byte-for-byte; create a new version
only after valid strategy selection/fixed endpoint training. Freeze the same
inference/semantics/test-comparator protocol. **STOP before T9**, regardless of
outcome. No production, integration, ensemble or demographic frontend changes.
