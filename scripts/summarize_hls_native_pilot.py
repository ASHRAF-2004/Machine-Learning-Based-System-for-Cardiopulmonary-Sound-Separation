"""Apply the frozen native-pilot gate once; metric/artifact reads only, no audio."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from summarize_external_transfer import absolute_gate, collect, metrics, read_rows, save, sha

ROOT=Path(__file__).resolve().parents[1]


def summarize(protocol_path: Path, output: Path):
    protocol=json.loads(protocol_path.read_text())
    phash=sha(protocol_path)
    base=ROOT/protocol['base_plan']
    assert sha(base)==protocol['base_plan_sha256']
    control_path=ROOT/protocol['control']['decision_receipt']
    assert sha(control_path)==protocol['control']['decision_receipt_sha256']
    control=json.loads(control_path.read_text())
    baseline, cm=collect(ROOT/protocol['control']['artifact_root'],'cv',base,576)
    baseline['evidence_hashes']={str(Path(p).relative_to(ROOT)):v for p,v in baseline['evidence_hashes'].items()}
    assert baseline==control['selected_metrics']
    for path,digest in baseline['evidence_hashes'].items():
        assert sha(ROOT/path)==digest
    gate=protocol['adoption_gate']
    for k,v in {'delta_macro_q_min_db':.5,'delta_macro_balanced_mean_min_db':.5,
                'delta_macro_heart_min_db':.25,'delta_macro_lung_min_db':.25,
                'max_family_pair_either_source_regression_db':.5,
                'new_numerical_failures_allowed':0,
                'max_increase_pooled_negative_sdri_rate_percentage_points_either_source':5.}.items():
        assert gate[k]==v
    assert gate['family_pair_balanced_mean_improvement_required']=='at least6 of8 strictlypositive'
    assert gate['fold_q_improvement_required']=='at least4 of5 strictlypositive'
    rows=[];folds={};runs={};hashes={};all_states=set();comparison_proof={}
    for f in protocol['folds']:
        directory=ROOT/protocol['artifact_root']/f'native-{f}-seed20260928'
        manifest=json.loads((directory/'run_manifest.json').read_text())
        p=manifest['provenance']
        assert manifest['status']=='COMPLETE_FIXED_ENDPOINT' and manifest['failures']==0
        assert manifest['optimizer_updates']==576 and p['seed']==20260928 and p['fold']==f
        assert p['parameter_count']==171313 and p['plan_sha256']==sha(base)
        assert p['native_plan_sha256']==phash
        assert manifest['fresh_seeded_state_sha256']==cm[f]['fresh_seeded_state_sha256']
        assert manifest['initialized_state_sha256']==manifest['fresh_seeded_state_sha256']
        all_states.add(json.dumps(p['git'],sort_keys=True))
        control_dir=ROOT/protocol['control']['artifact_root']/f'cv-{f}-seed20260928'
        synthetic=read_rows(directory/'training_recipes.jsonl')
        assert len(synthetic)==2304 and synthetic==read_rows(control_dir/'training_recipes.jsonl')[:2304]
        values=read_rows(directory/'validation-0576.jsonl')
        cvalues=read_rows(control_dir/'validation-0576.jsonl')
        assert [r['mixture_id'] for r in values]==[r['mixture_id'] for r in cvalues]
        expected_hash=json.loads((directory/'checkpoint_hashes.json').read_text())['endpoint.pt']
        assert sha(directory/'checkpoints/endpoint.pt')==expected_hash==manifest['endpoint_sha256']
        comparison_proof[f]={'identical_fresh_state':True,'identical_2304_synthetic_receipts':True,
                             'identical_validation_condition_ids':True,'no_initializer_loaded':p['initialization_checkpoint_sha256'] is None}
        folds[f]=metrics(values);rows.extend(values)
        runs[f]={'run_id':manifest['run_id'],'endpoint_sha256':expected_hash,
                 'runtime_seconds':manifest['runtime_seconds'],'peak_rss_mib':manifest['process_peak_rss_mib'],
                 'code':p['git'],'optimizer_updates':576}
        for name in ('run_manifest.json','validation-0576.jsonl','history.jsonl','native_recipes.jsonl'):
            path=directory/name
            hashes[str(path.relative_to(ROOT))]=sha(path)
    assert len(all_states)==1 and len(rows)==1775 and len({r['mixture_id'] for r in rows})==1775
    result=metrics(rows);assert result['family_pair_count']==8
    result['folds']=folds
    keys=('heart_sdri','lung_sdri','Q','M')
    delta={k:result[k]-baseline[k] for k in keys}
    pairs={g:{k:result['family_pairs'][g][k]-baseline['family_pairs'][g][k] for k in keys} for g in baseline['family_pairs']}
    fold_delta={f:folds[f]['Q']-baseline['folds'][f]['Q'] for f in folds}
    checks={'absolute_utility':absolute_gate(result),'delta_Q_at_least_0.5':delta['Q']>=.5,
            'delta_M_at_least_0.5':delta['M']>=.5,
            'both_source_macro_gains_at_least_0.25':min(delta['heart_sdri'],delta['lung_sdri'])>=.25,
            'at_least_6_of_8_pair_M_gains':sum(g['M']>0 for g in pairs.values())>=6,
            'at_least_4_of_5_fold_Q_gains':sum(v>0 for v in fold_delta.values())>=4,
            'no_pair_source_regression_over_0.5':min(g[s] for g in pairs.values() for s in ('heart_sdri','lung_sdri'))>=-.5,
            'no_new_numerical_failures':result['failures']==0,
            'negative_rate_increase_at_most_5pp':all(result['negative_rate_percent'][s]-baseline['negative_rate_percent'][s]<=5 for s in ('heart','lung'))}
    receipt={'kind':'HLS_NATIVE_ADOPTION_DECISION','accepted':all(checks.values()),
             'native_plan_sha256':phash,'base_plan_sha256':sha(base),'plan_sha256':sha(base),
             'selected_optimizer_updates':576,'control_receipt_sha256':sha(control_path),
             'baseline':baseline,'selected_metrics':result,'delta':delta,'family_pair_deltas':pairs,
             'fold_Q_deltas':fold_delta,'checks':checks,'matched_control_proof':comparison_proof,
             'runs':runs,'evidence_hashes':hashes,'test_access':False,'production_access':False,
             'interpretation':'One source-supervision treatment, five grouped-family folds, not five variants; descriptive correlated-family evidence, not IID significance.'}
    save(output,receipt)
    print(json.dumps({'accepted':receipt['accepted'],'delta':delta,'checks':checks},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--protocol',type=Path,default=ROOT/'research/configs/hls_native_pilot_v1.json')
    p.add_argument('--output',type=Path,default=ROOT/'research/evidence/hls_native_pilot_decision_v1.json')
    args=p.parse_args();summarize(args.protocol,args.output)
