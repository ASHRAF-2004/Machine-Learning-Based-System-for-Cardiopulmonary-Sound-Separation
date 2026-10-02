import importlib.util
import json
import shutil
import sqlite3
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).parents[1] / "deploy" / "backup-manifest.py"
SPEC = importlib.util.spec_from_file_location("stethofuse_backup_manifest", SCRIPT)
manifest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manifest)


def fixture_tree(root: Path):
    data, private = root / "data", root / "private"
    data.mkdir(parents=True)
    private.mkdir()
    with sqlite3.connect(data / "m1.sqlite3") as db:
        db.execute("CREATE TABLE fixture (value TEXT)")
        db.execute("INSERT INTO fixture VALUES ('synthetic-only')")
    (private / "fixture.wav").write_bytes(b"synthetic non-patient audio fixture")
    env = root / "runtime.env"
    env.write_text("STETHOFUSE_TEST_FIXTURE=synthetic\n")
    return data, private, env


def run_create(data, private, env):
    captured = StringIO()
    with redirect_stdout(captured):
        manifest.create(SimpleNamespace(data_root=data, private_root=private, runtime_env=env))
    return json.loads(captured.getvalue())


def test_manifest_restore_verifies_sqlite_hashes_exact_file_sets_and_bytes(tmp_path):
    source = tmp_path / "source"
    data, private, env = fixture_tree(source)
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(run_create(data, private, env)))

    restored = tmp_path / "restored"
    restored_data, restored_private, restored_env = fixture_tree(restored)
    restored_env.write_bytes(env.read_bytes())
    # Restore fixture_tree made its own SQLite rows; copy exact source files to
    # model an accurate Restic restore, with no writes to a live database.
    shutil.copy2(data / "m1.sqlite3", restored_data / "m1.sqlite3")
    shutil.copy2(private / "fixture.wav", restored_private / "fixture.wav")

    args = SimpleNamespace(manifest=manifest_file, source_data=data, source_private=private,
        source_env=env, restored_data=restored_data, restored_private=restored_private,
        restored_env=restored_env)
    output = StringIO()
    with redirect_stdout(output):
        manifest.verify(args)
    assert "integrity_check=ok" in output.getvalue()


def test_manifest_restore_rejects_tampered_private_file(tmp_path):
    source = tmp_path / "source"
    data, private, env = fixture_tree(source)
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(run_create(data, private, env)))
    restored = tmp_path / "restored"
    restored_data, restored_private, restored_env = fixture_tree(restored)
    shutil.copy2(data / "m1.sqlite3", restored_data / "m1.sqlite3")
    (restored_private / "fixture.wav").write_bytes(b"tampered")
    restored_env.write_bytes(env.read_bytes())
    args = SimpleNamespace(manifest=manifest_file, source_data=data, source_private=private,
        source_env=env, restored_data=restored_data, restored_private=restored_private,
        restored_env=restored_env)
    with pytest.raises(ValueError):
        manifest.verify(args)


def test_manifest_creation_rejects_symlink_roots(tmp_path):
    source = tmp_path / "source"
    data, private, env = fixture_tree(source)
    data_link = tmp_path / "data-link"
    data_link.symlink_to(data, target_is_directory=True)
    with pytest.raises(ValueError):
        run_create(data_link, private, env)
