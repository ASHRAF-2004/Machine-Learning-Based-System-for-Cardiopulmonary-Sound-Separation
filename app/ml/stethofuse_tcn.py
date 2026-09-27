"""Offline-only compact StethoFuse Conv-TasNet and target-free consistency."""
from __future__ import annotations

import torch
from torch import nn
import torchaudio


class StethoFuseConvTasNet(nn.Module):
    architecture_version = "stethofuse-convtasnet-4k-v1"
    source_order = ("heart", "lung")
    stride = 16

    def __init__(self) -> None:
        super().__init__()
        self.separator = torchaudio.models.ConvTasNet(
            num_sources=2, enc_kernel_size=32, enc_num_feats=128,
            msk_kernel_size=3, msk_num_feats=64, msk_num_hidden_feats=128,
            msk_num_layers=8, msk_num_stacks=3, msk_activate="relu")

    @property
    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())

    def forward(self, mixture: torch.Tensor) -> torch.Tensor:
        if mixture.ndim != 3 or mixture.shape[1] != 1 or mixture.shape[-1] == 0:
            raise ValueError("Expected [batch, 1, nonempty time] mixture")
        if not torch.isfinite(mixture).all():
            raise ValueError("Mixture contains nonfinite values")
        length = mixture.shape[-1]
        pad = (-length) % self.stride
        padded = torch.nn.functional.pad(mixture, (0, pad)) if pad else mixture
        raw = self.separator(padded)
        raw = raw[..., :length]
        # Equal residual projection: no target/reference enters this operation.
        residual = mixture - raw.sum(dim=1, keepdim=True)
        output = raw + residual / 2.0
        if output.shape != (mixture.shape[0], 2, length) or not torch.isfinite(output).all():
            raise RuntimeError("Conv-TasNet produced invalid output contract")
        return output
