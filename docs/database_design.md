# Database Design

## Overview

The project uses SQLite to store structured metadata for uploads, model configuration, separation jobs, output results, evaluation metrics, and logs.

The database file is:

```text
database/cardiopulmonary.db
```

The schema definition is:

```text
database/schema.sql
```

The database does not store full WAV audio content. WAV files are stored on the filesystem and SQLite stores their paths and metadata.

## Tables

### `uploaded_audio`

Stores one row for each uploaded mixed WAV file.

Important fields:

- `uploaded_audio_id`: primary key used by separation requests.
- `original_filename`: filename provided by the user after cleanup.
- `stored_path`: local path where the uploaded WAV was saved.
- `mime_type`: uploaded file type, normally `audio/wav`.
- `sample_rate_hz`: detected sample rate from the WAV header.
- `channels`: number of audio channels.
- `bit_depth`: sample width in bits.
- `duration_sec`: audio duration.
- `file_size_bytes`: uploaded file size.
- `uploaded_at`: upload timestamp.

Relationship:

- One uploaded audio record can have many `separation_job` records.

### `model`

Stores metadata for available NeoSSNet model files.

Important fields:

- `model_id`: primary key.
- `model_name`: model name, such as `NeoSSNet`.
- `version`: model version label.
- `architecture`: model architecture, currently NeoSSNet.
- `framework`: framework, currently PyTorch.
- `checkpoint_path`: path to the model checkpoint file.
- `config_path`: path to the model YAML config file.
- `is_active`: marks which model should be used by the backend.
- `created_at`: model record creation timestamp.

Relationship:

- One model record can be used by many `separation_job` records.

The working prototype expects the active model row to point to:

```text
storage/ml_models/model_best.pt
storage/ml_models/model.yaml
```

### `separation_job`

Stores the processing state for each separation request. This is the central workflow table.

Important fields:

- `job_id`: primary key returned by the separation API.
- `uploaded_audio_id`: links the job to an uploaded WAV file.
- `model_id`: links the job to the active model used for inference.
- `status`: one of `queued`, `running`, `completed`, `failed`, or `cancelled`.
- `requested_at`: time the job was requested.
- `started_at`: time processing started.
- `completed_at`: time processing ended.
- `processing_time_ms`: measured runtime in milliseconds.
- `parameters_json`: optional JSON text for future inference settings.
- `error_message`: stores failure details when inference fails.

Relationships:

- Many jobs can belong to one uploaded audio record.
- Many jobs can use one model record.
- One completed job has one `separation_result` row.
- One job can have many `system_log` rows.

### `separation_result`

Stores output metadata for completed separation jobs.

Important fields:

- `result_id`: primary key.
- `job_id`: unique link to `separation_job`.
- `heart_file_path`: filesystem path to the separated heart WAV file.
- `lung_file_path`: filesystem path to the separated lung WAV file.
- `output_sample_rate_hz`: output sample rate.
- `output_duration_sec`: output duration.
- `heart_file_size_bytes`: heart output file size.
- `lung_file_size_bytes`: lung output file size.
- `created_at`: result creation timestamp.

Relationship:

- Each `separation_result` belongs to exactly one `separation_job`.
- `job_id` is unique, so a job cannot have multiple result rows.
- One result can have many `evaluation_metric` rows.

### `evaluation_metric`

Stores optional evaluation scores for separated outputs.

Important fields:

- `metric_id`: primary key.
- `result_id`: links the metric to a separation result.
- `metric_name`: metric name, such as `SNR`, `SDR`, `SI-SDR`, `MSE`, or `MAE`.
- `metric_scope`: `heart`, `lung`, or `overall`.
- `metric_value`: numeric score.
- `metric_unit`: optional unit.
- `reference_type`: optional note about the reference signal used.
- `recorded_at`: metric timestamp.

Relationship:

- Many metrics can belong to one separation result.
- The schema prevents duplicate metrics for the same result, metric name, and scope.

### `system_log`

Stores structured log messages for important system events.

Important fields:

- `log_id`: primary key.
- `job_id`: optional link to a separation job.
- `log_level`: `DEBUG`, `INFO`, `WARNING`, or `ERROR`.
- `source_component`: source area such as `frontend`, `api`, `ml_model`, `database`, `filesystem`, or `system`.
- `event_type`: short event category.
- `message`: log message.
- `created_at`: log timestamp.

Relationship:

- Many logs can belong to one separation job.
- Logs can also be system-level records without a job ID.

## Relationship Summary

```text
uploaded_audio 1 --- many separation_job
model          1 --- many separation_job
separation_job 1 --- 0..1 separation_result
separation_result 1 --- many evaluation_metric
separation_job 1 --- many system_log
```

## SQLite vs Filesystem

SQLite stores:

- uploaded file metadata
- model metadata and active model paths
- job status
- timestamps
- processing time
- output file paths
- error messages
- evaluation metric values
- structured logs

The filesystem stores:

- uploaded mixed WAV files
- separated heart WAV files
- separated lung WAV files
- NeoSSNet checkpoint and config files
- HLS-CMDS dataset files
- temporary runtime files

This design avoids storing large binary audio blobs in SQLite. It keeps the database small, easier to inspect, and easier to explain during presentation.

## Main Runtime Flow In The Database

1. A user uploads a WAV file.
2. A row is inserted into `uploaded_audio`.
3. The user requests separation for that `uploaded_audio_id`.
4. The backend reads the active row from `model`.
5. A row is inserted into `separation_job` with status `running`.
6. NeoSSNet inference creates heart and lung WAV files.
7. A row is inserted into `separation_result`.
8. The job status changes to `completed`.
9. If inference fails, the job status changes to `failed` and `error_message` is saved.

## Why This Design Fits The Prototype

- The schema is small enough for a student project but still reflects a real processing workflow.
- The central `separation_job` table makes it easy to explain job tracking.
- The `separation_result` table cleanly separates job state from output metadata.
- File paths keep SQLite lightweight while preserving traceability between database rows and generated files.
- The design can later support evaluation metrics, logs, model versions, and richer history without changing the core upload and separation workflow.
