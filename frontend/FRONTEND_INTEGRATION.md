# StethoFuse frontend: integration and operation

## Winter-glass continuation — 2026-09-24

Visual changes are in the existing frontend only. The approved owl field is now the normal default. No backend/ML/service/production-auth/domain settings changed. See `WINTER_GLASS_REVIEW.md` for fresh design and verification evidence.

Demo reassignment revokes the old grant, creates a fresh ID, retains old authorship/history and starts an empty replacement review with a new notification link. A real API must enforce equivalent boundaries transactionally. Job detail is owner-only even if recording/result content is explicitly shared. UI guards and fictional browser state are not backend authorization.

## Scope and architecture

This is an additive frontend in `implementation/frontend/`, beside the existing FastAPI/Jinja2 application. It does not replace the ML, training, evaluation, database or backend routes. The old FastAPI `/` continues to serve its existing template; run the separate Vite server to review the new experience.

React and TypeScript provide reusable form/dialog/table/audio components, typed role and recording contracts, shared account state and lazy public/workspace/account page groups. This modular addition supports the full route inventory without introducing a second backend. The approved snowy composition, logo and source imagery are reused. Brand strings and configurable origin/API placeholders are centralized in `src/brand.ts`; neither the registered academic title nor the deployed domain has been changed.

Pinned dependencies are recorded in `package.json` and `package-lock.json`: React/React DOM 19.3.0, React Router DOM 7.18.4, Phosphor icons 2.1.10, TypeScript 7.0.2, Vite 8.3.0, React Vite plugin 6.1.1 and Playwright Core 1.63.0. No Firebase SDK or replacement server is installed.

## Run locally

```bash
cd /home/ashraf/Documents/StethoFuse/implementation/frontend
npm run dev
```

Open **http://127.0.0.1:4180/**. Dependencies are already installed in this workspace; a fresh checkout can reproduce them with `npm ci` before running. No backend, provider keys or private audio are required for the demonstration.

Normal production build and local preview:

```bash
npm run build
npm run preview
```

Stop the development server first if it occupies port 4180. A normal production build disables fixture sign-in. For an intentionally public, fictional demonstration build only:

```bash
VITE_ENABLE_DEMO=true npm run build
npm run preview
```

The demo flag is compiled into the bundle, not changed by a query parameter or browser storage. Never enable it on a real authenticated application. Disabling it also does **not** complete authentication integration: the current workspace gate deliberately requires demo mode until the real provider/session adapter is implemented.

| Configuration | Current behavior |
|---|---|
| `import.meta.env.DEV` | Enables explicit development persona and state controls in Vite development. |
| `VITE_ENABLE_DEMO=true` | Opt-in demonstration build. Default production value is disabled. |
| `VITE_API_BASE_URL` | Central placeholder, default `/api`; no live backend requests are wired. |
| `VITE_PUBLIC_ORIGIN` | Central origin placeholder; existing default does not prove domain/provider configuration. |

Vite-prefixed values are public client configuration, never secret storage. No DNS, deployment, authentication-provider allowlists or production credentials were changed.

## What is real, simulated and unavailable

| Capability | Actual implementation |
|---|---|
| Navigation, forms, validation, filters, modal confirmations, tabs and responsive shell | Working client UI. Public/auth routes and safe-return behavior have executed browser coverage. |
| Personas, own-recording scope, assignments, reviews, admin changes and settings | Fictional typed fixtures with local persistence and client-side permission checks. Not a security boundary. |
| Password login, public signup, Google sign-in/linking, reset email, verification | Not connected. Forms validate; provider actions report unavailable or explicitly labelled demo previews. No real account or email is created. |
| WAV selection | Local file validation/metadata workflow. No private recording is uploaded to any service. |
| Device recording | Explicit simulated device workflow, including failure scenarios. No real microphone capture or device authorization is claimed. |
| Ensemble processing | Timed local job stages and elapsed time, not ML execution or a genuine progress percentage. Navigation remains available. |
| Playback, WAV download, waveforms and spectrogram | Real browser audio/visualization of **synthetic demonstration samples**, not separated patient audio or ML output. Downloads are labelled accordingly. |
| Quality/reference metrics | Not invented. Demonstration data does not establish separation accuracy, superiority, diagnosis or reference-based scores. |
| Notifications, email preferences and support | Local UI/state only. No email, push or support ticket is sent. |
| Privacy/terms | Draft presentation for review, not an approved production policy. |

`AudioWorkbench` creates synthetic samples locally, including a periodic heart-like component and noise-based lung-like component. Its PCM WAVs, waveform plots and time/frequency visualization are derived from those samples. They must not be presented as genuine cardiopulmonary outputs.

## Fictional identities and persistence

Use the clearly labelled development-persona section at `/login#demo-personas`, or the demo switcher inside the application. Public registration has no privileged-role selector.

| Persona | User ID | Initial scope |
|---|---|---|
| Amina Rahman, staff | `USR-1001` | Own recordings including `REC-1042` through `REC-1046`. |
| Daniel Tan, staff | `USR-1002` | Separate own recordings including `REC-1047` through `REC-1049`; Google-only identity fixture. |
| Sofia Chen, analyst | `USR-2001` | Own sample plus explicit assignments `ASN-401` / `ASN-402`, not all staff audio. |
| Elias Noor, administrator | `USR-3001` | User/system metadata administration; role alone grants no private-audio access. |

Pending and disabled account fixtures also exist for administrative state handling. Demo mutations persist in `localStorage["stethofuse-demo-v1"]`; the selected fictional persona ID is in `sessionStorage["stethofuse-demo-persona"]`. Sign-out clears the selection, not all fictional saved metadata. Reset demonstration data is explicit and confirmed.

Passwords remain transient form state and are cleared after submission. The public forms do not persist passwords, auth tokens, reset action codes or provider credentials. Avoid entering real personal information: locally stored demonstration notes/metadata are not encrypted clinical storage. All personas' fictional data is downloadable in the client bundle/storage; UI scoping demonstrates the intended experience, **not** isolation against a malicious browser user.

## Adapter contracts and authorization boundary

`src/data/types.ts` defines users, roles/statuses, recordings, jobs, results, ensemble-run metadata, assignments, reviews, notifications, preferences and safe audit events. `src/data/store.tsx` is the functional fixture implementation.

`src/data/adapters.ts` deliberately separates future services:

- `AuthenticationAdapter`: `signIn`, `register`, `signInWithGoogle`, `sendPasswordReset`, `signOut`.
- `DataAdapter`: `getOwnRecordings`, `requestEnsemble`, `getAuthorizedAssignments`, `getAuthorizedAudioUrl`.

All exported live methods currently reject with an integration-unavailable error, except the no-op `signOut`. A failed live provider operation does not silently fall back to a fabricated authenticated user. Only the explicit demo persona control can select a fixture.

These are starting contracts, not a finished API client. A connected implementation must extend them for provider session observation, callback/action-code validation, verification/resend, reauthentication/linking, upload/capture, polling/cancellation, results, sharing/revocation, reviews, administration, settings and notifications. Replace the demonstration-only gate in `src/main.tsx` with real session bootstrap when that work is authorized.

Firebase would prove identity. FastAPI must independently validate the credential, resolve the application user/status/role, and enforce every object's ownership or active grant. Frontend guards, hidden buttons and a Firebase login alone are insufficient.

## Existing FastAPI APIs are not wired to this UI

The current backend exposes a useful single-system research workflow, but not the required multi-user permission model:

| Existing surface | Integration constraint |
|---|---|
| `GET /health` | Health only; not identity or authorization. |
| `GET /models`, `GET /methods` | Existing individual model/method registry, not the normal-user ensemble request contract. |
| `POST /upload` | Existing WAV upload; no new per-account authorization was added. |
| `POST /separate/{audio_id}` | Existing model-specific job path, including background mode; not the proposed ensemble API. |
| `GET /result/{job_id}` | Existing results and artifact metadata require ownership/grant enforcement before exposing them in this multi-user UI. |
| `GET /download/{job_id}/heart`, `/lung` | Existing download paths lack the required user/object access protection. They are not linked from the new UI. |
| `GET /history` | Existing **global history**, not an own-recordings endpoint. It must not back an account's private history without server-side scoping. |
| `/visualizations/...` | Existing static artifacts need an access strategy; an unprotected URL must not bypass revoked or private access. |

The existing upload/job database models do not establish the ownership/assignment policy represented by the fixtures. No backend authorization fix, migration, owner association, service account or live API wiring was performed in this frontend task.

Before live integration, the server needs verified-user bootstrap, ownership and grant checks on list/detail/media endpoints, revocation semantics, safe privileged metadata endpoints, last-admin protection, an ensemble request/result contract, error/cancellation behavior, audited role/status changes and a real retention policy. Normal users should request ensemble processing, not select internal experts.

## Authentication and recovery details

Recovery acknowledgments avoid revealing whether an email exists. Resend previews have a local cooldown; a real server/provider must enforce actual rate limits. Reset and verification `?state=` parameters are demo previews only and do not consume action codes or modify provider accounts.

`/auth/action` inspects supported action mode but does not render, store or forward a supplied raw action code. It routes to honest unavailable/invalid recovery presentation. Future integration must validate the provider code once, avoid logging it, and replace sensitive URL parameters after safe handling. Current demo UI is not a provider callback implementation.

The Google callback explicitly covers cancellation, unavailable/error and linking conflict. Its completing preview ends in unavailable, never fabricated success. Matching email strings do not link identities. Sensitive account changes require genuine provider reauthentication when connected.

Return destinations are constrained to normalized same-origin `/app/...` paths. External, malformed and traversal-like values are rejected; queries and fragments are discarded instead of forwarding potential secrets. Route permission checks still apply after any allowed return.

## Future deployment guidance — not applied

Serve the eventual built `dist/` with SPA fallback for frontend routes so nested-route refresh works. Do not apply that fallback to API/media paths. Decide explicitly whether FastAPI serves the build or a same-origin reverse proxy separates frontend/API; configure API origin/CORS and secure headers accordingly. These are future options, not repository/backend changes made here.

Keep demonstration builds clearly separated from real accounts/data. Configure actual Firebase authorized domains, Google callback/action URLs, API credential verification, secret management and protected artifact delivery in a separate authorized integration task. Neither the default brand origin nor this local preview changes the registered/deployed domain.

## Verification and evidence

From the frontend directory:

```bash
node tests/public.mjs
node tests/workflows.mjs
node tests/admin.mjs
npm test
```

Public tests use the running server at `http://127.0.0.1:4180`, installed `/usr/bin/google-chrome`, and Playwright Core. `FRONTEND_URL` and `CHROME_BIN` can override those values for that script. The scripts are review tools, not provider integration tests.

At this documentation checkpoint:

- **PASS, executed:** `tests/public.mjs`: 42 checks, zero failures/runtime exceptions, Chrome 151.0.7922.137. Safe redirects, signup without roles, secret non-persistence, recovery/callback states, direct public-route refresh, keyboard access and reduced-motion presentation covered.
- **Visually inspected:** public/auth screenshots at 1440, 1920, 768 and 390px widths, including mobile signup and reset, expired/success and unavailable Google states. Headless Chrome viewport emulation, not physical mobile devices. `evidence/public/REVIEW.md` records scope/caveats.
- **Pending coordinator's final verification update:** staff/analyst/admin suites, final combined build, visual consistency and animation/performance measurements. This document does not infer their results from files merely existing.
- **Not implemented/tested live:** Firebase/provider email, backend authorization, physical recording hardware, live ensemble separation, actual multi-user server isolation and production deployment.

See `evidence/public/results.json`, `evidence/public/*.png`, `FRONTEND_ROUTE_MAP.md`, and the coordinator's asset/performance and final verification reports. Development request counts are not production bundle/performance measurements. Old or independent owl PASS claims are not evidence for the final assembled frontend.
