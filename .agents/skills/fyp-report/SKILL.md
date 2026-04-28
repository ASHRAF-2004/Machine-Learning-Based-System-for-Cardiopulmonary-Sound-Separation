---
name: fyp-report
description: Use when writing or improving FYP report sections, methodology, database explanation, architecture explanation, viva answers, or presentation content.
---

# FYP Report Skill

Project:
Development of a Machine Learning-Based System for Cardiopulmonary Sound Separation

Tone:
- academic
- software engineering focused
- clear and easy to defend in viva

Important report claims:
- The system uses FastAPI as backend.
- SQLite stores metadata, logs, jobs, and results.
- Audio files are stored on the filesystem.
- HLS-CMDS is used as dataset.
- NeoSSNet is used for cardiopulmonary sound separation.
- Raw dataset and runtime storage are separated.

Avoid:
- claiming clinical accuracy unless validated
- claiming diagnosis
- claiming real hospital deployment
- overstating noise robustness if only HLS-CMDS is used

When writing:
- explain design decisions
- connect implementation to objectives
- mention limitations honestly
- include future work where appropriate