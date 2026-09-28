"""Offline-only compact StethoFuse Conv-TasNet and target-free consistency."""
from __future__ import annotations

import torch
from torch import nn
import torchaudio


class StethoFuseConvTasNet(nn.Module):
    architecture_version = "stethofuse-convtasnet-4k-v1"
    source_order = ("heart", "lung")
    profiles = {
        "stethofuse-convtasnet-4k-v1": {
            "enc_num_feats": 128, "msk_num_feats": 64,
            "msk_num_hidden_feats": 128, "parameter_count": 645681},
        "stethofuse-convtasnet-4k-small-v1": {
            "enc_num_feats": 64, "msk_num_feats": 32,
            "msk_num_hidden_feats": 64, "parameter_count": 171313},
    }
    stride = 16
    sample_rate_hz = 4000
    inference_window_samples = 40000
    inference_hop_samples = 32000
    overlap_samples = inference_window_samples - inference_hop_samples

    def __init__(self, architecture_version: str | None = None) -> None:
        super().__init__()
        version = architecture_version or type(self).architecture_version
        if version not in self.profiles:
            raise ValueError(f"Unsupported StethoFuse Conv-TasNet profile: {version}")
        self.architecture_version = version
        profile = self.profiles[version]
        self.separator = torchaudio.models.ConvTasNet(
            num_sources=2, enc_kernel_size=32, enc_num_feats=profile["enc_num_feats"],
            msk_kernel_size=3, msk_num_feats=profile["msk_num_feats"],
            msk_num_hidden_feats=profile["msk_num_hidden_feats"],
            msk_num_layers=8, msk_num_stacks=3, msk_activate="relu")
        if self.parameter_count != profile["parameter_count"]:
            raise RuntimeError(f"Profile {version} parameter count mismatch: {self.parameter_count}")

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

    @torch.inference_mode()
    def separate_recording(self, waveform: torch.Tensor) -> torch.Tensor:
        """Separate one 4-kHz mono record with frozen 10-s/8-s overlap policy.

        Returns `[heart, lung, time]` in the input's original shared scale.
        Windowing and scaling do not use references or per-source normalization.
        """
        if waveform.ndim == 2 and waveform.shape[0] == 1:
            waveform = waveform[0]
        if waveform.ndim != 1 or waveform.numel() == 0 or not torch.isfinite(waveform).all():
            raise ValueError("Expected finite nonempty mono waveform")
        waveform = waveform.to(dtype=torch.float32)
        if float(torch.sqrt(torch.mean(waveform.square()))) < 1e-6:
            if not torch.any(waveform):
                return torch.zeros((2, waveform.numel()), dtype=waveform.dtype,
                                   device=waveform.device)
            raise ValueError("Near-silent recording is not informative")
        peak = waveform.abs().max()
        normalized = waveform / peak
        length = waveform.numel()
        starts = list(range(0, max(1, length - self.inference_window_samples + 1),
                            self.inference_hop_samples))
        if not starts:
            starts = [0]
        while starts[-1] + self.inference_window_samples < length:
            starts.append(starts[-1] + self.inference_hop_samples)
        fade = 0.5 - 0.5 * torch.cos(torch.pi *
            (torch.arange(self.overlap_samples, device=waveform.device, dtype=waveform.dtype) + 1) /
            (self.overlap_samples + 1))
        sums = torch.zeros((2, length), dtype=waveform.dtype, device=waveform.device)
        coverage = torch.zeros(length, dtype=waveform.dtype, device=waveform.device)
        for index, start in enumerate(starts):
            valid = min(self.inference_window_samples, length - start)
            segment = normalized[start:start + valid]
            if valid < self.inference_window_samples:
                segment = torch.nn.functional.pad(segment, (0, self.inference_window_samples - valid))
            weights = torch.ones(self.inference_window_samples, dtype=waveform.dtype,
                                 device=waveform.device)
            if index > 0:
                weights[:self.overlap_samples] = fade
            if index < len(starts) - 1:
                weights[-self.overlap_samples:] = 1.0 - fade
            separated = self(segment.view(1, 1, -1))[0]
            sums[:, start:start + valid] += separated[:, :valid] * weights[:valid]
            coverage[start:start + valid] += weights[:valid]
        if torch.any(coverage <= 0):
            raise RuntimeError("Inference windows left uncovered input samples")
        return (sums / coverage.unsqueeze(0)) * peak
