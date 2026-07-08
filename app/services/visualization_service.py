"""Waveform and spectrogram visualization generation."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np

from app.ml.audio_utils import load_wav_mono, stft
from app.services import storage_service


class VisualizationError(RuntimeError):
    pass


def _import_pyplot():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as error:  # pragma: no cover - depends on local install
        raise VisualizationError(f"Matplotlib visualization unavailable: {error}") from error
    return plt


SOURCE_COLORS = {
    "mixed": "#2563eb",
    "heart": "#dc2626",
    "lung": "#0f766e",
}


def _plot_waveform(input_path: Path, output_path: Path, title: str, source: str) -> None:
    plt = _import_pyplot()
    audio = load_wav_mono(input_path)
    duration = audio.waveform.size / audio.sample_rate_hz
    time_axis = np.linspace(0.0, duration, num=audio.waveform.size, endpoint=False)

    figure, axis = plt.subplots(figsize=(7.4, 2.35), dpi=140)
    axis.plot(
        time_axis,
        audio.waveform,
        linewidth=0.75,
        color=SOURCE_COLORS.get(source, "#111827"),
    )
    axis.set_title(title)
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Amplitude")
    robust_peak = float(np.percentile(np.abs(audio.waveform), 99.5))
    amplitude_limit = min(1.0, max(0.05, robust_peak * 1.25))
    axis.set_ylim(-amplitude_limit, amplitude_limit)
    axis.grid(alpha=0.22, linewidth=0.55)
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path)
    plt.close(figure)


def _plot_spectrogram(input_path: Path, output_path: Path, title: str) -> None:
    plt = _import_pyplot()
    audio = load_wav_mono(input_path)
    transform = stft(audio.waveform, audio.sample_rate_hz, n_fft=512, hop_length=128)
    magnitude_db = 20.0 * np.log10(np.abs(transform.spectrum) + 1e-8)
    duration = audio.waveform.size / audio.sample_rate_hz
    max_frequency_hz = min(1000.0, audio.sample_rate_hz / 2.0)
    vmin, vmax = np.percentile(magnitude_db, [5, 99])
    if float(vmax) <= float(vmin):
        vmax = vmin + 1.0

    figure, axis = plt.subplots(figsize=(7.4, 2.75), dpi=140)
    image = axis.imshow(
        magnitude_db,
        origin="lower",
        aspect="auto",
        extent=[0.0, duration, 0.0, audio.sample_rate_hz / 2.0],
        cmap="magma",
        vmin=vmin,
        vmax=vmax,
    )
    axis.set_ylim(0.0, max_frequency_hz)
    axis.set_title(title)
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Frequency (Hz)")
    figure.colorbar(image, ax=axis, fraction=0.025, pad=0.02, label="dB")
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path)
    plt.close(figure)


def generate_visualizations(
    job_id: int,
    mixed_input_path: Path,
    heart_output_path: Path,
    lung_output_path: Path,
) -> dict[str, dict[str, str]]:
    paths = storage_service.build_visualization_output_paths(job_id)
    path_map = asdict(paths)
    plot_specs = (
        ("mixed_waveform_path", mixed_input_path, "Mixed Input Waveform", "mixed"),
        ("mixed_spectrogram_path", mixed_input_path, "Mixed Input Spectrogram", "mixed"),
        ("heart_waveform_path", heart_output_path, "Separated Heart Waveform", "heart"),
        ("heart_spectrogram_path", heart_output_path, "Separated Heart Spectrogram", "heart"),
        ("lung_waveform_path", lung_output_path, "Separated Lung Waveform", "lung"),
        ("lung_spectrogram_path", lung_output_path, "Separated Lung Spectrogram", "lung"),
    )

    for key, input_path, title, source in plot_specs:
        output_path = path_map[key]
        if "spectrogram" in key:
            _plot_spectrogram(input_path, output_path, title)
        else:
            _plot_waveform(input_path, output_path, title, source)

    return format_visualization_paths(job_id)


def _format_image(path: Path) -> dict[str, str]:
    relative_path = storage_service.relative_project_path(path)
    return {
        "path": relative_path,
        "url": f"/visualizations/{path.name}",
    }


def format_visualization_paths(job_id: int) -> dict[str, dict[str, dict[str, str]]]:
    paths = storage_service.build_visualization_output_paths(job_id)
    return {
        "mixed": {
            "waveform": _format_image(paths.mixed_waveform_path),
            "spectrogram": _format_image(paths.mixed_spectrogram_path),
        },
        "heart": {
            "waveform": _format_image(paths.heart_waveform_path),
            "spectrogram": _format_image(paths.heart_spectrogram_path),
        },
        "lung": {
            "waveform": _format_image(paths.lung_waveform_path),
            "spectrogram": _format_image(paths.lung_spectrogram_path),
        },
    }


def existing_visualizations(job_id: int) -> dict[str, dict[str, dict[str, str]]]:
    visualizations = format_visualization_paths(job_id)
    filtered: dict[str, dict[str, dict[str, str]]] = {}
    for source_name, source_images in visualizations.items():
        existing_images = {
            image_type: image
            for image_type, image in source_images.items()
            if storage_service.resolve_project_path(image["path"]).is_file()
        }
        if existing_images:
            filtered[source_name] = existing_images
    return filtered
