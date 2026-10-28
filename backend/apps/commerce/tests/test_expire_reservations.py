"""Commande cron expire_stock_reservations (plan D2 Task 4, ADR-0005 : outbox + cron)."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.commerce.models import Order, StockReservation
from apps.conftest import make_order

EXPIRE = "expire_stock_reservations"


def make_expired_reservation(order):
    reservation = order.reservations.get()
    StockReservation.objects.filter(pk=reservation.pk).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )
    return reservation


@pytest.mark.django_db
class TestExpireReservations:
    def test_expire_cancels_unpaid_order(self, user, artwork_factory):
        art = artwork_factory(price=10000, stock=3)
        order = make_order(user, art, quantity=1)
        make_expired_reservation(order)

        call_command(EXPIRE)

        order.refresh_from_db()
        assert order.status == Order.Status.CANCELLED
        assert order.cancelled_at is not None
        reservation = order.reservations.get()
        assert reservation.status == StockReservation.Status.EXPIRED
        assert reservation.released_at is not None
        assert order.payments.get().status == "CANCELLED"
        # le stock n'a jamais été décrémenté : la réservation libère, pas de vente
        art.refresh_from_db()
        assert art.stock_quantity == 3

    def test_expire_releases_future_active_reservation_of_cancelled_siblings(self, user, artwork_factory):
        """Une commande expirée est annulée : ses autres réservations encore valables sont libérées."""
        art_a = artwork_factory(title="A", price=10000, stock=3)
        art_b = artwork_factory(title="B", price=5000, stock=3)
        order = make_order(user, art_a, quantity=1)
        # 2e ligne même commande via une 2e commande non expirée n'existe pas (unique art/commande) :
        # on simule en ajoutant une réservation ACTIVE non expirée sur une autre œuvre.
        from apps.commerce.models import StockReservation as SR

        SR.objects.create(
            artwork=art_b,
            order=order,
            quantity=1,
            expires_at=timezone.now() + timedelta(minutes=25),
        )
        order.reservations.filter(artwork=art_a).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )

        call_command(EXPIRE)

        order.refresh_from_db()
        assert order.status == Order.Status.CANCELLED
        statuses = set(order.reservations.values_list("status", flat=True))
        assert statuses == {StockReservation.Status.EXPIRED, StockReservation.Status.RELEASED}

    def test_expire_ignores_paid_order(self, user, artwork_factory):
        art = artwork_factory(price=10000, stock=5)
        order = make_order(user, art, quantity=1, status=Order.Status.PAID)
        make_expired_reservation(order)  # réservation convertie puis corrompue : ne rien faire

        call_command(EXPIRE)

        order.refresh_from_db()
        assert order.status == Order.Status.PAID
        art.refresh_from_db()
        assert art.stock_quantity == 5

    def test_expire_ignores_active_future(self, user, artwork_factory):
        art = artwork_factory(price=10000, stock=3)
        order = make_order(user, art, quantity=1)  # expires dans +30 min

        call_command(EXPIRE)

        order.refresh_from_db()
        assert order.status == Order.Status.PENDING_PAYMENT
        assert order.reservations.get().status == StockReservation.Status.ACTIVE
