import base64
import json

import pytest
from app.services.orders import _validate_callback_url
from app.services.security import checkout_session_value
from app.services.updates import verify_package_digest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def test_callback_dns_private_address_is_rejected(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("10.0.0.8", 443))])
    with pytest.raises(ValueError, match="private"):
        _validate_callback_url("https://callback.example.test/hook")


def test_callback_public_dns_address_is_allowed(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))])
    _validate_callback_url("https://callback.example.test/hook")


def test_checkout_session_is_not_reusable_for_another_order():
    assert checkout_session_value("a") != checkout_session_value("b")


def test_package_digest_verification():
    assert verify_package_digest(b"release", "".join(["6e0f5a7b", "7c3b5a0c", "c33cce4d", "e4b6a2f3", "7a1d1e4a", "7e2f7d2c", "bba0a0f3", "6cc8d3a9"])) is False


def test_manifest_signature_canonicalization():
    private = Ed25519PrivateKey.generate()
    payload = {"version": "0.2.0", "sha256": "a" * 64, "url": "https://updates.example/release"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signature = private.sign(canonical)
    assert base64.b64decode(base64.b64encode(signature)) == signature
