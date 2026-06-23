# Member Speaking Guide

This is a fair suggested presentation distribution because the repository does not prove exact individual contribution history. Each member should adjust the wording if their real contribution differs.

No strict timing is required. Each member should present from their own laptop and show the strongest evidence for their own section.

## Fair Presentation Order

1. Ashraf: project overview, problem, objectives, architecture, and Facade Pattern debugging.
2. Ahmad Akmal: working prototype, UI workflow, upload flow, preview/download/history, and Factory Method debugging.
3. Reshma: database, storage, requirements, SOLID principles, and DBeaver database update demo.
4. Sharwin: UML diagrams, class/component design, Strategy Pattern debugging, solution achieved, and future improvements.

## Member 1 - Ashraf

### Part To Present

- Project overview.
- Problem statement.
- Objectives.
- System architecture.
- Facade Pattern debugging demo.

### Why This Fits

Ashraf's section introduces the full project and then proves the main backend workflow through the Facade Pattern. This is fair because Ashraf owns one design pattern demo, not all pattern demos.

### Open Before Presenting

- `docs/software_design_report/main.pdf`, introduction/objectives section.
- `docs/software_design_report/diagrams/img/overall_class_diagram.png`
- `docs/software_design_report/diagrams/img/facade_project.png`
- Browser at the running web app: `http://127.0.0.1:8000/`
- VS Code files:
  - `app/routers/separation.py`
  - `app/services/separation_service.py`
  - `app/services/model_service.py`
  - `app/services/storage_service.py`
  - `app/services/result_service.py`

### What To Show

- Project title and problem/objectives.
- Overall architecture/class diagram.
- Facade diagram.
- Breakpoints:
  - `app/routers/separation.py:31`
  - `app/services/separation_service.py:135`
  - `app/services/separation_service.py:136`
  - `app/services/separation_service.py:140`
  - `app/services/separation_service.py:156`
  - `app/services/separation_service.py:169`

### Short Script

> Now I will introduce our project. The title is Machine Learning-Based System for Cardiopulmonary Sound Separation. The problem is that a mixed chest sound contains both heart and lung components, so the user needs a system that can separate and review them clearly.
>
> As you can see, our project is a local FastAPI web prototype. The user uploads a mixed WAV file, the backend validates it, runs separation, saves heart and lung output files, and stores history in SQLite.
>
> Now I will show the Facade Pattern. The client is `SeparationRouter`, and the Facade is `SeparationService`. I click `Run separation`, and the breakpoint stops in the router. The router does not manage the full separation workflow. It calls one high-level method.
>
> As you can see, when I step into `SeparationService`, it calls subsystem services such as `ModelService`, `StorageService`, and `ResultService`. This proves the Facade hides the subsystem workflow behind one simple interface.

### Self-Reflection Lines

> My contribution was coordinating the project overview, objectives, architecture, and Facade design explanation. One challenge was aligning the backend workflow with the UML and report explanation. My improvement area is adding more automated tests and smoother deployment instructions.

### What Not To Say

- Do not claim clinical diagnosis.
- Do not explain every class in the class diagram.
- Do not take over Factory Method or Strategy debugging.
- Do not spend time on environment setup unless asked.

## Member 2 - Ahmad Akmal

### Part To Present

- Working prototype.
- UI workflow.
- Upload process.
- Preview/download/history from the user side.
- Factory Method debugging demo.

### Why This Fits

Ahmad's section starts from what the user sees, then proves the upload validation design using Factory Method. This connects UI action to backend validation clearly.

### Open Before Presenting

- Browser at `http://127.0.0.1:8000/`
- A ready WAV file for upload.
- `app/templates/index.html`
- `app/static/js/main.js`
- VS Code files:
  - `app/routers/upload.py`
  - `app/services/audio_validation.py`

### What To Show

- Upload mixed WAV section.
- Model dropdown.
- `Run separation` button.
- Status message.
- Result preview section.
- Heart/lung download buttons.
- History section.
- Factory Method breakpoints:
  - `app/routers/upload.py:28`
  - `app/services/audio_validation.py:46`
  - `app/services/audio_validation.py:49`
  - `app/services/audio_validation.py:22`

### Short Script

> Now I will show the prototype from the user side. As you can see, the page has one main workflow: upload a mixed WAV file, choose a model, and click `Run separation`.
>
> When I click the button, the frontend first uploads the file to the backend, then it calls the separation endpoint. After processing, the page displays the separated heart and lung audio. The user can preview the audio in the browser, download the outputs, and check previous jobs in history.
>
> Now I will show the Factory Method Pattern during upload validation. The breakpoint stops in `UploadRouter` at line 28. This route is the client. It does not directly create `WavAudioValidator`.
>
> As you can see, it asks `AudioValidatorFactory` for a validator. When I step into it, execution reaches `WavAudioValidatorFactory`, and line 49 returns `WavAudioValidator`. This proves object creation is separated from the upload route.

### Self-Reflection Lines

> My contribution was explaining the working prototype and user workflow, especially upload, result preview, download, history, and Factory Method upload validation. One challenge was keeping the interface simple while still showing enough technical information. My improvement area is more usability testing and clearer progress feedback.

### What Not To Say

- Do not spend time explaining CSS details.
- Do not debug frontend layout unless asked.
- Do not take over Facade or Strategy debugging.
- Do not wait too long if ML inference is slow.

## Member 3 - Reshma

### Part To Present

- Database.
- Storage.
- Requirements.
- SOLID principles.
- Database update demo using the DBeaver query.

### Why This Fits

Reshma's section proves that the system stores traceable history and follows separation of concerns. This is an important non-pattern demo and balances the pattern demos owned by other members.

### Open Before Presenting

- DBeaver connected to `database/cardiopulmonary.db`.
- SQL editor with the query from `database_demo_guide.md`.
- `docs/software_design_report/diagrams/img/erd.png`
- `database/schema.sql`
- Optional report section: `docs/software_design_report/chapters/03_requirements.tex`

### What To Show

- ERD image.
- Tables: `uploaded_audio`, `model`, `separation_job`, `separation_result`, `evaluation_metric`, `system_log`.
- DBeaver latest joined query result after a separation.
- `database/schema.sql` lines 3-16, 32-68, and 87-102 if code evidence is needed.

### Short Script

> Now I will show the database, storage, requirements, and SOLID part. As you can see in the ERD, SQLite stores metadata and processing history. The large WAV files are not stored inside SQLite. Instead, SQLite stores file paths, and the actual audio files are kept in local storage folders.
>
> Now I will run the prepared DBeaver query. This query joins the uploaded audio, separation job, and separation result tables. As you can see, the latest row shows the job ID, audio ID, uploaded filename, status, heart and lung output paths, timestamps, and processing time.
>
> This proves that the prototype has a working database layer and processing history. It also supports SOLID because responsibilities are separated: storage handles files, database tables handle metadata, and service classes coordinate the workflow.

### Self-Reflection Lines

> My contribution was explaining the database structure, storage separation, requirements, SOLID principles, and DBeaver database proof. One challenge was keeping upload, job, result, metric, and log records traceable. My improvement area is adding clearer metric reports and stronger result validation.

### What Not To Say

- Do not explain every column unless asked.
- Do not open unrelated runtime folders.
- Do not say audio is stored in SQLite.
- Do not take over the design pattern debugging demos.

## Member 4 - Sharwin

### Part To Present

- UML diagrams.
- Class diagram.
- Component/design explanation.
- Strategy Pattern debugging demo.
- Solution achieved and future improvements.

### Why This Fits

Sharwin's section explains the design diagrams and owns only the Strategy Pattern debugging demo. This keeps the pattern workload fair while still giving Sharwin a strong design-focused section.

### Open Before Presenting

- `docs/software_design_report/diagrams/img/use_case_diagram.png`
- `docs/software_design_report/diagrams/img/overall_class_diagram.png`
- `docs/software_design_report/diagrams/img/strategy_project.png`
- VS Code files:
  - `app/services/separation_service.py`
  - `app/ml/separation_engine.py`
  - `app/ml/separation_algorithm.py`
  - `app/ml/neossnet_strategy.py`
- Browser ready to click `Run separation`.

### What To Show

- Use case diagram.
- Overall class diagram.
- Strategy Pattern diagram.
- Strategy breakpoints:
  - `app/services/separation_service.py:137`
  - `app/ml/separation_engine.py:21`
  - `app/ml/separation_engine.py:29`
  - `app/ml/neossnet_strategy.py:14`
- Future improvements section from the report if needed.

### Short Script

> Now I will show the UML and component design. The use case diagram shows the user's main actions: upload, run separation, preview, download, and view history. The class diagram shows how the system separates routers, services, database models, storage, and ML classes.
>
> Now I will show the Strategy Pattern. The context is `SeparationEngine`, the strategy interface is `SeparationAlgorithm`, and the concrete strategy is `NeoSSNetStrategy`.
>
> As you can see, the algorithm object is prepared before the engine runs. When execution reaches `SeparationEngine`, line 29 calls `self.algorithm.separate(...)`. When I step into it, the runtime object is `NeoSSNetStrategy`. This proves the engine calls the algorithm through the abstraction instead of depending directly on NeoSSNet internals.
>
> The solution achieved is a working FastAPI prototype with upload, real separation workflow, output files, database history, and maintainable design. Future improvements include better progress feedback, more metrics, background processing, and more algorithms added through the Strategy structure.

### Self-Reflection Lines

> My contribution was explaining the UML diagrams, component design, Strategy Pattern, solution achieved, and future improvements. One challenge was keeping diagrams readable while still matching the implementation. My improvement area is updating diagrams and strategy support when more algorithms are added.

### What Not To Say

- Do not mention old or confusing pattern mappings.
- Do not mix roles between the three patterns.
- Do not take over Facade or Factory Method debugging.
- Do not step deep into NeoSSNet internals.
