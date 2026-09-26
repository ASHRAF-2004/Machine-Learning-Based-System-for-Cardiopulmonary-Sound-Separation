# M1 security boundaries and release gate

Local integration design, 26 September 2026. This is not a penetration-test certificate or
proof of live provider configuration. Executed test results belong in M1_ROUTE_AUDIT.md.

## Trust boundaries

| Input / actor | Trusted for | Never trusted for |
| --- | --- | --- |
| Browser Firebase user state | UX and obtaining an ID token | Backend identity, role, ownership or grants |
| Backend-verified Firebase ID token + current provider record | Stable UID and verified/active identity | Client-supplied/custom-claim application role |
| Application database | Active role/status, owner and explicit grants | Passwords, OAuth tokens or reset-link storage |
| Owner | Own recording metadata and deliberate resource grants | Assigning application roles or another owner's files |
| Assigned analyst | Scoped reading/research review while assignment is active | Global recording access, owner job management or self-grants |
| Administrator | Account management and safe operational metadata | Impersonation, reset links, automatic access to private media |
| Trusted operator bootstrap | Exactly confirmed existing verified UID | Email-string matching, invented UID or public signup promotion |

Every protected operation must re-resolve active application state. Authorization and related
database writes share a transaction; last-admin changes serialize the check and update.
An admin role alone does not satisfy an owner/resource check. Changing browser storage,
URL IDs or client role fields must not grant access.

## Files and revocation

Private files use opaque identifiers mapped inside the backend, not user-supplied paths.
They live outside both the public frontend and legacy storage roots. Each delivery request
checks current resource permission before opening the file. Public static/download aliases
must never offer an alternative path. New unowned legacy records are not silently assigned.

Revocation denies **subsequent requests**. Neither a server nor UI can recall bytes a recipient
already downloaded, recorded or copied. A stream authorized before revocation may finish.
The browser should release its in-memory Blob URLs when leaving a view or signing out;
this reduces accidental reuse but is not a DRM or retroactive confidentiality guarantee.

Scoped grants are additive. Revoking one grant does not revoke independent grants; the
explicit revoke-all operation must handle that distinction atomically. Review grants may
target an original recording or a result, with no automatic permission for sibling files.

## Browser authentication

Use only official Firebase authentication calls; do not store application passwords or
manually copy ID/refresh tokens to storage. The selected SDK-managed tab/session persistence
supports refresh restoration but remains JavaScript-readable and vulnerable to same-origin
XSS. It is not an HttpOnly session. A future BFF/cookie design would require CSRF handling
and a separate reviewed contract, not an undisclosed parallel authentication mechanism.

The API client confines bearer requests to same-origin `/api`, rejects arbitrary URLs and
redirects, distinguishes401/403, and must clear stale account data across identity changes.
Provider error messages must be mapped to safe UI text, not logged/rendered verbatim.
Demo personas are available only in an explicitly selected development mode, never as a
production sign-in bypass. Live mode must not fall back to fictional recordings or results.

## Required before production approval

- Genuine selected-project Web App, Google/email providers, authorized origins and email
  action flow inventory/configuration; harmless read check after user-operated CLI consent.
- Approved least-privilege Admin SDK credentials on the server; no keys committed or passed
  through chat. Verify revoked/disabled/wrong-project behavior with designated test identities.
- Real Google sign-in for the intended primary account, backend-derived UID confirmation,
  explicit bootstrap approval, admin access and a normal-user403 check.
- Reviewed own-server routing, HTTPS, host/proxy trust, request limits, CSP/security headers,
  rate limiting and safe cache behavior. Existing unrelated Axora containers stay unchanged.
- Private storage permissions, retention/backup/restore procedure and legacy ownership
  reconciliation. No existing database or recordings reset during M1.
- Real cross-account browser/API/media and revocation checks; mock evidence stays labelled.
- ML job/result integration and compatible-device testing are separately evidenced; an
  unavailable executor must not masquerade as successful ensemble processing.

No DNS change, deployment, patient/participant collection or external data upload is authorized
by this checkpoint. Test WAVs must be synthetic fixtures, never private recordings.
