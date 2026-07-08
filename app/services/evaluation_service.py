"""Evaluation metric calculation for separated cardiopulmonary sounds."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.database.db import PROJECT_ROOT
from app.ml.audio_utils import EPS, load_wav_mono, resample_linear
from app.models.db_models import EvaluationMetric, SeparationResult, UploadedAudio


DATASET_MIX_DIR = PROJECT_ROOT / "datasets" / "hls_cmds" / "raw" / "Mix"


@dataclass(frozen=True)
class ReferencePair:
    heart_path: Path
    lung_path: Path
    reference_type: str


@dataclass(frozen=True)
class MetricRecord:
    metric_name: str
    metric_scope: str
    metric_value: float
    metric_unit: str | None = None
    reference_type: str | None = None


def _extract_hls_id(filename: str | None) -> str | None:
    if not filename:
        return None
    match = re.search(r"[HLM](\d{4})", Path(filename).stem.upper())
    if not match:
        return None
    return match.group(1)


def find_hls_reference_pair(uploaded_audio: UploadedAudio) -> ReferencePair | None:
    """Find HLS-CMDS paired references when the filename exposes an HLS ID."""

    hls_id = _extract_hls_id(uploaded_audio.original_filename) or _extract_hls_id(
        uploaded_audio.stored_path
    )
    if hls_id is None:
        return None

    heart_path = DATASET_MIX_DIR / f"H{hls_id}.wav"
    lung_path = DATASET_MIX_DIR / f"L{hls_id}.wav"
    if heart_path.is_file() and lung_path.is_file():
        return ReferencePair(
            heart_path=heart_path,
            lung_path=lung_path,
            reference_type="hls_cmds_paired_reference",
        )
    return None


def _align_to_reference(
    estimate: np.ndarray,
    reference: np.ndarray,
    mixture: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    length = min(estimate.size, reference.size, mixture.size)
    return estimate[:length], reference[:length], mixture[:length]


def _slice_with_lag(
    estimate: np.ndarray,
    reference: np.ndarray,
    mixture: np.ndarray,
    lag_samples: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if lag_samples < 0:
        estimate = estimate[-lag_samples:]
    elif lag_samples > 0:
        reference = reference[lag_samples:]
        mixture = mixture[lag_samples:]
    return _align_to_reference(estimate, reference, mixture)


def _best_alignment_lag(
    estimate: np.ndarray,
    reference: np.ndarray,
    mixture: np.ndarray,
    max_lag_samples: int,
) -> int:
    if max_lag_samples <= 0:
        return 0

    best_lag = 0
    best_score = -math.inf
    step = max(1, max_lag_samples // 100)
    for lag in range(-max_lag_samples, max_lag_samples + 1, step):
        aligned_estimate, aligned_reference, _aligned_mixture = _slice_with_lag(
            estimate,
            reference,
            mixture,
            lag,
        )
        if aligned_estimate.size < 64:
            continue
        score = _si_sdr_db(aligned_estimate, aligned_reference)
        if score > best_score:
            best_score = score
            best_lag = lag
    return best_lag


def _sdr_db(estimate: np.ndarray, reference: np.ndarray) -> float:
    error = reference - estimate
    return 10.0 * math.log10((float(np.sum(reference * reference)) + EPS) / (float(np.sum(error * error)) + EPS))


def _si_sdr_db(estimate: np.ndarray, reference: np.ndarray) -> float:
    estimate = estimate - float(np.mean(estimate))
    reference = reference - float(np.mean(reference))
    reference_energy = float(np.sum(reference * reference)) + EPS
    scale = float(np.sum(estimate * reference)) / reference_energy
    target = scale * reference
    noise = estimate - target
    return 10.0 * math.log10((float(np.sum(target * target)) + EPS) / (float(np.sum(noise * noise)) + EPS))


def _correlation(estimate: np.ndarray, reference: np.ndarray) -> float:
    if float(np.std(estimate)) <= EPS or float(np.std(reference)) <= EPS:
        return 0.0
    return float(np.corrcoef(estimate, reference)[0, 1])


def _metrics_for_scope(
    scope: str,
    estimate: np.ndarray,
    reference: np.ndarray,
    mixture: np.ndarray,
    reference_type: str,
    max_alignment_lag_samples: int,
) -> list[MetricRecord]:
    lag_samples = _best_alignment_lag(
        estimate,
        reference,
        mixture,
        max_alignment_lag_samples,
    )
    estimate, reference, mixture = _slice_with_lag(
        estimate,
        reference,
        mixture,
        lag_samples,
    )
    before_sdr = _sdr_db(mixture, reference)
    after_sdr = _sdr_db(estimate, reference)
    return [
        MetricRecord("sdr", scope, after_sdr, "dB", reference_type),
        MetricRecord("si_sdr", scope, _si_sdr_db(estimate, reference), "dB", reference_type),
        MetricRecord("snr_improvement", scope, after_sdr - before_sdr, "dB", reference_type),
        MetricRecord("mse", scope, float(np.mean(np.square(reference - estimate))), None, reference_type),
        MetricRecord("mae", scope, float(np.mean(np.abs(reference - estimate))), None, reference_type),
        MetricRecord("correlation", scope, _correlation(estimate, reference), None, reference_type),
        MetricRecord("alignment_lag", scope, float(lag_samples), "samples", reference_type),
    ]


def calculate_reference_metrics(
    input_path: Path,
    heart_output_path: Path,
    lung_output_path: Path,
    reference_pair: ReferencePair,
    sample_rate_hz: int,
    max_alignment_lag_ms: float = 100.0,
) -> list[MetricRecord]:
    mixture = load_wav_mono(input_path, target_sample_rate=sample_rate_hz).waveform
    heart_estimate = load_wav_mono(heart_output_path, target_sample_rate=sample_rate_hz).waveform
    lung_estimate = load_wav_mono(lung_output_path, target_sample_rate=sample_rate_hz).waveform
    heart_reference = load_wav_mono(
        reference_pair.heart_path,
        target_sample_rate=sample_rate_hz,
    ).waveform
    lung_reference = load_wav_mono(
        reference_pair.lung_path,
        target_sample_rate=sample_rate_hz,
    ).waveform

    if heart_reference.size != heart_estimate.size:
        heart_reference = resample_linear(
            heart_reference,
            sample_rate_hz,
            sample_rate_hz,
        )
    if lung_reference.size != lung_estimate.size:
        lung_reference = resample_linear(
            lung_reference,
            sample_rate_hz,
            sample_rate_hz,
        )

    max_alignment_lag_samples = max(
        0,
        int(sample_rate_hz * max_alignment_lag_ms / 1000.0),
    )

    return [
        *_metrics_for_scope(
            "heart",
            heart_estimate,
            heart_reference,
            mixture,
            reference_pair.reference_type,
            max_alignment_lag_samples,
        ),
        *_metrics_for_scope(
            "lung",
            lung_estimate,
            lung_reference,
            mixture,
            reference_pair.reference_type,
            max_alignment_lag_samples,
        ),
    ]


def store_metrics(
    db: Session,
    result_id: int,
    metrics: list[MetricRecord],
) -> None:
    for metric in metrics:
        db.add(
            EvaluationMetric(
                result_id=result_id,
                metric_name=metric.metric_name,
                metric_scope=metric.metric_scope,
                metric_value=metric.metric_value,
                metric_unit=metric.metric_unit,
                reference_type=metric.reference_type,
            )
        )


def evaluate_and_store_result(
    db: Session,
    result: SeparationResult,
    uploaded_audio: UploadedAudio,
    input_path: Path,
    heart_output_path: Path,
    lung_output_path: Path,
    sample_rate_hz: int,
) -> list[MetricRecord]:
    reference_pair = find_hls_reference_pair(uploaded_audio)
    if reference_pair is None:
        return []

    metrics = calculate_reference_metrics(
        input_path=input_path,
        heart_output_path=heart_output_path,
        lung_output_path=lung_output_path,
        reference_pair=reference_pair,
        sample_rate_hz=sample_rate_hz,
    )
    store_metrics(db, result.result_id, metrics)
    return metrics
