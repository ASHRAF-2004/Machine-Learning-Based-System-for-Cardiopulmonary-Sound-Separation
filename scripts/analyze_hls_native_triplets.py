"""Bounded NON-TEST native correspondence forensics, not separation evaluation.

No model import, optimizer, audio export or test-file access. Alignment/gain uses
references offline, and is explicitly not an inference-time separator. The only
global waveform correction is fitted on predeclared fitting pairs and 6-9s time.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d

from audit_hls_native_registry import ROOT, authorized_native_path

FS = 4000
EPS = 1e-20
CONFIG = ROOT / 'research/configs/hls_native_forensics_v1.json'
REGISTRY = ROOT / 'research/manifests/hls_native_triplets_v1.json'
OUT = ROOT / '.local/training/stethofuse-tcn-v1/native-forensics-v1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rms(x):
    return float(np.sqrt(np.mean(np.square(x))))


def summary(values):
    x = np.asarray(values, dtype=float)
    if not np.isfinite(x).all():
        raise ValueError('Non-finite diagnostic, not silently omitted')
    return dict(zip(('min', 'q25', 'median', 'q75', 'max'), map(float, np.quantile(x, [0, .25, .5, .75, 1])))) | {'mean': float(x.mean()), 'n': len(x)}


def ncc_candidates(reference, template, start_min, start_max, count=5, separation=80):
    """Candidate reference starts; centered normalized dot product, no wrap."""
    y = template - template.mean()
    n = len(y)
    lo, hi = max(0, int(start_min)), min(len(reference)-n, int(start_max))
    if hi < lo:
        raise ValueError('No valid reference support')
    region = reference[lo:hi+n]
    dot = signal.correlate(region, y, mode='valid', method='fft')
    a = np.concatenate(([0.], np.cumsum(region)))
    b = np.concatenate(([0.], np.cumsum(region*region)))
    energy = np.maximum(b[n:]-b[:-n]-(a[n:]-a[:-n])**2/n, EPS)
    corr = dot / np.sqrt(energy * max(float(y@y), EPS))
    ranking = np.abs(corr).copy()
    result = []
    for _ in range(count):
        j = int(np.argmax(ranking))
        if ranking[j] < 0:
            break
        frac = 0.
        if 0 < j < len(corr)-1:
            ym, yc, yp = np.abs(corr[j-1:j+2])
            denom = ym - 2*yc + yp
            if abs(denom) > EPS:
                frac = float(np.clip(.5*(ym-yp)/denom, -.5, .5))
        result.append({'start': lo+j, 'correlation': float(corr[j]), 'fractional_peak_offset_samples': frac})
        ranking[max(0,j-separation):min(len(ranking),j+separation+1)] = -1
    return result


def linear_fit(x, h, l):
    a = np.column_stack((h, l))
    gains, _, _, _ = np.linalg.lstsq(a, x, rcond=None)
    residual = x-a@gains
    return gains, rms(residual)/max(rms(x), EPS), float(np.linalg.cond(a.T@a))


def metrics(x, h, l):
    y = h+l
    r = x-y
    xc, yc = x-x.mean(), y-y.mean()
    alpha = float(xc@yc)/max(float(xc@xc), EPS)
    sisdr = 10*np.log10((float((alpha*xc)@(alpha*xc))+EPS)/(float((yc-alpha*xc)@(yc-alpha*xc))+EPS))
    return {'residual_rms': rms(r), 'residual_mix_rms_ratio': rms(r)/max(rms(x), EPS),
            'residual_weaker_source_rms_ratio': rms(r)/max(min(rms(h),rms(l)), EPS),
            'mix_sum_si_sdr_db': float(sisdr),
            'correlation': float(xc@yc)/max(float(np.linalg.norm(xc)*np.linalg.norm(yc)), EPS),
            'heart_rms': rms(h), 'lung_rms': rms(l), 'mix_rms': rms(x),
            'residual_heart_correlation': float(r@h)/max(float(np.linalg.norm(r)*np.linalg.norm(h)),EPS),
            'residual_lung_correlation': float(r@l)/max(float(np.linalg.norm(r)*np.linalg.norm(l)),EPS)}


def align(x, h, l, cfg):
    a,b = [int(t*FS) for t in cfg['calibration_mixture_seconds']]
    bound = int(FS*cfg['maximum_absolute_lag_seconds'])
    kwargs = {'count':cfg['candidate_peaks_per_source'], 'separation':int(FS*cfg['peak_minimum_separation_seconds'])}
    candidates = [ncc_candidates(s, x[a:b], a-bound, a+bound, **kwargs) for s in (h,l)]
    trials = []
    for ch in candidates[0]:
        for cl in candidates[1]:
            hs,ls = ch['start'],cl['start']
            gains,score,cond = linear_fit(x[a:b], h[hs:hs+b-a], l[ls:ls+b-a])
            trials.append((score, a-hs, a-ls, gains,cond))
    trials.sort(key=lambda q:q[0])
    score,dh,dl,gains,cond = trials[0]
    start,stop = max(0,dh,dl), min(len(x),len(h)+dh,len(l)+dl)
    t = np.arange(start,stop)
    ah,al = h[t-dh],l[t-dl]
    check = (t < a) | (t >= b)
    # Three local residualized lags are descriptive; not applied to targets.
    drift = {'heart':[], 'lung':[]}
    for segment in np.array_split(t,3):
        s,e = int(segment[0]),int(segment[-1]+1)
        for role, ref, delay, other, odelay, ogain in (
            ('heart',h,dh,l,dl,gains[1]),('lung',l,dl,h,dh,gains[0])):
            template = x[s:e]-ogain*other[np.arange(s,e)-odelay]
            cs = ncc_candidates(ref,template,s-delay-1000,s-delay+1000,count=1)
            drift[role].append({'time_seconds':(s+e)/2/FS,
                                'lag_samples':s-cs[0]['start'], **{k:v for k,v in cs[0].items() if k!='start'}})
    info = {'heart_lag_samples':dh, 'lung_lag_samples':dl,
            'heart_gain':float(gains[0]),'lung_gain':float(gains[1]),
            'calibration_residual_mix_rms_ratio':score, 'calibration_gram_condition':cond,
            'second_best_residual_mix_rms_ratio':trials[1][0],
            'valid_support_seconds':len(t)/FS, 'heldout_support_seconds':int(check.sum())/FS,
            'candidates':candidates,'drift':drift,
            'aligned_temporal_holdout':metrics(x[t][check],(gains[0]*ah)[check],(gains[1]*al)[check]),
            'raw_common_temporal_holdout':metrics(x[t][check],h[t][check],l[t][check])}
    # Scalar gain comparison uses exactly the same untouched time support.
    sameg,_,_ = linear_fit(x[a:b],h[a:b],l[a:b])
    info['same_time_gain_temporal_holdout'] = metrics(x[t][check],sameg[0]*h[t][check],sameg[1]*l[t][check])
    info['same_time_gains'] = [float(g) for g in sameg]
    summed=h[a:b]+l[a:b]
    shared=float(summed@x[a:b])/max(float(summed@summed),EPS)
    info['same_time_shared_gain']=shared
    info['same_time_shared_gain_temporal_holdout']=metrics(x[t][check],shared*h[t][check],shared*l[t][check])
    # Full unshifted flanks avoid selecting a favorable support by fitted lags.
    flanks=[np.arange(0,a),np.arange(b,len(x))]
    info['same_time_shared_gain_full_flanks']=[metrics(x[z],shared*h[z],shared*l[z]) for z in flanks]
    info['same_time_two_gain_full_flanks']=[metrics(x[z],sameg[0]*h[z],sameg[1]*l[z]) for z in flanks]
    return info, (t, x[t], gains[0]*ah, gains[1]*al)


def fit_global(records, cfg):
    nfft,hop = cfg['stft_samples'],cfg['stft_hop']
    bins = nfft//2+1
    gram = np.zeros((bins,2,2),complex)
    rhs = np.zeros((bins,2),complex)
    counts = Counter(r['row']['family_pair_id'] for r in records if r['row']['correspondence_partition']=='fit_pair')
    for rec in records:
        row = rec['row']
        if row['correspondence_partition'] != 'fit_pair':
            continue
        t,x,h,l = rec['aligned']
        keep = (t>=6*FS)&(t<9*FS)
        scale = max(rms(x[keep]),EPS)
        spectra = [signal.stft(v[keep]/scale, fs=FS, nperseg=nfft,noverlap=nfft-hop,boundary=None,padded=False)[2] for v in (x,h,l)]
        m = spectra[0]
        a = np.stack(spectra[1:],axis=-1)
        weight = 1/(counts[row['family_pair_id']]*len(counts)*m.shape[1])
        gram += weight*np.einsum('fti,ftj->fij',a.conj(),a)
        rhs += weight*np.einsum('fti,ft->fi',a.conj(),m)
    ridge = cfg['ridge_trace_fraction']*np.trace(gram,axis1=1,axis2=2).real/2+EPS
    # Identity-centered regularization; retain identity in unidentifiable bins.
    transfer = np.linalg.solve(gram+ridge[:,None,None]*np.eye(2), (rhs+ridge[:,None])[...,None])[...,0]
    smooth = cfg['frequency_smoothing_bins']
    transfer = uniform_filter1d(transfer.real,smooth,axis=0)+1j*uniform_filter1d(transfer.imag,smooth,axis=0)
    transfer *= np.minimum(1,cfg['maximum_transfer_magnitude']/np.maximum(np.abs(transfer),EPS))
    impulses = np.fft.fftshift(np.fft.irfft(transfer,n=nfft,axis=0),axes=0)
    taps = cfg['fir_taps']; mid=nfft//2
    fir = impulses[mid-taps//2:mid+taps//2+1]*np.hanning(taps)[:,None]
    return fir, transfer


def synth_check():
    rng=np.random.default_rng(20260928)
    h=rng.normal(size=60000);l=rng.normal(size=60000)
    x=np.zeros(60000); dh=1234;dl=-827
    t=np.arange(2000,58000)
    x[t]=1.3*h[t-dh]-.7*l[t-dl]
    cfg=json.loads(CONFIG.read_text())
    info,_=align(x,h,l,cfg['alignment'])
    assert (info['heart_lag_samples'],info['lung_lag_samples'])==(dh,dl)
    assert np.allclose([info['heart_gain'],info['lung_gain']],[1.3,-.7],atol=1e-10)
    # A singleton identity spectrum transforms to a centered unit impulse.
    delta=np.fft.fftshift(np.fft.irfft(np.ones(513),n=1024))
    assert delta[512]==1 and np.count_nonzero(delta)==1
    print(json.dumps({'synthetic_alignment_and_fir_convention':'PASS','real_audio_opened':False}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic-check',action='store_true')
    args=parser.parse_args()
    if args.synthetic_check:
        synth_check();return
    started=time.monotonic()
    cfg=json.loads(CONFIG.read_text()); registry=json.loads(REGISTRY.read_text())
    rows=[r for r in registry['rows'] if r['eligible_non_test']]
    assert len(rows)==100
    records=[]
    opened=[]
    for row in rows:
        arrays=[];technical={}
        for role in ('mixture','heart','lung'):
            f=row['files'][role]
            path=authorized_native_path(row,f['path'])
            assert digest(path)==f['sha256']
            sr,data=wavfile.read(path)
            assert sr==FS and data.shape==(60000,) and data.dtype==np.int16
            x=data.astype(np.float64)/32768
            assert np.isfinite(x).all()
            arrays.append(x);opened.append(f['path'])
            technical[role]={'rms':rms(x),'dc':float(x.mean()),'peak':float(np.abs(x).max()),
                             'full_scale_samples':int((np.abs(data.astype(np.int32))>=32767).sum()),
                             'zero_samples':int((data==0).sum())}
        x,h,l=arrays
        info,aligned=align(x,h,l,cfg['alignment'])
        info.update({'triplet_id':row['triplet_id'],'family_pair_id':row['family_pair_id'],
                     'partition':row['correspondence_partition'],'technical':technical,
                     'raw_full':metrics(x,h,l)})
        records.append({'row':row,'arrays':arrays,'aligned':aligned,'info':info})
    fir,transfer=fit_global(records,cfg['waveform_global_transfer'])
    half=len(fir)//2
    for rec in records:
        t,x,h,l=rec['aligned']
        hp=signal.convolve(h,fir[:,0],mode='same',method='fft')
        lp=signal.convolve(l,fir[:,1],mode='same',method='fft')
        valid=(t>=t[0]+half)&(t<t[-1]+1-half)
        held=valid&((t<6*FS)|(t>=9*FS))
        info=rec['info']
        info['global_fir_temporal_holdout']=metrics(x[held],hp[held],lp[held])
        info['global_fir_temporal_holdout_seconds']=float(held.sum()/FS)
        info['waveform_error_tolerance_pass']=bool(info['global_fir_temporal_holdout']['residual_weaker_source_rms_ratio']<=.1 and len(t)/FS>=8)
        # PSD of residual is descriptive, not a noise-only estimate.
        f,p=signal.welch((x-hp-lp)[held],fs=FS,nperseg=2048,noverlap=1024)
        total=float(p.sum())+EPS
        info['corrected_residual_band_fractions']={f'{lo}-{hi}':float(p[(f>=lo)&(f<hi)].sum()/total) for lo,hi in [(0,20),(20,100),(100,400),(400,800),(800,2001)]}
    output={'schema_version':1,'interpretation':'REFERENCE_ASSISTED_CORRESPONDENCE_ONLY_NOT_SEPARATOR_RESULT',
            'config_sha256':digest(CONFIG),'registry_sha256':digest(REGISTRY),
            'test_audio_opened':False,'native_files_decoded':len(opened),'native_triplets':len(records),
            'fit_pairs':32,'heldout_pairs':8,'global_fir_taps':len(fir),
            'global_fit_time':'6-9s only; untouched temporal flanks evaluated',
            'global_pair_weighting':'equal family-pair then recording',
            'runtime_seconds':time.monotonic()-started,'rows':[r['info'] for r in records]}
    grouped={}
    for partition in ('all','fit_pair','heldout_pair'):
        subset=[r['info'] for r in records if partition=='all' or r['info']['partition']==partition]
        stages=('raw_full','raw_common_temporal_holdout','same_time_gain_temporal_holdout','same_time_shared_gain_temporal_holdout','aligned_temporal_holdout','global_fir_temporal_holdout')
        grouped[partition]={stage:{metric:summary([r[stage][metric] for r in subset]) for metric in ('residual_mix_rms_ratio','residual_weaker_source_rms_ratio','mix_sum_si_sdr_db','correlation')} for stage in stages}
        grouped[partition]['waveform_error_tolerance_pass']=sum(r['waveform_error_tolerance_pass'] for r in subset)
        for role in ('heart','lung'):
            grouped[partition][role+'_lag_seconds']=summary([r[role+'_lag_samples']/FS for r in subset])
            grouped[partition][role+'_gain']=summary([r[role+'_gain'] for r in subset])
            grouped[partition][role+'_negative_gain_count']=sum(r[role+'_gain']<0 for r in subset)
            grouped[partition][role+'_local_lag_range_samples']=summary([np.ptp([d['lag_samples'] for d in r['drift'][role]]) for r in subset])
    output['summary']=grouped
    output['additive_subgroup']={'rule':'Both unshifted full temporal flanks have shared-gain residual <= 0.10 weaker source RMS; label-tolerance fixed before first DSP, shared gain is nested in declared two-gain stage',
        'ids':[r['info']['triplet_id'] for r in records if all(f['residual_weaker_source_rms_ratio']<=.1 for f in r['info']['same_time_shared_gain_full_flanks'])]}
    output['analysis_revision_note']='After the declared two-gain stage identified heterogeneous closure, added its nested one-shared-gain diagnostic on complete 0-6s/9-15s flanks. No model results or training used; original stage settings unchanged.'
    output['heldout_pair_summary']={pair:{stage:float(np.mean([r['info'][stage]['residual_mix_rms_ratio'] for r in records if r['row']['family_pair_id']==pair])) for stage in ('raw_common_temporal_holdout','same_time_gain_temporal_holdout','aligned_temporal_holdout','global_fir_temporal_holdout')} for pair in sorted({r['row']['family_pair_id'] for r in records if r['row']['correspondence_partition']=='heldout_pair'})}
    OUT.mkdir(parents=True,exist_ok=True)
    np.savez(OUT/'global_transfer.npz',fir=fir,frequency_transfer=transfer)
    (OUT/'opened_allowlist.json').write_text(json.dumps(opened,indent=2)+'\n')
    (ROOT/'research/evidence/hls_native_correspondence_v1.json').write_text(json.dumps(output,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'runtime_seconds':output['runtime_seconds'],'summary':grouped,'heldout_pair_summary':output['heldout_pair_summary']},indent=2))


if __name__=='__main__':
    main()
