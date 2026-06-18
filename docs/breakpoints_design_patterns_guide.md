# Breakpoints And Design Patterns Guide

Use this guide to demonstrate the running workflow in VS Code or PyCharm. All paths are relative to the project root.

## 1. Debugger Setup

Start FastAPI in debug mode from the project root.

VS Code terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

PyCharm:

- Script/module: `uvicorn`
- Parameters: `app.main:app --reload`
- Working directory: project root

Open the app:

```text
http://127.0.0.1:8000/
```

Use `sample_inputs/H0001.wav` for the demo.

## 2. Sequence Workflow Breakpoints

Place these breakpoints in order.

| Step | File | Breakpoint target | Inspect |
| --- | --- | --- | --- |
| 1. Upload request enters FastAPI | `app/routers/upload.py` | line 23, `async def upload_audio(...)` | `file.filename`, `file.content_type` |
| 2. Factory creates validator | `app/routers/upload.py` | line 28, `audio_validator_factory.create_validator(...)` | `audio_validator_factory`, `file.filename` |
| 3. Factory method decision | `app/services/audio_validation.py` | line 46, `def create_validator(...)` | `filename`, returned `WavAudioValidator` |
| 4. WAV validation | `app/services/audio_validation.py` | line 22, `async def validate(...)` | `filename`, `header` at line 28 |
| 5. File save starts | `app/services/storage_service.py` | line 104, `async def save_uploaded_wav(...)` | `original_filename`, `destination` |
| 6. Uploaded audio DB insert | `app/routers/upload.py` | line 50, `db.add(audio_record)` | `audio_record.original_filename`, `audio_record.stored_path` |
| 7. Upload commit | `app/routers/upload.py` | line 52, `db.commit()` | `audio_record.uploaded_audio_id` after refresh |
| 8. Separation request enters FastAPI | `app/routers/separation.py` | line 25, `def separate_audio(...)` | `audio_id`, `model_id` |
| 9. Route calls Facade | `app/routers/separation.py` | line 31, `separate_uploaded_audio(...)` | returned `result` |
| 10. Facade starts workflow | `app/services/separation_service.py` | line 129, `def separate_uploaded_audio(...)` | `db`, `audio_id`, `model_id` |
| 11. Model record selected | `app/services/separation_service.py` | line 136, `model_service.get_model_for_separation(...)` | `model.model_id`, `model.architecture`, `model.checkpoint_path` |
| 12. Factory creates strategy | `app/services/separation_service.py` | line 137, `create_algorithm_from_factory(...)` | `self.algorithm_factory`, returned `algorithm` |
| 13. Factory method implementation | `app/services/separation_algorithm_factory.py` | line 22, `def create_algorithm(...)` | `model.architecture`, `strategy_class` |
| 14. Strategy context created | `app/services/separation_service.py` | line 138, `self.engine_class(...)` | `engine.algorithm` |
| 15. Job row created | `app/services/separation_service.py` | line 151, `create_running_job(...)` | `job.job_id`, `job.status` |
| 16. Start log inserted | `app/services/separation_service.py` | line 57, `add_system_log(...)` | `event_type = separation_started` |
| 17. Strategy context delegates | `app/ml/separation_engine.py` | line 21, `def separate(...)` | `self.algorithm`, paths |
| 18. Concrete strategy runs | `app/ml/neossnet_strategy.py` | line 14, `def separate(...)` | `input_wav_path`, `model_path`, `model_config_path` |
| 19. NeoSSNet inference starts | `app/ml/neossnet_inference.py` | line 144, `def run_neossnet_inference(...)` | `input_wav_path`, `device_name` |
| 20. Output WAV files saved | `app/ml/neossnet_inference.py` | lines 169-170, `save_mono_wav(...)` | `heart_output_path`, `lung_output_path` |
| 21. Result row inserted | `app/services/result_service.py` | line 116, `def create_separation_result(...)` | `result.heart_file_path`, `result.lung_file_path` |
| 22. Completion log inserted | `app/services/separation_service.py` | line 177, `add_system_log(...)` | `event_type = separation_completed` |
| 23. Final DB commit | `app/services/separation_service.py` | line 186, `db.commit()` | `job.status`, `job.processing_time_ms` |

## 3. Facade Pattern Demo

Pattern name: Facade Pattern

File path:

```text
app/services/separation_service.py
```

Class/function:

```text
SeparationService.separate_uploaded_audio
```

Breakpoint:

```text
app/services/separation_service.py:129
```

What it solves:

`SeparationService` gives the route one simple operation for the whole separation workflow. It hides upload lookup, model lookup, strategy factory selection, path resolution, inference, output creation, database result creation, status updates, and logs.

Inspect:

- `uploaded_audio`
- `model`
- `algorithm`
- `engine`
- `job`
- `output_paths`
- `inference_result`
- `result`

What to say:

> This class is the Facade. The FastAPI route does not know all the workflow details. It calls one service method, and the service coordinates the internal subsystems.

How it matches the sequence workflow:

The route calls `separate_uploaded_audio`, then the Facade coordinates model selection, factory creation, strategy execution, database job update, result insert, and logging.

## 4. Strategy Pattern Demo

Pattern name: Strategy Pattern

Files:

```text
app/ml/separation_algorithm.py
app/ml/separation_engine.py
app/ml/neossnet_strategy.py
```

Classes/functions:

```text
SeparationAlgorithm
SeparationEngine
NeoSSNetStrategy
```

Breakpoints:

```text
app/ml/separation_engine.py:21
app/ml/neossnet_strategy.py:14
```

What it solves:

The separation workflow can run any algorithm that implements the same `separate(...)` interface. The route and service do not need to know the internal NeoSSNet implementation.

Inspect:

- `self.algorithm` inside `SeparationEngine`
- `type(self.algorithm)`
- `input_wav_path`
- `model_path`
- `heart_output_path`
- `lung_output_path`

What to say:

> `SeparationEngine` is the context. It calls the algorithm through the `SeparationAlgorithm` interface. Today the concrete strategy is `NeoSSNetStrategy`, but another model can be added later without changing the route.

How it matches the sequence workflow:

The Facade creates the engine with the selected strategy. The engine delegates to `NeoSSNetStrategy`, which calls the real NeoSSNet inference boundary.

## 5. Factory Method Pattern Demo

Pattern name: Factory Method Pattern

File path:

```text
app/services/separation_algorithm_factory.py
```

Class/function:

```text
SeparationAlgorithmFactory.create_algorithm
```

Breakpoint:

```text
app/services/separation_algorithm_factory.py:22
```

What it solves:

The separation service does not directly instantiate `NeoSSNetStrategy`. The factory reads the selected `model` row and creates the correct strategy based on `model.architecture`.

Inspect:

- `model.model_id`
- `model.model_name`
- `model.architecture`
- `cls._registry`
- `strategy_class`
- returned strategy object

What to say:

> This is the Factory Method part of the design. The database model record says which architecture is selected. The factory converts that record into the correct strategy object. This keeps object creation separate from the business workflow.

How it matches the sequence workflow:

`SeparationService` loads the model record, calls `SeparationAlgorithmFactory.create_algorithm(model)`, receives a `SeparationAlgorithm`, then passes it to `SeparationEngine`.

## 6. Upload Validation Factory Demo

The upload route also contains a small Factory Method structure for file validation.

Files:

```text
app/routers/upload.py
app/services/audio_validation.py
```

Classes/functions:

```text
AudioValidatorFactory
WavAudioValidatorFactory
AudioValidator
WavAudioValidator
```

Breakpoints:

```text
app/routers/upload.py:28
app/services/audio_validation.py:46
app/services/audio_validation.py:22
```

Inspect:

- `file.filename`
- `suffix`
- returned `WavAudioValidator`
- `header`

What to say:

> The upload route asks a factory for the correct validator instead of directly creating the validator inside the route. For this prototype, only WAV is accepted.

## 7. Database Update Breakpoints

Upload insert:

```text
app/routers/upload.py:50
app/routers/upload.py:52
```

Inspect:

- `audio_record`
- `audio_record.uploaded_audio_id`

Separation job insert:

```text
app/services/separation_service.py:151
app/services/separation_service.py:55
```

Inspect:

- `job.job_id`
- `job.status`
- `job.started_at`

Separation result insert:

```text
app/services/result_service.py:116
app/services/separation_service.py:169
```

Inspect:

- `result.job_id`
- `result.heart_file_path`
- `result.lung_file_path`

Separation logs:

```text
app/services/separation_service.py:57
app/services/separation_service.py:177
```

Inspect:

- `event_type`
- `message`
- `job_id`

## 8. API Response Breakpoints

Upload response:

```text
app/routers/upload.py
```

Place a breakpoint on the final `return` statement. Inspect:

- `audio_record.uploaded_audio_id`
- `audio_record.stored_path`

Separation response:

```text
app/routers/separation.py
```

Place a breakpoint on the final `return` statement. Inspect:

- `result.job_id`
- `result.status`
- `result.heart_file_path`
- `result.lung_file_path`

## 9. Debugging Script To Follow During Demo

1. Start the debugger.
2. Open the web UI.
3. Upload `sample_inputs/H0001.wav`.
4. Step through upload route, validator factory, validator, storage save, and database insert.
5. Continue until upload succeeds.
6. Run separation.
7. Step through separation route and `SeparationService`.
8. Stop at `SeparationAlgorithmFactory.create_algorithm`.
9. Show that `model.architecture` is `NeoSSNet`.
10. Step into `SeparationEngine`.
11. Step into `NeoSSNetStrategy`.
12. Step into `run_neossnet_inference`.
13. Continue until output files are saved.
14. Step through result insert and completion log.
15. Open DBeaver and show the updated rows.

