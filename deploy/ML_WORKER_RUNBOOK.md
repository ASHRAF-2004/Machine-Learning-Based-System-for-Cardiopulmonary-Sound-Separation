# Frozen separator worker — deployment review only

**IMPLEMENTED LOCALLY / TESTED LOCALLY / NOT DEPLOYED.** Do not execute the
production steps below without separate owner authorization. No model training,
T9 access, provider redesign, new listener, Caddy reload or Cloudflare change is
part of this release. Existing production M1 and Axora remain untouched.

## Immutable artifact and environment

Model ID: `stethofuse-tcn-small-hls-refit-waveform-v2`, Conv-TasNet N64/B32/H64,
171,313 parameters. Load once at worker startup, strict state dict, eval and
inference mode, CPU, two intra-op threads / one inter-op thread. No fallback.

| Artifact | Required SHA-256 |
| --- | --- |
| `endpoint.pt` | `1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658` |
| `final_separator_v2.json` | `2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b` |

Python 3.14.4, torch/torchaudio 2.11.0+cpu, NumPy 2.4.4, SciPy 1.17.0 are
mandatory. `requirements-worker.lock.txt` pins/hashes the complete worker
environment; `Dockerfile.worker` uses the existing digest-pinned Python base.
The API image remains free of ML dependencies. No GPU, new driver or runtime
download is required. Worker startup checks the two artifact hashes, frozen
inference/preprocessing source hashes, environment and exact parameter count.
Missing/corrupt artifacts refuse startup before any claim or output generation.

Approved deployment bundle (not created on the server in this milestone):

```text
/srv/stethofuse/models/stethofuse-tcn-small-hls-refit-waveform-v2/
  endpoint.pt
  final_separator_v2.json
  SHA256SUMS
```

Use root owner, configured API/worker group (default GID 10001), directories
0750 and immutable bundle files 0440. The model root is read-only in the worker
and is never mounted by web/API or exposed over HTTP. Copy from the preserved
local checkpoint and frozen tracked specification; do not modify the originals.
Record an operator receipt with both hashes. Verify with `sha256sum` on each
complete file, then `sha256sum --check SHA256SUMS` from the bundle. A mismatch
stops deployment; never edit a constant or spec to accommodate another file.

## Existing persistence and migration

`/srv/stethofuse/data/m1.sqlite3` and `/srv/stethofuse/private` remain the only
mutable job/result/media storage. Both directories belong to the configured
API UID/GID (default 10001:10001), mode0700, files0600. Original files are never
replaced. Output UUIDs are reserved when a job is requested; filenames are not
authorization. Database resource records and existing grants are authoritative.

`app/m1/migrations/002_processing.sql` adds provenance, claim/recovery fields,
artifact hashes and a unique recording/model index to the existing tables.
M1 startup runs it once under `BEGIN IMMEDIATE`; fresh databases follow the same
v1→v2 route. No manual production SQL. The local migration test preserves an
existing UID/profile/preferences and verifies repeated startup. Before a real
release, back up the stopped database/private directory as one consistent set.
Schema rollback is **not** an automatic downgrade: old code rejects v2. Restore
the matching pre-migration backup and old image set if needed, after preserving
any post-release user data. Never drop columns/tables to force a rollback.

## Worker lifecycle and failure policy

`POST /api/recordings/{id}/jobs` authorizes the owner and returns202 promptly.
One job per immutable recording/model is reused even after success/failure.
The browser polls real state; closing it does not cancel the job. Enabling job
submission is explicit (`STETHOFUSE_SEPARATION_ENABLED=1`); default remains off.

One `python -m app.m1.worker` process holds an OS exclusive lock next to the
database for its entire lifetime. A second worker fails closed before loading
weights. SQLite `BEGIN IMMEDIATE` claims the oldest queued job and increments
attempts; a unique claim token protects finalization. No in-memory queue,
network broker, distributed filesystem or horizontal scaling is supported.

States: `queued → processing → succeeded | failed`. Claim and completion check
the active owner. SIGTERM finishes the current job; service stop grace is60s.
On restart after a crash, the released kernel lock proves the prior worker is
gone. Reserved partial outputs are removed; an unfinished first attempt is
requeued exactly once. A second interruption becomes `worker_interrupted`.
Already committed results are not duplicated or deleted. Ordinary inference,
input-integrity or output-storage errors become failed immediately, not an
automatic retry loop. The owner sees a safe error category/stage; no raw
exception, private path or alternative algorithm. Operational repair/retry
requires a separately reviewed action; no public force-retry endpoint exists.

Each output is written to its own mode0600 temporary WAV, flushed/fsynced,
read back and checked for sample identity/finite values. Publication uses
non-replacing links and directory fsync. Only after BOTH outputs verify does
one database transaction create protected result/audio resources, link their
hashes/provenance and commit succeeded. Failed/aborted jobs publish no result.
Cleanup only touches that job's four reserved temporary/final paths. Ambiguous
finalization stops the worker rather than deleting potentially committed audio.

## Local execution

Use an isolated M1 database/private directory and fictional test identities for
acceptance, not `/srv/stethofuse` and not production Firebase records. Set:

```text
STETHOFUSE_M1_DATABASE=<absolute isolated SQLite path>
STETHOFUSE_M1_PRIVATE_STORAGE=<absolute isolated private directory>
STETHOFUSE_SEPARATION_ENABLED=1                 # API only
STETHOFUSE_MODEL_CHECKPOINT=<absolute preserved endpoint.pt>
STETHOFUSE_SEPARATOR_SPEC=<absolute final_separator_v2.json>
```

Start the existing local API separately, then the worker in the pinned CPU
environment: `python -m app.m1.worker`. `--once` claims at most one job for
bounded operator/synthetic acceptance. No command invokes a training or
evaluation runner. Local Git provenance reports HEAD and worktree-dirty state;
container provenance uses the reviewed build's `STETHOFUSE_CODE_GIT_SHA`.

## Prepared production service (NOT activated)

The existing service manager is Docker Compose, not a new systemd ML service.
`compose.ml.yaml` is an explicit third override alongside the base and Firebase
files. It adds one worker with restart-unless-stopped, network disabled,
read-only root, non-root UID, dropped capabilities, no-new-privileges, bounded
logs, 2 CPU / 2GiB limit,64 PIDs and64MiB temporary filesystem. There is no
worker port. It shares only the existing data/private mounts plus the read-only
model bundle. Do not scale replicas; the host-local lock deliberately rejects it.

After owner review, a deployment operator must:

1. Verify clean reviewed code/remote SHA and preserved artifact hashes. Record
   the existing running image IDs and a maintenance/rollback plan.
2. Take a consistent existing backup without extending this task into a drill.
   Prepare the model bundle/permissions and encrypted off-host artifact retention.
3. Set `STETHOFUSE_CODE_GIT_SHA` in the owner-only runtime environment to the
   reviewed implementation commit. Preserve every existing Firebase setting.
4. Validate merged Compose with the existing runtime env and all three files:
   `compose.yaml`, `compose.firebase.yaml`, `compose.ml.yaml`. Build the reviewed
   API/frontend/worker images; do not use a dirty source tree or arbitrary SHA.
5. Stop affected StethoFuse writers for the migration, then start the reviewed
   stack. Do not touch Axora, routing, DNS, certificates or provider setup.
6. Require worker `ready` (hash/strict-load checks have passed), API health and
   one worker instance. Test only a new authorized synthetic/dev recording,
   owner/unauthorized output access and persisted result provenance. Never T9.
7. Update backup configuration and receipt, then seek owner release acceptance.
   If startup fails, stop job submission; do not substitute another checkpoint.

These are instructions, not evidence of production execution. Deployment
approval, production image rollout, migration, service activation and live
generated-output acceptance remain outstanding.

## Backup impact

Generated outputs already live under the existing Restic `private` scope, and
jobs/results/provenance under `data`; no new user-data path is omitted. The
prepared backup script's `STETHOFUSE_ML_WORKER_ENABLED=1` option also stops and
restarts `ml-worker` with web/API, so all writers are quiescent. Default remains0
and the production configuration was not changed. The runtime env must include
the reviewed code SHA before this option is enabled. A running worker check is
not a model-health proof; verify its ready log and queue/error state operationally.

The immutable `models` bundle is **outside the existing backup scope**. Before
deployment, retain a verified encrypted off-host copy (checkpoint+spec+receipt)
or explicitly approve adding that path to backup/restore tooling. A restored
database/private snapshot is not a complete ML service without the matching
model bundle and reviewed code image. No Restic/B2 snapshot/drill, credential
change, pruning or production backup reconfiguration ran in this milestone.
