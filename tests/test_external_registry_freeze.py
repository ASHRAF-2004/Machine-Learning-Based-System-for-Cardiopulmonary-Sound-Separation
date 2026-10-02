"""One focused synthetic guard for external pilot split/duplicate contracts."""
import hashlib

import numpy as np

from scripts import freeze_external_pilot_registry as registry


def test_external_freeze_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, 'DATA', tmp_path)
    rng = np.random.default_rng(715)
    signal = rng.normal(size=48000).astype('<f4')
    shifted_scaled = -0.3 * signal[4000:44000]
    assert registry.near_copy_score(signal, shifted_scaled) > 0.999
    assert registry.near_copy_score(signal, rng.normal(size=40000).astype('<f4')) < 0.1
    assert registry.subject_partition('circor', '123') == registry.subject_partition('circor', '123')

    def row(dataset, subject, recording, samples):
        original = tmp_path / (recording + '.fixture')
        original.write_bytes(recording.encode())
        derived = tmp_path / (recording + '.npy')
        np.save(derived, samples)
        return {'dataset_id': dataset, 'subject_id': subject, 'recording_id': recording,
                'source_type': 'heart' if dataset.startswith('circor') else 'lung',
                'original_path': str(original), 'original_sha256': registry.sha256_file(original),
                'derived_path': str(derived), 'derived_sha256': registry.sha256_file(derived),
                'canonical_waveform_sha256': hashlib.sha256(samples.tobytes()).hexdigest(),
                'canonical_samples': len(samples), 'canonical_sample_rate': 4000,
                'canonical_channel_count': 1, 'valid_intervals_4k': [[0, len(samples)]],
                'family_id': 'normal', 'age': 8, 'age_group': 'Child',
                'source_purity_tier': 'B', 'source_purity_confidence': 'imperfect',
                'source_purity_evidence': 'synthetic fixture only', 'purity_reviewer': 'fixture',
                'quality_status': 'TIER_B_CANDIDATE_PENDING_SIGNAL_REVIEW', 'exclusion_reasons': []}

    rows = [row('circor-1.0.3', '123', 'a', signal),
            row('circor-1.0.3', '456', 'b', signal.copy()),
            row('sprsound-biocas2022', '789', 'c', rng.normal(size=32000).astype('<f4'))]
    rows[2]['valid_intervals_4k'] = [[0, 32001]]
    config = {'sample_rate': 4000, 'crop_samples': 32000, 'datasets': list(registry.DATASETS),
              'test_access_allowed': False, 'pilot_candidate_subject_groups_per_dataset': 160,
              'pilot_max_recordings_per_subject_group': 2, 'minimum_training_subjects_each_source': 64}
    result, summary = registry.freeze(rows, config)
    assert not result['recordings']
    assert summary['all_rows_accounted_for']
    assert summary['status'] == 'REJECTED_INSUFFICIENT_QUALIFIED_SUBJECTS'
    excluded = {r['recording_id']: r['reasons'] for r in result['exclusions']}
    assert 'exact_duplicate_cross_subject_cluster' in excluded['a']
    assert 'exact_duplicate_cross_subject_cluster' in excluded['b']
    assert 'invalid_qualified_interval_bounds_duration_or_overlap' in excluded['c']
    try:
        registry.external_path(tmp_path / 'hls_cmds' / 'forbidden.npy')
    except ValueError:
        pass
    else:
        raise AssertionError('HLS path accepted')
