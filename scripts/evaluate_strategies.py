"""Evaluate separation strategies on paired HLS-CMDS test samples."""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.db import SessionLocal, initialize_database  # noqa: E402
from app.ml.strategy_factory import SeparationAlgorithmFactory  # noqa: E402
from app.services import evaluation_service, model_service, storage_service  # noqa: E402


DEFAULT_EVALUATION_DIR = PROJECT_ROOT / "evaluation"
TEST_PAIRS_PATH = PROJECT_ROOT / "datasets" / "hls_cmds" / "metadata" / "test_pairs.csv"
DEFAULT_STRATEGIES = ("fixed_filter", "nmf", "vmd", "neossnet")
SLOW_STRATEGIES = {"vmd_quality"}


@dataclass(frozen=True)
class EvaluationSample:
    mixed_id: str
    mixed_path: Path
    heart_path: Path
    lung_path: Path


@dataclass(frozen=True)
class EvaluationPaths:
    output_dir: Path

    @property
    def details_path(self) -> Path:
        return self.output_dir / "results_strategy_comparison.csv"

    @property
    def summary_path(self) -> Path:
        return self.output_dir / "summary_strategy_comparison.csv"

    @property
    def audio_output_dir(self) -> Path:
        return self.output_dir / "outputs"


DETAIL_FIELDS = [
    "sample_filename",
    "method_key",
    "strategy_key",
    "method_name",
    "method_type",
    "checkpoint_path",
    "status",
    "processing_time_ms",
    "heart_si_sdr_db",
    "lung_si_sdr_db",
    "heart_snr_improvement_db",
    "lung_snr_improvement_db",
    "heart_mse",
    "lung_mse",
    "heart_mae",
    "lung_mae",
    "heart_correlation",
    "lung_correlation",
    "heart_alignment_lag_samples",
    "lung_alignment_lag_samples",
    "heart_output_path",
    "lung_output_path",
    "failure_reason",
]

SUMMARY_FIELDS = [
    "method_key",
    "strategy_key",
    "method_name",
    "method_type",
    "checkpoint_path",
    "sample_count",
    "success_count",
    "failure_count",
    "timeout_count",
    "mean_processing_time_ms",
    "mean_heart_si_sdr_db",
    "mean_lung_si_sdr_db",
    "mean_heart_snr_improvement_db",
    "mean_lung_snr_improvement_db",
    "mean_heart_mse",
    "mean_lung_mse",
    "mean_heart_mae",
    "mean_lung_mae",
    "mean_heart_correlation",
    "mean_lung_correlation",
    "mean_heart_alignment_lag_samples",
    "mean_lung_alignment_lag_samples",
]

SUMMARY_NUMERIC_FIELDS = [
    "processing_time_ms",
    "heart_si_sdr_db",
    "lung_si_sdr_db",
    "heart_snr_improvement_db",
    "lung_snr_improvement_db",
    "heart_mse",
    "lung_mse",
    "heart_mae",
    "lung_mae",
    "heart_correlation",
    "lung_correlation",
    "heart_alignment_lag_samples",
    "lung_alignment_lag_samples",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare separation strategies on paired HLS-CMDS test samples. "
            "SI-SDR is reported in dB; higher values are better."
        )
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=10,
        help="Maximum number of paired test samples to evaluate. Default: 10.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--strategies",
        default=",".join(DEFAULT_STRATEGIES),
        help=(
            "Comma-separated strategy keys, for example "
            "fixed_filter,nmf,vmd,neossnet. Use 'all' for all active methods."
        ),
    )
    parser.add_argument(
        "--timeout-per-strategy",
        type=float,
        default=120.0,
        help=(
            "Total seconds allowed per strategy before remaining samples are "
            "marked as timeout. Use 0 to disable. Default: 120."
        ),
    )
    parser.add_argument(
        "--skip-slow",
        action="store_true",
        help="Skip known slow optional presets such as vmd_quality.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_EVALUATION_DIR,
        help="Directory for CSV files and generated evaluation WAV outputs.",
    )
    parser.add_argument("--include-disabled", action="store_true")
    parser.add_argument("--skip-neossnet", action="store_true")
    return parser.parse_args()


def project_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_test_samples(max_samples: int | None) -> list[EvaluationSample]:
    if not TEST_PAIRS_PATH.is_file():
        raise FileNotFoundError(
            f"Missing HLS-CMDS test split: {TEST_PAIRS_PATH}. "
            "Run `python scripts/prepare_dataset.py` first."
        )

    samples: list[EvaluationSample] = []
    with TEST_PAIRS_PATH.open("r", encoding="utf-8", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            sample = EvaluationSample(
                mixed_id=row["mixed_id"],
                mixed_path=project_path(row["mixed_path"]),
                heart_path=project_path(row["heart_path"]),
                lung_path=project_path(row["lung_path"]),
            )
            if (
                sample.mixed_path.is_file()
                and sample.heart_path.is_file()
                and sample.lung_path.is_file()
            ):
                samples.append(sample)
            if max_samples is not None and len(samples) >= max_samples:
                break
    if not samples:
        raise RuntimeError("No complete HLS-CMDS paired test samples were found.")
    return samples


def method_to_config(model) -> SimpleNamespace:
    return SimpleNamespace(
        model_id=getattr(model, "model_id", None),
        model_name=model.model_name,
        display_name=model.display_name or model.model_name,
        version=model.version,
        architecture=model.architecture,
        framework=model.framework,
        checkpoint_path=model.checkpoint_path,
        config_path=model.config_path,
        strategy_key=model_service.strategy_key_for_model(model),
        method_type=model.method_type,
        requires_checkpoint=getattr(model, "requires_checkpoint", 0),
        is_active=getattr(model, "is_active", 1),
        is_default=getattr(model, "is_default", 0),
        description=getattr(model, "description", None),
    )


def virtual_vmd_config(strategy_key: str, base_model: SimpleNamespace | None) -> SimpleNamespace:
    quality = strategy_key == "vmd_quality"
    display_name = "VMD Decomposition (Quality)" if quality else "VMD Decomposition (Fast)"
    architecture = "VMDQuality" if quality else "VMDFast"
    return SimpleNamespace(
        model_id=None,
        model_name=display_name,
        display_name=display_name,
        version="1.0",
        architecture=architecture,
        framework=getattr(base_model, "framework", "vmdpy"),
        checkpoint_path="builtin://vmd",
        config_path=None,
        strategy_key=strategy_key,
        method_type="decomposition",
        requires_checkpoint=0,
        is_active=1,
        is_default=0,
        description="Virtual VMD preset for evaluation.",
    )


def parse_strategy_keys(raw_value: str) -> list[str] | None:
    if raw_value.strip().lower() == "all":
        return None
    keys = [
        value.strip().lower()
        for value in raw_value.split(",")
        if value.strip()
    ]
    return keys or list(DEFAULT_STRATEGIES)


def active_models(
    include_disabled: bool,
    skip_neossnet: bool,
    strategy_keys: list[str] | None,
    skip_slow: bool,
) -> list[SimpleNamespace]:
    initialize_database()
    db = SessionLocal()
    try:
        models = [method_to_config(model) for model in model_service.list_models(db)]
    finally:
        db.close()

    if not include_disabled:
        models = [model for model in models if model.is_active]

    by_strategy: dict[str, list[SimpleNamespace]] = {}
    for model in models:
        by_strategy.setdefault(model.strategy_key, []).append(model)
    base_vmd = (by_strategy.get("vmd") or by_strategy.get("vmd_fast") or [None])[0]
    for virtual_key in ("vmd_fast", "vmd_quality"):
        if virtual_key not in by_strategy:
            by_strategy[virtual_key] = [virtual_vmd_config(virtual_key, base_vmd)]

    if strategy_keys is None:
        requested = [model.strategy_key for model in models]
    else:
        requested = strategy_keys

    selected: list[SimpleNamespace] = []
    for strategy_key in requested:
        if skip_neossnet and strategy_key == "neossnet":
            continue
        if skip_slow and strategy_key in SLOW_STRATEGIES:
            continue
        selected.extend(by_strategy.get(strategy_key, []))
    return selected


def metric_lookup(metrics: list[evaluation_service.MetricRecord]) -> dict[tuple[str, str], float]:
    return {
        (metric.metric_scope, metric.metric_name): metric.metric_value
        for metric in metrics
    }


def get_metric(metrics: dict[tuple[str, str], float], scope: str, name: str) -> float | None:
    value = metrics.get((scope, name))
    if value is None or not math.isfinite(value):
        return None
    return value


def empty_row(model, sample: EvaluationSample, status: str, reason: str) -> dict[str, object]:
    strategy_key = model_service.strategy_key_for_model(model)
    row: dict[str, object] = {
        "sample_filename": sample.mixed_path.name,
        "method_key": evaluation_method_key(model),
        "strategy_key": strategy_key,
        "method_name": evaluation_display_name(model),
        "method_type": model.method_type,
        "checkpoint_path": getattr(model, "checkpoint_path", None) or "",
        "status": status,
        "processing_time_ms": "",
        "heart_output_path": "",
        "lung_output_path": "",
        "failure_reason": reason,
    }
    for field in DETAIL_FIELDS:
        row.setdefault(field, "")
    return row


def _slug(value: str) -> str:
    safe = "".join(
        character.lower() if character.isalnum() else "_"
        for character in value
    )
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_") or "method"


def evaluation_display_name(model) -> str:
    strategy_key = model_service.strategy_key_for_model(model)
    name = model.display_name or model.model_name
    checkpoint = str(getattr(model, "checkpoint_path", None) or "").replace("\\", "/")
    if strategy_key == "neossnet" and checkpoint.endswith("model_best.pt"):
        return "NeoSSNet Original"
    return name


def evaluation_method_key(model) -> str:
    strategy_key = model_service.strategy_key_for_model(model)
    return f"{strategy_key}_{_slug(evaluation_display_name(model))}"


def evaluate_one(
    model,
    sample: EvaluationSample,
    paths: EvaluationPaths,
) -> dict[str, object]:
    strategy_key = model_service.strategy_key_for_model(model)
    method_key = evaluation_method_key(model)
    method_name = evaluation_display_name(model)
    output_prefix = f"{sample.mixed_id}_{method_key}"
    heart_output = paths.audio_output_dir / method_key / f"{output_prefix}_heart.wav"
    lung_output = paths.audio_output_dir / method_key / f"{output_prefix}_lung.wav"
    heart_output.parent.mkdir(parents=True, exist_ok=True)
    lung_output.parent.mkdir(parents=True, exist_ok=True)

    row: dict[str, object] = {
        "sample_filename": sample.mixed_path.name,
        "method_key": method_key,
        "strategy_key": strategy_key,
        "method_name": method_name,
        "method_type": model.method_type,
        "checkpoint_path": getattr(model, "checkpoint_path", None) or "",
        "status": "failed",
        "processing_time_ms": "",
        "heart_output_path": "",
        "lung_output_path": "",
        "failure_reason": "",
    }

    try:
        algorithm = SeparationAlgorithmFactory.create_algorithm(model)
        model_path = (
            storage_service.resolve_project_path(model.checkpoint_path)
            if model_service.model_requires_checkpoint(model)
            else storage_service.resolve_optional_project_path(model.checkpoint_path)
        )
        model_config_path = storage_service.resolve_optional_project_path(
            model.config_path
        )
        start = time.perf_counter()
        result = algorithm.separate(
            input_wav_path=sample.mixed_path,
            model_path=model_path,
            model_config_path=model_config_path,
            heart_output_path=heart_output,
            lung_output_path=lung_output,
            device_name="cpu",
        )
        processing_time_ms = int((time.perf_counter() - start) * 1000)
        reference_pair = evaluation_service.ReferencePair(
            heart_path=sample.heart_path,
            lung_path=sample.lung_path,
            reference_type="hls_cmds_processed_test_reference",
        )
        metrics = metric_lookup(
            evaluation_service.calculate_reference_metrics(
                input_path=sample.mixed_path,
                heart_output_path=result.heart_file_path,
                lung_output_path=result.lung_file_path,
                reference_pair=reference_pair,
                sample_rate_hz=result.sample_rate_hz,
            )
        )
        row.update(
            {
                "status": "completed",
                "processing_time_ms": processing_time_ms,
                "heart_si_sdr_db": get_metric(metrics, "heart", "si_sdr"),
                "lung_si_sdr_db": get_metric(metrics, "lung", "si_sdr"),
                "heart_snr_improvement_db": get_metric(
                    metrics, "heart", "snr_improvement"
                ),
                "lung_snr_improvement_db": get_metric(
                    metrics, "lung", "snr_improvement"
                ),
                "heart_mse": get_metric(metrics, "heart", "mse"),
                "lung_mse": get_metric(metrics, "lung", "mse"),
                "heart_mae": get_metric(metrics, "heart", "mae"),
                "lung_mae": get_metric(metrics, "lung", "mae"),
                "heart_correlation": get_metric(metrics, "heart", "correlation"),
                "lung_correlation": get_metric(metrics, "lung", "correlation"),
                "heart_alignment_lag_samples": get_metric(
                    metrics,
                    "heart",
                    "alignment_lag",
                ),
                "lung_alignment_lag_samples": get_metric(
                    metrics,
                    "lung",
                    "alignment_lag",
                ),
                "heart_output_path": storage_service.relative_project_path(heart_output),
                "lung_output_path": storage_service.relative_project_path(lung_output),
            }
        )
    except Exception as error:
        row["failure_reason"] = str(error)

    for field in DETAIL_FIELDS:
        row.setdefault(field, "")
    return row


def evaluate_strategy(
    model,
    samples: list[EvaluationSample],
    paths: EvaluationPaths,
    timeout_per_strategy: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    elapsed_seconds = 0.0
    for sample in samples:
        if timeout_per_strategy > 0 and elapsed_seconds >= timeout_per_strategy:
            rows.append(
                empty_row(
                    model,
                    sample,
                    "timeout",
                    (
                        "Strategy time budget exceeded after "
                        f"{elapsed_seconds:.2f}s."
                    ),
                )
            )
            continue

        start = time.perf_counter()
        row = evaluate_one(model, sample, paths)
        elapsed_seconds += time.perf_counter() - start
        rows.append(row)
    return rows


def numeric_values(rows: list[dict[str, object]], field: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(field)
        if value in ("", None):
            continue
        numeric = float(value)
        if math.isfinite(numeric):
            values.append(numeric)
    return values


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    method_keys = sorted({str(row["method_key"]) for row in rows})
    for method_key in method_keys:
        strategy_rows = [row for row in rows if row["method_key"] == method_key]
        completed = [row for row in strategy_rows if row["status"] == "completed"]
        timeouts = [row for row in strategy_rows if row["status"] == "timeout"]
        first = strategy_rows[0]
        summary = {
            "method_key": method_key,
            "strategy_key": first["strategy_key"],
            "method_name": first["method_name"],
            "method_type": first["method_type"],
            "checkpoint_path": first["checkpoint_path"],
            "sample_count": len(strategy_rows),
            "success_count": len(completed),
            "failure_count": len(strategy_rows) - len(completed) - len(timeouts),
            "timeout_count": len(timeouts),
        }
        for detail_field in SUMMARY_NUMERIC_FIELDS:
            values = numeric_values(completed, detail_field)
            summary[f"mean_{detail_field}"] = mean(values) if values else ""
        for field in SUMMARY_FIELDS:
            summary.setdefault(field, "")
        summaries.append(summary)
    return summaries


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def display_path(path: Path) -> str:
    try:
        return storage_service.relative_project_path(path)
    except ValueError:
        return str(path)


def print_summary(summary_rows: list[dict[str, object]]) -> None:
    print("HLS-CMDS strategy evaluation")
    print("SI-SDR is in dB; higher is better.")
    print(
        "Strategy                  Samples  OK  Fail  Timeout  Heart SI-SDR  Lung SI-SDR  Time ms"
    )
    print("-" * 96)
    for row in summary_rows:
        print(
            f"{str(row['method_name'])[:25]:25} "
            f"{row['sample_count']:>7} "
            f"{row['success_count']:>3} "
            f"{row['failure_count']:>5} "
            f"{row['timeout_count']:>8} "
            f"{_fmt(row['mean_heart_si_sdr_db']):>12} "
            f"{_fmt(row['mean_lung_si_sdr_db']):>12} "
            f"{_fmt(row['mean_processing_time_ms']):>8}"
        )


def _fmt(value: object) -> str:
    if value in ("", None):
        return "-"
    return f"{float(value):.3f}"


def _largest_available_count() -> int:
    if not TEST_PAIRS_PATH.is_file():
        return 0
    with TEST_PAIRS_PATH.open("r", encoding="utf-8", newline="") as csv_file:
        return sum(1 for _ in csv.DictReader(csv_file))


def selected_max_samples(args: argparse.Namespace) -> int | None:
    if args.limit is not None:
        return args.limit
    return args.max_samples


def main() -> int:
    args = parse_args()
    paths = EvaluationPaths(output_dir=args.output_dir.resolve())
    samples = load_test_samples(selected_max_samples(args))
    strategy_keys = parse_strategy_keys(args.strategies)
    models = active_models(
        include_disabled=args.include_disabled,
        skip_neossnet=args.skip_neossnet,
        strategy_keys=strategy_keys,
        skip_slow=args.skip_slow,
    )
    if not models:
        print("No active separation strategies found.", file=sys.stderr)
        return 1

    rows: list[dict[str, object]] = []
    available_count = _largest_available_count()
    print(
        f"Running evaluation on {len(samples)} HLS-CMDS paired test samples "
        f"(available complete test rows: {available_count})."
    )
    print(
        "Strategies: "
        + ", ".join(evaluation_display_name(model) for model in models)
    )
    for model in models:
        rows.extend(
            evaluate_strategy(
                model=model,
                samples=samples,
                paths=paths,
                timeout_per_strategy=args.timeout_per_strategy,
            )
        )

    summary_rows = summarize(rows)
    write_csv(paths.details_path, rows, DETAIL_FIELDS)
    write_csv(paths.summary_path, summary_rows, SUMMARY_FIELDS)
    print_summary(summary_rows)
    print(f"Detailed results: {display_path(paths.details_path)}")
    print(f"Summary results: {display_path(paths.summary_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
