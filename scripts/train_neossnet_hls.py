"""Fine-tune NeoSSNet on the processed HLS-CMDS train/validation split."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
import yaml  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402

from app.database.db import SessionLocal, initialize_database  # noqa: E402
from app.ml.hls_cmds_dataset import (  # noqa: E402
    HlsCmdsSeparationDataset,
    SEGMENT_SAMPLES,
    TARGET_SAMPLE_RATE_HZ,
)
from app.ml.neossnet_inference import (  # noqa: E402
    MODEL_SAMPLE_RATE,
    NEOSSNET_SOURCE_DIR,
    add_neossnet_source_to_path,
)
from app.services.model_service import ensure_finetuned_model_record  # noqa: E402


DEFAULT_BASE_CHECKPOINT = PROJECT_ROOT / "storage" / "ml_models" / "model_best.pt"
DEFAULT_MODEL_CONFIG_PATH = PROJECT_ROOT / "storage" / "ml_models" / "model.yaml"
DEFAULT_OUTPUT_CHECKPOINT = (
    PROJECT_ROOT / "storage" / "ml_models" / "neossnet_hls_finetuned.pt"
)
TRAINING_LOG_PATH = PROJECT_ROOT / "storage" / "ml_models" / "neossnet_hls_training_log.csv"

DEFAULT_MODEL_CONFIG = {
    "dec_type": "convolution",
    "enc_kernel_size": 512,
    "enc_num_feats": 512,
    "enc_type": "convolution",
    "mother_wavelet": "db10",
    "msk_conv_layers": 6,
    "msk_dropout": 0.3,
    "msk_ffn_expand": 4,
    "msk_individual_mask": True,
    "msk_kernel_size": 3,
    "msk_num_feats": 256,
    "msk_num_heads": 4,
    "msk_num_layers": 4,
    "msk_type": "transformer",
    "msk_use_conv": True,
    "num_sources": 2,
    "stochastic": False,
    "use_wavelet": False,
    "wavelet_scale": 8,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune NeoSSNet on processed HLS-CMDS pairs."
    )
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument(
        "--device",
        default="auto",
        help="auto, cpu, cuda, or an explicit PyTorch device string.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the output checkpoint/training state when available.",
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Use a tiny train/validation subset to verify the pipeline.",
    )
    parser.add_argument(
        "--output-checkpoint",
        type=Path,
        default=DEFAULT_OUTPUT_CHECKPOINT,
    )
    parser.add_argument(
        "--base-checkpoint",
        type=Path,
        default=DEFAULT_BASE_CHECKPOINT,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_MODEL_CONFIG_PATH,
    )
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--max-grad-norm", type=float, default=5.0)
    return parser.parse_args(argv)


def resolve_device(device_name: str) -> torch.device:
    if device_name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_name)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def output_config_path(output_checkpoint: Path) -> Path:
    return output_checkpoint.with_suffix(".yaml")


def training_state_path(output_checkpoint: Path) -> Path:
    return output_checkpoint.with_suffix(".training_state.pt")


def load_model_config(config_path: Path) -> dict[str, object]:
    if config_path.is_file():
        with config_path.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
        return dict(config)
    return dict(DEFAULT_MODEL_CONFIG)


def build_model(model_config: dict[str, object]):
    add_neossnet_source_to_path()
    from models import MaskNet

    return MaskNet(**model_config)


def load_initial_weights(
    model,
    output_checkpoint: Path,
    base_checkpoint: Path,
    state_path: Path,
    device: torch.device,
    resume: bool,
) -> tuple[int, float, str]:
    start_epoch = 1
    best_val_loss = float("inf")
    source = "scratch"

    if resume and state_path.is_file():
        state = torch.load(state_path, map_location=device)
        model.load_state_dict(state["model_state"])
        start_epoch = int(state.get("epoch", 0)) + 1
        best_val_loss = float(state.get("best_val_loss", best_val_loss))
        source = str(state_path)
        return start_epoch, best_val_loss, source

    checkpoint = output_checkpoint if resume and output_checkpoint.is_file() else base_checkpoint
    if checkpoint.is_file() and checkpoint.stat().st_size > 0:
        model.load_state_dict(torch.load(checkpoint, map_location=device))
        source = str(checkpoint)
    return start_epoch, best_val_loss, source


def create_loaders(args: argparse.Namespace) -> tuple[DataLoader, DataLoader]:
    max_train_items = 4 if args.quick_test else None
    max_val_items = 2 if args.quick_test else None
    train_dataset = HlsCmdsSeparationDataset(
        split="train",
        random_crop=True,
        max_items=max_train_items,
        seed=42,
    )
    val_dataset = HlsCmdsSeparationDataset(
        split="val",
        random_crop=False,
        max_items=max_val_items,
        seed=42,
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    return train_loader, val_loader


def separation_l1_loss(output: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    output = output[:, :2, :]
    length = min(output.shape[-1], target.shape[-1])
    return F.l1_loss(output[..., :length], target[..., :length])


def train_epoch(
    model,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    max_grad_norm: float,
) -> float:
    model.train()
    total_loss = 0.0
    for mixed, target in loader:
        mixed = mixed.to(device, non_blocking=True)
        target = target.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        output = model(mixed)
        loss = separation_l1_loss(output, target)
        loss.backward()
        if max_grad_norm > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        optimizer.step()
        total_loss += float(loss.item())
    return total_loss / max(1, len(loader))


def validate_epoch(model, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    total_loss = 0.0
    with torch.inference_mode():
        for mixed, target in loader:
            mixed = mixed.to(device, non_blocking=True)
            target = target.to(device, non_blocking=True)
            output = model(mixed)
            total_loss += float(separation_l1_loss(output, target).item())
    return total_loss / max(1, len(loader))


def save_training_log_header(path: Path) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "epoch",
                "train_loss",
                "val_loss",
                "best_val_loss",
                "epoch_time_sec",
                "checkpoint_saved",
            ],
        )
        writer.writeheader()


def append_training_log(
    path: Path,
    epoch: int,
    train_loss: float,
    val_loss: float,
    best_val_loss: float,
    epoch_time_sec: float,
    checkpoint_saved: bool,
) -> None:
    save_training_log_header(path)
    with path.open("a", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "epoch",
                "train_loss",
                "val_loss",
                "best_val_loss",
                "epoch_time_sec",
                "checkpoint_saved",
            ],
        )
        writer.writerow(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "best_val_loss": best_val_loss,
                "epoch_time_sec": epoch_time_sec,
                "checkpoint_saved": int(checkpoint_saved),
            }
        )


def register_finetuned_model(output_checkpoint: Path, output_config: Path) -> None:
    initialize_database()
    db = SessionLocal()
    try:
        ensure_finetuned_model_record(
            db,
            checkpoint_path=output_checkpoint,
            config_path=output_config,
        )
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.epochs < 0:
        raise ValueError("--epochs must be 0 or greater.")

    output_checkpoint = resolve_path(args.output_checkpoint)
    output_config = output_config_path(output_checkpoint)
    base_checkpoint = resolve_path(args.base_checkpoint)
    config_path = resolve_path(args.config)
    state_path = training_state_path(output_checkpoint)
    device = resolve_device(args.device)

    model_config = load_model_config(config_path)
    output_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    output_config.parent.mkdir(parents=True, exist_ok=True)

    print("NeoSSNet HLS-CMDS fine-tuning")
    print(f"- NeoSSNet source: {NEOSSNET_SOURCE_DIR.relative_to(PROJECT_ROOT)}")
    print(f"- sample rate: {TARGET_SAMPLE_RATE_HZ} Hz")
    print(f"- segment length: {SEGMENT_SAMPLES} samples")
    print(f"- model sample rate assumption: {MODEL_SAMPLE_RATE} Hz")
    print(f"- device: {device}")
    print(f"- output checkpoint: {output_checkpoint.relative_to(PROJECT_ROOT)}")
    print(f"- output config: {output_config.relative_to(PROJECT_ROOT)}")

    train_loader, val_loader = create_loaders(args)
    print(f"- train samples: {len(train_loader.dataset)}")
    print(f"- val samples: {len(val_loader.dataset)}")
    print(f"- batch size: {args.batch_size}")

    model = build_model(model_config).to(device)
    start_epoch, best_val_loss, weight_source = load_initial_weights(
        model=model,
        output_checkpoint=output_checkpoint,
        base_checkpoint=base_checkpoint,
        state_path=state_path,
        device=device,
        resume=args.resume,
    )
    print(f"- initial weights: {weight_source}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    if args.resume and state_path.is_file():
        state = torch.load(state_path, map_location=device)
        if "optimizer_state" in state:
            optimizer.load_state_dict(state["optimizer_state"])

    with output_config.open("w", encoding="utf-8") as config_file:
        yaml.safe_dump(model_config, config_file, sort_keys=True)

    if args.epochs == 0:
        torch.save(model.state_dict(), output_checkpoint)
        register_finetuned_model(output_checkpoint, output_config)
        print("Saved initial checkpoint because --epochs 0 was requested.")
        return 0

    for epoch in range(start_epoch, args.epochs + 1):
        epoch_start = time.perf_counter()
        train_loss = train_epoch(
            model=model,
            loader=train_loader,
            optimizer=optimizer,
            device=device,
            max_grad_norm=args.max_grad_norm,
        )
        val_loss = validate_epoch(model=model, loader=val_loader, device=device)
        checkpoint_saved = val_loss < best_val_loss
        if checkpoint_saved:
            best_val_loss = val_loss
            torch.save(model.state_dict(), output_checkpoint)

        torch.save(
            {
                "epoch": epoch,
                "best_val_loss": best_val_loss,
                "model_state": model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "model_config": model_config,
            },
            state_path,
        )
        epoch_time_sec = time.perf_counter() - epoch_start
        append_training_log(
            TRAINING_LOG_PATH,
            epoch,
            train_loss,
            val_loss,
            best_val_loss,
            epoch_time_sec,
            checkpoint_saved,
        )
        print(
            f"[{epoch}/{args.epochs}] "
            f"train_l1={train_loss:.6f} "
            f"val_l1={val_loss:.6f} "
            f"best_val_l1={best_val_loss:.6f} "
            f"time={epoch_time_sec:.1f}s "
            f"saved={checkpoint_saved}"
        )

    if not output_checkpoint.is_file():
        torch.save(model.state_dict(), output_checkpoint)
    register_finetuned_model(output_checkpoint, output_config)
    print("PASS: NeoSSNet HLS fine-tuning completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
