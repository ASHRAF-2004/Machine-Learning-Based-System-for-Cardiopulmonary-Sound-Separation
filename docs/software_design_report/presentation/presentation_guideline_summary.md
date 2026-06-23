# Presentation Guideline Summary

Source inspected:
- `docs/CW Project 2530 - CSE 6234 SDv5.pdf`
- `docs/software_design_report/main.pdf`
- `docs/software_design_report/main.tex`
- `docs/software_design_report/chapters/*.tex`

## What The Presentation Must Cover

The guideline asks the group to present a working software prototype and explain the software design behind it. For this project, the presentation should cover:

- System objectives: upload mixed cardiopulmonary WAV audio, run separation, save heart/lung outputs, and keep database history.
- System scope: local FastAPI web prototype, SQLite metadata, local file storage, NeoSSNet-based separation, browser preview, download, and history.
- System overview: UI layer, FastAPI routers, service layer, ML layer, SQLite layer, and storage folders.
- Component/class design: routers, services, ML classes, database models, and how responsibilities are separated.
- Software architecture: browser UI -> FastAPI routes -> services -> ML engine/strategy -> SQLite and storage.
- Input and output: input is a mixed WAV file; outputs are separated heart and lung WAV files plus database records.
- Solution achieved: the prototype demonstrates upload, validation, separation, preview/download, and processing history.
- Work segregation: each member should explain a real part of the project and one value-added contribution.
- Self-reflection report: each member should briefly state contribution, challenge, and improvement area.

## Rubric Focus

The rubric rewards:

- Working prototype and functionality.
- User interface design and usability.
- Correct use of software design patterns.
- Component-level design and software architecture.
- Clear documentation and presentation.
- Team collaboration and fair work distribution.
- Individual contribution, initiative, responsibility, and communication.

## Timing Note

The guideline mentions recorded/live timing requirements, including group presentation timing. The lecturer has clarified that the group does not need to follow the stated timing strictly. Use the timing requirement only as context. The presentation should be clear, complete, and practical rather than forced into an exact duration.

## Recommended Evidence To Show

- Working web prototype at `/`.
- Swagger/API endpoints if needed: `/upload`, `/separate/{audio_id}`, `/result/{job_id}`, `/history`, `/models`.
- SQLite database file: `database/cardiopulmonary.db`.
- Diagrams:
  - `docs/software_design_report/diagrams/img/use_case_diagram.png`
  - `docs/software_design_report/diagrams/img/overall_class_diagram.png`
  - `docs/software_design_report/diagrams/img/erd.png`
  - `docs/software_design_report/diagrams/img/object_diagram.png`
  - `docs/software_design_report/diagrams/img/facade_project.png`
  - `docs/software_design_report/diagrams/img/strategy_project.png`
  - `docs/software_design_report/diagrams/img/factory_method_project.png`
- Backend code breakpoints for Facade, Factory Method, and Strategy.

