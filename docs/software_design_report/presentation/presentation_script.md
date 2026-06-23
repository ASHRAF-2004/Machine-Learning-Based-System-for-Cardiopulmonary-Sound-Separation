# Full Speaking Script

Total target time: about 10 minutes. Keep the pace steady and avoid reading every bullet word-for-word.

## Slide 1 - Title And Team Introduction (Ashraf, 30 seconds)

Good day everyone. We are Group 1 from tutorial section TT5L. Our project is titled Machine Learning-Based System for Cardiopulmonary Sound Separation. It is a HealthTech software design prototype. The system accepts a mixed cardiopulmonary WAV recording and separates it into heart sound and lung sound outputs. In this presentation, we will explain the problem, system scope, architecture, component design, design patterns, prototype workflow, work segregation, and our individual self-reflections.

## Slide 2 - Problem And System Objectives (Ashraf, 55 seconds)

The problem is that cardiopulmonary recordings often contain overlapping heart and lung sounds. If we only have a mixed recording, it is difficult to preview the heart and lung components separately. Also, a machine learning script alone is not enough for a usable system. A user still needs upload, validation, storage, result preview, download, and history.

Our main objective is to build a local web-based prototype that accepts mixed WAV audio and produces separated heart and lung WAV outputs using NeoSSNet. From the software design side, our objective is to show a maintainable architecture using FastAPI, SQLite, local file storage, SOLID principles, and design patterns.

## Slide 3 - System Scope And Main Features (Ahmad Akmal, 55 seconds)

The system scope is focused on a local prototype for demonstration. The main features are upload, validation, separation, preview, download, and history. The user uploads a WAV file, the backend validates it, and then the system runs NeoSSNet to generate separated heart and lung outputs.

The web interface also supports browser audio playback, so the user can preview the original and separated files. The history feature allows previous jobs to be reviewed. The system is not a medical diagnosis tool and does not claim clinical validation. It is designed as a software design prototype for demonstrating the workflow clearly.

## Slide 4 - Software Architecture (Reshma, 55 seconds)

The architecture is layered so that each part has a clear responsibility. The UI layer uses HTML, CSS, and JavaScript templates for upload, preview, and history. The API layer uses FastAPI routers to receive upload and separation requests.

The business logic layer contains services such as SeparationService, ModelService, StorageService, and ResultService. The ML layer contains SeparationEngine and NeoSSNetStrategy for real inference. Finally, SQLite stores structured records such as uploads, jobs, results, and logs, while local folders store the actual audio files and model files. This separation keeps the system easier to understand and maintain.

## Slide 5 - Component-Level Design (Sharwin, 55 seconds)

This slide shows the main components behind the system. The FastAPI routers handle HTTP requests, but they do not contain all the business logic. The SeparationService coordinates the separation workflow. It works with ModelService for model lookup, StorageService for file paths and folders, and ResultService for output records and history.

The ML side is separated into SeparationEngine and NeoSSNetStrategy. The database models store uploaded audio, model records, separation jobs, results, metrics, and logs. This component-level design supports separation of concerns and makes the system easier to test and explain.

## Slide 6 - Design Patterns Applied (Ashraf and Sharwin, 1 minute 20 seconds)

Ashraf: We selected three design patterns. First is the Facade Pattern. The client is SeparationRouter, the facade is SeparationService, and the subsystems are ModelService, StorageService, and ResultService. This means the route can call one service method instead of controlling every internal step.

Sharwin: Second is the Strategy Pattern. The context is SeparationEngine, the strategy interface is SeparationAlgorithm, and the concrete strategy is NeoSSNetStrategy. This allows the engine to run separation through a common interface.

Ashraf: Third is the Factory Method Pattern for upload validation. The client is UploadRouter, the creator is AudioValidatorFactory, the concrete creator is WavAudioValidatorFactory, the product is AudioValidator, and the concrete product is WavAudioValidator. This keeps validator creation separate from upload route logic.

## Slide 7 - Prototype Workflow: Input To Output (Ahmad Akmal, 55 seconds)

The prototype workflow starts when the user uploads a mixed WAV audio file. The system validates the file type and WAV header. The user can use the selected or default model, then the backend runs separation.

After processing, the system saves two output files: one heart sound WAV and one lung sound WAV. The user can preview or download both outputs. At the same time, SQLite stores the upload record, job status, result paths, and logs. This creates a traceable workflow from input to output.

## Slide 8 - Solution Achieved And Future Work (Reshma, 55 seconds)

The solution achieved is a working local FastAPI prototype with real NeoSSNet separation. The web app supports upload, preview, download, and history. SQLite provides traceability for uploads, jobs, results, and logs.

For future work, the UI can be improved with clearer progress indicators and more usability testing. The system can also add more evaluation metrics such as SNR or SDR, support broader datasets and recording conditions, and use background processing for longer audio files. More separation models can also be added later through the strategy structure.

## Slide 9 - Work Segregation (Sharwin, 50 seconds)

This slide summarizes our work segregation. Ashraf focused on overall design coordination, backend alignment, and design pattern consistency. Ahmad Akmal focused on UI and prototype flow, especially upload, result, and history usability. Reshma focused on database, storage, requirements, and SOLID documentation. I focused on diagrams, architecture, component-level design, and design pattern explanation.

The value-added part is that we connected the prototype, database, UML diagrams, and report into one consistent software design story.

## Slide 10 - Individual Self-Reflection (All members, 1 minute 45 seconds)

Ashraf: My contribution was design coordination and aligning the backend, UML diagrams, and report. My challenge was making the code, diagrams, and explanation consistent. My improvement area is to add more automated testing and deployment preparation.

Ahmad Akmal: My contribution was the UI and prototype flow for upload, results, and history. My challenge was keeping the interface simple for users. My improvement area is to run more usability testing with different users.

Reshma: My contribution was database, storage, and requirements documentation. My challenge was organizing history and result records clearly. My improvement area is to add more detailed metrics and reporting.

Sharwin: My contribution was diagrams, architecture, and component design explanation. My challenge was keeping diagrams clean and consistent. My improvement area is to support more future models and validators.

Closing: Overall, our prototype demonstrates a working HealthTech workflow and the design explains how the system can be maintained and extended.
