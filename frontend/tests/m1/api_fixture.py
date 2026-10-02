"""TEST ONLY: real M1 API with two fictional verified identities, no live provider.

Loopback ephemeral listener + temporary DB/storage. Never import this into app.main.
"""
import json
import socket
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.access_foundation import AuthenticationDenied, VerifiedIdentity
from app.m1.api import create_app
from app.m1.config import Settings


class TestVerifier:
    def verify(self, token):
        if token not in {"M1-MOCK:alice", "M1-MOCK:bob"}:
            raise AuthenticationDenied("Invalid fictional test identity.")
        uid = token.split(":")[1]
        return VerifiedIdentity(uid, uid + "@example.invalid", True)


if __name__ == "__main__":
    with TemporaryDirectory(prefix="stethofuse-m1-browser-") as directory:
        root = Path(directory)
        app = create_app(Settings(root / "m1.sqlite3", root / "private"), verifier=TestVerifier())
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            print(json.dumps({"port": listener.getsockname()[1]}), flush=True)
            server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level="warning"))
            server.run(sockets=[listener])
