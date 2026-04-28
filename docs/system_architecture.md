# System Architecture

## Overview

This project is a local web-based prototype for cardiopulmonary sound separation. A user uploads a mixed WAV file, the backend records the upload in SQLite, NeoSSNet separates the audio into heart and lung components, and the generated WAV files are saved on the local filesystem.

The main architecture is intentionally simple:

- FastAPI handles HTTP routes and serves the template frontend.
- SQLite stores structured metadata, job state, result paths, and timing.
- The filesystem stores large WAV files, model files, and dataset files.
- NeoSSNet performs real PyTorch inference using the external implementation under `external/neossnet_source/`.

## Frontend

The frontend is built with FastAPI templates and static assets:

- `app/templates/index.html`
- `app/static/css/style.css`
- `app/static/js/main.js`

The browser UI supports the main demo workflow:

1. Select a mixed WAV file.
2. Upload it through `POST /upload`.
3. Run separation through `POST /separate/{audio_id}`.
4. Show loading and status messages.
5. Display the uploaded filename.
6. Preview separated heart and lung outputs with audio players.
7. Download the generated WAV files.
8. Show recent history from `GET /history`.

This keeps the frontend beginner-friendly and avoids a separate React build step.

## Backend

The backend uses FastAPI and is organized into routers and services:

```text
app/main.py
app/routers/upload.py
app/routers/separation.py
app/routers/results.py
app/services/storage_service.py
app/services/separation_service.py
app/services/result_service.py
app/ml/neossnet_inference.py
```

Routes stay thin. They validate request-level concerns, call service functions, and translate service errors into HTTP responses.

Service modules contain the core behavior:

- `storage_service.py` validates uploaded WAV files, saves them to `storage/uploads/raw/`, and extracts basic WAV metadata.
- `separation_service.py` creates separation jobs, loads the active model record, runs NeoSSNet inference, stores output metadata, and marks jobs as completed or failed.
- `result_service.py` reads job details, resolves download paths, and returns recent history.
- `neossnet_inference.py` wraps the external NeoSSNet implementation and handles WAV loading, mono conversion, resampling to 4000 Hz when needed, inference, and WAV saving.

## Database

The database is SQLite:

```text
database/cardiopulmonary.db
```

The schema is defined in:

```text
database/schema.sql
```

SQLite stores structured records rather than audio blobs. The main tables are:

- `uploaded_audio`
- `model`
- `separation_job`
- `separation_result`
- `evaluation_metric`
- `system_log`

The `separation_job` table is the central processing table. Each job links one uploaded WAV file to one model record. A completed job has one `separation_result` row containing the heart and lung output paths.

## Storage

Large files are stored on disk:

```text
storage/uploads/raw/       Uploaded mixed WAV files
storage/uploads/temp/      Temporary runtime/test files
storage/outputs/heart/     Separated heart WAV files
storage/outputs/lung/      Separated lung WAV files
storage/ml_models/         NeoSSNet checkpoint and config files
storage/logs/              Local logs
```

The dataset is kept separate from runtime storage:

```text
datasets/hls_cmds/raw/
datasets/hls_cmds/processed/
datasets/hls_cmds/metadata/
```

This separation makes the system easier to explain and prevents uploaded demo files from being mixed with training or evaluation data.

## NeoSSNet Inference Flow

The working inference flow is:

1. `POST /upload` receives a WAV file.
2. `storage_service.py` validates the filename and WAV header.
3. The file is saved under `storage/uploads/raw/`.
4. A row is inserted into `uploaded_audio`.
5. `POST /separate/{audio_id}` receives the uploaded audio ID.
6. `separation_service.py` loads the uploaded audio record.
7. The active NeoSSNet model row is loaded from the `model` table.
8. A `separation_job` row is created with status `running`.
9. `neossnet_inference.py` loads the uploaded WAV as mono float audio.
10. If needed, the waveform is resampled to the model sample rate of 4000 Hz.
11. The external NeoSSNet `generate_output` function runs real CPU inference.
12. Heart and lung WAV outputs are saved to `storage/outputs/heart/` and `storage/outputs/lung/`.
13. A `separation_result` row is inserted with output paths and metadata.
14. The `separation_job` row is marked `completed`.
15. The API returns the job ID, status, output paths, and processing time.

If inference fails, the job is marked `failed` and the error message is stored in `separation_job.error_message`.

## Request Flow Summary

```text
Browser UI
  -> POST /upload
  -> uploaded_audio row + stored WAV
  -> POST /separate/{audio_id}
  -> separation_job row
  -> NeoSSNet inference
  -> output WAV files
  -> separation_result row
  -> GET /result/{job_id}
  -> GET /download/{job_id}/heart
  -> GET /download/{job_id}/lung
  -> GET /history
```

## Design Rationale

The architecture favors a small, understandable system that is suitable for a student Final Year Project:

- FastAPI keeps backend routing clear and lightweight.
- SQLite is enough for local metadata, job tracking, and demo history.
- WAV files stay on the filesystem because they are large binary artifacts.
- NeoSSNet code is isolated in `app/ml/` so the API and ML concerns are easier to explain separately.
- Dataset folders are separated from runtime uploads and outputs.

## Current Limitations and Future Work

- Inference runs synchronously, so a long audio file can keep the HTTP request open.
- The system does not provide clinical diagnosis or validated clinical accuracy.
- There is no user authentication in the current prototype.
- Future work could add a background job queue, stronger logging, evaluation metrics, model selection controls, and deployment packaging.
