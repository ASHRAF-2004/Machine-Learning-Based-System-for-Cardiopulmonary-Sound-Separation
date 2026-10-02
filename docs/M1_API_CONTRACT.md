# M1 local API contract

Canonical base `/api`. Bearer Firebase ID token on every non-public call. No query-string
tokens, client roles/owner IDs, email-based admin switch or fixture fallback. This document
defines the implementation contract; final route/tests/live evidence is in M1_ROUTE_AUDIT.md.

## Identity

- `POST /auth/session` with empty JSON `{}`: verified-UID account sync; new accounts always
  `healthcare_staff`. Existing role/status is never overwritten. Returns the envelope below.
- `GET /auth/me`: same envelope, read-only; `404 account_missing` until session sync.
- `PATCH /auth/me` body `{ "display_name": "Research user" }`: own display name only.
- `GET /preferences` → `{ "preferences": {} }`; `PATCH /preferences` replaces the submitted
  own preference sections (general, appearance, notifications, recording, privacy, accessibility).
  PATCH body is `{ "preferences": { "general": { "language": "en" } } }`.
  These are persisted app preferences, not provider credentials or provider/session controls.

```json
{"user":{"id":"opaque-id","uid":"provider-uid","email":"person@example.invalid","display_name":"Research user","role":"healthcare_staff","status":"active","email_verified":true},"mode":"live","capabilities":{"recordings":true,"sharing":true,"reviews":false,"admin":false,"ensemble":false,"separation":true}}
```

Canonical roles: `healthcare_staff`, `audio_analyst`, `admin`. Status: `active`, `suspended`,
`disabled`. Verification is separate; an unverified identity cannot sync or access protected
data. Firebase controls registration/sign-in/sign-out, Google, verification and recovery.
The server does not create or store passwords. No bootstrap HTTP endpoint exists.

## Records and media

All collection responses are `{ "items": [...] }`. Timestamps are UTC epoch seconds.
Opaque resource IDs, never filesystem paths. Details include only authorized media resources.

- `GET /recordings`; `POST /recordings` multipart: required `file` (WAV), optional `title`.
  No owner/role/client-ID field is accepted. Maximum 25 MiB; mono/stereo PCM WAV.
- `GET /recordings/{id}`; owner-only `PATCH /recordings/{id}` body `{ "title": "New title" }`.
- `GET /media/{resource_id}`: protected bytes, including original/heart/lung and image assets.
  Frontend must authenticated-fetch then create an in-memory Blob URL; revoke it on unmount
  or sign-out. A direct unauthenticated URL receives 401. No public signed URL is issued.
- `GET /jobs`; `GET /jobs/{id}`: owner-only persisted state, never analyst/admin bypass.
- `POST /recordings/{id}/jobs` with `{}`: owner-only, `202` with a durable job.
  `STETHOFUSE_SEPARATION_ENABLED=1` is required (default off); otherwise `503
  separation_unavailable` with no job created. No inference in this request.
  Repeated calls return the same job for this immutable recording/model version,
  including succeeded/failed jobs. There is no public retry/reprocess endpoint.
- `GET /results`; `GET /results/{id}`: authorized persisted results and provenance.
  The worker, not a browser timer, creates them atomically after both outputs verify.

Recording DTO:

```json
{"id":"recording-id","owner_id":"user-id","title":"Research sample","original_filename":"sample.wav","created_at":1790380800,"duration_sec":2.0,"sample_rate_hz":4000,"channels":1,"file_size_bytes":16044,"original_resource_id":"resource-id","resources":[{"id":"resource-id","kind":"original_audio","media_type":"audio/wav","url":"/api/media/resource-id"}],"is_owner":true}
```

`original_resource_id` is null when the requester lacks original access. Shared recording
metadata is a minimal title/format summary; a scoped grant never exposes sibling files.
Job DTO: `{id,recording_id,requester_id,status,created_at,started_at,completed_at,error_code,
stage,attempts,model_version,result_id}`. `result_id` is null until succeeded;
claim tokens and reserved output IDs are not returned. States are queued,
processing, succeeded and failed. Safe error codes/stages describe failures;
no exception text, source samples or filesystem paths are exposed.
Result DTO: `{id,recording_id,job_id,created_at,method_label,provenance,resources,is_owner}`; `resources`
uses the same resource shape. Metadata never claims a measured score not actually stored.

The selected worker is exclusively frozen T8 v2, CPU, 171,313 parameters. There
is no user-selectable algorithm or automatic alternative. It writes 4-kHz mono
IEEE float32 WAVs without clipping/independent output normalization. Heart and
lung each use the existing `GET/HEAD /media/{resource_id}` protection and range
handling. Provenance includes model/spec/checkpoint/code hashes, input/output
hashes, preprocessing, sample count, fixed inference contract, environment,
runtime, worker version/attempt and timestamps. See
[local integration evidence](LOCAL_ML_INTEGRATION.md) and
[worker runbook](../deploy/ML_WORKER_RUNBOOK.md).

## Sharing, assignments and review

- `GET /recordings/{id}/grants`: owner only.
- `POST /recordings/{id}/grants` body `{recipient_id,permission,resource_id?,expires_at?}`;
  `permission` is `read` or `review`. Read defaults to explicit whole-recording access.
  Review requires an exact original_audio or result resource and an active analyst. Recipient must already
  have an application account. No unrestricted user directory is exposed to normal users;
  recipient supplies their app ID out of band.
- `DELETE /grants/{id}`: owner revokes that grant, returns 204. Grants are additive.
- `POST /recordings/{id}/revoke-access` body `{recipient_id,confirmed_recording_id}`: owner
  atomically revokes all grants for that recipient on the recording; returns `{revoked:number}`.
- `GET /assignments`: caller's active analyst assignments.
- `GET /assignments/{id}/review`; `PUT /assignments/{id}/review` body `{decision,notes}`.
  Decision: `pending`, `accepted`, `needs_attention`. Notes maximum 10,000 characters.
  Permission is rechecked within the persistence transaction. Admin status alone gives no access.

Grant/assignment DTO:
`{id,recording_id,resource_id,grantor_id,recipient_id,permission,status,expires_at,created_at,revoked_at}`.
Review DTO: `{assignment_id,resource_id,resource_kind,reviewer_id,decision,notes,updated_at}` (null updated_at
and empty notes before first save). Old assignment IDs/notes are never transferred to recipients.

A result review assignment permits that result's metadata/review, not its sibling
heart/lung files or original. Grant output resources explicitly (or deliberately
grant whole-recording read). Revocation blocks new requests; downloaded bytes
cannot be recalled. UI review reuses these exact rules.

## Administration

- `GET /admin/users` → `{items:[user DTO...]}`.
- `PATCH /admin/users/{id}` body `{role?,status?,confirmed_target_id}` → user DTO.
- `GET /admin/audit` → `{items:[{id,actor_id,action,target_id,created_at}]}`.
- `GET /admin/methods` → safe method catalog and availability, not public.
- `POST /admin/benchmarks` is an explicit honest `503 benchmark_unavailable` in the minimal
  non-ML runtime; it does not silently execute a normal-user ensemble or fabricate results.

No private audio, review notes, passwords/reset links or impersonation through admin APIs.
Last-active-admin changes and bootstrap are atomic trusted-store operations.

## Errors and retired paths

```json
{"detail":{"code":"forbidden","message":"Access denied."}}
```

401: missing/invalid/expired/revoked/wrong-project token. 403: `email_verification_required`,
`account_disabled`, or `forbidden`. 404: `account_missing` / unknown-or-inaccessible object.
409: `last_admin` or invalid state. 413: `upload_too_large`. 422: sanitized `invalid_request`
or specific validation error; supplied values are not echoed. 503: unconfigured provider/store, `separation_unavailable`,
`benchmark_unavailable`. No raw provider exception, token or filesystem path in errors.

Public: `/health`, `/api/health`, safe API-root status and non-private static app assets.
Legacy upload/separate/result/download/history paths are safely retired with 410 and no
data; `/models` and `/methods` use the admin-only catalog. `/visualizations/*` is not mounted
and returns 410. The default application entrypoint remains `app.main:app`, now M1-protected.

All JSON/media success and expected error responses use `Cache-Control: private, no-store`,
`X-Content-Type-Options: nosniff`, and `Referrer-Policy: no-referrer`. Media GET and HEAD apply
the same permission check before full or single-range responses. Revocation stops subsequent
requests; it cannot recall an already opened stream, saved download, or client-owned Blob.

Account demotion removes analyst review-write authority, not separate explicit read grants.
Revoking one grant removes only that grant; use the confirmed atomic revoke-access operation
when all current grants for a recipient/recording must be revoked. API roles/statuses above
are canonical; frontend display labels must not be sent as authority (`staff`/`analyst` are
not API roles, and frontend pending verification is not the API's suspended state).
