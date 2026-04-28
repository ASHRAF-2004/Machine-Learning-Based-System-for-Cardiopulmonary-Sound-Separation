"""Remove macOS junk files from the HLS-CMDS dataset folder."""

from __future__ import annotations

import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = PROJECT_ROOT / "datasets" / "hls_cmds"


def format_path(path: Path) -> str:
    """Return a readable project-relative path when possible."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def is_junk_file(path: Path) -> bool:
    """Match only known dataset junk files, never normal WAV audio files."""
    name = path.name
    return name == ".DS_Store" or name.startswith("._")


def remove_junk(dataset_root: Path) -> tuple[int, int]:
    files_removed = 0
    folders_removed = 0

    if not dataset_root.exists():
        raise FileNotFoundError(f"Dataset folder not found: {dataset_root}")

    for folder in sorted(dataset_root.rglob("__MACOSX"), key=lambda p: len(p.parts), reverse=True):
        if folder.is_dir():
            shutil.rmtree(folder)
            folders_removed += 1
            print(f"Removed folder: {format_path(folder)}")

    for path in sorted(dataset_root.rglob("*")):
        if path.is_file() and is_junk_file(path):
            path.unlink()
            files_removed += 1
            print(f"Removed file: {format_path(path)}")

    return files_removed, folders_removed


def main() -> None:
    files_removed, folders_removed = remove_junk(DATASET_ROOT)

    print()
    print("Cleanup summary")
    print(f"Dataset folder: {format_path(DATASET_ROOT)}")
    print(f"Files removed: {files_removed}")
    print(f"Folders removed: {folders_removed}")
    print(f"Total removed: {files_removed + folders_removed}")


if __name__ == "__main__":
    main()
