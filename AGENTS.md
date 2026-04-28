# AGENTS.md

## Project Overview
- **Project:** Development of a Machine Learning-Based System for Cardiopulmonary Sound Separation
- **Current stage:** Database, dataset folders, storage folders, and project structure have been created. The next phase is backend implementation.
- **Purpose:** A real web-based system that accepts mixed cardiopulmonary audio and separates it into heart sound and lung sound outputs using NeoSSNet.
- **Target user:** Students, lecturers, researchers, or healthcare-related demo users.
- **My skill level:** Beginner to intermediate
- **Primary stack:** FastAPI, Python, PyTorch, SQLite, HTML/CSS/JavaScript
- **Dataset:** HLS-CMDS dataset with HS (heart sounds), LS (lung sounds), and Mix (mixed sounds)
- **Storage approach:** Audio files are stored in local folders. SQLite stores metadata, logs, job records, and evaluation results.

## Core Project Rules
- This project must perform **real separation**, not mock or fake separation.
- NeoSSNet is the core separation model.
- The system must produce:
  - separated heart audio
  - separated lung audio
- Do not simulate model output unless I explicitly ask for temporary placeholder behavior during early UI/API testing.
- If temporary placeholder behavior is used for early pipeline testing, clearly mark it as temporary and replace it later with real NeoSSNet inference.
- Prefer the **easiest working solution** over overengineered architecture.
- Keep everything practical for a student Final Year Project.
- Use the existing database and folder structure before suggesting major restructuring.

## System Scope
Main features:
1. Upload mixed WAV file
2. Validate and save audio file
3. Run NeoSSNet inference
4. Generate real heart and lung output files
5. Play original and separated audio in browser
6. Download separated files
7. Store metadata in SQLite
8. Store logs in SQLite
9. Show processing history
10. Support testing and demo presentation

## Expected Architecture
- **Frontend:** HTML, CSS, JavaScript using FastAPI templates and static files
- **Backend API:** FastAPI
- **Machine Learning:** PyTorch implementation of NeoSSNet
- **Database:** SQLite
- **Database file:** `database/cardiopulmonary.db`
- **Schema file:** `database/schema.sql`
- **Seed file:** `database/seed.sql`
- **File Storage:** local folders under `storage/`, including uploads, outputs, logs, and ML model weights
- **Dataset Storage:** HLS-CMDS dataset under `datasets/hls_cmds/`
- **Optional later:** ONNX export only if needed after PyTorch version works

## Database Guidance
The database should store structured metadata, not large raw audio blobs unless explicitly requested.

Expected entities / tables:
- UploadedAudio / `uploaded_audio`
- Model / `model`
- SeparationJob / `separation_job`
- SeparationResult / `separation_result`
- EvaluationMetric / `evaluation_metric`
- SystemLog / `system_log`
- User (optional only if authentication is added)

The database should store:
- file names
- file paths
- upload timestamps
- processing status
- model version
- output paths
- evaluation metrics
- logs
- error messages

The filesystem should store:
- uploaded WAV files
- output WAV files
- model checkpoints
- dataset audio files
- generated plots/images if any

Use the existing SQLite schema before redesigning the database.

## Dataset Guidance
The HLS-CMDS dataset should stay outside the application source code.

Dataset folders:
- `datasets/hls_cmds/raw/HS/` for original heart sounds
- `datasets/hls_cmds/raw/LS/` for original lung sounds
- `datasets/hls_cmds/raw/Mix/` for original mixed sounds
- `datasets/hls_cmds/metadata/` for CSV metadata and split files
- `datasets/hls_cmds/processed/train/` for training data
- `datasets/hls_cmds/processed/val/` for validation data
- `datasets/hls_cmds/processed/test/` for testing data

Do not train from runtime upload folders.

Ignore or remove dataset junk files:
- `.DS_Store`
- `._*`
- `__MACOSX`

## Folder / File Expectations
Use the existing project structure:

- `app/`
- `app/main.py`
- `app/config.py`
- `app/routers/`
- `app/services/`
- `app/database/`
- `app/models/`
- `app/ml/`
- `app/static/`
- `database/cardiopulmonary.db`
- `database/schema.sql`
- `database/seed.sql`
- `datasets/hls_cmds/raw/`
- `datasets/hls_cmds/processed/`
- `datasets/hls_cmds/metadata/`
- `storage/uploads/raw/`
- `storage/uploads/temp/`
- `storage/outputs/heart/`
- `storage/outputs/lung/`
- `storage/ml_models/`
- `storage/logs/`
- `scripts/`
- `tests/`

Do not create a separate React frontend unless explicitly requested.

## Commands
- **Install:** `pip install -r requirements.txt`
- **Dev:** `uvicorn app.main:app --reload`
- **Test:** `pytest`
- **Lint:** `ruff check .`
- **Format:** `black .`

Update these commands if the actual project files differ.

## Do
- Read existing code before changing anything
- Match existing naming and structure
- Keep code modular and easy to explain in viva
- Add comments where useful, especially in ML/audio code
- Handle errors clearly and visibly
- Log important events to SQLite or log files
- Prefer practical, minimal dependencies
- Explain why architectural decisions are being made
- When building features, keep both technical correctness and FYP presentation quality in mind
- Make code easy for a student to run locally
- Build the project in small working milestones
- Start with upload, database insert, and history before full NeoSSNet integration

## Don't
- Do not replace real separation with fake outputs
- Do not add unnecessary dependencies without reason
- Do not overengineer microservices, Docker orchestration, or cloud complexity unless explicitly asked
- Do not store secrets or credentials in source code
- Do not rewrite working modules without clear benefit
- Do not delete report-related or experiment-related files unless confirmed
- Do not break existing endpoints just to refactor style
- Do not store large WAV files inside SQLite unless explicitly requested
- Do not move datasets into `app/`
- Do not train from `storage/uploads/` or `storage/outputs/`
- Do not commit `.env`, large generated outputs, or dataset junk files

## ML / Audio Rules
- Keep preprocessing consistent between training and inference
- Clearly state input shape, output shape, and sample rate assumptions
- Prefer reproducible pipeline design
- If using placeholder model behavior for early API testing, label it clearly as temporary
- Separate training code from inference/deployment code
- Training data should come from `datasets/hls_cmds/processed/`
- Runtime inference should use uploaded files from `storage/uploads/raw/`
- Model weights should be stored in `storage/ml_models/`
- Prefer simple, explainable evaluation metrics:
  - SNR
  - SDR
  - SI-SDR
  - MSE / MAE if appropriate

## API Rules
Expected endpoints may include:
- `POST /upload`
- `POST /separate/{audio_id}`
- `GET /result/{job_id}`
- `GET /download/{job_id}/{type}`
- `GET /history`
- `GET /logs/{job_id}`
- `GET /health`

Do not invent inconsistent endpoint naming if routes already exist.

Recommended implementation order:
1. database connection
2. database models
3. FastAPI app startup
4. upload endpoint
5. save uploaded WAV
6. insert upload record into database
7. history/results endpoints
8. separation job creation
9. NeoSSNet inference
10. output preview/download

## Frontend Rules
- Keep UI clean, modern, and simple
- Prioritize upload, playback, result viewing, and download flow
- Show meaningful status messages
- Use clear handling for error states
- Make the interface easy to demo to lecturer/examiner
- Use FastAPI templates and static files first
- Do not add React unless explicitly requested

## Testing
- Run existing tests after changes
- Add tests for new backend features where practical
- For ML/audio code, add at least basic validation tests when possible
- Never remove tests just to make the project pass
- Verify:
  - FastAPI starts
  - upload works
  - uploaded file is saved
  - database row is created
  - invalid files are rejected
  - separation job runs
  - outputs are saved
  - logs are written
  - history loads correctly

## When Stuck
- First identify whether the issue is:
  - frontend
  - backend
  - database
  - file path / storage
  - dataset structure
  - model inference
  - audio preprocessing
- Give the likely root cause first
- Try the smallest reasonable fix first
- If the task is large, break it into steps
- If temporary placeholder logic is required for progress, clearly label it as temporary

## Git
- Use small focused commits
- Write descriptive commit messages
- Never force push
- Do not commit large generated files unless needed
- Do not commit `.env`
- Do not commit dataset junk files such as `.DS_Store`, `._*`, or `__MACOSX`

## Response Style
- Be clear and direct
- Use plain English
- Avoid unnecessary jargon unless relevant
- Keep explanations practical
- When possible, give:
  1. what is wrong
  2. why it is wrong
  3. the fix
  4. the next step
- When modifying code, mention changed files and how to run/test them

## Priority Order
When making decisions, prioritize in this order:
1. Real functionality
2. Simplicity
3. Easy local execution
4. Clean architecture
5. Academic/FYP presentation value
6. Performance optimization later