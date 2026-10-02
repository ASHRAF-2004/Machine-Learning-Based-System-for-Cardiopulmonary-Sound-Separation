# Frozen v2 application integration — local acceptance

Date: 29 September 2026. **IMPLEMENTED LOCALLY / TESTED LOCALLY / FINAL ML
EVALUATION COMPLETE / PRODUCTION ML INTEGRATION NOT YET DEPLOYED.** Model
selection is closed. T9 is consumed and was not reused for application tests.
No training, fine-tuning, model/inference change, new comparator or deployment.

## Checkpoint and preflight

Starting implementation `2f57d6768bccce7bf7ad8cc862ed1adb47c256bd` and
documentation `cf256d5e2529caea0a1ce0bb6938d23984793448` were clean on
`fyp2/application` / `fyp2/documentation`. Root PAUSE anchor was
`aaae305c5c872b986b2aeb875e0288de2baf35a3`; unrelated root/frontend/owl changes
were preserved. Git name/account ASHRAF-2004 and existing configured email/remotes
were verified. Existing draft PRs #9/#2 are used; no merge/force-push/new PR.

Cheap read-only preflight covered all configured MCPs: Graphify, Cloudflare API,
bindings, builds, docs and observability, Resend, node_repl, cua_repl and
openaiDeveloperDocs; exposed GitHub tools returned ASHRAF-2004 and codex_tui
responded. Graphify repository query, Cloudflare read-only list/docs/account
checks, developer-docs listing, Resend domain listing and JavaScript smoke passed.
CUA responded with no attached surfaces; normal external browser launch via
`xdg-open` succeeded in an existing Brave session. GitHub HTTPS, CLI auth and
remotes passed. No sign-in, configuration deletion or provider write occurred.
Graphify was used first; its older graph omitted current M1/ML paths, which
were then read directly. Graphify Memory was not populated.

Implementation and clean acceptance anchor:
`58be00a4a972b77680edfd93a758e8a36e391184`. Packaging allow-list correction:
`2b6b3c0b461cff0bb8e865a11cf43f9db394d1e2` (only `.dockerignore`; application
behavior unchanged). Both were pushed under the required identity.

## Immutable model boundary

| Item | Verified value |
| --- | --- |
| Internal model ID | `stethofuse-tcn-small-hls-refit-waveform-v2` |
| Architecture | Compact Conv-TasNet N64/B32/H64, 171,313 parameters |
| Historical training | Fresh seed20260928,576 updates,45 heart/41 lung non-test sources |
| Checkpoint SHA-256 | `1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658` |
| Spec SHA-256 | `2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b` |
| Spec | `research/configs/final_separator_v2.json`, unchanged |
| Runtime | Python3.14.4, torch/torchaudio2.11.0+cpu, NumPy2.4.4, SciPy1.17.0 |
| Inference | 4kHz mono float32;10s window,8s hop,2s overlap; heart then lung |
| Reconstruction | Unmodified raw waveform inference + existing per-window equal-residual consistency |
| Not used | Projection, permutation, reference correction, ensemble, Treatment A/B, training code |

`app/m1/frozen_model.py` verifies checkpoint/spec/source/environment hashes
before strict load, checks parameter count and reuses one eval-mode instance.
It invokes **unchanged** `app/ml/stethofuse_tcn.py::separate_recording` under
inference mode. Existing PCM decoder and `ensemble_v1.canonicalize` are reused
only for canonicalization: arithmetic-mean mono, gcd polyphase anti-aliased
resampling (Kaiser5.0, constant padding, ceil length), no new gain cap. Importing
the latter helper does not execute its historical ensemble/NMF runner. The API
process imports no ML dependency; the dedicated worker owns all model execution.

Whole-recording shared amplitude normalization/restoration, windowing and
zero/near-silent behavior remain the frozen implementation's behavior. Output
length equals the canonicalized recording length. v1/v2/spec/checkpoints remain
preserved; no v3 or new model was created.

## Minimal application delta

Existing `m1_jobs`, `m1_results`, `m1_files`, `m1_result_files`, recordings,
resources, grants and audit tables are reused. No parallel ProcessingJob/Result
schema, legacy unowned database adoption or new auth authority was introduced.
Versioned `002_processing.sql` adds operational/provenance/hash fields and a
unique recording/model index; startup migrates only a recognized M1v1 database
transactionally. Existing identity/profile/preference data survives locally.

```text
record/upload → protected original → owner request (202) → durable queued job
    → one locked CPU worker → verified frozen model → two private verified WAVs
    → atomic result/provenance + succeeded → authorized metadata/audio review
```

The HTTP request does not wait for inference. One worker uses an OS exclusive
lock beside the SQLite file plus `BEGIN IMMEDIATE` claims and claim tokens.
The second worker is denied. The same recording/model request returns the same
job, including failed/succeeded state. No uncontrolled duplicate queue entries.
Jobs survive API/worker exits; browser refresh/logout does not own their state.

State transitions are `queued → processing → succeeded | failed`. After an
interruption, the next exclusively locked worker removes only that unfinished
job's reserved outputs and retries once; a second interruption fails durably.
Committed results are not repeated. Ordinary input/inference/storage errors
fail immediately with safe category, stage and timestamps. No alternative
algorithm, infinite retry, automatic user retry or silently replaced output.

## Private storage and publication

Local tests use isolated temporary SQLite/private directories, never production
paths. Deployment preserves existing `/srv/stethofuse/data` and `/private`.
Original and generated files are immutable UUID artifacts, directory0700 and
files0600, with database identity/resource authorization. Original bytes remain
unchanged. Heart/lung outputs are canonical4-kHz mono **IEEE float32 WAV**, not
independently normalized/clipped PCM exports. Chrome played both15-second WAVs.

Files are staged at job-reserved `.wav.tmp` paths, flushed/fsynced, read back
and verified before non-replacing publication and directory fsync. A single
database transaction publishes both output links and the result, or neither.
A partial output-write failure leaves failed state, no result, and removes its
reserved outputs. Failed orphan cleanup is retried on startup. Ambiguous
finalization stops instead of risking deletion of committed results.

No private path is statically served. The same bearer-authorized media endpoint
handles originals and outputs, including GET/HEAD/ranges. No public or guessable
download capability is issued. Browser Blob URLs are released on exit/sign-out;
revocation prevents later requests, not recall of already downloaded bytes.

## API and provenance

| Purpose | Actual route |
| --- | --- |
| Record/capture upload | `POST /api/recordings` (same PCM WAV contract) |
| One separation action | `POST /api/recordings/{recording_id}/jobs` with `{}` →202 |
| Job status/history | `GET /api/jobs/{job_id}`, `GET /api/jobs` (owner-only) |
| Result metadata | `GET /api/results/{result_id}`, `GET /api/results` |
| Heart audio | `GET/HEAD /api/media/{heart_resource_id}` |
| Lung audio | `GET/HEAD /api/media/{lung_resource_id}` |
| Assigned review | `GET/PUT /api/assignments/{grant_id}/review` |

Job submission defaults off until explicit `STETHOFUSE_SEPARATION_ENABLED=1`;
disabled returns503 without creating a job. Successful result provenance stores:
model name/version/architecture/count, checkpoint/spec/code SHA, code-dirty flag,
input recording/artifact hash, original PCM metadata, canonical waveform hash,
preprocessing version/resampling/channel policy,4-kHz rate/sample count,
window/hop/overlap, amplitude/padding contract, semantic order, consistency
version, no projection/ensemble, CPU environment/runtime, worker version/attempt,
heart/lung artifact IDs and hashes, created/started/completed timestamps.
There are no credentials, filesystem paths or invented per-record quality scores.

## Frontend and authorization

Existing live pages/components were connected, not redesigned. Upload or browser
capture → metadata/original review → **Separate** → Queued/Processing/Ready/Failed
→ protected Heart/Lung players and Original recording link. Real API state polls
every2s while active; no timer-generated completion or guessed percentage.
Failure text retains the original and gives a safe job/error identifier.
Sampling rate/duration/runtime are technical metadata, not medical interpretation.
No normal-user algorithm selector, demographics, owl/asset/theme/CSS redesign.

Browser capture is now an actual AudioWorklet PCM path using the browser-selected
input, requests mono/no AGC/no echo/noise processing, previews before saving,
encodes PCM16 at device rate, and stops at120s or25MiB. It uses the same protected
upload/validation path. Browser constraints are best effort; this fake-microphone
acceptance is **not physical digital-stethoscope qualification**.

Firebase UID/current-account checks, application active-status/role/owner/grants
and audits remain authoritative. Owner-only processing cannot be requested by
an unrelated user, analyst or admin. Result review grants do not imply sibling
audio: the assigned analyst needs explicit read grants for outputs (or deliberate
whole-recording access). Non-assigned/revoked analysts and ungranted admins are
denied. Review/audit history remains. Audit events include requested, started,
succeeded, failed and interruption requeue, without private waveform details.

## Local acceptance and test scope

Only generated sinusoids/PCM and a fake browser microphone were used. Identities
are fictional/injected; model weights, API, SQLite, private storage and inference
are real. This does not constitute fresh Firebase/provider or production evidence.

| Acceptance case | Evidence / outcome |
| --- | --- |
| Owner request; outsider/admin/unassigned analyst denial; rapid202 | Focused API+worker pass; request0.0141s |
| Durable queued→claim→processing→succeeded | Real API/worker and browser pass |
| Frozen hashes, strict load,171313 parameters, one loaded instance | Focused pass, unchanged model/spec hashes |
| Two private WAV outputs; finite; correct length; mixture sum | 60000 samples each for15s; max sum error<1e-6 |
| Owner bytes; anonymous401; outsiders403; admin no privilege | Focused pass |
| Explicit analyst metadata/audio, original denied, review persistence | API+browser pass |
| Non-assigned and revoked analyst denial | API+browser pass; post-revocation requests403 |
| New API instance/session + browser refresh retains result | Pass; same persisted provenance/job |
| Missing/wrong-hash artifact refuses startup | Temporary invalid/missing paths pass; real checkpoint untouched |
| Inference and second-output write failure | Durable failed state, no result or orphan output |
| Interrupted claim, lock exclusion, bounded retry, no duplicate result | Pass; first interruption retried, second terminal |
| Existing DB migration and repeated startup | Pass; existing UID/profile/preferences preserved |
| Non4k stereo + zero input + model reuse | Exact existing canonicalizer match; finite correct shape; zero→zero |
| Upload and fake-microphone capture through live UI | Five browser acceptance groups pass, zero page errors |
| Broader authorization/account/admin/browser regression |137 cases +26 subtests resolved passing;14 browser groups pass |

Focused final clean-source run:5 passed in2.485s
(`.local/ml-integration/focused-clean-v1.xml`). Real browser acceptance:
5/5 passed (`frontend/output/playwright/ml-integration-clean-v1/results.json`),
with queued/processing/ready screenshots visually checked. Broader browser:
14/14 passed, zero runtime errors/external provider requests; includes390px
containment and preservation of approved owl presentation. TypeScript and Vite
production build passed. No broad ML/research test suite was run.

The single broader regression campaign's initial collection stopped because
the isolated worker/test environment lacked test-only PyJWT. After matching that
helper to the existing auth-test environment,130 cases +26 subtests passed and
7 harness issues remained:6 needed Firebase Admin SDK (absent intentionally from
the worker runtime) and1 checked global Python imports after worker tests had
legitimately imported torch. The import-isolation assertion was made in a fresh
API subprocess; all7 passed in the existing auth-test environment. No failing
product assertion was discarded. Earlier XMLs are retained. The first broader
browser attempt blocked its new localhost port with an old4180-only guard; the
guard now uses the configured origin, retaining external-request denial. Its
failed record is preserved, and all14 passed after correction. A known existing
Starlette/httpx deprecation warning is non-failing. These overlapping passes are
not added together as independent tests.

## Resource measurement (one local synthetic sample, not an SLA)

Ryzen5 9600X CPU, pinned environment above; no GPU. Final focused run recorded:

| Measure | Value |
| --- | ---: |
| Full worker startup (imports+hashes+load) |1.060927s |
| Loader/hash/model setup within startup |0.502485s |
|15-second inference |0.034600s |
| Whole claimed job including storage/persistence |0.048140s |
| Startup+job process CPU time |0.909384s |
| Process peak RSS (includes pytest/API harness) |560.914MiB |
| Model loads per worker instance |1 |

Measurements include local test overhead and may overlap other local checks;
they are not production-service latency, clinical evidence or a throughput SLA.
The conservative observed RSS fits the prepared2-GiB single-worker limit; actual
deployed workload/resource acceptance remains a release gate.

## Evidence receipts and deployment boundary

Compact receipts: [local integration JSON](evidence/local_ml_integration_v1.json).
Ignored raw logs/XML/screenshots stay at the paths below; generated private
fixture databases/audio are automatically disposed, not committed.

| Evidence | SHA-256 |
| --- | --- |
| `.local/ml-integration/focused-clean-v1.xml` | `666f8d0ff2711eda4b0e43eab0ff0f077824eb782461a509a1a68ef8dfd9494c` |
| `.local/ml-integration/application-regression-v2.xml` (130 pass/7 harness failures) | `b6f51b48a443e25ccf4ec9857c666a31eba48d4fbcb80acd30d95a304253b786` |
| `.local/ml-integration/application-regression-followup.xml` (7 pass) | `ebc87a35193768f3e10a54c3c7e68c6b30d291c9ef2fe8d34257d0443f55869e` |
| `frontend/output/playwright/ml-integration-clean-v1/results.json` | `cd25cae737feab99315573f1e8765372819b21e0289ed187354463d65e67b3af` |
| `frontend/output/playwright/ml-regression-v2/results.json` | `601c72b97c89693dfe87c10f984bbed8c0e7290d3502e1163d0c16d43bd16a1d` |

[Deployment-review runbook](../deploy/ML_WORKER_RUNBOOK.md) prepares the private
model path/permissions, locked environment, opt-in Compose worker, v1→v2 DB
migration, service lifecycle, rollback and all-writer backup quiescence.
Output/database paths are already backed up; immutable model-bundle off-host
retention is an explicit prerequisite not covered by current backup scope.
Shell syntax and isolated Compose configuration validation passed. The first
worker-image build found the older `.dockerignore` allow-list excluded frozen
dependencies/migration; packaging commit2b6b3c0 fixes only that build context.
The corrected image built successfully and reached worker `ready` with strict
model loading, no network, read-only root,2GiB/2CPU, UID10001 and temporary state
only. Image ID and0.411703s loader measurement are in the compact receipt. A
first smoke used host UID1000, absent from the container passwd file; the test
was repeated with the image's intended UID10001, without source/model changes.
The smoke container was removed; its temporary empty database was disposable.
No production image tag/service/config/database/backup was modified.

## ML/FYP evidence remains separate

[T9 final report](T9_FINAL_HELDOUT_EVALUATION.md) and its tracked JSON remain
unchanged. Controlled held-out225-condition results (SI-SDR / SI-SDRi dB):

| Method | Heart | Lung | Failures |
| --- | --- | --- | ---: |
| Mixture |−0.037 /0.000 |−0.037 /0.000 |0 |
| Fixed Filter |0.325 /0.362 |−2.484 /−2.447 |0 |
| Generic NMF |−2.503 /−2.466 |−3.444 /−3.407 |0 |
| Frozen Conv-TasNet v2 |1.813 /1.849 |2.296 /2.333 |0 |

Both final source improvements were positive and exceeded these two comparators
under that frozen protocol only. Manikin domain, two independent test family
pairs, synthetic mixtures, modest improvement and difficult extreme levels
limit interpretation. No diagnostic/clinical/patient-level effectiveness claim.
External pretraining and native supervision negative transfer remain recorded;
TreatmentA remains promising non-test research, not selected/not T9-evaluated.
Its8/8 pair and5/5 fold improvements missed the unmodified +0.50dB gates.

This document preserves the local integration checkpoint. Production deployment
and live acceptance were completed later; see
[`PRODUCTION_ML_ACCEPTANCE_2026-09-29.md`](PRODUCTION_ML_ACCEPTANCE_2026-09-29.md).
No T9 rerun/audio access, model research, frontend visual-system redesign or
Axora change occurred in that later production acceptance.
