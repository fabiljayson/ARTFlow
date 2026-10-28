"""Order models constraints (docs/database.md §3: référence unique, commission figée, ledger append-only)."""
from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.commerce.models import (
    CommissionLedger,
    Order,
    OrderItem,
    Payment,
    StockReservation,
)


@pytest.fixture
def order(user, db):
    return Order.objects.create(
        buyer=user,
        reference="ORD-2026-000001",
        idempotency_key="key-000001",
        request_fingerprint="a" * 64,
        subtotal_items_xaf=30000,
        shipping_total_xaf=2000,
        grand_total_xaf=32000,
        shipping_address_snapshot={"city": "Yaoundé"},
    )


@pytest.fixture
def order_item(order, artwork_factory, seller_profile):
    return OrderItem.objects.create(
        order=order,
        artwork=artwork_factory(),
        artist=seller_profile,
        title_snapshot="Œuvre",
        unit_price_xaf=15000,
        quantity=2,
        line_total_xaf=30000,
        commission_rate_bps=1000,
        commission_xaf=3000,
        artist_net_xaf=27000,
    )


@pytest.mark.django_db
class TestOrderConstraints:
    def test_order_reference_unique(self, user, order):
        with pytest.raises(IntegrityError), transaction.atomic():
            Order.objects.create(
                buyer=user,
                reference=order.reference,
                idempotency_key="key-000002",
                request_fingerprint="b" * 64,
            )

    def test_order_idempotency_key_unique(self, user, order):
        with pytest.raises(IntegrityError), transaction.atomic():
            Order.objects.create(
                buyer=user,
                reference="ORD-2026-000002",
                idempotency_key=order.idempotency_key,
                request_fingerprint="b" * 64,
            )

    def test_order_default_status_pending(self, user):
        order = Order.objects.create(
            buyer=user,
            reference="ORD-2026-000003",
            idempotency_key="key-000003",
            request_fingerprint="c" * 64,
        )
        assert order.status == Order.Status.PENDING_PAYMENT
        assert order.currency == "XAF"
        assert order.placed_at is not None


@pytest.mark.django_db
class TestOrderItemConstraints:
    def test_order_item_quantity_positive(self, order, artwork_factory, seller_profile):
        with pytest.raises(IntegrityError), transaction.atomic():
            OrderItem.objects.create(
                order=order,
                artwork=artwork_factory(),
                artist=seller_profile,
                title_snapshot="Œuvre",
                unit_price_xaf=15000,
                quantity=0,
                line_total_xaf=0,
                commission_rate_bps=1000,
                commission_xaf=0,
                artist_net_xaf=0,
            )

    def test_order_item_commission_frozen_fields(self, order_item):
        assert order_item.commission_rate_bps == 1000
        assert order_item.commission_xaf == 3000
        assert order_item.artist_net_xaf == 27000
        assert order_item.line_total_xaf == order_item.commission_xaf + order_item.artist_net_xaf

    def test_order_item_unique_per_order_artwork(self, order_item):
        with pytest.raises(IntegrityError), transaction.atomic():
            OrderItem.objects.create(
                order=order_item.order,
                artwork=order_item.artwork,
                artist=order_item.artist,
                title_snapshot="Œuvre",
                unit_price_xaf=15000,
                quantity=1,
                line_total_xaf=15000,
                commission_rate_bps=1000,
                commission_xaf=1500,
                artist_net_xaf=13500,
            )


@pytest.mark.django_db
class TestStockReservation:
    def test_reservation_default_active(self, order, artwork_factory):
        reservation = StockReservation.objects.create(
            artwork=artwork_factory(),
            order=order,
            quantity=1,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        assert reservation.status == StockReservation.Status.ACTIVE
        assert reservation.released_at is None


@pytest.mark.django_db
class TestPayment:
    def test_payment_default_created(self, order):
        payment = Payment.objects.create(
            order=order, external_reference="ext-000001", amount_xaf=32000
        )
        assert payment.status == Payment.Status.CREATED
        assert payment.provider == Payment.Provider.MOCK

    def test_payment_external_reference_unique(self, order):
        Payment.objects.create(order=order, external_reference="ext-000001", amount_xaf=1)
        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.create(order=order, external_reference="ext-000001", amount_xaf=2)


@pytest.mark.django_db
class TestCommissionLedger:
    def test_ledger_unique_charge_per_order_item(self, order, order_item):
        CommissionLedger.objects.create(
            order_item=order_item,
            order=order,
            artist=order_item.artist,
            kind=CommissionLedger.Kind.CHARGE,
            gross_xaf=30000,
            commission_xaf=3000,
            artist_net_xaf=27000,
            commission_rate_bps=1000,
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            CommissionLedger.objects.create(
                order_item=order_item,
                order=order,
                artist=order_item.artist,
                kind=CommissionLedger.Kind.CHARGE,
                gross_xaf=30000,
                commission_xaf=3000,
                artist_net_xaf=27000,
                commission_rate_bps=1000,
            )

    def test_ledger_charge_plus_refund_adjustment_allowed(self, order, order_item):
        defaults = dict(
            order_item=order_item,
            order=order,
            artist=order_item.artist,
            gross_xaf=-30000,
            commission_xaf=-3000,
            artist_net_xaf=-27000,
            commission_rate_bps=1000,
        )
        CommissionLedger.objects.create(
            kind=CommissionLedger.Kind.CHARGE, gross_xaf=30000, commission_xaf=3000,
            artist_net_xaf=27000,
            order_item=order_item, order=order, artist=order_item.artist,
            commission_rate_bps=1000,
        )
        CommissionLedger.objects.create(kind=CommissionLedger.Kind.REFUND_ADJUSTMENT, **defaults)
        assert CommissionLedger.objects.filter(order_item=order_item).count() == 2
