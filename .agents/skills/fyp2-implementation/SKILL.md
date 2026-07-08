---
name: fyp2-implementation
description: Use when implementing, refactoring, testing, or improving final FYP2 project code for the Machine Learning-Based System for Cardiopulmonary Sound Separation with model selection, interchangeable separation strategies, baseline algorithms, NeoSSNet deep learning inference, FastAPI integration, SQLite persistence, output WAV generation, metrics, and test/check scripts. This skill is for code implementation only, not report writing.
---

# FYP2 Implementation Skill

Use this skill for final FYP2 code implementation only.

## Architecture Correction

Do not implement the project as NeoSSNet-only.

Follow Chapter 5 of the FYP report:
- upload, validation, model selection, job status, storage, preview, download, and history are reusable application functions
- separation algorithms are interchangeable strategies

## Main Goal

Build a real working Machine Learning-Based System for Cardiopulmonary Sound Separation with multi-model/model-selection support.

The system must support at least one real machine-learning/deep-learning strategy and may include traditional baseline strategies for comparison and workflow testing.

The project qualifies as machine learning-based because it includes:
1. Dataset support.
2. Trained or pre-trained ML model support.
3. Real inference process.
4. Model-generated heart/lung outputs.
5. Evaluation metrics when references are available.

## Required Separation Strategies

### Fixed Filter Baseline

- Simple baseline strategy.
- Use for sanity-checking the full application pipeline.
- Do not label as machine learning.

### NMF-Based Strategy

- Traditional decomposition strategy based on spectrogram factorization.
- Implement if feasible using available Python libraries.
- If not feasible, document the exact blocker.

### VMD-Based Strategy

- Traditional decomposition strategy based on variational mode decomposition.
- Implement if feasible using available Python libraries.
- If not feasible, document the exact blocker.

### NeoSSNet Deep Separation Strategy

- Main machine-learning/deep-learning strategy.
- Use PyTorch and available checkpoint/config if provided.
- Treat as the core ML model of the system.

## Required Architecture

- Use Strategy Pattern for separation algorithms.
- Use Factory Method or a model registry to create the correct strategy from the selected model record.
- Keep API/router code independent of algorithm internals.
- The frontend model selector must list available strategies/models.
- Store the selected model ID/strategy in the database job record.

## Important Wording Rules

- Do not call the whole system traditional signal processing only.
- Do not claim FixedFilter, NMF, or VMD are ML models.
- Explain FixedFilter, NMF, and VMD as baseline/conventional strategies.
- Explain NeoSSNet as the main ML/deep-learning strategy.

## Supporting Skills

Use when needed:
- `audio-ml-pipeline` for preprocessing, strategies, inference, output WAV, and metrics.
- `hls-dataset` for dataset preparation.
- `fastapi-backend` for API/routes/services.
- `sqlite-schema` for database/schema/models.

Do not use report/documentation skills unless explicitly asked:
- `fyp-report`
- `latex-report`
- `software-design-assignment`
- `plantuml-diagrams`
- `mermaid-diagrams`

## Implementation Modules

- audio validation
- preprocessing
- strategy interface
- strategy factory/model registry
- `FixedFilterSeparationStrategy`
- `NmfSeparationStrategy` if feasible
- `VmdSeparationStrategy` if feasible
- `NeoSSNetSeparationStrategy`
- model list API
- selected model execution
- job status
- output saving
- preview/download
- metrics
- processing history
- database logging
- frontend model selector
- test/check scripts

## Implementation Rules

- Focus on working code, not report text.
- Do not fake machine learning outputs.
- Do not claim an algorithm works unless it was actually tested.
- Do not hard-code local absolute paths in application logic.
- Keep ML logic separate from API routes.
- Use strategy/factory design for model selection.
- Do not implement diagnosis or medical recommendation features.
- Keep the system focused on sound separation only.

## Testing Requirements

Test each available strategy separately:
1. Strategy can be selected.
2. Strategy starts correctly.
3. Strategy returns heart and lung paths.
4. Output WAV files exist.
5. Output WAV files are playable.
6. Output files are not empty.
7. Job stores selected model/strategy.
8. Result endpoint returns correct files.
9. Missing model/checkpoint failures return clear errors.

## Done Criteria

The task is complete only when:
1. FastAPI starts successfully.
2. Frontend can upload WAV audio.
3. Frontend/API can list available models/strategies.
4. User can select at least Fixed Filter and NeoSSNet.
5. The selected model/strategy is stored in SQLite.
6. Separation runs using the selected strategy.
7. Heart and lung WAV outputs are generated.
8. Preview/download works.
9. History shows completed jobs and selected strategy.
10. Metrics are calculated when reference signals exist.
11. Tests/check scripts pass.
12. The final system follows Chapter 5: model selection, interchangeable strategies, and ML-based NeoSSNet core model.

## Final Response Format

After implementation, report:
- What was changed
- What files were modified
- What model/strategy is active
- What commands were run
- Which tests passed
- Where output files are saved
- What still needs improvement
