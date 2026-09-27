# NeoSSNet and fallback qualification — 28 September 2026

**Status: planning / research qualification only.** This note follows the
bounded NeoSSNet diagnosis. No author email was sent; no new audio was read,
scored, or copied; no training, fine-tuning, checkpoint download, production
change, or ensemble redesign occurred. The fixed 50/50 mask ensemble remains
frozen and **not qualified for integration**.

## Author clarification request

**Prepared / not sent.** The contact `Yang.Poh@monash.edu` is listed in the
original NeoSSNet author repository README's support/known-issues section. It is
the original project's own contact source, not a guessed address. The request
text is recorded in the workspace `PAUSE_NOTES.md` for owner review.

It asks for (1) distinct code and checkpoint permissions for university
research, wrapping/modification, public demonstration, deployment, and
redistribution versus setup-time download; (2) the checkpoint/fold/config/run
identity for Table VII's baseline; (3) channel order; (4) a small lawful native
reproduction fixture and expected outputs; and (5) clarification of the
notebook's SI-SDRi/category-median aggregation, permutation handling, and any
projection/scaling. No request for identifiable or restricted patient data is
made.

NeoSSNet code/weights remain **RESEARCH QUALIFICATION ONLY**. Production use and
redistribution remain **BLOCKED pending explicit rights clarification**. No
checkpoint or author source was added to Git.

## Focused fallback shortlist — candidates, not selected replacements

| Candidate | Provenance, code rights and artifact | Fit and main risks |
| --- | --- | --- |
| **Periodicity-informed NMF / LingoNMF** | Torabi, Shirani, & Reilly's 2025 arXiv preprint and 2026 journal article; [author repository](https://github.com/Torabiy/LingoNMF) declares an MIT `LICENSE`. It provides Python/MATLAB code; no neural checkpoint is needed or listed. The journal abstract reports evaluation on synthesized mixtures and clinical-manikin recordings. | Closest apparent domain match to HLS-CMDS and modest implementation burden. The published headline gains are SDR/SAR/SIR (including maximum gains), **not directly comparable to our fixed-label SI-SDR/SI-SDRi means**. The core function receives `fs` but no single deployment input-rate contract was confirmed; first qualification must use a frozen 4-kHz input or reproduce the authors' stated preprocessing. The repo's core routine is periodicity-penalized NMF; LLM use is described in a separate notebook/workflow, whose exact role at inference needs confirmation. The README also says “All rights reserved” while the repository has an MIT license; code rights appear explicitly MIT, but included audio/MATLAB data rights are separate and unclear. Do not use bundled data. Public paper/repo evaluation may overlap the same manikin domain; exact source/test overlap must be audited before any evaluation. **Best next small qualification candidate; not accepted yet.** |
| **Grooby neonatal NMF / NMCF** | Grooby et al. (2023), *IEEE Journal of Biomedical and Health Informatics*, DOI `10.1109/JBHI.2022.3215995`; [author code repository](https://github.com/egrooby/Heart-and-Lung-Sound-Separation) declares GPL-3.0. MATLAB implementation is public; no ready checkpoint. The code has a separately linked GPL-3.0 signal-quality dependency. | Direct neonatal chest-sound relevance and source-level reference-informed NMF/NMCF. The associated preprocessing resamples mixed-rate respiratory recordings to 11,025 Hz, so conversion from our archived 4-kHz material and an apples-to-apples protocol must be validated. NMCF uses high-quality reference sounds during the factorisation and the paper reports median 28.3 s per 10-s input (NMF 342 ms), so NMCF is too slow for normal interactive use without job execution. Requires resolving rights/access for the high-quality reference corpus and GPL distribution obligations before app inclusion. Different data/protocol; published advantage is not evidence of StethoFuse target performance. **Viable research comparator/backup, not selected.** |

These are the only two candidates in this pass with an explicit repository
license and direct cardiopulmonary-separation provenance. Existing generic NMF,
Fixed Filter and VMD remain local comparators, not newly qualified fallbacks.
Standalone `vmdpy` is MIT-licensed and maintained through `sktime`, but it is a
generic decomposition primitive rather than a new heart/lung separator. The
public Colombian focused-NMF implementation and PC-DAE repo have no declared
software license; the complete DAE–NMF–VMD paper materials are not an openly
licensed, ready-to-use implementation. They are **not reuse-qualified**. The
recent XVAE-WMT preprint is too new to qualify here: no matching author code,
license, or checkpoint was verified.

No candidate has been load-tested or benchmarked during this qualification
step. The first follow-up should be a **small development-only load/run and
provenance check of LingoNMF's code path**, without importing its bundled audio
or tuning against any validation/test material. This does not alter the
ensemble decision.

## Source-data and leakage plan

Counts below come from the existing ignored metadata manifest
`.local/ensemble/qualification/manifest.json`; source audio and held-out samples
were not read for this update. The current family-separated manifest contains:

| Source | Development | Validation | Locked test |
| --- | ---: | ---: | ---: |
| Heart (HS) | 36 files / 6 sound families | 9 / 2 families | 5 / 2 families |
| Lung (LS) | 36 files / 4 sound families | 5 / 1 family | 9 / 1 family |

The frozen test source IDs are HS `F_S4_RC`, `M_S4_LUSB`, `M_AVB_LLSB`,
`M_AVB_A`, `M_AVB_RC`; and LS `M_CC_LLA`, `M_CC_LUA`, `M_CC_RLA`, `F_CC_LMA`,
`F_CC_RLA`, `F_CC_RMA`, `F_CC_LLA`, `M_CC_LMA`, `F_CC_LUA`. They belong to the
AV Block/S4 heart and Coarse Crackles lung families. Do not load them into
training, inspect their waveforms, use them for preprocessing/model selection,
or generate metrics before the final protocol and expert are frozen.

The current grouping is by sound-type family, **not by patient/subject**. HLS-CMDS
is clinical-manikin audio and the metadata does not identify independent human
subjects. It therefore supports held-out sound-family evaluation, not a claim
of subject-independent generalisation. Preserve the current test IDs. Before
any final study, audit recording/session/location/template provenance from
available metadata, without changing the frozen test after seeing results.

For a future fine-tuning plan, use development sources only to construct
mixtures: at most `36 × 36 = 1,296` heart/lung source pairings before crops/gain
conditions. These are **not 1,296 independent recordings**; they reuse only
36+36 source files and 6+4 sound families. Use validation sources only for
preprocessing/model selection (`9 × 5 = 45` possible pairings). Keep the
`5 × 9 = 45` test pairings unavailable until all model choices are frozen.
Every digital mixture must record both source IDs/families, gains, resampling,
crop, alignment and mixing rule. Never mix a source across partitions.

There are 50 heart and 50 lung source WAVs in total, 15 seconds each; clean
separate source tracks exist in the current archive, and source-family-disjoint
synthetic additive mixtures are technically constructible. The training pool
is modest and family-diverse but small; overlapping crops and many remix
conditions do not increase the count of independent source recordings. Data may
support a cautious pilot adaptation if rights and the native-reproduction gate
are resolved, but it does not yet support a claim that full fine-tuning is
feasible or likely to generalise. Do not begin it now.

## Next gates

1. Owner reviews/sends the prepared author email; status remains **PREPARED / NOT
   SENT** until then.
2. If the authors provide lawful fixture/run identity, perform one small
   **AUTHOR-PROTOCOL REPRODUCTION**, separately labeled from our fixed-label
   StethoFuse target-domain protocol. Keep final source IDs sealed.
3. If no native fixture is available, record exactly what the authors confirm;
   do not relabel current manikin probes as native reproduction.
4. Only after NeoSSNet's native behavior/rights gate is resolved should the
   frozen LingoNMF candidate receive a bounded development qualification. Audit
   its method/configuration, code/license scope, data lineage, output labels,
   sample-rate contract and code/test overlap first.
5. Fine-tuning is still not approved. Revisit only if native NeoSSNet is shown
   to work under author conditions and then materially degrades on our distinct
   target protocol, or if an explicit author clarification justifies a separate
   adaptation study. No final FYP result or superiority claim follows from this
   note.
