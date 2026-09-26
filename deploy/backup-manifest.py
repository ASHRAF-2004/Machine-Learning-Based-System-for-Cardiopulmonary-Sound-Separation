#!/usr/bin/env python3
"""Create/verify non-secret SHA-256 metadata for isolated backup drills."""
from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path, PurePosixPath


def entries(root: Path, area: str):
    if root.is_symlink():
        raise ValueError("Backup input root must not be a symlink.")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Backup input is not a directory.")
    result = []
    for base, dirs, files in os.walk(root, followlinks=False):
        base_path = Path(base)
        for name in dirs:
            path = base_path / name
            if path.is_symlink():
                raise ValueError("Symlink in persistent backup data.")
        for name in files:
            path = base_path / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("Non-regular entry in persistent backup data.")
            digest = hashlib.sha256()
            size = 0
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
                    size += len(block)
            result.append({"area": area, "path": path.relative_to(root).as_posix(),
                           "size": size, "sha256": digest.hexdigest()})
    return result


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def regular_directory(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError("Persistent backup root must not be a symlink.")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError("Persistent backup root must be a directory.")
    return resolved


def regular_file_set(root: Path) -> set[str]:
    result = set()
    for base, dirs, files in os.walk(root, followlinks=False):
        base_path = Path(base)
        for name in dirs:
            if (base_path / name).is_symlink():
                raise ValueError("Symlink in persistent backup data.")
        for name in files:
            path = base_path / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("Non-regular entry in persistent backup data.")
            result.add(path.relative_to(root).as_posix())
    return result


def create(args):
    if args.runtime_env.is_symlink() or not args.runtime_env.is_file():
        raise ValueError("Runtime environment must be a regular file.")
    env_path = args.runtime_env.resolve(strict=True)
    digest = sha256_path(env_path)
    output = {
        "format": "stethofuse-sha256-manifest-v1",
        "files": entries(args.data_root, "data") + entries(args.private_root, "private") + [
            {"area": "config", "path": "runtime.env", "size": env_path.stat().st_size, "sha256": digest}
        ],
    }
    json.dump(output, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")


def _safe_member(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if relative.is_absolute() or not relative.parts or any(p in ("", ".", "..") for p in relative.parts):
        raise ValueError("Invalid manifest path.")
    root = root.resolve(strict=True)
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("Manifest path traverses a symlink.")
    path = candidate.resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Manifest points outside a regular restored file.")
    return path


def verify(args):
    manifest = json.loads(args.manifest.read_text())
    if not isinstance(manifest, dict) or manifest.get("format") != "stethofuse-sha256-manifest-v1" or not isinstance(manifest.get("files"), list):
        raise ValueError("Unsupported backup manifest.")
    for env_path in (args.source_env, args.restored_env):
        if env_path.is_symlink() or not env_path.is_file():
            raise ValueError("Runtime environment restore path must be a regular file.")
    roots = {
        "data": (regular_directory(args.source_data), regular_directory(args.restored_data)),
        "private": (regular_directory(args.source_private), regular_directory(args.restored_private)),
        "config": (args.source_env.resolve(strict=True).parent, args.restored_env.resolve(strict=True).parent),
    }
    expected_keys = set()
    for item in manifest["files"]:
        if not isinstance(item, dict) or item.get("area") not in roots or not isinstance(item.get("path"), str):
            raise ValueError("Invalid manifest entry.")
        area, relative = item["area"], item["path"]
        if area == "config" and relative != "runtime.env":
            raise ValueError("Unsupported backup config path.")
        key = (area, relative)
        if key in expected_keys:
            raise ValueError("Duplicate manifest entry.")
        expected_keys.add(key)
        source_root, restored_root = roots[area]
        source_name = "runtime.env" if area == "config" else relative
        restored_name = "runtime.env" if area == "config" else relative
        source = _safe_member(source_root, source_name)
        restored = _safe_member(restored_root, restored_name)
        if source.stat().st_size != item.get("size") or restored.stat().st_size != item.get("size"):
            raise ValueError("Restored file size differs from backup manifest.")
        for file_path in (source, restored):
            if sha256_path(file_path) != item.get("sha256"):
                raise ValueError("Source or restored file differs from SHA-256 manifest.")
        if not filecmp.cmp(source, restored, shallow=False):
            raise ValueError("Restored file bytes differ from source.")

    # Compare exact file sets so omitted/unexpected persistent files are visible.
    for area in ("data", "private"):
        source_root, restored_root = roots[area]
        source_files = regular_file_set(source_root)
        restored_files = regular_file_set(restored_root)
        expected = {name for kind, name in expected_keys if kind == area}
        if source_files != expected or restored_files != expected:
            raise ValueError("Persistent file set differs from backup manifest.")

    database = args.restored_data / "m1.sqlite3"
    if not database.is_file():
        raise ValueError("Restored M1 SQLite database is missing.")
    uri = database.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise ValueError("Restored SQLite integrity check failed.")
    print("Restore verification passed: manifest SHA-256, exact data/private file sets, byte comparisons, and SQLite integrity_check=ok.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("create")
    make.add_argument("--data-root", type=Path, required=True)
    make.add_argument("--private-root", type=Path, required=True)
    make.add_argument("--runtime-env", type=Path, required=True)
    make.set_defaults(func=create)
    check = commands.add_parser("verify-restore")
    for name in ("manifest", "source-data", "source-private", "source-env", "restored-data", "restored-private", "restored-env"):
        check.add_argument("--" + name, type=Path, required=True)
    check.set_defaults(func=verify)
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception:
        print("Backup manifest operation failed; inspect paths and the isolated development data.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
