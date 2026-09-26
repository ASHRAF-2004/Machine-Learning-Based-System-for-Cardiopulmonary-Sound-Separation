# Firebase current-account verifier (Cloud Run)

This is a deliberately small, independently deployable Firebase identity check.
It is not the StethoFuse API and does not decide application roles, ownership,
sharing, analyst assignment, or recording access. It accepts one Firebase ID token,
checks its signature/expiry/revocation and current Firebase Auth user state, and
returns only the verified UID, email, and verification boolean. It has no
enumeration or Auth mutation routes and suppresses HTTP access logs.
Email and verification state are required by the existing local account-sync
contract; no display name, provider list, claims, roles, or profile is returned.

## Current state

Source and pinned/hash-locked dependencies are prepared. Local tests use injected
mock Firebase boundaries; no Cloud Run service, service account, custom IAM role,
Artifact Registry repository, image, or project IAM change has been created. The
production service has not been deployed or verified live. The self-hosted API
fails closed if `STETHOFUSE_FIREBASE_VERIFIER_URL` is missing/unavailable.

## Trust boundary and IAM

The self-hosted API validates Firebase's RS256 JWT locally against Google's public
Firebase signing certificates and checks audience, issuer, `sub`, `exp`, `iat` and
`auth_time`. It then posts the token over HTTPS to the exact Cloud Run `*.run.app`
service URL. No Google credential is needed on the self-hosted server. Cloud Run
uses native Application Default Credentials from a dedicated user-managed service
account. Do not set `GOOGLE_APPLICATION_CREDENTIALS` or mount any service-account
key.

The Admin SDK operation requiring Google authorization is current-user lookup:
`auth.get_user(uid)`. `verify_id_token(check_revoked=True)` also reads that user's
record to detect revocation/disablement. Both require `firebaseauth.users.get`.
Signature verification uses public certificates and requires no privileged Google
API. The implementation performs no Firebase Auth user writes, enumeration, email
sends, or custom-claim operations. `firebaseauth.users.get` is supported in
project-level custom roles; the proposed dedicated custom role contains exactly
that permission, rather than the broader predefined Firebase Authentication
Viewer role. The role belongs only to the dedicated
`stethofuse-auth-verifier` service account on project
`stethofuse-c18cd-3cca0`.

The service is intentionally publicly invokable because the self-hosted host must
not receive a second Google identity credential. This is safe only as a narrow
token-check API: malformed/expired/revoked/disabled/unverified tokens are rejected;
the signed token determines the only UID looked up; there is no UID parameter,
listing route, profile expansion, or role data. HTTPS is provided by Cloud Run.
Maximum instances, concurrency, body-size limits, short request limits, and
suppressed request logs bound resource use; they are not a distributed rate limiter.
Residual abuse by holders of valid project tokens remains possible. Do not expose
any additional operation here. Cloud Armor or gateway-level rate limiting would
be a separately reviewed future hardening if observed abuse warrants the added
infrastructure. A certificate fetch is bounded to 5 seconds, the self-hosted HTTP
client to a 4-second connection / 38-second I/O timeout, and Firebase Admin calls
to 15 seconds per request. The Cloud Run request deadline is 45 seconds. SDK
retries can outlast the client; the client still rejects the request on timeout.
Neither a failed check nor a previous success is cached as authorization.
Body/header logging and SDK debug logging must stay disabled. Cloud Run platform
request metadata logs are distinct from the disabled Uvicorn access log; never
send tokens in URL/query strings or enable HTTP body/header tracing.

## Local checks

From `implementation/`, install the pinned dependencies in an isolated environment
using the existing lock, then run:

```sh
python -m pytest -q tests/test_auth_verifier_service.py tests/test_firebase_token_boundary.py
```

Those tests inject a controlled identity boundary and exercise an RSA-signed test
JWT with generated test keys. They are mocked/local cryptographic tests, not a live
Firebase or Cloud Run acceptance result. Never use a real ID token in unit-test
fixtures or shell arguments.

## Proposed resources and deployment (not executed)

The following is a prepared change, not authorization to run it. Review Cloud Run
public invocation policy and the Firebase Auth custom role at the final infrastructure
gate. Region `asia-southeast1` (Singapore) is the intended low-latency region. Use a
commit-pinned image in Artifact Registry, and deploy the service into the existing
Firebase/GCP project; do not create a new project.

```sh
PROJECT_ID=stethofuse-c18cd-3cca0
REGION=asia-southeast1
SERVICE=stethofuse-auth-verifier
SERVICE_ACCOUNT=stethofuse-auth-verifier@${PROJECT_ID}.iam.gserviceaccount.com
REVIEWED_COMMIT="$(git rev-parse HEAD)"  # Confirm this clean revision is approved first.
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/stethofuse/auth-verifier:${REVIEWED_COMMIT}"

# These are Google Cloud writes and are intentionally NOT run during preparation.
gcloud services enable run.googleapis.com artifactregistry.googleapis.com --project "$PROJECT_ID"
gcloud artifacts repositories create stethofuse --repository-format=docker \
  --location "$REGION" --project "$PROJECT_ID" --description="StethoFuse reviewed runtime images"
gcloud iam service-accounts create stethofuse-auth-verifier --project "$PROJECT_ID" \
  --display-name="StethoFuse Firebase current-account verifier"
gcloud iam roles create stethofuseFirebaseUserReader --project "$PROJECT_ID" \
  --title="StethoFuse Firebase user reader" \
  --description="Read a token's current Firebase Auth user for revocation and status verification" \
  --permissions=firebaseauth.users.get --stage=GA
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="projects/${PROJECT_ID}/roles/stethofuseFirebaseUserReader"

# Build/push the reviewed image using an owner-authorized Artifact Registry writer.
gcloud auth configure-docker "${REGION}-docker.pkg.dev"
docker buildx build --platform linux/amd64 \
  --tag "$IMAGE" --push deploy/auth-verifier

gcloud run deploy "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
  --image "$IMAGE" --service-account "$SERVICE_ACCOUNT" \
  --no-invoker-iam-check --ingress all --port 8080 --cpu 1 --memory 512Mi \
  --min 0 --max 2 --max-instances 2 --concurrency 8 --timeout 45s \
  --startup-probe='httpGet.path=/health,httpGet.port=8080,periodSeconds=10,timeoutSeconds=2,failureThreshold=12' \
  --set-env-vars "FIREBASE_PROJECT_ID=${PROJECT_ID}" \
  --tag=auth-verifier-candidate
```

These commands assume the named resources do not exist; describe them first and
reuse matching resources on a retry. Confirm the existing project's billing state
and estimated usage with the owner; do not silently link a billing account.
The first deployment exposes only this token-gated service and serves its initial
revision immediately. It does not connect the self-hosted app or publish StethoFuse.
For later revisions, add `--no-traffic` and verify the tagged revision before a
reviewed traffic switch. Obtain the service URL with:

```sh
gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
  --format='value(status.url)'
```

After inspecting the deployed candidate revision's URL, run health, invalid-token, valid-token,
disabled/revoked and unverified-email checks using approved disposable test
identities. Set the exact service URL in the external self-hosted env only after
acceptance. All commands remain behind the owner infrastructure approval gate.
Use no email/UID lookup endpoint.

The deployer needs scoped Cloud Run/Artifact Registry write access and
`iam.serviceAccounts.actAs` on this dedicated account; those deployer permissions
are separate from the runtime service identity. Do not grant them to the service
account. Public invocation uses Google's supported `--no-invoker-iam-check` setting;
the application still requires a Firebase ID token. Do not override organization
policies that prohibit this setting. If public invocation is blocked, stop without adding a
long-lived credential to the self-hosted API.

## Rotation, rollback, and removal

There are no private keys to rotate. The custom role can be revoked by removing its
project binding; disabling the service account or removing Cloud Run traffic also
fails API authentication closed. Keep the prior Cloud Run revision until the new
revision passes verification. Roll traffic back to the recorded previous revision;
if the service is new, re-enable its invoker IAM check to disable public access:

```sh
gcloud run services update "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --invoker-iam-check
gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="projects/${PROJECT_ID}/roles/stethofuseFirebaseUserReader"
```

Both commands intentionally fail application authentication closed; do not fall
back to developer credentials or skip revocation checks. Delete the service only
after the API no longer references its URL. Remove the
custom role binding first, then the unused service account, custom role and image
repository in a separately reviewed cleanup. Never delete an identity/resource
still used by another service.

References: [Firebase ID-token verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens),
[Firebase Auth IAM permissions](https://docs.cloud.google.com/iam/docs/roles-permissions/firebaseauth),
[custom role permission support](https://cloud.google.com/iam/docs/custom-roles-permissions-support),
[Cloud Run service identity](https://docs.cloud.google.com/run/docs/securing/service-identity),
[Cloud Run public invocation](https://docs.cloud.google.com/run/docs/authenticating/public).
