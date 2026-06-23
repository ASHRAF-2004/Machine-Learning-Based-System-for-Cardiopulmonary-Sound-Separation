# Design Pattern Debugging Demo

This guide shows the implemented design patterns using current backend line numbers. Use it as a practical demo script, not as a strict timing plan.

## Fair Demo Ownership

- Ashraf presents the Facade Pattern debugging demo.
- Ahmad Akmal presents the Factory Method Pattern debugging demo.
- Reshma presents the database/SOLID demonstration using DBeaver.
- Sharwin presents the Strategy Pattern debugging demo.

Do not let one member present all design pattern breakpoints. Each member should only show the part assigned above.

## Final Pattern Mapping

Facade Pattern:

- Client: `SeparationRouter`
- Facade: `SeparationService`
- Subsystems: `ModelService`, `StorageService`, `ResultService`

Factory Method Pattern:

- Client: `UploadRouter`
- Creator: `AudioValidatorFactory`
- ConcreteCreator: `WavAudioValidatorFactory`
- Product: `AudioValidator`
- ConcreteProduct: `WavAudioValidator`

Strategy Pattern:

- Context: `SeparationEngine`
- Strategy: `SeparationAlgorithm`
- ConcreteStrategy: `NeoSSNetStrategy`

## Breakpoint Summary

| Pattern | File | Line | Function / Statement | Pattern Role | Trigger | What This Proves |
|---|---:|---:|---|---|---|---|
| Facade | `app/routers/separation.py` | 31 | `result = separate_uploaded_audio(db, audio_id, model_id=model_id)` | Client calls Facade | Click `Run separation` after selecting a WAV file | Router delegates workflow instead of managing it directly. |
| Facade | `app/services/separation_service.py` | 129 | `def separate_uploaded_audio(...)` | Facade method start | Continue from router | Workflow enters the Facade. |
| Facade | `app/services/separation_service.py` | 135 | `uploaded_audio = get_uploaded_audio(db, audio_id)` | Facade retrieves upload record | Continue inside Facade | Facade owns workflow coordination. |
| Facade | `app/services/separation_service.py` | 136 | `model = model_service.get_model_for_separation(db, model_id)` | Calls `ModelService` subsystem | Step over/into | Model lookup is hidden behind service logic. |
| Facade | `app/services/separation_service.py` | 140 | `input_path = storage_service.resolve_project_path(...)` | Calls `StorageService` subsystem | Step over/into | File path handling is delegated. |
| Facade | `app/services/separation_service.py` | 156 | `output_paths = storage_service.build_separation_output_paths(job.job_id)` | Calls `StorageService` subsystem | Continue inside Facade | Output path creation is delegated. |
| Facade | `app/services/separation_service.py` | 169 | `result = result_service.create_separation_result(...)` | Calls `ResultService` subsystem | Continue after inference | Result/history creation is delegated. |
| Facade | `app/services/separation_service.py` | 201 | `mark_job_failed(db, job, error, processing_time_ms)` | Error handling path | Trigger only if inference fails | Failed jobs are recorded instead of silently disappearing. |
| Factory Method | `app/routers/upload.py` | 28 | `validator = audio_validator_factory.create_validator(file.filename)` | Client asks Creator | Select WAV and click `Run separation`; upload runs first | Upload route does not directly create the validator. |
| Factory Method | `app/services/audio_validation.py` | 39 | `def create_validator(self, filename: str | None) -> AudioValidator:` | Creator method contract | Open as reference line | The route uses the product abstraction. Runtime stepping normally enters the concrete creator at line 46. |
| Factory Method | `app/services/audio_validation.py` | 46 | `def create_validator(self, filename: str | None) -> AudioValidator:` | ConcreteCreator method | Continue/step in | WAV-specific creator handles creation. |
| Factory Method | `app/services/audio_validation.py` | 49 | `return WavAudioValidator()` | ConcreteProduct creation | Step over line 49 | Factory returns the concrete validator. |
| Factory Method | `app/services/audio_validation.py` | 22 | `async def validate(self, upload_file: UploadFile) -> None:` | ConcreteProduct behavior | Continue after creation | The returned validator performs WAV validation. |
| Strategy | `app/services/separation_service.py` | 137 | `algorithm = create_algorithm_from_factory(self.algorithm_factory, model)` | Strategy object prepared | Click `Run separation` and continue | Inspect `algorithm`; expected object is `NeoSSNetStrategy`. |
| Strategy | `app/ml/separation_engine.py` | 21 | `def separate(...)` | Context method start | Continue to engine | Execution reaches the Strategy Context. |
| Strategy | `app/ml/separation_engine.py` | 29 | `return self.algorithm.separate(...)` | Context calls Strategy | Step into line 29 | Engine calls through the algorithm abstraction. |
| Strategy | `app/ml/separation_algorithm.py` | 22 | `class SeparationAlgorithm(Protocol):` | Strategy interface | Open file for explanation | The interface defines the expected `separate(...)` operation. |
| Strategy | `app/ml/neossnet_strategy.py` | 14 | `def separate(...)` | ConcreteStrategy | Step into algorithm call | Actual runtime strategy is NeoSSNet. |

## Ashraf - Facade Pattern Demo

Goal: show that `SeparationService` is the Facade and that it calls subsystem services.

### Breakpoints To Set

1. `app/routers/separation.py`, line 31  
   Function: `separate_audio`  
   Statement: `result = separate_uploaded_audio(db, audio_id, model_id=model_id)`  
   Role: Client calling Facade.

2. `app/services/separation_service.py`, line 129  
   Function: `SeparationService.separate_uploaded_audio`  
   Statement: `def separate_uploaded_audio(...)`  
   Role: Facade method.

3. `app/services/separation_service.py`, line 135  
   Function: `SeparationService.separate_uploaded_audio`  
   Statement: `uploaded_audio = get_uploaded_audio(db, audio_id)`  
   Role: Facade starts upload/audio lookup.

4. `app/services/separation_service.py`, line 136  
   Function: `SeparationService.separate_uploaded_audio`  
   Statement: `model = model_service.get_model_for_separation(db, model_id)`  
   Role: Facade calls `ModelService`.

5. `app/services/separation_service.py`, line 140  
   Function: `SeparationService.separate_uploaded_audio`  
   Statement: `input_path = storage_service.resolve_project_path(uploaded_audio.stored_path)`  
   Role: Facade calls `StorageService` for stored file path.

6. `app/services/separation_service.py`, line 156  
   Function: `SeparationService.separate_uploaded_audio`  
   Statement: `output_paths = storage_service.build_separation_output_paths(job.job_id)`  
   Role: Facade calls `StorageService` for output file paths.

7. `app/services/separation_service.py`, line 169  
   Function: `SeparationService.separate_uploaded_audio`  
   Statement: `result = result_service.create_separation_result(...)`  
   Role: Facade calls `ResultService`.

8. `app/services/separation_service.py`, line 201  
   Function: `SeparationService.separate_uploaded_audio`  
   Statement: `mark_job_failed(db, job, error, processing_time_ms)`  
   Role: Facade error handling path.

### Trigger

Select a WAV file in the web page and click `Run separation`. The frontend uploads first, then sends the separation request.

### What To Say

> Now I will show the Facade Pattern using breakpoints.
>
> As you can see, the first breakpoint stops in `SeparationRouter`. This is the client. The router does not manage the full separation workflow directly.
>
> It calls one high-level method in `SeparationService`. Now the debugger stops inside `SeparationService`. This class is the Facade because it hides the subsystem details behind one simple method.
>
> When I step forward, we can see the Facade calling upload lookup, `ModelService`, `StorageService`, and `ResultService`. These subsystem services do the detailed work.
>
> This proves the Facade Pattern is working in the actual code, not only in the diagram.

### Expected Result

- Breakpoint stops at `app/routers/separation.py:31`.
- Step into or continue to `app/services/separation_service.py:129`.
- Step through lines 135, 136, 140, 156, and 169.
- If ML inference fails locally, line 201 may run and mark the job as failed.

## Ahmad Akmal - Factory Method Pattern Demo

Goal: show that upload validation object creation is separated from the upload route.

### Breakpoints To Set

1. `app/routers/upload.py`, line 28  
   Function: `upload_audio`  
   Statement: `validator = audio_validator_factory.create_validator(file.filename)`  
   Role: Client asks Creator for a Product.

2. `app/services/audio_validation.py`, line 39  
   Function: `AudioValidatorFactory.create_validator`  
   Statement: `def create_validator(self, filename: str | None) -> AudioValidator:`  
   Role: Creator method contract. This is a reference line to show the abstraction; the debugger normally steps into the concrete creator at line 46.

3. `app/services/audio_validation.py`, line 46  
   Function: `WavAudioValidatorFactory.create_validator`  
   Statement: `def create_validator(self, filename: str | None) -> AudioValidator:`  
   Role: ConcreteCreator method.

4. `app/services/audio_validation.py`, line 49  
   Function: `WavAudioValidatorFactory.create_validator`  
   Statement: `return WavAudioValidator()`  
   Role: ConcreteCreator creates ConcreteProduct.

5. `app/services/audio_validation.py`, line 22  
   Function: `WavAudioValidator.validate`  
   Statement: `async def validate(self, upload_file: UploadFile) -> None:`  
   Role: ConcreteProduct validates the file.

### Trigger

Select a WAV file and click `Run separation` in the web page. Upload validation is the first backend action. If using Swagger, execute `POST /upload`.

### What To Say

> Now I will show the Factory Method Pattern using upload validation.
>
> As you can see, the breakpoint stops in `UploadRouter`. This route is the client. It does not directly create `WavAudioValidator`.
>
> Instead, it asks `AudioValidatorFactory` for a validator. When I step into the call, execution enters `WavAudioValidatorFactory`.
>
> At line 49, the concrete creator returns `WavAudioValidator`. Then the returned validator runs `validate(...)`.
>
> This keeps validator creation separate from route logic, so another validator can be added later with less impact on the upload route.

### Expected Result

- Breakpoint stops at `app/routers/upload.py:28`.
- Step into factory creation in `app/services/audio_validation.py`.
- Runtime validator object should be `WavAudioValidator`.
- Validation passes for a real WAV file or returns a clear error for invalid input.

## Sharwin - Strategy Pattern Demo

Goal: show that `SeparationEngine` runs the algorithm through the `SeparationAlgorithm` abstraction.

### Breakpoints To Set

1. `app/services/separation_service.py`, line 137  
   Function: `SeparationService.separate_uploaded_audio`  
   Statement: `algorithm = create_algorithm_from_factory(self.algorithm_factory, model)`  
   Role: supporting point to inspect selected algorithm object.

2. `app/ml/separation_engine.py`, line 21  
   Function: `SeparationEngine.separate`  
   Statement: `def separate(...)`  
   Role: Strategy Context method start.

3. `app/ml/separation_engine.py`, line 29  
   Function: `SeparationEngine.separate`  
   Statement: `return self.algorithm.separate(...)`  
   Role: Context calls Strategy interface.

4. `app/ml/separation_algorithm.py`, line 22  
   Function/class: `SeparationAlgorithm`  
   Statement: `class SeparationAlgorithm(Protocol):`  
   Role: Strategy interface.

5. `app/ml/neossnet_strategy.py`, line 14  
   Function: `NeoSSNetStrategy.separate`  
   Statement: `def separate(...)`  
   Role: ConcreteStrategy.

### Trigger

Click `Run separation` and continue until the separation workflow reaches the ML engine.

### What To Say

> Now I will show the Strategy Pattern.
>
> As you can see, the algorithm object is prepared before the engine runs. I can inspect `algorithm`, and the current runtime object is `NeoSSNetStrategy`.
>
> Now execution reaches `SeparationEngine`. This is the Strategy Context. At line 29, the engine calls `self.algorithm.separate(...)`.
>
> When I step into that call, it enters `NeoSSNetStrategy.separate`. This is the ConcreteStrategy.
>
> This proves that the engine depends on the `SeparationAlgorithm` abstraction instead of depending directly on NeoSSNet internals.

### Expected Result

- At `app/services/separation_service.py:137`, inspect `algorithm` after the line executes.
- Expected type: `NeoSSNetStrategy`.
- At `app/ml/separation_engine.py:29`, step into the call.
- The debugger should enter `app/ml/neossnet_strategy.py:14`.

## What To Avoid During Debugging

- Do not step deep into NeoSSNet internal model code.
- Do not explain every database line during the pattern demo.
- Do not debug frontend CSS or HTML.
- Do not show unrelated files.
- Do not mix roles between the three patterns.
- Do not use compatibility/helper names as the main Factory Method explanation.
- Use only the final mapping shown at the top of this guide.
