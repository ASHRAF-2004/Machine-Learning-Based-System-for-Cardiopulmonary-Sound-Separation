# NeoSSNet Cardiopulmonary Sound Separation Prototype

This project is a C++20 software design prototype for cardiopulmonary sound separation using:
- Strategy pattern (`SeparationStrategy` -> `NeoSSNetStrategy`)
- Abstract Factory pattern (`PipelineFactory` -> `NeoSSNetFactory`)
- Observer pattern (`NotificationCenter` + `UIObserver`/`AuditObserver`)

## Design Patterns Used (and Why)

1. **Strategy Pattern**
   - `SeparationStrategy` defines a common separation interface, while `NeoSSNetStrategy` provides a concrete algorithm implementation.
   - `SeparationService` can call `separate(...)` without depending on one hard-coded algorithm class.
   - Benefit: easy to swap in future models (e.g., another neural architecture) with minimal service-layer changes.

2. **Abstract Factory Pattern**
   - `PipelineFactory` abstracts creation of strategy objects and `NeoSSNetFactory` creates the concrete `NeoSSNetStrategy`.
   - `SeparationService` asks a factory for a strategy instead of constructing algorithm classes directly.
   - Benefit: centralizes creation logic and supports future families of pipeline components.

3. **Observer Pattern**
   - `NotificationCenter` stores multiple `ResultObserver` subscribers and broadcasts `onResultReady(...)` events.
   - `UIObserver` and `AuditObserver` react independently when separation results are produced.
   - Benefit: decouples result-processing flow from side effects like UI updates and audit logging.

## Project Layout

- `src/main.cpp`: Crow app entrypoint.
- `src/api`: upload and results REST controllers.
- `src/core`: domain entities (`Recording`, `SeparationResult`, `ModelConfig`).
- `src/processing`: strategy and factory abstractions plus mock NeoSSNet implementation.
- `src/services`: orchestration (`SeparationService`) and observer notification center.
- `src/storage`: SQLite persistence (`SQLiteManager`, `ResultRepository`).
- `templates`: upload and results pages.
- `sql/schema.sql`: SQLite schema script.
- `docs/uml.puml`: PlantUML class diagram.
- `tests`: GoogleTest unit tests.

## Build Prerequisites

- CMake >= 3.20
- vcpkg
- C++20 compiler

Install deps:

```bash
vcpkg install crow nlohmann-json sqlite3 sqlite-modern-cpp libsndfile fftw3 onnxruntime spdlog gtest
```

## Build

```bash
mkdir -p build
cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake
cmake --build . -j
```

## Run

```bash
./neossnet_app
```

Open: <http://localhost:8080>

## API

- `POST /api/upload` — upload WAV bytes (raw body), returns `recordingId`.
- `POST /api/separate/{recordingId}` — process recording and persist outputs.
- `GET /results/{recordingId}` — return result metadata and download paths.

## Tests

```bash
ctest --output-on-failure
```

## Notes

- `NeoSSNetStrategy` uses a mock separation operation for prototype mode (`x*1.2` heart, `x*0.8` lung).
- Replace `src/processing/neossnet_strategy.cpp` with real ONNX runtime inferencing for production ML behavior.
