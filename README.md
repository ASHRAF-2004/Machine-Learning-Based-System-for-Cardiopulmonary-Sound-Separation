<img src="frontend/public/assets/logo.svg" alt="StethoFuse — Listen further" width="250">

# StethoFuse

A cardiopulmonary sound-separation application for research and education, with a calm
winter workspace for recordings, separation runs and explicitly shared audio review.
**Not a diagnostic system. No production deployment is claimed.**

Academic project: **Machine Learning-Based System for Cardiopulmonary Sound Separation**.
The application and FYP report remain separate Git repositories. Submitted FYP1 evidence
is preserved in the sibling documentation repository.

## Current milestone

M1 connects Firebase identity to FastAPI authorization and private, persistent user data.
The approved frontend/artwork and continuous two-axis owl renderer are preserved.
Read [the M1 API contract](docs/M1_API_CONTRACT.md) and
[route protection evidence](docs/M1_ROUTE_AUDIT.md) for exact scope and limitations.

| Layer | Technology / boundary |
| --- | --- |
| Interface | React19, TypeScript, Vite, React Router; existing winter/glass design |
| Identity | Official Firebase Web SDK; email/password and Google flows |
| Authorization | FastAPI + trusted application SQLite records; verified Firebase UID |
| Private data | Explicit development database and private filesystem, outside public assets |
| Media | Authorized API delivery; no public upload/output/visualization mount |
| ML/evaluation | Preserved Python Strategy/Factory services, PyTorch NeoSSNet adapter and individual baselines |
| Testing | Pytest API/permission integration and real Chrome browser automation; mocks distinguished from live providers |

Live identity cannot be inferred from a successful build or mock test. The selected project
`stethofuse-c18cd-3cca0` has its registered Web App and enabled email/password and Google
providers. Developer CLI consent, restricted keyless backend ADC and harmless provider
reads are verified. On 27 September 2026, real Google-authenticated sessions for the
verified primary Administrator and an existing Healthcare Staff account were accepted by
the local FastAPI verifier. Admin Users returned 200 to the Administrator and 403 to Staff;
Staff also received 403 when submitting a forged admin-role request. A synthetic silent WAV
verified owner access, exact-resource sharing, direct-media/download denial before sharing,
and denial again immediately after revocation. A second Staff-owned silent fixture returned
403 to the Administrator for metadata, media and download and remained absent from the
Admin recording list. This is **LOCAL REAL PROVIDER** plus **LOCAL BACKEND** evidence, not
production verification. Email/password and recovery flows remain untested, and no
verification/reset email was sent. No Firebase project is created automatically.

## Identity and access

```text
Firebase sign-in → current ID token → Authorization: Bearer → FastAPI verification
  → UID-linked application account → active status + role + owner/grant check → resource
```

- Public registration defaults to `healthcare_staff`; no requested browser role is accepted.
- `audio_analyst` can review only explicitly assigned resources.
- `admin` manages accounts and safe operational metadata, not everyone's private audio.
- The current administrator's own User Management row is read-only: FastAPI rejects
  self role/status changes with `403`; another administrator must act, and the last-active
  administrator safeguard remains enforced.
- First-admin bootstrap is a trusted operator action against a real, verified UID, never an
  email match, first-user promotion, browser toggle or public HTTP endpoint.
- Role/status/grant checks use trusted records; UI guards only support navigation.
- Legacy unowned data stays quarantined. No automatic ownership inference or destructive
  database migration is performed on startup.
- Demo personas and synthetic audio are development-only and isolated from live mode.

See [roles, signup/sign-in and administrator provisioning](docs/ROLES_AND_ACCOUNT_PROVISIONING.md)
for the permission matrix, steps for promoting another verified account and FYP2 use-case actors.
The user confirmed that an existing administrator may promote additional administrators;
public signup still never grants privileged roles.

The working branch is `fyp2/application` (`939052f`), based on the preserved `16af63c` checkpoint.
Its author configuration matches the existing human-authored repository identity
`ASHRAF-2004 <adoashraf103@gmail.com>` and the authenticated GitHub account. The earlier
`codex/fyp2-application-rebuild` remote branch remains preserved. Its duplicate draft PR #8
was closed as superseded by owner-maintained draft PR #9; no history was rewritten. The
normal branch is pushed for review, not merged to main.
This is not a production deployment or a claim that the final hostname is live.

## Local development (Ubuntu)

Reuse installed dependencies. This repository does not require reinstallation of the working
frontend, Blender or ML stack to test authentication. From this repository:

```sh
# Existing frontend: normal mode is live and fails closed if configuration is absent.
cd frontend
npm run dev -- --host 127.0.0.1 --port 4180 --strictPort
```

Copy `frontend/.env.example` to an ignored local configuration only after obtaining the
existing project's genuine Web App settings. Firebase web configuration is public client
configuration; Firebase Admin credentials and OAuth secrets must never go into `VITE_*`.
The prepared workspace already has its genuine configuration in ignored `frontend/.env.local`.
Use **http://localhost:4180/login** for local provider tests: `localhost` is currently an
authorized Firebase domain; `127.0.0.1` and the not-yet-deployed final hostname are not.
Use the existing provider auth domain, not an invented callback URL. No email is sent by tests
without an explicitly designated recipient.

The API-only dependencies are pinned in `requirements-m1.txt`. The prepared workspace uses
`../.local/venvs/backend-smoke/`; a standalone checkout may use its own ignored virtualenv.

```sh
# Prepared workspace environment, not system Python:
../.local/venvs/backend-smoke/bin/python -m pip install -r requirements-m1.txt

# Explicit isolated paths, never the legacy database or frontend public directory:
export STETHOFUSE_M1_DATABASE=/home/ashraf/Documents/StethoFuse/.local/data/m1.sqlite3
export STETHOFUSE_M1_PRIVATE_STORAGE=/home/ashraf/Documents/StethoFuse/.local/private-storage/m1
export STETHOFUSE_FIREBASE_PROJECT=stethofuse-c18cd-3cca0
/home/ashraf/Documents/StethoFuse/.local/venvs/backend-smoke/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Firebase Admin needs an approved Application Default Credentials mechanism. CLI sign-in and
server credentials are separate. Do not generate keys, copy tokens into this repository or
disable verification to make local startup appear connected. Exact initialization/bootstrap
commands and runtime limitations are maintained in the M1 route audit. Do not start an
additional process if the relevant loopback port already serves this project.

The approved local credential mechanism is keyless impersonation of
`stethofuse-m1-auth-reader@stethofuse-c18cd-3cca0.iam.gserviceaccount.com`, with Firebase
Authentication Viewer only. The user's ADC consent and harmless provider check have
succeeded. The backend command above additionally needs these settings before startup:

```sh
export CLOUDSDK_CONFIG=/home/ashraf/.config/stethofuse-gcloud
export STETHOFUSE_FIREBASE_ENABLED=1
```

Do not enable this flag merely because IAM permissions exist. The isolated ADC directory
is outside the repository, owner-only, and must never be copied into reports or backups.
Keyless ADC still contains sensitive source-user credentials. No application admin role
is conferred by these infrastructure settings.

Explicit fictional preview (development server only):

```sh
cd frontend
VITE_APP_MODE=demo npm run dev -- --host 127.0.0.1 --port 4181 --strictPort
```

## Checks and evidence

```sh
cd frontend
npm run build

# From repository root; isolated temporary databases/private files and mock identity:
/home/ashraf/Documents/StethoFuse/.local/venvs/backend-smoke/bin/python -m pytest tests/test_access_foundation.py tests/test_m1_api.py tests/test_m1_operator_safety.py -q
```

Use the exact test filenames/commands recorded in the route audit if additional suites are
added. **MOCK** proves application behavior against controlled identities, not successful
Google login or Firebase project configuration. **EMULATOR**, **LOCAL REAL PROVIDER** and
**PRODUCTION** results must be separately identified. No production tests are implied.

From `frontend/`, the focused live-client tests are `node tests/m1/client.mjs` and
`node tests/m1/browser.mjs` (running loopback Vite required). `node tests/m1/cross-layer.mjs`
starts an ephemeral loopback FastAPI instance with temporary SQLite/private files and
exercises actual browser upload/media/isolation using **mock identity only**. Test SDK
substitutions live under `tests/`, not in an application login bypass. Use a new
`EVIDENCE_ROOT` for repeat runs; evidence is never silently overwritten.

## Separation and research provenance

The normal workflow requests **one ensemble separation**, not a choice of individual
algorithm. Ensemble Learning remains in scope; Federated Learning is excluded.
The M1 API must report unavailable execution honestly while the verified ensemble executor
is not connected—it must not manufacture jobs, outputs or superiority scores.

| Component | Preserved implementation and evidence boundary |
| --- | --- |
| Fixed-filter baseline | Frequency-domain baseline for controlled benchmarking |
| NMF baseline | NumPy multiplicative-update spectrogram decomposition; not a complete published NMF/NMCF reproduction |
| VMD baseline | `vmdpy` mode decomposition/grouping; not the combined DAE-NMF-VMD method |
| NeoSSNet | Existing PyTorch adapter and source reference; checkpoint identity, license and exact paper correspondence require verification |
| Ensemble | Intended expert/fusion direction; no superiority claim without appropriate experiments |

Existing training, dataset preparation and evaluation scripts remain in `scripts/` and
`evaluation/`. They are **not** run as part of M1 setup. See the preserved
[legacy baseline instructions](docs/LEGACY_BASELINE_README.md) for historical commands, not
for current public API/security instructions. Its old performance/availability statements
are historical, not newly verified results. The report's candidate attribution register is
`../documentation/fyp2/provenance/METHOD_ATTRIBUTION.md`.

Reference-based metrics require valid paired references, documented splits/alignment and
real executions. Synthetic demo waveforms are never evaluation results. Do not collect
participant/patient recordings as development fixtures.

## Repository map

```text
frontend/             existing responsive application, approved assets, auth adapters/tests
app/access_foundation/ shared identity/role/last-admin primitives
app/m1/               protected API, persistent authorization and private-media integration
app/ml/               preserved individual-method adapters
app/services/         preserved preprocessing, separation and evaluation services
database/             legacy schema/seed recipes (not runtime data)
scripts/              trusted local tools and preserved experiment commands
tests/                foundation, API and legacy tests
docs/                 contracts, route inventory, migration and evidence boundaries
```

Large historical render evidence and inactive frame libraries remain on disk, excluded from
new Git commits; approved runtime owl assets and source scripts are retained. No frame library
was regenerated during M1. Environment files, credentials, databases, recordings, model weights,
caches and build output are ignored. Never serve the parent workspace.

## Deployment target — not deployed

Target: **https://stethofuse.ashraf-alsaloul.com**, on the owner's Linux server. Frontend and
`/api` should share this origin. Firebase provides identity, not application hosting.

Existing Cloudflare/Caddy infrastructure must be inspected and reviewed before routing
changes. No DNS edits, service restarts, public tunnels, pushes or production deployment are
authorized by this local M1 milestone. Production requires separate approval, provider/edge
configuration, secure storage/backup review and real-account authorization evidence.
