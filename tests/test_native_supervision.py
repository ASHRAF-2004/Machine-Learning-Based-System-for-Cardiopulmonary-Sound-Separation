"""Three focused native-stream checks; no real audio reads or optimizer steps."""
from copy import deepcopy
import json

import numpy as np
import pytest
import torch

from app.ml.native_supervision import (load_native_selection, materialize_native, native_recipe_prefix,
                                       select_native_rows, validate_native_plan)
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_objective import fixed_label_components
from scripts.train_stethofuse_family_refit import ROOT, file_sha256, load_eligible_metadata, snapshot


def test_metadata_fold_guard_and_frozen_native_contract() -> None:
    path = ROOT / "research/configs/pre_t9_family_refit_plan_v1.json"
    base = json.loads(path.read_text())
    plan = json.loads((ROOT / "research/configs/hls_native_pilot_v1.json").read_text())
    sources = load_eligible_metadata(base)  # Only frozen metadata; no WAV reads.
    validate_native_plan(plan, base, file_sha256(path), 576)
    for fold in base["folds"]:
        rows = load_native_selection(ROOT, plan, sources, base, fold["id"])
        assert rows
        assert all(r["heart_family"] not in fold["holdout_heart_families"] and
                   r["lung_family"] not in fold["holdout_lung_families"] for r in rows)
    assert len(load_native_selection(ROOT, plan, sources, base, "refit")) == 26
    with pytest.raises(ValueError, match="single approved"):
        validate_native_plan(dict(plan, native_loss_weight=.5), base, file_sha256(path), 576)
    qualified = json.loads((ROOT / plan["qualified_manifest"]).read_text())
    registry = json.loads((ROOT / plan["registry"]).read_text())
    bad = deepcopy(qualified)
    row = next(r for r in bad["rows"] if r["triplet_id"] in bad["selected_ids"])
    row["eligible_non_test"] = False
    with pytest.raises(ValueError, match="seal"):
        select_native_rows(bad, registry, sources, base, "refit")


def test_independent_native_rng_and_original_mixture_common_scaling() -> None:
    rows = [{"triplet_id": f"M{index:04d}", "heart_family": f"h{index % 2}",
             "lung_family": f"l{index % 3}", "gain": 2.0,
             "files": {role: {"sha256": str(index) * 64} for role in ("mixture", "heart", "lung")}}
            for index in range(1, 7)]
    np.random.seed(77)
    before = np.random.get_state()
    recipes = native_recipe_prefix(rows, 48)
    after = np.random.get_state()
    assert before[0] == after[0] and np.array_equal(before[1], after[1]) and before[2:] == after[2:]
    assert recipes == native_recipe_prefix(rows, 48)
    assert all(0 <= r["crop_start"] <= 28000 for r in recipes)
    t = np.arange(60000, dtype=np.float32) / 4000
    heart, lung = .1 * np.sin(2 * np.pi * 70 * t), .04 * np.sin(2 * np.pi * 310 * t)
    original_mix = 2 * (heart + lung) + .0002  # Preserve nonzero recording residual.
    cache = {r["triplet_id"]: np.stack((original_mix, heart, lung)) for r in rows}
    recipe = recipes[0]
    x, y, receipt = materialize_native(recipe, cache)
    start = recipe["crop_start"]
    peak = np.max(np.abs(original_mix[start:start + 32000]))
    assert x.shape == (32000,) and y.shape == (2, 32000)
    np.testing.assert_array_equal(x, original_mix[start:start + 32000] / peak)
    np.testing.assert_array_equal(y[0], 2 * heart[start:start + 32000] / peak)
    np.testing.assert_array_equal(y[1], 2 * lung[start:start + 32000] / peak)
    assert not np.array_equal(x, y.sum(0))
    assert materialize_native(receipt, cache)[2] == receipt


def test_separate_weighted_backward_and_native_resume_cursor_without_step() -> None:
    torch.set_num_threads(2)
    torch.manual_seed(20260928)
    model = StethoFuseConvTasNet("stethofuse-convtasnet-4k-small-v1")
    t = torch.arange(512) / 4000
    y = torch.stack((.1 * torch.sin(2 * torch.pi * 73 * t),
                     .04 * torch.sin(2 * torch.pi * 311 * t)))[None]
    x = y.sum(1, keepdim=True)
    synthetic = fixed_label_components(model(x), y)["loss"]
    native = fixed_label_components(model(x * .8), y * .8)["loss"]
    parameters = tuple(model.parameters())
    expected = torch.autograd.grad(synthetic + .25 * native, parameters, retain_graph=True)
    synthetic.backward()
    (.25 * native).backward()
    assert model.parameter_count == 171313
    for parameter, want in zip(parameters, expected):
        assert torch.isfinite(parameter.grad).all()
        torch.testing.assert_close(parameter.grad, want, rtol=3e-5, atol=3e-5)
    optimizer = torch.optim.AdamW(parameters, lr=.001, weight_decay=.0001)
    manifest = {"training_stage": "synthetic_contract_only", "provenance_sha256": "1" * 64,
                "provenance": {"native_plan_sha256": "2" * 64}}
    state = snapshot(model, optimizer, 0, manifest, [], 0)
    assert state["native_recipe_cursor"] == state["recipe_cursor"] == 0
    assert not state["optimizer_state_dict"]["state"]  # No optimizer step occurred.
