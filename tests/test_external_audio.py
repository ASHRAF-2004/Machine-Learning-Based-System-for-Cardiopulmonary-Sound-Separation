"""External-data contracts using synthetic temporary WAVs only (no datasets)."""
from pathlib import Path
import struct

import numpy as np
import pytest
from scipy.io import wavfile

from app.ml.external_audio import canonicalize_recording, sha256_file


def _record(path: Path) -> dict:
    return {"recording_id": "synthetic", "dataset_id": "fixture", "source_type": "heart",
            "source_url": "https://example.org/synthetic-fixture.wav", "original_path": str(path),
            "original_sha256": sha256_file(path)}


def _derive(record: dict, derived_dir: Path) -> dict:
    return canonicalize_recording(record, derived_dir=derived_dir,
                                  authorized_originals={str(Path(record["original_path"]).resolve()):
                                                        record["original_sha256"]})


def test_deterministic_antialiased_derivation_preserves_original(tmp_path: Path) -> None:
    path = tmp_path / "original.wav"
    t = np.arange(8 * 16000) / 16000
    signal = .2 * np.sin(2 * np.pi * 200 * t) + .2 * np.sin(2 * np.pi * 3000 * t)
    wavfile.write(path, 16000, (signal * 32767).astype(np.int16))
    record = _record(path)
    first = _derive(record, tmp_path / "derived")
    second = _derive(record, tmp_path / "derived")
    assert first == second
    assert sha256_file(path) == record["original_sha256"]
    y = np.load(first["derived_path"], allow_pickle=False)
    assert y.shape == (32000,) and y.dtype == np.float32 and np.isfinite(y).all()
    expected = .2 * np.sin(2 * np.pi * 200 * np.arange(32000) / 4000)
    assert np.sqrt(np.mean((y[100:-100] - expected[100:-100]) ** 2)) < .001
    assert first["source_purity_tier"] == "UNASSESSED"
    assert first["subject_id"] is None and not first["purity_automatically_assessed"]


def test_allowlist_hls_guard_hash_and_nonfinite_rejection(tmp_path: Path) -> None:
    # The forbidden path need not exist: rejection precedes hashing/decoding.
    fake = {"recording_id": "fake", "dataset_id": "fixture", "source_type": "lung",
            "source_url": "https://example.org/fake.wav", "original_sha256": "0" * 64,
            "original_path": str(tmp_path / "datasets/hls_cmds/raw/never_open.wav")}
    with pytest.raises(ValueError, match="HLS-CMDS"):
        _derive(fake, tmp_path / "derived")
    path = tmp_path / "float.wav"
    wavfile.write(path, 4000, np.array([0, np.nan, .1], dtype=np.float32))
    record = _record(path)
    with pytest.raises(ValueError, match="allowlist"):
        canonicalize_recording(record, authorized_originals={}, derived_dir=tmp_path / "derived")
    with pytest.raises(ValueError, match="hash changed"):
        _derive(dict(record, original_sha256="0" * 64), tmp_path / "derived")
    with pytest.raises(ValueError, match="Nonfinite"):
        _derive(record, tmp_path / "derived")
    assert not (tmp_path / "derived").exists()


def test_quality_flags_do_not_approve_purity_or_pad_short_audio(tmp_path: Path) -> None:
    path = tmp_path / "stereo.wav"
    pcm = np.zeros((4000, 2), dtype=np.int16)
    pcm[:2] = [[32767, -32768], [-32768, 32767]]
    wavfile.write(path, 4000, pcm)
    record = _record(path)
    result = _derive(record, tmp_path / "derived")
    assert result["quality_status"] == "EXCLUDED"
    assert result["canonical_samples"] == 4000 and result["channel_count"] == 2
    assert "shorter_than_8_second_crop" in result["exclusion_reasons"]
    assert "digital_silence_or_near_zero" in result["exclusion_reasons"]
    assert result["original_full_scale_fraction"] == 2 / 4000
    assert result["source_purity_tier"] == "UNASSESSED"
    with pytest.raises(ValueError, match="reviewer"):
        _derive(dict(record, source_purity_tier="B"), tmp_path / "derived")


def test_sprsound_exact_block_align_defect_is_repaired_in_memory_only(tmp_path: Path) -> None:
    path = tmp_path / 'spr.wav'
    wavfile.write(path, 8000, (np.sin(np.arange(64000) * .1) * 6000).astype(np.int16))
    payload = bytearray(path.read_bytes())
    assert struct.unpack('<HHIIHH', payload[20:36]) == (1, 1, 8000, 16000, 2, 16)
    struct.pack_into('<H', payload, 32, 4)
    path.write_bytes(payload)
    record = dict(_record(path), dataset_id='sprsound-biocas2022')
    result = _derive(record, tmp_path / 'derived')
    assert result['duration_seconds'] == 8 and result['canonical_samples'] == 32000
    assert result['decode_header_repairs'][0]['decoded_as'] == 2
    assert path.read_bytes() == payload
    with pytest.raises(ValueError):
        _derive(dict(record, dataset_id='unrecognized'), tmp_path / 'other')
