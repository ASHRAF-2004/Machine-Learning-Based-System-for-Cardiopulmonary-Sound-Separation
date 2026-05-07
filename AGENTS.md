# AGENTS.md

## Project Overview
- **Project:** Development of a Machine Learning-Based System for Cardiopulmonary Sound Separation
- **Current stage:** Working FastAPI prototype completed with SQLite, HLS-CMDS dataset setup, upload flow, real NeoSSNet inference, result preview/download, history, tests, and LaTeX report assets. The next phase is maintainable model-selection support.
- **Purpose:** A real web-based system that accepts mixed cardiopulmonary audio and separates it into heart sound and lung sound outputs using real machine learning inference.
- **Target user:** Students, lecturers, researchers, or healthcare-related demo users.
- **My skill level:** Beginner to intermediate
- **Primary stack:** FastAPI, Python, PyTorch, SQLite, HTML/CSS/JavaScript
- **Dataset:** HLS-CMDS dataset with HS (heart sounds), LS (lung sounds), and Mix (mixed sounds)
- **Storage approach:** Audio files are stored in local folders. SQLite stores metadata, logs, job records, model records, and evaluation results.

## Core Project Rules
- This project must perform **real separation**, not mock or fake separation.
- NeoSSNet is the current real working separation model.
- The system must produce:
  - separated heart audio
  - separated lung audio
- Do not simulate model output unless I explicitly ask for temporary placeholder behavior during early UI/API testing.
- If temporary placeholder behavior is used for early pipeline testing, clearly mark it as temporary and replace it later with real model inference.
- Prefer the **easiest working solution** over overengineered architecture.
- Keep everything practical for a student Final Year Project.
- Use the existing database and folder structure before suggesting major restructuring.
- Do not break the existing working NeoSSNet path while adding model-selection support.

## System Scope
Main features:
1. Upload mixed WAV file
2. Validate and save audio file
3. Let the user choose an available separation model when model-selection is implemented
4. Run real model inference
5. Generate real heart and lung output files
6. Play original and separated audio in browser
7. Download separated files
8. Store metadata in SQLite
9. Store logs in SQLite
10. Show processing history
11. Support testing and demo presentation

## Expected Architecture
- **Frontend:** HTML, CSS, JavaScript using FastAPI templates and static files
- **Backend API:** FastAPI
- **Machine Learning:** PyTorch implementation of NeoSSNet first; additional models should be added through Strategy + Factory structure
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
- selected model ID
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
- `docs/software_design_report/`
- `.agents/skills/`

Do not create a separate React frontend unless explicitly requested.

## Commands
- **Install:** `pip install -r requirements.txt`
- **Dev:** `uvicorn app.main:app --reload`
- **Dev without reload:** `uvicorn app.main:app`
- **Test:** `pytest`
- **Quick project check:** `python scripts/check_project.py`
- **Lint:** `ruff check .`
- **Format:** `black .`
- **Render PlantUML diagrams:** `python scripts/render_plantuml.py`
- **Render Mermaid diagrams:** `python scripts/render_mermaid.py`

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
- Preserve existing working endpoints unless explicitly asked to change them
- Verify changes with tests/check scripts before summarizing work

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
- Do not commit `.env`, large generated outputs, dataset files, model weights, runtime database files, or dataset junk files
- Do not hardcode NeoSSNet throughout the codebase when adding model-selection support

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

## Maintainability / Model Selection Rules
The model-selection feature must be designed so new separation models can be added later without rewriting the upload, separation, history, result, download, or frontend workflow.

Use a Strategy + Factory structure:

- `SeparationAlgorithm` = common interface for all separation models
- `NeoSSNetStrategy` = current real model implementation
- `SeparationAlgorithmFactory` / `ModelFactory` = creates the correct strategy based on the selected model record
- `SeparationService` = uses the interface, not a hardcoded model class

Adding a new model later should mainly require:

1. adding a new strategy class
2. registering it in the factory
3. adding a model row in SQLite

Do not hardcode NeoSSNet throughout the codebase.

Do not duplicate the separation workflow for every model.

Keep the code easy to test, maintain, extend, and explain in the Software Design report.

The design should support the selected patterns:

- Facade Pattern: `SeparationService`
- Strategy Pattern: `SeparationAlgorithm` and `NeoSSNetStrategy`
- Factory Method Pattern: `SeparationAlgorithmFactory` / `ModelFactory`

## API Rules
Expected endpoints may include:
- `POST /upload`
- `POST /separate/{audio_id}`
- `POST /separate/{audio_id}?model_id={model_id}`
- `GET /models`
- `GET /result/{job_id}`
- `GET /download/{job_id}/{type}`
- `GET /history`
- `GET /logs/{job_id}`
- `GET /health`

Do not invent inconsistent endpoint naming if routes already exist.

Recommended implementation order for model selection:
1. preserve current NeoSSNet inference function
2. add `SeparationAlgorithm` abstraction
3. add `NeoSSNetStrategy`
4. add model lookup/list service
5. add model/algorithm factory
6. update separation service to use selected/default model
7. add `GET /models`
8. add frontend model dropdown
9. update tests
10. verify old and new separation flows

## Frontend Rules
- Keep UI clean, modern, and simple
- Prioritize upload, playback, result viewing, download flow, and model selection
- Show meaningful status messages
- Use clear handling for error states
- Make the interface easy to demo to lecturer/examiner
- Use FastAPI templates and static files first
- Do not add React unless explicitly requested
- If model-selection support is added, use a simple dropdown populated from `GET /models`
- If model loading fails in the frontend, keep the upload UI usable and fall back to default backend behavior when possible

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
  - selected model ID is recorded when model selection is used
  - logs are written
  - history loads correctly
  - `GET /models` works if model selection is implemented
  - both `/separate/{audio_id}` and `/separate/{audio_id}?model_id=1` work after model selection is implemented

## Software Design Report Rules
- The report is written in LaTeX under `docs/software_design_report/`
- Use APA-style BibLaTeX references in `references.bib`
- Keep diagrams clean, readable, and aligned with the actual/proposed design
- Use PlantUML for formal UML/pattern diagrams
- Use Mermaid only when it produces cleaner overview/workflow diagrams
- Do not insert `architecture_diagram`, `system_workflow`, or `upload_separation_sequence` unless explicitly requested
- Design pattern diagrams should focus on pattern roles only, not the whole system
- The selected patterns should remain:
  - Facade Pattern
  - Strategy Pattern
  - Factory Method Pattern
- Documentation and diagrams should reflect the code or clearly label proposed design classes when they are not yet implemented

## When Stuck
- First identify whether the issue is:
  - frontend
  - backend
  - database
  - file path / storage
  - dataset structure
  - model inference
  - audio preprocessing
  - LaTeX/report
  - diagram rendering
  - Git/GitHub
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
- Do not commit runtime database files such as `database/*.db`
- Do not commit datasets unless explicitly requested
- Do not commit model weights such as `*.pt`, `*.pth`, or `*.onnx` unless explicitly requested

## GitHub Workflow
When making code, report, or documentation changes, always provide Git commands at the end.

Before suggesting `git add .`, check that `.gitignore` excludes:
- `.env`
- database runtime files such as `database/*.db`
- datasets/
- `storage/uploads/`
- `storage/outputs/`
- `storage/logs/`
- model weights such as `*.pt`, `*.pth`, `*.onnx`
- Python cache files
- LaTeX auxiliary files if they should not be committed

After each completed task, provide commands like:

```bash
git status
git add .
git commit -m "Clear short commit message"
git push
```

If only specific files changed, prefer safer commands like:

```bash
git add path/to/file1 path/to/file2
git commit -m "Clear short commit message"
git push
```

Do not run `git push` unless the user wants to push changes.

Warn the user before adding generated files, datasets, model weights, database files, or `.env`.

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
- After changes, include a Git section with recommended `git status`, `git add`, `git commit`, and `git push` commands

## Priority Order
When making decisions, prioritize in this order:
1. Real functionality
2. Simplicity
3. Easy local execution
4. Maintainability and model extensibility
5. Clean architecture
6. Academic/FYP presentation value
7. Performance optimization later
