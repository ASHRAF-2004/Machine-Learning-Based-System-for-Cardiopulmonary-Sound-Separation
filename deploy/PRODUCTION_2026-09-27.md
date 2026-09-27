# Production deployment receipt — 27 September 2026

**DEPLOYED; the checks explicitly listed below are VERIFIED LIVE.** This receipt
supersedes earlier planned/not-deployed snapshots. Public M1 application:
https://stethofuse.ashraf-alsaloul.com . No Cloud Run, Artifact Registry, production
Google service identity/custom role, service-account key or billing change was made.

## Installed release and boundaries

- Application source: `921c40d0e5a9672d3917d98aea6d8802ec1d1b92`, exported without
  Git/private workspace files to `/opt/stethofuse/releases/921c40d`.
  `/opt/stethofuse/deploy` points to that release's `deploy` directory.
- Compose project `stethofuse-production`; containers
  `stethofuse-production-web-1` and `stethofuse-production-api-1`, both healthy.
  Separate Docker network; no Axora membership or modification.
- Web image alias `stethofuse/web:921c40d`, image ID
  `sha256:95396f18a12bb79474a4f7102f118e65003a94b46c459541b8ae93cd3c1d0f40`;
  API alias `stethofuse/api:921c40d`, image ID
  `sha256:a46612da4ddbeba67b1104e6290b99e44f927fc44c101b1f30706bdbe1afd716`.
  Compose currently references the matching local image tags; do not rebuild or
  replace these tags during rollback without recording the intended image IDs.
- Caddy publishes only `127.0.0.1:8088` to container `8080`. FastAPI `8000` is
  internal, with no host port publication. Caddy serves the static SPA and
  proxies `/api`, `/health`, `/static/*` to the protected API.
- Persistent paths `/srv/stethofuse/data` and `/srv/stethofuse/private` belong
  to UID/GID `10001`, directories `0700`, files `0600`. The web container mounts
  neither. Runtime configuration is `/etc/stethofuse/runtime.env`, root `0600`.
- Initial production SQLite state was made with SQLite's backup API from the
  existing M1 development database, preserving its two verified accounts/roles
  and two explicitly synthetic fixtures. Private files were copied separately
  while development writes were quiesced. Originals remain intact. This is not
  a legacy migration, a repeated bootstrap, or patient-data collection.
- Identity is **local Firebase JWT validation → HTTPS Firebase Auth REST
  `accounts:lookup` using the same token → UID/current-state/revocation checks →
  local account/status/role/owner/grant authorization**. The server key permits
  Identity Toolkit only. No developer ADC is mounted in the runtime.

## Edge and Firebase configuration

- Dedicated remotely-managed Cloudflare tunnel `stethofuse-production`:
  `5677e02c-89a9-4e40-8bee-3b3f0d13dc8b`, healthy, configuration version `1`.
  Only ingress is the StethoFuse hostname → `http://127.0.0.1:8088`, then a
  catch-all `http_status:404`.
- Proxied CNAME record `094b8b7393932d2ad6dc1ae443bfa747` points the hostname to
  `5677e02c-89a9-4e40-8bee-3b3f0d13dc8b.cfargotunnel.com` (automatic TTL).
- A final plain-HTTP check initially returned 200. A hostname-scoped Cloudflare
  Single Redirect was added, without changing zone-wide settings: ruleset
  `98bafe245d2740de83b3dc4ac8bbad03`, rule `b9567f6717d24687b2c06f30290ec79c`,
  matching `(http.host eq "stethofuse.ashraf-alsaloul.com" and not ssl)`.
  It redirects to the same hostname/path over HTTPS with 308, preserving the
  query string. No existing redirect-phase ruleset existed; other managed
  rulesets were preserved. Configuration follows the official
  [Single Redirect API](https://developers.cloudflare.com/rules/url-forwarding/single-redirects/create-api/).
  After edge propagation, `/app/admin/users?probe=https` returned 308 with the
  exact HTTPS path/query; HTTPS health and Axora still returned 200.
- `cloudflared-stethofuse.service` enabled/active, dedicated unprivileged
  `stethofuse-tunnel` account. Its root-only token source is
  `/etc/cloudflared/stethofuse-production.token` (`0400`), delivered with systemd
  `LoadCredential`; metrics/readiness listen on `127.0.0.1:20243` only. The
  token was never printed or committed. See the matching service example.
- Firebase authorized domains now include `stethofuse.ashraf-alsaloul.com`.
  Existing `stethofuse-c18cd-3cca0.firebaseapp.com` authDomain, Google provider,
  sign-in configuration and callback behavior were preserved. No new project.
- Axora tunnel `axora-production`, version `1`, still has only
  `axora.management → http://caddy:8080`. Its containers remained healthy and
  public HTTPS returned `200`; no Axora DNS, routes, configuration or service
  restart was performed.

## Observed production acceptance

Normal external Google Chrome was used, not embedded-browser authentication.
Real Firebase tokens were used transiently for requests, never printed or
persisted in evidence. No real account was disabled/revoked for testing.

| Check | Observed result / classification |
| --- | --- |
| DNS, HTTPS, SPA, nested-route refresh | Public HTTPS `200`, TLS certificate verification successful; Admin Users direct refresh loads its Users heading. **PRODUCTION** |
| Same-origin health | `200`, storage/provider configured, `ensemble_available=false`. **PRODUCTION** |
| Verified primary Google Administrator | `/api/auth/me` `200`, matching Firebase UID and active local `admin`; `/api/admin/users` `200`. **PRODUCTION + REAL FIREBASE** |
| Verified ordinary Google Staff | `/api/auth/me` `200`, matching UID and `healthcare_staff`; Admin API `403`, direct Admin navigation `/403`. **PRODUCTION + REAL FIREBASE** |
| Owner's synthetic recording | Metadata/media/download `200`; media SHA-256 matches the stored synthetic file. **PRODUCTION + REAL FIREBASE** |
| Staff accesses Admin-owned fixture | Metadata/media/download `403`. **PRODUCTION + REAL FIREBASE** |
| Admin accesses Staff-owned fixture | Metadata/media/download `403`; admin does not bypass ownership. **PRODUCTION + REAL FIREBASE** |
| Anonymous private media / malformed token | `401`; guessed private-storage path is an HTML SPA fallback, not file bytes. **PRODUCTION** |
| Restart persistence | API container restart preserved two accounts, their roles/status, two recordings/owners and both private-file hashes; SQLite integrity `ok`; API healthy. **PRODUCTION** |
| Container logs | Scan found no server API-key value, JWT-shaped value or Authorization/Bearer header. **PRODUCTION**, bounded to observed logs |
| Disabled/revoked/upstream-malformed behavior | Existing **MOCK** boundary evidence, not live account mutation. The focused optional-boolean fix passed 13 REST cases; no broad suite rerun. |

Share/revoke evidence remains **REAL FIREBASE + LOCAL BACKEND** from the earlier
controlled test; it was not repeated/relabelled as production. Email/password,
recovery emails, real Analyst acceptance and derived separation outputs remain
untested. Ensemble execution/worker/GPU integration is not deployed. No clinical
use, participant evaluation, production penetration test or availability guarantee
is implied by these bounded checks.

## Post-deployment action-link acceptance

On 27 September 2026, a bounded check in separate tabs of normal external Chrome
verified a missing reset link and deliberately invalid reset/verification codes.
Both invalid-code requests reached real Firebase and returned HTTP400
`INVALID_OOB_CODE`; the UI showed “This link cannot be used”, removed the query,
did not render the supplied code, and offered no reset-password form. Zero
verification/reset emails were requested. These are **PRODUCTION + REAL FIREBASE**
invalid-code checks; the missing-code case is **PRODUCTION UI** only. They do not
prove successful email/password, mailbox delivery, reset completion, or expiry.
No existing account/session was changed, and no new automated test suite was added.

The next owner-gated step is one designated test mailbox, separate from the two
Google accounts. The owner enters credentials and opens emails directly in the
normal browser. A subsequently verified account can also serve as the explicitly
designated Analyst test identity; no promotion occurs merely from a chosen email.

## First production backup and schedule

- Restic `0.18.1`, private B2 bucket `stethofuse-prod-backup-927f5b7d`, EU Central,
  S3 endpoint `s3.eu-central-003.backblazeb2.com`, repository prefix `restic`.
- First production snapshot:
  `e0772dc0f83823e7d04b692ab0f54031f3fd8731bba811340de964383dca1df4`,
  `2026-09-27T12:50:24+08:00`, host `stethofuse-production`, tags
  `stethofuse,production`. Encrypted remote snapshot metadata was independently
  retrieved after the successful systemd job.
- Five files / 145.326 KiB processed: SQLite state, two synthetic private files,
  runtime configuration and SHA-256 manifest. B2/Restic secrets, Git, image layers,
  developer credentials and Axora data are excluded. Configuration is inside
  client-side encrypted Restic, not a plaintext remote archive.
- Helpers installed under `/usr/local/libexec/stethofuse/`; backup service/timer
  under `/etc/systemd/system`. Separate B2 key ID/secret and Restic password are
  root `0400`, delivered with systemd credentials. `backup.env` is root `0600`.
- Timer enabled: daily `03:15` Asia/Kuala_Lumpur plus up to 45 minutes jitter.
  The consistent backup briefly stops only StethoFuse web/API and restarts them;
  first job exited `0`, both services became healthy and public health returned
  `200`. This maintenance interval means a brief daily application outage.
- Retention target 7 daily / 4 weekly / 6 monthly; **pruning remains disabled**.
  `/etc/stethofuse/remote-restore-verified` is deliberately absent despite the
  earlier successful synthetic restore. Do not create it without pruning approval.
- Earlier synthetic remote restore and independent paper-password recovery
  remain valid separate recovery evidence. This first production snapshot was
  completed/listed, not subjected to another full restore campaign.

## Exact operational commands and rollback

Run as the owner through authorized sudo; never dump `compose config` or
container environments because those contain runtime configuration.

```sh
sudo docker compose --project-name stethofuse-production \
  --project-directory /opt/stethofuse/deploy \
  --env-file /etc/stethofuse/runtime.env \
  -f /opt/stethofuse/deploy/compose.yaml \
  -f /opt/stethofuse/deploy/compose.firebase.yaml ps
curl --fail --silent https://stethofuse.ashraf-alsaloul.com/api/health
sudo systemctl status cloudflared-stethofuse.service stethofuse-backup.timer
sudo journalctl -u stethofuse-backup.service --since today --no-pager
```

For immediate isolation/rollback, stop ingress and scheduled maintenance first:

```sh
sudo systemctl disable --now stethofuse-backup.timer
sudo systemctl stop cloudflared-stethofuse.service
# If a backup is running, allow its EXIT trap to restore service before this stop.
sudo docker compose --project-name stethofuse-production \
  --project-directory /opt/stethofuse/deploy \
  --env-file /etc/stethofuse/runtime.env \
  -f /opt/stethofuse/deploy/compose.yaml \
  -f /opt/stethofuse/deploy/compose.firebase.yaml stop
```

Preserve `/srv/stethofuse`, root-only credentials, encrypted B2 snapshots and
release images. Do not use `down -v`, delete private data or touch Axora. This is
the first production release, so there is no older live application release to
switch back to. Removing its CNAME means deleting **only** record
`094b8b7393932d2ad6dc1ae443bfa747` from zone
`ef6d706c4c74662047331229b2818ba5`. Delete the new tunnel only if abandoning the
deployment and after its connector is stopped. Remove only the newly added
redirect rule `b9567f6717d24687b2c06f30290ec79c` from ruleset
`98bafe245d2740de83b3dc4ac8bbad03`; do not delete the whole ruleset if other rules
have since been added. Remove only the newly added
Firebase domain if reverting that configuration; retain all existing domains.
The previous backup configuration is retained root-only at
`/var/backups/stethofuse/pre-deploy-20260927/backup.env` (same-host rollback copy,
not off-host recovery). Restore data only to a new staging directory, verify
SQLite and hashes, then perform a separately reviewed data-root switch.

No main merge or force-push is part of deployment. This document and the
installed tunnel/backup helper updates may have a later Git commit than the
deployed application release; do not mistake that for an application redeploy.
