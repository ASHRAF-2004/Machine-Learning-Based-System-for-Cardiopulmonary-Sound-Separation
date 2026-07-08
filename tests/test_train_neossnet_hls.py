from __future__ import annotations

from pathlib import Path

from scripts import train_neossnet_hls


def test_train_neossnet_hls_quick_test_args_parse() -> None:
    args = train_neossnet_hls.parse_args(
        ["--quick-test", "--epochs", "1", "--batch-size", "2"]
    )

    assert args.quick_test is True
    assert args.epochs == 1
    assert args.batch_size == 2


def test_train_neossnet_hls_output_config_path_matches_checkpoint() -> None:
    checkpoint = Path("storage/ml_models/neossnet_hls_finetuned.pt")

    assert train_neossnet_hls.output_config_path(checkpoint) == Path(
        "storage/ml_models/neossnet_hls_finetuned.yaml"
    )
