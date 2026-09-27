# Ensemble evidence and source audit

27 September 2026; offline/read-only inspection against implementation
`319e0e39cb2dff95897808ae16728cb60066efd6`, documentation
`28021e85b15a7e39c2365ecb871130809fe2b48a`. Companion to [ADR E01](ENSEMBLE_DESIGN.md).
Statuses here distinguish source inspection, a tiny execution probe, historical
artifacts and work that has not run. No production service/data was accessed.

## Located paths and graph freshness

Graphify graph `559ddba2f1e553f1266f4c1810ed1f75244aa210`, build
`520709ff-a97e-42f2-9f73-08ce7b12051a`, located the legacy strategy/factory,
preprocessing, dataset and evaluator paths. A scoped Git comparison from that
revision to current HEAD found no changes to the inspected legacy ML/evaluator
paths. The graph was **not** treated as current for M1 application integration;
the actual located `app/m1/{api,store,schema.sql}` sources were read separately.
No redundant whole-repository search or reindex was done.

```
Legacy strategy_factory → fixed_filter / nmf / vmd / neossnet
  → BaseSeparationStrategy or run_neossnet_inference → WAV output
scripts/evaluate_strategies.py → strategies → evaluation_service
datasets/hls_cmds → HlsCmdsSeparationDataset → train_neossnet_hls.py
Current M1 owner POST /api/recordings/{id}/jobs → ensemble_unavailable503
```

Existing tests include `tests/test_baseline_strategies.py`, `test_strategy.py`,
`test_hls_cmds_dataset.py`, `test_evaluation_service.py` and `test_m1_api.py`.
Their presence is not a new pass result. Legacy service tests import legacy DB
paths; the evaluator initialises that DB. Neither was run against application data.

## Implemented expert inventory / compatibility

| Method | Actual callable implementation | Contract and differences | Current evidence / v1 position |
| --- | --- | --- | --- |
| NeoSSNet original | `app/ml/neossnet_strategy.py` → `neossnet_inference.py` → vendored `models.MaskNet` | 4kHz; `(B,1,T)`→`(B,2,T)`; heart0/lung1. Unit-peak input; linear resampling. Current writer clamps then peak-caps each output separately. Model handles stride padding. | Released checkpoint/config/model definition match author Git blobs. Current environment lacks Torch; load/inference NOT RUN here. **Conditional member**, raw-output adapter + permission/load qualification required. |
| Local NMF | `app/ml/strategies/nmf_strategy.py` | Magnitude STFT, Euclidean multiplicative W/H updates; 6 components/80 iterations/seed42. 220-Hz centroid partition, ordered-half fallback. Mixture phase; no pretrained dictionary. | Two-second synthetic execution passed finite/length checks. **Conditional member** after common STFT correction. Generic unsupervised baseline, not Torabi periodicity NMF, Grooby NMCF or a DAE hybrid. |
| Fixed Filter | `fixed_filter_strategy.py` + `audio_utils.frequency_mask_split` | Complementary frequency masks; logistic priors centred180/130Hz, widths35/55Hz; no training. | Synthetic execution finite/length checks passed. Comparator only; shared spectral assumptions with NMF limit diversity. |
| VMD fast / quality | `vmd_strategy.py`, `vmdpy.VMD` | 4kHz input, internally1kHz/K3 or2kHz/K5; segmented, modes grouped at220Hz. Duration caps30/20s; exceptions/caps can substitute Fixed Filter. `max_iterations` metadata is not passed to vmdpy. | Dependency absent; NOT RUN here. Bandwidth loss and fallback identity make it unsuitable as a v1 member. Optional strict comparator, not DAE–NMF–VMD. |
| NeoSSNet fine-tuned | `scripts/train_neossnet_hls.py` and log | Local L1 training differs from paper SI-SDR objective. Script can save epoch0 or train from scratch if base unavailable; log alone cannot prove model identity. | `neossnet_hls_finetuned.pt` absent. `neossnet_v1.pth` empty. Historical numbers only; excluded. |
| NMCF / DAE–NMF–VMD | No registered corresponding full strategy | Names in references/legacy external wrappers do not establish these implementations. | Excluded from v1; no missing component will be invented or relabelled. |

Shared legacy postprocessing silently fits lengths and independently peak-caps
outputs; WAV writer replaces nonfinite values with zero. These behaviours cannot
be used as ensemble validity checks. Canonical adapters must inspect raw arrays.

## NeoSSNet provenance — concrete positive finding and remaining limit

Author repository: [yangyipoh/Neonatal-Chest-Sound-Separation-using-Deep-Learning](https://github.com/yangyipoh/Neonatal-Chest-Sound-Separation-using-Deep-Learning),
main revision `d97886b93bd2e71fd019c6b5073bb2dce2854ade` inspected through public Git/API.
No LICENSE/COPYING entry was found in its recursive tree or the local vendored
source. Paper CC-BY status does not itself settle code/checkpoint reuse rights.
Resolve permission before distribution/deployment; no author message was sent.

| Item | Local location | Identity |
| --- | --- | --- |
| Released weights | `storage/ml_models/model_best.pt`, 34,973,929 bytes | SHA256 `abf4f05321d7c0a9da0ee25bfe50f0dbb5736d5f855150787009b4221f947358`; local Git blob `e7dd72ff1b21f70c40dc3ffcda104a6164150b29` equals author model blob |
| Model configuration | `storage/ml_models/model.yaml` | SHA256 `b7d82e7fb9cbcbd7382d6eadb69220fba5c7d25cafd5bbfdb83f714ca39d5096`; Git blob `7ea727febf485138faf0b6ed8b1d08de59ad010f` equals author config |
| Architecture source | `app/ml/neossnet_source/models/__init__.py` | Git blob `9bda001fbf0015681da996ffbab7824a839b2bce` equals author source |

Config: convolution encoder/decoder, kernel512/features512, mask features256,
4 heads/4 layers, two source-specific mask generators, 6 convolution layers,
dropout0.3, stochastic/wavelet disabled. This confirms a released artifact, not
every paper experiment/fold or its exact training split. Imports still require
Torch, torchaudio and ptwt even with wavelets disabled; inspect/pin compatible
versions in a separate ML environment, never upgrade the live API environment.

## Research attribution / applicability

Full verified bibliographic entries are in the documentation repository's
`fyp2/provenance/ensemble-references.bib`; the FYP2 design note supplies APA7 references.

- **Poh et al. (2024), NeoSSNet** — [original article](https://pmc.ncbi.nlm.nih.gov/articles/PMC11186644/),
  DOI10.1109/OJEMB.2024.3401571. Learned convolutional encoder/decoder with
  convolution/transformer masks; waveform input and labelled waveforms out.
  Paper uses neonatal recordings, artificial mixtures, SI-SDR training and
  AdamW; 8-s training crops, 4-kHz/10-s inference examples. Released weights avoid
  new training, but adult/manikin domain transfer and artifact risk remain.
  Training/reported clinical signals in that paper are not StethoFuse evidence.
- **Lee and Seung (2000)** — [original NIPS13 proceedings](https://proceedings.neurips.cc/paper_files/paper/2000/hash/f9d1152547c0bde01830b7e8bd60024c-Abstract.html).
  Euclidean multiplicative factorisation motivates the local NumPy NMF updates.
  That paper does not define StethoFuse's cardiopulmonary centroid labelling rule.
  Inference fits nonnegative factors to each input spectrogram; no external
  training/checkpoint. Interpretability/low setup cost versus overlap/label ambiguity.
- **Grooby et al. (2023), neonatal NMF/NMCF** — [author preprint](https://arxiv.org/abs/2201.03211),
  DOI10.1109/JBHI.2022.3215995. Spectral factorisation/co-factorisation with
  source/noise-informed structure; a distinct family, not our generic NMF.
  [Author MATLAB repository](https://github.com/egrooby/Heart-and-Lung-Sound-Separation)
  revision `c0b4f7780291766bbbd5e82d13ad0104cad2fa63`, GPL3, also requires author
  signal-quality code. README cites the earlier2021 NMCF paper: exact correspondence
  to2023 method variants still needs qualification. Dictionaries, dependencies and
  language/license integration make adoption a separate milestone.
- **Sun, Zhang, and Chen (2024), DAE–NMF–VMD** —
  [publisher article](https://link.springer.com/article/10.1186/s13634-024-01152-0),
  DOI10.1186/s13634-024-01152-0. Denoising-autoencoder feature extraction,
  periodicity-based NMF grouping, then VMD denoising. Requires trained DAE and
  matching feature/reconstruction stages, not a chain of our two baselines.
  No verified matching author code/checkpoint found in this bounded audit.
  Full objective/hyperparameter reproduction remains unresolved. Paper experiments
  do not justify importing speech PESQ/STOI as clinical audio metrics.
- **Dragomiretskiy and Zosso (2014), VMD** —
  [original author manuscript](https://ww3.math.ucla.edu/camreport/cam13-22.pdf),
  DOI10.1109/TSP.2013.2288675. Variational narrowband-mode decomposition solved
  iteratively; no learned checkpoint. [vmdpy](https://github.com/vrcarva/vmdpy)
  is an MIT-licensed Python implementation. Local frequency grouping, downsampling,
  segmentation and fallback are StethoFuse adaptations, not paper-level heart/lung
  semantics. Runtime/mode choices and bandwidth are limitations; version not locked
  in the currently usable environment, so no new execution claim.

## Data and historical evaluation audit

Published HLS-CMDS [record](https://zenodo.org/records/15376628) and
[README](https://zenodo.org/records/15376628/files/HLS_CMDS_README.txt?download=1):
clinical manikin/digital stethoscope, 50 heart +50 lung +145 mixed/heart/lung triples,
535 WAVs total, 15 s, **22,050 Hz**. Metadata API reports CC-BY4.0. The local
535 headers all say **4,000 Hz, mono, PCM16, 60,000 samples**. The exact
downsampling/conversion lineage is not documented by those headers.

Local `datasets/hls_cmds/metadata/Mix.csv` has145 complete ID triples, each heart
and lung ID unique within the CSV; IDs are not proof of distinct manikin source
templates. Fields describe sound type, gender and location, not subject/template
identity. `train_split.csv` and `val_split.csv` are actually Excel ZIP files with
CSV names; `test_split.csv` is empty. The `*_pairs.csv` expected by the dataset
class are absent. `prepare_dataset.py` shuffles mixture rows70/15/15 (seed42), not
source groups. Do not run it and claim leakage control. `HlsCmdsSeparationDataset`
uses15-s crops/padding and per-file loader gain caps; this is not the v1 contract.

Historical CSVs are preserved, **not a current FYP2 comparison**:
`evaluation/results_strategy_comparison.csv` has115 completed rows, the same23
sample IDs for five methods. Summary means (heart/lung SI-SDR dB) are:

| Historical label | Heart | Lung |
| --- | ---: | ---: |
| Fixed Filter | -18.269 | -26.440 |
| VMD | -18.983 | -32.299 |
| NeoSSNet original | -18.359 | -29.599 |
| NeoSSNet fine-tuned | -20.477 | -24.763 |
| NMF | -21.746 | -27.744 |

No frozen split, checkpoint hash, environment/hardware receipt accompanies these
rows; fine-tuned weights are now missing. `evaluation_service.py` searches a
reference-dependent ±100-ms lag separately for estimates, maximising SI-SDR and
cropping overlap. That oracle and uncertain recorded references invalidate direct
comparison with a new strict pipeline. Mean runtime fields are historical only.
Never combine these numbers with future ensemble scores as an improvement claim.

SHA256 results CSV: `b71d14fdbc90419d15894a2850566232f6f75527219d627b024a553f1402d7e9`;
summary CSV: `36b95302bb707c0e30916e35d7618fbcbfbfdeccc0f81bdbf38d060a48b94fb0`.

## One bounded probe — actual execution, not benchmark

Command: `OPENBLAS_NUM_THREADS=1 python3 scripts/probe_ensemble_contract.py`.
NumPy2.3.5, host CPU, synthetic2-s cosine80Hz+500Hz. No new dependency, Torch,
training, source-quality metric or large evaluation run. Fixed Filter and NMF
returned finite `(8000,)` heart/lung at4kHz. Single uncontrolled run times were
0.005571s /0.018327s; **not** performance estimates for real recordings.

Legacy STFT round-trip changed first sample0.300000012→0 and had max error0.300000012.
The same endpoint defect appears in both baseline reconstructions. Three CSV-first
manikin triples had relative residual norms after best same-time two-gain fitting
of **0.999989 /0.999764 /0.999507**. This demonstrates those pairs are not usable
as-is additive references; it does not diagnose the acquisition process or prove
that all other triples are unusable. Do not solve it by optimising alignment on test.

Probe input SHA256 (M/H/L), retained for reproducibility:

```
M0001 8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616
H0001 2778d5741abddac9df61c9d6c8e56b33e8e03e8b72e8e2dd4f328018a709feb5
L0001 3add3455ce4f23a91b602119efa053632f462a7b1f44ced6542911dfdad25e3b
M0002 88d9be33e1f37e27dc8b20e87e34fd80712a792dff5a92b2c5cfd95475c1f388
H0002 bd5e2d6535f482905412e9b0bd19543a5f0dda32c84ac45936c666ae3909b73b
L0002 012a1a39d4f38e5b08717bfb134b69e90621989c86f5e6181e307f178eb6a673
M0003 64b66124aa3571223666dc2c337602f3b293fd4bd579c0b8291ff6f9d6c562c7
H0003 2ce6ab8b7b51d440e974da652a95ee140f36edc7b434c9a741dcd7d5a326618c
L0003 7c7e83b21a113db5782bf07364b05002ed6818b234c9f4ed16e6c20311d82902
```

## Submitted FYP1 and guidance boundary

Targeted revised DOCX/PDF reading: §4.5.2/Table4.12 (PDF physical54/printed41),
§4.5.3 preprocessing/strategies/model selection, §4.5.4 storage and §5.1.3 planned
model integration. The submitted design explicitly leaves actual results to FYP2.
Historical repository CSVs must not be relabelled as validated submitted results.
The PDF page was rendered/read to verify the table/section, not rewritten.
Handbook Application-Based structure remains seven chapters; no invented rubric.

Unchanged SHA256:

- Submitted PDF: `6d7e442f031880ba7d4c35c87218eb708b8efafcf9dac1abc1c29737fd53623d`.
- Revised submitted DOCX: `1d9ba76c6a61738ec4a2a5b93da2966e46d4d90fde94af8d54a07ba694c0759f`.

The owner now explicitly supplies academic title **Development of a Machine
Learning-Based System for Cardiopulmonary Sound Separation**. Use it for this
FYP2 design; preserve historical title variants/submitted pages unchanged and
confirm exact registration wording before final submission rather than back-editing FYP1.
