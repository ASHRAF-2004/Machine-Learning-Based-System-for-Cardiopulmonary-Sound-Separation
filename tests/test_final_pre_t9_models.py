"""Focused non-test shape/loss checks for the frozen final treatments."""
import torch

from app.ml.stethofuse_tcn import StethoFuseConvTasNet
from app.ml.stethofuse_tf import StethoFuseComplexTFUNet, stft
from app.ml.spectral_objective import spectral_log1p_loss, treatment_b_loss
from app.ml.training_objective import fixed_label_loss
from app.ml.representation_selection import aggregate, adoption_gate, select_winner
from scripts.train_stethofuse_baseline import state_sha256


def test_frozen_model_counts_and_seeded_initial_states() -> None:
    torch.manual_seed(20260928)
    tf_model = StethoFuseComplexTFUNet()
    assert tf_model.parameter_count == 390450
    assert state_sha256(tf_model) == "8d617e4199c55ce0f0e1502ca7413305e1600c701f70e585f6dd41bd1584d687"
    torch.manual_seed(20260928)
    tcn = StethoFuseConvTasNet("stethofuse-convtasnet-4k-small-v1")
    assert tcn.parameter_count == 171313
    assert state_sha256(tcn) == "7171ef15eadc33e001c833271bd8e1301145e974af64337fdbb2ef51c205f9b9"


def test_complex_tf_mask_and_waveform_contract() -> None:
    torch.set_num_threads(2)
    torch.manual_seed(20260928)
    model = StethoFuseComplexTFUNet()
    mixture = torch.randn(1, 1, 32001) * 0.05
    output = model(mixture)
    masks = model.masks(stft(mixture[:, 0]))
    assert output.shape == (1, 2, 32001)
    assert torch.isfinite(output).all()
    assert torch.allclose(masks[:, 0] + masks[:, 1], torch.ones_like(masks[:, 0]), atol=1e-7)
    assert torch.allclose(output.sum(1, keepdim=True), mixture, atol=2e-6, rtol=0)
    target = torch.randn_like(output) * 0.05
    loss = fixed_label_loss(output, target)
    loss.backward()
    assert torch.isfinite(loss)
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
    zero = model(torch.zeros(1, 1, 32000))
    assert torch.count_nonzero(zero) == 0


def test_spectral_objective_fixed_source_and_finite_gradient() -> None:
    torch.manual_seed(20260928)
    target = torch.randn(2, 2, 32000) * 0.03
    assert spectral_log1p_loss(target, target).item() == 0.0
    estimate = (target + 0.005 * torch.randn_like(target)).requires_grad_(True)
    spectral = spectral_log1p_loss(estimate, target)
    total, returned = treatment_b_loss(estimate, target, fixed_label_loss(estimate, target))
    total.backward()
    assert torch.equal(spectral, returned)
    assert torch.isfinite(spectral) and torch.isfinite(total)
    assert estimate.grad is not None and torch.isfinite(estimate.grad).all()


def test_treatment_b_forward_consistency_is_unchanged() -> None:
    torch.manual_seed(20260928)
    model = StethoFuseConvTasNet("stethofuse-convtasnet-4k-small-v1")
    mixture = torch.randn(2, 1, 32001) * 0.02
    output = model(mixture)
    assert output.shape == (2, 2, 32001)
    assert torch.isfinite(output).all()
    assert torch.allclose(output.sum(1, keepdim=True), mixture, atol=1e-7, rtol=0)


def test_frozen_adoption_gate_and_tie_rule() -> None:
    rows = []
    pairs = [(f"heart-{i}", f"lung-{i}") for i in range(8)]
    folds = ["f1", "f2", "f3", "f4", "f5"]
    for index in range(1775):
        heart, lung = pairs[index % 8]
        rows.append({"heart_family": heart, "lung_family": lung,
                     "fold": folds[index % 5], "heart_si_sdr_db": 4.0,
                     "heart_si_sdri_db": 2.0, "lung_si_sdr_db": 4.0,
                     "lung_si_sdri_db": 2.0})
    control = aggregate(rows)
    treatment = aggregate([{**row, "heart_si_sdri_db": 2.6, "lung_si_sdri_db": 2.6,
                            "heart_si_sdr_db": 4.6, "lung_si_sdr_db": 4.6} for row in rows])
    assert adoption_gate(treatment, control)["pass"]
    gates = {"A": adoption_gate(treatment, control), "B": adoption_gate(treatment, control)}
    assert select_winner({"A": True, "B": True}, {"A": treatment, "B": treatment}, gates) == "B"
    assert select_winner({"A": False, "B": False}, {}, {}) == "CONTROL"
