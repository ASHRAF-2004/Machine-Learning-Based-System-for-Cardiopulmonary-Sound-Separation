---
name: audio-ml-pipeline
description: Use when implementing real cardiopulmonary audio preprocessing, multi-strategy separation, model loading, PyTorch inference, traditional baseline algorithms, decomposition-based algorithms, output WAV saving, segmentation/reconstruction, and evaluation metrics.
---

# Audio ML Pipeline Skill

Use this skill for real FYP2 audio and separation implementation.

## Architecture Correction

This project is not NeoSSNet-only. Support multiple interchangeable separation strategies through a common strategy interface.

NeoSSNet is the main machine-learning/deep-learning strategy, but baseline and decomposition strategies may also exist for comparison, workflow testing, and sanity checks.

## Supported Strategies

### FixedFilterSeparationStrategy

- Simple fixed filter or frequency-mask baseline.
- Use to sanity-check upload, preprocessing, output writing, preview, download, and history.
- Clearly label as a baseline, not machine learning.

### NmfSeparationStrategy

- Use non-negative matrix factorization on magnitude spectrograms.
- Reconstruct heart and lung estimates using soft masks where feasible.
- Clearly label as a traditional/decomposition baseline unless a trained ML component is added.

### VmdSeparationStrategy

- Use variational mode decomposition or an available practical VMD implementation.
- Group decomposed modes into heart/lung components based on frequency or documented rules.
- Clearly label as a traditional/decomposition baseline.

### NeoSSNetSeparationStrategy

- Main machine-learning/deep-learning strategy.
- Use NeoSSNet or a NeoSSNet-style PyTorch model.
- Load checkpoint/config from `storage/ml_models/` when available.
- Treat this as the main reason the system qualifies as machine learning-based.

## Strategy Contract

All strategies must follow the same backend-facing contract.

Recommended methods:
- `load()`
- `preprocess(input_audio)`
- `separate(input_audio)`
- `postprocess(outputs)`
- `save_outputs()`
- `evaluate(reference_heart=None, reference_lung=None)`

Each strategy should:
- accept a prepared mixed WAV/audio waveform
- return heart output, lung output, metadata, and optional metrics
- hide algorithm internals from the backend route

The backend should call strategies through a service/factory, not directly hard-code algorithm logic.

## Rules

- Do not fake final separation outputs.
- Placeholder/mock separation is allowed only for API/UI testing and must be clearly named `MockSeparationStrategy`.
- Never present mock output as real separation.
- Do not claim Fixed Filter, NMF, or VMD are machine learning unless a real learning/training component is implemented.
- Treat NeoSSNet as the core ML strategy, but not the only available strategy.
- Keep training code separate from inference code.
- Keep preprocessing consistent across strategies where possible.
- Clearly document sample rate, mono/stereo conversion, normalization, tensor shape, segmentation, reconstruction, and output channel order.
- Save heart outputs to `storage/outputs/heart/`.
- Save lung outputs to `storage/outputs/lung/`.
- Output WAV files must be playable, not empty, not fully silent, and not clipped.
- Segment and reconstruct long audio when the selected strategy requires fixed-length input.

## Evaluation Metrics

Calculate and return:
- SI-SDR when references exist
- SDR if feasible
- SNR improvement
- MSE/MAE when references exist
- correlation when references exist
- processing time
- output duration
- sample rate
- strategy/model name

If reference signals are missing, report only non-reference metrics and metadata. Do not invent quality metrics.

## Done Criteria

- The system has a common separation strategy interface.
- `FixedFilterSeparationStrategy` exists as a working baseline.
- `NeoSSNetSeparationStrategy` exists as the main ML strategy.
- `NmfSeparationStrategy` and/or `VmdSeparationStrategy` is implemented if feasible, or clearly documented as unavailable with the exact reason.
- One inference/separation function accepts one WAV path and selected strategy/model ID.
- The selected strategy generates two WAV files: heart and lung.
- Output paths, metadata, and metrics are returned to the backend.
- A test/check script verifies:
  - outputs exist
  - outputs are playable WAV files
  - outputs have valid duration/sample rate
  - outputs are not empty
  - outputs are not fully silent
