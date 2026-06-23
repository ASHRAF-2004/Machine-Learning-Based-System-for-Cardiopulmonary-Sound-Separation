# Database Demo Guide

Presenter: Reshma.

Assumptions:

- DBeaver is already open.
- DBeaver is already connected to `database/cardiopulmonary.db`.
- The SQL query is already pasted in the SQL editor.
- A WAV upload and separation attempt has already been run from the web app.

## Database File

Open this SQLite database:

```text
database/cardiopulmonary.db
```

## Tables To Show

- `uploaded_audio`
- `model`
- `separation_job`
- `separation_result`
- `evaluation_metric`
- `system_log`

## Main Demo Query

```sql
SELECT
    sj.job_id AS job_id,
    sj.uploaded_audio_id AS audio_id,
    ua.original_filename AS original_file_name,
    sj.status,
    sr.heart_file_path,
    sr.lung_file_path,
    sj.requested_at,
    sj.started_at,
    sj.completed_at,
    sj.processing_time_ms
FROM separation_job sj
LEFT JOIN uploaded_audio ua
    ON sj.uploaded_audio_id = ua.uploaded_audio_id
LEFT JOIN separation_result sr
    ON sj.job_id = sr.job_id
ORDER BY sj.job_id DESC;
```

## What To Do

1. After upload/separation, switch to DBeaver.
2. Run the prepared query.
3. Point to the latest row at the top.
4. Explain only the important columns:
   - `job_id`: separation job identifier.
   - `audio_id`: uploaded audio identifier.
   - `original_file_name`: original uploaded WAV filename.
   - `status`: `running`, `completed`, or `failed`.
   - `heart_file_path`: saved heart output path if separation succeeds.
   - `lung_file_path`: saved lung output path if separation succeeds.
   - `requested_at`, `started_at`, `completed_at`: workflow timestamps.
   - `processing_time_ms`: processing duration.

## What To Say

> Now I will show that the database is updated after the separation workflow.
>
> As you can see, this query joins the separation job, uploaded audio, and separation result tables.
>
> The latest row is at the top. It shows the uploaded file, job status, output paths, timestamps, and processing time.
>
> If separation succeeds, the heart and lung output paths are stored here. If inference fails, the failed status and error information can still be recorded, so the system keeps processing history and traceability.
>
> This proves that the prototype has a working database layer and processing history.

## Reshma's SOLID Link

After the query, briefly connect the database demo to SOLID:

> This also supports separation of responsibilities. SQLite stores metadata and history, local folders store WAV files, and service classes coordinate the workflow. This keeps the database layer, storage layer, and business logic easier to maintain.

## What Changes Before And After Separation

Before upload:

- No new row for the selected file in `uploaded_audio`.
- No new job row in `separation_job`.
- No new result row in `separation_result`.

After upload:

- A new row appears in `uploaded_audio`.
- It stores original filename, stored path, MIME type, sample rate, duration, size, and upload time.

After separation:

- A new row appears in `separation_job`.
- If separation succeeds, a new row appears in `separation_result`.
- The result row stores heart and lung output file paths.
- Logs may appear in `system_log`.

## Extra Quick Queries

```sql
SELECT * FROM uploaded_audio ORDER BY uploaded_at DESC LIMIT 5;
```

```sql
SELECT * FROM separation_job ORDER BY requested_at DESC, job_id DESC LIMIT 5;
```

```sql
SELECT * FROM separation_result ORDER BY created_at DESC LIMIT 5;
```

```sql
SELECT * FROM system_log ORDER BY created_at DESC LIMIT 10;
```

## What To Avoid

- Do not explain every column.
- Do not claim the database stores the audio files themselves.
- Do not spend time setting up the DBeaver connection during the presentation.
- Do not panic if the latest job shows `failed`; explain that failed status still proves traceability.
