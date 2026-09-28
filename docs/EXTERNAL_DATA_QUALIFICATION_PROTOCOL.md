# External-data qualification — pre-training protocol

Status: DATA QUALIFICATION ONLY. No external model result exists. T9 SEALED.
The original T8 specification/checkpoint remain intact. The prior HLS-only
grouped-family refit is paused as a fallback, not deleted or executed.

## Initial bounded acquisition

Official, public candidates: CirCor DigiScope 1.0.3 (ODC-By 1.0) for heart;
SPRSound at Git commit `bca1e51422a42a042441010081519610ef3845d0`
(CC BY 4.0) for lung. These are provisional **Tier B**, never clean isolated
references. No audio from an HLS mirror or any T9 partition is acquired.

Before waveform inspection, choose 40 patient groups per dataset, at most two
recordings per group. Deterministic SHA-256 ordering keyed by seed 20260928;
round-robin populated metadata strata. CirCor strata use released age category,
murmur status and campaign; merge Additional ID links before sampling. SPRSound
uses only canonical BioCAS2022 training files initially; subject/age/sex come
from the officially defined filename, not inferred demographics. Strata use
age domain and recorded sex, with deterministic recording/site rotation.
The full audit includes poor-quality/unknown controls: no waveform-based
replacement of selected samples. Record every failed/excluded sample.

CirCor candidate training intervals must be continuously covered by annotation
states 1–4 for at least 8 seconds. This retains systolic/diastolic morphology
and murmurs; do not train on S1/S2-only fragments or concatenate intervals.
SPRSound Poor Quality recordings are excluded from supervised pretraining.
Keep normal/adventitious labels as released. An annotation-quality pass does
not establish absence of opposite-source leakage.

Both: immutable originals, official SHA-256 (CirCor) or pinned Git blob
verification (SPRSound), own SHA-256 receipts, deterministic anti-aliased 4-kHz
mono float32 derivations, no independent amplitude normalization before the
existing crop-RMS mixture rule. Exclude unreadable/nonfinite/digital-silent,
near-zero, materially clipped, missing-subject, duplicate, or too-short data
with explicit reasons. No repetition/padding to manufacture an 8-second source.
Quality statistics cannot automatically certify source purity.

Choose training eligibility only after source protocol, annotation, technical
quality and bounded signal inspection. If purity remains inadequate, do not
make fake clean targets; reject that training path. A later pilot protocol
must freeze subjects, sampling, update budgets and an HLS grouped-transfer
adoption threshold **before treatment training**. No optimizer step is
authorized by this qualification file alone.

## Safety and tooling

M0: configured Graphify, cloudflare-api/bindings/builds/docs/observability,
cua_repl, node_repl, openaiDeveloperDocs and resend all responded to read-only
checks. Hosted codex_apps GitHub, Figma, Gmail, Drive, Notion, Canva and Zapier
checks responded; codex_tui and web responded. Zapier has no enabled actions.
CUA has no attached browser surface, but xdg-open launched official MCP docs in
the user's existing Brave session, confirmed by the visible window title.
No login/authentication failure occurred. GitHub MCP and CLI identify
ASHRAF-2004. No production configuration/content was changed.

Graphify describes historical commit 559ddba, not the current offline ML code;
it was consulted first, then narrow current-file reads were used. Implementation
178ff9326247f11e424bfe3796381178e40fc7e7 and documentation
6a168c60441255c88ff0bfbf6df2ba4bd3c4b80f matched remotes and were clean at start.
Original T8 checkpoint/spec and 86-row non-test allowlist hashes matched.
About 519 GiB was available on the existing local filesystem. Large artifacts
remain under ignored `.local/datasets/`; no audio/checkpoint is committed.

Unselected restricted MSCAD is not acquired (noncommercial terms, no isolated
reference qualification). Official ICBHI download host has an expired TLS
certificate in direct access; do not disable TLS validation or use an
unverified mirror. Neither blocks qualification of the public candidates.
