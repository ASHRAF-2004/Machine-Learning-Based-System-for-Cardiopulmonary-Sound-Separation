# Machine Learning-Based System for Cardiopulmonary Sound Separation

This repository contains a Python prototype system that separates mixed cardiopulmonary audio into heart and lung components.

## Included Artifacts
- [Implementation Plan](IMPLEMENTATION_PLAN.md)
- [Implementation Status](docs/IMPLEMENTATION_STATUS.md)

## Prototype Architecture
The code follows the plan's recommended patterns:
- **Layered architecture** (`domain`, `application`, `infrastructure`, `interface`)
- **Strategy pattern** for interchangeable separation methods
- **Abstract Factory pattern** for model component selection
- **Observer pattern** for inference lifecycle events

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## CLI Inference Example
```bash
python -m cpss.interface.cli \
  --input sample.npy \
  --sample-rate 4000 \
  --model neossnet \
  --output-prefix output/separated
```

Outputs are saved as:
- `output/separated.heart.npy`
- `output/separated.lung.npy`
