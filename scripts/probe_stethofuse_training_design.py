"""ADR T01 synthetic sizing probe only. No audio, optimizer, or saved weights.

Uses torchaudio's BSD-2-Clause model as a dependency, not NeoSSNet source/weights.
Run with the isolated research environment; never from a production container.
"""
import hashlib
import json
import resource
import time
from pathlib import Path

import torch
import torchaudio
import yaml

ROOT = Path(__file__).resolve().parents[1]
config = yaml.safe_load((ROOT / "research/configs/stethofuse_tcn_v1.yaml").read_text())
torch.set_num_threads(2)
torch.set_num_interop_threads(1)
torch.manual_seed(config["seed"])
torch.use_deterministic_algorithms(True)
keys = ("num_sources", "enc_kernel_size", "enc_num_feats", "msk_kernel_size",
        "msk_num_feats", "msk_num_hidden_feats", "msk_num_layers", "msk_num_stacks", "msk_activate")
model = torchaudio.models.ConvTasNet(**{k: config["model"][k] for k in keys})


def fingerprint():
    return hashlib.sha256(b"".join(p.detach().numpy().tobytes()
                                  for p in model.state_dict().values())).hexdigest()


def separate(x):
    raw = model(x)
    return raw + (x - raw.sum(1, keepdim=True)) / 2


before = fingerprint()
t = torch.arange(32000) / 4000
h = 0.2 * torch.sin(2 * torch.pi * 73 * t) * (0.6 + 0.4 * torch.cos(2 * torch.pi * 1.1 * t))
l = 0.08 * torch.randn(32000)
target = torch.stack([h, l])[None].repeat(4, 1, 1)
mixture = target.sum(1, keepdim=True)
start = time.perf_counter()
output = separate(mixture)
forward_seconds = time.perf_counter() - start
tc, ec = target - target.mean(-1, keepdim=True), output - output.mean(-1, keepdim=True)
projection = (ec * tc).sum(-1, keepdim=True) / tc.square().sum(-1, keepdim=True) * tc
score = 10 * torch.log10((projection.square().sum(-1) + 1e-8) /
                         ((ec - projection).square().sum(-1) + 1e-8))
amplitude = (output - target).abs().mean(-1) / (target.square().mean(-1).sqrt() + 1e-6)
loss = -score.mean() + 5 * amplitude.mean()
loss.backward()
forward_backward_seconds = time.perf_counter() - start
assert torch.isfinite(loss) and all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
assert output.shape == (4, 2, 32000)
additivity = float((output.detach().sum(1, keepdim=True) - mixture).abs().max())
model.zero_grad(set_to_none=True)
del output, loss, projection, score, amplitude, ec, tc
model.eval()
with torch.inference_mode():
    x = torch.randn(1, 1, 40000) * 0.1
    separate(x)  # one warm-up
    start = time.perf_counter()
    result = separate(x)
    inference_seconds = time.perf_counter() - start
    repeated, tail = separate(x), separate(x[..., :-1])
assert result.shape == (1, 2, 40000) and tail.shape == (1, 2, 39999)
assert torch.isfinite(result).all() and torch.equal(result, repeated)
assert fingerprint() == before
print(json.dumps({"classification": "SYNTHETIC DESIGN PROBE; NOT TRAINING OR QUALITY EVIDENCE",
                  "parameters": sum(p.numel() for p in model.parameters()),
                  "torch": torch.__version__, "torchaudio": torchaudio.__version__,
                  "seed": config["seed"], "threads": 2, "optimizer_steps": 0,
                  "shape_finite_gradient_repeat_and_unchanged_weights": "PASS",
                  "mixture_consistency_max_abs_error": additivity,
                  "batch4_8s_forward_seconds": forward_seconds,
                  "batch4_8s_forward_backward_seconds": forward_backward_seconds,
                  "batch1_10s_inference_seconds": inference_seconds,
                  "process_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}, indent=2))
