import base64
import json
import time
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import pytest

from app.access_foundation.firebase_token import FirebaseIdTokenVerifier
from app.access_foundation.identity import (AuthenticationDenied, EmailVerificationRequired,
                                            ProviderAccountDisabled, ProviderUnavailable)
from app.m1.firebase_remote import FirebaseRestIdentityVerifier


def token_with_header(header=None):
    header = header or {"alg": "RS256", "kid": "test-key"}
    encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    return encoded + ".e30.signature"


def claims(**changes):
    value = {"aud": "stethofuse-c18cd-3cca0", "iss": "https://securetoken.google.com/stethofuse-c18cd-3cca0",
             "sub": "firebase-uid", "exp": 5000, "iat": 1000, "auth_time": 900,
             "email_verified": True}
    value.update(changes)
    return value


def test_local_verifier_calls_google_auth_firebase_verifier_and_checks_firebase_claims():
    calls = []
    verifier = FirebaseIdTokenVerifier("stethofuse-c18cd-3cca0", verify=lambda *a, **k: calls.append((a, k)) or claims(),
                                      request=object(), clock=lambda: 2000)
    result = verifier.verify(token_with_header())
    assert result["sub"] == "firebase-uid"
    assert calls[0][0][0] == token_with_header()
    assert calls[0][1] == {"audience": "stethofuse-c18cd-3cca0", "clock_skew_in_seconds": 0}


@pytest.mark.parametrize("header", [
    {"alg": "HS256", "kid": "test-key"},
    {"alg": "RS256"},
    {"alg": "RS256", "kid": ""},
])
def test_local_verifier_rejects_wrong_algorithm_or_missing_key(header):
    verifier = FirebaseIdTokenVerifier("stethofuse-c18cd-3cca0", verify=lambda *a, **k: claims(),
                                      request=object(), clock=lambda: 2000)
    with pytest.raises(AuthenticationDenied):
        verifier.verify(token_with_header(header))


@pytest.mark.parametrize("change", [
    {"aud": "wrong-project"}, {"iss": "https://accounts.google.com"}, {"sub": " "},
    {"exp": 2000}, {"iat": 2001}, {"auth_time": 2001}, {"auth_time": True},
])
def test_local_verifier_rejects_invalid_firebase_claims(change):
    verifier = FirebaseIdTokenVerifier("stethofuse-c18cd-3cca0", verify=lambda *a, **k: claims(**change),
                                      request=object(), clock=lambda: 2000)
    with pytest.raises(AuthenticationDenied):
        verifier.verify(token_with_header())


def test_local_verifier_distinguishes_public_certificate_outage_from_bad_token():
    verifier = FirebaseIdTokenVerifier("stethofuse-c18cd-3cca0", verify=lambda *a, **k: (_ for _ in ()).throw(RuntimeError()), request=object())
    with pytest.raises(ProviderUnavailable):
        verifier.verify(token_with_header())


def _signed_firebase_token(private_key, **changes):
    now = int(time.time())
    payload = {"aud": "stethofuse-c18cd-3cca0", "iss": "https://securetoken.google.com/stethofuse-c18cd-3cca0",
               "sub": "firebase-uid", "exp": now + 3600, "iat": now - 10,
               "auth_time": now - 20}
    payload.update(changes)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "firebase-key", "typ": "JWT"})


def _firebase_certificate_request(private_key):
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Firebase test key")])
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(private_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=2))
        .sign(private_key, hashes.SHA256()))
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)

    class Request:
        def __call__(self, url, method="GET", **kwargs):
            assert url == "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
            assert method == "GET"
            return SimpleNamespace(status=200, data=json.dumps({"firebase-key": cert_pem.decode()}).encode())
    return Request()


def test_google_auth_performs_real_rs256_signature_and_claim_verification():
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = FirebaseIdTokenVerifier("stethofuse-c18cd-3cca0", request=_firebase_certificate_request(signing_key))
    assert verifier.verify(_signed_firebase_token(signing_key))["sub"] == "firebase-uid"
    with pytest.raises(AuthenticationDenied):
        verifier.verify(_signed_firebase_token(wrong_key))
    with pytest.raises(AuthenticationDenied):
        verifier.verify(_signed_firebase_token(signing_key, iss="https://accounts.google.com"))


class FakeResponse:
    def __init__(self, status, value):
        self.status_code = status
        self.value = value

    def __enter__(self): return self
    def __exit__(self, *args): return False
    def iter_bytes(self): yield json.dumps(self.value).encode()


class FakeClient:
    def __init__(self, response): self.response, self.calls = response, []
    def stream(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


class FakeLocalVerifier:
    def verify(self, token):
        assert token == "signed-token"
        return claims()


def rest_user(**changes):
    value = {"localId": "firebase-uid", "disabled": False, "validSince": "999",
             "email": "user@example.invalid", "emailVerified": True}
    value.update(changes)
    return {"users": [value]}


def rest_verifier(client):
    return FirebaseRestIdentityVerifier(project_id="stethofuse-c18cd-3cca0", api_key="public-test-api-key",
                                        client=client, token_verifier=FakeLocalVerifier())


def test_rest_verifier_checks_live_record_and_posts_same_token_without_auth_header():
    client = FakeClient(FakeResponse(200, rest_user()))
    verifier = rest_verifier(client)
    identity = verifier.verify("signed-token")
    assert identity.uid == "firebase-uid" and identity.email_verified is True
    method, url, request = client.calls[0]
    assert method == "POST" and url == "https://identitytoolkit.googleapis.com/v1/accounts:lookup"
    assert request["params"] == {"key": "public-test-api-key"}
    assert request["json"] == {"idToken": "signed-token"}
    assert "Authorization" not in request["headers"]


@pytest.mark.parametrize("record,error", [
    (rest_user(disabled=True), ProviderAccountDisabled),
    (rest_user(validSince="1001"), AuthenticationDenied),
    (rest_user(localId="another-uid"), ProviderUnavailable),
    ({"users": []}, ProviderUnavailable),
    ({"users": [{"localId": "firebase-uid", "disabled": False}]}, ProviderUnavailable),
])
def test_rest_verifier_rejects_disabled_revoked_mismatched_or_malformed_current_record(record, error):
    with pytest.raises(error):
        rest_verifier(FakeClient(FakeResponse(200, record))).verify("signed-token")


@pytest.mark.parametrize("message", ["INVALID_ID_TOKEN", "TOKEN_EXPIRED", "USER_NOT_FOUND"])
def test_rest_verifier_denies_invalid_or_deleted_identity(message):
    with pytest.raises(AuthenticationDenied):
        rest_verifier(FakeClient(FakeResponse(400, {"error": {"message": message}}))).verify("signed-token")


def test_rest_verifier_provider_failures_fail_closed_and_suppress_secret_diagnostics(caplog, capsys):
    import httpx
    from unittest.mock import Mock

    client = Mock()
    secret_diagnostic = "signed-token api-key-diagnostic"
    client.stream.side_effect = httpx.ReadTimeout(secret_diagnostic)
    verifier = rest_verifier(client)
    with pytest.raises(ProviderUnavailable, match="^Firebase Auth current-user check is unavailable.$"):
        verifier.verify("signed-token")
    captured = capsys.readouterr()
    rendered = "\n".join([str(caplog.text), captured.out, captured.err])
    assert secret_diagnostic not in rendered
