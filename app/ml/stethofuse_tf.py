"""Frozen compact complex-mask TF separator for the pre-T9 comparison."""
from __future__ import annotations

import math

import torch
from torch import nn
from torch.nn import functional as F

from app.ml.stethofuse_tcn import StethoFuseConvTasNet


FFT = 256
HOP = 64
WINDOW_ENERGY = 96.0


def stft(waveform: torch.Tensor) -> torch.Tensor:
    window = torch.hann_window(FFT, periodic=True, device=waveform.device,
                               dtype=waveform.dtype)
    return torch.stft(waveform, n_fft=FFT, hop_length=HOP, win_length=FFT,
                      window=window, center=True, pad_mode="constant",
                      normalized=False, onesided=True, return_complex=True)


def istft(spectrum: torch.Tensor, length: int) -> torch.Tensor:
    window = torch.hann_window(FFT, periodic=True, device=spectrum.device,
                               dtype=spectrum.real.dtype)
    return torch.istft(spectrum, n_fft=FFT, hop_length=HOP, win_length=FFT,
                       window=window, center=True, normalized=False,
                       onesided=True, length=length)


class _TFBlock(nn.Module):
    def __init__(self, incoming: int, outgoing: int, second_time_dilation: int = 1):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(incoming, outgoing, 3, padding=1, bias=False),
            nn.GroupNorm(1, outgoing, eps=1e-8, affine=True), nn.SiLU(),
            nn.Conv2d(outgoing, outgoing, 3,
                      padding=(1, second_time_dilation),
                      dilation=(1, second_time_dilation), bias=False),
            nn.GroupNorm(1, outgoing, eps=1e-8, affine=True), nn.SiLU())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)


class StethoFuseComplexTFUNet(nn.Module):
    """Four-feature, 390,450-parameter heart/lung complex-mask U-Net."""

    architecture_version = "stethofuse-tfcomplex-4k-v1"
    source_order = ("heart", "lung")
    sample_rate_hz = 4000
    inference_window_samples = StethoFuseConvTasNet.inference_window_samples
    inference_hop_samples = StethoFuseConvTasNet.inference_hop_samples
    overlap_samples = StethoFuseConvTasNet.overlap_samples
    separate_recording = StethoFuseConvTasNet.separate_recording

    def __init__(self) -> None:
        super().__init__()
        widths = (8, 16, 32, 64)
        self.encoders = nn.ModuleList(
            [_TFBlock(a, b) for a, b in zip((4, *widths[:-1]), widths)])
        self.bottleneck = _TFBlock(64, 96, second_time_dilation=8)
        self.decoders = nn.ModuleList([
            _TFBlock(160, 64), _TFBlock(96, 32),
            _TFBlock(48, 16), _TFBlock(24, 8)])
        self.head = nn.Conv2d(8, 2, 1, bias=True)
        if self.parameter_count != 390450:
            raise RuntimeError(f"Frozen TF parameter count mismatch: {self.parameter_count}")

    @property
    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())

    def masks(self, spectrum: torch.Tensor) -> torch.Tensor:
        if spectrum.ndim != 3 or spectrum.shape[1] != 129:
            raise ValueError("Expected one-sided [batch,129,time] STFT")
        magnitude = spectrum.abs()
        phase_scale = magnitude.clamp_min(1e-6)
        frequency = torch.linspace(0, 1, spectrum.shape[-2], device=spectrum.device,
                                   dtype=magnitude.dtype).view(1, -1, 1).expand_as(magnitude)
        features = torch.stack((torch.log1p(magnitude / math.sqrt(WINDOW_ENERGY)),
                                spectrum.real / phase_scale,
                                spectrum.imag / phase_scale,
                                frequency), dim=1)
        frequency_bins, frames = features.shape[-2:]
        features = F.pad(features, (0, (-frames) % 16, 0, (-frequency_bins) % 16))
        skips = []
        value = features
        for block in self.encoders:
            value = block(value)
            skips.append(value)
            value = F.avg_pool2d(value, 2, stride=2)
        value = self.bottleneck(value)
        for block, skip in zip(self.decoders, reversed(skips)):
            value = value.repeat_interleave(2, dim=-2).repeat_interleave(2, dim=-1)
            value = block(torch.cat((value, skip), dim=1))
        raw = self.head(value)[..., :frequency_bins, :frames]
        interior = torch.ones_like(raw[:, 1])
        interior[:, 0] = 0
        interior[:, -1] = 0
        heart = torch.complex(0.5 + raw[:, 0], raw[:, 1] * interior)
        return torch.stack((heart, 1 - heart), dim=1)

    def forward(self, mixture: torch.Tensor) -> torch.Tensor:
        if mixture.ndim != 3 or mixture.shape[1] != 1 or mixture.shape[-1] == 0:
            raise ValueError("Expected [batch,1,nonempty time] mixture")
        if not torch.isfinite(mixture).all():
            raise ValueError("Mixture contains nonfinite values")
        length = mixture.shape[-1]
        spectrum = stft(mixture[:, 0])
        masks = self.masks(spectrum)
        masked = masks * spectrum[:, None]
        raw = istft(masked.flatten(0, 1), length).reshape(mixture.shape[0], 2, length)
        output = raw + (mixture - raw.sum(dim=1, keepdim=True)) / 2
        if output.shape != (mixture.shape[0], 2, length) or not torch.isfinite(output).all():
            raise RuntimeError("TF model violated its finite shape contract")
        return output
