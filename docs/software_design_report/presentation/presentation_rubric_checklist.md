# Presentation Rubric Checklist

Source: `docs/CW Project 2530 - CSE 6234 SDv5.pdf`

| Rubric / Guideline Requirement | Covered In Slide(s) | Evidence In Deck |
| --- | --- | --- |
| Working prototype | 3, 7, 8 | Upload, validation, separation, preview, download, history workflow. |
| Functionality | 3, 7 | Main end-to-end features are shown from mixed WAV input to heart/lung outputs. |
| UI design | 3, 7 | Browser upload, preview, download, and history are explained. |
| Business logic layer | 4, 5 | Service layer and SeparationService are shown. |
| Database layer | 4, 5, 7 | SQLite stores uploads, jobs, results, logs, and history. |
| Software architecture | 4 | Layered architecture: UI, API, service, ML, database/storage. |
| Component-level design | 5 | Routers, services, ML components, and SQLite models are mapped. |
| Software design patterns | 6 | Facade, Strategy, and Factory Method are mapped to project classes. |
| Documentation/design choices | 2, 4, 5, 8 | Design objectives, layered decisions, and future improvements are explained. |
| Input and output | 7 | Mixed WAV input; separated heart/lung WAV output; SQLite history. |
| Solution achieved? | 8 | Working local FastAPI prototype with real NeoSSNet separation and traceability. |
| Work segregation | 9 | Member roles and value-added contributions are listed. |
| Individual contribution | 10 | Each member states contribution, challenge, and improvement. |
| Presentation clarity | All slides | Minimal text, readable layout, simple diagrams, 10-minute timing plan. |
| Team collaboration | 9, 10 | Clear role distribution and individual reflection. |

## Design Pattern Mapping Used In Slides

| Pattern | Mapping |
| --- | --- |
| Facade | Client: `SeparationRouter`; Facade: `SeparationService`; Subsystems: `ModelService`, `StorageService`, `ResultService`. |
| Strategy | Context: `SeparationEngine`; Strategy: `SeparationAlgorithm`; ConcreteStrategy: `NeoSSNetStrategy`. |
| Factory Method | Client: `UploadRouter`; Creator: `AudioValidatorFactory`; ConcreteCreator: `WavAudioValidatorFactory`; Product: `AudioValidator`; ConcreteProduct: `WavAudioValidator`. |

## Final Review

- 10 slides are included.
- Total timing fits about 10 minutes.
- Each member has a speaking part.
- Slides avoid paragraphs and use short phrases.
- No clinical validation claim is made.
- The presentation focuses on important rubric items only.
