"""Webhook API — POST /api/v1/payments/webhook/ (docs/payments.md §2.1.1, plan D3 Task 3)."""
import json

import pytest
from rest_framework.test import APIClient

from apps.commerce.models import Order, Payment
from apps.conftest import make_order, make_pending
from apps.payments import gateway
from apps.payments.models import PaymentEvent

WEBHOOK = "/api/v1/payments/webhook/"


@pytest.fixture
def client():
    return APIClient()


def payload(payment, *, event_id="evt-1", status="SUCCESSFUL", amount=None, failure_reason=None):
    body = {
        "event_id": event_id,
        "external_reference": payment.external_reference,
        "status": status,
        "amount_xaf": payment.amount_xaf if amount is None else amount,
    }
    if failure_reason:
        body["failure_reason"] = failure_reason
    return body


def post_raw(client, raw: bytes, *, signed=True):
    headers = {"HTTP_X_ARTFLOW_SIGNATURE": gateway.sign(raw)} if signed else {}
    return client.post(
        WEBHOOK, raw, content_type="application/json", **headers
    )


def post_payload(client, body: dict, *, signed=True):
    return post_raw(client, json.dumps(body).encode(), signed=signed)


@pytest.fixture
def pending_payment(db, user, artwork_factory):
    art = artwork_factory(title="Œuvre à payer", price=25000, stock=5)
    return make_pending(make_order(user, art, quantity=2))


class TestSignature:
    def test_valid_signature_marks_order_paid(self, client, pending_payment):
        resp = post_payload(client, payload(pending_payment))

        assert resp.status_code == 200
        assert resp.json() == {
            "event_id": "evt-1",
            "payment_status": Payment.Status.SUCCEEDED,
            "order_status": Order.Status.PAID,
            "duplicate": False,
        }
        pending_payment.order.refresh_from_db()
        assert pending_payment.order.status == Order.Status.PAID
        assert PaymentEvent.objects.get(event_id="evt-1").signature_valid is True

    def test_missing_signature_rejected(self, client, pending_payment):
        resp = post_payload(client, payload(pending_payment), signed=False)

        assert resp.status_code == 403
        error = resp.json()["error"]
        assert error["code"] == "invalid_signature"
        assert set(error) == {"code", "message", "details"}
        pending_payment.refresh_from_db()
        assert pending_payment.status == Payment.Status.PENDING
        assert not PaymentEvent.objects.exists()

    def test_tampered_body_rejected(self, client, pending_payment):
        raw = json.dumps(payload(pending_payment)).encode()
        signature = gateway.sign(raw)
        tampered = json.dumps(
            payload(pending_payment, amount=1)
        ).encode()  # même event, montant modifié après signature

        resp = client.post(
            WEBHOOK, tampered, content_type="application/json",
            HTTP_X_ARTFLOW_SIGNATURE=signature,
        )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "invalid_signature"
        assert not PaymentEvent.objects.exists()


class TestIdempotencyAndErrors:
    def test_duplicate_event_id_200_noop(self, client, pending_payment):
        body = payload(pending_payment)
        first = post_payload(client, body)
        second = post_payload(client, body)

        assert first.status_code == 200 and first.json()["duplicate"] is False
        assert second.status_code == 200 and second.json()["duplicate"] is True
        assert PaymentEvent.objects.filter(event_id="evt-1").count() == 1

    def test_amount_mismatch_conflict(self, client, pending_payment):
        resp = post_payload(client, payload(pending_payment, amount=1))

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "conflict"
        assert not PaymentEvent.objects.exists()

    def test_unknown_reference_404(self, client, db):
        body = {
            "event_id": "evt-x",
            "external_reference": "inconnu",
            "status": "SUCCESSFUL",
            "amount_xaf": 1000,
        }
        resp = post_payload(client, body)

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"

    def test_malformed_json_400(self, client):
        resp = post_raw(client, b"pas du json")

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "validation_error"

    def test_unknown_provider_status_400(self, client, pending_payment):
        resp = post_payload(client, payload(pending_payment, status="WEIRD"))

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "validation_error"
        assert not PaymentEvent.objects.exists()


class TestFailedDelivery:
    def test_failed_webhook_releases_and_cancels(self, client, pending_payment):
        resp = post_payload(
            client,
            payload(pending_payment, status="FAILED", failure_reason="Refus opérateur"),
        )

        assert resp.status_code == 200
        assert resp.json()["payment_status"] == Payment.Status.FAILED
        pending_payment.order.refresh_from_db()
        assert pending_payment.order.status == Order.Status.CANCELLED
