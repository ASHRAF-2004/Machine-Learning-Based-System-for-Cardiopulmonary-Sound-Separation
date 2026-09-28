# Final ensemble reconsideration — validation only

2026-09-28. T7 COMPLETE / FINAL ENSEMBLE DECISION IN PROGRESS / FINAL TEST SEALED /
NOT DEPLOYED.

## Predeclared diagnostic protocol

One pass over the existing 225 correlated validation conditions (two family
pairs). Selected small Conv-TasNet seed 20260928, epoch 8, checkpoint SHA-256
`89f8d66134c0a49aa2a05971720cdffbdd1e501ebce99bb83119e6683d58ac93` is the control.
The seed 20260929 checkpoint is not inspected for expert/weight selection.

Compare only the control waveform, its target-free complementary magnitude
mask projection, the existing Fixed Filter, and existing Generic NMF
(6 components, 80 multiplicative-update iterations, seed 42 per inference
window). NMF fits its existing unsupervised per-input decomposition; no new
trained model, bases, settings or neural optimizer steps are introduced.
VMD remains excluded because its no-fallback path has not been qualified;
NeoSSNet and the large TCN are excluded as final ensemble experts.

Use the unchanged TCN 10-second / 8-second-hop window, overlap, whole-record
shared gain, padding and trimming for every method. “TCN waveform/raw” includes
the already-trained target-free equal-residual mixture-consistency layer; it
does not mean the unconstrained decoder before that layer. Projection means
`m_h=|STFT(h)|/(|STFT(h)|+|STFT(l)|)`, stable epsilon with a 0.5 silent-bin
default, `m_l=1-m_h`, applied to the mixture's complex STFT; n_fft1024/hop256
and the existing centered periodic-Hann implementation. It uses no reference.
Both masks are computed per canonical window, then the same overlap-add is used.

Reuse the validated SI-SDR and weaker-source family-pair macro selector. Replay
control scores against saved T7 rows (tolerance 1e-5dB). Measure per-condition,
family and five frozen relative levels, residual correlations at shared scale,
consistency error and method runtime. A per-source max-over-experts diagnostic
is **ORACLE UPPER BOUND — NOT DEPLOYABLE**, only for hard expert routing, not an
upper bound on every possible mixture of outputs. It may violate pairwise
mixture consistency and cannot select outputs in deployment.

Alignment diagnostic is fixed in advance: first frozen-recipe pair from each
validation family, at all five levels; cross-correlation within ±128 samples
(32ms) against references, with no shifts, sign corrections or oracle output
changes applied. No final-test audio, metadata labels, recipes or metrics are
used. Only the eligible training-run metadata and validation recipe are parsed.

`scripts/diagnose_final_ensemble.py` is an offline analytical entry point with
no fusion weights/search, no training function calls, and no application DB or
job writes. It refuses to overwrite prior results. Outputs remain ignored in
`.local/ensemble/final_reconsideration/primary-validation-v1/`.

Decide from these diagnostics whether to predeclare one simple future fusion
experiment or retain standalone TCN. No ensemble score will be calculated in
this diagnostic pass. No additional seed training is authorized.
