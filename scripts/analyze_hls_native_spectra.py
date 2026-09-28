"""Predeclared global PSD correspondence diagnostic; no separator training.

Only authorized non-test native triplet files may be decoded. Welch uses Hann,
2048 samples, 1024 overlap, constant detrend, density scaling, mean averaging.
For each frequency fit nonnegative ridge least squares [P_h,P_l] -> P_m with
equal family-pair weight then equal recording weight, all PSDs divided by the
same recording's mixture variance. Ridge=.01*trace(X'WX), toward zero.
Solve the two-variable nonnegative problem exactly, smooth each response with
a 9-bin arithmetic moving average (nearest boundary), clip to [0,100]. No
per-record fit, gain normalization, or held-out tuning. Report only 20–1800 Hz.

Counterfactuals are chosen before audio access by SHA256 seeded metadata:
wrong heart, wrong lung, both wrong, and same-family alternative references.
Candidates come ONLY from the fitting partition; same recording site preferred.
No waveform or score is used to select a counterfactual.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import scipy
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d
from scipy.signal import csd, welch

from audit_hls_native_registry import ROOT, authorized_native_path, sha256

REGISTRY = ROOT / 'research/manifests/hls_native_triplets_v1.json'
CONFIG = ROOT / 'research/configs/hls_native_forensics_v1.json'
SEED = 20260928


def nn_ridge(h: np.ndarray, l: np.ndarray, m: np.ndarray, weights: np.ndarray,
             ridge: float) -> np.ndarray:
    """Exact nonnegative two-regressor ridge solution, independent per bin."""
    a = np.sum(weights[:, None] * h * h, axis=0)
    b = np.sum(weights[:, None] * h * l, axis=0)
    d = np.sum(weights[:, None] * l * l, axis=0)
    u = np.sum(weights[:, None] * h * m, axis=0)
    v = np.sum(weights[:, None] * l * m, axis=0)
    penalty = ridge * (a + d)
    a, d = a + penalty, d + penalty
    det = a * d - b * b
    det = np.maximum(det, np.finfo(np.float64).tiny)
    unconstrained = np.stack(((d * u - b * v) / det, (a * v - b * u) / det))
    edge_h = np.stack((np.maximum(u / np.maximum(a, 1e-300), 0), np.zeros_like(u)))
    edge_l = np.stack((np.zeros_like(v), np.maximum(v / np.maximum(d, 1e-300), 0)))
    candidates = np.stack((unconstrained, edge_h, edge_l, np.zeros_like(unconstrained)))
    costs = (a * candidates[:, 0] ** 2 + 2 * b * candidates[:, 0] * candidates[:, 1]
             + d * candidates[:, 1] ** 2 - 2 * u * candidates[:, 0] - 2 * v * candidates[:, 1])
    costs[np.any(candidates < 0, axis=1)] = np.inf
    best = np.argmin(costs, axis=0)
    return np.stack((candidates[best, 0, np.arange(len(a))],
                     candidates[best, 1, np.arange(len(a))]))


def synthetic_sanity() -> dict:
    """No HLS bytes opened; detects regressor order/sign/ridge wiring defects."""
    rng = np.random.default_rng(SEED)
    h, l = rng.uniform(.1, 2, (2, 20, 8))
    target = 2 * h + .3 * l
    weights = np.ones(20) / 20
    result = nn_ridge(h, l, target, weights, 0)
    assert np.max(np.abs(result - np.array([[2], [.3]]))) < 1e-10
    boundary = nn_ridge(h, l, 2 * h - .5 * l, weights, .01)
    assert np.all(boundary >= 0) and np.isfinite(boundary).all()
    identical = metrics(target[0], target[0])
    assert identical['hellinger'] == 0 and identical['total_variation'] == 0
    assert identical['log_psd_mae_db'] == 0
    return {'status': 'PASS', 'source': 'generated positive PSD arrays only',
            'known_map_max_absolute_error': float(np.max(np.abs(result - np.array([[2], [.3]])))),
            'nonnegative_boundary_finite': True, 'zero_identical_distances': True}


def metrics(predicted: np.ndarray, observed: np.ndarray) -> dict:
    floor = max(float(np.mean(observed)) * 1e-8, 1e-30)
    p = np.maximum(predicted, 0)
    q = np.maximum(observed, 0)
    pn, qn = p / max(p.sum(), 1e-30), q / max(q.sum(), 1e-30)
    return {'hellinger': float(np.sqrt(.5 * np.sum((np.sqrt(pn) - np.sqrt(qn)) ** 2))),
            'total_variation': float(.5 * np.sum(np.abs(pn - qn))),
            'log_psd_mae_db': float(np.mean(np.abs(10 * np.log10((p + floor) / (q + floor))))),
            'band_power_error_db': float(10 * np.log10((p.sum() + floor) / (q.sum() + floor))),
            'relative_psd_rmse': float(np.sqrt(np.mean((p - q) ** 2) / max(np.mean(q ** 2), 1e-60)))}


def describe(values) -> dict:
    x = np.asarray(values, dtype=np.float64)
    return {'n': len(x), 'mean': float(x.mean()), 'median': float(np.median(x)),
            'q25': float(np.quantile(x, .25)), 'q75': float(np.quantile(x, .75)),
            'min': float(x.min()), 'max': float(x.max())}


def metadata_counterfactuals(rows: list[dict]) -> dict:
    fitting = [r for r in rows if r['correspondence_partition'] == 'fit_pair']
    heldout = [r for r in rows if r['correspondence_partition'] == 'heldout_pair']
    def select(row, role, same_family):
        key = role + '_family'
        candidates = [r for r in fitting if (r[key] == row[key]) == same_family]
        if not candidates:
            raise ValueError('No metadata-only counterfactual candidate')
        same_site = [r for r in candidates if r['recording_position'] == row['recording_position']]
        pool = same_site or candidates
        chosen = min(pool, key=lambda r: hashlib.sha256(
            f'native-psd-counterfactual-v1:{SEED}:{row["triplet_id"]}:{role}:{same_family}:{r["triplet_id"]}'.encode()).hexdigest())
        return {'triplet_id': chosen['triplet_id'], 'family': chosen[key],
                'same_site': chosen['recording_position'] == row['recording_position'],
                'site': chosen['recording_position'], 'source_partition': 'fit_pair'}
    return {r['triplet_id']: {f'{role}_{kind}': select(r, role, kind == 'same')
                              for role in ('heart', 'lung') for kind in ('wrong', 'same')}
            for r in heldout}


def aggregate(records: list[dict], key: str) -> dict:
    grouped = defaultdict(list)
    for r in records:
        grouped[r['family_pair_id']].append(r[key])
    names = next(iter(grouped.values()))[0].keys()
    pairs = {pair: {name: float(np.mean([r[name] for r in values])) for name in names}
             for pair, values in sorted(grouped.items())}
    return {'pair_macro': {name: float(np.mean([r[name] for r in pairs.values()])) for name in names},
            'per_pair_mean': pairs,
            'row_descriptive_not_iid': {name: describe([r[key][name] for r in records]) for name in names}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic-only', action='store_true')
    args = parser.parse_args()
    started = time.perf_counter()
    sanity = synthetic_sanity()
    if args.synthetic_only:
        print(json.dumps(sanity, indent=2))
        return
    config = json.loads(CONFIG.read_text())
    cfg = config['spectral_global_transfer']
    assert cfg['welch_samples'] == 2048 and cfg['welch_overlap'] == 1024
    assert cfg['ridge_trace_fraction'] == .01 and cfg['frequency_smoothing_bins'] == 9
    assert cfg['maximum_power_transfer'] == 100 and cfg['band_hz'] == [20, 1800]
    registry = json.loads(REGISTRY.read_text())
    rows = [r for r in registry['rows'] if r['eligible_non_test'] is True]
    assert len(rows) == 100
    counts = Counter(r['correspondence_partition'] for r in rows)
    assert counts == {'fit_pair': 74, 'heldout_pair': 26}
    cf = metadata_counterfactuals(rows)  # Before any signal access.
    psds, stationary, cross_terms = {}, {}, {}
    welch_args = dict(fs=4000, window='hann', nperseg=2048, noverlap=1024,
                      detrend='constant', scaling='density', average='mean')
    opened = []
    for row in rows:
        signals = {}
        for role in ('mixture', 'heart', 'lung'):
            path = authorized_native_path(row, row['files'][role]['path'])
            if sha256(path) != row['files'][role]['sha256']:
                raise ValueError(f'Eligible native bytes changed: {path}')
            rate, samples = wavfile.read(path)
            assert rate == 4000 and samples.shape == (60000,) and samples.dtype == np.int16
            x = samples.astype(np.float64) / 32768
            assert np.isfinite(x).all() and np.var(x) > 1e-14
            signals[role] = x
            opened.append(str(path.relative_to(ROOT)))
        f, pm = welch(signals['mixture'], **welch_args)
        _, ph = welch(signals['heart'], **welch_args)
        _, pl = welch(signals['lung'], **welch_args)
        band = (f >= 20) & (f <= 1800)
        variance = float(np.var(signals['mixture']))
        psds[row['triplet_id']] = {'mixture': pm, 'heart': ph, 'lung': pl, 'variance': variance}
        station = {}
        for role, x in signals.items():
            _, first = welch(x[:30000], **welch_args)
            _, second = welch(x[30000:], **welch_args)
            station[role] = metrics(first[band], second[band])
        stationary[row['triplet_id']] = station
        _, cross = csd(signals['heart'], signals['lung'], **welch_args)
        _, summed = welch(signals['heart'] + signals['lung'], **welch_args)
        identity_error = float(np.max(np.abs(summed - ph - pl - 2 * cross.real)))
        assert identity_error < 1e-12
        cross_terms[row['triplet_id']] = {
            'sum_psd_cross_term_identity_max_abs_error': identity_error,
            'absolute_cross_term_band_mass_over_source_psd_mass':
                float(np.sum(np.abs(2 * cross.real[band])) / np.sum((ph + pl)[band])),
            'signed_cross_term_band_mass_over_source_psd_mass':
                float(np.sum(2 * cross.real[band]) / np.sum((ph + pl)[band]))}
    fitting = [r for r in rows if r['correspondence_partition'] == 'fit_pair']
    pair_counts = Counter(r['family_pair_id'] for r in fitting)
    assert len(pair_counts) == 32
    weights = np.array([1 / (32 * pair_counts[r['family_pair_id']]) for r in fitting])
    assert np.isclose(weights.sum(), 1)
    arrays = {role: np.stack([psds[r['triplet_id']][role] / psds[r['triplet_id']]['variance']
                             for r in fitting]) for role in ('mixture', 'heart', 'lung')}
    response = nn_ridge(arrays['heart'], arrays['lung'], arrays['mixture'], weights, .01)
    response = np.clip(uniform_filter1d(response, size=9, axis=-1, mode='nearest'), 0, 100)
    assert np.isfinite(response).all() and np.min(response) >= 0
    records = []
    for row in rows:
        ident = row['triplet_id']
        p = psds[ident]
        record = {key: row[key] for key in ('triplet_id', 'family_pair_id', 'correspondence_partition',
                                           'heart_family', 'lung_family', 'recording_position')}
        record['uncorrected'] = metrics((p['heart'] + p['lung'])[band], p['mixture'][band])
        record['global_corrected'] = metrics((response[0] * p['heart'] + response[1] * p['lung'])[band],
                                             p['mixture'][band])
        record['stationarity'] = stationary[ident]
        record['reference_cross_spectrum'] = cross_terms[ident]
        if ident in cf:
            h_wrong = psds[cf[ident]['heart_wrong']['triplet_id']]['heart']
            l_wrong = psds[cf[ident]['lung_wrong']['triplet_id']]['lung']
            h_same = psds[cf[ident]['heart_same']['triplet_id']]['heart']
            l_same = psds[cf[ident]['lung_same']['triplet_id']]['lung']
            for name, h, l in (('wrong_heart', h_wrong, p['lung']), ('wrong_lung', p['heart'], l_wrong),
                                ('both_wrong', h_wrong, l_wrong), ('same_family_alternatives', h_same, l_same)):
                record[name] = metrics((response[0] * h + response[1] * l)[band], p['mixture'][band])
            record['counterfactual_selection'] = cf[ident]
        records.append(record)
    aggregate_by_partition = {}
    for partition in ('fit_pair', 'heldout_pair'):
        subset = [r for r in records if r['correspondence_partition'] == partition]
        names = ['uncorrected', 'global_corrected']
        if partition == 'heldout_pair':
            names += ['wrong_heart', 'wrong_lung', 'both_wrong', 'same_family_alternatives']
        aggregate_by_partition[partition] = {name: aggregate(subset, name) for name in names}
    heldout = [r for r in records if r['correspondence_partition'] == 'heldout_pair']
    contrasts = {}
    for name in ('wrong_heart', 'wrong_lung', 'both_wrong', 'same_family_alternatives'):
        contrast = []
        for row in heldout:
            contrast.append({'family_pair_id': row['family_pair_id'],
                             'delta': {metric: row[name][metric] - row['global_corrected'][metric]
                                       for metric in ('hellinger', 'total_variation', 'log_psd_mae_db')}})
        contrasts[name] = {'counterfactual_minus_correct_error': aggregate(contrast, 'delta'),
                           'correct_lower_error_condition_count': {
                               metric: sum(r['global_corrected'][metric] < r[name][metric] for r in heldout)
                               for metric in ('hellinger', 'total_variation', 'log_psd_mae_db')}}
    output_dir = ROOT / '.local/analysis/hls-native-triplets-v1/spectra'
    output_dir.mkdir(parents=True, exist_ok=True)
    array_path = output_dir / 'global_transfer.npz'
    np.savez(array_path, frequency_hz=f, heart_power_transfer=response[0], lung_power_transfer=response[1])
    detail_path = output_dir / 'per_triplet.json'
    detail_path.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')
    summary = {
        'schema_version': 1, 'status': 'GLOBAL_PSD_CORRESPONDENCE_DIAGNOSTIC_COMPLETE',
        'no_model_training': True, 'no_inference_model_access': True, 'test_audio_access': False,
        'seed': SEED, 'synthetic_sanity_before_audio': sanity,
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'script_sha256': sha256(Path(__file__)), 'config_sha256': sha256(CONFIG),
        'registry_sha256': sha256(REGISTRY), 'numpy_version': np.__version__, 'scipy_version': scipy.__version__,
        'method': __doc__, 'fit_configuration': cfg,
        'epsilon_policy': 'Log PSD epsilon=max(mean observed band PSD * 1e-8,1e-30); no signal-dependent parameter tuning',
        'fit_triplets': 74, 'fit_pairs': 32, 'heldout_triplets': 26, 'heldout_pairs': 8,
        'opened_audio_files': len(opened), 'opened_audio_paths_sha256':
            hashlib.sha256(json.dumps(sorted(opened), separators=(',', ':')).encode()).hexdigest(),
        'per_partition': aggregate_by_partition, 'counterfactual_contrasts': contrasts,
        'stationarity_first_vs_second_half': {role: {
            metric: describe([r['stationarity'][role][metric] for r in records])
            for metric in ('hellinger', 'total_variation', 'log_psd_mae_db', 'band_power_error_db')}
            for role in ('heart', 'lung', 'mixture')},
        'reference_cross_term': {name: describe([r['reference_cross_spectrum'][name] for r in records])
                                 for name in next(iter(cross_terms.values()))},
        'transfer_power_gain_band': {role: describe(response[i, band]) for i, role in enumerate(('heart', 'lung'))},
        'artifact_paths': {'arrays': str(array_path.relative_to(ROOT)), 'arrays_sha256': sha256(array_path),
                           'per_triplet': str(detail_path.relative_to(ROOT)), 'per_triplet_sha256': sha256(detail_path)},
        'runtime_seconds': time.perf_counter() - started,
        'interpretation_limits': [
            'PSD(mixture) includes the cross-spectrum: P(H+L)=PH+PL+2Re(CHL). Ignoring it is an approximation.',
            'Reference cross-spectrum here is between separate recordings, not the unknown mixture-domain source components.',
            'Held-out pairs share constituent families with fitting pairs; no unseen-family generalization claim.',
            'Aggregate spectrum reconstruction cannot identify unique clean heart/lung component targets or waveform phase.',
            'Power transfer does not establish an invertible physical device filter or source-pure supervision.',
            'Counterfactuals preserve native source amplitudes; shape metrics separate gross spectral mismatch from scale.',
            'All condition statistics are descriptive, not IID independent physiological samples.']}
    out = ROOT / 'research/evidence/hls_native_spectra_v1.json'
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': str(out.relative_to(ROOT)), 'sha256': sha256(out),
                      'runtime_seconds': summary['runtime_seconds'],
                      'heldout_macro': {name: value['pair_macro'] for name, value in aggregate_by_partition['heldout_pair'].items()},
                      'counterfactual_correct_win_counts': {name: value['correct_lower_error_condition_count']
                                                            for name, value in contrasts.items()}}, indent=2))


if __name__ == '__main__':
    main()
