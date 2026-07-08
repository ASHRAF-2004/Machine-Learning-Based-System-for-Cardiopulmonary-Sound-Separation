"""Prepare HLS-CMDS paired files into train/val/test processed folders.

The raw dataset is left untouched. This script copies the paired Mix folder
files into:

datasets/hls_cmds/processed/{train,val,test}/{mixed,heart,lung}/

and writes split CSV files under datasets/hls_cmds/metadata/.
"""

from __future__ import annotations

import argparse
import csv
import random
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "datasets" / "hls_cmds"
SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class PairedExample:
    heart_id: str
    lung_id: str
    mixed_id: str
    row: dict[str, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare HLS-CMDS paired references for evaluation/training."
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DEFAULT_DATASET_ROOT,
        help="Path to datasets/hls_cmds.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of paired examples to prepare.",
    )
    return parser.parse_args()


def read_pairs(dataset_root: Path) -> list[PairedExample]:
    metadata_path = dataset_root / "metadata" / "Mix.csv"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"HLS-CMDS metadata file is missing: {metadata_path}")

    examples: list[PairedExample] = []
    with metadata_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            heart_id = (row.get("Heart Sound ID") or "").strip()
            lung_id = (row.get("Lung Sound ID") or "").strip()
            mixed_id = (row.get("Mixed Sound ID") or "").strip()
            if heart_id and lung_id and mixed_id:
                examples.append(
                    PairedExample(
                        heart_id=heart_id,
                        lung_id=lung_id,
                        mixed_id=mixed_id,
                        row=row,
                    )
                )
    return examples


def existing_pairs(dataset_root: Path, examples: list[PairedExample]) -> list[PairedExample]:
    raw_mix = dataset_root / "raw" / "Mix"
    available: list[PairedExample] = []
    for example in examples:
        paths = (
            raw_mix / f"{example.mixed_id}.wav",
            raw_mix / f"{example.heart_id}.wav",
            raw_mix / f"{example.lung_id}.wav",
        )
        if all(path.is_file() for path in paths):
            available.append(example)
    return available


def split_examples(
    examples: list[PairedExample],
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> dict[str, list[PairedExample]]:
    if not 0.0 < train_ratio < 1.0:
        raise ValueError("--train-ratio must be between 0 and 1.")
    if not 0.0 <= val_ratio < 1.0:
        raise ValueError("--val-ratio must be between 0 and 1.")
    if train_ratio + val_ratio >= 1.0:
        raise ValueError("--train-ratio + --val-ratio must be less than 1.")

    shuffled = list(examples)
    random.Random(seed).shuffle(shuffled)
    train_end = int(len(shuffled) * train_ratio)
    val_end = train_end + int(len(shuffled) * val_ratio)
    return {
        "train": shuffled[:train_end],
        "val": shuffled[train_end:val_end],
        "test": shuffled[val_end:],
    }


def ensure_output_dirs(dataset_root: Path) -> None:
    for split in SPLITS:
        for source_type in ("mixed", "heart", "lung"):
            (dataset_root / "processed" / split / source_type).mkdir(
                parents=True,
                exist_ok=True,
            )


def copy_split_files(dataset_root: Path, split: str, examples: list[PairedExample]) -> None:
    raw_mix = dataset_root / "raw" / "Mix"
    processed = dataset_root / "processed" / split
    for example in examples:
        shutil.copy2(raw_mix / f"{example.mixed_id}.wav", processed / "mixed" / f"{example.mixed_id}.wav")
        shutil.copy2(raw_mix / f"{example.heart_id}.wav", processed / "heart" / f"{example.heart_id}.wav")
        shutil.copy2(raw_mix / f"{example.lung_id}.wav", processed / "lung" / f"{example.lung_id}.wav")


def write_split_csv(dataset_root: Path, split: str, examples: list[PairedExample]) -> None:
    output_path = dataset_root / "metadata" / f"{split}_pairs.csv"
    fieldnames = [
        "split",
        "mixed_id",
        "heart_id",
        "lung_id",
        "mixed_path",
        "heart_path",
        "lung_path",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for example in examples:
            writer.writerow(
                {
                    "split": split,
                    "mixed_id": example.mixed_id,
                    "heart_id": example.heart_id,
                    "lung_id": example.lung_id,
                    "mixed_path": f"datasets/hls_cmds/processed/{split}/mixed/{example.mixed_id}.wav",
                    "heart_path": f"datasets/hls_cmds/processed/{split}/heart/{example.heart_id}.wav",
                    "lung_path": f"datasets/hls_cmds/processed/{split}/lung/{example.lung_id}.wav",
                }
            )


def main() -> int:
    args = parse_args()
    dataset_root = args.dataset_root.resolve()
    examples = existing_pairs(dataset_root, read_pairs(dataset_root))
    if args.limit is not None:
        examples = examples[: args.limit]

    if not examples:
        print("No complete HLS-CMDS paired examples found.", file=sys.stderr)
        return 1

    ensure_output_dirs(dataset_root)
    splits = split_examples(
        examples=examples,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )

    for split, split_examples_list in splits.items():
        copy_split_files(dataset_root, split, split_examples_list)
        write_split_csv(dataset_root, split, split_examples_list)
        print(f"{split}: {len(split_examples_list)} paired examples")

    print(f"Prepared {sum(len(items) for items in splits.values())} HLS-CMDS pairs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
