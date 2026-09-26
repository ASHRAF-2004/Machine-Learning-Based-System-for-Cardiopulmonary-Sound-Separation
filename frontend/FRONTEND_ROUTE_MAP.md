# StethoFuse route and role map

Base URL: **http://127.0.0.1:4180** after `npm run dev` in `implementation/frontend`. These are implemented screens and demonstration states, not declarations that backend authorization or real provider flows exist. See `FRONTEND_INTEGRATION.md` for the boundary and run/build commands.

## Shared access rules

2026-09-24 continuation: existing routes now share the winter-glass design. `/app/processing/:jobId` is owner-only. Explicit recipients can open a recording and its available results, not job controls/history. Administrator reassignment creates a fresh ID after revoking the old assignment; previous notes/authorship remain in their original history and are not transferred to the replacement reviewer.

- Public routes need no account. Public signup never offers a privileged role.
- `/app/*` currently requires an explicitly selected development persona. Normal production builds do not expose this bypass; live authentication remains unconfigured.
- Disabled and unverified/pending accounts route to their recovery screen. Analyst/admin routes also require the matching role.
- Every role has a personal workspace. Audio/result access requires ownership or an active explicit share/assignment; administrator status is not an audio grant.
- Query-state selectors/persona controls exist only when `DEMO_ENABLED` is true. State URLs below are development previews, not real action-code validation.
- Unknown public routes show 404. Unknown account routes go to 404; missing workspace objects show an unavailable/not-found screen without fabricating data.

## Public, authentication and utility routes

| Route | Implemented content / exact preview |
|---|---|
| `/` | Approved winter hero, logo, owl, Get started → registration, Sign in → login; workflow, scope and support. Anchors `/#how-it-works`, `/#research-scope`, `/#support`. |
| `/login` | Validation, password visibility, safe return, unavailable real auth, development personas. `?state=ready`, `submitting`, `failure`, `offline`; `#demo-personas`. |
| `/register` | Name/email/password/confirmation/terms, password rules, no role choice. `?state=ready`, `submitting`, `failure`, `success`. Success is a demo preview, not account creation. |
| `/forgot-password` | Generic acknowledgment, cooldown, errors. `?state=ready`, `success`, `throttled`, `failure`. No real email. |
| `/reset-password` | Matching-password validation, invalid/expired/already-used link states. `?state=valid` (or `ready`), `expired`, `invalid`, `used`, `failure`, `success`. Production without provider validation is invalid. |
| `/verify-email` | Pending, resend cooldown, return navigation. `?state=pending`, `success`, `verified`, `expired`, `invalid`, `failure`, `throttled`. No actual verification mutation. |
| `/auth/action` | Reset/verification mode routing; missing/unsupported-mode guidance. `?mode=resetPassword&state=expired`, `?mode=verifyEmail&state=invalid`. Raw action codes are not rendered, persisted or forwarded. |
| `/auth/callback` | Google completion/unavailable, cancellation, linking conflict. `?state=completing`, `cancelled`, `error`, `link-conflict`. Completing ends in unavailable, never fake success. |
| `/account-disabled` | Disabled explanation, sign-out / recovery navigation; no automatic reactivation. |
| `/session-expired` | Expired session and safe return, e.g. `?returnTo=%2Fapp%2Frecordings`. Retains fictional local drafts. |
| `/privacy` | Draft privacy presentation, demo handling and access boundaries. |
| `/terms` | Draft research/education terms; no clinical approval claim. |
| `/403` | Access denied and safe navigation. |
| `/404` | Missing page and return navigation. |
| `/500` | Failure guidance/reload. Shared runtime error boundary also offers reload. |
| `/offline` | Offline guidance/network retry feedback, not fictitious successful sync. |
| `/maintenance` | Maintenance presentation/retry guidance; does not change server maintenance. |

`/login?returnTo=%2Fapp%2Frecordings` demonstrates a safe return. External origins, malformed paths and traversal attempts fall back to an allowed home; queries/fragments are not forwarded.

## Personal recording workflow — each signed-in role, scoped to itself

| Route | Implemented interaction / seeded example |
|---|---|
| `/app/dashboard` | Own summary, recent records/jobs, new-recording actions and updates. |
| `/app/recordings` | Own list, search/filter/sort, empty state and details. Staff accounts have different records. |
| `/app/recordings/new` | WAV upload or explicit simulated device capture. |
| `/app/recordings/new/upload` | Local WAV checks, metadata, validation and save; no private upload. |
| `/app/recordings/new/record` | Simulated connect/start/stop/preview/save; normal, denied, missing device, unsupported, silence, clipping or disconnect scenario. No real hardware request. |
| `/app/recordings/:id` | Authorized details, synthetic playback, metadata, owner controls, ensemble request, deletion confirmation and run history. `/app/recordings/REC-1042` as Amina. |
| `/app/processing` | Own job list and states; navigation does not block local progression. |
| `/app/processing/:jobId` | Own stage/elapsed time, result/error/cancel/retry where allowed. `/app/processing/JOB-2100`. No fabricated percent or ML-speed claim. |
| `/app/results` | Own results/status filters; partial exists in contracts/UI but is not a seeded quality claim. |
| `/app/results/:resultId` | Synthetic original/heart/lung playback, waveforms/spectrogram, downloads and run metadata. `/app/results/RES-3100`. No invented quality scores. |
| `/app/history` | Own processing/activity history, filters and authorized links. |
| `/app/shared` | Sent/received shares, review or listening permission, confirmed revocation removing current recipient access. |

A share does not confer ownership or deletion rights. Job details remain owner-scoped. These are fixture/UI checks; the live backend must independently enforce them.

## Profile, all personal Settings sections, notifications and Help

| Route | Implemented interaction |
|---|---|
| `/app/profile` | Own display information, User ID/provider/status, save/cancel and unsaved-change handling. No tokens/passwords. |
| `/app/settings?section=general` | Display preferences, available English language, timezone/date format, save/cancel. |
| `/app/settings?section=appearance` | Reduced motion, snow and higher contrast within the approved theme. |
| `/app/settings?section=notifications` | Email/job/review preferences; no external delivery implied. |
| `/app/settings?section=security` | Provider presentation, reset guidance, Google-only/link-conflict/reauthentication-unavailable states and fictional sessions. No pretend provider changes. |
| `/app/settings?section=recording` | Default metadata, preferred input/sample rate and playback preferences; not a claim of actual device support. |
| `/app/settings?section=data` | Declared usage/retention, own JSON metadata export, confirmed deletion-request preview. No real account deletion. |
| `/app/notifications` | Own all/unread tabs, mark/read/all, empty state and permission-checked destinations after revocation. |
| `/app/help` | Searchable workflow/access/recovery/accessibility FAQs and safe report-template copying. No ticket sent. |

`/app/settings` defaults to General. Sections are URL-addressable. Dirty forms use the shared unsaved-change guard.

## Analyst review — role and active explicit assignment required

| Route | Implemented interaction / example |
|---|---|
| `/app/review-queue` | Assigned review tasks, states and filters, not global audio discovery. |
| `/app/assigned` | Explicitly assigned/shared recordings and permissions. |
| `/app/reviews/:assignmentId` | Authorized synthetic audio workbench, timestamped notes, draft save, reviewed/re-record decision and confirmation. `/app/reviews/ASN-401` as Sofia. |
| `/app/review-history` | Own decisions/notes and still-authorized assignment links. |

`ASN-401` refers to Amina's `REC-1042`; `ASN-402` to Daniel's `REC-1047`. Revoked/listening-only grants cannot authorize review mutation. Re-record is a workflow decision, not a diagnosis.

## Administration — operational metadata, not automatic private audio

| Route | Implemented interaction / exact preview |
|---|---|
| `/app/admin` | Operational account/job/assignment summary and safe audit activity. |
| `/app/admin/users` | User ID/name/email search; role/status/provider/date filters, sort, clear, pagination. `?q=USR-1002`, `?status=pending`, `?role=analyst`. |
| `/app/admin/users/:userId` | Provider/verification metadata/audit timeline; confirmed role/status changes. `/app/admin/users/USR-1001`; last-admin protection on `USR-3001`. No passwords/reset links/impersonation. |
| `/app/admin/records` | Global IDs, owner/source/status/storage metadata, filters/detail. `?status=failed`. No private notes/audio/plots/downloads due solely to admin role. |
| `/app/admin/assignments` | Owner/recipient/permission/status metadata and permitted revocation; no automatic content grant. |
| `/app/admin/ensemble` | Expert/version/status/provenance, local fusion configuration and audit. Unverified provenance stays pending; no live hot-swap. |
| `/app/admin/audit` | Safe event metadata and action/actor/target/time/outcome filters; `?query=USR-1001`. |
| `/app/admin/settings` | Validated local upload/retention limits and maintenance preference. Does not configure FastAPI or production retention/maintenance. |

The last active administrator cannot be disabled/demoted. There is no arbitrary two-admin cap. Public signup still offers no privileged roles.

## Repeatable demonstration paths

1. Choose Amina at `/login#demo-personas`; inspect own records, switch to Daniel and compare, including refresh. Persona is per tab; non-sensitive fictional metadata persists.
2. Save a small test WAV's metadata or finish simulated capture, request ensemble processing and navigate away. Reopen the job/result; synthetic output remains labelled.
3. Share an owned recording with Sofia for review; switch to Sofia, save timestamped notes and a decision; switch back to inspect history.
4. Revoke the assignment as owner/permitted admin, then revisit its old URL as recipient. A link is not a continuing access grant.
5. As Elias search `?q=USR-1002`, inspect providers, confirm an allowed account change and inspect audit. Directly opening private staff results must not gain access from admin role.
6. Edit then navigate away to test dirty-form protection; use demo session expiry and sign into the same fixture to inspect saved metadata.
7. Use the query previews for expired/used/invalid reset and Google cancel/conflict. No actual email, account creation or credential exchange occurs.

## Executed verification checkpoint

- `tests/public.mjs`: **42 PASS, 0 FAIL**, actual headless Chrome 151.0.7922.137. `evidence/public/results.json` and `REVIEW.md` record evidence.
- Public/auth screenshots were opened and visually inspected at 1440/1920/768/390px. Viewport emulation, not physical mobile testing. Public suite used reduced motion and does not certify owl animation.
- Final shared build, role workflow suites, combined consistency and asset/runtime performance: **pending coordinator's final verification update** here. Merely existing scripts/screenshots do not establish PASS.
- Live Firebase, backend authorization, physical capture, real ensemble outputs and deployment are not implemented/tested in this demonstration.
