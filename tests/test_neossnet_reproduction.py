"""One regression for the released checkpoint's shared positional encoding."""
from pathlib import Path

import pytest


def test_released_individual_masks_accumulate_shared_positional_encoding(monkeypatch):
    torch = pytest.importorskip("torch")
    pytest.importorskip("torchaudio")
    pytest.importorskip("ptwt")
    source = Path(__file__).resolve().parents[1] / "app/ml/neossnet_source"
    monkeypatch.syspath_prepend(str(source))
    from models.transformer import TransformerEncoder

    # MaskGenerator calls both branches with the same tensor. Out-of-place
    # addition silently changes the lung branch seen by the released weights.
    first = TransformerEncoder(encoder_dim=4, num_layers=0)
    second = TransformerEncoder(encoder_dim=4, num_layers=0)
    shared = torch.zeros(1, 3, 4)
    one = first(shared).clone()
    two = second(shared).clone()
    assert torch.equal(one, first.pos_enc(3))
    assert torch.equal(two, 2 * first.pos_enc(3))
