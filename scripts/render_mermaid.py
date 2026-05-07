"""Render Mermaid diagrams for the software design report."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MMD_DIR = ROOT_DIR / "docs" / "software_design_report" / "diagrams" / "mmd"
SVG_DIR = ROOT_DIR / "docs" / "software_design_report" / "diagrams" / "img" / "mermaid" / "svg"
PNG_DIR = ROOT_DIR / "docs" / "software_design_report" / "diagrams" / "img" / "mermaid" / "png"


def format_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def find_mermaid_cli() -> str | None:
    """Prefer the Windows npm .cmd shim, then fall back to mmdc."""
    return shutil.which("mmdc.cmd") or shutil.which("mmdc")


def print_missing_tool_instructions() -> None:
    print("Mermaid CLI was not found.")
    print()
    print("Install it with:")
    print("npm install -g @mermaid-js/mermaid-cli")
    print()
    print("Then test it with:")
    print("mmdc.cmd -h")


def render_diagram(mmdc_path: str, mmd_file: Path, output_file: Path, output_format: str) -> bool:
    command = [
        mmdc_path,
        "-i",
        str(mmd_file),
        "-o",
        str(output_file),
        "-e",
        output_format,
        "--quiet",
    ]

    print(f"Rendering: {format_path(mmd_file)} -> {format_path(output_file)}")
    result = subprocess.run(
        command,
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())

    if result.returncode != 0:
        print(f"FAILED: {mmd_file.name} to {output_format.upper()} exited with code {result.returncode}")
        return False

    if not output_file.exists():
        print(f"FAILED: expected output was not created: {format_path(output_file)}")
        return False

    print(f"Rendered: {format_path(output_file)}")
    return True


def main() -> int:
    if not MMD_DIR.exists():
        print(f"Input folder does not exist: {format_path(MMD_DIR)}")
        return 1

    mmd_files = sorted(MMD_DIR.glob("*.mmd"))
    if not mmd_files:
        print(f"No .mmd files found in: {format_path(MMD_DIR)}")
        return 1

    mmdc_path = find_mermaid_cli()
    if not mmdc_path:
        print(f"Found {len(mmd_files)} Mermaid source file(s), but no renderer is available.")
        print()
        print_missing_tool_instructions()
        print()
        print(f"Summary: rendered 0 of {len(mmd_files) * 2} output file(s).")
        return 1

    SVG_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Mermaid CLI: {mmdc_path}")
    print(f"Input folder: {format_path(MMD_DIR)}")
    print(f"SVG output folder: {format_path(SVG_DIR)}")
    print(f"PNG output folder: {format_path(PNG_DIR)}")
    print()

    rendered = 0
    failed = 0

    for mmd_file in mmd_files:
        outputs = [
            (SVG_DIR / f"{mmd_file.stem}.svg", "svg"),
            (PNG_DIR / f"{mmd_file.stem}.png", "png"),
        ]

        for output_file, output_format in outputs:
            if render_diagram(mmdc_path, mmd_file, output_file, output_format):
                rendered += 1
            else:
                failed += 1

    total_outputs = len(mmd_files) * 2

    print()
    print("Mermaid render summary")
    print(f"Source diagrams: {len(mmd_files)}")
    print(f"Expected outputs: {total_outputs}")
    print(f"Rendered: {rendered}")
    print(f"Failed: {failed}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
