"""Local configuration safety, not live-provider evidence."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.m1.api import create_app
from app.m1.config import Settings


def test_existing_nonprivate_directory_is_not_chmodded_or_adopted(tmp_path):
    storage = tmp_path / "unrelated"
    storage.mkdir(mode=0o755)
    storage.chmod(0o755)
    database = tmp_path / "new.sqlite3"
    with pytest.raises(ValueError, match="must be private"):
        with TestClient(create_app(Settings(database, storage))):
            pass
    assert storage.stat().st_mode & 0o777 == 0o755
    assert not database.exists()


def test_runtime_context_explicitly_includes_all_required_migrations():
    """A local migration pass is insufficient if Docker excludes its SQL file."""
    root = Path(__file__).parents[1]
    rules = (root / ".dockerignore").read_text().splitlines()
    for migration in sorted((root / "app/m1/migrations").glob("*.sql")):
        include = "!" + migration.relative_to(root).as_posix()
        assert include in rules, f"Runtime context is missing {migration.name}"
        assert rules.index(include) > rules.index("app/m1/migrations/*")
