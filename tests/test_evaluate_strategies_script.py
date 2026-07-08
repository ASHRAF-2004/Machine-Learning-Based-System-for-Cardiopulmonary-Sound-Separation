from __future__ import annotations

import csv
from types import SimpleNamespace

from scripts import evaluate_strategies


def _completed_row(sample_name: str = "M0001.wav") -> dict[str, object]:
    return {
        "sample_filename": sample_name,
        "method_key": "fixed_filter_fixed_filter_baseline",
        "strategy_key": "fixed_filter",
        "method_name": "Fixed Filter Baseline",
        "method_type": "baseline",
        "checkpoint_path": "builtin://fixed_filter",
        "status": "completed",
        "processing_time_ms": 10,
        "heart_si_sdr_db": 1.0,
        "lung_si_sdr_db": 2.0,
        "heart_snr_improvement_db": 0.5,
        "lung_snr_improvement_db": 0.6,
        "heart_mse": 0.01,
        "lung_mse": 0.02,
        "heart_mae": 0.03,
        "lung_mae": 0.04,
        "heart_correlation": 0.8,
        "lung_correlation": 0.7,
        "heart_output_path": "evaluation/outputs/heart.wav",
        "lung_output_path": "evaluation/outputs/lung.wav",
        "failure_reason": "",
    }


def test_evaluate_strategies_writes_detail_and_summary_csv(tmp_path, monkeypatch) -> None:
    samples = [SimpleNamespace(mixed_path=tmp_path / "M0001.wav")]
    monkeypatch.setattr(evaluate_strategies, "load_test_samples", lambda max_samples: samples)
    monkeypatch.setattr(evaluate_strategies, "_largest_available_count", lambda: 1)
    monkeypatch.setattr(
        evaluate_strategies,
        "active_models",
        lambda include_disabled, skip_neossnet, strategy_keys, skip_slow: [
            SimpleNamespace(
                strategy_key="fixed_filter",
                display_name="Fixed Filter Baseline",
                model_name="Fixed Filter Baseline",
                method_type="baseline",
            )
        ],
    )
    monkeypatch.setattr(
        evaluate_strategies,
        "evaluate_strategy",
        lambda model, samples, paths, timeout_per_strategy: [_completed_row()],
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "evaluate_strategies.py",
            "--max-samples",
            "1",
            "--strategies",
            "fixed_filter",
            "--output-dir",
            str(tmp_path),
        ],
    )

    exit_code = evaluate_strategies.main()

    details_path = tmp_path / "results_strategy_comparison.csv"
    summary_path = tmp_path / "summary_strategy_comparison.csv"
    assert exit_code == 0
    assert details_path.is_file()
    assert summary_path.is_file()
    assert "fixed_filter" in details_path.read_text(encoding="utf-8")
    assert "mean_heart_si_sdr_db" in summary_path.read_text(encoding="utf-8")


def test_evaluate_strategies_accepts_more_than_three_samples(tmp_path, monkeypatch) -> None:
    requested_counts: list[int | None] = []

    def fake_load_test_samples(max_samples):
        requested_counts.append(max_samples)
        return [
            SimpleNamespace(mixed_path=tmp_path / f"M{index:04d}.wav")
            for index in range(4)
        ]

    monkeypatch.setattr(evaluate_strategies, "load_test_samples", fake_load_test_samples)
    monkeypatch.setattr(evaluate_strategies, "_largest_available_count", lambda: 4)
    monkeypatch.setattr(
        evaluate_strategies,
        "active_models",
        lambda include_disabled, skip_neossnet, strategy_keys, skip_slow: [
            SimpleNamespace(
                strategy_key="fixed_filter",
                display_name="Fixed Filter Baseline",
                model_name="Fixed Filter Baseline",
                method_type="baseline",
            )
        ],
    )

    def fake_evaluate_strategy(model, samples, paths, timeout_per_strategy):
        return [
            _completed_row(sample.mixed_path.name)
            for sample in samples
        ]

    monkeypatch.setattr(evaluate_strategies, "evaluate_strategy", fake_evaluate_strategy)
    monkeypatch.setattr(
        "sys.argv",
        [
            "evaluate_strategies.py",
            "--max-samples",
            "4",
            "--strategies",
            "fixed_filter",
            "--output-dir",
            str(tmp_path),
        ],
    )

    exit_code = evaluate_strategies.main()

    with (tmp_path / "results_strategy_comparison.csv").open(
        "r",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert exit_code == 0
    assert requested_counts == [4]
    assert len(rows) == 4


def test_evaluate_summary_keeps_original_and_finetuned_neossnet_separate() -> None:
    original = _completed_row("M0001.wav")
    original.update(
        {
            "method_key": "neossnet_neossnet_original",
            "strategy_key": "neossnet",
            "method_name": "NeoSSNet Original",
            "method_type": "deep_learning",
            "checkpoint_path": "storage/ml_models/model_best.pt",
        }
    )
    fine_tuned = _completed_row("M0001.wav")
    fine_tuned.update(
        {
            "method_key": "neossnet_neossnet_hls_fine_tuned",
            "strategy_key": "neossnet",
            "method_name": "NeoSSNet HLS Fine-tuned",
            "method_type": "deep_learning",
            "checkpoint_path": "storage/ml_models/neossnet_hls_finetuned.pt",
        }
    )

    summary = evaluate_strategies.summarize([original, fine_tuned])

    assert len(summary) == 2
    assert {row["method_name"] for row in summary} == {
        "NeoSSNet Original",
        "NeoSSNet HLS Fine-tuned",
    }
