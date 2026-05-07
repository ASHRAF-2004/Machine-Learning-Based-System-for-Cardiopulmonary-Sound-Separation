---
name: software-design-assignment
description: Use when working on the CSE6234 Software Design assignment, especially software design proposal, UML diagrams, design patterns, pattern justification, literature review, sample code, LaTeX report structure, and PDF-ready documentation.
---

# Software Design Assignment Skill

## Assignment Context
This project is for CSE6234 Software Design.

Deliverable:
- Software Design Proposal and Software Design Pattern Document
- Final submission must be PDF format.
- The final report should be written in LaTeX when possible.

The report must show understanding of:
- software design concepts
- software design principles
- design patterns
- UML modeling
- planned code design
- pattern justification

## Required Report Sections
The report should generally follow this assignment structure:

1. **Cover Page**
2. **Table of Contents**
3. **Abstract / Executive Summary**
4. **Introduction**
   - Problem Statement
   - Project Objectives
   - Literature Review: 3 Reviews
   - Project and System Scope
5. **System Overview**
   - Generic Use Case
   - Class Diagram
   - Entity Relationship Diagram (ERD)
   - Object Diagram
6. **Requirements**
   - Software Design Concepts
   - Design Principles
7. **Proposed Design Patterns**
   - Design Pattern 1
   - Design Pattern 2
   - Design Pattern 3
8. **Conclusion and Suggestions**
9. **Bibliography / References**

Do not delete these major sections unless the user explicitly requests it.

Additional explanatory sections may be added when they improve the report, for example:
- Data Flow Explanation
- Pattern Mapping Tables
- Implementation Notes

Do not insert optional global diagrams such as `architecture_diagram`, `system_workflow`, or `upload_separation_sequence` unless the user explicitly asks for them.

The assignment structure should be preserved, but the report may include extra subsections to improve clarity and completeness.

## LaTeX Requirement
The final report should be written in LaTeX.

Use:
- `docs/software_design_report/main.tex`
- `docs/software_design_report/references.bib`
- modular chapter files under `docs/software_design_report/chapters/`
- PlantUML source diagrams under `docs/software_design_report/diagrams/puml/`
- rendered diagram images under `docs/software_design_report/diagrams/img/`

Use APA-style citations with BibLaTeX:

```latex
\usepackage[
  backend=biber,
  style=apa,
  sorting=nyt
]{biblatex}

\addbibresource{references.bib}
```

References should be built from:
- `docs/Referances/`
- `docs/Papers/` if needed

Do not invent bibliography metadata. If metadata is missing, mark it with a clear TODO comment.

## Pattern Section Template
For each design pattern, use this structure:

### Pattern Name
Example: Facade Pattern, Strategy Pattern, Factory Method Pattern.

### Pattern Type
State whether the pattern is structural, behavioral, or creational.

### Problem
Explain the specific design problem in this project that motivates the pattern.

### Solution
Explain how the pattern solves the problem in this project using clear software design language.

### Structure
Explain the original GoF-style template structure and reference the template pattern diagram.
Use numbered participants so the explanation is easy to match with the diagram.

Example for Facade:
1. Facade
2. Additional Facade
3. Complex Subsystem
4. Client

Prefer original PlantUML-generated template diagrams based on GoF-style structure. Do not use external template screenshots unless they are properly cited or recreated as original diagrams.

### Participants / Structure Explanation
Explain how each numbered template participant maps to the project design.
Include a mapping table from template participants to project classes.

Example:
- Facade -> `SeparationService`
- Complex Subsystem -> `AudioPreprocessor`, `NeoSSNetInference`, `StorageService`, `DatabaseSession`

### Function or Software Component Affected
Identify which module/component uses the pattern.

### Description of Workflow or Data Flow
Explain how data moves through the pattern.

### Sample Class Diagram
Create a PlantUML class diagram that reflects the pattern structure using this project's actual classes.

### Sample Other UML Notation, Preferably Sequence Diagram
Provide a PlantUML sequence diagram or other relevant UML notation using project classes.

### Sample Potential Code
Give small clean code sample.
Prefer Python if the project is FastAPI/PyTorch.
Use C++ only if the user asks.

### Benefits
Explain why this pattern improves the design.

### Limitations
Explain trade-offs or possible disadvantages.

## UML Rules
Use PlantUML for formal UML pattern template diagrams, adapted project class diagrams, and sequence diagrams unless the user asks for another format.
Use Mermaid mainly for optional workflow diagrams or clean global overview diagrams when needed.

Every pattern should include:
1. Pattern Name
2. Pattern Type
3. Problem
4. Solution
5. Structure with numbered template participants
6. Participants / Structure Explanation
7. Function or Software Component Affected
8. Description of workflow or data flow
9. Sample Class Diagram
10. Sample Other UML Notation, preferably Sequence Diagram
11. Sample Potential Code
12. Benefits
13. Limitations

Global UML diagrams should include:
- high-level class diagram
- use case diagram
- ERD
- object diagram

Do not insert optional global diagrams such as `architecture_diagram`, `system_workflow`, or `upload_separation_sequence` unless the user explicitly asks for them.

Large diagrams may be placed on landscape pages in LaTeX.

## Recommended Patterns for This Project
For a HealthTech cardiopulmonary sound separation system, prefer these 3 patterns:

### 1. Facade Pattern
- Main class: `SeparationService`
- Purpose: hides preprocessing, NeoSSNet inference, output saving, and database updates behind one simple interface.
- Why suitable: the separation workflow contains multiple complex steps, but the router only needs one simple call.

Recommended mapping:
- Client → `separation.py` router
- Facade → `SeparationService`
- Subsystem → `AudioPreprocessor`
- Subsystem → `NeoSSNetInference`
- Subsystem → `StorageService`
- Subsystem → `DatabaseSession`

### 2. Strategy Pattern
- Main abstraction: `SeparationAlgorithm`
- Concrete strategy: `NeoSSNetStrategy`
- Purpose: allows NeoSSNet or future algorithms to be swapped without changing the API or service workflow.
- Why suitable: the system may later support ONNX, baseline filtering, or other ML models.

Recommended mapping:
- Context → `SeparationService`
- Strategy → `SeparationAlgorithm`
- ConcreteStrategy → `NeoSSNetStrategy`
- Future ConcreteStrategy → `ONNXNeoSSNetStrategy` or `BaselineSeparationStrategy`
- Client → `separation.py` router

### 3. Factory Method Pattern
- Main class: `SeparationAlgorithmFactory` or `ModelFactory`
- Purpose: creates the correct separation algorithm/model object based on the active model record in SQLite.
- Why suitable: the system stores model information in the database and should avoid hardcoding model creation across the codebase.

Recommended mapping:
- Creator → `SeparationAlgorithmFactory`
- Product → `SeparationAlgorithm`
- ConcreteProduct → `NeoSSNetStrategy`
- Client → `SeparationService`

Optional future pattern:
- Observer Pattern for job status notifications, logging, metrics updates, or frontend progress updates.

## Report Quality Rules
- Keep the tone academic but understandable.
- Connect every pattern to a real requirement or software quality attribute.
- Do not add a pattern just for decoration.
- Every pattern must solve a real design problem.
- Avoid claiming clinical validation.
- Mention that the project is a prototype/proof of concept if relevant.
- Use citations for research papers in literature review.
- Use references for GoF/design pattern theory.
- Make the final content easy to convert into a PDF report.

## Anti-Patterns to Avoid
- Do not force too many patterns.
- Do not make UML diagrams that do not match the code/design.
- Do not use Singleton everywhere.
- Do not describe patterns only theoretically; always connect them to the system.
- Do not write sample code that contradicts the UML.
- Do not claim a pattern is implemented if it is only a future improvement; label it clearly as planned/future if needed.

## Done Criteria
A high-quality answer should:
- follow the assignment structure
- include at least 3 design patterns
- write pattern sections using Pattern Name, Pattern Type, Problem, Solution, Structure, and Participants / Structure Explanation first
- include the assignment-required subsections for each pattern
- include PlantUML-generated template/project class diagrams and sequence diagrams where useful
- include sample code for each pattern
- include benefits and limitations
- connect design choices to requirements and software attributes
- use LaTeX-friendly structure when writing report content
- be easy to compile/export into a PDF report
