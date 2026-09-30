# Current plan: LOCAL identity foundation — 1 October 2026

Owner approved the integrated core/feedback UI and instructed continuation until
the next reviewable working slice. Execute L0 and only the profile/core display
connections it needs, not the entire handoff. Normative scope/verification:
`docs/LOCAL_IDENTITY_FOUNDATION.md`. Tasks tracked in `tasks/todo.md`.

1. Add missing-only identity metadata and public references in migration003.
   Keep underlying UID/PK/FK values, authorization predicates and protected media.
2. Complete existing authenticated profile PATCH with canonical one-change handle;
   database-enforced uniqueness and transaction tests before UI connection.
3. Reuse approved settings/profile material/layout, real identity and copyable
   public IDs. Connect recording title/public-ID search. No handle-login or lookup.
4. Prove migration preservation/restart, concurrent rename, independent privacy,
   real local profile persistence and responsive Frost/Midnight. Standalone builds.
5. Prepare a separate persistent local review namespace, preserve the owner's
   current review DB/browser/data, update evidence/Git, stop for hands-on review.

No production schema/app/provider changes, public directory, avatar backend,
export/delete/unlink, global Insights, owl flight, ML training or T9. No dependencies.

# Preserved completed plan: four-screen Frost Studio proof

The owner's explicit implementation order is the prototype authorization.
Full-app/identity/privacy/backend work waits for visual approval.

1. Foundations: isolated dev entry, tokens, shell/primitives and synthetic fixture
   contract. Verify TypeScript and normal production-entry isolation.
2. Overview slice: unfinished work, identity, recent list. Capture/critique/fix.
3. Library slice: reusable recording rows, search/four filters/cards. Capture twice.
4. Audio detail slice: abortable auto-load, GainNode/compressor, actual sample
   analysis and source UI. Inspect Frost/Midnight/mobile, test permission states.
5. Profile slice: identity, themes/audio and explicitly local privacy/avatar
   prototypes. No migration or real export/delete. Capture/critique/fix.
6. Review evidence:7 final screenshots, focused checks/build, five-axis review,
   exact design freeze and Luna phases. Commit/push, update PAUSE, stop.

Dependencies: foundations → each screen → review. Sequential shared tokens.
Risk: existing auth/session coupling; mitigate isolated provider and unchanged
API client. Risk: fabricated signal analysis; compute from synthetic WAVs.
Risk: flight assets absent; freeze requirements, do not fake static-poster flight.
