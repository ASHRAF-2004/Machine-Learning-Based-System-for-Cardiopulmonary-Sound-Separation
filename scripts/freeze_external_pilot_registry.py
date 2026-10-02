"""Freeze external-only Tier-B pilot eligibility; never opens HLS or trains a model.

Near-copy screening is deliberately bounded, not proof of global uniqueness.
Originals are hash-verified only; signal comparisons use authorized derivations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.signal import correlate, resample_poly, welch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.external_audio import sha256_file
from scripts.acquire_external_qualification import save_json

DATA = ROOT / '.local/datasets'
DATASETS = {'circor-1.0.3': ('circor', 'heart'),
            'sprsound-biocas2022': ('sprsound', 'lung')}
AGES = {'Infant', 'Child', 'Adolescent'}
SCREEN = {'version': 'external-pilot-near-copy-v1', 'neighbors_per_record': 12,
          'fingerprint': '32 equal-width log Welch PSD bands, centered/unit norm',
          'excerpt_samples': 32000, 'excerpts': 'shorter recording start/middle/end',
          'search_rate_hz': 500, 'coarse_abs_correlation_min': 0.95,
          'full_rate_abs_correlation_uncertain': 0.970,
          'full_rate_abs_correlation_probable': 0.985,
          'policy': 'exclude every member of near-copy connected clusters',
          'limitation': 'bounded shortlist; not exhaustive fingerprint deduplication or purity certification'}


def subject_partition(dataset_group: str, merged_subject_id: str) -> str:
    key = f'external-v1:{dataset_group}:{merged_subject_id}'.encode()
    return 'external_validation' if int(hashlib.sha256(key).hexdigest(), 16) % 10 == 0 else 'train'


def external_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve()
    if (not resolved.is_relative_to(DATA.resolve()) or
            any('hls' in part.lower() for part in (*path.parts, *resolved.parts))):
        raise ValueError(f'Not an authorized external-data path: {path}')
    return resolved


def fingerprint(x: np.ndarray) -> np.ndarray:
    _, power = welch(x, fs=4000, nperseg=1024)
    bands = np.array([np.mean(v) for v in np.array_split(power, 32)])
    f = np.log(np.maximum(bands / max(float(bands.sum()), 1e-30), 1e-12))
    f -= f.mean()
    return f / max(float(np.linalg.norm(f)), 1e-12)


def sliding_correlation(template: np.ndarray, signal: np.ndarray) -> tuple[float, int]:
    """Maximum absolute centered correlation; permits polarity and gain changes."""
    n = len(template)
    if len(signal) < n or n < 2:
        return 0.0, 0
    t = np.asarray(template, dtype=np.float64)
    t = t - t.mean()
    y = np.asarray(signal, dtype=np.float64)
    sums = np.r_[0., np.cumsum(y)]
    squares = np.r_[0., np.cumsum(y * y)]
    local_sum = sums[n:] - sums[:-n]
    variance = np.maximum(squares[n:] - squares[:-n] - local_sum * local_sum / n, 0.)
    numerator = correlate(y, t, mode='valid', method='fft')
    denominator = np.sqrt(variance * np.dot(t, t))
    scores = np.divide(np.abs(numerator), denominator, out=np.zeros_like(numerator),
                       where=denominator > 1e-20)
    index = int(np.argmax(scores))
    return float(min(scores[index], 1.)), index


def near_copy_score(a: np.ndarray, b: np.ndarray) -> float:
    """Gain/polarity/offset/truncation screen with full-band confirmation."""
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    n = SCREEN['excerpt_samples']
    if len(short) < n:
        return 0.
    low_long = resample_poly(long, 1, 8)
    best = 0.
    for start in sorted({0, (len(short) - n) // 2, len(short) - n}):
        excerpt = np.asarray(short[start:start+n])
        coarse, lag = sliding_correlation(resample_poly(excerpt, 1, 8), low_long)
        if coarse < SCREEN['coarse_abs_correlation_min']:
            continue
        # Coarse downsampling may move the best alignment by several samples.
        first = max(0, lag * 8 - 16)
        last = min(len(long) - n, lag * 8 + 16)
        if last >= first:
            full, _ = sliding_correlation(excerpt, long[first:last+n])
            best = max(best, full)
    return best


def short_record(row: dict, reasons: list[str]) -> dict:
    return {**{k: row.get(k) for k in ('recording_id', 'dataset_id', 'source_type',
            'subject_id', 'merged_subject_id', 'dataset_group', 'age_group',
            'original_sha256', 'derived_sha256', 'quality_status', 'source_purity_tier')},
            'reasons': sorted(set(reasons))}


def freeze(rows: list[dict], config: dict) -> tuple[dict, dict]:
    if (config['sample_rate'] != 4000 or config['crop_samples'] != 32000 or
            set(config['datasets']) != set(DATASETS) or config['test_access_allowed']):
        raise ValueError('Config is not the approved external-only pilot contract')
    if len(rows) > 2 * config['pilot_candidate_subject_groups_per_dataset'] * config['pilot_max_recordings_per_subject_group']:
        raise ValueError('Registry exceeds bounded pilot acquisition size')
    keys = [(r['dataset_id'], r['recording_id']) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate registry row identifiers')
    rows = sorted((dict(r) for r in rows), key=lambda r: (r['dataset_id'], r['recording_id']))
    reasons = [list(r.get('exclusion_reasons', [])) for r in rows]
    arrays, fps = {}, {}
    for i, row in enumerate(rows):
        if row['dataset_id'] not in DATASETS:
            raise ValueError('Only explicitly selected external datasets are allowed')
        group, kind = DATASETS[row['dataset_id']]
        if row['source_type'] != kind:
            raise ValueError('Dataset/source semantic mismatch')
        row['dataset_group'] = group
        row['access_terms'] = row.get('access_terms') or ('ODC-By 1.0; attribution required' if group == 'circor'
                                                       else 'CC BY 4.0; attribution required')
        row['official_license_url'] = ('https://physionet.org/content/circor-heart-sound/1.0.3/LICENSE.txt' if group == 'circor'
            else 'https://github.com/SJTU-YONGFU-RESEARCH-GRP/SPRSound/blob/bca1e51422a42a042441010081519610ef3845d0/LICENSE')
        subject = row.get('subject_id')
        if subject is None or str(subject).strip().lower() in {'', 'none', 'null', 'unknown', 'nan'}:
            reasons[i].append('missing_subject_id')
        row['merged_subject_id'] = str(subject) if subject is not None else None
        # CirCor components were formed from Additional ID before acquisition.
        row['subject_id'] = row['merged_subject_id']
        original = external_path(row['original_path'])
        if sha256_file(original) != row['original_sha256']:
            raise ValueError('Immutable original hash changed')
        if row.get('source_purity_tier') != 'B' or not all(row.get(k) for k in
                ('source_purity_confidence', 'source_purity_evidence', 'purity_reviewer')):
            reasons[i].append('not_qualified_tier_b')
        if row.get('quality_status') != 'TIER_B_CANDIDATE_PENDING_SIGNAL_REVIEW':
            reasons[i].append('not_annotation_technical_candidate')
        if row.get('age_group') not in AGES:
            reasons[i].append('unknown_or_unsupported_age_domain')
        if group == 'sprsound':
            age = row.get('age')
            if not isinstance(age, (int, float)) or not np.isfinite(age) or not 0 <= age <= 18:
                reasons[i].append('unsupported_sprsound_age')
            elif row['age_group'] != ('Infant' if age <= 1 else 'Child' if age < 12 else 'Adolescent'):
                raise ValueError('SPRSound age-bin mismatch')
        if not row.get('family_id'):
            reasons[i].append('missing_released_sound_label')
        if not row.get('derived_path'):
            reasons[i].append('no_canonical_derivation')
            continue
        derived = external_path(row['derived_path'])
        if sha256_file(derived) != row['derived_sha256']:
            raise ValueError('Canonical artifact hash changed')
        x = np.load(derived, mmap_mode='r', allow_pickle=False)
        if (x.ndim != 1 or x.dtype != np.dtype('<f4') or not np.isfinite(x).all() or
                row.get('canonical_sample_rate') != 4000 or row.get('canonical_channel_count') != 1 or
                len(x) != row.get('canonical_samples')):
            raise ValueError('Canonical waveform contract mismatch')
        waveform_sha = hashlib.sha256(x.tobytes()).hexdigest()
        if row.get('canonical_waveform_sha256') != waveform_sha:
            raise ValueError('Canonical waveform hash mismatch')
        intervals = row.get('valid_intervals_4k', [])
        previous_end = 0
        for interval in intervals:
            if (not isinstance(interval, list) or len(interval) != 2 or
                    not all(isinstance(v, int) and not isinstance(v, bool) for v in interval)):
                reasons[i].append('invalid_qualified_interval_format')
                break
            a, b = interval
            if not 0 <= previous_end <= a < b <= len(x) or b-a < 32000:
                reasons[i].append('invalid_qualified_interval_bounds_duration_or_overlap')
                break
            previous_end = b
        if not intervals:
            reasons[i].append('no_valid_8s_interval')
        if len(x) >= 32000:
            arrays[i] = x
            fps[i] = fingerprint(x)

    # All qualified/excluded records with hashes participate before any split.
    exact_groups = []
    for field in ('original_sha256', 'canonical_waveform_sha256', 'derived_sha256'):
        groups = defaultdict(list)
        for i, row in enumerate(rows):
            if row.get(field):
                groups[row[field]].append(i)
        exact_groups.extend(group for group in groups.values() if len(group) > 1)
    parents = list(range(len(rows)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for group in exact_groups:
        for i in group[1:]:
            parents[find(i)] = find(group[0])
    clusters = defaultdict(list)
    for i in range(len(rows)):
        clusters[find(i)].append(i)
    exact_evidence = []
    for cluster in clusters.values():
        if len(cluster) < 2:
            continue
        subjects = {(rows[i]['dataset_group'], rows[i]['merged_subject_id']) for i in cluster}
        cross_subject = len(subjects) > 1
        keep = min(cluster, key=lambda i: (bool(reasons[i]), i))
        for i in cluster:
            if cross_subject or i != keep:
                reasons[i].append('exact_duplicate_cross_subject_cluster' if cross_subject else 'exact_duplicate_same_subject')
        exact_evidence.append({'records': [f"{rows[i]['dataset_id']}:{rows[i]['recording_id']}" for i in cluster],
                               'action': 'exclude_cluster' if cross_subject else 'keep_first_eligible_only'})

    # Screen all technically readable >=8s records, including prior exclusions.
    indices = sorted(fps)
    candidates = set()
    if len(indices) > 1:
        matrix = np.stack([fps[i] for i in indices])
        similarity = matrix @ matrix.T
        for a, i in enumerate(indices):
            neighbors = sorted((b for b in range(len(indices)) if b != a),
                               key=lambda b: (-similarity[a, b], indices[b]))[:SCREEN['neighbors_per_record']]
            candidates.update(tuple(sorted((i, indices[b]))) for b in neighbors)
    near_evidence = []
    comparisons = 0
    for i, j in sorted(candidates):
        if find(i) == find(j):
            continue
        score = near_copy_score(arrays[i], arrays[j])
        comparisons += 1
        if score >= SCREEN['full_rate_abs_correlation_uncertain']:
            label = 'probable_near_duplicate' if score >= SCREEN['full_rate_abs_correlation_probable'] else 'uncertain_near_duplicate'
            reasons[i].append(label)
            reasons[j].append(label)
            near_evidence.append({'a': f"{rows[i]['dataset_id']}:{rows[i]['recording_id']}",
                                  'b': f"{rows[j]['dataset_id']}:{rows[j]['recording_id']}",
                                  'abs_correlation': score, 'classification': label,
                                  'action': 'exclude_both_not_adjudicated'})
    # A duplicate of a near-copy must not survive merely because its exact copy
    # was excluded already. Propagate exclusions through exact duplicate clusters.
    for cluster in clusters.values():
        if any(any('near_duplicate' in reason for reason in reasons[i]) for i in cluster):
            for i in cluster:
                reasons[i].append('near_duplicate_linked_exact_cluster')

    shared = set.intersection(*(set(rows[i]['age_group'] for i in range(len(rows))
                     if not reasons[i] and rows[i]['source_type'] == kind) for kind in ('heart', 'lung')))
    for i, row in enumerate(rows):
        if row.get('age_group') not in shared:
            reasons[i].append('age_domain_not_shared_by_eligible_sources')
        if not reasons[i]:
            row['partition'] = subject_partition(row['dataset_group'], row['merged_subject_id'])
    # Both train and external sanity must support shared age-compatible pairing.
    train_shared = set.intersection(*(set(r['age_group'] for i, r in enumerate(rows)
                 if not reasons[i] and r['source_type'] == kind and r['partition'] == 'train')
                 for kind in ('heart', 'lung')))
    validation_shared = set.intersection(*(set(r['age_group'] for i, r in enumerate(rows)
                 if not reasons[i] and r['source_type'] == kind and r['partition'] == 'external_validation')
                 for kind in ('heart', 'lung')))
    for i, row in enumerate(rows):
        if not reasons[i] and row['age_group'] not in (train_shared if row['partition'] == 'train' else validation_shared):
            reasons[i].append('age_domain_not_shared_within_partition')
    accepted = [r for i, r in enumerate(rows) if not reasons[i]]
    for row in accepted:
        row['original_quality_status'] = row['quality_status']
        row['quality_status'] = 'ELIGIBLE_IMPERFECT_SOURCE_PRETRAINING'
        row['original_purity_reviewer'] = row['purity_reviewer']
        row['purity_reviewer'] = ('protocol_and_annotation_audit_plus_bounded_representative_signal_review; '
                                  'not_individual_clinician_listening_or_clean_reference_certification')
    excluded = [short_record(r, reasons[i]) for i, r in enumerate(rows) if reasons[i]]
    counts = {}
    for kind in ('heart', 'lung'):
        counts[kind] = {}
        for part in ('train', 'external_validation'):
            selected = [r for r in accepted if r['source_type'] == kind and r['partition'] == part]
            counts[kind][part] = {'recordings': len(selected), 'subjects': len({r['merged_subject_id'] for r in selected}),
                'age_groups': dict(Counter(r['age_group'] for r in selected)),
                'valid_interval_seconds': sum((b-a)/4000 for r in selected for a,b in r['valid_intervals_4k'])}
    partitions = defaultdict(set)
    for row in accepted:
        partitions[(row['dataset_group'], row['merged_subject_id'])].add(row['partition'])
    if any(len(values) != 1 for values in partitions.values()):
        raise AssertionError('Subject leakage')
    gate = all(counts[k]['train']['subjects'] >= config['minimum_training_subjects_each_source']
               and counts[k]['external_validation']['subjects'] > 0 for k in ('heart', 'lung'))
    summary = {'status': 'FROZEN_PILOT_ELIGIBLE' if gate else 'REJECTED_INSUFFICIENT_QUALIFIED_SUBJECTS',
               'counts': counts, 'input_records': len(rows), 'accepted_records': len(accepted),
               'excluded_records': len(excluded), 'minimum_train_subjects_per_source': config['minimum_training_subjects_each_source'],
               'shared_train_age_domains': sorted(train_shared), 'shared_validation_age_domains': sorted(validation_shared),
               'near_copy_candidate_pairs': len(candidates), 'near_copy_comparisons': comparisons,
               'exact_duplicate_clusters': exact_evidence, 'near_copy_flags': near_evidence,
               'duplicate_screen': SCREEN, 'all_rows_accounted_for': len(accepted)+len(excluded) == len(rows),
               'source_purity': 'Tier B imperfect source-dominant targets, NEVER isolated clean references',
               'test_audio_accessed': False}
    return {'recordings': accepted, 'exclusions': excluded}, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DATA/'pilot-acquisition-v1/registry-v2.json')
    parser.add_argument('--config', type=Path, default=ROOT/'research/configs/external_pretraining_pilot_v1.json')
    parser.add_argument('--review', type=Path, default=DATA/'qualification-v1/source_review_selection.json')
    parser.add_argument('--output', type=Path, default=DATA/'pilot-acquisition-v1/accepted-registry-v1.json')
    parser.add_argument('--manifest', type=Path, default=ROOT/'research/manifests/external_pilot_registry_v1.json')
    args = parser.parse_args()
    source, review, output = map(external_path, (args.input, args.review, args.output))
    if not args.manifest.resolve().is_relative_to((ROOT/'research/manifests').resolve()):
        raise ValueError('Tracked output must be metadata under research/manifests')
    review_records = json.loads(review.read_text())
    if not review_records:
        raise ValueError('Missing prior representative signal-review selection evidence')
    rows = json.loads(source.read_text())
    result, summary = freeze(rows, json.loads(args.config.read_text()))
    result['provenance'] = {
        'schema_version': 1, 'status': summary['status'], 'source_registry_path': str(source.relative_to(ROOT)),
        'source_registry_sha256': sha256_file(source), 'config_path': str(args.config.resolve().relative_to(ROOT)),
        'config_sha256': sha256_file(args.config), 'signal_review_selection_sha256': sha256_file(review),
        'qualification_protocol_sha256': sha256_file(ROOT/'docs/EXTERNAL_DATA_QUALIFICATION_PROTOCOL.md'),
        'script_sha256': sha256_file(Path(__file__)),
        'implementation_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'implementation_worktree_clean': not bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
        'holdout_rule': "int(sha256('external-v1:' + dataset_group + ':' + merged_subject_id).hexdigest(),16) % 10 == 0",
        'source_purity_assumption': 'Imperfect Tier B; no clinical listening or clean-reference certification',
        'duplicate_screen': SCREEN}
    save_json(output, result)
    fields = ('recording_id', 'dataset_id', 'dataset_group', 'source_type', 'subject_id', 'merged_subject_id',
              'partition', 'family_id', 'age_group', 'original_sha256', 'derived_sha256',
              'canonical_waveform_sha256', 'canonical_samples', 'valid_intervals_4k', 'source_purity_tier',
              'quality_status', 'original_quality_status', 'access_terms', 'official_license_url')
    manifest = {'provenance': result['provenance'], 'registry_sha256': sha256_file(output),
                'recordings': [{k: r[k] for k in fields} for r in result['recordings']],
                'exclusions': result['exclusions'], 'summary': summary}
    save_json(args.manifest, manifest)
    summary.update({'registry_sha256': sha256_file(output), 'tracked_manifest_sha256': sha256_file(args.manifest)})
    summary_path = output.parent/'freeze-summary-v1.json'
    save_json(summary_path, summary)
    print(json.dumps({'status': summary['status'], 'counts': summary['counts'],
                      'registry_sha256': summary['registry_sha256'],
                      'manifest_sha256': summary['tracked_manifest_sha256'],
                      'summary_sha256': sha256_file(summary_path)}, indent=2))
    if summary['status'] != 'FROZEN_PILOT_ELIGIBLE':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
