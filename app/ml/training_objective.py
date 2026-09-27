"""Fixed-label training loss and validation-selection aggregation."""
from __future__ import annotations

import math
import torch
from torch import Tensor


def fixed_label_si_sdr_db(estimate: Tensor, target: Tensor) -> Tensor:
    if estimate.shape != target.shape or estimate.ndim != 3 or estimate.shape[1] != 2:
        raise ValueError("Expected matching [batch, heart/lung, time] tensors")
    if not torch.isfinite(estimate).all() or not torch.isfinite(target).all():
        raise ValueError("Nonfinite estimate or target")
    t = target - target.mean(dim=-1, keepdim=True)
    v = estimate - estimate.mean(dim=-1, keepdim=True)
    energy = t.square().sum(dim=-1, keepdim=True)
    if torch.any(energy / target.shape[-1] < 1e-12):
        raise ValueError("Silent reference is invalid for SI-SDR")
    projection = (v * t).sum(dim=-1, keepdim=True) / energy * t
    residual = v - projection
    return 10.0 * torch.log10((projection.square().sum(dim=-1) + 1e-8) /
                              (residual.square().sum(dim=-1) + 1e-8))


def fixed_label_loss(estimate: Tensor, target: Tensor) -> Tensor:
    score = fixed_label_si_sdr_db(estimate, target)
    rms = target.square().mean(dim=-1).sqrt()
    normalized_l1 = (estimate - target).abs().mean(dim=-1) / (rms + 1e-6)
    return (-score + 5.0 * normalized_l1).mean()


def selection_score(pair_rows: list[dict[str, float]]) -> dict[str, float]:
    """Return per-source family-balanced means and frozen weaker-source Q."""
    if not pair_rows:
        raise ValueError("Validation rows cannot be empty")
    groups: dict[tuple[str, str], list[dict[str, float]]] = {}
    for row in pair_rows:
        groups.setdefault((row["heart_family"], row["lung_family"]), []).append(row)
    heart = sum(sum(r["heart_si_sdri_db"] for r in rows) / len(rows)
                for rows in groups.values()) / len(groups)
    lung = sum(sum(r["lung_si_sdri_db"] for r in rows) / len(rows)
               for rows in groups.values()) / len(groups)
    return {"heart_family_mean_si_sdri_db": heart,
            "lung_family_mean_si_sdri_db": lung,
            "selection_q_db": min(heart, lung),
            "tie_break_mean_db": (heart + lung) / 2.0}


def normalized_l1(estimate: Tensor, target: Tensor) -> Tensor:
    return (estimate - target).abs().mean(dim=-1) / (target.square().mean(dim=-1).sqrt() + 1e-6)
