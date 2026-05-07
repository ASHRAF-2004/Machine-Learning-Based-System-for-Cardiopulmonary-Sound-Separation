from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PUML_DIR = ROOT_DIR / "docs" / "software_design_report" / "diagrams" / "puml"
IMG_DIR = ROOT_DIR / "docs" / "software_design_report" / "diagrams" / "img"
PLANTUML_JAR = ROOT_DIR / "tools" / "plantuml.jar"


def print_missing_tool_instructions() -> None:
    print("PlantUML was not found.")
    print()
    print("Setup instructions:")
    print("1. Install Java and make sure the 'java' command works.")
    print("2. Download plantuml.jar into this project folder:")
    print(f"   {PLANTUML_JAR}")
    print("3. Optionally install Graphviz if PlantUML reports that dot/Graphviz is required.")
    print()
    print("Alternative:")
    print("Install PlantUML so the 'plantuml' command is available from PATH.")


def build_command(puml_file: Path) -> list[str] | None:
    if PLANTUML_JAR.exists():
        java_path = shutil.which("java")
        if not java_path:
            print("tools/plantuml.jar exists, but Java was not found on PATH.")
            print_missing_tool_instructions()
            return None

        return [
            java_path,
            "-jar",
            str(PLANTUML_JAR),
            "-tpng",
            "-o",
            str(IMG_DIR),
            str(puml_file),
        ]

    plantuml_path = shutil.which("plantuml")
    if plantuml_path:
        return [
            plantuml_path,
            "-tpng",
            "-o",
            str(IMG_DIR),
            str(puml_file),
        ]

    print_missing_tool_instructions()
    return None


def render_diagram(puml_file: Path) -> bool:
    output_file = IMG_DIR / f"{puml_file.stem}.png"
    command = build_command(puml_file)
    if command is None:
        return False

    print(f"Rendering: {puml_file.relative_to(ROOT_DIR)} -> {output_file.relative_to(ROOT_DIR)}")
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
        print(f"FAILED: {puml_file.name} exited with code {result.returncode}")
        return False

    if not output_file.exists():
        print(f"FAILED: expected output was not created: {output_file}")
        return False

    print(f"Rendered: {output_file.relative_to(ROOT_DIR)}")
    return True


def main() -> int:
    if not PUML_DIR.exists():
        print(f"Input folder does not exist: {PUML_DIR}")
        return 1

    IMG_DIR.mkdir(parents=True, exist_ok=True)

    puml_files = sorted(PUML_DIR.glob("*.puml"))
    if not puml_files:
        print(f"No .puml files found in: {PUML_DIR}")
        return 1

    if PLANTUML_JAR.exists() and not shutil.which("java"):
        print("tools/plantuml.jar exists, but Java was not found on PATH.")
        print()
        print_missing_tool_instructions()
        print()
        print("Summary: rendered 0 of {0} diagram(s).".format(len(puml_files)))
        return 1

    if not PLANTUML_JAR.exists() and not shutil.which("plantuml"):
        print(f"Found {len(puml_files)} PlantUML source file(s), but no renderer is available.")
        print()
        print_missing_tool_instructions()
        print()
        print("Summary: rendered 0 of {0} diagram(s).".format(len(puml_files)))
        return 1

    rendered = 0
    failed = 0

    for puml_file in puml_files:
        if render_diagram(puml_file):
            rendered += 1
        else:
            failed += 1

    print()
    print("Summary:")
    print(f"- Input folder: {PUML_DIR}")
    print(f"- Output folder: {IMG_DIR}")
    print(f"- Found: {len(puml_files)} diagram source file(s)")
    print(f"- Rendered: {rendered}")
    print(f"- Failed: {failed}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
