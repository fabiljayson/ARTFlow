"""Simulateur mock + cron poll_pending_payments (docs/payments.md §2.1 §5, plan D3 Task 4)."""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.commerce.models import Order, Payment
from apps.conftest import make_order, make_pending
from apps.payments import gateway
from apps.payments.models import PaymentEvent

SIMULATE = "/api/v1/payments/dev/simulate/"
POLL = "poll_pending_payments"


@pytest.fixture
def client():
    return APIClient()


def pending_payment(user, artwork_factory, *, title="Simulé", age=None):
    art = artwork_factory(title=title, price=25000, stock=5)
    payment = make_pending(make_order(user, art, quantity=2))
    if age is not None:
        Payment.objects.filter(pk=payment.pk).update(
            initiated_at=timezone.now() - age
        )
        payment.refresh_from_db()
    return payment


def simulate(client, payment, scenario, *, as_user=None):
    if as_user is not None:
        client.force_login(as_user)
    return client.post(
        SIMULATE,
        {"external_reference": payment.external_reference, "scenario": scenario},
        format="json",
    )


def run_poll() -> str:
    out = StringIO()
    call_command(POLL, stdout=out)
    return out.getvalue().strip()


class TestScenarios:
    def test_success_delivers_and_pays(self, db, user, artwork_factory, client):
        payment = pending_payment(user, artwork_factory)

        resp = simulate(client, payment, "success", as_user=user)

        assert resp.status_code == 200
        assert resp.json() == {"delivered": 1}
        payment.refresh_from_db()
        payment.order.refresh_from_db()
        artwork = payment.order.items.get().artwork
        artwork.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED
        assert payment.order.status == Order.Status.PAID
        assert artwork.stock_quantity == 3
        event = PaymentEvent.objects.get(payment=payment)
        assert event.event_id == f"mock:{payment.provider_reference}:SUCCESSFUL"

    def test_fail_cancels_and_keeps_stock(self, db, user, artwork_factory, client):
        payment = pending_payment(user, artwork_factory)

        resp = simulate(client, payment, "fail", as_user=user)

        assert resp.status_code == 200
        assert resp.json() == {"delivered": 1}
        payment.refresh_from_db()
        payment.order.refresh_from_db()
        artwork = payment.order.items.get().artwork
        artwork.refresh_from_db()
        assert payment.status == Payment.Status.FAILED
        assert payment.order.status == Order.Status.CANCELLED
        assert artwork.stock_quantity == 5

    def test_timeout_delivers_nothing(self, db, user, artwork_factory, client):
        payment = pending_payment(user, artwork_factory)

        resp = simulate(client, payment, "timeout", as_user=user)

        assert resp.status_code == 200
        assert resp.json() == {"delivered": 0}
        payment.refresh_from_db()
        assert payment.status == Payment.Status.PENDING
        assert not PaymentEvent.objects.exists()

    def test_webhook_lost_then_late_poll_reconciles(
        self, db, user, artwork_factory, client
    ):
        payment = pending_payment(user, artwork_factory, age=timedelta(seconds=120))

        resp = simulate(client, payment, "webhook_lost_then_late", as_user=user)
        assert resp.status_code == 200
        assert resp.json() == {"delivered": 0}
        payment.refresh_from_db()
        assert payment.status == Payment.Status.PENDING  # rien de livré
        assert payment.raw_last_status["simulated_status"] == "SUCCESSFUL"
        assert not PaymentEvent.objects.exists()

        assert run_poll() == "1 paiement(s) réconcilié(s)."

        payment.refresh_from_db()
        payment.order.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED
        assert payment.order.status == Order.Status.PAID
        assert PaymentEvent.objects.get(payment=payment).kind == (
            PaymentEvent.Kind.STATUS_POLL
        )

    def test_duplicate_webhook_decrements_once(self, db, user, artwork_factory, client):
        payment = pending_payment(user, artwork_factory)

        resp = simulate(client, payment, "duplicate_webhook", as_user=user)

        assert resp.status_code == 200
        assert resp.json() == {"delivered": 2, "duplicates": 1}
        payment.refresh_from_db()
        payment.order.refresh_from_db()
        artwork = payment.order.items.get().artwork
        artwork.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED
        assert artwork.stock_quantity == 3  # un seul décrément
        assert PaymentEvent.objects.filter(payment=payment).count() == 1


class TestSimulateErrors:
    def test_not_owner_404(self, db, user, artwork_factory, client, user_factory):
        payment = pending_payment(user, artwork_factory)
        resp = simulate(client, payment, "success", as_user=user_factory())
        assert resp.status_code == 404

    def test_not_pending_409(self, db, user, artwork_factory, client):
        art = artwork_factory(title="Créé", price=10000, stock=2)
        payment = make_order(user, art).payments.get()  # CREATED

        resp = simulate(client, payment, "success", as_user=user)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "conflict"

    def test_unknown_reference_404(self, db, user, client):
        client.force_login(user)
        resp = client.post(
            SIMULATE,
            {"external_reference": "inconnu", "scenario": "success"},
            format="json",
        )
        assert resp.status_code == 404

    def test_invalid_scenario_400(self, db, user, artwork_factory, client):
        payment = pending_payment(user, artwork_factory)
        resp = simulate(client, payment, "chaos", as_user=user)
        assert resp.status_code == 400

    def test_anonymous_401(self, db, artwork_factory, user, client):
        payment = pending_payment(user, artwork_factory)
        resp = simulate(client, payment, "success")  # pas de force_login
        assert resp.status_code == 401

    def test_disabled_off_mock_404(self, db, user, artwork_factory, client):
        payment = pending_payment(user, artwork_factory)
        with override_settings(PAYMENT_PROVIDER="campay"):
            resp = simulate(client, payment, "success", as_user=user)
        assert resp.status_code == 404


class TestPollCommand:
    def test_poll_increments_without_status(self, db, user, artwork_factory):
        payment = pending_payment(user, artwork_factory, age=timedelta(seconds=120))

        assert run_poll() == "0 paiement(s) réconcilié(s)."

        payment.refresh_from_db()
        assert payment.status == Payment.Status.PENDING
        assert payment.poll_count == 1

    def test_poll_skips_recent_initiations(self, db, user, artwork_factory):
        payment = pending_payment(user, artwork_factory, age=timedelta(seconds=30))

        run_poll()

        payment.refresh_from_db()
        assert payment.poll_count == 0

    def test_poll_stops_after_max_attempts(
        self, db, user, artwork_factory, monkeypatch
    ):
        payment = pending_payment(user, artwork_factory, age=timedelta(seconds=120))
        Payment.objects.filter(pk=payment.pk).update(poll_count=20)
        called: list[int] = []

        original = gateway.MockPaymentGateway.get_status
        monkeypatch.setattr(
            gateway.MockPaymentGateway,
            "get_status",
            lambda self, p: called.append(p.pk) or original(self, p),
        )

        assert run_poll() == "0 paiement(s) réconcilié(s)."
        assert called == []  # poll_count >= 20 → jamais interrogé
