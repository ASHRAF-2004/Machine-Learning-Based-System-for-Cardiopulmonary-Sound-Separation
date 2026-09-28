"""One complex-mask design probe, contrasting the restricted real-mask prototype.

No optimizer or model fitting. This is the selected A reference implementation.
The real-mask prototype is an analytical comparison, NOT a third treatment.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import sys
import time
import torch
from torch import nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.probes.final_representation_v1 import (
    TFBlock, StethoFuseTFMaskUNet, stft, SEED, state_sha256, sha256_file)
from app.ml.training_objective import fixed_label_loss


class StethoFuseComplexTFUNet(StethoFuseTFMaskUNet):
    architecture_version = 'stethofuse-tfcomplex-4k-v1'

    def __init__(self):
        nn.Module.__init__(self)
        widths = (8, 16, 32, 64)
        self.encoders = nn.ModuleList([TFBlock(a,b) for a,b in zip((4,*widths[:-1]),widths)])
        self.bottleneck = TFBlock(64,96,second_time_dilation=8)
        self.decoders = nn.ModuleList([TFBlock(a,b) for a,b in
                                      ((160,64),(96,32),(48,16),(24,8))])
        self.head = nn.Conv2d(8,2,1,bias=True)

    def masks(self,spectrum):
        magnitude = spectrum.abs()
        phase_scale = magnitude.clamp_min(1e-6)
        coordinate = torch.linspace(0,1,spectrum.shape[-2],device=spectrum.device,
                                    dtype=magnitude.dtype).view(1,-1,1).expand_as(magnitude)
        z = torch.stack((torch.log1p(magnitude/math.sqrt(96.0)),
                         spectrum.real/phase_scale,spectrum.imag/phase_scale,coordinate),1)
        freq,frames = z.shape[-2:]
        z = F.pad(z,(0,(-frames)%16,0,(-freq)%16))
        skips=[]
        for block in self.encoders:
            z=block(z);skips.append(z);z=F.avg_pool2d(z,2,stride=2)
        z=self.bottleneck(z)
        for block,skip in zip(self.decoders,reversed(skips)):
            z=z.repeat_interleave(2,-2).repeat_interleave(2,-1)
            z=block(torch.cat((z,skip),1))
        raw=self.head(z)[...,:freq,:frames]
        # Real-valued waveform endpoints have no imaginary DC or Nyquist component.
        interior=torch.ones_like(raw[:,1]);interior[:,0]=0;interior[:,-1]=0
        heart=torch.complex(.5+raw[:,0],raw[:,1]*interior)
        return torch.stack((heart,1-heart),1)


def main():
    out=ROOT/'research/evidence/final_representation_complex_probe_v1.json'
    if out.exists():raise FileExistsError('Do not overwrite evidence')
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True);torch.manual_seed(SEED)
    model=StethoFuseComplexTFUNet()
    before=state_sha256(model)
    rows=[]
    for length in (1,32000,32001,40000):
        x=torch.randn(1,1,length)*.1
        with torch.no_grad():
            y=model(x);masks=model.masks(stft(x[:,0]))
        rows.append({'samples':length,'shape':list(y.shape),'finite':bool(torch.isfinite(y).all()),
                     'mask_sum_max_error':float((masks.sum(1)-1).abs().max()),
                     'mixture_max_error':float((y.sum(1,keepdim=True)-x).abs().max())})
    torch.manual_seed(SEED)
    targets=torch.randn(4,2,32000)*.1;x=targets.sum(1,keepdim=True)
    timing=[]
    for _ in range(3):
        model.zero_grad(set_to_none=True);tic=time.perf_counter()
        value=fixed_label_loss(model(x),targets);value.backward()
        timing.append(time.perf_counter()-tic)
        assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
    with torch.no_grad():
        long_x=torch.randn(60001)*.1;long_y=model.separate_recording(long_x)
        zero=model(torch.zeros(1,1,32000))
    assert state_sha256(model)==before
    result={'kind':'DESIGN_ONLY_COMPLEX_MASK_SHAPE_PROBE','seed':SEED,'optimizer_updates':0,
            'real_audio_opened':False,'test_audio_accessed':False,'parameter_count':model.parameter_count,
            'initial_state_sha256':before,'script_sha256':sha256_file(Path(__file__)),
            'dependency_prototype_sha256':sha256_file(ROOT/'research/probes/final_representation_v1.py'),
            'checks':rows,'finite_gradients':True,'batch4_forward_backward_seconds':timing,
            'median_forward_backward_seconds':sorted(timing)[1],
            'zero_max':float(zero.abs().max()),'long_shape':list(long_y.shape),
            'long_consistency_max':float((long_y.sum(0)-long_x).abs().max()),
            'model_state_unchanged':True}
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
