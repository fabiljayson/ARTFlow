"""Mock gateway HMAC signature tests (docs/payments.md §5, §2.1)."""
import pytest
from django.test import override_settings

from apps.payments import gateway


def test_sign_returns_sha256_prefix():
    sig = gateway.sign(b"hello")
    assert sig.startswith("sha256=")
    assert len(sig) == len("sha256=") + 64


def test_verify_roundtrip():
    body = b'{"event_id": "x"}'
    assert gateway.verify_signature(body, gateway.sign(body)) is True


def test_verify_fails_on_tampered_body():
    sig = gateway.sign(b'{"amount_xaf": 202000}')
    assert gateway.verify_signature(b'{"amount_xaf": 1}', sig) is False


def test_verify_fails_on_wrong_secret():
    sig = gateway.sign(b"body")
    with override_settings(PAYMENT_WEBHOOK_SECRET="autre-secret"):
        assert gateway.verify_signature(b"body", sig) is False


def test_verify_fails_on_malformed_header():
    assert gateway.verify_signature(b"body", None) is False
    assert gateway.verify_signature(b"body", "") is False
    assert gateway.verify_signature(b"body", "md5=abc") is False
    assert gateway.verify_signature(b"body", "sha256=zz") is False


def test_provider_status_mapping():
    assert gateway.provider_to_internal("SUCCESSFUL") == "SUCCEEDED"
    assert gateway.provider_to_internal("FAILED") == "FAILED"
    assert gateway.provider_to_internal("PENDING") == "PENDING"
    assert gateway.provider_to_internal("EXPIRED") == "EXPIRED"
    with pytest.raises(ValueError):
        gateway.provider_to_internal("WEIRD")


def test_initiate_returns_unique_mock_reference():
    first = gateway.initiate()
    second = gateway.initiate()
    assert first != second
    assert first.startswith("MOCK-") and second.startswith("MOCK-")
    assert len(first) <= 64
