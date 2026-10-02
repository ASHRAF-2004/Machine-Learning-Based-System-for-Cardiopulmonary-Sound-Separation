# Roles, sign-in and account provisioning

Confirmed policy, 26 September 2026. Firebase identifies the person; the StethoFuse
backend database determines their application role and permitted files. This guide
describes the actual M1 role controls and labels later workflow capabilities separately.

## Who can register and sign in?

| Role | Public signup | Sign-in | Authority |
| --- | --- | --- | --- |
| Healthcare Staff (`healthcare_staff`) | Yes; every newly onboarded account starts here | Email/password or Google, using a verified identity and active application account | Own recordings and permitted resources; explicit sharing/assignment; personal settings |
| Audio Analyst (`audio_analyst`) | No privileged signup; an existing administrator assigns this role to an onboarded account | Same sign-in page/providers; role is loaded from the backend | Personal workspace plus review of explicitly assigned resources; no global recording access |
| Administrator (`admin`) | No admin signup; first admin uses trusted server setup, subsequent admins may be promoted by an existing admin | Same sign-in page/providers; no separate admin password or login bypass | Account role/status management, safe operational metadata and audit access; no automatic access to another person's audio |

Google sign-in may create a new identity on its first use. That still creates only a
Healthcare Staff application account. Email/password users must verify their email
before accessing the protected workspace. Having a Google account is not an application
role, and Healthcare Staff is a workflow label, not proof of professional qualification.
Suspended/disabled accounts and unverified identities cannot use protected APIs.

There is no public role selector, automatic first-user administrator, email-based admin
rule, browser-storage authorization, or Firebase/Google infrastructure-permission mapping.
All three roles can own recordings; all three need ownership or a valid grant for private
content. Processing through the ensemble is the intended common workflow, but the real
ensemble executor and connected-device capture remain unavailable in this M1 release.

## Primary administrator — already initialized locally

The approved primary person signed in with Google. The official Firebase directory
confirmed an enabled, verified Google identity; its UID matched the active local account.
The existing trusted `scripts/bootstrap_m1_admin.py` then initialized the first admin
in the isolated development database. One permanent bootstrap marker and one
`admin.bootstrap` audit event exist. Repeating the same operation made no change.

This was a backend role change, not a change to Firebase IAM or custom claims. The
bootstrap is not an HTTP endpoint, cannot initialize a second admin and cannot restore
a demoted first admin. Do not remove its marker or edit the database to bypass it.
No production database or deployed application was changed.

## Add another administrator (confirmed: existing admins may promote)

1. Obtain explicit approval for the intended person. They create a normal account or
   use Google on the regular sign-in page, complete verification where applicable, and
   enter the application once. They initially receive Healthcare Staff.
2. Have them provide their **application User ID**, not a password, token or reset link.
   Confirm the intended identity and exact account independently.
3. Sign in as an existing active Administrator. Open **Administration → Users**
   (`/app/admin/users`). Search by the application User ID; check the account details.
4. Set **Role → Administrator**, leave the intended status **Active**, choose
   **Confirm changes**, and check the exact target in the confirmation dialog.
5. FastAPI verifies the acting administrator's current Firebase account, requires an
   existing target whose verification came from its own authenticated provider session,
   checks the confirmed target, and commits the role/status change with an `account.changed` audit
   event in the same transaction. A normal user cannot
   invoke this operation successfully, even with a forged request or hidden UI exposed.
   The token-only Cloud Run boundary does not look up arbitrary target UIDs. Target
   verification in this operation is stored provenance, not a fresh provider lookup;
   the target's next protected request must pass current revocation/disabled/email checks
   before the new local role can be used. A provider-disabled/deleted account cannot use
   its role. This distinction supersedes the earlier ADC-based target recheck design.
6. The promoted person refreshes or refocuses their application tab. Account roles are
   fetched from the backend (also periodically), so no Firebase custom-claim edit or
   new Google account is required. Verify that Administration opens for them.
7. Review the audit entry. Repeat privileged-access and ordinary-user-denial checks
   before treating a production provisioning workflow as accepted.

To appoint an analyst, follow the same steps but select **Audio Analyst**. Separately,
the recording owner must issue a review assignment for the particular original/result;
the role alone grants no recording access. Changing a role does not transfer ownership.

An administrator can also demote/suspend accounts through these server-checked controls,
but the **last active verified administrator cannot be demoted, suspended or disabled**
through application account management. There is no arbitrary two-admin limit. Provider-
side deletion/disablement is outside that database safeguard; exceptional recovery must
be reviewed by the trusted operator, not solved by a public recovery/admin bypass.

The current administrator is deliberately excluded from editable role and status controls.
The User Management row shows the backend-authoritative role with a **You** marker and
the active status, while FastAPI rejects any self role/status mutation with `403` before
the last-administrator calculation. Another active administrator must perform such a
change. This is a security rule, not a presentation-only restriction.

## Actors for the application use-case diagram

The three primary authenticated human actors are **Healthcare Staff**, **Audio Analyst**
and **Administrator**. They share a common **Authenticated User** abstraction for
sign-in/session, profile and own-workspace use cases. Authenticated User is a diagram
abstraction, not a fourth stored role. Analyst and Admin do not inherit unrestricted
access to other users' files.

Additional actors depend on the diagram boundary:

- **Visitor / unauthenticated user:** public information, ordinary account registration,
  sign-in and recovery. Never associate Visitor with privileged-role registration.
- **Firebase Authentication:** supporting external identity system. Google may be
  shown behind Firebase in an authentication detail diagram, not as a human role.
- **Compatible recording device:** external input actor only in the intended device-
  capture use case; physical-device integration remains planned, not verified.
- **Trusted deployment operator:** separate setup/operations actor for first-admin
  initialization and deployment. This is not a publicly selectable application role.

FastAPI, the database, private storage and ensemble engine are internal components in
the StethoFuse application boundary, not additional people/roles. A patient is not a
current authenticated actor; do not imply a patient portal or authorize data collection.
Preserve submitted FYP1 diagrams; document this clarified FYP2 model separately.

## Evidence and limits

- **LOCAL REAL PROVIDER:** official directory checks of the intended Google identity,
  matched UID-linked application account, successful trusted bootstrap and backend
  `require_admin` check; one active admin, one audit event, unchanged same-user retry.
- **User-reported browser result:** successful Google sign-in in the user's normal
  browser. The embedded browser previously failed; do not repeat cloud consent.
- **Before hardening, MOCK/local regression:** 22 tests plus 21 subtests passed using the focused selection
  below (64 deselected). Covers default role, non-admin denial, bootstrap/last-admin
  controls and privacy boundaries. It is not a real second-account permission test.
- **Final MOCK/local regression after hardening:** 99 tests plus 26 subtests passed;
  `../.local/m1-tests/admin-provisioning-junit.xml` relative to this repository.
  Thirteen new API cases exercise successful promotion/demotion, exact audit actors,
  unknown/local-unverified targets, currently unverified/disabled/deleted/mismatched
  provider identities, provider outages and rollback when auditing fails. No roles
  change on these denied requests. This does not impersonate a real Firebase user.
- **Still to verify:** post-promotion real-browser admin API success; a distinct real
  ordinary account receiving 403 for the same admin request; real email/password,
  recovery/verification delivery and remaining M1 acceptance. No production test.

From the implementation repository, using the prepared workspace environment:

```sh
../.local/venvs/backend-smoke/bin/python -m pytest \
  tests/test_access_foundation.py tests/test_m1_api.py tests/test_m1_operator_safety.py \
  -q -k 'admin or bootstrap or role or signup or registration'

# Final full bounded backend regression (no live provider requests):
../.local/venvs/backend-smoke/bin/python -m pytest \
  tests/test_access_foundation.py tests/test_m1_api.py tests/test_m1_operator_safety.py \
  -q --junitxml=../.local/m1-tests/admin-provisioning-junit.xml
```

One existing Starlette TestClient deprecation warning is unrelated to the role mutation.
Only narrow backend verification guards and regression tests changed beyond the account
bootstrap and documentation. Approved owl, frontend code/artwork, ML core and original
FYP1 are unchanged. Private UID/database/credential values are not report evidence.

The current-provider recheck uses the existing read-only Admin SDK lookup, following
[Firebase's UID-based user lookup documentation](https://firebase.google.com/docs/auth/admin/manage-users#retrieve_user_data).
No new Firebase account, provider permission or custom claim is created by promotion.
