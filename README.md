# Cardiopulmonary Sound Separation Prototype

## Project Overview

This project is a Final Year Project prototype for separating mixed cardiopulmonary audio into heart sound and lung sound outputs. It provides a FastAPI web interface where a user can upload a mixed WAV file, run real NeoSSNet inference, preview the separated outputs, download the generated WAV files, and view recent processing history.

The system is designed for local academic demonstration, testing, and research workflow support. It is not a clinical diagnostic system.

## Features

- Upload mixed cardiopulmonary `.wav` files through a browser UI.
- Validate and store uploaded WAV files under `storage/uploads/raw/`.
- Run real PyTorch-based NeoSSNet inference using the configured model files.
- Save separated heart and lung WAV outputs under `storage/outputs/`.
- Play the original upload and separated outputs in the browser.
- Download separated heart and lung WAV files.
- Store upload metadata, model metadata, job status, result paths, and processing timing in SQLite.
- View recent separation history.
- Validate project folders, database tables, and dataset hygiene with a helper script.

## Folder Structure

```text
app/
  database/              SQLite connection helpers
  ml/                    NeoSSNet inference wrapper
  models/                SQLAlchemy database models
  routers/               FastAPI route modules
  services/              Upload, separation, and result business logic
  static/                CSS and JavaScript for the browser UI
  templates/             FastAPI/Jinja2 HTML templates
database/
  cardiopulmonary.db     Local SQLite database
  schema.sql             Database schema
  seed.sql               Seed data reference
datasets/
  hls_cmds/              HLS-CMDS dataset folders
docs/                    Project explanation and demo notes
external/
  neossnet_source/       External NeoSSNet source implementation
sample_inputs/           Small sample WAV files for testing
scripts/                 Project validation and inference test scripts
storage/
  ml_models/             NeoSSNet checkpoint and config files
  outputs/heart/         Generated heart sound WAV files
  outputs/lung/          Generated lung sound WAV files
  uploads/raw/           Uploaded mixed WAV files
  uploads/temp/          Temporary files used by tests/runtime helpers
  logs/                  Local log folder
tests/                   Pytest tests
```

## Installation

Use Python 3.10+ in a local virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PyTorch installation fails on your machine, install the correct CPU build from the official PyTorch installation command for your Python version, then run `python -m pip install -r requirements.txt` again.

## How To Run

Start the FastAPI development server from the project root:

```powershell
uvicorn app.main:app --reload
```

Open the web interface:

```text
http://127.0.0.1:8000/
```

Basic workflow:

1. Choose a mixed `.wav` file.
2. Click upload/run separation in the web UI.
3. Wait for NeoSSNet inference to finish.
4. Preview the heart and lung output audio.
5. Download the generated output files if needed.

## How To Test

Run the automated tests:

```powershell
pytest -q
```

Validate the project structure, database, and HLS-CMDS dataset folders:

```powershell
python scripts/check_project.py
```

Run the standalone NeoSSNet inference smoke test:

```powershell
python scripts/test_neossnet_inference.py
```

The standalone inference test reads `sample_inputs/H0001.wav` and writes:

- `storage/outputs/heart/test_heart.wav`
- `storage/outputs/lung/test_lung.wav`

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Browser interface |
| `GET` | `/health` | Health check and database existence status |
| `POST` | `/upload` | Upload and store a WAV file |
| `POST` | `/separate/{audio_id}` | Run NeoSSNet separation for an uploaded audio record |
| `GET` | `/result/{job_id}` | Return job status, uploaded audio metadata, output paths, and timing |
| `GET` | `/download/{job_id}/heart` | Download separated heart sound WAV |
| `GET` | `/download/{job_id}/lung` | Download separated lung sound WAV |
| `GET` | `/history` | Return recent separation jobs |

## Dataset Notes

The HLS-CMDS dataset is kept outside the application source code under `datasets/hls_cmds/`.

Expected dataset folders:

```text
datasets/hls_cmds/raw/HS/
datasets/hls_cmds/raw/LS/
datasets/hls_cmds/raw/Mix/
datasets/hls_cmds/metadata/
datasets/hls_cmds/processed/train/
datasets/hls_cmds/processed/val/
datasets/hls_cmds/processed/test/
```

Runtime uploads and outputs are separate from the dataset. The backend reads uploaded files from `storage/uploads/raw/` during inference and writes generated outputs to `storage/outputs/heart/` and `storage/outputs/lung/`.

Dataset junk files such as `.DS_Store`, `._*`, and `__MACOSX` should not be kept under `datasets/hls_cmds/`. Use `python scripts/check_project.py` to check this.

## Model Files Notes

NeoSSNet source code is stored in:

```text
external/neossnet_source/
```

The active model entry in `database/cardiopulmonary.db` should point to:

```text
storage/ml_models/model_best.pt
storage/ml_models/model.yaml
```

The backend loads the active model row from the `model` table, uses `checkpoint_path` and `config_path`, runs CPU inference by default, and writes one heart WAV and one lung WAV per completed job.

If the database is rebuilt from SQL files, verify that the active `model` row contains both the checkpoint path and config path used by the working prototype.

## Documentation

- `docs/system_architecture.md` explains the frontend, backend, database, storage, and NeoSSNet inference flow.
- `docs/database_design.md` explains the SQLite tables, relationships, and why WAV files are stored on the filesystem.
- `docs/demo_steps.md` provides a step-by-step demo flow for presentation.

## Current Limitations

- The prototype is intended for local demonstration and academic evaluation, not diagnosis.
- Inference currently runs synchronously inside the request/response flow.
- SQLite and local filesystem storage are suitable for this student prototype, but a production deployment would need stronger job queueing, storage management, authentication, and validation.
