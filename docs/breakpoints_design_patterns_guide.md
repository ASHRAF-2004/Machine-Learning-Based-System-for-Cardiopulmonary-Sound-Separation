# Breakpoints And Design Patterns Guide

Use this guide to demonstrate the running workflow in VS Code or PyCharm. All paths are relative to the project root.

## 1\. Debugger Setup

Start FastAPI in debug mode from the project root.

VS Code terminal:

```powershell
.\\\\.venv\\\\Scripts\\\\Activate.ps1
python -m uvicorn app.main:app --reload
```

PyCharm:

* Script/module: `uvicorn`
* Parameters: `app.main:app --reload`
* Working directory: project root

Open the app:

```text
http://127.0.0.1:8000/
```

Use `sample\\\_inputs/H0001.wav` for the demo.

## 2\. Sequence Workflow Breakpoints

Place these breakpoints in order.

|Step|File|Breakpoint target|Inspect|
|-|-|-|-|
|1. Upload request enters FastAPI|`app/routers/upload.py`|line 23, `async def upload\\\_audio(...)`|`file.filename`, `file.content\\\_type`|
|2. Factory creates validator|`app/routers/upload.py`|line 28, `audio\\\_validator\\\_factory.create\\\_validator(...)`|`audio\\\_validator\\\_factory`, `file.filename`|
|3. Factory method decision|`app/services/audio\\\_validation.py`|line 46, `def create\\\_validator(...)`|`filename`, returned `WavAudioValidator`|
|4. WAV validation|`app/services/audio\\\_validation.py`|line 22, `async def validate(...)`|`filename`, `header` at line 28|
|5. File save starts|`app/services/storage\\\_service.py`|line 104, `async def save\\\_uploaded\\\_wav(...)`|`original\\\_filename`, `destination`|
|6. Uploaded audio DB insert|`app/routers/upload.py`|line 50, `db.add(audio\\\_record)`|`audio\\\_record.original\\\_filename`, `audio\\\_record.stored\\\_path`|
|7. Upload commit|`app/routers/upload.py`|line 52, `db.commit()`|`audio\\\_record.uploaded\\\_audio\\\_id` after refresh|
|8. Separation request enters FastAPI|`app/routers/separation.py`|line 25, `def separate\\\_audio(...)`|`audio\\\_id`, `model\\\_id`|
|9. Route calls Facade|`app/routers/separation.py`|line 31, `separate\\\_uploaded\\\_audio(...)`|returned `result`|
|10. Facade starts workflow|`app/services/separation\\\_service.py`|line 129, `def separate\\\_uploaded\\\_audio(...)`|`db`, `audio\\\_id`, `model\\\_id`|
|11. Model record selected|`app/services/separation\\\_service.py`|line 136, `model\\\_service.get\\\_model\\\_for\\\_separation(...)`|`model.model\\\_id`, `model.architecture`, `model.checkpoint\\\_path`|
|12. Factory creates strategy|`app/services/separation\\\_service.py`|line 137, `create\\\_algorithm\\\_from\\\_factory(...)`|`self.algorithm\\\_factory`, returned `algorithm`|
|13. Factory method implementation|`app/services/separation\\\_algorithm\\\_factory.py`|line 22, `def create\\\_algorithm(...)`|`model.architecture`, `strategy\\\_class`|
|14. Strategy context created|`app/services/separation\\\_service.py`|line 138, `self.engine\\\_class(...)`|`engine.algorithm`|
|15. Job row created|`app/services/separation\\\_service.py`|line 151, `create\\\_running\\\_job(...)`|`job.job\\\_id`, `job.status`|
|16. Start log inserted|`app/services/separation\\\_service.py`|line 57, `add\\\_system\\\_log(...)`|`event\\\_type = separation\\\_started`|
|17. Strategy context delegates|`app/ml/separation\\\_engine.py`|line 21, `def separate(...)`|`self.algorithm`, paths|
|18. Concrete strategy runs|`app/ml/neossnet\\\_strategy.py`|line 14, `def separate(...)`|`input\\\_wav\\\_path`, `model\\\_path`, `model\\\_config\\\_path`|
|19. NeoSSNet inference starts|`app/ml/neossnet\\\_inference.py`|line 144, `def run\\\_neossnet\\\_inference(...)`|`input\\\_wav\\\_path`, `device\\\_name`|
|20. Output WAV files saved|`app/ml/neossnet\\\_inference.py`|lines 169-170, `save\\\_mono\\\_wav(...)`|`heart\\\_output\\\_path`, `lung\\\_output\\\_path`|
|21. Result row inserted|`app/services/result\\\_service.py`|line 116, `def create\\\_separation\\\_result(...)`|`result.heart\\\_file\\\_path`, `result.lung\\\_file\\\_path`|
|22. Completion log inserted|`app/services/separation\\\_service.py`|line 177, `add\\\_system\\\_log(...)`|`event\\\_type = separation\\\_completed`|
|23. Final DB commit|`app/services/separation\\\_service.py`|line 186, `db.commit()`|`job.status`, `job.processing\\\_time\\\_ms`|

## 3\. Facade Pattern Demo

Pattern name: Facade Pattern

File path:

```text
app/services/separation\\\_service.py
```

Class/function:

```text
SeparationService.separate\\\_uploaded\\\_audio
```

Breakpoint:

```text
app/services/separation\\\_service.py:129
```

What it solves:

`SeparationService` gives the route one simple operation for the whole separation workflow. It hides upload lookup, model lookup, strategy factory selection, path resolution, inference, output creation, database result creation, status updates, and logs.

Facade participants and subsystems:

|Role|Project file/class|Breakpoint to use|What to inspect|
|-|-|-|-|
|Client|`app/routers/separation.py`, `separate\\\_audio`|`app/routers/separation.py:25`|`audio\\\_id`, `model\\\_id`|
|Facade|`app/services/separation\\\_service.py`, `SeparationService.separate\\\_uploaded\\\_audio`|`app/services/separation\\\_service.py:129`|`db`, `audio\\\_id`, `model\\\_id`|
|Subsystem: upload lookup|`app/services/separation\\\_service.py`, `get\\\_uploaded\\\_audio`|`app/services/separation\\\_service.py:40`|`uploaded\\\_audio.stored\\\_path`|
|Subsystem: model lookup|`app/services/model\\\_service.py`, `get\\\_model\\\_for\\\_separation`|`app/services/model\\\_service.py:65`|`model.model\\\_id`, `model.architecture`, `model.checkpoint\\\_path`|
|Subsystem: storage paths|`app/services/storage\\\_service.py`, `resolve\\\_project\\\_path`, `build\\\_separation\\\_output\\\_paths`|`app/services/storage\\\_service.py:65`, `app/services/storage\\\_service.py:75`|input path and heart/lung output paths|
|Subsystem: factory|`app/services/separation\\\_algorithm\\\_factory.py`, `create\\\_algorithm`|`app/services/separation\\\_algorithm\\\_factory.py:22`|`model.architecture`, `strategy\\\_class`|
|Subsystem: strategy context|`app/ml/separation\\\_engine.py`, `SeparationEngine.separate`|`app/ml/separation\\\_engine.py:21`|`self.algorithm`, output path arguments|
|Subsystem: real inference|`app/ml/neossnet\\\_strategy.py`, `NeoSSNetStrategy.separate`|`app/ml/neossnet\\\_strategy.py:14`|`model\\\_path`, `model\\\_config\\\_path`, returned result|
|Subsystem: result insert|`app/services/result\\\_service.py`, `create\\\_separation\\\_result`|`app/services/result\\\_service.py:116`|`result.heart\\\_file\\\_path`, `result.lung\\\_file\\\_path`|
|Subsystem: job/log update|`app/services/separation\\\_service.py`, `create\\\_running\\\_job`, `add\\\_system\\\_log`, completion update|`app/services/separation\\\_service.py:47`, `app/services/separation\\\_service.py:67`, `app/services/separation\\\_service.py:177`|`job.status`, `event\\\_type`, `processing\\\_time\\\_ms`|

Subsystem explanation:

* `ModelService` hides how the active or selected model is read from SQLite.
* `StorageService` hides project-relative file paths and output folder creation.
* `SeparationAlgorithmFactory` hides concrete strategy creation.
* `SeparationEngine` hides how the selected strategy is executed.
* `NeoSSNetStrategy` and `neossnet\\\_inference.py` hide real PyTorch inference details.
* `ResultService` hides result-row creation for heart/lung output files.
* SQLAlchemy models and `db` session hide the raw SQL insert/update details.

Inspect:

* `uploaded\\\_audio`
* `model`
* `algorithm`
* `engine`
* `job`
* `output\\\_paths`
* `inference\\\_result`
* `result`

Some thing you need to know :

> This class is the Facade. The FastAPI route does not know all the workflow details. It calls one service method, and the service coordinates the internal subsystems: model lookup, storage, factory selection, strategy execution, real NeoSSNet inference, result insertion, job status update, and logging.

How it matches the sequence workflow:

The route calls `separate\\\_uploaded\\\_audio`, then the Facade coordinates model selection, factory creation, strategy execution, database job update, result insert, and logging.

## 4\. Strategy Pattern Demo

Pattern name: Strategy Pattern

Files:

```text
app/ml/separation\\\_algorithm.py
app/ml/separation\\\_engine.py
app/ml/neossnet\\\_strategy.py
```

Classes/functions:

```text
SeparationAlgorithm
SeparationEngine
NeoSSNetStrategy
```

Strategy participants:

|Role|Project file/class|What to inspect|
|-|-|-|
|Client|`app/services/separation\\\_service.py`, `SeparationService`|The selected `algorithm` returned by the factory.|
|Context|`app/ml/separation\\\_engine.py`, `SeparationEngine`|`self.algorithm` and `type(self.algorithm)`.|
|Strategy interface|`app/ml/separation\\\_algorithm.py`, `SeparationAlgorithm`|The required `separate(...)` method signature.|
|Concrete strategy|`app/ml/neossnet\\\_strategy.py`, `NeoSSNetStrategy`|The real call to `run\\\_neossnet\\\_inference(...)`.|
|Future concrete strategy|Future class implementing `SeparationAlgorithm`|Explain that the route can stay unchanged.|

Breakpoints:

```text
app/ml/separation\\\_engine.py:21
app/ml/neossnet\\\_strategy.py:14
```

What it solves:

The separation workflow can run any algorithm that implements the same `separate(...)` interface. The route and service do not need to know the internal NeoSSNet implementation.

Inspect:

* `self.algorithm` inside `SeparationEngine`
* `type(self.algorithm)`
* `input\\\_wav\\\_path`
* `model\\\_path`
* `heart\\\_output\\\_path`
* `lung\\\_output\\\_path`

Some thing you need to know:

> `SeparationEngine` is the context. It calls the algorithm through the `SeparationAlgorithm` interface. Today the concrete strategy is `NeoSSNetStrategy`, but another model can be added later without changing the route.

How it matches the sequence workflow:

The Facade creates the engine with the selected strategy. The engine delegates to `NeoSSNetStrategy`, which calls the real NeoSSNet inference boundary.

## 5\. Factory Method Pattern Demo

Pattern name: Factory Method Pattern

File path:

```text
app/services/separation\\\_algorithm\\\_factory.py
```

Class/function:

```text
SeparationAlgorithmFactory.create\\\_algorithm
```

Factory Method participants:

|Role|Project file/class|What to inspect|
|-|-|-|
|Client|`app/services/separation\\\_service.py`, `SeparationService`|The selected `model` record before factory call.|
|Creator|`app/services/separation\\\_algorithm\\\_factory.py`, `SeparationAlgorithmFactory`|`\\\_registry` and `create\\\_algorithm(model)`.|
|Product interface|`app/ml/separation\\\_algorithm.py`, `SeparationAlgorithm`|The common object type expected by the engine.|
|Concrete product|`app/ml/neossnet\\\_strategy.py`, `NeoSSNetStrategy`|The returned object for `model.architecture = NeoSSNet`.|
|Selection data|SQLite `model` table|`model.architecture`, `checkpoint\\\_path`, `config\\\_path`.|

Breakpoint:

```text
app/services/separation\\\_algorithm\\\_factory.py:22
```

What it solves:

The separation service does not directly instantiate `NeoSSNetStrategy`. The factory reads the selected `model` row and creates the correct strategy based on `model.architecture`.

Inspect:

* `model.model\\\_id`
* `model.model\\\_name`
* `model.architecture`
* `cls.\\\_registry`
* `strategy\\\_class`
* returned strategy object

Some thing you need to know:

> This is the Factory Method part of the design. The database model record says which architecture is selected. The factory converts that record into the correct strategy object. This keeps object creation separate from the business workflow.

How it matches the sequence workflow:

`SeparationService` loads the model record, calls `SeparationAlgorithmFactory.create\\\_algorithm(model)`, receives a `SeparationAlgorithm`, then passes it to `SeparationEngine`.

## 6\. Upload Validation Factory Demo

The upload route also contains a small Factory Method structure for file validation.

Files:

```text
app/routers/upload.py
app/services/audio\\\_validation.py
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
app/services/audio\\\_validation.py:46
app/services/audio\\\_validation.py:22
```

Inspect:

* `file.filename`
* `suffix`
* returned `WavAudioValidator`
* `header`

Some thing you need to know;:

> The upload route asks a factory for the correct validator instead of directly creating the validator inside the route. For this prototype, only WAV is accepted.

## 7\. Database Update Breakpoints

Upload insert:

```text
app/routers/upload.py:50
app/routers/upload.py:52
```

Inspect:

* `audio\\\_record`
* `audio\\\_record.uploaded\\\_audio\\\_id`

Separation job insert:

```text
app/services/separation\\\_service.py:151
app/services/separation\\\_service.py:55
```

Inspect:

* `job.job\\\_id`
* `job.status`
* `job.started\\\_at`

Separation result insert:

```text
app/services/result\\\_service.py:116
app/services/separation\\\_service.py:169
```

Inspect:

* `result.job\\\_id`
* `result.heart\\\_file\\\_path`
* `result.lung\\\_file\\\_path`

Separation logs:

```text
app/services/separation\\\_service.py:57
app/services/separation\\\_service.py:177
```

Inspect:

* `event\\\_type`
* `message`
* `job\\\_id`

## 8\. API Response Breakpoints

Upload response:

```text
app/routers/upload.py
```

Place a breakpoint on the final `return` statement. Inspect:

* `audio\\\_record.uploaded\\\_audio\\\_id`
* `audio\\\_record.stored\\\_path`

Separation response:

```text
app/routers/separation.py
```

Place a breakpoint on the final `return` statement. Inspect:

* `result.job\\\_id`
* `result.status`
* `result.heart\\\_file\\\_path`
* `result.lung\\\_file\\\_path`

## 9\. Debugging Script To Follow During Demo

1. Start the debugger.
2. Open the web UI.
3. Upload `sample\\\_inputs/H0001.wav`.
4. Step through upload route, validator factory, validator, storage save, and database insert.
5. Continue until upload succeeds.
6. Run separation.
7. Step through separation route and `SeparationService`.
8. Stop at `SeparationAlgorithmFactory.create\\\_algorithm`.
9. Show that `model.architecture` is `NeoSSNet`.
10. Step into `SeparationEngine`.
11. Step into `NeoSSNetStrategy`.
12. Step into `run\\\_neossnet\\\_inference`.
13. Continue until output files are saved.
14. Step through result insert and completion log.
15. Open DBeaver and show the updated rows.

