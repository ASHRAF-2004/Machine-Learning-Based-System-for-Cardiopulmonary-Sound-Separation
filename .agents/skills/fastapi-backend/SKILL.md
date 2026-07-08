---
name: fastapi-backend
description: Use when implementing or modifying FastAPI app startup, routes, services, audio upload, validation, model selection, separation execution, result preview/download, metrics display, processing history, database access, and error handling for the cardiopulmonary separation project.
---

# FastAPI Backend Skill

Use this skill for backend work on the cardiopulmonary sound separation system.

## Important Folders

- `app/main.py`
- `app/routers/`
- `app/services/`
- `app/ml/`
- `app/database/`
- `app/models/`
- `storage/uploads/raw/`
- `storage/outputs/heart/`
- `storage/outputs/lung/`
- `database/cardiopulmonary.db`

## Rules

- Keep routes thin.
- Put business logic in services.
- Do not store WAV files in SQLite.
- Store file paths, metadata, job status, metrics, and errors in SQLite.
- Accept only WAV files for the first stable version unless explicit support is added for other formats.
- Validate files before saving or processing.
- Use clear JSON responses.
- Use FastAPI `HTTPException` for user-facing errors.
- Do not hard-code absolute paths in code.
- Use project config or environment variables for paths.
- Separation routes must call the ML/audio service through a strategy or service interface.
- Do not hard-code NeoSSNet logic directly inside routers.

## Required Backend Features

1. Upload mixed WAV audio.
2. Validate uploaded audio.
3. Save uploaded file to `storage/uploads/raw/`.
4. Insert uploaded audio metadata into SQLite.
5. List available models/algorithms.
6. Select model/algorithm.
7. Run separation job.
8. Save heart/lung output paths.
9. Return job status and result metadata.
10. Preview or download heart/lung WAV outputs.
11. Store and display processing history.
12. Store and return metrics when available.
13. Log errors cleanly.

## Implementation Order

1. `app/config.py`
2. `app/database/db.py`
3. `app/models/db_models.py`
4. `app/services/storage_service.py`
5. `app/services/audio_service.py`
6. `app/services/model_service.py`
7. `app/services/separation_service.py`
8. `app/services/evaluation_service.py`
9. `app/routers/upload.py`
10. `app/routers/models.py`
11. `app/routers/separation.py`
12. `app/routers/results.py`
13. `app/routers/history.py`
14. `app/main.py`

Follow the existing project structure when files already exist. Do not create duplicate route/service names just to match this list.

## Done Criteria

- FastAPI starts with `uvicorn app.main:app --reload`.
- Upload endpoint saves a WAV file and inserts one `uploaded_audio` row.
- Model list endpoint returns available algorithms.
- Separation endpoint creates a job, runs real separation, saves outputs, updates job status, and returns output paths.
- Result endpoint can preview/download heart and lung files.
- History endpoint shows previous jobs.
- Metrics are stored and returned when available.
- Errors are stored and returned clearly.
