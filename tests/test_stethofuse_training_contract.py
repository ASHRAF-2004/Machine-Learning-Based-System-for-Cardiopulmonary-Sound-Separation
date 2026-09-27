"""Focused frozen T0-T4 training contracts; no dataset or test split access."""
from __future__ import annotations

import numpy as np
import pytest
import torch

from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_data import make_mixture, read_manifest, training_epoch
from app.ml.training_objective import fixed_label_loss, selection_score


def test_training_recipe_is_seeded_balanced_and_development_only() -> None:
    sources = read_manifest()
    first = training_epoch(sources, 0)
    assert first == training_epoch(sources, 0)
    assert len(first) == 576
    by_key = {(source.kind, source.id): source for source in sources}
    assert all(by_key[("HS", row["heart_id"])].split == "development" and
               by_key[("LS", row["lung_id"])].split == "development" for row in first)
    assert len({(r["heart_family"], r["lung_family"]) for r in first}) == 24
    for kind, id_key, family_key in (("HS", "heart_id", "heart_family"),
                                     ("LS", "lung_id", "lung_family")):
        families = {row[family_key] for row in first}
        for family in families:
            counts = [sum(row[family_key] == family and row[id_key] == source.id for row in first)
                      for source in sources if source.kind == kind and source.family == family
                      and source.split == "development"]
            assert max(counts) - min(counts) <= 1


def test_shared_mix_gain_preserves_additivity_and_peak() -> None:
    t = np.arange(32000, dtype=np.float32) / 4000
    heart = .02 * np.sin(2 * np.pi * 40 * t)
    lung = .01 * np.sin(2 * np.pi * 320 * t)
    mixture, targets, info = make_mixture(heart, lung, 3.0)
    assert np.max(np.abs(mixture - targets.sum(0))) < 1e-6
    assert np.max(np.abs(targets)) <= .950001
    assert info["relative_lung_to_heart_db"] == 3.0


def test_fixed_semantics_model_shape_consistency_and_gradients() -> None:
    torch.manual_seed(20260928)
    model = StethoFuseConvTasNet()
    x = torch.randn(2, 1, 32001) * .01
    y = model(x)
    loss = y.square().mean()
    loss.backward()
    assert model.parameter_count == 645681
    assert y.shape == (2, 2, 32001) and torch.isfinite(y).all()
    assert torch.max(torch.abs(y.sum(1, keepdim=True) - x)) < 2e-6
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())


def test_fixed_label_objective_and_validation_selection() -> None:
    target = torch.zeros(1, 2, 2048)
    time = torch.arange(2048) / 4000
    target[:, 0] = torch.sin(2 * torch.pi * 70 * time)
    target[:, 1] = .4 * torch.sin(2 * torch.pi * 500 * time)
    correct = fixed_label_loss(target.clone(), target)
    swapped = fixed_label_loss(target.flip(1), target)
    assert torch.isfinite(correct) and correct < swapped
    result = selection_score([
        {"heart_family": "h1", "lung_family": "l1", "heart_si_sdri_db": 3., "lung_si_sdri_db": 1.},
        {"heart_family": "h2", "lung_family": "l1", "heart_si_sdri_db": 5., "lung_si_sdri_db": -1.},
    ])
    assert result["heart_family_mean_si_sdri_db"] == 4
    assert result["lung_family_mean_si_sdri_db"] == 0
    assert result["selection_q_db"] == 0


def test_silent_supervised_target_is_rejected() -> None:
    with pytest.raises(ValueError, match="Silent reference"):
        fixed_label_loss(torch.zeros(1, 2, 32), torch.zeros(1, 2, 32))


def test_inference_windows_restore_length_scale_and_additivity() -> None:
    torch.manual_seed(7)
    model = StethoFuseConvTasNet().eval()
    signal = torch.randn(60001) * .02
    outputs = model.separate_recording(signal)
    assert outputs.shape == (2, signal.numel())
    assert torch.isfinite(outputs).all()
    assert torch.max(torch.abs(outputs.sum(0) - signal)) < 2e-6
