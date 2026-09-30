# Plan: four-screen Frost Studio proof

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
