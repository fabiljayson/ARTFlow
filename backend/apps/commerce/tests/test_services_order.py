"""OrderService.mark_paid — conversion réservations + ledger idempotent (plan D2 Task 4)."""
import pytest
from rest_framework.exceptions import APIException

from apps.commerce.models import CommissionLedger, Order, StockReservation
from apps.commerce.services import mark_paid
from apps.commerce.tests.conftest import make_order


@pytest.mark.django_db
class TestMarkPaid:
    def test_mark_paid_happy_path(self, user, artwork_factory):
        art = artwork_factory(title="Payée", price=30000, stock=5)
        order = make_order(user, art, quantity=2)
        assert art.stock_quantity == 5

        mark_paid(order)

        order.refresh_from_db()
        art.refresh_from_db()
        assert order.status == Order.Status.PAID
        assert order.paid_at is not None
        assert art.stock_quantity == 3  # 5 − 2, décrémenté au paiement
        reservation = order.reservations.get()
        assert reservation.status == StockReservation.Status.CONVERTED
        entry = CommissionLedger.objects.get()
        item = order.items.get()
        assert entry.order_item == item
        assert entry.kind == CommissionLedger.Kind.CHARGE
        assert entry.gross_xaf == 60000
        assert entry.commission_xaf == 6000
        assert entry.artist_net_xaf == 54000
        assert entry.commission_rate_bps == 1000

    def test_mark_paid_idempotent(self, user, artwork_factory):
        art = artwork_factory(price=30000, stock=5)
        order = make_order(user, art, quantity=2)

        mark_paid(order)
        mark_paid(order)  # rejeu webhook en D3

        art.refresh_from_db()
        assert art.stock_quantity == 3  # décrémenté une seule fois (5 − 2)
        assert CommissionLedger.objects.filter(order_item__order=order).count() == 1
        order.refresh_from_db()
        assert order.status == Order.Status.PAID

    def test_mark_paid_never_negative_stock(self, user, artwork_factory):
        art = artwork_factory(price=10000, stock=1)
        order = make_order(user, art, quantity=2)  # réservé qty 2, stock réduit à 1 entre-temps
        art.stock_quantity = 0
        art.save()

        with pytest.raises(APIException):
            mark_paid(order)

        art.refresh_from_db()
        assert art.stock_quantity == 0  # aucun décrément partiel
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING_PAYMENT
        assert not CommissionLedger.objects.filter(order_item__order=order).exists()
