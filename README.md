# NeoSSNet Cardiopulmonary Sound Separation Prototype

This project is a C++20 software design prototype for cardiopulmonary sound separation using:
- Strategy pattern (`SeparationStrategy` -> `NeoSSNetStrategy`)
- Abstract Factory pattern (`PipelineFactory` -> `NeoSSNetFactory`)
- Observer pattern (`NotificationCenter` + `UIObserver`/`AuditObserver`)

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
