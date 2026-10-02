"""Allowlisted metadata plus one disposable synthetic step; no WAV/data experiments."""
from dataclasses import replace
import json

import numpy as np
import pytest
import torch

from scripts.train_stethofuse_family_refit import (
    ROOT, SEED, load_eligible_metadata, partition_sources, prepare_fold_manifest, snapshot,
    training_prefix, validate_initialization, validate_plan, validate_sources,
)
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_objective import fixed_label_loss, selection_score
from scripts.train_stethofuse_baseline import atomic_torch_save, state_sha256


def test_family_manifest_partitions_and_deterministic_recipe_prefix(tmp_path) -> None:
    plan = json.loads((ROOT / "research/configs/pre_t9_family_refit_plan_v1.json").read_text())
    validate_plan(plan, 1152)
    sources = load_eligible_metadata(plan)  # Metadata only: no source hash/audio opens.
    for fold in plan["folds"]:
        train, val = partition_sources(sources, plan, fold["id"])
        assert not {(s.kind, s.id) for s in train} & {(s.kind, s.id) for s in val}
        assert not {(s.kind, s.family) for s in train} & {(s.kind, s.family) for s in val}
        recipes = training_prefix(train, 576)
        assert recipes == training_prefix(train, 576)
        assert len(recipes) == 2304 and recipes[0]["virtual_epoch"] == 0
        train_keys = {(s.kind, s.id) for s in train}
        assert all(("HS", r["heart_id"]) in train_keys and ("LS", r["lung_id"]) in train_keys for r in recipes)
        assert len({(r["heart_family"], r["lung_family"]) for r in recipes}) == fold["train_family_pairs"]
    all_train, no_holdout = partition_sources(sources, plan, "refit")
    assert len(all_train) == 86 and no_holdout == []
    artifact = prepare_fold_manifest(plan, tmp_path / "folds.csv")
    assert artifact["rows"] == 86 and artifact["audio_opened"] is False
    assert artifact == prepare_fold_manifest(plan, tmp_path / "folds.csv")


def test_locked_metadata_unapproved_budget_and_policy_changes_fail_closed() -> None:
    plan = json.loads((ROOT / "research/configs/pre_t9_family_refit_plan_v1.json").read_text())
    sources = load_eligible_metadata(plan)
    forbidden = [replace(sources[0], split="test"), *sources[1:]]
    with pytest.raises(ValueError, match="non-test"):
        validate_sources(forbidden, plan)
    with pytest.raises(ValueError, match="Locked"):
        partition_sources(forbidden, plan, "refit")
    with pytest.raises(ValueError, match="budget"):
        validate_plan(plan, 144)
    with pytest.raises(ValueError, match="contract"):
        validate_plan(dict(plan, test_access_allowed=True), 576)
    with pytest.raises(ValueError, match="Fresh-only"):
        validate_initialization(plan, ROOT / "synthetic.pt", "1" * 64)
    with pytest.raises(ValueError, match="Fresh refit"):
        validate_initialization(plan, None, None, {"initialization_checkpoint_sha256": None})
    treatment = dict(plan, initialization="external_pretraining_endpoint",
                     initialization_checkpoint_sha256="1" * 64,
                     cv_max_optimizer_updates_per_fold=864, cv_evaluation_updates=[864])
    validate_plan(treatment, 864)
    validate_initialization(treatment, ROOT / "synthetic.pt", "1" * 64,
                            {"initialization_checkpoint_sha256": "1" * 64})
    with pytest.raises(ValueError, match="endpoint"):
        validate_plan(dict(treatment, cv_evaluation_updates=[576, 864]), 864)
    with pytest.raises(ValueError, match="hash frozen"):
        validate_initialization(treatment, ROOT / "synthetic.pt", "2" * 64)
    with pytest.raises(ValueError, match="receipt"):
        validate_initialization(treatment, ROOT / "synthetic.pt", "1" * 64, {})


def test_synthetic_model_snapshot_resume_and_eight_group_macro(tmp_path) -> None:
    # One disposable synthetic optimizer update, not a capacity or data experiment.
    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    model = StethoFuseConvTasNet("stethofuse-convtasnet-4k-small-v1")
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.0001)
    t = torch.arange(1024) / 4000
    target = torch.stack((.1 * torch.sin(2 * torch.pi * 70 * t),
                          .05 * torch.sin(2 * torch.pi * 330 * t)))[None]
    mixture = target.sum(1, keepdim=True)
    output = model(mixture)
    assert model.parameter_count == 171313 and output.shape == (1, 2, 1024)
    assert torch.max(torch.abs(output.sum(1, keepdim=True) - mixture)) < 1e-6
    loss = fixed_label_loss(output, target)
    assert torch.isfinite(loss)
    loss.backward()
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())
    torch.nn.utils.clip_grad_norm_(model.parameters(), 5, error_if_nonfinite=True)
    optimizer.step()
    manifest = {"training_stage": "synthetic_contract_only", "provenance_sha256": "1" * 64}
    state = snapshot(model, optimizer, 1, manifest, [{"loss": float(loss.detach())}], .1)
    atomic_torch_save(state, tmp_path / "synthetic.pt")
    expected_next_random = torch.rand(3)
    restored = StethoFuseConvTasNet(model.architecture_version)
    restored_optimizer = torch.optim.AdamW(restored.parameters(), lr=.001, weight_decay=.0001)
    loaded = torch.load(tmp_path / "synthetic.pt", weights_only=False)
    restored.load_state_dict(loaded["state_dict"], strict=True)
    restored_optimizer.load_state_dict(loaded["optimizer_state_dict"])
    torch.set_rng_state(loaded["torch_rng_state"])
    assert torch.equal(torch.rand(3), expected_next_random)
    assert state_sha256(restored) == state_sha256(model)
    assert loaded["recipe_cursor"] == 4 and restored_optimizer.state
    assert restored_optimizer.param_groups[0]["lr"] == .001
    rows = [{"heart_family": f"h{i}", "lung_family": f"l{i % 5}",
             "heart_si_sdri_db": float(i), "lung_si_sdri_db": float(7 - i)}
            for i in range(8) for _ in range(i + 1)]
    score = selection_score(rows)
    assert score["selection_q_db"] == score["tie_break_mean_db"] == 3.5
    assert not np.isclose(np.mean([row["heart_si_sdri_db"] for row in rows]), 3.5)
