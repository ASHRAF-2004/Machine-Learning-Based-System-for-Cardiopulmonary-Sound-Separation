"""Metadata-only tests: no waveform is opened or decoded."""
import copy

import pytest

from scripts.audit_hls_native_registry import authorized_native_path, build_registry


def test_native_registry_metadata_counts_mapping_and_partition():
    registry = build_registry(inspect_eligible_headers=False)
    assert registry['counts']['native_triplets'] == 145
    assert registry['counts']['all_wavs'] == 535
    assert registry['counts']['eligible_triplets'] == 100
    eligible = [r for r in registry['rows'] if r['eligible_non_test']]
    excluded = [r for r in registry['rows'] if not r['eligible_non_test']]
    assert len(excluded) == 45
    assert all(not f['audio_bytes_opened'] and f['sha256'] is None
               for row in registry['rows'] for f in row['files'].values())
    pairs = {partition: {r['family_pair_id'] for r in eligible if r['correspondence_partition'] == partition}
             for partition in ('fit_pair', 'heldout_pair')}
    assert len(pairs['fit_pair']) == 32 and len(pairs['heldout_pair']) == 8
    assert not pairs['fit_pair'] & pairs['heldout_pair']
    assert registry['correspondence_holdout']['triplet_counts'] == {'fit_pair': 74, 'heldout_pair': 26}


def test_native_guard_rejects_sealed_ids_wrong_paths_and_fold_leakage():
    registry = build_registry(inspect_eligible_headers=False)
    included = next(r for r in registry['rows'] if r['eligible_non_test'])
    excluded = next(r for r in registry['rows'] if not r['eligible_non_test'])
    assert authorized_native_path(included, included['mixture_file']).name == included['triplet_id'] + '.wav'
    with pytest.raises(ValueError):
        authorized_native_path(excluded, excluded['mixture_file'])
    forged = copy.deepcopy(excluded)
    forged['eligible_non_test'] = True
    forged['exclusion_reasons'] = []
    with pytest.raises(ValueError):
        authorized_native_path(forged, forged['mixture_file'])
    with pytest.raises(ValueError):
        authorized_native_path(included, excluded['mixture_file'])
    with pytest.raises(ValueError):
        authorized_native_path(included, included['mixture_file'], included['withheld_from_training_folds'][0])
    assert authorized_native_path(included, included['heart_reference_file'], included['eligible_training_folds'][0])
