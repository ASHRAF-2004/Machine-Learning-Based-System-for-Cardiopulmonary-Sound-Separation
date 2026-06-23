# Full Project Presentation Guide

This guide is for a full Software Design project demo. It is not a fixed timing plan. Each member should present from their own laptop and focus on clear evidence: working prototype, diagrams, code, and database records.

## Fair Member Distribution

Use this distribution so the live demo is balanced across separate laptops:

- Ashraf: project overview, problem statement, objectives, system architecture, and Facade Pattern debugging demo.
- Ahmad Akmal: working prototype, UI workflow, upload process, preview/download/history from the user side, and Factory Method debugging demo.
- Reshma: database, storage, requirements, SOLID principles, and DBeaver database update demo.
- Sharwin: UML diagrams, class/component design explanation, Strategy Pattern debugging demo, solution achieved, and future improvements.

Each design pattern is owned by a different member:

- Facade Pattern: Ashraf.
- Factory Method Pattern: Ahmad Akmal.
- Strategy Pattern: Sharwin.
- Database/SOLID proof: Reshma.

## 1. Project Problem

Mixed cardiopulmonary recordings contain both heart and lung sounds. If the sounds stay mixed, it is harder to preview or analyze the individual components. A machine learning model alone is not enough for a usable system, because the user still needs upload, validation, separation, output storage, preview, download, and history.

What to say:

> Our project solves a HealthTech software problem. The user uploads one mixed WAV recording, and the system separates it into heart sound and lung sound outputs. The focus is not clinical diagnosis. The focus is a working and maintainable software prototype around real audio separation.

## 2. Objectives

The main objectives are:

- Accept mixed cardiopulmonary WAV audio through a browser.
- Validate the uploaded file before saving.
- Run NeoSSNet-based separation.
- Save heart and lung output WAV files.
- Store upload metadata, job status, result paths, logs, and optional metrics in SQLite.
- Allow preview, download, and history viewing.
- Explain the system using UML, SOLID principles, and design patterns.

## 3. Scope

In scope:

- Local FastAPI prototype.
- HTML/CSS/JavaScript frontend.
- SQLite database.
- Local storage for uploads, outputs, logs, and model files.
- Real NeoSSNet inference path.
- Upload, separation, result, download, history, and model list workflow.

Out of scope:

- Clinical diagnosis.
- Hospital deployment.
- Authentication and role management.
- Training from runtime upload folders.
- Cloud production infrastructure.

## 4. User Workflow

Show the browser prototype and explain:

1. User selects a mixed WAV file.
2. User selects or keeps the active separation model.
3. User clicks `Run separation`.
4. Frontend uploads the file to `/upload`.
5. Backend validates and stores the file.
6. Frontend calls `/separate/{audio_id}`.
7. Backend runs separation and saves heart/lung outputs.
8. User previews or downloads the outputs.
9. History is recorded in SQLite and shown in the browser.

What to say:

> As you can see, the user flow is simple. The user only needs to choose a WAV file and run separation. Behind the screen, the backend validates the file, creates database records, runs the ML workflow, saves the outputs, and updates history.

## 5. Architecture

Use `docs/software_design_report/diagrams/img/overall_class_diagram.png`.

Explain the layers:

- UI layer: `app/templates/index.html` and `app/static/js/main.js`.
- API layer: FastAPI routers in `app/routers/`.
- Business logic layer: services in `app/services/`.
- ML layer: `app/ml/`.
- Database layer: SQLite models and schema.
- Storage layer: local folders under `storage/`.

What to say:

> The architecture separates the user interface, API routes, business services, ML logic, database records, and file storage. This makes the project easier to explain, debug, and extend.

## 6. Database

Use the ERD image and DBeaver query guide.

Important tables:

- `uploaded_audio`: uploaded WAV metadata.
- `model`: model name, version, architecture, checkpoint, config, active status.
- `separation_job`: one processing job per separation request.
- `separation_result`: heart and lung output paths.
- `evaluation_metric`: optional output metrics.
- `system_log`: important processing events and errors.

What to say:

> SQLite stores metadata and history, not large WAV blobs. The actual audio files stay in local folders. This keeps the database lightweight and makes history easy to inspect in DBeaver.

## 7. Design Patterns

Use only the final clean mapping below.

### Facade Pattern

Presenter: Ashraf.

- Client: `SeparationRouter`
- Facade: `SeparationService`
- Subsystems: `ModelService`, `StorageService`, `ResultService`

What to say:

> Now I will show the Facade Pattern. The router does not manage the full workflow. It calls one high-level method in `SeparationService`. As you can see when I step through the breakpoint, the Facade hides model lookup, file path handling, result creation, and job status updates behind subsystem calls.

### Factory Method Pattern

Presenter: Ahmad Akmal.

- Client: `UploadRouter`
- Creator: `AudioValidatorFactory`
- ConcreteCreator: `WavAudioValidatorFactory`
- Product: `AudioValidator`
- ConcreteProduct: `WavAudioValidator`

What to say:

> Now I will show the Factory Method Pattern during upload validation. As you can see, the upload route does not directly create the WAV validator. It asks a factory for a validator. This keeps validation object creation separate from route logic.

### Strategy Pattern

Presenter: Sharwin.

- Context: `SeparationEngine`
- Strategy: `SeparationAlgorithm`
- ConcreteStrategy: `NeoSSNetStrategy`

What to say:

> Now I will show the Strategy Pattern. `SeparationEngine` runs the algorithm through the `SeparationAlgorithm` interface. As you can see when I step into the call, the current concrete strategy is `NeoSSNetStrategy`, so the engine does not depend directly on NeoSSNet internals.

## 8. SOLID Principles

Presenter: Reshma.

Explain briefly:

- SRP: routers, services, storage, model lookup, result logic, and ML strategy have separate responsibilities.
- OCP: new validators or algorithms can be added with less change to existing workflow.
- LSP: `NeoSSNetStrategy` can be used wherever `SeparationAlgorithm` is expected.
- ISP: small focused interfaces such as `AudioValidator` and `SeparationAlgorithm`.
- DIP: `SeparationEngine` depends on `SeparationAlgorithm`, not a concrete NeoSSNet class.

## 9. Working Prototype Evidence

Show:

- Browser upload panel.
- Model dropdown.
- Result preview panel.
- Download buttons.
- History list.
- DBeaver latest database row after separation.

What to say:

> The prototype is working because we can start from a mixed WAV file, run the separation workflow, see output paths and history, and inspect the database records created by the process.

## 10. Solution Achieved

The project achieved:

- A usable local FastAPI web application.
- Real backend workflow for upload, validation, separation, result, and history.
- SQLite persistence for traceability.
- Local file storage for uploaded and separated audio.
- UML and design pattern documentation.
- A maintainable structure suitable for future models or validators.

## 11. Future Improvements

Good future improvements:

- Better progress indicators for long inference.
- More evaluation metrics and reports.
- More real separation algorithms added through Strategy.
- Better usability testing.
- Background processing for long audio files.
- Broader dataset testing before any clinical claim.

## 12. What To Avoid

- Do not claim the system is clinically validated.
- Do not spend too long explaining NeoSSNet internal ML code.
- Do not show unrelated files.
- Do not mix roles between the three patterns.
- Do not use compatibility/helper names as the main Factory Method explanation.
- Use only the final mapping shown in this guide.
