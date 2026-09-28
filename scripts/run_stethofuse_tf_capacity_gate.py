"""Run the one frozen 400-update development-only capacity gate for Treatment A."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import random
import resource
import subprocess
import sys
import time

import numpy as np
import torch
import torchaudio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.stethofuse_tf import StethoFuseComplexTFUNet
from app.ml.training_data import read_manifest, read_source, make_mixture, sha256_file
from app.ml.training_objective import fixed_label_loss, fixed_label_si_sdr_db, normalized_l1
from scripts.train_stethofuse_representation import (ARTIFACT_ROOT, PLAN, PLAN_SHA,
                                                      check_integrity, file_sha256,
                                                      atomic_json, state_sha256)

SEED = 20260928
PAIRS = (("F_AF_A", "F_N_LLA"), ("F_ESM_LLSB", "F_PR_LLA"))
RUN_ID = "tf-capacity-seed20260928"


def main() -> None:
    started = time.perf_counter()
    git = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise RuntimeError("Capacity gate requires clean committed implementation")
    plan = json.loads(PLAN.read_text())
    rows, _ = check_integrity(plan)
    target_dir = ARTIFACT_ROOT / RUN_ID
    if target_dir.exists():
        raise FileExistsError("Capacity-gate artifact already exists; refusing overwrite/re-run")
    sources = {(s.kind, s.id): s for s in rows if s.split == "development"}
    requested = {(kind, source_id) for pair in PAIRS for kind, source_id in zip(("HS", "LS"), pair)}
    if set(sources.keys()) & requested != requested:
        raise RuntimeError("Capacity-gate pair sources absent from frozen allowlist")
    waveforms, source_hashes = {}, {}
    for key in sorted(requested):
        source = sources[key]
        if sha256_file(source.path) != source.sha256:
            raise RuntimeError("Capacity-gate development source hash mismatch")
        waveforms[key] = read_source(source)
        source_hashes[f"{key[0]}/{key[1]}"] = source.sha256
    mixtures, targets, baselines = [], [], []
    for heart_id, lung_id in PAIRS:
        mixture, target, _ = make_mixture(waveforms[("HS", heart_id)],
                                          waveforms[("LS", lung_id)], 0.0,
                                          heart_start=0, lung_start=0, crop_samples=32000)
        scale = float(np.max(np.abs(mixture)))
        mixture = mixture / scale
        target = target / scale
        mixtures.append(mixture); targets.append(target)
        baselines.append(mixture)
    x = torch.from_numpy(np.stack(mixtures)[:, None]).float()
    y = torch.from_numpy(np.stack(targets)).float()
    mixture_sources = x.expand(-1, 2, -1).contiguous()
    baseline_l1 = normalized_l1(mixture_sources, y).detach()

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    model = StethoFuseComplexTFUNet().cpu()
    if model.parameter_count != 390450:
        raise RuntimeError("A capacity-gate parameter count mismatch")
    initial_hash = state_sha256(model)
    if initial_hash != "8d617e4199c55ce0f0e1502ca7413305e1600c701f70e585f6dd41bd1584d687":
        raise RuntimeError("A capacity-gate fresh initialization hash mismatch")
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, betas=(.9, .999),
                                  eps=1e-8, weight_decay=0.0)
    records = []

    def evaluate(update: int) -> bool:
        model.eval()
        with torch.inference_mode():
            output = model(x)
            improvement = fixed_label_si_sdr_db(output, y) - fixed_label_si_sdr_db(mixture_sources, y)
            current_l1 = normalized_l1(output, y)
            reduction = 1.0 - current_l1 / baseline_l1.clamp_min(1e-12)
        rows_out = []
        for case, (heart_id, lung_id) in enumerate(PAIRS):
            for source, label, idx in ((heart_id, "heart", 0), (lung_id, "lung", 1)):
                rows_out.append({"case": f"{heart_id}/{lung_id}", "heart_id": heart_id,
                                 "lung_id": lung_id, "source": label,
                                 "sdri_db": float(improvement[case, idx]),
                                 "normalized_l1_reduction": float(reduction[case, idx])})
        if not all(math.isfinite(row["sdri_db"]) and math.isfinite(row["normalized_l1_reduction"])
                   for row in rows_out):
            raise RuntimeError("Nonfinite capacity-gate metric")
        records.append({"optimizer_updates": update, "sources": rows_out,
                        "runtime_seconds": time.perf_counter() - started})
        model.train()
        return all(row["sdri_db"] >= 10.0 and row["normalized_l1_reduction"] >= .50
                   for row in rows_out)

    passed_at = 0 if evaluate(0) else None
    for update in range(1 if passed_at is None else 401, 401):
        optimizer.zero_grad(set_to_none=True)
        prediction = model(x)
        loss = fixed_label_loss(prediction, y)
        if not torch.isfinite(loss):
            raise RuntimeError("Nonfinite capacity-gate loss")
        loss.backward()
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
            raise RuntimeError("Nonfinite capacity-gate gradient")
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0, error_if_nonfinite=True)
        optimizer.step()
        if not all(torch.isfinite(p).all() for p in model.parameters()):
            raise RuntimeError("Nonfinite capacity-gate parameter")
        if update % 20 == 0:
            print(json.dumps({"optimizer_updates": update, "loss": float(loss.detach()),
                              "gradient_norm_before_clip": float(grad_norm),
                              "runtime_seconds": time.perf_counter() - started}, sort_keys=True), flush=True)
            if evaluate(update):
                passed_at = update
                break
        if time.perf_counter() - started > 600:
            break
    passed = passed_at is not None
    target_dir.mkdir(parents=True)
    endpoint = target_dir / "capacity-evidence.pt"
    torch.save({"architecture_version": model.architecture_version,
                "parameter_count": model.parameter_count, "state_dict": model.state_dict(),
                "updates": records[-1]["optimizer_updates"]}, endpoint)
    receipt = {"status": "PASS" if passed else "FAIL", "run_id": RUN_ID,
               "git_commit": git, "plan_sha256": PLAN_SHA, "seed": SEED,
               "pairs": PAIRS, "source_hashes": source_hashes,
               "parameter_count": model.parameter_count,
               "initial_state_sha256": initial_hash,
               "updates_completed": records[-1]["optimizer_updates"],
               "passed_at_update": passed_at, "criteria": {
                   "every_case_source_si_sdri_min_db": 10.0,
                   "every_case_source_normalized_l1_reduction_min_fraction": 0.50,
                   "max_updates": 400, "max_seconds": 600},
               "history": records, "checkpoint_sha256": file_sha256(endpoint),
               "runtime_seconds": time.perf_counter() - started,
               "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
               "test_access": False, "validation_access": False,
               "checkpoint_reuse_for_grouped_training": False,
               "created_utc": datetime.now(timezone.utc).isoformat()}
    atomic_json(target_dir / "gate.json", receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != "history"}, indent=2))


if __name__ == "__main__":
    main()
