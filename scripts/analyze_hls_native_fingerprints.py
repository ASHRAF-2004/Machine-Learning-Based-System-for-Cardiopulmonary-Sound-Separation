"""Bounded NON-TEST HLS replay fingerprints and native/synthetic descriptors.

No model/optimizer imports. Native access is guarded by registry identity and
underlying family exclusion; standalone access is restricted to the pinned
86-source non-test allowlist. Correlation/PSD similarity are not identity proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import wave
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.signal import correlate, welch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.training_data import make_mixture, read_manifest, read_source
from scripts.audit_hls_native_registry import (ELIGIBLE, EXPECTED, MANIFEST,
                                                authorized_native_path, read_csv, sha256)

REGISTRY = ROOT / 'research/manifests/hls_native_triplets_v1.json'
RATE = 4000
BANDS = [(0, 50), (50, 100), (100, 200), (200, 400), (400, 800), (800, 2000.1)]


def summary(values) -> dict:
    values = np.asarray(list(values), dtype=float)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError('Empty or nonfinite diagnostic vector')
    return {'n': len(values), 'mean': float(values.mean()), 'median': float(np.median(values)),
            'p25': float(np.quantile(values, .25)), 'p75': float(np.quantile(values, .75)),
            'min': float(values.min()), 'max': float(values.max())}


def lagged_match(template: np.ndarray, source: np.ndarray,
                 nominal_start: int = 24000, max_lag: int = 16000) -> dict:
    """Centered normalized correlation; source lag is relative to nominal start.

    Template is native [6,9) seconds. Search source starts [2,10] seconds,
    i.e. +/-4 seconds about nominal6s, preserving a complete three-second match.
    """
    template = np.asarray(template, dtype=np.float64)
    template = template - template.mean()
    first = max(0, nominal_start - max_lag)
    last = min(len(source) - len(template), nominal_start + max_lag)
    signal = np.asarray(source[first:last + len(template)], dtype=np.float64)
    n = len(template)
    sums = np.r_[0., np.cumsum(signal)]
    squares = np.r_[0., np.cumsum(signal * signal)]
    local_sum = sums[n:] - sums[:-n]
    local_var = np.maximum(squares[n:] - squares[:-n] - local_sum ** 2 / n, 0)
    numerator = correlate(signal, template, mode='valid', method='fft')
    denominator = np.sqrt(local_var * np.dot(template, template))
    correlations = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 1e-20)
    best = int(np.argmax(np.abs(correlations)))
    return {'absolute_correlation': float(min(abs(correlations[best]), 1.)),
            'signed_correlation': float(np.clip(correlations[best], -1, 1)),
            'source_start_sample': first + best,
            'source_start_lag_seconds': (first + best - nominal_start) / RATE}


def synthetic_check() -> dict:
    rng = np.random.default_rng(20260928)
    source = rng.normal(size=60000)
    start = 24000 + 1234
    template = -2.7 * source[start:start + 12000] + 5.4
    result = lagged_match(template, source)
    assert result['absolute_correlation'] > .999999999
    assert result['signed_correlation'] < -.999999999
    assert result['source_start_sample'] == start
    return {'status': 'PASS', 'known_lag_samples': 1234, 'recovered_lag_samples': result['source_start_sample'] - 24000,
            'gain_and_dc_invariant': True, 'polarity_recovered': 'negative', 'correlation': result['absolute_correlation']}


def psd(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return welch(x.astype(np.float64), fs=RATE, nperseg=2048, noverlap=1024, detrend='constant')


def psd_shape(x: np.ndarray) -> np.ndarray:
    frequency, power = psd(x)
    power = power[frequency >= 20]
    return power / max(float(power.sum()), 1e-30)


def descriptors(x: np.ndarray) -> dict:
    y = x.astype(np.float64)
    rms = float(np.sqrt(np.mean(y * y)))
    peak = float(np.max(np.abs(y)))
    f, p = psd(y)
    total = max(float(p.sum()), 1e-30)
    positive = p[f >= 20]
    blocks = y[:len(y) // 200 * 200].reshape(-1, 200)
    envelope = np.sqrt(np.mean(blocks * blocks, axis=1))
    low = float(np.quantile(envelope, .1))
    high = float(np.quantile(envelope, .9))
    ef, ep = welch(envelope - envelope.mean(), fs=20, nperseg=min(256, len(envelope)))
    return {'rms': rms, 'peak': peak, 'peak_normalized_rms': rms / max(peak, 1e-30),
            'crest_factor': peak / max(rms, 1e-30), 'dc': float(y.mean()),
            'centroid_hz': float(np.sum(f * p) / total),
            'flatness_20_2000hz': float(np.exp(np.log(np.maximum(positive, 1e-30)).mean()) / max(float(positive.mean()), 1e-30)),
            'low_50ms_rms_p10': low, 'low_50ms_rms_p10_over_record_rms': low / max(rms, 1e-30),
            'envelope_p90_to_p10_db': float(20 * np.log10(max(high, 1e-30) / max(low, 1e-30))),
            'envelope_cv': float(envelope.std() / max(float(envelope.mean()), 1e-30)),
            'envelope_modulation_0p1_to_2hz_fraction': float(ep[(ef >= .1) & (ef < 2)].sum() / max(float(ep.sum()), 1e-30)),
            **{f'band_{lo:g}_{min(hi, 2000):g}hz_fraction': float(p[(f >= lo) & (f < hi)].sum() / total) for lo, hi in BANDS}}


def read_native(row: dict, role: str) -> np.ndarray:
    file = row['files'][role]
    path = authorized_native_path(row, file['path'])
    if sha256(path) != file['sha256']:
        raise ValueError('Native source bytes changed')
    with wave.open(str(path), 'rb') as wav:
        if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getnframes()) != (4000, 1, 2, 60000):
            raise ValueError('Native header contract changed')
        data = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(np.float32) / 32768.
    if not np.isfinite(data).all():
        raise ValueError('Nonfinite native audio')
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic-check-only', action='store_true')
    parser.add_argument('--output', default='research/evidence/hls_native_fingerprints_v1.json')
    parser.add_argument('--details', default='.local/training/hls-native-audit-v1/fingerprints_details_v1.json')
    args = parser.parse_args()
    check = synthetic_check()
    if args.synthetic_check_only:
        print(json.dumps(check, indent=2)); return
    start = time.perf_counter()
    if sha256(ELIGIBLE) != EXPECTED[ELIGIBLE]:
        raise ValueError('Non-test allowlist changed')
    registry = json.loads(REGISTRY.read_text())
    rows = [r for r in registry['rows'] if r['eligible_non_test']]
    if len(rows) != 100 or any(r['exclusion_reasons'] for r in rows):
        raise ValueError('Expected exact conservative 100-triplet non-test population')
    sources = read_manifest(ELIGIBLE)
    if len(sources) != 86 or any(s.split not in {'development', 'validation'} for s in sources):
        raise ValueError('Unexpected non-test standalone pool')
    # Read full manifest only for already-authorized source metadata; never audio.
    if sha256(MANIFEST) != EXPECTED[MANIFEST]:
        raise ValueError('Frozen metadata changed')
    frozen_metadata = read_csv(MANIFEST)
    metadata = {(r['kind'], r['id']): r for r in frozen_metadata if r['split'] != 'test'}
    sealed_hashes = {r['sha256'] for r in frozen_metadata if r['split'] == 'test'}
    if any(f['sha256'] in sealed_hashes for row in rows for f in row['files'].values()):
        raise ValueError('Native hash matches sealed T9 metadata; do not decode')
    audio = {}
    spectra = {}
    for source in sources:
        if sha256(source.path) != source.sha256:
            raise ValueError('Standalone non-test source changed')
        audio[(source.kind, source.id)] = read_source(source)
        spectra[(source.kind, source.id)] = psd_shape(audio[(source.kind, source.id)])
    fingerprints = []
    domains = []
    selected_sources = []
    native_hashes = set()
    for row in rows:
        native = {role: read_native(row, role) for role in ('mixture', 'heart', 'lung')}
        for role, kind in (('heart', 'HS'), ('lung', 'LS')):
            target = native[role]
            shape = psd_shape(target)
            family = row[f'{role}_family']
            candidates = []
            for source in sources:
                if source.kind != kind:
                    continue
                match = lagged_match(target[24000:36000], audio[(kind, source.id)])
                match.update({'standalone_id': source.id, 'family': source.family, 'same_family': source.family == family,
                              'exact_file_hash': source.sha256 == row['files'][role]['sha256'],
                              'psd_20_2000hz_bhattacharyya': float(np.sqrt(shape * spectra[(kind, source.id)]).sum())})
                candidates.append(match)
            same = max((c for c in candidates if c['same_family']), key=lambda c: (c['absolute_correlation'], c['standalone_id']))
            other = max((c for c in candidates if not c['same_family']), key=lambda c: (c['absolute_correlation'], c['standalone_id']))
            overall = max(candidates, key=lambda c: (c['absolute_correlation'], c['standalone_id']))
            best_psd = max(candidates, key=lambda c: (c['psd_20_2000hz_bhattacharyya'], c['standalone_id']))
            fingerprints.append({'triplet_id': row['triplet_id'], 'role': role, 'family': family,
                                 'native_sha256': row['files'][role]['sha256'], 'exact_hash_matches': sum(c['exact_file_hash'] for c in candidates),
                                 'best_same_family': same, 'best_other_family': other,
                                 'best_overall': overall, 'best_psd_overall': best_psd,
                                 'candidates': candidates})
            native_hashes.add(row['files'][role]['sha256'])
        domains.append({'triplet_id': row['triplet_id'], 'domain': 'native',
                        'family_pair_id': row['family_pair_id'], 'descriptors': descriptors(native['mixture'])})
        chosen = {}
        for role, kind in (('heart', 'HS'), ('lung', 'LS')):
            def key(source):
                meta = metadata[(kind, source.id)]
                return (meta['location'] != row['recording_position'],
                        meta['gender'] != row['manikin_gender_label'], source.id)
            chosen[role] = min((s for s in sources if s.kind == kind and s.family == row[f'{role}_family']), key=key)
        for level in (-10, -5, 0, 5, 10):
            h, l = chosen['heart'], chosen['lung']
            mixture, _, gain = make_mixture(audio[('HS', h.id)], audio[('LS', l.id)], level, crop_samples=60000)
            domains.append({'triplet_id': row['triplet_id'], 'domain': 'synthetic', 'relative_db': level,
                            'family_pair_id': row['family_pair_id'], 'heart_id': h.id, 'lung_id': l.id,
                            'gain': gain, 'descriptors': descriptors(mixture)})
        selected_sources.append({'triplet_id': row['triplet_id'], 'heart_id': chosen['heart'].id, 'lung_id': chosen['lung'].id})
    role_summary = {}
    for role in ('heart', 'lung'):
        selected = [r for r in fingerprints if r['role'] == role]
        role_summary[role] = {
            'native_reference_count': len(selected), 'standalone_candidates_per_reference': sum(s.kind == ('HS' if role == 'heart' else 'LS') for s in sources),
            'exact_hash_matches': sum(r['exact_hash_matches'] for r in selected),
            'best_overall_same_family_count': sum(r['best_overall']['same_family'] for r in selected),
            'best_psd_same_family_count': sum(r['best_psd_overall']['same_family'] for r in selected),
            'best_same_family_correlation': summary(r['best_same_family']['absolute_correlation'] for r in selected),
            'best_other_family_correlation': summary(r['best_other_family']['absolute_correlation'] for r in selected),
            'same_minus_other_correlation': summary(r['best_same_family']['absolute_correlation'] - r['best_other_family']['absolute_correlation'] for r in selected),
            'same_family_best_psd_similarity': summary(max(c['psd_20_2000hz_bhattacharyya'] for c in r['candidates'] if c['same_family']) for r in selected),
            'other_family_best_psd_similarity': summary(max(c['psd_20_2000hz_bhattacharyya'] for c in r['candidates'] if not c['same_family']) for r in selected),
            'best_same_family_abs_correlation_ge_0p8': sum(r['best_same_family']['absolute_correlation'] >= .8 for r in selected),
            'best_same_family_abs_correlation_ge_0p9': sum(r['best_same_family']['absolute_correlation'] >= .9 for r in selected),
            'best_same_family_abs_correlation_ge_0p95': sum(r['best_same_family']['absolute_correlation'] >= .95 for r in selected),
            'best_same_family_lag_seconds': summary(r['best_same_family']['source_start_lag_seconds'] for r in selected),
            'negative_best_same_family_polarity_count': sum(r['best_same_family']['signed_correlation'] < 0 for r in selected),
            'non_exact_reference_same_family_correlation': summary(r['best_same_family']['absolute_correlation'] for r in selected if not r['exact_hash_matches']),
            'by_family': {family: {'n': sum(r['family'] == family for r in selected),
                                    'same_family_correlation': summary(r['best_same_family']['absolute_correlation'] for r in selected if r['family'] == family),
                                    'other_family_correlation': summary(r['best_other_family']['absolute_correlation'] for r in selected if r['family'] == family)}
                          for family in sorted({r['family'] for r in selected})},
        }
    descriptor_keys = list(domains[0]['descriptors'])
    domain_summary = {domain: {key: summary(r['descriptors'][key] for r in domains if r['domain'] == domain)
                              for key in descriptor_keys} for domain in ('native', 'synthetic')}
    # One native descriptor vector vs mean of predeclared five levels per triplet;
    # family-pair macro avoids counting heavily represented pairs as independent.
    paired = []
    for row in rows:
        native = next(r for r in domains if r['triplet_id'] == row['triplet_id'] and r['domain'] == 'native')
        synthetic = [r for r in domains if r['triplet_id'] == row['triplet_id'] and r['domain'] == 'synthetic']
        paired.append({'pair': row['family_pair_id'],
                       **{key: native['descriptors'][key] - np.mean([r['descriptors'][key] for r in synthetic]) for key in descriptor_keys}})
    pair_macro = {key: summary(np.mean([r[key] for r in paired if r['pair'] == pair]) for pair in sorted({r['pair'] for r in paired}))
                  for key in descriptor_keys}
    non_test_hash_metadata = {r['sha256']: r for r in metadata.values()}
    reuse = {}
    for role in ('mixture', 'heart', 'lung'):
        groups = {}
        for row in rows:
            groups.setdefault(row['files'][role]['sha256'], []).append(row)
        exact_rows = [(row, non_test_hash_metadata[row['files'][role]['sha256']])
                      for row in rows if row['files'][role]['sha256'] in non_test_hash_metadata]
        reuse[role] = {
            'unique_native_file_hashes': len(groups), 'duplicate_rows_beyond_one_per_hash': len(rows) - len(groups),
            'largest_hash_cluster': max(len(group) for group in groups.values()),
            'hash_clusters_crossing_correspondence_fit_and_holdout': sum(len({r['correspondence_partition'] for r in group}) > 1 for group in groups.values()),
            'exact_standalone_row_matches': len(exact_rows),
            'exact_standalone_unique_ids': len({meta['id'] for _, meta in exact_rows}),
            'exact_copy_family_metadata_disagreement': sum(row.get(f'{role}_family') != meta['family'] for row, meta in exact_rows),
            'exact_copy_position_metadata_disagreement': sum(row['recording_position'] != meta['location'] for row, meta in exact_rows),
            'exact_copy_manikin_gender_metadata_disagreement': sum(row['manikin_gender_label'] != meta['gender'] for row, meta in exact_rows),
            'duplicate_clusters': [{'sha256': digest, 'triplet_ids': [r['triplet_id'] for r in group]}
                                   for digest, group in sorted(groups.items()) if len(group) > 1],
        }
    reuse['triplets_with_both_references_exact_standalone_copies'] = sum(
        row['files']['heart']['sha256'] in non_test_hash_metadata and row['files']['lung']['sha256'] in non_test_hash_metadata for row in rows)
    details = {'fingerprints': fingerprints, 'descriptor_rows': domains, 'synthetic_source_selection': selected_sources}
    detail_path = ROOT / args.details
    detail_path.parent.mkdir(parents=True, exist_ok=True)
    detail_path.write_text(json.dumps(details, indent=2, sort_keys=True) + '\n')
    result = {'schema_version': 1, 'status': 'NON_TEST_SOURCE_FORENSICS_ONLY',
              'registry_sha256': sha256(REGISTRY), 'standalone_allowlist_sha256': sha256(ELIGIBLE),
              'script_sha256': sha256(Path(__file__)), 'test_audio_opened': False, 'training_performed': False,
              'synthetic_correlation_check': check, 'native_triplets_decoded': len(rows), 'standalone_sources_decoded': len(sources),
              'eligible_native_hash_matches_sealed_T9_hash_metadata': 0,
              'native_reference_unique_file_hashes': len(native_hashes),
              'exact_reuse_summary': reuse,
              'native_unique_non_test_heart_families': 8, 'native_unique_non_test_lung_families': 5,
              'new_native_family_categories_beyond_standalone_non_test': 0, 'new_native_pair_categories_beyond_synthetic_cartesian_pool': 0,
              'methods': {'waveform': 'native center [6,9)s template; centered normalized absolute correlation; standalone offset [2,10]s; maximum over +/-4s shifts; gain/DC/polarity invariant; no warp/filter fitting',
                          'PSD': 'Welch 2048/1024 at4k; normalized PSD20..2000Hz Bhattacharyya coefficient; source-shape similarity, not waveform identity',
                          'synthetic_choice': 'same family; prioritize exact CSV location then gender; lexicographic source ID tie-break; fixed five dB values; full15s starts0; frozen make_mixture RMS/common scaling',
                          'noise_proxy': '10th percentile of50ms RMS blocks; contains low-energy physiological signal, NOT measured device/ambient noise floor',
                          'aggregation': 'descriptive row summaries + equal40family-pair mean of native-minus-five-level-synthetic descriptor differences; no confidence intervals'},
              'fingerprint_summary': role_summary, 'descriptor_summary': domain_summary,
              'family_pair_macro_native_minus_synthetic': pair_macro,
              'detail_path': str(detail_path.relative_to(ROOT)), 'detail_sha256': sha256(detail_path),
              'runtime_seconds': time.perf_counter() - start,
              'limitations': ['No new independent subjects: same clinical manikin family labels.',
                              'High lagged waveform correlation may indicate repeated manikin waveform/style but does not identify the hidden playback source.',
                              'Low correlation does not disprove filtered, time-warped, independently phased, or outside-window replay.',
                              'PSD similarity is not source purity or identity evidence.',
                              'Exact source files are reused across native pairs, including correspondence fit/holdout: unseen-pair transfer is not independent-reference generalization.',
                              'Mix.csv position/gender are row-level labels; exact reused references sometimes disagree with standalone metadata, so per-reference location/gender correspondence cannot be assumed.',
                              'Synthetic comparison is predeclared same-family/site-first, not an estimate of actual native source amplitudes.',
                              'Raw RMS scales differ because synthetic common gain is explicit; peak-normalized RMS/crest and PSD descriptors provide amplitude-invariant comparison.',
                              '100 native and500 synthetic rows are correlated repeats over40family pairs; no IID inference.']}
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': str(output.relative_to(ROOT)), 'sha256': sha256(output),
                      'runtime_seconds': result['runtime_seconds'], 'fingerprints': {
                          role: {k: v for k, v in values.items() if k != 'by_family'} for role, values in role_summary.items()}}, indent=2))


if __name__ == '__main__':
    main()
