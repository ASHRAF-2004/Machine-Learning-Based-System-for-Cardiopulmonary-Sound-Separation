"""Offline external-WAV registry derivation; technical checks are not purity labels.

Callers must first freeze an explicit path/hash allowlist obtained from a dataset
selection manifest. No HLS-CMDS path is accepted here, including through symlinks.
Original files are never modified; derived files are deterministic float32 NPYs.
"""
from __future__ import annotations

import hashlib
import io
import math
import re
import struct
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

import numpy as np
import scipy
from scipy.io import wavfile
from scipy.signal import resample_poly

CANONICAL_SAMPLE_RATE = 4000
RESAMPLER = {"implementation": "scipy.signal.resample_poly", "window": ["kaiser", 8.6],
             "padtype": "constant", "cval": 0.0}
UNKNOWN_FIELDS = ("subject_id", "family_id", "age", "age_group", "sex", "pathology",
                  "recording_site", "device", "institution", "split_group", "notes",
                  "source_purity_confidence", "source_purity_evidence", "purity_reviewer",
                  "dataset_version", "access_terms", "original_bit_depth")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _external_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if any(part.lower() == "hls_cmds" for p in (path, resolved) for part in p.parts):
        raise ValueError("HLS-CMDS is forbidden in the external-audio helper")
    return resolved


def _wav_bits(path: Path) -> int | None:
    """Read RIFF format precision (including extensible valid bits), not infer it."""
    with path.open("rb") as stream:
        header = stream.read(12)
        if header[:4] not in (b"RIFF", b"RIFX", b"RF64") or header[8:] != b"WAVE":
            return None
        endian = ">" if header[:4] == b"RIFX" else "<"
        while chunk := stream.read(8):
            if len(chunk) != 8:
                return None
            size = struct.unpack(endian + "I", chunk[4:])[0]
            if chunk[:4] == b"fmt ":
                fmt = stream.read(min(size, 40))
                if len(fmt) < 16:
                    return None
                tag, bits = struct.unpack(endian + "H", fmt[:2])[0], struct.unpack(endian + "H", fmt[14:16])[0]
                if tag == 0xFFFE and len(fmt) >= 20:
                    valid = struct.unpack(endian + "H", fmt[18:20])[0]
                    return valid or bits
                return bits
            stream.seek(size + size % 2, 1)
    return None


def _pcm_float(data: np.ndarray, bits: int | None) -> tuple[np.ndarray, np.ndarray]:
    """Convert PCM at its container scale (SciPy left-justifies 24-bit PCM)."""
    if data.dtype == np.uint8:
        full_scale = (data == 0) | (data == 255)
        values = (data.astype(np.float64) - 128.0) / 128.0
    elif data.dtype.kind == "i":
        info = np.iinfo(data.dtype)
        values = data.astype(np.float64) / float(-info.min)
        # SciPy returns left-justified int32 for PCM24; its positive rail is not
        # int32.max. Use the declared precision instead of missing that rail.
        precision = bits or info.bits
        full_scale = (values <= -1.0) | (values >= 1.0 - 2.0 ** (1 - precision))
    elif data.dtype.kind == "f":
        values = data.astype(np.float64)
        full_scale = np.abs(values) >= 1.0
    else:
        raise ValueError(f"Unsupported WAV sample dtype: {data.dtype}")
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite original WAV samples")
    return values, full_scale


def canonicalize_recording(record: Mapping[str, object], *,
                           authorized_originals: Mapping[str, str],
                           derived_dir: Path) -> dict[str, object]:
    """Derive one explicit, hash-authorized external recording; never approve purity.

    ``authorized_originals`` maps absolute resolved paths to frozen SHA-256s.
    A dataset's classification label or this function's quality flags must never
    be taken as clean-source supervision evidence. Short sources are excluded,
    not padded, tiled, or concatenated. Existing differing artifacts are refused.
    """
    required = ("recording_id", "dataset_id", "source_type", "original_path",
                "original_sha256", "source_url")
    if any(not record.get(key) for key in required):
        raise ValueError(f"Required registry fields: {required}")
    for key in ("dataset_id", "recording_id"):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", str(record[key])):
            raise ValueError(f"Unsafe registry identifier: {key}")
    if str(record["dataset_id"]).lower() == "hls_cmds":
        raise ValueError("HLS-CMDS is forbidden in the external-audio helper")
    if record["source_type"] not in {"heart", "lung", "mixed", "unknown"}:
        raise ValueError("Unsupported source_type")
    url = urlparse(str(record["source_url"]))
    if url.scheme not in {"https", "http"} or not url.netloc:
        raise ValueError("An explicit original source URL is required")
    source = _external_path(Path(str(record["original_path"])))
    expected_hash = str(record["original_sha256"])
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ValueError("Expected lowercase SHA-256")
    if authorized_originals.get(str(source)) != expected_hash:
        raise ValueError("Source is absent from the explicit frozen path/hash allowlist")
    if source.suffix.lower() != ".wav" or sha256_file(source) != expected_hash:
        raise ValueError("Original WAV missing or its hash changed")
    header_repairs = []
    try:
        sample_rate, pcm = wavfile.read(source)
    except ValueError as error:
        # Pinned SPRSound originals have PCM16 mono data and a matching 16kB/s
        # byte rate, but declare blockAlign=4 rather than 2. Repair only this
        # exact redundant header defect in memory; never rewrite source bytes.
        payload = bytearray(source.read_bytes())
        if (not str(record['dataset_id']).startswith('sprsound-') or
                payload[:4] != b'RIFF' or payload[8:12] != b'WAVE'):
            raise
        offset = 12
        repaired = False
        while offset + 8 <= len(payload):
            tag = payload[offset:offset + 4]
            size = struct.unpack('<I', payload[offset + 4:offset + 8])[0]
            if tag == b'fmt ' and size == 16:
                fields = struct.unpack('<HHIIHH', payload[offset + 8:offset + 24])
                if fields == (1, 1, 8000, 16000, 4, 16):
                    struct.pack_into('<H', payload, offset + 20, 2)
                    repaired = True
                    header_repairs.append({'field': 'nBlockAlign', 'original': 4,
                                           'decoded_as': 2, 'scope': 'in_memory_only',
                                           'reason': 'PCM16 mono and byte rate independently imply 2 bytes/frame'})
                break
            offset += 8 + size + size % 2
        if not repaired:
            raise error
        sample_rate, pcm = wavfile.read(io.BytesIO(payload))
    if not isinstance(sample_rate, int) or sample_rate <= 0:
        raise ValueError("Invalid sample rate")
    if pcm.ndim not in (1, 2) or pcm.shape[0] == 0 or (pcm.ndim == 2 and pcm.shape[1] == 0):
        raise ValueError("Empty or unsupported audio shape")
    channels = 1 if pcm.ndim == 1 else pcm.shape[1]
    bit_depth = _wav_bits(source)
    values, full_scale = _pcm_float(pcm, bit_depth)
    mono = values if channels == 1 and values.ndim == 1 else values.mean(axis=1)
    divisor = math.gcd(sample_rate, CANONICAL_SAMPLE_RATE)
    canonical = (mono if sample_rate == CANONICAL_SAMPLE_RATE else
                 resample_poly(mono, CANONICAL_SAMPLE_RATE // divisor, sample_rate // divisor,
                               window=("kaiser", 8.6), padtype="constant", cval=0.0))
    canonical = canonical.astype("<f4")
    if not np.isfinite(canonical).all():
        raise ValueError("Nonfinite canonical audio")
    rms = float(np.sqrt(np.mean(canonical.astype(np.float64) ** 2)))
    peak = float(np.max(np.abs(canonical)))
    duration = pcm.shape[0] / sample_rate
    excluded = []
    review = []
    if duration < 8.0:
        excluded.append("shorter_than_8_second_crop")
    if rms < 1e-6:
        excluded.append("digital_silence_or_near_zero")
    if full_scale.any():
        review.append("original_full_scale_samples_potential_clipping")
    if peak >= 1.0:
        review.append("canonical_peak_at_or_above_full_scale_no_clipping_applied")
    if channels > 1:
        review.append("channels_mean_downmixed_not_independent_source_references")
    tier = record.get("source_purity_tier", "UNASSESSED")
    if tier not in {"A", "B", "C", "REJECTED", "UNASSESSED"}:
        raise ValueError("Unknown source-purity tier")
    if tier in {"A", "B"} and not all(record.get(k) for k in
                                     ("source_purity_evidence", "source_purity_confidence", "purity_reviewer")):
        raise ValueError("Tier A/B requires explicit reviewer/evidence/confidence, not signal statistics")
    payload = io.BytesIO()
    np.save(payload, canonical, allow_pickle=False)
    derived_bytes = payload.getvalue()
    derived_hash = hashlib.sha256(derived_bytes).hexdigest()
    destination = _external_path(derived_dir) / f"{record['dataset_id']}__{record['recording_id']}.npy"
    if destination.is_symlink():
        raise ValueError("Derived artifact path must not be a symlink")
    destination = _external_path(destination)
    if destination.resolve() == source:
        raise ValueError("Derived path cannot overwrite the original")
    # Recheck immutable source identity before creating any derived artifact.
    if sha256_file(source) != expected_hash:
        raise ValueError("Original changed during derivation")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != derived_hash:
            raise FileExistsError("Refusing to replace a different derived artifact")
    else:
        with destination.open("xb") as stream:
            stream.write(derived_bytes)
    result = {field: record.get(field) for field in UNKNOWN_FIELDS}
    result.update({key: record[key] for key in required})
    result.update({"schema_version": 1, "original_path": str(source),
                   "original_sample_rate": sample_rate, "canonical_sample_rate": CANONICAL_SAMPLE_RATE,
                   "original_dtype": str(pcm.dtype), "original_bit_depth": bit_depth,
                   "decode_header_repairs": header_repairs,
                   "duration_seconds": duration,
                   "channel_count": channels, "canonical_channel_count": 1,
                   "canonical_samples": len(canonical), "canonical_dtype": "float32",
                   "channel_conversion": "none" if channels == 1 else "arithmetic_mean",
                   "amplitude_conversion": "PCM full-scale conversion only; no gain normalization",
                   "resampler": dict(RESAMPLER, scipy_version=scipy.__version__),
                   "resampling_applied": sample_rate != CANONICAL_SAMPLE_RATE,
                   "quality_status": "EXCLUDED" if excluded else
                   ("REVIEW_REQUIRED" if review else "TECHNICAL_PASS_NOT_PURITY_APPROVAL"),
                   "exclusion_reasons": excluded, "quality_review_flags": review,
                   "source_purity_tier": tier, "purity_automatically_assessed": False,
                   "original_full_scale_fraction": float(full_scale.mean()),
                   "canonical_rms": rms, "canonical_peak": peak,
                   "canonical_zero_fraction": float(np.mean(canonical == 0)),
                   "derived_path": str(destination), "derived_sha256": derived_hash})
    return result
