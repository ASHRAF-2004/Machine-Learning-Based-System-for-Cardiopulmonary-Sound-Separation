# Demo Steps

## Before The Demo

Confirm the required project files are present:

```powershell
python scripts/check_project.py
```

Run the tests:

```powershell
pytest -q
```

Optional: run the standalone NeoSSNet smoke test:

```powershell
python scripts/test_neossnet_inference.py
```

This verifies that NeoSSNet can load `storage/ml_models/model_best.pt` and `storage/ml_models/model.yaml`, read `sample_inputs/H0001.wav`, and create test outputs.

## Start The Web Application

From the project root:

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

## Demo Workflow

1. Open the web UI.
2. Briefly explain that the system accepts a mixed cardiopulmonary WAV file.
3. Choose a `.wav` input file.
4. Upload the file.
5. Point out that the backend saves the upload under `storage/uploads/raw/` and inserts an `uploaded_audio` row.
6. Run separation from the UI.
7. Explain that the backend creates a `separation_job` row with status `running`.
8. Wait for NeoSSNet inference to finish.
9. Show that the job status becomes `completed`.
10. Play the heart sound output in the browser.
11. Play the lung sound output in the browser.
12. Use the download buttons for the heart and lung WAV files.
13. Show the recent history section.
14. Explain that history comes from SQLite job and result records.

## API Checks During Demo

Health check:

```text
http://127.0.0.1:8000/health
```

Recent history:

```text
http://127.0.0.1:8000/history
```

Result details after a job completes:

```text
http://127.0.0.1:8000/result/{job_id}
```

Download output files:

```text
http://127.0.0.1:8000/download/{job_id}/heart
http://127.0.0.1:8000/download/{job_id}/lung
```

Replace `{job_id}` with the completed job ID shown by the UI or returned from the API.

## What To Explain In The Presentation

- The frontend is a simple FastAPI template UI, not a separate React app.
- FastAPI handles upload, separation, result lookup, download, and history endpoints.
- SQLite stores metadata, model paths, job status, result paths, timing, and errors.
- WAV files are stored on the filesystem because they are large binary files.
- NeoSSNet performs real separation; the outputs are not fake or copied placeholders.
- Dataset folders are separate from runtime upload and output folders.
- The current prototype is for academic demonstration and is not a clinical diagnostic tool.

## Expected Output Files

For a completed web separation job:

```text
storage/outputs/heart/{job_id}_heart.wav
storage/outputs/lung/{job_id}_lung.wav
```

For the standalone inference test:

```text
storage/outputs/heart/test_heart.wav
storage/outputs/lung/test_lung.wav
```

## Troubleshooting

If the web page does not load:

- Confirm `uvicorn app.main:app --reload` is running.
- Confirm the address is `http://127.0.0.1:8000/`.

If upload fails:

- Confirm the file extension is `.wav`.
- Confirm the file is a readable WAV file, not a renamed non-WAV file.

If separation fails:

- Confirm the active model row in SQLite points to `storage/ml_models/model_best.pt` and `storage/ml_models/model.yaml`.
- Confirm `external/neossnet_source/` exists.
- Run `python scripts/test_neossnet_inference.py` to isolate the ML inference path from the web app.

If downloads fail:

- Confirm the job completed successfully.
- Confirm the files exist under `storage/outputs/heart/` and `storage/outputs/lung/`.
