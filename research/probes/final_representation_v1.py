"""Design-only executable reference: no optimizer, validation replay or test audio.

Luna must preserve these exact model/loss operations when moving them into app/ml.
The only real audio opened is the four predeclared development capacity-gate files.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
import torchaudio

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.training_data import read_manifest, read_source, make_mixture, sha256_file
from app.ml.training_objective import fixed_label_components, fixed_label_si_sdr_db
from scripts.train_stethofuse_baseline import state_sha256

SEED = 20260928
ELIGIBLE = ROOT / '.local/training/stethofuse-tcn-v1/t7-small-seed20260928/eligible_split.csv'
ELIGIBLE_SHA = '82e677af9f27256aa163b8aa80ca096874bc5cc37da10f29d029f7fee93999dd'
PAIRS = (('F_AF_A', 'F_N_LLA'), ('F_ESM_LLSB', 'F_PR_LLA'))
FFT = 256
HOP = 64


def stft(x: torch.Tensor) -> torch.Tensor:
    return torch.stft(x, n_fft=FFT, hop_length=HOP, win_length=FFT,
                      window=torch.hann_window(FFT, periodic=True, device=x.device, dtype=x.dtype),
                      center=True, pad_mode='constant', normalized=False,
                      onesided=True, return_complex=True)


def istft(x: torch.Tensor, length: int) -> torch.Tensor:
    return torch.istft(x, n_fft=FFT, hop_length=HOP, win_length=FFT,
                       window=torch.hann_window(FFT, periodic=True, device=x.device,
                                                dtype=x.real.dtype),
                       center=True, normalized=False, onesided=True, length=length)


def spectral_log1p_loss(estimate: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Mean fixed-source RMS-normalized log1p STFT magnitude absolute error."""
    if estimate.shape != target.shape or estimate.ndim != 3 or estimate.shape[1] != 2:
        raise ValueError('Expected equal [batch,2,time] arrays')
    rho = target.square().mean(-1, keepdim=True).sqrt() + 1e-6
    # Identical target RMS scales BOTH estimate and reference: no estimate normalization.
    e = stft((estimate / rho).flatten(0, 1)).abs() / math.sqrt(96.0)
    t = stft((target / rho).flatten(0, 1)).abs() / math.sqrt(96.0)
    return (torch.log1p(e) - torch.log1p(t)).abs().mean()


class TFBlock(nn.Module):
    def __init__(self, incoming: int, outgoing: int, second_time_dilation: int = 1):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(incoming, outgoing, 3, padding=1, bias=False),
            nn.GroupNorm(1, outgoing, eps=1e-8), nn.SiLU(),
            nn.Conv2d(outgoing, outgoing, 3, padding=(1, second_time_dilation),
                      dilation=(1, second_time_dilation), bias=False),
            nn.GroupNorm(1, outgoing, eps=1e-8), nn.SiLU())

    def forward(self, x):
        return self.layers(x)


class StethoFuseTFMaskUNet(nn.Module):
    """Two-channel input (log magnitude, absolute frequency coordinate), two masks."""
    architecture_version = 'stethofuse-tfmask-4k-v1'
    source_order = ('heart', 'lung')
    inference_window_samples = 40000
    inference_hop_samples = 32000
    overlap_samples = 8000
    # Reuse only the exact target-free external window/amplitude wrapper, not TCN weights.
    separate_recording = StethoFuseConvTasNet.separate_recording

    def __init__(self):
        super().__init__()
        widths = (8, 16, 32, 64)
        self.encoders = nn.ModuleList([TFBlock(a, b) for a, b in zip((2, *widths[:-1]), widths)])
        self.bottleneck = TFBlock(64, 96, second_time_dilation=8)
        self.decoders = nn.ModuleList([TFBlock(a, b) for a, b in
                                      ((96+64, 64), (64+32, 32), (32+16, 16), (16+8, 8))])
        self.head = nn.Conv2d(8, 2, 1, bias=True)

    @property
    def parameter_count(self):
        return sum(p.numel() for p in self.parameters())

    def masks(self, spectrum):
        magnitude = torch.log1p(spectrum.abs() / math.sqrt(96.0))
        coordinate = torch.linspace(0, 1, spectrum.shape[-2], device=spectrum.device,
                                    dtype=magnitude.dtype).view(1, -1, 1).expand_as(magnitude)
        z = torch.stack((magnitude, coordinate), dim=1)
        freq, frames = z.shape[-2:]
        z = F.pad(z, (0, (-frames) % 16, 0, (-freq) % 16))
        skips = []
        for block in self.encoders:
            z = block(z)
            skips.append(z)
            z = F.avg_pool2d(z, 2, stride=2)
        z = self.bottleneck(z)
        for block, skip in zip(self.decoders, reversed(skips)):
            z = z.repeat_interleave(2, dim=-2).repeat_interleave(2, dim=-1)
            z = block(torch.cat((z, skip), dim=1))
        return torch.softmax(self.head(z)[..., :freq, :frames], dim=1)

    def forward(self, mixture):
        if mixture.ndim != 3 or mixture.shape[1] != 1 or mixture.shape[-1] == 0:
            raise ValueError('Expected [batch,1,nonempty time]')
        if not torch.isfinite(mixture).all():
            raise ValueError('Nonfinite mixture')
        length = mixture.shape[-1]
        spectrum = stft(mixture[:, 0])
        masked = self.masks(spectrum) * spectrum[:, None]
        raw = istft(masked.flatten(0, 1), length).reshape(mixture.shape[0], 2, length)
        output = raw + (mixture - raw.sum(1, keepdim=True)) / 2
        if output.shape != (mixture.shape[0], 2, length) or not torch.isfinite(output).all():
            raise RuntimeError('Invalid TF output')
        return output


def gradients(loss, model):
    gs = torch.autograd.grad(loss, tuple(model.parameters()), retain_graph=True)
    return torch.cat([g.detach().flatten().double() for g in gs])


def receptive_intervals(dilation):
    # Exact longest-path integer dependency intervals; ignore normalization/global features.
    result = []
    for phase in range(16):
        lo = hi = 1024 + phase
        for _ in range(4):  # reverse decoder two convs, then nearest-repeat upsample
            lo, hi = (lo - 2) // 2, (hi + 2) // 2
        lo, hi = lo - 1 - dilation, hi + 1 + dilation  # bottleneck
        for _ in range(4):  # reverse avgpool, then encoder two convs
            lo, hi = 2 * lo - 2, 2 * hi + 3
        result.append({'phase': phase, 'lo': lo, 'hi': hi, 'frames': hi-lo+1})
    return result


def main():
    out = ROOT / 'research/evidence/final_representation_probe_v1.json'
    if out.exists():
        raise FileExistsError('Do not overwrite analytical evidence')
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    assert platform.python_version() == '3.14.4'
    assert torch.__version__ == torchaudio.__version__ == '2.11.0+cpu'
    assert sha256_file(ELIGIBLE) == ELIGIBLE_SHA
    wanted = {('HS', h) for h, _ in PAIRS} | {('LS', l) for _, l in PAIRS}
    sources = {(s.kind, s.id): s for s in read_manifest(ELIGIBLE)
               if (s.kind, s.id) in wanted and s.split == 'development'}
    assert set(sources) == wanted
    for s in sources.values():
        assert sha256_file(s.path) == s.sha256
    cache = {k: read_source(s) for k, s in sources.items()}
    batches = {}
    for level in (-10, 0, 10):
        xs, ys = [], []
        for h, l in PAIRS:
            x, y, _ = make_mixture(cache['HS', h], cache['LS', l], level)
            scale = np.max(np.abs(x))
            xs.append(x / scale)
            ys.append(y / scale)
        batches[level] = (torch.from_numpy(np.stack(xs)[:, None]), torch.from_numpy(np.stack(ys)))

    torch.manual_seed(SEED)
    tcn = StethoFuseConvTasNet('stethofuse-convtasnet-4k-small-v1').train()
    initial_hash = state_sha256(tcn)
    grad_rows = []
    for level, (x, y) in batches.items():
        prediction = tcn(x)
        base = fixed_label_components(prediction, y)['loss']
        spectral = spectral_log1p_loss(prediction, y)
        ga, gb = gradients(base, tcn), gradients(spectral, tcn)
        assert torch.isfinite(ga).all() and torch.isfinite(gb).all()
        grad_rows.append({'level_db': level, 'base_loss': float(base.detach()),
                          'spectral_loss': float(spectral.detach()), 'base_norm': float(ga.norm()),
                          'spectral_norm': float(gb.norm()),
                          'cosine': float(torch.dot(ga, gb)/(ga.norm()*gb.norm()))})
    ratios = [r['base_norm']/r['spectral_norm'] for r in grad_rows]
    raw_lambda = min(.2*float(np.median(ratios)), .5*min(ratios))
    # Predeclared conservative two-significant-digit floor, not a performance search.
    precision = 10**(math.floor(math.log10(raw_lambda))-1)
    weight = math.floor(raw_lambda/precision)*precision
    for r in grad_rows:
        r['weighted_spectral_to_base_norm_ratio'] = weight*r['spectral_norm']/r['base_norm']
    assert state_sha256(tcn) == initial_hash

    torch.manual_seed(SEED)
    tf = StethoFuseTFMaskUNet().train()
    tf_hash = state_sha256(tf)
    checks = []
    for length in (1, 32000, 32001, 40000):
        x = torch.randn(1, 1, length) * .1
        with torch.no_grad():
            output = tf(x)
            masks = tf.masks(stft(x[:, 0]))
        checks.append({'samples': length, 'shape': list(output.shape),
                       'finite': bool(torch.isfinite(output).all()),
                       'mixture_max_error': float((output.sum(1, keepdim=True)-x).abs().max()),
                       'mask_sum_max_error': float((masks.sum(1)-1).abs().max())})
    x, y = batches[0]
    x4, y4 = x.repeat(2, 1, 1), y.repeat(2, 1, 1)
    benchmarks = {}
    for name, model in (('tf', tf), ('tcn', tcn)):
        times = []
        for _ in range(3):
            model.zero_grad(set_to_none=True)
            tick = time.perf_counter()
            prediction = model(x4)
            loss = fixed_label_components(prediction, y4)['loss']
            if name == 'tcn':
                loss = loss + weight*spectral_log1p_loss(prediction, y4)
            loss.backward()
            assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
            times.append(time.perf_counter()-tick)
        benchmarks[name] = {'forward_backward_seconds': times, 'median_seconds': float(np.median(times))}
    with torch.no_grad():
        zero = tf(torch.zeros(1,1,32000))
        identity = spectral_log1p_loss(y, y)
        roundtrip = (istft(stft(x[:,0]), x.shape[-1])-x[:,0]).abs().max()
        long_x = torch.randn(60001)*.1
        long_y = tf.separate_recording(long_x)
        X, H = stft(x[:,0]), stft(y[:,0])
        alpha = ((H*X.conj()).real / X.abs().square().clamp_min(1e-12)).clamp(0,1)
        candidate = torch.stack((istft(alpha*X,32000), istft((1-alpha)*X,32000)),1)
        scores = fixed_label_si_sdr_db(candidate,y)-fixed_label_si_sdr_db(x.expand(-1,2,-1),y)
    assert state_sha256(tf) == tf_hash and state_sha256(tcn) == initial_hash
    result = {'kind':'DESIGN_PROBE_NOT_TRAINING','base_git_commit':subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'script_sha256':sha256_file(Path(__file__)),
        'working_tree_note':'New analytical prototype uncommitted at probe time; frozen model/runner unchanged',
        'python':platform.python_version(),'torch':torch.__version__,'torchaudio':torchaudio.__version__,
        'seed':SEED,'optimizer_updates':0,'test_audio_accessed':False,'validation_audio_accessed':False,
        'eligible_manifest_sha256':ELIGIBLE_SHA,'development_pairs':PAIRS,
        'source_hashes':{f'{s.kind}/{s.id}':s.sha256 for s in sources.values()},
        'tcn_parameter_count':tcn.parameter_count,'tcn_initial_state_sha256':initial_hash,
        'tf_parameter_count':tf.parameter_count,'tf_initial_state_sha256':tf_hash,
        'gradient_rows':grad_rows,'lambda_rule':'floor_2significant(min(.2*median(base_norm/spec_norm), .5*min(base_norm/spec_norm)))',
        'lambda_raw':raw_lambda,'lambda_selected':weight,'tf_shape_checks':checks,
        'tf_frequency_conv_support':receptive_intervals(1),'tf_time_conv_support':receptive_intervals(8),
        'stft_roundtrip_max_error':float(roundtrip),'spectral_identity_loss':float(identity),
        'zero_output_max':float(zero.abs().max()),'full_record_shape':list(long_y.shape),
        'full_record_consistency_error':float((long_y.sum(0)-long_x).abs().max()),
        'reference_assisted_bounded_real_mask_development_sdri':scores.tolist(),
        'oracle_caveat':'Not deployable, not generalization, not a strict waveform SI-SDR upper bound; binwise squared-complex-error projection',
        'benchmarks':benchmarks,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        'model_states_unchanged':True}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
