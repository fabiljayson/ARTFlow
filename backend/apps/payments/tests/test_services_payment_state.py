"""Payment state machine tests — apply_status + ingest_event (docs/payments.md §2)."""
import logging

import pytest
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.commerce.models import CommissionLedger, Order, Payment, StockReservation
from apps.conftest import make_order, make_pending
from apps.core.exceptions import Conflict
from apps.payments import services as payment_services
from apps.payments.models import PaymentEvent


def ingest(
    payment,
    *,
    event_id,
    status="SUCCESSFUL",
    amount_xaf=None,
    source="WEBHOOK",
    failure_reason=None,
):
    amount = payment.amount_xaf if amount_xaf is None else amount_xaf
    payload = {
        "event_id": event_id,
        "external_reference": payment.external_reference,
        "status": status,
        "amount_xaf": amount,
    }
    if failure_reason:
        payload["failure_reason"] = failure_reason
    return payment_services.ingest_event(
        event_id=event_id,
        external_reference=payment.external_reference,
        status=status,
        amount_xaf=amount,
        payload=payload,
        source=source,
    )


class TestIngestSucceeded:
    def test_succeeded_marks_order_paid_with_ledger(self, db, user, artwork_factory):
        art = artwork_factory(title="Payée", price=25000, stock=5)
        payment = make_pending(make_order(user, art, quantity=2))
        order = payment.order

        result = ingest(payment, event_id="evt-ok-1")

        order.refresh_from_db()
        art.refresh_from_db()
        assert result["payment_status"] == Payment.Status.SUCCEEDED
        assert result["order_status"] == Order.Status.PAID
        assert result["duplicate"] is False
        assert order.status == Order.Status.PAID and order.paid_at is not None
        assert art.stock_quantity == 3  # 5 − 2, décrément unique
        assert CommissionLedger.objects.filter(
            order_item__order=order, kind=CommissionLedger.Kind.CHARGE
        ).count() == 1
        event = PaymentEvent.objects.get(event_id="evt-ok-1")
        assert event.kind == PaymentEvent.Kind.WEBHOOK_RECEIVED
        assert event.signature_valid is True
        assert event.status_after == Payment.Status.SUCCEEDED

    def test_duplicate_event_id_noop(self, db, user, artwork_factory):
        art = artwork_factory(title="Rejeu", price=25000, stock=5)
        payment = make_pending(make_order(user, art, quantity=2))

        first = ingest(payment, event_id="evt-dup")
        second = ingest(payment, event_id="evt-dup")

        art.refresh_from_db()
        assert first["duplicate"] is False
        assert second["duplicate"] is True
        assert art.stock_quantity == 3  # un seul décrément
        assert PaymentEvent.objects.filter(event_id="evt-dup").count() == 1

    def test_amount_mismatch_rejected(self, db, user, artwork_factory, caplog):
        art = artwork_factory(title="Mauvais montant", price=25000, stock=5)
        payment = make_pending(make_order(user, art, quantity=2))

        with caplog.at_level(logging.WARNING), pytest.raises(Conflict) as exc:
            ingest(payment, event_id="evt-amount", amount_xaf=1)

        assert "montant" in str(exc.value).lower()
        payment.refresh_from_db()
        art.refresh_from_db()
        assert payment.status == Payment.Status.PENDING
        assert art.stock_quantity == 5
        assert not PaymentEvent.objects.filter(event_id="evt-amount").exists()
        assert any("Montant" in r.message for r in caplog.records)

    def test_illegal_transition_rejected(self, db, user, artwork_factory):
        art = artwork_factory(title="Contredit", price=25000, stock=5)
        payment = make_pending(make_order(user, art, quantity=2))
        ingest(payment, event_id="evt-paid")

        with pytest.raises(Conflict):
            ingest(payment, event_id="evt-then-failed", status="FAILED")

        payment.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED
        assert PaymentEvent.objects.filter(payment=payment).count() == 1

    def test_same_status_re_receipt_is_noop(self, db, user, artwork_factory):
        art = artwork_factory(title="Doublon", price=25000, stock=5)
        payment = make_pending(make_order(user, art, quantity=2))
        ingest(payment, event_id="evt-a")

        result = ingest(payment, event_id="evt-b")  # même SUCCESSFUL, autre event_id

        art.refresh_from_db()
        assert result["payment_status"] == Payment.Status.SUCCEEDED
        assert art.stock_quantity == 3  # pas de second décrément
        assert PaymentEvent.objects.filter(payment=payment).count() == 2


class TestIngestFailed:
    def test_failed_releases_stock_and_cancels_order(self, db, user, artwork_factory):
        art = artwork_factory(title="Échec", price=25000, stock=5)
        payment = make_pending(make_order(user, art, quantity=2))
        order = payment.order

        result = ingest(
            payment, event_id="evt-fail", status="FAILED", failure_reason="Échec opérateur"
        )

        order.refresh_from_db()
        art.refresh_from_db()
        assert result["payment_status"] == Payment.Status.FAILED
        assert result["order_status"] == Order.Status.CANCELLED
        assert order.status == Order.Status.CANCELLED and order.cancelled_at
        payment = order.payments.get()
        assert payment.status == Payment.Status.FAILED
        assert payment.failure_reason == "Échec opérateur"
        reservation = order.reservations.get()
        assert reservation.status == StockReservation.Status.RELEASED
        assert reservation.released_at is not None
        assert art.stock_quantity == 5  # jamais décrémenté

    def test_failed_on_cancelled_order_is_harmless(self, db, user, artwork_factory):
        art = artwork_factory(title="Déjà annulée", price=25000, stock=5)
        payment = make_pending(make_order(user, art, quantity=2))
        order = payment.order
        order.status = Order.Status.CANCELLED
        order.cancelled_at = timezone.now()
        order.save(update_fields=["status", "cancelled_at", "updated_at"])

        result = ingest(payment, event_id="evt-fail2", status="FAILED")

        order.refresh_from_db()
        assert result["order_status"] == Order.Status.CANCELLED
        assert order.status == Order.Status.CANCELLED


class TestLateSuccess:
    def _cancel(self, order):
        order.status = Order.Status.CANCELLED
        order.cancelled_at = timezone.now()
        order.save(update_fields=["status", "cancelled_at", "updated_at"])
        order.reservations.filter(status=StockReservation.Status.ACTIVE).update(
            status=StockReservation.Status.RELEASED, released_at=timezone.now()
        )

    def test_late_success_after_cancel_accepts_payment(self, db, user, artwork_factory):
        art = artwork_factory(title="Tardif", price=25000, stock=5)
        payment = make_pending(make_order(user, art, quantity=2))
        order = payment.order
        self._cancel(order)

        result = ingest(payment, event_id="evt-late")

        order.refresh_from_db()
        art.refresh_from_db()
        assert order.status == Order.Status.PAID
        assert art.stock_quantity == 3
        assert result["order_status"] == Order.Status.PAID

    def test_late_success_clamps_stock_and_alerts_finance(
        self, db, user, artwork_factory, caplog
    ):
        art = artwork_factory(title="Stock épuisé", price=25000, stock=1)
        payment = make_pending(make_order(user, art, quantity=2))
        order = payment.order
        self._cancel(order)

        with caplog.at_level(logging.WARNING):
            ingest(payment, event_id="evt-late-clamp")

        art.refresh_from_db()
        assert art.stock_quantity == 0  # jamais négatif
        assert any("finance" in r.message for r in caplog.records)


class TestIngestEdge:
    def test_unknown_reference_404(self, db):
        with pytest.raises(Http404):
            payment_services.ingest_event(
                event_id="evt-x",
                external_reference="inconnu",
                status="SUCCESSFUL",
                amount_xaf=1000,
                payload={},
            )

    def test_unknown_provider_status_is_validation_error(self, db, user, artwork_factory):
        art = artwork_factory(title="Statut étrange", price=10000, stock=3)
        payment = make_pending(make_order(user, art))
        with pytest.raises(ValidationError):
            payment_services.ingest_event(
                event_id="evt-weird",
                external_reference=payment.external_reference,
                status="WEIRD",
                amount_xaf=payment.amount_xaf,
                payload={},
            )
