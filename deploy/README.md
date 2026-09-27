# StethoFuse production-like runtime

## Current Firebase auth configuration — 27 September 2026

This section supersedes earlier Cloud Run verifier instructions in this file.
FastAPI locally validates the Firebase ID-token signature and claims, then calls
Firebase Authentication REST `accounts:lookup` over HTTPS with that same user
token and a dedicated Firebase Web API key restricted to
`identitytoolkit.googleapis.com`. The current-user record must contain the same
UID, an enabled account, verified email, and a `validSince` boundary not newer
than token `iat` (both seconds). Invalid/deleted/revoked/disabled identity is
denied; malformed responses and upstream failures return unavailable and fail
closed. Local StethoFuse account status/role/ownership/grants remain the
authorization authority. No Google ADC, service-account credential or Cloud Run
dependency is used. The project does not need Google Cloud billing for this
Firebase REST check.

The auto-created browser key is not reused by the server: inspection found it
permitted numerous unrelated APIs. A separate key `StethoFuse server Firebase
Auth lookup` was created with only `identitytoolkit.googleapis.com` as its API
target and verified against that API. Its value is stored only in the ignored,
owner-only local file `.local/firebase-auth-rest-api-key`; do not copy it into
Git, browser assets, logs or chat. Provision the same restricted key into the
external runtime environment as `STETHOFUSE_FIREBASE_API_KEY`. No Google Cloud
billing was enabled. The earlier Cloud Run verifier source/runbook is retained
as superseded history and is not part of the active runtime.

This package builds the current authenticated M1 application into an isolated
Docker Compose stack. It is a **local production-like validation package**, not
an applied production deployment. It does not join or modify Axora's networks,
containers, Caddy configuration, Cloudflare tunnel, or DNS.

## Included and not included

- React/Vite static frontend served by Caddy on container port 8080.
- Same-origin `/api`, `/health`, and `/static/*` reverse proxy to FastAPI.
- FastAPI with local Firebase ID-token signature/claim verification, Firebase Auth
  REST current-account/revocation checking, and trusted local M1 authorization.
- Separate persistent SQLite and private-file bind mounts; neither is exposed by
  the web container or served from the public frontend directory.
- Non-root processes, read-only container roots, dropped capabilities, resource
  limits, health checks, restart policies and bounded container logs.
- Digest-pinned base images and hash-pinned Python runtime dependencies.

The current M1 API explicitly reports `ensemble_available: false`; separation
job submission returns unavailable. There is no production worker, queue,
ensemble service, GPU scheduling, or connected model execution in this package.
Existing ML and benchmark code is preserved in the repository but is not copied
into these runtime images. Do not treat the demo output or old baselines as a
deployed separation service.

## Prerequisites and configuration

Use Docker Engine with Compose v2 and BuildKit. Make a private runtime directory
outside the repository/web root. Copy `.env.example` to an owner-only file at an
external path (for example `/etc/stethofuse/runtime.env`) and set its permissions
to `0600`. Fill in the selected Firebase Web App's public client configuration;
the production Vite build fails if any required browser configuration is absent.
Those Firebase Web SDK values are public client configuration, not Admin
credentials.

The API runtime does not use Google ADC or a Firebase Admin credential. It verifies
ID-token signatures locally against Google's public Firebase signing certificates and
validates Firebase's project, issuer, time and subject claims. On each request it calls
the Firebase Auth REST `accounts:lookup` endpoint with the same token, checks the
current UID, disabled flag, verified-email state and `validSince` revocation boundary,
and fails closed on invalid responses or upstream failure. The server-specific Web API
key is API-restricted to Identity Toolkit. Do not mount developer ADC or a service
account credential into this runtime.

The trusted first-admin CLI is separate and operator-only. It may use a separately
authorized local ADC session when explicitly invoked for that action; never place that
credential in the API container, production environment, image or backup.

Prepare empty persistent paths owned by the configured API UID/GID, with private
storage mode `0700` and data directory mode `0700`; do not put them beneath
`frontend/public`, Caddy's `/srv`, or the repository. For the default UID/GID:

```sh
sudo install -d -o root -g root -m 0750 /srv/stethofuse
sudo install -d -o 10001 -g 10001 -m 0700 /srv/stethofuse/data /srv/stethofuse/private
```

Create the first database using the application startup path; do not import or
auto-migrate legacy databases. Preserve existing uploads and DBs before changing
schema or image version.

## Build and run locally

The Firebase-enabled invocation requires `STETHOFUSE_FIREBASE_API_KEY` and the Firebase
Web App settings in the external env file. Missing Web App settings fail the frontend
image build; a missing server API key fails Compose configuration, and an unavailable
Firebase Auth endpoint fails API authorization closed. Do not insert a placeholder key
for a real-provider check.

```sh
docker compose \
  --project-name stethofuse-production \
  --env-file /etc/stethofuse/runtime.env \
  -f deploy/compose.yaml \
  -f deploy/compose.firebase.yaml \
  config --quiet

docker compose \
  --project-name stethofuse-production \
  --env-file /etc/stethofuse/runtime.env \
  -f deploy/compose.yaml \
  -f deploy/compose.firebase.yaml \
  build

docker compose \
  --project-name stethofuse-production \
  --env-file /etc/stethofuse/runtime.env \
  -f deploy/compose.yaml \
  -f deploy/compose.firebase.yaml \
  up -d
```

The default published listener is `127.0.0.1:8088`; no API port is published.
The reverse proxy is the only web entrypoint. Verify locally before any
production routing work:

```sh
curl --fail http://127.0.0.1:8088/health
curl --fail http://127.0.0.1:8088/api/health
curl -i http://127.0.0.1:8088/api/auth/me       # 401 without a Firebase token
curl -i http://127.0.0.1:8088/api/admin/users   # 401 without a Firebase token
docker compose --env-file /etc/stethofuse/runtime.env \
  --project-name stethofuse-production \
  -f deploy/compose.yaml -f deploy/compose.firebase.yaml ps
```

Expected API health contains `storage_configured: true`,
`provider_configured: true`, and `ensemble_available: false`. Never pass an ID
token on the command line or save it in a shell history. Authenticated role and
private-media acceptance should use the normal browser/local-provider procedure,
not a token copied into a deployment smoke script.

To stop without deleting data, run the same Compose command with `stop`. Do not
use `down -v`; persistent bind-mounted data is user data.

## Local production-like smoke evidence

On 27 September 2026, before replacing runtime ADC with the Cloud Run identity
boundary, both images built locally and the isolated Compose stack was exercised
with the existing local development ADC (not production credentials) and synthetic-only
data. Those results remain historical package evidence; the updated verifier/API image
and current real-provider path require targeted revalidation. Results at that earlier
checkpoint:

- frontend `/` and SPA route `/app/admin/users`: HTTP 200;
- same-origin `/api/health`: `ok`, storage/provider configured, ensemble false;
- tokenless `/api/auth/me`, `/api/admin/users`, and `/api/media/{id}`: HTTP 401;
- guessed `/private/...` URL returned the SPA document, not a private file;
- API SQLite record and synthetic private marker survived container restart;
- web container had no private-storage bind mount and API port was not host-published.

Current boundary validation (27 September 2026): verifier and API images built from
hash-locked dependencies; the verifier image was rebuilt after the production emulator
guard. A credential-free API container with networking disabled returned health 200,
401 for protected endpoints without tokens, and 401 for a malformed token. Compose
interpolation passed with a placeholder service URL. There were 42 focused verifier /
manifest tests and 91 M1/access/operator regression tests plus 26 subtests passing.
The initial broader attempt lacked the already-locked upload parser in its temporary
environment and used a stale bootstrap mock name; both were corrected. No live Cloud
Run or B2 acceptance was performed. Exactly two test functions (four parameterized
executions) were added in this final sprint, reusing the preceding work's tests.

This is local packaging evidence, not a production deployment, live user
acceptance, real media authorization test, backup disaster-recovery proof, or
ensemble evaluation. The M1 real-provider authorization evidence is separately
recorded in FYP2 notes.

## Backup and restore

The approved off-host target is **Backblaze B2 via Restic's S3-compatible backend**.
The owner-created private bucket `stethofuse-prod-backup-927f5b7d` is in EU Central
at `s3.eu-central-003.backblazeb2.com`. Restic `0.18.1` initialized the repository
and passed a synthetic encrypted remote backup/restore drill (2026-09-27): repository
check had no errors; restored SQLite returned `integrity_check=ok`; SHA-256 manifest,
exact file sets and byte comparisons passed. The owner then independently entered
the offline paper-copy password; it unlocked the repository and restored the known
synthetic file with the expected SHA-256. This is **not** production deployment,
a scheduled backup, or a live-application restore. `/srv` and `/var/backups` remain same-host copies,
not disk-loss protection. Review the region if formal data-residency obligations arise.
The workspace decision record is `planning/PRODUCTION_IDENTITY_AND_BACKUP.md`.

`backup-restic.sh`, `backup-manifest.py`, `backup-restore-drill.sh`, `backup.env.example`, and the example systemd
service/timer are prepared deployment files, not an installed/verified scheduled production job.
The helper receives the bucket-scoped B2 S3 key ID, secret, and separate Restic
password through systemd's private credential mechanism from root-only source files.
Do not place either value in Git,
Compose images, shell history, or chat. Keep the Restic encryption password in
an independently recoverable offline password manager/escrow; losing it makes
the encrypted repository unrecoverable. Keep B2 key material separate from
the encryption secret. The environment file and runtime data are included
inside Restic's encrypted snapshots; B2 and Restic credentials are not.

After production deployment is approved, install the helper outside
the checkout and run it under a dedicated root-owned systemd oneshot/timer. The
remote repository already exists. The helper refuses non-B2/local targets and
requires one healthy API and web container before stopping the pair for a
consistent SQLite and media snapshot. It attempts to bring them back even if
the backup fails. It backs up only the persistent database, private original/result files, runtime
environment and an encrypted snapshot's SHA-256 file manifest; image layers,
caches, build outputs, and developer ADC are excluded. The prepared retention
policy is 7 daily, 4 weekly, and 6 monthly. No production snapshots exist and no
prune was run. The helper skips `forget --prune` until a root-owned
`/etc/stethofuse/remote-restore-verified` marker is installed after reviewing the
successful synthetic remote restore evidence and approving scheduled production
backup setup. The drill did not create this marker or enable a timer.

For a recovery drill, restore a named snapshot into a **new empty staging
directory**, never over the active runtime. Check `PRAGMA integrity_check` on
the restored SQLite file, verify manifest/file hashes and ownership/modes,
start the matching image against staged copies, and perform health plus
authorized synthetic-media checks before any root switch. Periodically run
`restic check`; at least quarterly perform a full isolated restore. See
[`BACKUP_B2_RUNBOOK.md`](BACKUP_B2_RUNBOOK.md) for current evidence, secure
credential handling and operational steps. No B2 credentials are to be sent in
Git or chat.

## Rollback

Keep the prior image digest, runtime env file, verifier URL/revision, and data root. For an
application-only rollback, stop the new Compose stack and start the previously
recorded image with the same verified configuration and compatible database
schema. Do not roll back a schema change by overwriting the active DB: take a
fresh backup, restore into a new staging root, and validate before switching.
Production config changes require a separate reviewed backup and rollback for
the tunnel, proxy, and DNS records; this repository package does not apply them.

## Future separation worker / GPU path

The Compose network is isolated and can later host a separate authenticated
worker service, but no worker is included now. Before adding one, define durable
job state, idempotency, cancellation, resource limits, provenance, retry policy,
private result storage, API authorization and evaluation correspondence. GPU
access should be an explicit host-specific Compose override after verifying the
server's driver/runtime; CPU service startup does not depend on GPU support.
