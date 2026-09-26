# StethoFuse production-like runtime

This package builds the current authenticated M1 application into an isolated
Docker Compose stack. It is a **local production-like validation package**, not
an applied production deployment. It does not join or modify Axora's networks,
containers, Caddy configuration, Cloudflare tunnel, or DNS.

## Included and not included

- React/Vite static frontend served by Caddy on container port 8080.
- Same-origin `/api`, `/health`, and `/static/*` reverse proxy to FastAPI.
- FastAPI with Firebase Admin ID-token verification and trusted M1 authorization.
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

The API needs Firebase Admin Application Default Credentials (ADC) for the
selected project. Use a dedicated, least-privilege production identity and a
secure host credential mechanism. Do not copy developer ADC, CLI state, service
account keys, or tokens from a workstation into production. The Firebase overlay
mounts the selected ADC file read-only outside the image. Never commit that file.
With the default runtime UID/GID, ensure the credential file is readable only by
UID 10001 (for example owner `10001`, mode `0400`) and its parent directories are
not writable by the application; grant host-operator access separately. The
production identity/source-credential mechanism itself remains to be provisioned
and reviewed.

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

The Firebase-enabled invocation requires the ADC file path and Firebase web
settings in the external env file. Missing Web App settings fail the frontend
image build; missing ADC path fails Compose configuration, and unreadable/invalid
ADC or unavailable provider fails API startup/health rather than granting access.

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

On 27 September 2026, both images built locally and the isolated Compose stack
was exercised with the existing local development ADC (not production
credentials) and synthetic-only data. Results:

- frontend `/` and SPA route `/app/admin/users`: HTTP 200;
- same-origin `/api/health`: `ok`, storage/provider configured, ensemble false;
- tokenless `/api/auth/me`, `/api/admin/users`, and `/api/media/{id}`: HTTP 401;
- guessed `/private/...` URL returned the SPA document, not a private file;
- API SQLite record and synthetic private marker survived container restart;
- web container had no private-storage bind mount and API port was not host-published.

This is local packaging evidence, not a production deployment, live user
acceptance, real media authorization test, backup disaster-recovery proof, or
ensemble evaluation. The M1 real-provider authorization evidence is separately
recorded in FYP2 notes.

## Backup and restore

The production backup target is **not provisioned yet**. Host discovery found
no remote filesystem, configured object-store client, or StethoFuse backup
repository. `/srv`, `/var/backups`, and the workspace share the host's root
storage; those are local rollback copies, not disaster-recovery backups. The
prepared default is Restic to a private Backblaze B2 bucket through its
S3-compatible endpoint. Restic encrypts/authenticates repository contents on
the client before upload. B2's published price is currently $6.95/TB per 30
days, with the first 10 GB free and egress allowances; exact charges depend on
the stored data, region, and restore volume. B2 currently offers US East, US
West, EU Central and Canada East regions, not an Asia region, so the selected
region and institutional/privacy suitability must be considered before
creating the bucket. No account, bucket, key, paid resource, or backup has been
created. The workspace-level decision record is `planning/PRODUCTION_IDENTITY_AND_BACKUP.md`.

`backup-restic.sh`, `backup.env.example`, and the example systemd service/timer
are prepared deployment files, not an installed/verified production job. The
helper requires the future bucket-scoped B2 S3 key from a root-only systemd
environment file and the Restic password delivered to the service through
systemd's private credential mechanism from a separate root-only source file.
Do not place either value in Git,
Compose images, shell history, or chat. Keep the Restic encryption password in
an independently recoverable offline password manager/escrow; losing it makes
the encrypted repository unrecoverable. Keep B2 key material separate from
the encryption secret. The environment file and runtime data are included
inside Restic's encrypted snapshots; B2 and Restic credentials are not.

After the destination is approved and provisioned, install the helper outside
the checkout, create the private repository once, and run it under a dedicated
root-owned systemd oneshot/timer. The helper refuses non-B2/local targets and
requires one healthy API and web container before stopping the pair for a
consistent SQLite and media snapshot. It attempts to bring them back even if
the backup fails. It backs up only the persistent database, private original/result files, runtime
environment and an encrypted snapshot's SHA-256 file manifest; image layers,
caches, build outputs, and developer ADC are excluded. Choose a retention
policy and repository maintenance schedule only after estimating actual data
volume, privacy requirements and restore needs; do not prune snapshots before
that policy is approved.

For a recovery drill, restore a named snapshot into a **new empty staging
directory**, never over the active runtime. Check `PRAGMA integrity_check` on
the restored SQLite file, verify manifest/file hashes and ownership/modes,
start the matching image against staged copies, and perform health plus
authorized synthetic-media checks before any root switch. Periodically run
`restic check`; at least quarterly perform a full isolated restore. A local
synthetic tar/copy test is not an off-host backup or restore proof. The actual
encrypted off-host restore remains blocked until an approved remote bucket and
key exist.

## Rollback

Keep the prior image digest, runtime env file, ADC source, and data root. For an
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
