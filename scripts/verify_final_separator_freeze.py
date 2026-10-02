"""Metadata/checkpoint and synthetic-only v2 smoke. Never discovers/opens audio."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import scipy
import torch
import torchaudio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.stethofuse_tcn import StethoFuseConvTasNet


def sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main() -> None:
    spec_path = "research/configs/final_separator_v2.json"
    spec = json.loads((ROOT / spec_path).read_text())
    old_path = "research/configs/final_separator_v1.json"
    old = json.loads((ROOT / old_path).read_text())
    assert sha(old_path) == spec["supersedes_before_t9"]["specification_sha256"]
    assert sha(old["model"]["checkpoint_path_ignored_local"]) == old["model"]["checkpoint_sha256"]
    assert spec["t9_protocol"] == old["t9_protocol"]
    assert spec["signal_and_inference"] == old["signal_and_inference"]
    assert spec["status"] == "FROZEN_FOR_HELD_OUT_TEST"
    model_spec = spec["model"]
    for item in spec["t9_protocol"]["frozen_code_sources"].values():
        assert sha(item["path"]) == item["sha256"], item["path"]
    assert sha(model_spec["configuration_path"]) == model_spec["configuration_sha256"]
    provenance = model_spec["training_provenance"]
    for key in ("plan", "authorization", "grouped_validation_manifest", "budget_decision", "external_rejection"):
        assert sha(provenance[key + "_path"]) == provenance[key + "_sha256"], key
    for key in ("training_manifest", "run_manifest"):
        assert sha(provenance[key + "_path_ignored_local"]) == provenance[key + "_sha256"], key
    recipe = model_spec["training_recipe_set"]
    assert sha(recipe["path_ignored_local"]) == recipe["file_sha256"]
    assert sha(model_spec["checkpoint_path_ignored_local"]) == model_spec["checkpoint_sha256"]
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    environment = {"python": platform.python_version(), "torch": torch.__version__,
                   "torchaudio": torchaudio.__version__, "numpy": np.__version__,
                   "scipy": scipy.__version__, "device": "cpu"}
    assert all(spec["environment"][key] == value for key, value in environment.items())
    # This is our hash-verified local training artifact, not an untrusted pickle.
    checkpoint = torch.load(ROOT / model_spec["checkpoint_path_ignored_local"],
                            map_location="cpu", weights_only=False)
    assert checkpoint["architecture_version"] == model_spec["architecture_version"]
    assert checkpoint["parameter_count"] == model_spec["parameter_count"] == 171313
    assert checkpoint["optimizer_updates"] == model_spec["selected_optimizer_updates"] == 576
    model = StethoFuseConvTasNet(model_spec["architecture_version"]).eval()
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    assert list(model.source_order) == spec["signal_and_inference"]["source_order"]
    # Odd length exercises last-window right padding, overlap, and exact trim.
    time = torch.arange(60001, dtype=torch.float32) / 4000
    synthetic = .25 * torch.sin(2 * torch.pi * 73 * time) + .1 * torch.cos(2 * torch.pi * 317 * time)
    output = model.separate_recording(synthetic)
    error = float((output.sum(0) - synthetic).abs().max())
    assert output.shape == (2, 60001) and torch.isfinite(output).all()
    assert error < 1e-6
    silent = model.separate_recording(torch.zeros(1001))
    assert silent.shape == (2, 1001) and not torch.any(silent)
    result = {"status": "PASS", "spec_path": spec_path, "spec_sha256": sha(spec_path),
              "checkpoint_sha256": model_spec["checkpoint_sha256"],
              "parameter_count": model.parameter_count, "strict_load": True,
              "synthetic_shape": list(output.shape), "finite": True,
              "maximum_mixture_consistency_error": error, "zero_input_check": True,
              "source_order_configured": list(model.source_order),
              "semantics_note": "Configured fixed labels verified; synthetic smoke is not semantic accuracy evidence",
              "environment": environment, "v1_preserved": True,
              "inference_and_t9_protocol_unchanged": True,
              "metadata_hash_checks": "PASS", "audio_files_opened": 0,
              "optimizer_updates": 0, "test_access": False, "production_access": False,
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "worktree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
              "probe_source_sha256": sha("scripts/verify_final_separator_freeze.py")}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
