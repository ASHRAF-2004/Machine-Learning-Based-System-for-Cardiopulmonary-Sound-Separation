"""TEST ONLY: isolated real API + fictional identities; optional worker pause for UI observation."""
import json
import socket
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.access_foundation import AuthenticationDenied, Role, VerifiedIdentity
from app.m1.api import create_app
from app.m1.config import Settings
from app.m1.store import M1Store


class TestVerifier:
    def verify(self, token):
        if token not in {"M1-MOCK:" + name for name in ("alice", "bob", "analyst", "admin")}:
            raise AuthenticationDenied("Invalid test identity")
        uid = token.split(":")[1]
        return self.lookup_existing(uid)

    def lookup_existing(self, uid):
        return VerifiedIdentity(uid, uid + "@example.invalid", True)


if __name__ == "__main__" and "--worker" in sys.argv:
    import os
    from app.m1.worker import Worker
    with Worker(Settings.from_environment(), Path(os.environ["STETHOFUSE_MODEL_CHECKPOINT"]),
                ROOT / "research/configs/final_separator_v2.json") as worker:
        actual = worker.separator.separate
        def observed(canonical):
            print("READY_FOR_INFERENCE", flush=True)
            if sys.stdin.readline().strip() != "continue":
                raise RuntimeError("Test harness terminated")
            return actual(canonical)
        worker.separator.separate = observed
        print(json.dumps(worker.run_once()), flush=True)
elif __name__ == "__main__":
    import uvicorn
    with TemporaryDirectory(prefix="stethofuse-ml-browser-") as directory:
        root = Path(directory)
        settings = Settings(root / "m1.sqlite3", root / "private", separation_enabled=True)
        settings.validate()
        # Local acceptance owns this new temporary directory, never an operator DB.
        assert settings.database.parent == root and settings.private_storage.parent == root
        verifier = TestVerifier()
        store = M1Store(settings.database)
        store.initialize()
        for name in ("alice", "bob", "analyst", "admin"):
            store.register_verified_identity(verifier.lookup_existing(name))
        store.bootstrap_first_admin(verifier, provider_uid="admin", confirmed_uid="admin")
        analyst_id = store.me(verifier.lookup_existing("analyst"))["id"]
        store.change_account(verifier.lookup_existing("admin"), analyst_id,
                             confirmed_target_id=analyst_id, role=Role.AUDIO_ANALYST)
        app = create_app(settings, verifier=verifier)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            print(json.dumps({"port":listener.getsockname()[1],"database":str(settings.database),
                              "privateStorage":str(settings.private_storage),"analystId":analyst_id,
                              "host":"127.0.0.1", "workerLock":str(settings.database)+".worker.lock",
                              "identityMode":"TEST ONLY verifier injection + browser SDK stand-in"}),flush=True)
            uvicorn.Server(uvicorn.Config(app, access_log=False, log_level="warning")).run(sockets=[listener])
