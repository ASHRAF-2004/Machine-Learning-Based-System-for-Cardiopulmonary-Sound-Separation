---
name: audio-ml-pipeline
description: Use when implementing audio preprocessing, NeoSSNet loading, PyTorch inference, waveform saving, or evaluation metrics.
---

# Audio ML Pipeline Skill

The project separates mixed cardiopulmonary audio into:
- heart output
- lung output

Model:
- NeoSSNet
- PyTorch first
- model weights should load from storage/ml_models/neossnet_v1.pth

Rules:
- Keep training code separate from inference code.
- Keep preprocessing consistent between training and inference.
- Clearly document sample rate, mono/stereo handling, normalization, and tensor shape.
- Do not fake final separation outputs.
- Temporary placeholder inference is allowed only for API/UI testing and must be clearly marked.
- Save output files to:
  - storage/outputs/heart/
  - storage/outputs/lung/

Evaluation metrics:
- SNR
- SDR
- SI-SDR
- MSE/MAE if appropriate

When done:
- inference function should accept one WAV path
- output should be two WAV files
- output paths should be returned to backend service