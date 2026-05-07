---
name: latex-report
description: Use when writing, editing, compiling, or organizing LaTeX reports, APA references, BibTeX/BibLaTeX files, cover pages, figures, tables, and PDF-ready academic documents.
---

# LaTeX Report Skill

## Purpose
Use this skill for the CSE6234 Software Design report written in LaTeX.

The final output should be a PDF-ready LaTeX report with:
- structured chapters/sections
- university logo
- APA-style citations
- `.bib` bibliography file
- PlantUML-generated diagrams included as images
- clean academic formatting

## Important Project Paths
Use these paths:

- Assignment references:
  - `docs/Referances/`

- Extra papers if needed:
  - `docs/Papers/`

- University logo and elements:
  - `docs/elements/`

- Recommended LaTeX report folder:
  - `docs/software_design_report/`

## Recommended LaTeX Structure

Use this structure:

```text
docs/software_design_report/
├── main.tex
├── references.bib
├── chapters/
│   ├── 01_introduction.tex
│   ├── 02_system_overview.tex
│   ├── 03_requirements_design_principles.tex
│   ├── 04_design_patterns.tex
│   └── 05_conclusion.tex
├── figures/
│   ├── logo/
│   ├── uml/
│   └── architecture/
└── tables/
```

## APA Style

Use BibLaTeX APA style:

```latex
\usepackage[
  backend=biber,
  style=apa,
  sorting=nyt
]{biblatex}

\addbibresource{references.bib}
```

Use in-text citations like:

```latex
\parencite{key2024}
\textcite{key2024}
```

Print references using:

```latex
\printbibliography
```

## Report Requirements

The report should generally follow this structure:

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

Additional sections or diagrams may be added when they improve the report, for example:
- Architecture Diagram
- Sequence Diagram
- Data Flow Explanation
- Pattern Mapping Tables
- System Workflow
- Implementation Notes

The assignment structure should be preserved, but the report may include extra subsections to improve clarity and completeness.

## Group Details

Use these group details on the cover page:

Group: Group 1  
Tutorial Section: TT5L

Members:

- AL-SALOUL, ASHRAF ALI HUSSEIN | 1221303805
- AHMAD AKMAL ASYRAAF BIN SHAMS | 242UC244CJ
- RESHMA A/P KRISHNAMURTHY | 243UC247KW
- SHARWIN A/L R SIVALINGAM | 241UC241C1

## LaTeX Quality Rules

- Keep formatting clean and academic.
- Use `\section`, `\subsection`, and `\subsubsection` properly.
- Use tables for pattern mapping.
- Use figures for UML diagrams.
- Use `pdflscape` or landscape pages for very large diagrams.
- Do not write unsupported claims.
- Do not claim clinical validation.
- Keep wording suitable for a software design assignment.

## Bibliography Rules

- Create and maintain `references.bib`.
- Use APA-compatible BibLaTeX entries.
- Use the 3 research papers from `docs/Referances/`.
- If reference metadata is incomplete, inspect files in `docs/Papers/`.
- Do not invent author names, titles, years, DOI, or publication details.
- If metadata cannot be found, flag it clearly.

## Done Criteria

A good output should:

- compile as LaTeX
- include citations from `references.bib`
- include the university logo if available
- include UML diagrams as figures
- be ready to export to PDF