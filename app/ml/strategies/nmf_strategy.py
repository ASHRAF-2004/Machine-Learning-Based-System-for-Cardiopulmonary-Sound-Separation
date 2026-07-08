"""Unsupervised NMF decomposition baseline strategy."""

from __future__ import annotations

import numpy as np

from app.ml.audio_utils import AudioData, EPS, istft, stft
from app.ml.strategies.base import BaseSeparationStrategy, SeparatedWaveforms, StrategyContext


class NmfSeparationStrategy(BaseSeparationStrategy):
    """Practical NMF baseline on the magnitude spectrogram.

    This is an unsupervised decomposition baseline. It is not the supervised
    MATLAB NMF/NMCF method from the NeoSSNet reference repository.
    """

    strategy_key = "nmf"
    display_name = "NMF Decomposition"
    method_type = "decomposition"

    def __init__(
        self,
        n_components: int = 6,
        iterations: int = 80,
        random_seed: int = 42,
    ) -> None:
        self.n_components = n_components
        self.iterations = iterations
        self.random_seed = random_seed

    def _factorize(self, magnitude: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        rng = np.random.default_rng(self.random_seed)
        n_freq, n_frames = magnitude.shape
        components = max(2, min(self.n_components, n_freq, n_frames))
        w = rng.random((n_freq, components), dtype=np.float32) + 1e-3
        h = rng.random((components, n_frames), dtype=np.float32) + 1e-3

        for _ in range(self.iterations):
            h *= (w.T @ magnitude) / (w.T @ w @ h + EPS)
            w *= (magnitude @ h.T) / (w @ h @ h.T + EPS)
            scale = np.maximum(w.sum(axis=0, keepdims=True), EPS)
            w /= scale
            h *= scale.T

        return w, h

    @staticmethod
    def _split_components(
        basis: np.ndarray,
        activations: np.ndarray,
        frequencies_hz: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, list[float]]:
        component_count = basis.shape[1]
        centroids = (
            (basis * frequencies_hz[:, None]).sum(axis=0)
            / np.maximum(basis.sum(axis=0), EPS)
        )

        heart_indexes = np.where(centroids <= 220.0)[0]
        lung_indexes = np.where(centroids > 220.0)[0]

        if heart_indexes.size == 0 or lung_indexes.size == 0:
            order = np.argsort(centroids)
            split = max(1, component_count // 2)
            heart_indexes = order[:split]
            lung_indexes = order[split:]
            if lung_indexes.size == 0:
                lung_indexes = order[-1:]
                heart_indexes = order[:-1]

        heart_mag = sum(
            basis[:, index : index + 1] @ activations[index : index + 1, :]
            for index in heart_indexes
        )
        lung_mag = sum(
            basis[:, index : index + 1] @ activations[index : index + 1, :]
            for index in lung_indexes
        )
        return heart_mag, lung_mag, [float(value) for value in centroids]

    def separate_waveform(
        self,
        audio: AudioData,
        context: StrategyContext,
    ) -> SeparatedWaveforms:
        transform = stft(audio.waveform, audio.sample_rate_hz)
        magnitude = np.abs(transform.spectrum).astype(np.float32) + EPS
        basis, activations = self._factorize(magnitude)
        heart_mag, lung_mag, centroids = self._split_components(
            basis,
            activations,
            transform.frequencies_hz,
        )

        denominator = heart_mag + lung_mag + EPS
        heart_mask = heart_mag / denominator
        lung_mask = lung_mag / denominator
        heart = istft(transform, transform.spectrum * heart_mask)
        lung = istft(transform, transform.spectrum * lung_mask)

        return SeparatedWaveforms(
            heart=heart,
            lung=lung,
            sample_rate_hz=audio.sample_rate_hz,
            metadata={
                "nmf_components": basis.shape[1],
                "nmf_iterations": self.iterations,
                "component_centroids_hz": centroids,
                "reproduction_note": (
                    "Unsupervised Python NMF baseline using spectrogram soft masks; "
                    "not a trained ML model."
                ),
            },
        )
