"""Focused offline ensemble regressions; no model or patient audio required."""
from __future__ import annotations

import numpy as np
import pytest

from app.ml.ensemble_v1 import EnsembleEngine, EnsembleError, canonicalize, fuse_window
from app.ml.strategies.base import SeparatedWaveforms
from scripts.evaluate_ensemble_qualification import si_sdr


def test_canonical_resampling_and_mono_contract() -> None:
    stereo = np.stack((np.ones(2205, dtype=np.float32) * 0.2,
                       np.ones(2205, dtype=np.float32) * 0.4))
    result = canonicalize(stereo, 22050)
    assert result.shape == (400,)
    assert np.isfinite(result).all()
    assert np.median(result[10:-10]) == pytest.approx(0.3, abs=1e-3)


def test_complementary_mask_fusion_is_finite_and_mixture_consistent() -> None:
    time = np.arange(40000, dtype=np.float32) / 4000
    heart = (0.2 * np.sin(2 * np.pi * 80 * time)).astype(np.float32)
    lung = (0.1 * np.sin(2 * np.pi * 600 * time)).astype(np.float32)
    mixture = heart + lung
    first = SeparatedWaveforms(heart, lung, 4000)
    second = SeparatedWaveforms(heart * 0.7, lung * 1.3, 4000)
    output = fuse_window(mixture, first, second)
    estimated_heart, estimated_lung = output["ensemble"]
    assert np.isfinite(estimated_heart).all() and np.isfinite(estimated_lung).all()
    assert np.max(np.abs(estimated_heart + estimated_lung - mixture)) <= 1e-5
    assert np.array_equal(estimated_heart, fuse_window(mixture, first, second)["ensemble"][0])


def test_bad_required_expert_fails_instead_of_falling_back() -> None:
    class Good:
        id = "good"
        device = "cpu"

        def separate(self, window):
            return SeparatedWaveforms(window * 0.5, window * 0.5, 4000)

    class Bad:
        id = "bad"

        def separate(self, window):
            return SeparatedWaveforms(np.full_like(window, np.nan), window, 4000)

    mixture = np.full(40000, 0.2, dtype=np.float32)
    with pytest.raises(EnsembleError, match="required_expert_or_fusion_failed") as failure:
        EnsembleEngine(Good(), Bad()).separate(mixture)
    assert failure.value.provenance["status"] == "failed_offline"
    assert failure.value.provenance["fallback_events"] == []


def test_two_window_overlap_preserves_mixture_edges() -> None:
    class Half:
        id = "controlled"
        device = "cpu"

        def separate(self, window):
            return SeparatedWaveforms(window * 0.5, window * 0.5, 4000)

    time = np.arange(72001, dtype=np.float32) / 4000
    mixture = 0.2 * np.sin(2 * np.pi * 80 * time)
    result = EnsembleEngine(Half(), Half()).separate(mixture)
    assert result.heart.shape == mixture.shape
    assert np.max(np.abs(result.heart + result.lung - mixture)) <= 1e-5
    assert result.provenance["window_count"] == 3


def test_si_sdr_is_mean_centered_and_gain_invariant() -> None:
    time = np.arange(4000, dtype=np.float32) / 4000
    target = np.sin(2 * np.pi * 80 * time)
    interference = np.sin(2 * np.pi * 500 * time)
    baseline = si_sdr(target + interference, target)
    improved = si_sdr(3 * target + 0.3 * interference + 4, target)
    assert improved - baseline == pytest.approx(20.0, abs=0.05)
