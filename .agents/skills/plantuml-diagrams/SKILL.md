---
name: plantuml-diagrams
description: Use when creating, editing, validating, or rendering PlantUML diagrams such as use case diagrams, class diagrams, ERD, object diagrams, sequence diagrams, architecture diagrams, and design pattern diagrams.
---

# PlantUML Diagrams Skill

## Purpose

Use this skill for UML diagrams in the CSE6234 Software Design report.

Required diagrams may include:

- Use Case Diagram
- ERD
- Overall System Class Diagram
- Object Diagram
- Architecture Diagram
- Template Design Pattern Diagram
- Adapted Design Pattern Diagram
- Sequence Diagram for each design pattern

## Recommended Diagram Folder Structure

```text
docs/software_design_report/diagrams/
├── puml/
│   ├── use_case_diagram.puml
│   ├── erd.puml
│   ├── overall_class_diagram.puml
│   ├── object_diagram.puml
│   ├── architecture_diagram.puml
│   ├── facade_template.puml
│   ├── facade_project.puml
│   ├── facade_sequence.puml
│   ├── strategy_template.puml
│   ├── strategy_project.puml
│   ├── strategy_sequence.puml
│   ├── observer_template.puml
│   ├── observer_project.puml
│   └── observer_sequence.puml
└── img/
```

## PlantUML Rules

- Use PlantUML syntax.
- Every diagram must start with `@startuml` and end with `@enduml`.
- Keep diagrams readable.
- If a diagram is too large, split it or mark it for landscape layout in LaTeX.
- Use project-specific class names, not generic placeholders.
- Template pattern diagrams should reflect GoF-style structure.
- Adapted project diagrams must map the pattern participants to actual project classes.

## Required Design Pattern Diagrams

For each pattern, create:

1. **Template UML Diagram**
   - Shows general pattern participants.

2. **Adapted Project UML Diagram**
   - Maps the pattern to the project.

3. **Sequence Diagram**
   - Shows workflow/data flow.

## Recommended Patterns

Use these 3 unless the user says otherwise:

### 1. Facade Pattern

- Main class: `SeparationService`
- Purpose: hides preprocessing, NeoSSNet inference, output saving, and database updates behind one simple interface.
- Why suitable: the separation workflow contains multiple complex steps, but the router only needs one call.

### 2. Strategy Pattern

- Main abstraction: `SeparationAlgorithm`
- Concrete strategy: `NeoSSNetStrategy`
- Purpose: allows NeoSSNet or future algorithms to be swapped without changing the API or service workflow.
- Why suitable: the system may later support ONNX, baseline filtering, or other ML models.

### 3. Factory Method Pattern

- Main class: `SeparationAlgorithmFactory` or `ModelFactory`
- Purpose: creates the correct separation algorithm/model object based on the active model record in SQLite.
- Why suitable: the system stores model information in the database and should avoid hardcoding model creation across the codebase.

Optional future pattern:
- Observer Pattern for job status notifications, logging, or frontend progress updates.

## Rendering Rules

Render `.puml` files into images under:

```text
docs/software_design_report/diagrams/img/
```

Preferred output:

- PNG for easy LaTeX inclusion.
- SVG is also acceptable if the LaTeX setup supports it.

## LaTeX Inclusion

Use:

```latex
\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{diagrams/img/use_case_diagram.png}
    \caption{Use Case Diagram}
    \label{fig:use-case}
\end{figure}
```

For large diagrams, use landscape:

```latex
\begin{landscape}
\begin{figure}[H]
    \centering
    \includegraphics[width=1.25\textwidth]{diagrams/img/overall_class_diagram.png}
    \caption{Overall Class Diagram}
\end{figure}
\end{landscape}
```

## Done Criteria

A good diagram set should:

- Compile/render without PlantUML syntax errors.
- Match the project architecture.
- Be readable in the report.
- Support the design pattern explanation.
- Avoid unnecessary classes.
