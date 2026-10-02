"""The single frozen spectral auxiliary objective for pre-T9 Treatment B."""
from __future__ import annotations

import math

import torch

from app.ml.stethofuse_tf import FFT, HOP, WINDOW_ENERGY


SPECTRAL_WEIGHT = 6.0


def spectral_log1p_loss(estimate: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Equal mean of fixed-label source-RMS-normalized log1p magnitude errors."""
    if estimate.shape != target.shape or estimate.ndim != 3 or estimate.shape[1] != 2:
        raise ValueError("Expected matching [batch,heart/lung,time] tensors")
    if not torch.isfinite(estimate).all() or not torch.isfinite(target).all():
        raise ValueError("Nonfinite source waveform")
    rho = target.square().mean(-1, keepdim=True).sqrt() + 1e-6
    window = torch.hann_window(FFT, periodic=True, device=target.device,
                               dtype=target.dtype)

    def magnitude(value: torch.Tensor) -> torch.Tensor:
        spectrum = torch.stft(value.flatten(0, 1), n_fft=FFT, hop_length=HOP,
                              win_length=FFT, window=window, center=True,
                              pad_mode="constant", normalized=False,
                              onesided=True, return_complex=True)
        return spectrum.abs() / math.sqrt(WINDOW_ENERGY)

    estimated_magnitude = magnitude(estimate / rho)
    target_magnitude = magnitude(target / rho)
    return (torch.log1p(estimated_magnitude) - torch.log1p(target_magnitude)).abs().mean()


def treatment_b_loss(estimate: torch.Tensor, target: torch.Tensor,
                     existing_loss: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    spectral = spectral_log1p_loss(estimate, target)
    return existing_loss + SPECTRAL_WEIGHT * spectral, spectral
