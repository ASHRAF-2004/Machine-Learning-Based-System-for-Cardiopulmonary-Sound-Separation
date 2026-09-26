import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

SOURCE = Path(__file__).parents[1] / "deploy" / "auth-verifier" / "main.py"
SPEC = importlib.util.spec_from_file_location("stethofuse_auth_verifier", SOURCE)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.fixture
def verified_client():
    verify = Mock(return_value={"uid": "uid-a", "email": "a@example.invalid", "email_verified": True})
    app = module.create_app(verify_identity=verify)
    with TestClient(app) as client:
        yield client, verify


def test_health_is_static_and_has_no_identity_dependency(verified_client):
    client, verify = verified_client
    response = client.get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    verify.assert_not_called()


def test_valid_verification_returns_only_minimal_identity(verified_client):
    client, verify = verified_client
    response = client.post("/v1/verify", json={"id_token": "synthetic-token"})
    assert response.status_code == 200
    assert response.json() == {"uid": "uid-a", "email": "a@example.invalid", "email_verified": True}
    verify.assert_called_once_with("synthetic-token")
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("kwargs,status", [
    ({"json": {}}, 400),
    ({"json": {"id_token": "x", "uid": "uid-attacker"}}, 400),
    ({"content": b'{"id_token":"x"}', "headers": {"content-type": "text/plain"}}, 400),
    ({"json": {"id_token": "x" * 20000}}, 413),
])
def test_bad_and_oversized_requests_do_not_call_auth(verified_client, kwargs, status):
    client, verify = verified_client
    response = client.post("/v1/verify", **kwargs)
    assert response.status_code == status
    verify.assert_not_called()


def test_no_user_enumeration_or_other_operations(verified_client):
    client, verify = verified_client
    assert client.get("/v1/users/uid-a").status_code == 404
    for method, path in (("post", "/v1/users"), ("patch", "/v1/verify"), ("delete", "/v1/verify")):
        assert client.request(method.upper(), path, json={}).status_code == 404
    verify.assert_not_called()


class User:
    uid = "uid-a"
    email = "a@example.invalid"
    email_verified = True
    disabled = False


class FakeAuth:
    class UserDisabledError(Exception): pass
    class InvalidIdTokenError(Exception): pass
    class ExpiredIdTokenError(Exception): pass
    class RevokedIdTokenError(Exception): pass
    class UserNotFoundError(Exception): pass

    def __init__(self, *, verify_error=None, user=None):
        self.verify_error = verify_error
        self.user = user or User()
        self.verify_calls, self.user_calls = [], []

    def verify_id_token(self, token, **kwargs):
        self.verify_calls.append((token, kwargs))
        if self.verify_error:
            raise self.verify_error
        return {"uid": "uid-a"}

    def get_user(self, uid, **kwargs):
        self.user_calls.append((uid, kwargs))
        return self.user


def test_firebase_current_user_enables_revocation_and_reads_current_record():
    auth = FakeAuth()
    result = module.firebase_current_user("only-a-test-placeholder", auth_module=auth, app="explicit")
    assert result == {"uid": "uid-a", "email": "a@example.invalid", "email_verified": True}
    assert auth.verify_calls == [("only-a-test-placeholder", {"app": "explicit", "check_revoked": True, "clock_skew_seconds": 0})]
    assert auth.user_calls == [("uid-a", {"app": "explicit"})]


@pytest.mark.parametrize("user,error", [
    (SimpleNamespace(uid="uid-a", email="a@example.invalid", email_verified=True, disabled=True), module.AccountDisabled),
    (SimpleNamespace(uid="uid-a", email="a@example.invalid", email_verified=False, disabled=False), module.EmailUnverified),
    (SimpleNamespace(uid="uid-b", email="a@example.invalid", email_verified=True, disabled=False), module.InvalidIdentity),
])
def test_firebase_current_user_rejects_non_current_identity(user, error):
    with pytest.raises(error):
        module.firebase_current_user("placeholder", auth_module=FakeAuth(user=user))


def test_firebase_revoked_disabled_and_missing_tokens_are_not_accepted(caplog, capsys):
    import logging

    caplog.set_level(logging.DEBUG)
    secret_marker = "synthetic-private-token-and-header"
    for error, expected in ((FakeAuth.RevokedIdTokenError, 401),
                            (FakeAuth.UserDisabledError, 403), (RuntimeError, 503)):
        auth = FakeAuth(verify_error=error(secret_marker))
        app = module.create_app(verify_identity=lambda token: module.firebase_current_user(token, auth_module=auth))
        with TestClient(app) as client:
            response = client.post("/v1/verify", json={"id_token": secret_marker},
                                   headers={"Authorization": "Bearer " + secret_marker})
            assert response.status_code == expected
            assert secret_marker not in response.text
    captured = capsys.readouterr()
    assert secret_marker not in caplog.text + captured.out + captured.err
