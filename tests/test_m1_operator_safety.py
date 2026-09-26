"""Local configuration safety, not live-provider evidence."""
import pytest
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
