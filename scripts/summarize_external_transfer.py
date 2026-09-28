"""Predeclared family-macro control selection and external-transfer decision.

Reads experiment metadata/metric rows only. Never loads audio or checkpoints.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def save(path, data):
    payload = json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != payload:
        raise FileExistsError('Decision receipts are immutable')
    if not path.exists():
        path.write_text(payload)


def metrics(rows):
    groups = defaultdict(list)
    for row in rows:
        if not all(math.isfinite(row[f'{s}_si_{m}_db']) for s in ('heart', 'lung') for m in ('sdr', 'sdri')):
            raise ValueError('Nonfinite evidence cannot be silently dropped')
        groups[(row['heart_family'], row['lung_family'])].append(row)
    family = {}
    for pair, values in sorted(groups.items()):
        item = {f'{s}_{m}': float(np.mean([r[f'{s}_si_{m}_db'] for r in values]))
                for s in ('heart', 'lung') for m in ('sdr', 'sdri')}
        item.update({'conditions': len(values), 'Q': min(item['heart_sdri'], item['lung_sdri']),
                     'M': (item['heart_sdri'] + item['lung_sdri']) / 2})
        family[' | '.join(pair)] = item
    result = {f'{s}_{m}': float(np.mean([g[f'{s}_{m}'] for g in family.values()]))
              for s in ('heart', 'lung') for m in ('sdr', 'sdri')}
    result.update({'Q': min(result['heart_sdri'], result['lung_sdri']),
                   'M': (result['heart_sdri'] + result['lung_sdri']) / 2,
                   'conditions': len(rows), 'family_pair_count': len(family), 'family_pairs': family,
                   'failures': 0,
                   'negative_rate_percent': {s: 100 * float(np.mean([r[f'{s}_si_sdri_db'] < 0 for r in rows]))
                                             for s in ('heart', 'lung')}})
    return result


def absolute_gate(result):
    return (result['heart_sdri'] >= 1 and result['lung_sdri'] >= 1 and result['failures'] == 0
            and all(g[f'{s}_sdri'] >= 0 for g in result['family_pairs'].values() for s in ('heart', 'lung')))


def collect(root, prefix, plan, update):
    rows, folds, files, manifests = [], {}, {}, {}
    plan_hash = sha(plan)
    spec = json.loads(plan.read_text())
    for fold in spec['folds']:
        directory = root / f"{prefix}-{fold['id']}-seed20260928"
        manifest_path = directory / 'run_manifest.json'
        manifest = json.loads(manifest_path.read_text())
        if (manifest['status'] != 'COMPLETE_FIXED_ENDPOINT' or manifest['failures'] != 0 or
                manifest['provenance']['plan_sha256'] != plan_hash or
                manifest['provenance']['fold'] != fold['id'] or
                manifest['provenance']['seed'] != 20260928):
            raise ValueError('Incomplete/foreign experiment cannot enter selection')
        p = manifest['provenance']
        if (manifest['optimizer_updates'] != spec['cv_max_optimizer_updates_per_fold'] or
                p['architecture_version'] != spec['architecture_version'] or
                p['parameter_count'] != spec['parameter_count'] or
                p['eligible_manifest_sha256'] != spec['eligible_manifest_sha256'] or
                p['initialization_checkpoint_sha256'] != spec.get('initialization_checkpoint_sha256')):
            raise ValueError('Experiment model/data/initialization/budget differs from plan')
        path = directory / f'validation-{update:04d}.jsonl'
        values = read_rows(path)
        if len(values) != fold['validation_conditions']:
            raise ValueError('Missing validation conditions')
        rows.extend(values)
        folds[fold['id']] = metrics(values)
        files[str(path)] = sha(path)
        files[str(manifest_path)] = sha(manifest_path)
        manifests[fold['id']] = manifest
    result = metrics(rows)
    if len({json.dumps(m['provenance']['git'], sort_keys=True) for m in manifests.values()}) != 1:
        raise ValueError('Fold code provenance differs within this experiment arm')
    if len({r['mixture_id'] for r in rows}) != 1775 or result['family_pair_count'] != 8:
        raise ValueError('Expected 1775 unique conditions across 8 family-pair groups')
    result.update({'folds': folds, 'evidence_hashes': files})
    return result, manifests


def control(args):
    plan = json.loads(args.plan.read_text())
    snapshots = {str(n): collect(args.root, args.prefix, args.plan, n)[0] for n in (576, 864, 1152)}
    winner = 576
    for n in (864, 1152):
        a, b = snapshots[str(n)], snapshots[str(winner)]
        if a['Q'] > b['Q'] + 1e-6 or (abs(a['Q'] - b['Q']) <= 1e-6 and a['M'] > b['M'] + 1e-6):
            winner = n
    ranked = snapshots[str(winner)]
    selected = next(n for n in (576, 864, 1152)
                    if snapshots[str(n)]['Q'] >= ranked['Q'] - .1 and snapshots[str(n)]['M'] >= ranked['M'] - .1)
    receipt = {'kind': 'HLS_CONTROL_BUDGET_DECISION', 'plan_sha256': sha(args.plan),
               'selected_optimizer_updates': selected, 'ranked_best_updates': winner,
               'accepted': absolute_gate(snapshots[str(selected)]), 'selected_metrics': snapshots[str(selected)],
               'snapshots': snapshots, 'test_access': False,
               'interpretation': 'Family-group descriptive transfer qualification; not IID inference or comparison to contaminated oldT8'}
    save(args.output, receipt)
    print(json.dumps({k: receipt[k] for k in ('selected_optimizer_updates', 'ranked_best_updates', 'accepted')}))
    print(json.dumps({k: receipt['selected_metrics'][k] for k in ('heart_sdri', 'lung_sdri', 'Q', 'M')}))


def treatment(args):
    control_receipt = json.loads(args.control.read_text())
    protocol = json.loads(args.protocol.read_text())
    gate = protocol['adoption_gate']
    expected_numeric = {'delta_macro_q_min_db': .5, 'delta_macro_balanced_mean_min_db': .5,
                        'delta_macro_heart_min_db': .25, 'delta_macro_lung_min_db': .25,
                        'max_family_pair_either_source_regression_db': .5,
                        'new_numerical_failures_allowed': 0,
                        'max_increase_pooled_negative_sdri_rate_percentage_points_either_source': 5.0}
    if (any(gate.get(k) != v for k, v in expected_numeric.items()) or
            gate['family_pair_balanced_mean_improvement_required'] != 'at least6 of8 strictlypositive' or
            gate['fold_q_improvement_required'] != 'at least4 of5 strictlypositive' or
            gate['absolute_utility_gate'] != 'heart and lung macro SI-SDRi each >=1dB; every8 family-pair/source mean >=0dB; zero numerical failures'):
        raise ValueError('Supplied protocol does not match the predeclared implemented gate')
    if (control_receipt['kind'] != 'HLS_CONTROL_BUDGET_DECISION' or
            control_receipt['plan_sha256'] != protocol['hls_control_plan_sha256']):
        raise ValueError('Foreign control budget receipt')
    n = control_receipt['selected_optimizer_updates']
    if n not in (576, 864, 1152):
        raise ValueError('Unapproved control-selected budget')
    result, manifests = collect(args.root, args.prefix, args.plan, n)
    baseline = control_receipt['selected_metrics']
    control_plan = Path(__file__).resolve().parents[1] / protocol['hls_control_plan']
    if sha(control_plan) != protocol['hls_control_plan_sha256']:
        raise ValueError('Original control plan changed')
    for snapshot in control_receipt['snapshots'].values():
        for path, expected in snapshot['evidence_hashes'].items():
            if sha(Path(path)) != expected:
                raise ValueError('Control evidence changed after budget selection')
    recomputed, _ = collect(args.control_root, args.control_prefix, control_plan, n)
    if recomputed != baseline:
        raise ValueError('Control receipt does not reproduce from supplied control root')
    plan = json.loads(args.plan.read_text())
    if plan['initialization'] != 'external_pretraining_endpoint' or plan['cv_evaluation_updates'] != [n]:
        raise ValueError('Treatment must have one frozen initialized endpoint')
    # Match row identities and exact optimizer-exposure prefix, not only aggregate counts.
    for fold in plan['folds']:
        control_dir = args.control_root / f"{args.control_prefix}-{fold['id']}-seed20260928"
        treatment_dir = args.root / f"{args.prefix}-{fold['id']}-seed20260928"
        c = read_rows(control_dir / f'validation-{n:04d}.jsonl')
        t = read_rows(treatment_dir / f'validation-{n:04d}.jsonl')
        if [r['mixture_id'] for r in c] != [r['mixture_id'] for r in t]:
            raise ValueError('Treatment conditions differ from control')
        if read_rows(control_dir / 'training_recipes.jsonl')[:4*n] != read_rows(treatment_dir / 'training_recipes.jsonl'):
            raise ValueError('Treatment optimizer exposures differ from control prefix')
    delta = {k: result[k] - baseline[k] for k in ('heart_sdri', 'lung_sdri', 'Q', 'M')}
    group_deltas = {g: {k: result['family_pairs'][g][k] - baseline['family_pairs'][g][k]
                        for k in ('heart_sdri', 'lung_sdri', 'Q', 'M')} for g in baseline['family_pairs']}
    fold_q = {f: result['folds'][f]['Q'] - baseline['folds'][f]['Q'] for f in baseline['folds']}
    checks = {'absolute_utility': absolute_gate(result), 'delta_Q_at_least_0.5': delta['Q'] >= .5,
              'delta_M_at_least_0.5': delta['M'] >= .5,
              'both_source_macro_gains_at_least_0.25': min(delta['heart_sdri'], delta['lung_sdri']) >= .25,
              'at_least_6_of_8_pair_M_gains': sum(g['M'] > 0 for g in group_deltas.values()) >= 6,
              'at_least_4_of_5_fold_Q_gains': sum(d > 0 for d in fold_q.values()) >= 4,
              'no_pair_source_regression_over_0.5': min(g[s] for g in group_deltas.values() for s in ('heart_sdri', 'lung_sdri')) >= -.5,
              'no_new_numerical_failures': result['failures'] == 0,
              'negative_rate_increase_at_most_5pp': all(result['negative_rate_percent'][s] - baseline['negative_rate_percent'][s] <= 5 for s in ('heart', 'lung'))}
    receipt = {'kind': 'EXTERNAL_TRANSFER_ADOPTION_DECISION', 'accepted': all(checks.values()),
               'plan_sha256': sha(args.plan), 'pilot_protocol_sha256': sha(args.protocol),
               'control_receipt_sha256': sha(args.control), 'selected_optimizer_updates': n,
               'initialization_checkpoint_sha256': plan['initialization_checkpoint_sha256'],
               'checks': checks, 'delta': delta, 'family_pair_deltas': group_deltas, 'fold_Q_deltas': fold_q,
               'selected_metrics': result, 'test_access': False}
    save(args.output, receipt)
    print(json.dumps({'accepted': receipt['accepted'], 'delta': delta, 'checks': checks}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['control', 'treatment'])
    for name in ('root', 'plan', 'output', 'control', 'control-root', 'protocol'):
        parser.add_argument('--' + name, type=Path, required=name in ('root', 'plan', 'output'))
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--control-prefix', default='cv')
    args = parser.parse_args()
    if args.mode == 'control':
        control(args)
    else:
        if not all((args.control, args.control_root, args.protocol)):
            parser.error('Treatment requires control receipt/root and frozen protocol')
        treatment(args)
