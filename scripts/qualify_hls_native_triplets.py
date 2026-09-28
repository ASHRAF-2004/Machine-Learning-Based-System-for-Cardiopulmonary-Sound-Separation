"""Freeze native waveform correspondence tiers before model training.

Qualification uses the root forensic signal evidence, not model performance.
The optional wrong-reference probe is post-hoc structural characterization,
not a new target-preparation method, selection metric, or training experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_hls_native_fingerprints import read_native, summary
from scripts.audit_hls_native_registry import ELIGIBLE, read_csv, sha256

REGISTRY = ROOT / 'research/manifests/hls_native_triplets_v1.json'
CORRESPONDENCE = ROOT / 'research/evidence/hls_native_correspondence_v1.json'
OUTPUT = ROOT / 'research/manifests/hls_native_qualified_v1.json'
THRESHOLD = .1


def qualify(registry: dict, correspondence: dict) -> dict:
    if correspondence['registry_sha256'] != sha256(REGISTRY):
        raise ValueError('Correspondence and registry identities differ')
    waveinfo = {r['triplet_id']: r for r in correspondence['rows']}
    seen = {}
    result = []
    for source in sorted(registry['rows'], key=lambda r: r['triplet_id']):
        row = {'triplet_id': source['triplet_id'], 'eligible_non_test': source['eligible_non_test'],
               'quality_tier': 'UNASSESSED_T9_EXCLUDED', 'reasons': source['exclusion_reasons'].copy(),
               'selected': False, 'heart_family': source['heart_family'], 'lung_family': source['lung_family'],
               'family_pair_id': source['family_pair_id']}
        if source['eligible_non_test']:
            info = waveinfo[source['triplet_id']]
            flanks = info['same_time_shared_gain_full_flanks']
            gain = info['same_time_shared_gain']
            good = len(flanks) == 2 and math.isfinite(gain) and gain > 0 and all(
                math.isfinite(x['residual_weaker_source_rms_ratio']) and x['residual_weaker_source_rms_ratio'] <= THRESHOLD for x in flanks)
            row['quality_tier'] = 'N1' if good else 'REJECTED_CORRESPONDENCE'
            row['reasons'] = [] if good else ['IDENTITY_DELAY_SHARED_GAIN_RESIDUAL_EXCEEDS_10_PERCENT_WEAKER_SOURCE_RMS_ON_AT_LEAST_ONE_FULL_FLANK']
            row['full_flank_residual_weaker_source_rms_ratios'] = [x['residual_weaker_source_rms_ratio'] for x in flanks]
            if good:
                signature = tuple(source['files'][role]['sha256'] for role in ('mixture', 'heart', 'lung'))
                row['selected'] = signature not in seen
                if row['selected']:
                    seen[signature] = source['triplet_id']
                else:
                    row['reasons'].append('EXACT_TRIPLET_DUPLICATE_RETAIN_LEXICOGRAPHIC_FIRST')
                    row['duplicate_of'] = seen[signature]
                row.update({'gain': gain, 'files': source['files'],
                            'eligible_training_folds': source['eligible_training_folds'],
                            'correspondence_partition': source['correspondence_partition'],
                            'recording_position': source['recording_position'],
                            'manikin_gender_label': source['manikin_gender_label'],
                            'heart_lag_samples': 0, 'lung_lag_samples': 0, 'transfer_filter': 'identity',
                            'acquisition_status': 'AFFINE_ADDITIVE_RELEASE_SUBSET_CAPTURE_MODE_UNVERIFIED'})
        result.append(row)
    counts = dict(Counter(r['quality_tier'] for r in result))
    counts.update({'N2': 0, 'N3': 0, 'selected_training_triplets': sum(r['selected'] for r in result),
                   'exact_triplet_duplicates_not_selected': sum(r['quality_tier'] == 'N1' and not r['selected'] for r in result)})
    if counts != {'N1': 27, 'REJECTED_CORRESPONDENCE': 73, 'UNASSESSED_T9_EXCLUDED': 45,
                  'N2': 0, 'N3': 0, 'selected_training_triplets': 26, 'exact_triplet_duplicates_not_selected': 1}:
        raise ValueError(f'Unexpected forensic qualification population: {counts}')
    return {'schema_version': 1, 'status': 'SIGNAL_CORRESPONDENCE_QUALIFIED_NOT_MODEL_EVALUATED',
            'selected_role': 'A_DIRECT_WAVEFORM_SUPERVISION_FOR_QUALIFIED_SUBSET_ONLY',
            'registry_path': str(REGISTRY.relative_to(ROOT)), 'registry_sha256': sha256(REGISTRY),
            'correspondence_path': str(CORRESPONDENCE.relative_to(ROOT)), 'correspondence_sha256': sha256(CORRESPONDENCE),
            'source_allowlist_path': str(ELIGIBLE.relative_to(ROOT)), 'source_allowlist_sha256': sha256(ELIGIBLE),
            'rule': {'gain': 'positive least-squares common scalar fitted on6-9s only',
                     'alignment': 'identity; zero lag; no warp', 'filter': 'identity; no fitted transfer filter',
                     'assessment_intervals_seconds': [[0, 6], [9, 15]],
                     'acceptance': 'BOTH full temporal flank residual RMS / min(gain*heart RMS,gain*lung RMS) <=0.1',
                     'threshold': THRESHOLD, 'duplicate_rule': 'identical ordered mixture/heart/lung hashes; retain lexicographic first triplet',
                     'no_ID_range_selection': True, 'no_model_scores_used': True},
            'target_contract': {'input': 'released mixture waveform m', 'heart': 'g*h_reference', 'lung': 'g*l_reference',
                                'native_target_residual_projection': False, 'inference_references_required': False,
                                'output_domain': 'empirically shared-gain mixture recording domain; capture mode unverified'},
            'counts': counts, 'selected_ids': [r['triplet_id'] for r in result if r['selected']],
            'selected_counts_by_fold': {f'f{i}': sum(r['selected'] and f'f{i}' in r.get('eligible_training_folds', []) for r in result) for i in range(1, 6)},
            'notes': ['N1 means quantified waveform correspondence, not proof of simultaneous physical acquisition.',
                      'Every selected row happens to be in the later release ID block; ID was not a selection criterion.',
                      'Rejected early triplets are not demonstrated useless for all future methods; none enters this bounded waveform intervention.',
                      'T9-associated native files are unassessed and unopened, not technically rejected based on test audio.'],
            'test_audio_opened': False, 'training_performed': False, 'rows': result}


def wrong_reference_probe(registry: dict, qualified: dict) -> dict:
    rows = [r for r in registry['rows'] if r['eligible_non_test']]
    lookup = {r['triplet_id']: r for r in rows}
    cache = {}
    def read(row, role):
        key = (row['triplet_id'], role)
        if key not in cache:
            cache[key] = read_native(row, role).astype(np.float64)
        return cache[key]
    def wrong(row, role):
        candidates = [r for r in rows if r[f'{role}_family'] == row[f'{role}_family']
                      and r['files'][role]['sha256'] != row['files'][role]['sha256']]
        def key(r):
            digest = hashlib.sha256(f'native-wrong-reference-v1:20260928:{row["triplet_id"]}:{role}:{r["triplet_id"]}'.encode()).hexdigest()
            return (r['correspondence_partition'] != 'fit_pair', r['recording_position'] != row['recording_position'], digest)
        return min(candidates, key=key)
    records = []
    for q in qualified['rows']:
        if q['quality_tier'] != 'N1':
            continue
        row = lookup[q['triplet_id']]
        wh, wl = wrong(row, 'heart'), wrong(row, 'lung')
        m, h, l = read(row, 'mixture'), read(row, 'heart'), read(row, 'lung')
        combinations = {'correct': (h, l), 'wrong_heart_only': (read(wh, 'heart'), l),
                        'wrong_lung_only': (h, read(wl, 'lung')),
                        'wrong_both': (read(wh, 'heart'), read(wl, 'lung'))}
        for name, (heart, lung) in combinations.items():
            total = heart + lung
            calibration = total[24000:36000]
            gain = max(0., float(np.dot(m[24000:36000], calibration) / max(np.dot(calibration, calibration), 1e-30)))
            scores = []
            for first, last in ((0, 24000), (36000, 60000)):
                residual = m[first:last] - gain * total[first:last]
                rms = float(np.sqrt(np.mean(residual ** 2)))
                mixture_rms = float(np.sqrt(np.mean(m[first:last] ** 2)))
                weaker = gain * min(float(np.sqrt(np.mean(heart[first:last] ** 2))), float(np.sqrt(np.mean(lung[first:last] ** 2))))
                scores.append({'residual_mix_rms_ratio': rms / max(mixture_rms, 1e-30),
                               'residual_weaker_source_rms_ratio': rms / weaker if weaker > 1e-20 else None})
            records.append({'triplet_id': row['triplet_id'], 'correspondence_partition': row['correspondence_partition'],
                            'condition': name, 'wrong_heart_triplet_id': wh['triplet_id'], 'wrong_lung_triplet_id': wl['triplet_id'],
                            'gain': gain, 'full_flanks': scores,
                            'passes_original_N1_error_rule': all(v['residual_weaker_source_rms_ratio'] is not None and v['residual_weaker_source_rms_ratio'] <= THRESHOLD for v in scores)})
    return {'schema_version': 1, 'status': 'POSTHOC_STRUCTURAL_CHARACTERIZATION_NOT_MODEL_TUNING',
            'registry_sha256': sha256(REGISTRY), 'qualified_manifest_sha256': sha256(OUTPUT),
            'selection': 'same-family different-hash references; fit-partition then exact site preferred; SHA256 seed20260928 tie-break; no waveform-quality selection',
            'objective': 'test whether scalar closure requires documented corresponding source files rather than arbitrary same-family recordings',
            'threshold_unchanged': THRESHOLD, 'no_modification_of_forensic_config': True,
            'correlation_search': False, 'transfer_filter_fitting': False,
            'calibration_seconds': [6, 9], 'assessment_seconds': [[0, 6], [9, 15]],
            'summary': {name: {'n': sum(r['condition'] == name for r in records),
                                'passes': sum(r['condition'] == name and r['passes_original_N1_error_rule'] for r in records),
                                'max_flank_residual_mix_rms_ratio': summary(max(v['residual_mix_rms_ratio'] for v in r['full_flanks']) for r in records if r['condition'] == name)}
                        for name in ('correct', 'wrong_heart_only', 'wrong_lung_only', 'wrong_both')},
            'heldout_pair_subset': {'n_triplets': sum(r['condition'] == 'correct' and r['correspondence_partition'] == 'heldout_pair' for r in records),
                                    'interpretation': 'descriptive small unseen-pair subset, not independent-family evidence'},
            'decoded_native_files': len(cache), 'test_audio_opened': False, 'training_performed': False, 'rows': records}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wrong-reference-probe', action='store_true')
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text())
    result = qualify(registry, json.loads(CORRESPONDENCE.read_text()))
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'manifest': str(OUTPUT.relative_to(ROOT)), 'sha256': sha256(OUTPUT),
                      'counts': result['counts'], 'fold_counts': result['selected_counts_by_fold']}, indent=2))
    if args.wrong_reference_probe:
        probe = wrong_reference_probe(registry, result)
        path = ROOT / 'research/evidence/hls_native_wrong_reference_v1.json'
        path.write_text(json.dumps(probe, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'wrong_reference_summary': probe['summary'], 'sha256': sha256(path)}, indent=2))


if __name__ == '__main__':
    main()
