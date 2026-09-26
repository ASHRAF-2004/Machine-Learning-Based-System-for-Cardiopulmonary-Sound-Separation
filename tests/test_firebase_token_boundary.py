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
from app.m1.firebase_remote import CloudRunFirebaseIdentityVerifier


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


def test_remote_verifier_posts_only_token_and_requires_uid_match():
    client = FakeClient(FakeResponse(200, {"uid": "firebase-uid", "email": "user@example.invalid", "email_verified": True}))
    verifier = CloudRunFirebaseIdentityVerifier(project_id="stethofuse-c18cd-3cca0", service_url="https://auth-verifier-xyz.a.run.app",
                                               client=client, token_verifier=FakeLocalVerifier())
    identity = verifier.verify("signed-token")
    assert identity.uid == "firebase-uid" and identity.email_verified is True
    method, url, request = client.calls[0]
    assert method == "POST" and url == "https://auth-verifier-xyz.a.run.app/v1/verify"
    assert request["json"] == {"id_token": "signed-token"}
    assert "Authorization" not in request["headers"]


def test_remote_verifier_transport_timeout_fails_closed():
    import httpx
    from unittest.mock import Mock

    client = Mock()
    client.stream.side_effect = httpx.ReadTimeout("private transport diagnostic")
    verifier = CloudRunFirebaseIdentityVerifier(project_id="stethofuse-c18cd-3cca0",
        service_url="https://auth-verifier-xyz.a.run.app", client=client,
        token_verifier=FakeLocalVerifier())
    with pytest.raises(ProviderUnavailable, match="^Firebase verifier is unavailable.$"):
        verifier.verify("signed-token")


@pytest.mark.parametrize("body", [
    b"not-json",
    b'{"uid":"different-uid","email":"a@example.invalid","email_verified":true}',
    b'{"uid":"firebase-uid","email":"a@example.invalid","email_verified":true,"role":"admin"}',
])
def test_remote_verifier_untrusted_success_response_fails_closed(body):
    response = FakeResponse(200, None)
    response.iter_bytes = lambda: iter([body])
    verifier = CloudRunFirebaseIdentityVerifier(project_id="stethofuse-c18cd-3cca0",
        service_url="https://auth-verifier-xyz.a.run.app", client=FakeClient(response),
        token_verifier=FakeLocalVerifier())
    with pytest.raises(ProviderUnavailable):
        verifier.verify("signed-token")


@pytest.mark.parametrize("status,payload,error", [
    (401, {"error": "invalid_identity"}, AuthenticationDenied),
    (403, {"error": "email_verification_required"}, EmailVerificationRequired),
    (403, {"error": "account_disabled"}, ProviderAccountDisabled),
    (503, {"error": "identity_provider_unavailable"}, ProviderUnavailable),
])
def test_remote_verifier_maps_minimal_provider_results(status, payload, error):
    verifier = CloudRunFirebaseIdentityVerifier(project_id="stethofuse-c18cd-3cca0", service_url="https://auth-verifier-xyz.a.run.app",
                                               client=FakeClient(FakeResponse(status, payload)), token_verifier=FakeLocalVerifier())
    with pytest.raises(error):
        verifier.verify("signed-token")


@pytest.mark.parametrize("url", [
    "http://auth-verifier.a.run.app", "https://example.com",
    "https://auth-verifier.a.run.app.evil.test", "https://u:p@auth-verifier.a.run.app",
    "https://auth-verifier.a.run.app/?next=x",
])
def test_remote_verifier_rejects_untrusted_service_urls(url):
    with pytest.raises(ValueError):
        CloudRunFirebaseIdentityVerifier(project_id="stethofuse-c18cd-3cca0", service_url=url,
                                         client=FakeClient(FakeResponse(503, {})), token_verifier=FakeLocalVerifier())
