"""Technical/annotation qualification of the fixed external sample, not clean labels."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.signal import welch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.external_audio import canonicalize_recording
from scripts.acquire_external_qualification import DATA, digest, save_json


def annotated_intervals(path: Path) -> list[list[int]]:
    spans = []
    start = end = None
    for line in path.read_text().splitlines():
        a, b, label = map(float, line.split())
        # Official files sometimes end with a zero-length unannotated marker.
        # It contains no samples and creates no eligible training interval.
        if label == 0 and b == a:
            continue
        if label not in {0, 1, 2, 3, 4} or b <= a:
            raise ValueError('Invalid official annotation')
        if label == 0:
            if start is not None:
                spans.append([int(np.ceil(start * 4000)), int(np.floor(end * 4000))])
            start = end = None
        elif start is not None and abs(a - end) < 0.00025:
            end = b
        else:
            if start is not None:
                spans.append([int(np.ceil(start * 4000)), int(np.floor(end * 4000))])
            start, end = a, b
    if start is not None:
        spans.append([int(np.ceil(start * 4000)), int(np.floor(end * 4000))])
    return [s for s in spans if s[1] - s[0] >= 32000]


def main(pilot: bool = False) -> None:
    base = DATA / ('pilot-acquisition-v1' if pilot else 'qualification-v1')
    selection = json.loads((base / 'sample_manifest.json').read_text())
    receipts = json.loads((base / 'audio_receipts.json').read_text())
    receipts = {str((ROOT / r['path']).resolve()): r for r in receipts}
    allowlist = {p: r['sha256'] for p, r in receipts.items() if p.endswith('.wav')}
    rows = []
    original_seen = {}
    audio_seen = {}
    for source in selection['records']:
        heart = source['dataset_id'].startswith('circor')
        original = DATA / ('circor-1.0.3/original' if heart else 'sprsound/original') / source['remote_path']
        receipt = receipts[str(original.resolve())]
        meta = source['metadata']
        annotation_error = None
        if heart:
            try:
                intervals = annotated_intervals(original.with_suffix('.tsv'))
            except ValueError as error:
                # Corrupt/unknown official labels are excluded, never repaired
                # into invented cardiac-cycle annotations or replacement cases.
                intervals = []
                annotation_error = str(error)
            annotation = {'record_annotation': meta['Murmur']}
            age = None
            age_group = meta['Age']
            sex = meta['Sex']
            site = source['recording_id'].split('_')[1]
        else:
            annotation_path = Path(str(original).replace('train2022_wav', 'train2022_json')).with_suffix('.json')
            annotation = json.loads(annotation_path.read_text())
            intervals = []  # Full-record interval added only after header/PCM inspection.
            age, sex, site = meta['age_years'], meta['sex'], meta['site']
            age_group = 'Infant' if age <= 1 else ('Child' if age < 12 else 'Adolescent')
        record = {'recording_id': source['recording_id'], 'dataset_id': source['dataset_id'],
                  'dataset_version': '1.0.3' if heart else 'bca1e51422a42a042441010081519610ef3845d0',
                  'source_type': 'heart' if heart else 'lung', 'subject_id': source['subject_id'],
                  'split_group': f"{source['dataset_id']}:{source['subject_id']}",
                  'age': age, 'age_group': age_group, 'sex': sex,
                  'family_id': annotation['record_annotation'],
                  'pathology': meta.get('Outcome') if heart else None,
                  'recording_site': site,
                  'device': 'Littmann 3200' if heart else 'Yunting II',
                  'institution': 'Caravana do Coracao, Northeast Brazil' if heart else 'Shanghai Childrens Medical Center',
                  'original_path': str(original), 'original_sha256': receipt['sha256'],
                  'source_url': receipt['url'],
                  'source_purity_tier': 'UNASSESSED',
                  'notes': 'Clinical source-dominant recording; opposite-source leakage is not excluded. Not an isolated clean reference.'}
        try:
            result = canonicalize_recording(record, authorized_originals=allowlist,
                                             derived_dir=base / 'derived')
        except Exception as error:
            rows.append({**record, 'quality_status': 'EXCLUDED', 'exclusion_reasons': [str(error)]})
            continue
        if not heart and annotation['record_annotation'] != 'Poor Quality':
            intervals = [[0, result['canonical_samples']]] if result['canonical_samples'] >= 32000 else []
        reasons = result['exclusion_reasons']
        if annotation_error:
            reasons.append('invalid_official_annotation:' + annotation_error)
        if not intervals:
            reasons.append('no_contiguous_8s_qualified_interval')
        if heart and meta['Murmur'] == 'Unknown':
            reasons.append('unknown_murmur_quality_control_not_training')
        if not heart and annotation['record_annotation'] == 'Poor Quality':
            reasons.append('official_poor_quality')
        # Conservative technical exclusion, fixed before waveform results.
        if result['original_full_scale_fraction'] >= .001:
            reasons.append('at_least_0.1_percent_full_scale_samples')
        x = np.load(result['derived_path'], allow_pickle=False)
        waveform_hash = digest(x.astype('<f4').tobytes())
        for value, seen, reason in ((result['original_sha256'], original_seen, 'exact_original_duplicate'),
                                    (waveform_hash, audio_seen, 'exact_canonical_audio_duplicate')):
            if value in seen:
                reasons.append(reason + ':' + seen[value])
            else:
                seen[value] = source['recording_id']
        f, power = welch(x, fs=4000, nperseg=min(2048, len(x)))
        bands = [(0, 100), (100, 400), (400, 1000), (1000, 2001)]
        result['spectral_band_energy_fractions'] = [float(power[(f >= lo) & (f < hi)].sum() / (power.sum() + 1e-20)) for lo, hi in bands]
        result['spectral_centroid_hz'] = float((f * power).sum() / (power.sum() + 1e-20))
        result['valid_intervals_4k'] = intervals
        result['annotation'] = annotation
        result['canonical_waveform_sha256'] = waveform_hash
        result['source_purity_tier'] = 'C' if reasons else 'B'
        result['source_purity_confidence'] = 'low_to_medium_not_isolated'
        result['source_purity_evidence'] = ('Expert accepted continuous cardiac-cycle intervals; clinical leakage not ruled out'
            if heart else 'Official non-Poor-Quality respiratory recording/event annotation; cardiac leakage not ruled out')
        result['purity_reviewer'] = 'protocol_and_annotation_audit_not_clinician_listening'
        result['quality_status'] = 'EXCLUDED_FROM_PRETRAINING' if reasons else 'TIER_B_CANDIDATE_PENDING_SIGNAL_REVIEW'
        rows.append(result)
    summary = {}
    for dataset in sorted({r['dataset_id'] for r in rows}):
        group = [r for r in rows if r['dataset_id'] == dataset]
        passed = [r for r in group if not r['exclusion_reasons']]
        summary[dataset] = {'sample_records': len(group), 'sample_subjects': len({r['subject_id'] for r in group}),
                           'candidate_records': len(passed), 'candidate_subjects': len({r['subject_id'] for r in passed}),
                           'sample_duration_seconds': sum(r.get('duration_seconds', 0) for r in group),
                           'candidate_interval_seconds': sum(sum((b-a)/4000 for a,b in r['valid_intervals_4k']) for r in passed),
                           'exclusions': dict(Counter(reason for r in group for reason in r['exclusion_reasons'])),
                           'sample_rates': dict(Counter(str(r.get('original_sample_rate')) for r in group)),
                           'age_groups': dict(Counter(str(r['age_group']) for r in passed)),
                           'labels': dict(Counter(str(r['family_id']) for r in passed))}
    save_json(base / 'registry-v2.json', rows)
    save_json(base / 'summary-v2.json', {'sample_manifest_sha256': digest((base / 'sample_manifest.json').read_bytes()),
                                    'registry_sha256': digest((base / 'registry-v2.json').read_bytes()),
                                    'summary': summary, 'purity_is_not_proven_by_statistics': True})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot', action='store_true')
    main(parser.parse_args().pilot)
