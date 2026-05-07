---
name: mermaid-diagrams
description: Use when creating, editing, validating, or rendering Mermaid diagrams such as architecture diagrams, flowcharts, ERDs, sequence diagrams, class diagrams, and report-ready visual diagrams.
---

# Mermaid Diagrams Skill

## Purpose

Use this skill when Mermaid is better for clean, readable report visuals.

Mermaid should be considered for:

- Architecture diagrams
- Workflow diagrams
- ERD
- Simple sequence diagrams
- Simple class diagrams
- System overview diagrams

For formal GoF design pattern template UML, prefer PlantUML unless the user asks otherwise.

## Project Context

The project is a HealthTech cardiopulmonary sound separation system.

Main flow:

- User uploads mixed WAV audio.
- FastAPI validates and stores upload.
- NeoSSNet separates heart and lung sounds.
- SQLite stores metadata, jobs, results, logs, and metrics.
- Local storage stores uploaded and generated WAV files.
- User previews and downloads outputs.

## Recommended Folder Structure

```text
docs/software_design_report/diagrams/mermaid/
├── architecture_diagram.mmd
├── erd.mmd
├── use_case_diagram.mmd
├── system_workflow.mmd
└── sequence_upload_separation.mmd
```

Rendered outputs should go to:

```text
docs/software_design_report/diagrams/img/
```

## Mermaid Rules

- Every diagram file should be valid Mermaid syntax.
- Prefer readable diagrams over overly detailed diagrams.
- Use clear node names.
- Avoid huge diagrams.
- Split large diagrams into smaller diagrams if needed.
- Use Mermaid for clean report visuals, not for forced UML complexity.
- Keep diagram content consistent with the LaTeX report and system architecture.

## Recommended Diagram Types

### Architecture / Workflow

Use `flowchart`.

### Sequence Diagram

Use `sequenceDiagram`.

### ERD

Use `erDiagram`.

### Class Diagram

Use `classDiagram`.

## Export Rules

Prefer SVG for LaTeX/report quality.

Acceptable outputs:

- SVG
- PDF
- High-resolution PNG

## Mermaid CLI

Use Mermaid CLI if available:

```bash
mmdc -i input.mmd -o output.svg
```

Mermaid CLI can generate SVG, PNG, and PDF from Mermaid definition files.

## Done Criteria

A good Mermaid diagram should:

- Render without syntax errors.
- Be readable in the final PDF.
- Explain the system better than text alone.
- Avoid unnecessary details.
- Match the project architecture and database schema.
