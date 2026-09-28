# Final pre-T9 representation/objective decision

29 September 2026. **T8 V2 FROZEN · FINAL MODEL REVIEW DESIGNED, NOT EXECUTED ·
T9 SEALED · NOT DEPLOYED.** This is the last bounded model branch, not evidence
that a new model improves separation. No optimizer steps were taken in this sprint.

## 1. Decision and diagnosis

**Select BOTH treatments, and no others:**

- **A:** compact complex-complementary-mask STFT U-Net, **390,450 parameters**,
  with the existing waveform objective. One STFT, one architecture.
- **B:** unchanged **171,313-parameter Conv-TasNet**, adding the one specified
  source-normalized log1p spectral loss with **lambda = 6.0**. No alternate weight.

Maximum **two full treatment protocols** = five fresh family-fold fits each,
at most ten CV fits, followed by at most one fresh final refit if a treatment
passes. The capacity gate is separate and cannot initialize a scored run.
Neither treatment is combined with the other. No external/native audio or
weights, new seeds, ensemble, rescue variant or duration search.

**Is representation/objective now the established primary bottleneck? NO.**
The most defensible inference remains limited independent family priors and
data-efficient generalization, with **representation as an untested interaction**
of medium plausibility. Objective inadequacy has weaker direct support. Failed
data additions do not prove that sufficient useful independent data were added:
the clinical sources had domain/purity mismatch; qualified native references
added recorded hashes but no new families. Those failures reject their tested
protocols, not the original data-limited diagnosis. These final experiments ask
whether an explicit TF basis or spectral emphasis uses the small trusted pool
better. They do not assume that an architecture defect has been demonstrated.

### Observed history (not directly interchangeable evaluations)

| Evidence | Heart SI-SDRi | Lung SI-SDRi | Interpretation |
|---|---:|---:|---|
| T4 two-example fit | about 11.5–12 dB | about 11.5–12 dB | Local capacity, not unseen-family accuracy |
| Selected small T7, old two-pair validation | 3.101 | 3.130 | Narrow, correlated validation |
| Same-width second seed, old validation | 3.332 | 3.328 | Robustness uncertain; not a replacement checkpoint |
| Matched five-fold HLS control at 576 updates | 2.012519 | 1.913416 | Authoritative current control |
| External pretraining treatment | 1.860144 | 1.585710 | Rejected negative transfer |
| Qualified native treatment | 2.050186 | 0.831803 | Rejected substantial lung regression |

The approximately 12-versus-2 dB difference is not a measured train/validation
gap of one identically evaluated model. More late iterations reduced training
loss without establishing a useful transfer gain; 576 was the predeclared
earliest budget within 0.10 dB of the ranked control budget. No new budget
selection is warranted. Earlier gain/SI-SDR/semantics/gradient/context audits
remain valid. Equal-residual consistency remains essential and unchanged.

## 2. Reproducibility anchors

Starting implementation `57b4b5a6eed422c62831f5970ccab5bf694d90b1`; documentation
`6431fd045318f770f88d064f0ef892293fa3ba69`; root PAUSE
`51ef5b1460e21e2375c0844ed734c6b8ef421f08`. Both nested worktrees were clean.
All configured MCP checks passed without sign-in, including Graphify/GitHub,
five Cloudflare servers, browser, Node runtime, developer docs and Resend.
Git identity/account: ASHRAF-2004. Normal external Brave launch and HTTPS checked.
Graphify's `559ddba` index did not contain the current TasNet symbols; narrow
source inspection followed. Receipt: `research/evidence/final_model_review_preflight_v1.json`.
The Cloudflare skill constrained preflight to read-only calls; no infrastructure
or authentication configuration was modified.

Frozen machine protocol: `research/configs/final_pre_t9_model_plan_v1.json`.
SHA-256: `6776e53c1d53c66d39c8882169b6de729bc05358f337e26a91257fd74dce8103`.

The unchanged fallback is `research/configs/final_separator_v2.json`, SHA
`2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b`;
checkpoint SHA `1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658`.
V1 and v2/checkpoints must remain byte-identical. No fallback inference code,
data generator, metric or loss implementation changed in this design sprint.

## 3. Treatment A — exact TF model

Executable selected reference:
`research/probes/final_representation_complex_v1.py::StethoFuseComplexTFUNet`,
using the block/STFT/forward definitions in `final_representation_v1.py`.
Luna's production-independent research module will be
`app/ml/stethofuse_tf.py::StethoFuseComplexTFUNet`; no job/application imports.
Copy these operations and initialization order exactly, not a generic U-Net.

### Representation and mask decision

One STFT at 4 kHz: **n_fft = win_length = 256, hop = 64**, periodic Hann,
`center=True`, constant-zero padding, `normalized=False`, one-sided complex
output, all **129 bins**, including DC/Nyquist. Window 64 ms, frame hop 16 ms,
frequency grid 15.625 Hz, window squared-energy 96. Eight seconds produces
129×501; ten seconds produces 129×626. The frequency grid is not a claim of
15.625-Hz two-tone resolution (Hann main-lobe width is larger).

This compromise exposes narrowband/envelope structure without using a
256-ms frame. Short events still affect overlapping complex frames; the STFT
is reconstructible, not a hard removal of sub-64-ms waveform information.
Mask variation is nevertheless limited by the 16-ms grid. No frequency cutoff,
heart/lung crossover, mel compression, resampling or sample-rate change.

Four input channels, in this order:

1. `log1p(abs(X)/sqrt(96))`;
2. `real(X)/max(abs(X), 1e-6)`;
3. `imag(X)/max(abs(X), 1e-6)`;
4. `frequency_bin_index/128`, repeated over time.

The coordinate supplies absolute-frequency location rather than pretending
cardiopulmonary patterns are invariant to shifts along the Hz axis. Phase
channels avoid an angle discontinuity and vanish safely in zero-energy bins.
All are mixture-only. There are no dataset-fitted input statistics.

Head outputs two unrestricted real arrays `u,v`, not two source logits:

`Mh = 0.5 + u + i*v`, `Ml = 1 - Mh`;
`Hhat = Mh*X`, `Lhat = Ml*X`.

Force `v=0` at DC and Nyquist. ISTFT each source with the identical window/hop,
explicit original length; then apply existing equal waveform residual correction.
The two complex masks sum to one. They may be negative, complex or exceed one;
no sigmoid/tanh/clamp, mask-ratio target, oracle alignment or division by X is
used in the loss or deployment. Thus cancellation bins do not create singular
ratio labels. Exact X=0 still cannot reveal two cancelling components locally;
phase recovery/generalization is not guaranteed.

**Why not the simpler positive real mask?** We analytically tested the same
backbone with softmax complementary masks (390,306 parameters). On the two
predeclared development examples the reference-assisted binwise least-squares
bounded real mask `clip(Re(H*conj(X))/max(|X|^2,1e-12),0,1)` reconstructed only
9.099/9.157 and 8.069/8.074 dB H/L improvement. This is NOT a trained result,
deployable method or strict waveform-SI-SDR upper bound. It exposes a concrete
phase/amplitude restriction; it does not prove the +10-dB gate impossible.
Complex masks remove that restriction with just **144 extra input-convolution
parameters**. The extra flexibility/phase sensitivity is a generalization risk,
but a better final representation test than forcing mixture phase. No full
real-mask treatment is authorized. Prior post-hoc projected-TCN results are
not adopted or replayed.

### Exact architecture

Frequency then time axes; all ordinary convolutions 3×3, stride1, biasFalse.
Each block: Conv → GroupNorm(1,C,eps=1e-8,affine=True) → SiLU → Conv → same
normalization → SiLU. Default library initialization. No dropout or BatchNorm.

| Stage | Channels | Eight-second feature geometry |
|---|---|---|
| Input | 4 | 129×501, zero-pad bottom/right to 144×512 |
| E0 | 4→8→8 | 144×512; retain skip, average-pool2/stride2 |
| E1 | 8→16→16 | 72×256; skip, pool2 |
| E2 | 16→32→32 | 36×128; skip, pool2 |
| E3 | 32→64→64 | 18×64; skip, pool2 |
| Bottleneck | 64→96→96 | 9×32; second convolution dilation(1,8), padding(1,8) |
| D3 | concat160→64→64 | repeat-nearest2 to18×64; concatenate E3 |
| D2 | concat96→32→32 | 36×128; concatenate E2 |
| D1 | concat48→16→16 | 72×256; concatenate E1 |
| D0 | concat24→8→8 | 144×512; concatenate E0 |
| Head | 8→2 | 1×1, biasTrue; crop to129×501 before complex masks |

Upsampling is exactly two `repeat_interleave(2)` operations, not transposed
convolution/bilinear interpolation. Ten-second padded geometry is144×640,
bottleneck9×40. Count **390,450**, between171,313 and645,681. The depth reduces
129 bins to9 coarse bins while skips retain fine structure; widths support
that geometry. It is not a parameter-count-matched causal ablation of TCN.

### Context derivation

Ignore normalization to measure the local convolutional path. Reverse each
decoder's two convolutions and nearest upsample on output interval `[a,b]`:
`[floor((a-2)/2), floor((b+2)/2)]`, four times. Reverse bottleneck convolutions:
expand by1+8 frames on each side. Reverse each encoder pool and two convolutions:
`[2a-2, 2b+3]`, four times. Evaluating all16 output phases gives **412 or428
STFT-frame spans** (not the loose424-frame textbook interpolation approximation).
Including the 256-sample analysis window: **26,560–27,584 samples =6.640–6.896s**
nominal support. Hann endpoint zeros shorten the maximum nonzero bounding span
by one sample. Frequency spans188/204 bins nominally; true input has129 bins
plus padding. GroupNorm additionally makes computational dependence full-window.
Neither bounding support nor global normalization proves learned effective use
of every sample. Context is not obviously shorter than the existing6.132s TCN.

### Loss and external inference

**A uses exactly the existing fixed-label waveform loss**, after ISTFT and
equal-residual consistency: mean negative SI-SDR +5×RMS-normalized waveform L1.
No additional spectral objective in A: isolate the representation package.
Reuse the current `separate_recording` wrapper exactly: shared whole-record peak,
10s windows/8s hop/2s cosine overlap, right-zero padded tail, exact original
output length/scale, zero maps to zeros, near-silent nonzero and nonfinite fail.
Heart channel0, lung1; no permutation, references, extra projection or ensemble.

## 4. Treatment B — one precise spectral auxiliary objective

Architecture and forward consistency are **unchanged**. Keep all existing loss
operations untouched; add a separate `app/ml/spectral_objective.py` helper.
Use the same single256/64 STFT above, on each predicted/reference source.

For batch example b and source s, let `rho_bs = RMS(y_bs) + 1e-6` and
`A_bs(z) = |STFT(z/rho_bs)| / sqrt(96)`. Then

`Lsp = mean_(b,s,f,t) | ln(1 + A_bs(yhat)) - ln(1 + A_bs(y)) |`.

`L_B = mean_(b,s)[-SI-SDR(yhat,y) + 5*mean_time|yhat-y|/(RMS(y)+1e-6)] + 6*Lsp`.

Both sources/frequency bins/frames receive equal averaging. Natural log1p,
no log epsilon/clamp, no predicted-RMS normalization, no separate-source gain
correction, no PIT. The only RMS epsilon is1e-6, matching existing waveform L1.
Periodic Hann sqrt-energy normalization is fixed, not fitted. Nonfinite or
silent targets remain rejected by the existing primary objective.

Single-resolution log1p is chosen over multi-resolution spectral convergence
plus log losses to avoid extra scales/weights and an additional amplitude
convention. Plain log-magnitude with a tiny floor can overweight nearly silent
bins; log1p has finite slope at zero. Spectral convergence is also useful in
other tasks, but emphasizes large spectral energy and adds another component.
No claim that single-resolution is universally superior. SI-SDR still optimizes
waveform morphology; waveform L1 and Lsp use the same target scale to anchor
amplitude. Magnitude loss alone is phase ambiguous, hence it is auxiliary only.

### Measured gradient scale (zero optimizer updates)

Fresh seed20260928 small TCN; the same two original development pairs, first8s,
relative levels−10/0/+10. No validation audio/checkpoint used. Measure the full
concatenated parameter gradient in float64 norms before clipping.

| Lung/heart dB | Existing loss norm | Lsp norm | Gradient cosine | 6Lsp/base norm |
|---:|---:|---:|---:|---:|
| −10 | 26.8052 | 0.88218 | 0.93683 | 0.19746 |
| 0 | 22.6759 | 0.76504 | 0.94860 | 0.20243 |
| +10 | 29.4447 | 0.96795 | 0.84965 | 0.19724 |

Predeclared scale rule in the probe before measurements:
`raw_lambda=min(.2*median(||g0||/||gsp||), .5*min(||g0||/||gsp||))`;
floor to two significant digits. Raw6.07706 → **6.0**. No performance search,
alternate lambda or adaptive gradient reweighting. This is an initial local
scale calibration, not a guarantee of20% gradient contribution later.
The alignment means there is no evidence of a broken/conflicting objective;
the nonparallel component may emphasize frequency structure differently.
B is a conservative, lower-confidence complementary test, not a promised fix.

## 5. Probes completed here; no training evidence

Receipts: `research/evidence/final_representation_probe_v1.json` and
`final_representation_complex_probe_v1.json`. Only four original development
WAVs opened; no validation replay or T9 audio. No optimizer constructed/stepped;
all model state hashes unchanged. The new probe files were uncommitted during
execution, explicitly recorded; no trained checkpoint was produced.

- Exact counts171,313/390,306/390,450; selected A initial-state SHA
  `8d617e4199c55ce0f0e1502ca7413305e1600c701f70e585f6dd41bd1584d687`.
- B fresh state `7171ef15eadc33e001c833271bd8e1301145e974af64337fdbb2ef51c205f9b9`
  matches every historical control. A cannot share TCN topology/initial weights;
  the same seed is a reproducibility rule, not paired identical weights.
- Forward lengths1,32000,32001,40000 passed; full-record length60001 passed.
- Complex-mask sum error≤1.20e-7; full-record mixture error5.96e-8;
  zero output exact zero, STFT roundtrip error1.79e-7, identical-target Lsp=0.
- Batch-four forward/backward finite. Median A0.1607s, B0.1331s across three
  no-step probes; combined process peak about1.2GiB. These are runtime estimates,
  not training/generalization results or a comprehensive test suite.

## 6. Matched grouped-family experiment

Only the existing86-row eligible allowlist. All optimizer data must exclude
both held-out source families per fold, before audio decoding. No native
triplets, external sources, augmented streams or full100-source decoder scan.

| Fold | Held-out heart | Held-out lung | Train H/L | Holdout H/L | Conditions |
|---|---|---|---|---|---:|
| f1 | Mid Systolic Murmur | Normal | 38/29 | 7/12 | 420 |
| f2 | Normal | Pleural Rub | 36/32 | 9/9 | 405 |
| f3 | Early Systolic Murmur, Tachycardia | Rhonchi | 36/33 | 9/8 | 360 |
| f4 | Late Systolic Murmur, Atrial Fibrillation | Wheezing | 36/34 | 9/7 | 315 |
| f5 | Late Diastolic Murmur, S3 | Fine Crackles | 34/36 | 11/5 | 275 |

Each arm/fold: fresh seed20260928, **576 optimizer steps**, batch4 =2,304 draws;
same control's realized recipe prefix and exact saved CV recipes. AdamW.001,
betas(.9,.999), eps1e-8, decay.0001, clip norm5, constant LR. CPU float32,
Python3.14.4/torch and torchaudio2.11.0+cpu,2threads/1interop, deterministic
algorithms. No plateau scheduler/early stop. Evaluate once at endpoint576,
not intermediate checkpoints. Preserve resumability; an unchanged experiment
may resume with model/optimizer/RNG/recipe cursor state, never silently restart.

Authoritative control receipt `research/evidence/external_hls_control_decision_v1.json`,
SHA `0d8893d61d9ed9517d0227781f33b3357b1c41f85d4ee80228f1691545d47dbe`.
All ten stored control manifest/validation hashes and ten recipe artifacts were
rechecked. Use `validation-0576.jsonl`, not final1152-update results. Control
H/L SI-SDR2.021192/1.922089, SI-SDRi2.012519/1.913416,
**Q1.913416, M1.962968**, zero failures. No control retraining needed.

Average conditions within each of eight heart×lung family pairs, then average
those pair means equally for each source; Q=min(H,L), M=(H+L)/2. Do not average
five folds equally. Report fixed-level breakdown, per-pair/per-fold scores,
median/IQR, negative-condition rates, failures and CPU runtime. No IID-row
standard errors, significance claims or demographic/clinical conclusions.

## 7. Frozen adoption and winner rules

Apply **every** clause independently to A and B, unchanged from the prior
data-programme gate:

- ΔQ≥0.5dB and ΔM≥0.5dB; ΔH≥0.25 and ΔL≥0.25dB.
- At least6/8 pair-M and4/5 fold-Q scores strictly improve.
- No pair/either-source mean regresses by more than0.5dB.
- Negative-condition rate increases by no more than5 percentage points for
  either source; zero numerical failures and all1,775 conditions present.
- Absolute H/L macro SI-SDRi each≥1dB; every pair/source mean≥0dB.

0.5dB exceeds twice the old observed~0.227dB seed-Q difference; it is an
engineering margin, **not a statistically calibrated significance cutoff**.
The families have already informed several decisions, and even eight pairs
share families/recordings. Two more comparisons increase selection optimism.
Capacity/gradient probes also use development families appearing in CV holdouts;
fresh fold resets prevent optimizer leakage, but this is not untouched nested CV.
Strict bounded gates and the still-sealed T9 limit—not eliminate—that risk.

Neither passes → retain v2, **STOP MODEL DEVELOPMENT**.
Exactly one passes → select it. Both pass → higher Q, then M, then count of
positive pair-M gains, then positive fold-Q count; metric ties use1e-6dB.
If still tied choose **B**, predeclared for smaller model/unchanged inference.
No best-family, runtime, seed or checkpoint cherry-picking. Always complete B
even if A passes; if A fails its capacity gate, B alone remains eligible.

## 8. Exact Luna handoff

All new artifacts under ignored `.local/training/stethofuse-representation-v1/`.
Every trained run records clean starting commit, this plan hash, model/loss
source hashes, all manifest/recipe hashes, fresh initial-state hash, environment,
seed, optimizer/LR/budget, history, resumable state, endpoint hash and failures.
No overwrite of prior artifacts. No optimizer steps from a dirty implementation.

| Phase | Exact work and stopping boundary |
|---|---|
| **R0** | Recheck MCP/auth, AGENTS, PAUSE, nested branches/HEADs, v1/v2 hashes. Verify this plan hash,86-row allowlist, fold/control receipts/recipes. Metadata only. Stop on identity/integrity mismatch. No T9/audio enumeration. |
| **R1** | Add `app/ml/stethofuse_tf.py` and `app/ml/spectral_objective.py` from the selected prototypes. Add `scripts/train_stethofuse_representation.py` with only arms A/B,576steps and f1–f5/refit. Reuse pure metadata/partition/recipe helpers from `train_stethofuse_family_refit.py` and unchanged `evaluate_validation`, metric/checkpoint/atomic-save helpers from baseline runner. Do NOT weaken the old runner's hardcoded guards or expose native/external initialization. New runner has no arbitrary seed/LR/budget/init flags. Commit implementation before any optimizer step, including gate. |
| **R2** | Focused tests only: strict save/load and expected initial hashes/counts; TF input/ISTFT length, zero/finite/mask+waveform consistency; loss identity/finite gradient/equal source semantics; recipe and heldout-family guards; gate/winner predicate fixtures. Synthetic generated inputs plus the four named original-development files only. B may take exactly one disposable development batch optimizer step at.001; discard model/state. Never reuse it. No T4 rerun for B. |
| **R3** | Add/run `scripts/run_stethofuse_tf_capacity_gate.py`: fresh A seed20260928, pairs F_AF_A/F_N_LLA and F_ESM_LLSB/F_PR_LLA, first32000samples,0dB, batch2, same waveform loss. AdamW.001,betas(.9,.999),eps1e-8,decay0,clip5. Max400steps/600s. Evaluate initial then every20steps; PASS only EVERY case/source≥+10dB SI-SDRi AND normalized-L1 reduction≥50%. Stop firstPASS. All finite. Failed gate rejects A, no replacement/extra steps; B continues. Retain gate receipt/hash, never load gate weights into CV. |
| **R4** | Commit/push focused support and gate/sanity metadata as ASHRAF-2004. Confirm local=remote and clean before full initialization. Existing PR9 only. Freeze executable source hashes into run manifest. No changed scientific settings. |
| **R5** | If A gatePASS, run A f1→f5, seed20260928 reset each fold,576updates,constant.001,exact2,304-control-draw prefix. Evaluate only endpoint. Run IDs `a-tfcomplex-f1-seed20260928` etc. Keep all results; no response to one weak fold except genuine anomaly. |
| **R6** | Run B f1→f5 regardless of A score, same seed/budget/LR/recipes. Run IDs `b-tcn-spectral-f1-seed20260928` etc. Frozen lambda6.0; log primary loss components and raw/weighted Lsp every144steps, without validation between steps. |
| **R7** | New `scripts/summarize_stethofuse_representation.py` reads endpoint JSONL plus hashed historical control only. Verify all1,775 IDs/folds/levels/targets before aggregation. Apply all gate clauses; preserve per-clause PASS/FAIL and per-family deltas. Missing/corrupt results invalidate an arm, never shrink denominator. |
| **R8** | Apply section7 rank mechanically. Write tracked `research/evidence/final_model_comparison_decision_v1.json` binding plan,clean code,run and endpoint hashes. If neither passes retain v2, update evidence,STOP. No third model/loss/mask/seed. |
| **R9** | Only a valid passing-winner receipt unlocks fresh final refit. All45H/41L allowlisted sources, no holdout/evaluation during refit, same synthetic2,304-draw prefix as v2, seed20260928,576updates,batch4,constant AdamW.001,decay.0001,clip5. Winner architecture/loss unchanged. Never initialize from folds/gate/v2. Sole endpoint576, not lowest training loss. |
| **R10** | If winner refit valid, freeze `research/configs/final_separator_v3.json`, preserving v1/v2 bytes and recording supersession inside v3. Freeze architecture/count,exact objective,seed,budget,code/data/loss/checkpoint/spec hashes,environment,complete input/output/inference rules. For A explicitly identify complex masking, NOT mixture-phase projection; B inference unchanged. Strict load/zero/odd-length/finite/consistency synthetic-only smoke. No refit generalization claim without heldout evidence. |
| **R11** | Once-update FYP2, PAUSE and existing PR9/2; commit/push; check nested worktrees and remotes. **STOP BEFORE T9** whether v2 retained or v3 frozen. T9 source/condition generation, metrics, aggregations, levels and non-neural comparators stay fixed; only the pre-test selected neural system identity can be replaced. Separate owner T9 authorization required. |

Expected CLI contract (Luna implements it, do not execute in this sprint):

```text
.local/ensemble/venv/bin/python scripts/train_stethofuse_representation.py \
  --plan research/configs/final_pre_t9_model_plan_v1.json \
  --treatment A --fold f1 --run-id a-tfcomplex-f1-seed20260928
# Repeat remaining A folds if capacityPASS, then B folds with treatment B.
# For the sole winner refit: --fold refit plus --decision-receipt <frozen PASS receipt>.
```

Do not silently accept another mode or CLI config. Stop on nonfinite losses,
outputs/gradients, corrupted checkpoints/data, label/recipe mismatch or memory
exhaustion. Limits8GiB RSS,20min/fold/refit and600s gate; preserve evidence and
diagnose once. A genuine defect needs documented invalidation/correction; no
changed-design rescue or automatic endless retry. Resume only if exact
code/config/recipe/model/optimizer/RNG state represents the same experiment.

Measured forward/backward implies about93s A and77s B optimizer work/fold,
before optimizer/data/validation overhead. Budget roughly **20–35 CPU minutes
for both five-fold protocols**, plus≤10min capacity gate and a few minutes
for one conditional refit. This is an estimate, not measured full-run runtime.
No GPU/environment changes. Report actual time/memory separately later.

## 9. Literature scope and interpretation

These sources motivate mechanisms, not target-domain score predictions. The
U-Net reference establishes spectrogram encoder/decoder use in separation;
phase-sensitive work distinguishes real and complex filter classes; spectral
training literature motivates frequency losses but not this exact coefficient.
Our architecture, source-RMS normalization and bounded protocol are project
design choices, not claimed paper reproductions. No borrowed weights.

- Jansson, A., Humphrey, E., Montecchio, N., Bittner, R., Kumar, A., & Weyde, T.
  (2017). Singing voice separation with deep U-Net convolutional networks.
  *Proceedings of ISMIR*,745–751. [Original proceedings](https://archives.ismir.net/ismir2017/paper/000171.pdf).
- Erdogan, H., Hershey, J. R., Watanabe, S., & Le Roux, J. (2015).
  Phase-sensitive and recognition-boosted speech separation using deep recurrent
  neural networks. *ICASSP*,708–712. [Author manuscript](https://www.jonathanleroux.org/pdf/Erdogan2015ICASSP04.pdf).
- Yamamoto, R., Song, E., & Kim, J.-M. (2019). *Parallel WaveGAN: A fast waveform
  generation model based on generative adversarial networks with multi-resolution
  spectrogram* [Preprint]. arXiv. https://arxiv.org/abs/1910.11480
- PyTorch contributors. (n.d.). *torch.stft* and *torch.istft* (version2.11).
  [STFT](https://docs.pytorch.org/docs/2.11/generated/torch.stft.html),
  [ISTFT](https://docs.pytorch.org/docs/2.11/generated/torch.istft.html).

**No new model improvement is claimed.** The current v2 remains the fallback;
representation/objective treatments are **NOT YET TRAINED**. Neither treatment
passing ends model development. T9, production, frontend, demographics and
submitted FYP1 are outside this sprint.
