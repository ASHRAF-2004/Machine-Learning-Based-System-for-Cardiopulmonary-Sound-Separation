# Lecturer Demo Guide

This guide is for demonstrating the FastAPI cardiopulmonary sound separation project to a lecturer. All paths are relative to the project root.

## 1. Project Locations

- Project root: the folder that contains `app/`, `database/`, `storage/`, `requirements.txt`, and `README.md`.
- FastAPI app folder: `app/`
- FastAPI startup file: `app/main.py`
- SQLite database file: `database/cardiopulmonary.db`
- Database schema file: `database/schema.sql`
- Upload endpoint: `POST /upload` in `app/routers/upload.py`
- Separation endpoint: `POST /separate/{audio_id}` in `app/routers/separation.py`
- Web UI: `GET /`
- Swagger UI: `GET /docs`

## 2. Run The Project Demo

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open one of these in the browser:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/docs
```

The app creates `database/cardiopulmonary.db` and required `storage/` folders automatically at startup. Optional manual initialization:

```powershell
python scripts/init_db.py
```

## 3. Demo Audio Separation

Use one of the included sample WAV files:

```text
sample_inputs/H0001.wav
sample_inputs/H0002.wav
sample_inputs/H0003.wav
```

Web UI flow:

1. Open `http://127.0.0.1:8000/`.
2. Select `sample_inputs/H0001.wav`.
3. Keep the model dropdown on the active NeoSSNet model.
4. Click `Run separation`.
5. Wait until the status becomes completed.
6. Preview the heart and lung audio players.
7. Confirm output files are created:

```text
storage/outputs/heart/{job_id}_heart.wav
storage/outputs/lung/{job_id}_lung.wav
```

Swagger UI flow:

1. Open `http://127.0.0.1:8000/docs`.
2. Run `POST /upload` with a WAV file.
3. Copy the returned `audio_id`.
4. Run `POST /separate/{audio_id}`.
5. Copy the returned `job_id`.
6. Run `GET /result/{job_id}`.
7. Run `GET /history`.

## 4. Open SQLite Database In DBeaver

1. Open DBeaver.
2. Click `New Database Connection`.
3. Choose `SQLite`.
4. For the database file, select:

```text
database/cardiopulmonary.db
```

5. Test the connection.
6. Finish and open the database.
7. Open these tables:

```text
uploaded_audio
model
separation_job
separation_result
evaluation_metric
system_log
```

Main history tables:

- `uploaded_audio`: one row per uploaded WAV file.
- `separation_job`: one row per separation request.
- `separation_result`: heart/lung output paths for completed jobs.
- `system_log`: start/completion/failure logs for separation jobs.
- `evaluation_metric`: reserved for metric results; it may be empty during a normal web demo.

## 5. SQL Queries For The Demo

Row counts before and after demo:

```sql
SELECT 'uploaded_audio' AS table_name, COUNT(*) AS row_count FROM uploaded_audio
UNION ALL
SELECT 'separation_job', COUNT(*) FROM separation_job
UNION ALL
SELECT 'separation_result', COUNT(*) FROM separation_result
UNION ALL
SELECT 'system_log', COUNT(*) FROM system_log
UNION ALL
SELECT 'evaluation_metric', COUNT(*) FROM evaluation_metric;
```

Latest uploaded audio:

```sql
SELECT
    uploaded_audio_id,
    original_filename,
    stored_path,
    sample_rate_hz,
    channels,
    duration_sec,
    file_size_bytes,
    uploaded_at
FROM uploaded_audio
ORDER BY uploaded_at DESC, uploaded_audio_id DESC
LIMIT 5;
```

Latest separation jobs:

```sql
SELECT
    job_id,
    uploaded_audio_id,
    model_id,
    status,
    requested_at,
    started_at,
    completed_at,
    processing_time_ms,
    error_message
FROM separation_job
ORDER BY requested_at DESC, job_id DESC
LIMIT 5;
```

Latest heart/lung output paths:

```sql
SELECT
    r.result_id,
    r.job_id,
    a.original_filename,
    j.status,
    r.heart_file_path,
    r.lung_file_path,
    r.output_sample_rate_hz,
    r.output_duration_sec,
    r.created_at
FROM separation_result r
JOIN separation_job j ON j.job_id = r.job_id
JOIN uploaded_audio a ON a.uploaded_audio_id = j.uploaded_audio_id
ORDER BY r.created_at DESC, r.result_id DESC
LIMIT 5;
```

Latest separation logs:

```sql
SELECT
    log_id,
    job_id,
    log_level,
    source_component,
    event_type,
    message,
    created_at
FROM system_log
ORDER BY created_at DESC, log_id DESC
LIMIT 10;
```

Show the full latest job history in one query:

```sql
SELECT
    j.job_id,
    a.original_filename,
    m.model_name,
    m.version,
    j.status,
    j.processing_time_ms,
    r.heart_file_path,
    r.lung_file_path,
    j.requested_at,
    j.completed_at
FROM separation_job j
JOIN uploaded_audio a ON a.uploaded_audio_id = j.uploaded_audio_id
JOIN model m ON m.model_id = j.model_id
LEFT JOIN separation_result r ON r.job_id = j.job_id
ORDER BY j.requested_at DESC, j.job_id DESC
LIMIT 5;
```

Evaluation metrics, if available:

```sql
SELECT
    metric_id,
    result_id,
    metric_name,
    metric_scope,
    metric_value,
    metric_unit,
    recorded_at
FROM evaluation_metric
ORDER BY recorded_at DESC, metric_id DESC
LIMIT 10;
```

## 6. Prove Database Update Before And After Separation

Before upload:

1. Run the row count query.
2. Note the counts for `uploaded_audio`, `separation_job`, `separation_result`, and `system_log`.

After upload:

1. Upload `sample_inputs/H0001.wav` in the web UI or Swagger UI.
2. Run the latest uploaded audio query.
3. Show the new row in `uploaded_audio`.
4. Explain that the database stores metadata only; the WAV file is stored under `storage/uploads/raw/`.

After separation:

1. Run separation from the UI or `POST /separate/{audio_id}`.
2. Run the latest separation jobs query.
3. Show the new `separation_job` row with status `completed`.
4. Run the latest heart/lung output paths query.
5. Show the new `separation_result` row with `heart_file_path` and `lung_file_path`.
6. Run the latest separation logs query.
7. Show `separation_started` and `separation_completed` logs for the job.
8. Open the output folder and show:

```text
storage/outputs/heart/{job_id}_heart.wav
storage/outputs/lung/{job_id}_lung.wav
```

## 7. Design Patterns To Demonstrate

### Facade Pattern

- File: `app/services/separation_service.py`
- Class: `SeparationService`
- Main method: `separate_uploaded_audio`
- Problem solved: the route does not need to manage upload lookup, model lookup, factory selection, output paths, inference, job status, result records, and logs.
- What to show: `app/routers/separation.py` calls one service function, while `SeparationService` coordinates the workflow.

Project role mapping:

| Facade participant | Project file/class | What to show in the demo |
| --- | --- | --- |
| Client | `app/routers/separation.py`, `separate_audio` | The route receives `audio_id` and calls one service function. |
| Facade | `app/services/separation_service.py`, `SeparationService` | This class coordinates the full separation workflow. |
| Subsystem: upload lookup | `app/services/separation_service.py`, `get_uploaded_audio` | Gets the uploaded file metadata from SQLite. |
| Subsystem: model lookup | `app/services/model_service.py`, `get_model_for_separation` | Selects the requested or active model record. |
| Subsystem: storage paths | `app/services/storage_service.py` | Resolves upload paths and builds heart/lung output paths. |
| Subsystem: factory | `app/services/separation_algorithm_factory.py`, `SeparationAlgorithmFactory` | Creates the correct separation strategy from `model.architecture`. |
| Subsystem: strategy context | `app/ml/separation_engine.py`, `SeparationEngine` | Runs the selected strategy through the shared interface. |
| Subsystem: real ML inference | `app/ml/neossnet_strategy.py` and `app/ml/neossnet_inference.py` | Runs real NeoSSNet inference and writes output audio. |
| Subsystem: result database update | `app/services/result_service.py`, `create_separation_result` | Inserts heart/lung result paths into SQLite. |
| Subsystem: job/log update | `app/services/separation_service.py`, `create_running_job`, `add_system_log`, job status update | Inserts/updates job status and separation logs. |

Short lecturer explanation:

> The Facade is not doing every low-level task by itself. It gives the route one simple method, then delegates to smaller subsystems for model selection, storage paths, strategy creation, inference, database result insertion, and logging.

### Strategy Pattern

- Interface: `app/ml/separation_algorithm.py`, `SeparationAlgorithm`
- Context: `app/ml/separation_engine.py`, `SeparationEngine`
- Concrete strategy: `app/ml/neossnet_strategy.py`, `NeoSSNetStrategy`
- Problem solved: the engine can run any future separation algorithm that implements the same `separate(...)` method.
- What to show: `SeparationEngine` calls `self.algorithm.separate(...)`, not a hardcoded NeoSSNet function.

Project role mapping:

| Strategy participant | Project file/class | What to show in the demo |
| --- | --- | --- |
| Client | `app/services/separation_service.py`, `SeparationService` | Creates the engine with the selected algorithm. |
| Context | `app/ml/separation_engine.py`, `SeparationEngine` | Calls `self.algorithm.separate(...)`. |
| Strategy interface | `app/ml/separation_algorithm.py`, `SeparationAlgorithm` | Defines the common `separate(...)` operation. |
| Concrete strategy | `app/ml/neossnet_strategy.py`, `NeoSSNetStrategy` | Implements the interface using real NeoSSNet inference. |
| Future strategy slot | A future strategy class | A new model can be added without changing the route. |

### Factory Method Pattern

- File: `app/services/separation_algorithm_factory.py`
- Creator: `SeparationAlgorithmFactory`
- Factory method: `create_algorithm(model)`
- Product interface: `SeparationAlgorithm`
- Concrete product: `NeoSSNetStrategy`
- Problem solved: the separation workflow does not directly instantiate a concrete model strategy.
- What to show: the factory reads `model.architecture` and returns the correct strategy object.

Project role mapping:

| Factory Method participant | Project file/class | What to show in the demo |
| --- | --- | --- |
| Client | `app/services/separation_service.py`, `SeparationService` | Requests an algorithm for the selected model. |
| Creator | `app/services/separation_algorithm_factory.py`, `SeparationAlgorithmFactory` | Contains `create_algorithm(model)`. |
| Product interface | `app/ml/separation_algorithm.py`, `SeparationAlgorithm` | The type returned by the factory. |
| Concrete product | `app/ml/neossnet_strategy.py`, `NeoSSNetStrategy` | The current product when `model.architecture` is `NeoSSNet`. |
| Selection data | SQLite `model` table | `architecture`, `checkpoint_path`, and `config_path` control the created strategy and inference files. |

Upload validation also has a small factory method structure:

- File: `app/services/audio_validation.py`
- Creator: `AudioValidatorFactory`
- Concrete creator: `WavAudioValidatorFactory`
- Product: `AudioValidator`
- Concrete product: `WavAudioValidator`

## 8. What To Say To The Lecturer

Starting the server:

> I start the FastAPI server from the project root. The app automatically creates the SQLite database and required storage folders if they are missing.

Uploading audio:

> I upload a WAV recording. The backend validates the file, saves it under `storage/uploads/raw/`, and inserts its metadata into `uploaded_audio`.

Running separation:

> I run separation for the uploaded audio. The backend creates a separation job, selects the active NeoSSNet model, runs real PyTorch inference, and saves two output WAV files.

Showing DBeaver:

> In DBeaver, the database shows the system history. After upload, `uploaded_audio` increases. After separation, `separation_job`, `separation_result`, and `system_log` show the completed workflow.

Explaining Facade Pattern:

> `SeparationService` is the Facade. The route calls one method, but the service hides the subsystems behind the workflow: model lookup, storage path handling, strategy factory selection, inference, output file creation, database result insertion, job status updates, and logs.

Explaining Strategy Pattern:

> `SeparationAlgorithm` is the strategy interface. `NeoSSNetStrategy` is the current concrete strategy. `SeparationEngine` runs the selected strategy without knowing the internal model implementation.

Explaining Factory Method Pattern:

> `SeparationAlgorithmFactory` creates the correct strategy from the model record. Currently it returns `NeoSSNetStrategy`, but a future model can be added by registering another strategy without rewriting the route or separation workflow.

Explaining the sequence workflow:

> The workflow follows the sequence diagram: upload request enters FastAPI, validation and storage happen, upload metadata is inserted, separation request enters FastAPI, `SeparationService` coordinates the workflow, the factory creates the strategy, the engine runs the strategy, NeoSSNet saves outputs, result rows and logs are inserted, and the API returns the completed job.
