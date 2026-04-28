---
name: sqlite-schema
description: Use when working with SQLite, schema.sql, seed.sql, database models, database queries, or SQLAlchemy mappings.
---

# SQLite Schema Skill

The project uses SQLite.

Database files:
- database/cardiopulmonary.db
- database/schema.sql
- database/seed.sql

Main tables:
- uploaded_audio
- model
- separation_job
- separation_result
- evaluation_metric
- system_log

Rules:
- Do not redesign the schema unless explicitly asked.
- Do not store audio blobs in SQLite.
- Store file paths, metadata, timestamps, job status, logs, and metrics.
- Match SQLAlchemy models to the existing schema.
- Keep table names lowercase because the current schema uses lowercase names.

Expected relationships:
- uploaded_audio 1-to-many separation_job
- model 1-to-many separation_job
- separation_job 1-to-1 separation_result
- separation_result 1-to-many evaluation_metric
- separation_job 1-to-many system_log

When done:
- schema must remain compatible with existing cardiopulmonary.db
- foreign keys should be respected
- do not break existing table names