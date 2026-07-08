"""Standalone NeoSSNet inference and validation smoke test.

The script uses the same backend wrapper as the FastAPI service, so it checks
the real runtime preprocessing, checkpoint/config loading, tensor shapes,
output channel order assumption, output scaling, and optional HLS-CMDS metrics.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ml.audio_utils import load_wav_mono  # noqa: E402
from app.ml.neossnet_inference import (  # noqa: E402
    MODEL_SAMPLE_RATE,
    NEOSSNET_SOURCE_DIR,
    load_wav_for_neossnet,
    run_neossnet_inference,
)
from app.services import evaluation_service  # noqa: E402


MODEL_PATH = PROJECT_ROOT / "storage" / "ml_models" / "model_best.pt"
MODEL_CONFIG_PATH = PROJECT_ROOT / "storage" / "ml_models" / "model.yaml"
DEFAULT_HEART_OUTPUT_PATH = PROJECT_ROOT / "storage" / "outputs" / "heart" / "test_heart.wav"
DEFAULT_LUNG_OUTPUT_PATH = PROJECT_ROOT / "storage" / "outputs" / "lung" / "test_lung.wav"
TEST_PAIRS_PATH = PROJECT_ROOT / "datasets" / "hls_cmds" / "metadata" / "test_pairs.csv"

REQUIRED_PACKAGES = {
    "torch": "torch",
    "torchaudio": "torchaudio",
    "yaml": "pyyaml",
    "ptwt": "ptwt",
    "prettytable": "prettytable",
    "numpy": "numpy",
}


def parse_args() -> argparse.Namespace:
    default_input, default_heart_ref, default_lung_ref = default_hls_pair()
    parser = argparse.ArgumentParser(description="Run and validate NeoSSNet inference.")
    parser.add_argument("--input", type=Path, default=default_input)
    parser.add_argument("--heart-reference", type=Path, default=default_heart_ref)
    parser.add_argument("--lung-reference", type=Path, default=default_lung_ref)
    parser.add_argument("--checkpoint", type=Path, default=MODEL_PATH)
    parser.add_argument("--config", type=Path, default=MODEL_CONFIG_PATH)
    parser.add_argument("--heart-output", type=Path, default=DEFAULT_HEART_OUTPUT_PATH)
    parser.add_argument("--lung-output", type=Path, default=DEFAULT_LUNG_OUTPUT_PATH)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--bandpass",
        action="store_true",
        help="Apply the optional reference helper bandpass before inference.",
    )
    return parser.parse_args()


def default_hls_pair() -> tuple[Path, Path | None, Path | None]:
    if TEST_PAIRS_PATH.is_file():
        with TEST_PAIRS_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            for row in csv.DictReader(csv_file):
                mixed = PROJECT_ROOT / row["mixed_path"]
                heart = PROJECT_ROOT / row["heart_path"]
                lung = PROJECT_ROOT / row["lung_path"]
                if mixed.is_file() and heart.is_file() and lung.is_file():
                    return mixed, heart, lung
    return PROJECT_ROOT / "sample_inputs" / "H0001.wav", None, None


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def check_dependencies() -> None:
    missing = [
        pip_name
        for import_name, pip_name in REQUIRED_PACKAGES.items()
        if importlib.util.find_spec(import_name) is None
    ]
    if not missing:
        return

    unique_missing = sorted(set(missing))
    print("Missing Python dependencies:")
    for package_name in unique_missing:
        print(f"- {package_name}")
    print()
    print("Install command:")
    print(f"pip install {' '.join(unique_missing)}")
    fail("Install the missing dependencies and run this script again.")


def check_required_files(args: argparse.Namespace) -> None:
    required_paths = [
        NEOSSNET_SOURCE_DIR / "utils" / "__init__.py",
        NEOSSNET_SOURCE_DIR / "models" / "__init__.py",
        args.checkpoint,
        args.config,
        args.input,
    ]
    for path in required_paths:
        if path is None or not path.exists():
            fail(f"Required file or folder is missing: {relative(path)}")

    if args.checkpoint.stat().st_size == 0:
        fail(f"Model checkpoint is empty: {relative(args.checkpoint)}")


def relative(path: Path | None) -> str:
    if path is None:
        return "None"
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _fmt(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "-"
    return f"{value:.6f}"


def print_input_validation(input_path: Path) -> None:
    input_wav, sample_rate = load_wav_for_neossnet(input_path)
    raw_audio = load_wav_mono(input_path)
    print("NeoSSNet input validation")
    print(f"- input file: {relative(input_path)}")
    print(f"- original sample rate: {raw_audio.original_sample_rate_hz} Hz")
    print(f"- model sample rate: {sample_rate} Hz")
    print(f"- expected model sample rate: {MODEL_SAMPLE_RATE} Hz")
    print(f"- duration: {input_wav.shape[-1] / sample_rate:.3f} s")
    print(f"- mono conversion: channels={raw_audio.channels} -> 1")
    print(f"- input shape before batch: {tuple(input_wav.shape)}")
    print(f"- direct model input shape: {(1, *tuple(input_wav.shape))}")
    print(
        "- input min/max/RMS: "
        f"{_fmt(float(input_wav.min()))} / "
        f"{_fmt(float(input_wav.max()))} / "
        f"{_fmt(float((input_wav.square().mean().sqrt())))}"
    )


def metric_lookup(metrics: list[evaluation_service.MetricRecord]) -> dict[tuple[str, str], float]:
    return {
        (metric.metric_scope, metric.metric_name): metric.metric_value
        for metric in metrics
    }


def print_reference_metrics(args: argparse.Namespace, sample_rate_hz: int) -> None:
    if not args.heart_reference or not args.lung_reference:
        print("Reference metrics: skipped; no paired heart/lung references supplied.")
        return
    if not args.heart_reference.is_file() or not args.lung_reference.is_file():
        print("Reference metrics: skipped; reference files are missing.")
        return

    reference_pair = evaluation_service.ReferencePair(
        heart_path=args.heart_reference,
        lung_path=args.lung_reference,
        reference_type="hls_cmds_validation_reference",
    )
    metrics = metric_lookup(
        evaluation_service.calculate_reference_metrics(
            input_path=args.input,
            heart_output_path=args.heart_output,
            lung_output_path=args.lung_output,
            reference_pair=reference_pair,
            sample_rate_hz=sample_rate_hz,
        )
    )
    print("Reference metrics")
    print(f"- heart reference: {relative(args.heart_reference)}")
    print(f"- lung reference: {relative(args.lung_reference)}")
    print(f"- heart SI-SDR: {_fmt(metrics.get(('heart', 'si_sdr')))} dB")
    print(f"- lung SI-SDR: {_fmt(metrics.get(('lung', 'si_sdr')))} dB")
    print(f"- heart SNR improvement: {_fmt(metrics.get(('heart', 'snr_improvement')))} dB")
    print(f"- lung SNR improvement: {_fmt(metrics.get(('lung', 'snr_improvement')))} dB")
    print(f"- heart correlation: {_fmt(metrics.get(('heart', 'correlation')))}")
    print(f"- lung correlation: {_fmt(metrics.get(('lung', 'correlation')))}")


def main() -> int:
    args = parse_args()
    check_dependencies()
    check_required_files(args)

    print(f"NeoSSNet source: {relative(NEOSSNET_SOURCE_DIR)}")
    print(f"Checkpoint path: {relative(args.checkpoint)}")
    print(f"Config path: {relative(args.config)}")
    print("Output channel order assumption: channel 0 heart, channel 1 lung")
    print("Channel order evidence: reference evaluate.py indexes output[:, 0, :] as heart and output[:, 1, :] as lung.")
    print_input_validation(args.input)

    result = run_neossnet_inference(
        input_wav_path=args.input,
        model_path=args.checkpoint,
        model_config_path=args.config,
        heart_output_path=args.heart_output,
        lung_output_path=args.lung_output,
        device_name=args.device,
        bandpass=args.bandpass,
    )

    print("NeoSSNet output validation")
    print(f"- output shape: {result.output_shape}")
    print(f"- bandpass enabled: {result.bandpass_enabled}")
    print(
        "- heart min/max/RMS: "
        f"{_fmt(result.heart_min)} / {_fmt(result.heart_max)} / {_fmt(result.heart_rms)}"
    )
    print(
        "- lung min/max/RMS: "
        f"{_fmt(result.lung_min)} / {_fmt(result.lung_max)} / {_fmt(result.lung_rms)}"
    )
    print(f"- heart output saved: {relative(result.heart_file_path)}")
    print(f"- lung output saved: {relative(result.lung_file_path)}")
    print_reference_metrics(args, result.sample_rate_hz)
    print("PASS: NeoSSNet inference completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
