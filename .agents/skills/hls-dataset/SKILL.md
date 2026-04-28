---
name: hls-dataset
description: Use when preparing, cleaning, splitting, loading, or validating the HLS-CMDS dataset with HS, LS, and Mix audio files.
---

# HLS-CMDS Dataset Skill

Dataset location:
- datasets/hls_cmds/

Raw folders:
- datasets/hls_cmds/raw/HS/
- datasets/hls_cmds/raw/LS/
- datasets/hls_cmds/raw/Mix/

Metadata:
- datasets/hls_cmds/metadata/HS.csv
- datasets/hls_cmds/metadata/LS.csv
- datasets/hls_cmds/metadata/Mix.csv

Processed folders:
- datasets/hls_cmds/processed/train/heart/
- datasets/hls_cmds/processed/train/lung/
- datasets/hls_cmds/processed/train/mixed/
- datasets/hls_cmds/processed/val/heart/
- datasets/hls_cmds/processed/val/lung/
- datasets/hls_cmds/processed/val/mixed/
- datasets/hls_cmds/processed/test/heart/
- datasets/hls_cmds/processed/test/lung/
- datasets/hls_cmds/processed/test/mixed/

Rules:
- Never modify raw dataset files directly.
- Copy cleaned/processed files into processed/.
- Ignore or delete junk files:
  - .DS_Store
  - ._*
  - __MACOSX
- Keep train/val/test split reproducible.
- Use fixed random seed when splitting.
- Print summary counts after preparing dataset.

When done:
- processed folders should contain usable WAV files
- train_split.csv, val_split.csv, and test_split.csv should be updated if needed