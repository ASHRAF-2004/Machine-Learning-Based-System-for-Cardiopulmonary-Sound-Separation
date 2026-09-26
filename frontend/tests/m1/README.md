# M1 focused frontend evidence

These tests distinguish actual application behavior from provider verification.
They never claim a real Firebase account, email delivery, Google consent flow,
production deployment or clinical/model result was verified.

## Current results (2026-09-26)

All paths below are relative to `implementation/frontend/`.

| Command | Actual result | Retained evidence |
| --- | --- | --- |
| `npm run build` | PASS: TypeScript and production Vite build | Terminal output; coordinator build log |
| `EVIDENCE_ROOT=output/playwright/m1/browser-final node tests/m1/browser.mjs` | 14 PASS, 0 FAIL | `output/playwright/m1/browser-final/results.json` |
| `EVIDENCE_ROOT=output/playwright/m1/client-final node tests/m1/client.mjs` | 7 PASS, 0 FAIL | `output/playwright/m1/client-final/results.json` |
| `node tests/m1/regression.mjs workflows` | 16 PASS, 0 FAIL, explicit development demo | `output/playwright/m1/workflows/workflows/results.json` |
| `node tests/m1/regression.mjs home` | 5 viewport/CTA checks PASS on default live mode | `output/playwright/m1/home/results.json` |
| `node tests/m1/regression.mjs motion` | 6 PASS, approved real-pointer owl/static checks | `output/playwright/m1/motion/motion/results.json` |
| `node tests/m1/preservation.mjs` | 1,282 protected files SHA256 unchanged from `c681839` | `output/playwright/m1/preservation/results.json` |
| `EVIDENCE_ROOT=output/playwright/m1/cross-layer-final node tests/m1/cross-layer.mjs` | 6 PASS, real local API/storage with MOCK identity | `output/playwright/m1/cross-layer-final/results.json` |

Evidence directories are append-only by convention: every new harness refuses
an existing output directory. Set a new `EVIDENCE_ROOT` for reruns. Run from the
frontend directory. Default live dev server is `npm run dev` on loopback 4180;
the historical fixture workflows require `npm run dev:demo` on loopback 4182.
Both require existing installed dependencies and Chrome `/usr/bin/google-chrome`.
No browser/provider installation is performed by these scripts.

### Browser test boundary

`browser.mjs` first loads the real missing-config runtime: live login is disabled,
fixture local/session storage does not admit workspace access, and public home
still loads its approved owl. Subsequent checks intercept only test browser
network responses for the official SDK imports and public runtime configuration,
then provide a clearly MOCK API. There is no test bypass, mock token parser, or
fixture fallback in application source. SDK method invocations and application
adapters run, but Google/Firebase services are not contacted.

Covered: email login/restoration; server-assigned role; owner collections and
foreign denial; asynchronous upload with actual returned ID; bearer media blob;
exact original-resource review grant; server-confirmed preference envelope;
profile update; 390px containment; logout and storage checks; analyst review and
revocation; refreshed role restriction; one forced-token retry and session expiry;
Google adapter; unverified registration/verification request/reload; reset request,
single code consumption, URL redaction and invalid/expired handling.

The protected media renderer now uses the authenticated response Blob MIME, not
a guessed review type or response URL. Application memory URLs are revoked on
page/account exit. Already downloaded bytes cannot be recalled by revocation.

The coordinator separately owns `cross-layer.mjs` and `api_fixture.py`, with real
local FastAPI/isolated SQLite/private media and an explicitly fictional verifier.
Its final results are under `output/playwright/m1/cross-layer-final/`; these are not real
Firebase verification either.

### Historical assertions preserved

The regression wrapper leaves old suite files and old evidence untouched. It
changes output destinations and uses the explicit demo server where appropriate.
Only the motion checkpoint's `adapters.ts` and `brand.ts` source hashes are omitted:
those two modules were intentionally changed by the authorized M1 integration.
All approved owl/controller/art identity checks remain. The separate preservation
test checks all tracked public assets, CSS, owl renderers and scenery source.

Initial browser failure reports remain at `output/playwright/m1/browser/` and
`browser-run2/`. One immediate checkbox assertion assumed synchronous local state;
the corrected assertion clicks, waits for the actual server-save message, and
asserts persisted server preferences. Two exact `/login` URL assertions did not
allow the legitimate safe `returnTo` query. The corrected test checks pathname,
cleared workspace and empty identity persistence. The coordinator independently
confirmed the login form after real-local-API logout. No app authorization error
was hidden by these corrections.

## Implemented but not verified live

Official Firebase 12.19.0 SDK flows are implemented; required web-app config is
intentionally absent and fails closed. Provider setup, authorized domains,
password/email policy, email templates/action handler routing, real Google/email
consent/delivery and deployed HTTPS behavior remain external verification gates.
SDK browser-session persistence is JavaScript-accessible and is not HttpOnly or
XSS-proof. No manual credential/token localStorage/sessionStorage writes exist in
the application. Test-only storage contains a fictional UID/verified flag only.

Canonical backend roles remain `healthcare_staff`, `audio_analyst`, `admin`.
`staff`/`analyst` aliases exist solely to reuse presentation; frontend checks are
not an authorization boundary. Live mode never reads fixture data or manufactures
recordings, processing jobs, results, audio, metrics or notifications.

Unconnected live screens/actions explicitly say unavailable: ensemble execution,
device capture, recording archive/delete, notification delivery, historical
review UI, provider linking/session management, export/deletion/retention,
advanced administration/benchmark controls. No synthetic success replaces them.
