---
name: fastapi-backend
description: Use when implementing or modifying FastAPI routes, services, database access, uploads, downloads, or app startup for the cardiopulmonary separation project.
---

# FastAPI Backend Skill

Follow the existing project structure.

Important folders:
- app/main.py
- app/routers/
- app/services/
- app/database/
- app/models/
- storage/uploads/raw/
- storage/outputs/heart/
- storage/outputs/lung/
- database/cardiopulmonary.db

Rules:
- Keep routes thin.
- Put business logic in services.
- Do not store WAV files in SQLite.
- Store file paths and metadata in SQLite.
- Validate uploaded files before saving.
- Accept only WAV files for the first version.
- Use clear JSON responses.
- Handle errors with FastAPI HTTPException.

Implementation order:
1. app/database/db.py
2. app/models/db_models.py
3. app/main.py
4. app/routers/upload.py
5. app/services/storage_service.py

When done:
- FastAPI must start with `uvicorn app.main:app --reload`
- upload endpoint must save file to storage/uploads/raw/
- uploaded_audio table must receive one row