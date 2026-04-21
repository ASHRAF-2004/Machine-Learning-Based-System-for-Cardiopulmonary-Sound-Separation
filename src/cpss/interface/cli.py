from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from cpss.application.orchestrator import SeparationOrchestrator
from cpss.domain.models import AudioSample
from cpss.infrastructure.factory import BaselineFactory, NeoSSNetFactory


def _load_signal(path: Path) -> np.ndarray:
    return np.load(path).astype(np.float32)


def _save_output(prefix: Path, heart: np.ndarray, lung: np.ndarray) -> None:
    np.save(prefix.with_suffix(".heart.npy"), heart)
    np.save(prefix.with_suffix(".lung.npy"), lung)


def main() -> None:
    parser = argparse.ArgumentParser(description="CPSS prototype CLI")
    parser.add_argument("--input", type=Path, required=True, help="Path to input .npy signal")
    parser.add_argument("--sample-rate", type=int, required=True)
    parser.add_argument("--model", choices=["baseline", "neossnet"], default="neossnet")
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()

    signal = _load_signal(args.input)
    sample = AudioSample(signal=signal, sample_rate=args.sample_rate)

    factory = NeoSSNetFactory() if args.model == "neossnet" else BaselineFactory()
    orchestrator = SeparationOrchestrator(factory=factory)
    result = orchestrator.run_inference(sample)
    _save_output(args.output_prefix, result.heart, result.lung)

    print(
        json.dumps(
            {
                "strategy": result.strategy_name,
                "samples": int(signal.size),
                "sample_rate": args.sample_rate,
                "outputs": {
                    "heart": str(args.output_prefix.with_suffix('.heart.npy')),
                    "lung": str(args.output_prefix.with_suffix('.lung.npy')),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
