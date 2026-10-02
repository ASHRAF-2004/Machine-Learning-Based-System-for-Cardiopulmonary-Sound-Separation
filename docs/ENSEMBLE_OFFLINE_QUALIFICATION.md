# Ensemble v1 Phase A–D offline checkpoint — 27 September 2026

> Later diagnostic: [NeoSSNet reproduction report](NEOSSNET_REPRODUCTION_DIAGNOSIS.md).
> The table below is preserved historical Phase-D evidence. A released-forward
> compatibility restoration changed NeoSSNet lung mean by only0.04 dB; it did
> not resolve poor separation. Native reproduction is blocked, target expert
> qualification fails, and application integration/fine-tuning remain on hold.

**Implemented and tested offline; not integrated with the application, not
deployed, and not a final FYP separation result.** The original fixed 50/50
complementary magnitude-mask decision is unchanged. All measurements here are
from isolated, development-only manikin/synthetic data. No patient audio,
production database, Firebase, Cloudflare or deployed service was touched.

## Artifact, runtime and permission qualification

- The released NeoSSNet checkpoint SHA-256 is
  `abf4f05321d7c0a9da0ee25bfe50f0dbb5736d5f855150787009b4221f947358`;
  configuration SHA-256 is
  `b7d82e7fb9cbcbd7382d6eadb69220fba5c7d25cafd5bbfdb83f714ca39d5096`.
  They match the existing local author-revision artifacts. `torch.load` uses
  `weights_only=True`; strict state-dict load succeeded. The author documents
  output order channel 0=heart, channel 1=lung, and training concatenates those
  targets in that order. There is no reference-optimised channel permutation.
- An isolated ignored CPU environment used Python 3.14.4, Torch/torchaudio
  2.11.0+cpu, NumPy 2.4.4, SciPy 1.17.0, PyYAML 6.0.3, ptwt 1.0.1 and
  prettytable 3.17.0. A synthetic 1-s and 10-s input both yielded finite
  `(1,2,N)` arrays. The 10-s probe: cold checkpoint load 0.046 s, first model
  inference 0.036 s, peak process RSS 367,788 KiB (~359 MiB). These are
  single-machine probes, not latency/RAM SLAs. `torch.cuda.is_available()` was
  false; GPU inference remains **not tested**.
- Recreate this ignored offline environment from the implementation root with
  `uv venv .local/ensemble/venv`, then install
  `torch==2.11.0+cpu torchaudio==2.11.0+cpu` from the official PyTorch CPU wheel
  index and pin `numpy==2.4.4 scipy==1.17.0 PyYAML==6.0.3 ptwt==1.0.1
  prettytable==3.17.0 pytest==9.0.3 vmdpy==0.2`. Do not modify the running
  production environment. The released model/config remain the previously
  recorded local artifacts; their hash checks fail closed.
- [Original author repository](https://github.com/yangyipoh/Neonatal-Chest-Sound-Separation-using-Deep-Learning)
  has no declared GitHub license (`license: null`) or license file in its
  inspected tree. A paper license is not code/checkpoint permission. The existing
  previously tracked source/weights were not newly copied or modified here.
  Redistribution and production use remain **blocked pending explicit rights
  clarification**. Do not deploy or claim licensed reuse on this evidence.

## Released dataset and frozen qualification contract

- [HLS-CMDS Zenodo record 15376628](https://zenodo.org/records/15376628)
  describes 22,050 Hz in its README, but **all 535 actual WAVs** in the official
  HS/LS/Mix ZIP files are mono 4-kHz, 16-bit PCM; all 535 local WAV bytes match
  the corresponding official ZIP members by SHA-256. Official ZIP MD5 values
  match the Zenodo record: HS `ac5a2390390f40e7abfe03fff7d73222`, LS
  `b27336a3e53c42fcc3c4629e0c8f23d8`, Mix
  `6c9ae67a15e46a45b476e2ae20d50850`. Thus the *released files used here*
  underwent no local 22.05→4-kHz conversion. Earlier pre-release acquisition/
  conversion history remains unknown; we do not assert the recording hardware
  originally captured at 4 kHz. Other input rates use the new pinned polyphase
  resampling contract, not legacy linear interpolation.
- The released LS.csv has 14 filename-label discrepancies: whitespace on one
  wheezing ID and older `C`/`G` sound abbreviations where released filenames use
  `FC`/`CC`. The qualification script resolves only those family-declared aliases,
  retains both original metadata ID and resolved filename in its ignored manifest,
  and rejects any other mismatch. The source WAVs/metadata were not rewritten.
- Source grouping is by sound type across gender/site because independent
  manufacturer-template or subject IDs are unavailable. Seed 42 assigned heart
  families 6/2/2 and lung families 4/1/1 to development/validation/test before
  mixing. Source-file counts are heart 36/9/5 and lung 36/5/9. The three older
  recorded-probe families are forced into development. This conservative split
  has very few independent families; broad generalisation cannot be claimed.
- Two development-family pairs were used (heart/lung IDs `F_AF_A`/`F_N_LLA` and
  `F_ESM_LLSB`/`F_PR_LLA`). Each received frozen −5/0/+5-dB lung-to-heart RMS
  ratios, first 10-s crop, and one shared anti-clipping gain. All six generated
  mixtures equalled their actual heart+lung references exactly as float32 sums
  (`max error=0`). The ignored, hashed manifest and per-record scores are in
  `.local/ensemble/qualification/`; no dataset/audio/results are committed.

## Implemented offline path and tests

`app/ml/ensemble_v1.py` provides shared-gain, 4-kHz canonicalisation, exact
10-s/8-s-hop windows, NeoSSNet raw-array and generic-NMF adapters, validated
heart/lung shapes, 1024/256 periodic-Hann centred STFT, epsilon-stable expert
magnitude-ratio masks, frozen 0.5/0.5 heart mask, complementary lung mask,
original-mixture-phase inversion, and overlap-add. No model selector, gate,
waveform averaging, reference oracle, silent expert fallback or API wiring.
Required-expert failure produces a safe failed-offline provenance record.
Successful runs include expert/checkpoint/config/source hashes, code revision
(when supplied or available) and exact engine hash even without `.git`, seed,
device, timing and no output artifact IDs (nothing is persisted).

The prior unpadded legacy STFT lost its first sample. One focused test reproduced
the 0.8 first-sample error; centred left/right padding and periodic Hann repair
passed that boundary test at max absolute error ≤1e-5. Five additional focused
tests cover canonical resampling, mask complementarity/finite deterministic
reconstruction, fail-closed required-expert output, overlap edges and SI-SDR
definition. A sixth focused test protects provenance in an image without Git
metadata. Initial focused run: **8 passed, 4 VMD cases deselected**. After
installing the existing pinned `vmdpy==0.2` into the ignored CPU environment,
one nearby ML regression pass was **12 passed** (ensemble + baseline strategies).
The final provenance portability fix then passed **2 targeted tests**; the
broader suite was not repeated for that metadata-only change.
This is not a strict no-fallback 10-s VMD benchmark; VMD was not relabelled as
Fixed Filter. No broad auth/security suite was rerun because those paths changed
neither code nor configuration.

## Six-mixture engineering probe (dB, means; n=2 pairs × 3 ratios)

| Method | Heart SI-SDR | Heart SI-SDRi | Lung SI-SDR | Lung SI-SDRi |
| --- | ---: | ---: | ---: | ---: |
| Released NeoSSNet raw | −3.48 | −3.47 | −13.84 | −13.83 |
| Released NeoSSNet projected | −2.62 | −2.61 | −12.44 | −12.43 |
| Generic NMF raw | −4.72 | −4.71 | −10.18 | −10.17 |
| Generic NMF projected | −4.63 | −4.62 | −9.90 | −9.88 |
| Fixed Filter | −2.50 | −2.49 | −6.50 | −6.49 |
| **50/50 ensemble** | **−3.24** | **−3.22** | **−10.21** | **−10.20** |

Six of six runs completed; no numerical/shape failures. Engine warm processing
was ~30–60 ms per 10-s mixture on this machine (excluding model startup and
evaluation/IO). SI-SDR is mean-centred float64; SI-SDRi subtracts that mixture's
own SI-SDR against the same target. Heart and lung are separate; repeated ratios
are not independent observations. These scores **do not show an improvement** on
this narrow development subset. No weight tuning or extra expert was performed.

Source-label diagnostic: upstream code specifies 0=heart/1=lung, yet a reference
comparison on two selected manikin mixtures scored better under a swap; other
development probes did not show a consistent reversal. This is a model/domain
qualification concern, **not** permission to swap channels per record using
reference labels or to claim a superior method. Investigate only with a frozen,
reference-free ordering rule or explicit upstream checkpoint evidence before any
release decision. Never change the label mapping based on the final test set.

## Phase-D gate and next bounded work

The engine and development-only evaluation pipeline are implemented/tested
offline. **Do not proceed to application jobs or production deployment at this
checkpoint.** Before a final controlled held-out study, resolve NeoSSNet reuse
rights; qualify source ordering and applicability without an oracle; review the
negative dev scores and exact preprocessing contract; and assess whether the
tiny sound-type-family split can support a meaningful independent test. Only an
approved next phase may expand evaluation or integrate the worker/results/UI.
