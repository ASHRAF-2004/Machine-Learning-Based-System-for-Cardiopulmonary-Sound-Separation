# Luna handoff — bounded implementation of ADR E01

> **Current handoff, 28 September 2026:** [ADR T01](STETHOFUSE_MODEL_TRAINING_PLAN.md)
> selects our own compact Conv-TasNet trained from scratch. Next: T0–T4 source
> freeze, additive generator, model/loss contracts and tiny overfit gate, then
> checkpoint before baseline training. No training occurred in this design
> sprint. NeoSSNet is research-only; author email is not an active prerequisite
> for our model. The50/50 ensemble below stays frozen/unqualified; no application
> integration, test-set use or deployment. Older stop instructions are history.

> **Historical diagnosis gate:** read [the reproduction diagnosis](NEOSSNET_REPRODUCTION_DIAGNOSIS.md).
> Do not start Phase E, training or final evaluation. Next: owner-authorised
> author/artifact/rights clarification and small native reproduction fixtures;
> not more manikin sweeps. See the report's exact request and acceptance gate.

> **Later status, 27 September 2026:** Phases A–D below have since been
> implemented/tested **offline only**. Read [the Phase A–D qualification
> checkpoint](ENSEMBLE_OFFLINE_QUALIFICATION.md) before using this original
> plan. NeoSSNet reuse rights, manikin source-order applicability and negative
> tiny development-set scores require review before final evaluation or
> application integration. Production remains unchanged.

Architecture/design sprint complete, 27 September 2026. Read
[selected design](ENSEMBLE_DESIGN.md) and [audited evidence](ENSEMBLE_SOURCE_AUDIT.md),
not the whole project history. **Stop at this design checkpoint until the owner
authorises implementation. No production deployment is implied.**

Selected: equal-weight complementary TF magnitude-mask fusion, released NeoSSNet
plus local NMF **conditional on qualification**. No learned gate or new model
training. Do not turn the absence of permissions/data into a replacement architecture.

## Phases and gates

| Phase / likely files | Deliverable and acceptance | Focused checks / safety |
| --- | --- | --- |
| A. Qualify artifacts/data/environment — existing `storage/ml_models/`, `app/ml/neossnet_source/`, new isolated ML lock and ignored evidence folder | Check pinned source/config/weights against audit; resolve code/weight reuse permission before release. Load original checkpoint with safe weights-only loading; two labelled finite outputs on one synthetic and one approved development window. Establish local4k derivative lineage and source-family manifest; no test-set scores yet. CPU first; measure cold/warm RSS/time. | One bounded dependency/load probe; reuse existing baseline smoke contracts. No global packages, live container, dataset overwrite, model download or training. If dependencies/permission cannot be resolved in one focused attempt, record blocker and stop that path. |
| B. Canonical adapters — `app/ml/ensemble/signal.py`, `adapters.py` (proposed), reuse existing DTOs and raw NeoSS/NMF paths | Anti-aliased4k mono conversion; common gain; boundary-safe STFT;10-s windows/8-s hop; exact labelled lengths; bypass legacy per-output normalisation. New path must leave historical adapters usable. | Small parametrised signal-contract batch: round-trip edges/resampling/length/nonfinite/source order. Real checkpoint shape test from A, not mocked proof of loadability. Do not build a general DSP framework. |
| C. Ensemble core — proposed `app/ml/ensemble/engine.py` + frozen version config | Exact masks and0.5/0.5 fusion; both experts mandatory; overlap-add and shared export gain; provenance. Missing expert means unavailable/failed, never silent fallback. | Controlled complementary-mask reconstruction and one failure-path test reusing B fixtures. Synthetic checks establish mechanics, not physiological separation. |
| D. Offline qualification/evaluation — new manifest-driven research runner beside `scripts/evaluate_strategies.py`, **no legacy DB initialisation** | Freeze source-group split and preprocessing. Controlled summed sources, fixed ratios/seeds, same methods/metrics; development debugging first, locked held-out evaluation once stable. Save per-source results/config hashes/failures, not just averages. | Reuse SI-SDR mathematical tests but disable ref-oracle alignment in the new evaluator. Test one known target/permutation/no-oracle contract. Do not rerun historical23 or fit weights; no large sweep. If independent test families inadequate, descriptive result only. |
| E. Durable queue — `app/m1/api.py`, `store.py`, `schema.sql` and current migration/version checks; proposed `app/ml/worker.py` | Existing owner POST returns202; reuse `m1_jobs`, atomic claim, persisted status, single ML process, heartbeat/deadline, interrupted-job failure and explicit retry. No broker. | In temp DB: owner isolation, one claim for concurrent requests, process-loss recovery. Existing M1 role/grant tests reused; no wholesale auth retest per edit. Migration must preserve original/review/audit data; back up a development DB before applying. |
| F. Result publication — existing `m1_results`, `m1_files`, `af_resources`, `m1_result_files` + private staging | Atomic publication of heart/lung/provenance; originals unchanged; no orphan public result; exact resource grants only, no implicit derived access. No inferred quality metric without ground truth. | One successful synthetic end-to-end job and one interrupted-publication check; owner200/ungranted403/anonymous401 and grant/revoke through existing paths. No new public media mount. |
| G. Existing UI integration — `frontend/src/data/` live client, current job/result pages | Enable current ensemble request/status/playback/history; no model selector, fake progress/confidence, demo fallback, owl or theme changes. | Focused request202→poll→result smoke, accessible failure state, protected playback. No redesign campaign. |
| H. Worker packaging / evidence — future isolated worker image/Compose override and `deploy/backup-restic.sh`, FYP2 evidence | API stays lightweight; models read-only; no worker Firebase credential or public port; verify CPU resource cap before optional GPU. Extend backup quiescence to **all** writers, not only existing API/web. Stage only after local integration passes. | One appropriate combined regression after stable code, one local synthetic worker/restart check. No production deployment/routing/backup change without later approval. |

Order A→B→C→D, then E→F→G→H. Queue/result design may be implemented in isolated
fixtures while permission is pending, but execution must remain disabled publicly.
Do not create a second database/model/job API. An unchanged auth milestone is not
an invitation to rerun real-user acceptance on every ML edit.

## Immediate next task

Phase A only: use pinned released NeoSSNet hashes and existing requirements as
inputs to an isolated **CPU ML** environment; confirm license/permission status and
load the checkpoint, then run one10-s synthetic shape/finite/channel check. Preserve
original dataset/model bytes. Current lightweight environment has NumPy2.3.5 but
not Torch/torchaudio/scipy/vmdpy; no GPU claim is established (`nvidia-smi` absent).
Do not spend hours on dependency experiments: report a specific unresolved blocker.

## Evidence required before claims

- Two qualified experts, corrected signal contract, exact version/provenance.
- Auditable4k derivative/source-family split; controlled digital mixtures as primary
  quantitative targets. Recorded triplets are not assumed additive truth.
- SI-SDR/SI-SDRi for heart and lung separately; raw/projection single-expert controls,
  runtime/memory/failures; paired uncertainty only with independent groups.
- Native NeoSSNet versus mask projection difference must be visible: improvement
  cannot be claimed merely by comparing against an artificially weakened expert.
- No clinical/diagnostic claim, no invented fine-tuned result, no “NMCF” label for
  generic NMF, no published-paper performance transferred to this application.

## Rollback boundary

Keep the existing `ensemble_unavailable` path as the feature-off state. Develop
additive migrations against copies only; do not downgrade a populated DB or erase
recordings to roll back. Worker/result writes must be quiesced for coherent backup
and deployment. Preserve current application/security/backup and submitted FYP1.
Each phase ends at a meaningful owner-authored commit, not automatic production work.

This design sprint added one read-only probe, **zero automated test functions**,
ran it once, and ran no regression/benchmark/training campaign. At the time,
the probe and documentation were the only implementation-repository changes;
there was no ensemble runtime yet. See the later status above.
