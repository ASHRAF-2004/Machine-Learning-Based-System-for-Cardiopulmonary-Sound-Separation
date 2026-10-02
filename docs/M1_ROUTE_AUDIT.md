# M1 backend route and authorization audit

## Local frozen-model integration — 29 September 2026

[Current integration evidence](LOCAL_ML_INTEGRATION.md) supersedes the historical
unavailable-job statements below: explicitly enabled owner POST now returns202
with a durable job; one separate CPU worker publishes real protected outputs
and provenance. Job/result/media routes and exact grant boundaries are reused.
Admin has no private-audio override. The production identity path remains the
already deployed Firebase JWT + REST current-account check (not the historical
Cloud Run proposal below). No identity/provider change or production rollout
occurred in this local ML milestone. See [current API contract](M1_API_CONTRACT.md).

2026-09-26. Implementation evidence, not production approval. Default entrypoint remains
`app.main:app`; it now constructs `app.m1.api.create_app`. Legacy routers are preserved
on disk but are neither imported nor registered. No production deployment, Firebase
account mutation or legacy-data migration was performed by the route implementation.
Subsequent approved local first-admin bootstrap is recorded in
[account provisioning](ROLES_AND_ACCOUNT_PROVISIONING.md). A later narrow hardening
also rechecks the target's current verified/enabled Firebase UID before role changes;
existing actor authorization, audit transaction and last-admin protection are preserved.

## Current Firebase production identity path — 27 September 2026

The current `fyp2/application` working tree supersedes the former API-runtime ADC
adapter described later in this audit. The path is now:

```text
protected FastAPI request
  → Firebase RS256 signature/public-certificate + issuer/audience/time/sub validation
  → HTTPS Cloud Run verifier: Firebase Admin check_revoked + current get_user(uid)
  → UID-linked local application record
  → local active status / role / owner / grant / assignment authorization
```

The self-hosted API runtime needs no Google ADC or private key. The only Google
permission required by the inspected Admin SDK calls is `firebaseauth.users.get`;
the prepared Cloud Run identity will receive it through a project custom role with
that one permission. Cloud Run has no StethoFuse role, ownership, grant or media
authority and exposes no user enumeration or mutation route. Its proposed public
HTTPS endpoint accepts only a signed Firebase ID token, resolves only the UID
inside that token and returns minimal current identity state. Cloud Run/IAM resources
do not exist yet. The real Firebase acceptance recorded below applies to the prior
local backend path, not a live Cloud Run verifier.

Admin role PATCH no longer issues an arbitrary-UID provider lookup. It requires an
existing locally provider-verified target and applies role/status/audit transactionally;
that account's future API calls still require its own valid, unrevoked provider token.
This keeps the verifier from becoming a UID-enumeration oracle. New verifier and role
tests use mocked/controlled providers only.

The final focused local run recorded 42 passed across
`test_auth_verifier_service.py`, `test_firebase_token_boundary.py`,
`test_backup_manifest.py`. One broader M1/access/operator batch passed 91 cases plus
26 subtests after its temporary environment was aligned with the existing runtime
lock and the bootstrap test's old patch target was corrected. It includes generated
RSA test keys and synthetic backup data; it is not a live Firebase/Cloud Run test.
The existing Starlette/httpx deprecation warning is non-failing. No production write
occurred.

Only two new test functions (four parameterized executions) were added in the final
security sprint: transport timeout and untrusted successful verifier responses.
Eighteen already-written verifier/manifest test functions were preserved, and existing
revocation/disabled/error tests gained token/header log-redaction assertions. The
new production Cloud Run service, IAM identity and encrypted B2 repository remain
unprovisioned; their source/runbooks and restore drill are ready for owner actions.

The sections below are the route inventory and original September 26 M1 evidence;
they remain useful for endpoint/data-policy scope but must not be read as the current
production credential implementation.

## Before: complete legacy HTTP inventory

| Legacy entrypoint | Former exposure | M1 disposition |
| --- | --- | --- |
| `GET /` | Legacy algorithm-selection HTML | Safe API service description only |
| `GET /health` | Public service status | Public, no paths/private data; also `/api/health` |
| `GET /models`, `GET /methods` | Public method catalog | Fresh verified active **admin** required; honest empty unavailable catalog |
| `POST /upload` | Unauthenticated unowned upload | `410 legacy_route_retired` |
| `POST /separate/{audio_id}` | Unauthenticated method execution | `410 legacy_route_retired` |
| `GET /result/{job_id}` | Global result metadata, filesystem paths/errors | `410`; HEAD also retired |
| `GET /download/{job_id}/heart` | Direct heart bytes | `410`; HEAD also retired |
| `GET /download/{job_id}/lung` | Direct lung bytes | `410`; HEAD also retired |
| `GET /history` | All users' legacy history | `410`; HEAD also retired |
| `/visualizations/*` static mount | Predictable public PNG paths | Mount removed; GET/HEAD `410` |
| `/static/*` | Application CSS/JS only | Retained source-assets mount, no private-media/DB path |
| Default `/docs`, `/redoc`, `/openapi.json` | Public schema UI | Disabled, `404` |

Ten explicit original handlers plus two mounts and default documentation routes were
reviewed. Retired endpoints return no record data even with a bearer token or Range
header; unsupported methods are `405`. Old `app/routers/*`, service/strategy code and
ML assets remain unchanged, but importing the supported application no longer imports
NumPy/Torch, initializes the legacy DB, or exposes those routers. Do not mount them
into another server: their authorization has not been retrofitted. The old frontend
algorithm workflow is intentionally not the live M1 API.

## Canonical registered API

| Path | Methods | Authority/data behavior |
| --- | --- | --- |
| `/api/auth/session` | POST | Verified provider identity; empty body; creates staff only, preserves existing role/status |
| `/api/auth/me` | GET, PATCH | GET read-only account lookup; PATCH own display name |
| `/api/preferences` | GET, PATCH | Own persisted preference sections only |
| `/api/recordings` | GET, POST | Own/explicitly shared receipts; real bounded PCM WAV upload with server-derived owner |
| `/api/recordings/{recording_id}` | GET, PATCH | Authorized minimal metadata/scoped resources; owner-only title changes |
| `/api/media/{resource_id}` | GET, HEAD | Owner or current exact/recording grant; same check for original, output, PNG, download and byte ranges |
| `/api/jobs`, `/api/jobs/{job_id}` | GET | Owner-only persisted operational metadata |
| `/api/recordings/{recording_id}/jobs` | POST | Owner check then honest `503 ensemble_unavailable`; no job inserted |
| `/api/results`, `/api/results/{result_id}` | GET | Authorized persisted results and individually authorized files; initially empty |
| `/api/recordings/{recording_id}/grants` | GET, POST | Owner-only grant history and explicit share/assignment creation |
| `/api/grants/{grant_id}` | DELETE | Owner-only single-grant revocation |
| `/api/recordings/{recording_id}/revoke-access` | POST | Owner plus exact recording confirmation; atomically revoke all current recipient grants |
| `/api/assignments` | GET | Current analyst's active scoped assignments |
| `/api/assignments/{grant_id}/review` | GET, PUT | Assigned active analyst only; exact original_audio **or** result; transactionally persisted notes/decision |
| `/api/admin/users` | GET | Admin user metadata, not private recordings |
| `/api/admin/users/{user_id}` | PATCH | Admin role/status mutation, explicit target confirmation, atomic last-admin protection |
| `/api/admin/audit` | GET | Admin last 200 metadata-only audit entries |
| `/api/admin/methods` | GET | Admin catalog availability; no ML initialization |
| `/api/admin/benchmarks` | POST | Admin only, `503 benchmark_unavailable`; legacy executor not wired |

Contract and JSON examples: [M1_API_CONTRACT.md](M1_API_CONTRACT.md).
No unauthenticated signup-to-admin, impersonation, bootstrap route, public recipient
directory, password storage, token query parameter, or automatic clinical output exists.

## Data, authorization and files

`app/m1/store.py` subclasses the existing access foundation and uses the **same** SQLite
connection/transaction domain and role/grant tables. `app/m1/schema.sql` adds upload/file,
job/result, review and preferences metadata. It accepts only its exact combined schema;
an existing seven-table preparation DB or legacy SQLAlchemy DB is not silently upgraded.
This is an isolated development adapter, not a production migration design.

Legacy `uploaded_audio` and `separation_job` rows do not contain verified ownership and
remain quarantined in the untouched legacy DB/storage. Neither numeric legacy IDs nor
old file paths are adopted. No timestamps, emails, device details or first login are
used to infer an owner. Later import requires an explicitly approved ownership mapping
and audited migration; no such utility is implemented here.

Under the current path, FastAPI verifies the signed token and Firebase claims locally,
then calls the Cloud Run verifier for revocation/current-user state before resolving
the UID to the trusted local active account/role. Custom role claims and frontend role
state are ignored. Expected project is `stethofuse-c18cd-3cca0`; invalid, expired,
revoked or wrong-project tokens fail `401`; unverified, provider-disabled or locally
inactive users fail `403`. Missing verifier configuration or provider outages fail
closed. The Cloud Run service is not yet provisioned; current new tests use injected
identities, not live Cloud Run or production requests.

Admin has no implicit private-content access. All role/status changes, original/result
review writes, grants and revocations recheck policy inside a transaction. Concurrent
last-admin removal is protected by `BEGIN IMMEDIATE` plus count/update/audit in one
transaction. This protects locally active/verified admins; provider-console changes can
still disable the last account and require an approved operator recovery procedure.

Grants are additive. Exact result access never implicitly reveals original audio,
sibling output audio, plots, context or other results. Exact original review works even
while ensemble execution is unavailable. Role demotion removes analyst review writes
but not independent explicit read authority. Owner-confirmed revoke-all removes every
active grant for that recipient/recording; revoking one ID does not promise that.
Review notes are private to their authorized assigned analyst in this bounded M1 API;
owner feedback display and admin assignment reassignment are not implemented.

Uploads are real files: max 25 MiB, PCM WAV, mono/stereo, 1–192 kHz, supported 8/16/24/32
bit PCM, max 30 minutes, complete declared frames. Filename is metadata only; UUID file
names use exclusive create and 0600 permissions in an explicit 0700 private directory.
An existing media directory with group/other permissions is refused, not silently chmodded;
this prevents a configuration typo changing permissions on an unrelated existing directory.
No supplied path is joined to storage. Media checks authority and opens the file in one
DB snapshot, validates the UUID filename and root containment, and uses `O_NOFOLLOW`.
No public storage mount or signed public media URL exists. Single byte ranges and HEAD
reuse full authentication/authorization; invalid/oversized ranges return 416.
Revocation prevents new requests but cannot recall an already opened stream or download.

All expected JSON/media responses have private/no-store, nosniff and no-referrer headers.
Validation errors do not echo request input. Audits contain IDs/action/time, never audio,
review notes, reset links, passwords, provider exceptions or tokens. API access logs
must not be extended to log Authorization headers; browser Blob URLs must be revoked
on sign-out/navigation. HTTPS/reverse-proxy headers, rate limits, retention/deletion,
backups, shared production DB, storage quotas and production deployment remain gates.

## Local operator commands (not live operations performed)

The minimal local test environment is `/home/ashraf/Documents/StethoFuse/.local/venvs/backend-smoke`.
`requirements-m1.txt` contains development/bootstrap and test dependencies. The production
API image now uses `deploy/requirements-runtime.lock.txt` with `google-auth`, certificate
caching/transport and HTTPX; Firebase Admin is retained only in the standalone Cloud Run
verifier image and trusted operator bootstrap environment. No model weights/Torch were
installed for M1.

From `implementation`, trusted local startup:

```bash
export STETHOFUSE_M1_DATABASE=/home/ashraf/Documents/StethoFuse/.local/data/m1.sqlite3
export STETHOFUSE_M1_PRIVATE_STORAGE=/home/ashraf/Documents/StethoFuse/.local/private-storage/m1
export STETHOFUSE_FIREBASE_PROJECT=stethofuse-c18cd-3cca0
/home/ashraf/Documents/StethoFuse/.local/venvs/backend-smoke/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Startup initializes only that explicit isolated DB/private directory. With no explicit
paths, health is available and private operations fail closed; with no provider enable
flag, authentication remains unavailable. The current live API path needs
`STETHOFUSE_FIREBASE_ENABLED=1` and the exact approved
`STETHOFUSE_FIREBASE_VERIFIER_URL` in the external environment. Cloud Run is not deployed,
so do not use a placeholder or call this new path live-verified. The separate trusted
bootstrap CLI may use separately approved local ADC for that operator action only. Do not
paste credentials or tokens into source, screenshots, shell arguments, logs or evidence;
keep browser Firebase Web App settings separate from private operator credentials.
Port 8000 matches the frontend's default API proxy. Access logging is disabled because
even rejected unexpected URL query strings can contain sensitive caller-supplied text.

After the intended primary person really signs in, verifies their account and syncs as
ordinary staff, copy and independently confirm their exact Firebase UID. The script is
dry-run by default and makes no provider call or mutation in that mode:

```bash
/home/ashraf/Documents/StethoFuse/.local/venvs/backend-smoke/bin/python scripts/bootstrap_m1_admin.py --uid CONFIRMED_UID --confirm-uid CONFIRMED_UID
```

Only after explicit user/operator approval add `--apply` to that same command. Apply
requires the real existing verified provider UID and existing local active account;
atomic singleton bootstrap is idempotent only for the unchanged same administrator.
No primary/backup account is auto-created; any backup requires separate approval.
The initial bootstrap was already completed in a prior milestone. This task did **not**
execute apply or repeat bootstrap.

## Executed evidence and limitations

From the StethoFuse workspace root:

```bash
.local/venvs/backend-smoke/bin/python -m pytest implementation/tests/test_m1_api.py implementation/tests/test_access_foundation.py implementation/tests/test_m1_operator_safety.py -q
.local/venvs/backend-smoke/bin/python -m pip check
```

Coordinator final result: **86 passed, 26 subtests passed**, comprising 49 M1 HTTP/SDK-boundary
cases, one operator-path safety test and 36 foundation tests. Artifact:
`../.local/m1-tests/backend-final-junit.xml` from this repository. One non-failing Starlette warning notes future TestClient migration
from httpx to httpx2. Tests cover real temporary SQLite/files/HTTP routing with fictional
identities; official SDK exception classes and invocation arguments are mocked without
network. Coverage includes ownership after restart, unverified/disabled/role changes,
scoped original/result reviews, all derived media kinds, additive/all-grant revocation,
expired scopes, context separation, admin isolation, duplicate-email non-escalation,
atomic last-admin/concurrent foundation safeguards, bootstrap dry run, legacy paths,
direct/range/HEAD media denial, path/symlink/collision safety, declared/chunked upload
limits, input-error sanitization and no synthetic ensemble output.

**Not verified:** real Firebase signature/issuer/audience/revocation against an issued
token, email/password/Google/verification/recovery browser flows, a real primary admin,
production proxy/storage/concurrency, legacy ML execution, ensemble inference, clinical
validity or production readiness. Existing legacy endpoint tests intentionally target
the retired pre-M1 contract and are not used as a claim that old public routes still
work. Internal ML algorithms have not changed or been retested in this minimal runtime.
Frontend browser integration evidence is tracked separately by its implementer.

Official SDK references checked for this integration:
[verify ID tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens),
[Python Admin auth reference](https://firebase.google.com/docs/reference/admin/python/firebase_admin.auth),
[Admin setup](https://firebase.google.com/docs/admin/setup),
[Firebase Admin 7.7.0 package](https://pypi.org/project/firebase-admin/7.7.0/).
