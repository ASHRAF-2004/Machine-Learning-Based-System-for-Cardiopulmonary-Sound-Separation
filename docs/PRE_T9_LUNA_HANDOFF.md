# One pre-test intervention — Luna execution contract

**DESIGNED / NOT EXECUTED. Owner approval required. T9 SEALED.**
This handoff accompanies [the diagnosis](PRE_T9_PLATEAU_DIAGNOSIS.md). It does
not authorize execution during the diagnosis sprint. There is one intervention:
broader non-test-family training, with grouped budget qualification, then one
fixed-budget refit. Do not add a second setting, seed, loss, sampler or ensemble.
The exact [JSON plan](../research/configs/pre_t9_family_refit_plan_v1.json) is
normative together with this document. Fail closed on disagreement.

## Frozen behavior and explicit differences

Keep small Conv-TasNet171,313parameters, N64/B32/H64; fresh seed20260928 every
run; 4kHz,8s training,10s/8s-hop inference; heart/lung labels; equal-residual
consistency; current normalization/padding; no mixture-phase projection/PIT.
Loss remains mean negative SI-SDR +5×RMS-normalizedL1. CPU pinned environment
Python3.14.4, torch/torchaudio2.11.0+cpu; float32,2intra-op/1inter-op threads.
AdamW .001, betas(.9,.999), eps1e−8, decay1e−4, batch4, clip5.

Changes are **data membership and a fixed stopping budget**. Replace validation-
driven ReduceLROnPlateau/early stopping with **constant LR0.001 from update1
through1152**, stopping earlier only at the selected refit endpoint or a genuine
failure. No LR boundary/reduction exists. Both selected small-run optima occurred
before LR reductions; late decays supplied no consistent benefit. A scheduler
using absorbed validation would be invalid. Do not borrow a late decay or extend
updates merely because training loss keeps improving.

## P0 — integrity and non-test partition freeze

Files: T8 spec, this plan, original small YAML; prior run `eligible_split.csv`.
Verify clean Git HEAD/auth/identity, all hashes in the plan, selected T8 checkpoint
bytes, pinned environment and171,313construction. Do not load T8 into training.
Use **only the86-row eligible manifest**; reject any row not development/validation.
Do not call `audit_manifest`, enumerate the dataset, or inspect test files/labels.
Preserve original split CSV, test assignments and existing225validation recipes.

Create `research/manifests/pre_t9_family_cv_v1.csv` (metadata only) with original
split, kind, ID, family, source hash and assigned holdout fold; each source belongs
to exactly one holdout fold by the following fixed family assignment. Source
hash verification/PCM reads apply only to this allowlist. Store/hash manifests
before any training. No test recipe exists or is generated.

| Fold | Held-out heart families (files) | Held-out lung family (files) | TrainH/L | Held-out pairs ×5 |
| --- | --- | --- | --- | ---: |
| f1 | Mid Systolic Murmur(7) | Normal(12) | 38/29 | 420 |
| f2 | Normal(9) | Pleural Rub(9) | 36/32 | 405 |
| f3 | Early Systolic Murmur(6), Tachycardia(3) | Rhonchi(8) | 36/33 | 360 |
| f4 | Late Systolic Murmur(5), AF(4) | Wheezing(7) | 36/34 | 315 |
| f5 | Late Diastolic Murmur(6), S3(5) | Fine Crackles(5) | 34/36 | 275 |

This count-balanced assignment was specified before CV scores, not chosen by
model performance or test characteristics. Five folds follow the five available
lung families, retaining four training lung families in each fold. A three-fold
partition would remove two lung families in some folds and confound coverage
more severely. Each of8heart/5lung families is held out once. Fold training sets
overlap; CV results are not independent trials or an unbiased final-test estimate.
Only8of40possible non-test family-pair combinations are held out: each heart
family is assessed with one assigned lung family. This is broader family
coverage, not comprehensive disentanglement of heart×lung interactions.

Acceptance: exact counts, hashes, zero train/holdout file/family overlap per fold;
all86sources assigned; no test path reachable. Runtime~1min. Stop on discrepancy.
Checkpoint: committed metadata and provenance before P3.

## P1 — minimum offline runner support

Files to add: `scripts/train_stethofuse_family_refit.py`, optionally
`app/ml/family_refit_data.py` if a small adapter is needed. Reuse model/loss/
metrics and existing `training_epoch`/`make_mixture`; do not refactor application
code or weaken the existing test lock. The old baseline runner/config remains
reproducible. No scientific model behavior changes.

For each fold, exclude its held-out HS and LS families **entirely** from training;
do not mix a held-out source with a training source. For sampler input only,
construct training Source objects with development role; retain immutable
original split/fold provenance alongside. Never relabel a test source. Holdout
Source objects use validation role, drawn only from the allowlist.

Keep24draws per available family pair, shuffled source cycles, keyed PCG64 seed,
independent crop starts0..28000 and uniform[-10,+10]dB; identical crop-RMS/shared
gain math and peak normalization. Virtual epoch sizes f1/f2=672draws, f3–f5=576;
refit=960. Concatenate epochs beginning0 and consume exactly `4*update_budget`
draws. Save realized recipe prefixes including gains/hashes. Do not force576
draws by changing family weights. Truncating the last shuffled virtual epoch is
predeclared; no epoch rounding, source-exposure rescaling or duplicated fixed pair.

Fold holdout recipe: sorted `(family,ID)` HS outer loop ×sorted LS, each at
[-10,-5,0,5,10]dB; full60,000samples/start0; existing mixture equation. Freeze/hash
all1,775conditions before optimizer update1. These are **CV-only non-test**
conditions, not T9 recipes. Preserve original225validation evidence separately.

Runner: strict fixed-update stopping, snapshots/resume at576/864/1152, finite
loss/output/gradient assertions, compact logs every144updates, source/recipe
hashes, seed, clean code SHA, environment and initialization fingerprint. Save
model/optimizer/RNG/recipe-cursor state; resume only identical code/config/data.
No old checkpoint/T4/CV-fold weight initialization. No plateau scheduler, tuning,
cross-fold warm start, additional seed or checkpoint averaging.

Acceptance: exact planned parameter/config values and inaccessible test path.
Runtime: implementation work only. Checkpoint: commit/push as ASHRAF-2004 before
any real fold initialization; record clean SHA in each run.

## P2 — focused contract sanity, not another capacity campaign

Synthetic tensors only: one finite forward/backward, parameter count/source
order/additivity; verify optimizerLR and fixed stop/snapshot cursor. One synthetic
optimizer save/resume check may be used in a separate disposable smoke run,
never as initialization. Metadata-only fold/recipe determinism and aggregation
check (equal family-pair means, not row/fold weighting). At most3focused tests
cover these new runner contracts. Do not rerun T4 or an application suite.
Runtime<2min. Any defect: fix only the demonstrated defect, preserve evidence,
recheck before real training. No data/scientific change without owner review.

## P3 — one five-fold budget qualification

Execution order f1→f2→f3→f4→f5. Fresh seed20260928 for each, same model/settings.
Each runs **exactly1152 optimizer updates** (4,608draws), constantLR.001.
Evaluate only at updates **576,864,1152**; no every-batch or intermediate
model-selection evaluation. The three budgets bracket the historical4–8epoch
useful range (144updates/old epoch), not a wide schedule search.

At each snapshot evaluate every fold's frozen holdout condition under unchanged
10s/8s-hop inference, fixed-label SI-SDR/SI-SDRi; record per-family/level, failures,
runtime, normalized training components and gradient health. Do not compare an
oldT8 replay on these fold holdouts: many were T8 training sources, so that would
be a contaminated control. Never compare the CV aggregate directly to3.101dB
as if it were the same validation population.

At each budget calculate each of the8held-out **family-pair** source means,
then weight those8groups equally: H(u),L(u),Q(u)=min(H,L),M(u)=(H+L)/2.
Do not weight5folds equally (their group counts1,1,2,2,2 differ), nor1,775rows
equally. Report8group values and5fold descriptors, not an IID standard error.

Artifacts: ignored `.local/training/stethofuse-tcn-v1/pre-t9-family-refit-v1/`,
run IDs specified in JSON; own config/allowlist/fold/recipe/run SHA manifests,
all3snapshots, latest/resume, history, per-condition scores and hashes. No WAV
materialization or weights in Git. Expected~4–6min/fold on measuredCPU;5folds
~20–30min plus inference/I/O. More than15min/fold or90min campaign, RSS>4GiB,
nonfinite/label/data failure or repeat process crash: stop and preserve evidence.
Do not change threads/batch/LR to rescue performance. No stop merely for noisy
scores, unless numerical/contract/resource failure invalidates the experiment.

## P4 — deterministic decision gate, before any refit

1. Rank576/864/1152 by Q, thenM, then earlier update; metric ties tolerance1e−6dB.
2. Relative to that ranked winner, select the **earliest** budget having both
   Q andM within0.10dB below it. This is a predeclared stability preference,
   not a confidence interval/significance claim. Winner itself always qualifies.
3. At that selected budget require **H≥1.0dB andL≥1.0dB**, **each of8family
   pairs has both source means≥0dB**, and **zero failures** across all snapshots/
   folds. No dropping a difficult group/condition. The1dB utility guard is an
   engineering requirement against the mixture baseline, not a statistical
   assertion or direct improvement threshold over oldT8.
4. If ANY requirement fails: stop, keep T8 unchanged, report all evidence. Do
   not try another budget that happens to pass, a majority-fold rule, another
   seed, more updates or a different architecture. Owner review is required.

The gate qualifies broader held-family transfer and a training budget. It
**cannot demonstrate that the later all-data model beats T8**, because there is
no remaining clean validation set for that claim. Adopting refit is the
predeclared data-use decision, not post-hoc selection on absorbed validation.
Persist/hash the selected budget/gate receipt before P5. No model checkpoint
from CV becomes the deployment/T9 candidate. Runtime seconds.

## P5 — one final all-non-test refit, only after PASS

Use all45heart/41lung allowlisted files (8/5families), same sampler rules and
model/loss/optimizer; **fresh seed20260928**. Run exactly the P4-selected number
of updates: **576 OR864 OR1152**, not a discretionary range. ConstantLR0.001
for updates1..N; stop atN. No scalingN for data size; no validation scheduler,
early stopping, loss-based endpoint choice, extra seed or CV weight warm start.

The sole candidate is **checkpoint immediately after updateN**. The original
validation sources now participate in fitting, so do not score them for selection
or call old225-condition results new generalization evidence. Training curves
are numerical health evidence only. No test access. Save endpoint +resume,
SHA256, complete recipe/config/data/code/environment manifest and initialization
proof. Runtime~2–5min; same15min/4GiB safety cap. Failures stop for owner review,
not a scientifically different silent restart.

## P6 — replacement T8 integrity freeze

Only if P5 finishes the predetermined endpoint without invalidating defects:
strictly load/hash the checkpoint, confirm171,313parameters and current inference
source hashes; synthetic finite/length/consistency smoke only. Create a new
versioned separator specification (preserve `final_separator_v1.json` and its
checkpoint as historical T8, do not overwrite). Specify artifact, update count,
seed20260928, CV-budget receipt,86-source refit manifest and clean commit.

Inference, source semantics, comparators and original T9 metric/condition policy
stay unchanged. No ensemble reconsideration. Clearly distinguish CV budget
qualification from final-refit training and **no new held-out result**. Update
FYP2/PAUSE with actual evidence once, commit/push both repos, verify remoteHEADs
and clean nested worktrees; model artifacts stay ignored. Runtime<2min checks.

## P7 — stop before T9

Return five-fold results/selected budget/gate, final-refit provenance if executed,
replacement spec/checkpoint hashes, commits, runtime/failures and test-seal
confirmation. **STOP. T9 requires separate explicit owner authorization.**
If eventually opened, T9 remains one-shot on the complete frozen system; no
test-driven model/postprocessing/ensemble changes. Poor results must be reported.
Production, application jobs/frontend/security/deployment, Axora and submitted
FYP1 remain outside every phase.
