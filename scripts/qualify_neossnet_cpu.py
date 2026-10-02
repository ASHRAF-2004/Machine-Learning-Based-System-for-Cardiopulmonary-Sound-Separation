"""Read-only CPU qualification of the pinned released NeoSSNet checkpoint.

Run with the isolated ML environment. This script writes no audio/model file and
does not use patient recordings or the production application.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/ml/neossnet_source"
WEIGHTS = ROOT / "storage/ml_models/model_best.pt"
CONFIG = ROOT / "storage/ml_models/model.yaml"
EXPECTED_WEIGHTS = "abf4f05321d7c0a9da0ee25bfe50f0dbb5736d5f855150787009b4221f947358"
EXPECTED_CONFIG = "b7d82e7fb9cbcbd7382d6eadb69220fba5c7d25cafd5bbfdb83f714ca39d5096"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=1.0)
    args = parser.parse_args()
    if not 0.1 <= args.seconds <= 10.0:
        parser.error("seconds must be between 0.1 and 10")
    if digest(WEIGHTS) != EXPECTED_WEIGHTS or digest(CONFIG) != EXPECTED_CONFIG:
        raise RuntimeError("Pinned released checkpoint/configuration hashes do not match")

    sys.path.insert(0, str(SOURCE))
    import numpy as np
    import torch
    import yaml
    from models import MaskNet

    torch.set_num_threads(2)
    torch.manual_seed(42)
    with CONFIG.open() as stream:
        config = yaml.safe_load(stream)
    start_load = time.perf_counter()
    model = MaskNet(**config)
    state = torch.load(WEIGHTS, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.eval()
    load_seconds = time.perf_counter() - start_load

    length = round(args.seconds * 4000)
    times = torch.arange(length, dtype=torch.float32) / 4000.0
    mixture = (0.2 * torch.sin(2 * torch.pi * 80 * times)
               + 0.05 * torch.sin(2 * torch.pi * 500 * times)).view(1, 1, -1)
    with torch.inference_mode():
        start_inference = time.perf_counter()
        output = model(mixture)
        inference_seconds = time.perf_counter() - start_inference
    if tuple(output.shape) != (1, 2, length) or not bool(torch.isfinite(output).all()):
        raise RuntimeError("NeoSSNet output violates shape/finite contract")
    print(json.dumps({
        "classification": "OFFLINE SYNTHETIC LOAD/SHAPE PROBE, NOT QUALITY BENCHMARK",
        "checkpoint_sha256": EXPECTED_WEIGHTS,
        "config_sha256": EXPECTED_CONFIG,
        "torch": torch.__version__,
        "numpy": np.__version__,
        "cpu_threads": torch.get_num_threads(),
        "cuda_available": torch.cuda.is_available(),
        "input_shape": list(mixture.shape),
        "output_shape": list(output.shape),
        "source_order": "author code channel 0 heart / channel 1 lung; not independently validated by synthetic tone",
        "output_min": float(output.min()),
        "output_max": float(output.max()),
        "output_rms_by_channel": [float(torch.sqrt(torch.mean(output[0, i] ** 2))) for i in range(2)],
        "cold_load_seconds": round(load_seconds, 3),
        "first_inference_seconds": round(inference_seconds, 3),
        "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
