from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.ml.audio_utils import is_effectively_silent, load_wav_mono, save_wav_mono
from app.ml.strategies.fixed_filter_strategy import FixedFilterSeparationStrategy
from app.ml.strategies.nmf_strategy import NmfSeparationStrategy
from app.ml.strategies.vmd_strategy import (
    VmdQualitySeparationStrategy,
    VmdSeparationStrategy,
)


def create_synthetic_mix(path: Path, duration_sec: float = 1.0) -> None:
    sample_rate_hz = 4000
    time_axis = np.arange(int(sample_rate_hz * duration_sec), dtype=np.float32)
    time_axis /= sample_rate_hz
    heart_like = 0.55 * np.sin(2 * np.pi * 80.0 * time_axis)
    lung_like = 0.28 * np.sin(2 * np.pi * 650.0 * time_axis)
    save_wav_mono(path, heart_like + lung_like, sample_rate_hz)


def assert_playable_not_silent(path: Path, expected_sample_rate_hz: int = 4000) -> None:
    assert path.is_file()
    audio = load_wav_mono(path)
    assert audio.sample_rate_hz == expected_sample_rate_hz
    assert audio.duration_sec > 0
    assert not is_effectively_silent(audio.waveform)


def run_strategy(strategy, tmp_path: Path, duration_sec: float = 1.0) -> tuple[Path, Path]:
    input_path = tmp_path / "mixed.wav"
    heart_path = tmp_path / "heart.wav"
    lung_path = tmp_path / "lung.wav"
    create_synthetic_mix(input_path, duration_sec=duration_sec)

    result = strategy.separate(
        input_wav_path=input_path,
        model_path=None,
        model_config_path=None,
        heart_output_path=heart_path,
        lung_output_path=lung_path,
        device_name="cpu",
    )

    assert result.output_shape[1] == 2
    assert result.metadata["method_type"] in {"baseline", "decomposition"}
    return heart_path, lung_path


def test_fixed_filter_strategy_writes_playable_outputs(tmp_path: Path) -> None:
    heart_path, lung_path = run_strategy(FixedFilterSeparationStrategy(), tmp_path)

    assert_playable_not_silent(heart_path)
    assert_playable_not_silent(lung_path)


def test_nmf_strategy_writes_playable_outputs(tmp_path: Path) -> None:
    strategy = NmfSeparationStrategy(n_components=4, iterations=8)

    heart_path, lung_path = run_strategy(strategy, tmp_path)

    assert_playable_not_silent(heart_path)
    assert_playable_not_silent(lung_path)


def test_vmd_strategy_writes_playable_outputs(tmp_path: Path) -> None:
    pytest.importorskip("vmdpy")
    strategy = VmdSeparationStrategy(mode_count=3, segment_seconds=2.0)

    heart_path, lung_path = run_strategy(strategy, tmp_path, duration_sec=0.6)

    assert_playable_not_silent(heart_path)
    assert_playable_not_silent(lung_path)


def test_vmd_fast_preset_records_speed_controls(tmp_path: Path) -> None:
    pytest.importorskip("vmdpy")
    strategy = VmdSeparationStrategy()
    input_path = tmp_path / "mixed.wav"
    heart_path = tmp_path / "heart.wav"
    lung_path = tmp_path / "lung.wav"
    create_synthetic_mix(input_path, duration_sec=0.8)

    result = strategy.separate(
        input_wav_path=input_path,
        model_path=None,
        model_config_path=None,
        heart_output_path=heart_path,
        lung_output_path=lung_path,
        device_name="cpu",
    )

    assert result.metadata["vmd_preset"] == "fast"
    assert result.metadata["vmd_internal_sample_rate_hz"] == 1000
    assert result.metadata["vmd_processing_time_ms"] >= 0


def test_vmd_quality_preset_records_quality_controls(tmp_path: Path) -> None:
    pytest.importorskip("vmdpy")
    strategy = VmdQualitySeparationStrategy()
    input_path = tmp_path / "mixed.wav"
    heart_path = tmp_path / "heart.wav"
    lung_path = tmp_path / "lung.wav"
    create_synthetic_mix(input_path, duration_sec=0.2)

    result = strategy.separate(
        input_wav_path=input_path,
        model_path=None,
        model_config_path=None,
        heart_output_path=heart_path,
        lung_output_path=lung_path,
        device_name="cpu",
    )

    assert result.metadata["vmd_preset"] == "quality"
    assert result.metadata["vmd_internal_sample_rate_hz"] == 2000


def test_vmd_strategy_uses_safe_fallback_for_long_audio(tmp_path: Path) -> None:
    strategy = VmdSeparationStrategy(
        mode_count=3,
        segment_seconds=1.0,
        max_vmd_duration_seconds=0.5,
    )
    input_path = tmp_path / "mixed.wav"
    heart_path = tmp_path / "heart.wav"
    lung_path = tmp_path / "lung.wav"
    create_synthetic_mix(input_path, duration_sec=1.0)

    result = strategy.separate(
        input_wav_path=input_path,
        model_path=None,
        model_config_path=None,
        heart_output_path=heart_path,
        lung_output_path=lung_path,
        device_name="cpu",
    )

    assert result.metadata["vmd_fallback_used"] is True
    assert "duration limit" in result.metadata["vmd_fallback_reason"]
    assert_playable_not_silent(heart_path)
    assert_playable_not_silent(lung_path)
