"""Orders API — /orders/ (docs/api.md §6, plan D2 Task 4)."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.commerce.models import Order, StockReservation
from apps.conftest import make_order

ORDERS = "/api/v1/orders/"


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestOrderList:
    def test_unauthenticated_401(self, client):
        assert client.get(ORDERS).status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_scoped_to_buyer(self, client, user, other_user, artwork_factory):
        client.force_login(user)
        mine = make_order(user, artwork_factory(title="La mienne", price=10000, stock=2))
        make_order(other_user, artwork_factory(title="La sienne", price=20000, stock=2))

        data = client.get(ORDERS).json()

        assert data["count"] == 1
        row = data["results"][0]
        assert row["reference"] == mine.reference
        assert row["status"] == "PENDING_PAYMENT"
        assert row["grand_total_xaf"] == 10000
        assert row["items_count"] == 1
        for key in ("placed_at", "paid_at", "subtotal_items_xaf", "shipping_total_xaf"):
            assert key in row


@pytest.mark.django_db
class TestOrderDetail:
    def test_unauthenticated_401(self, client):
        assert client.get(f"{ORDERS}ORD-X/").status_code == status.HTTP_401_UNAUTHORIZED

    def test_detail_shape_and_frozen_price(self, client, user, artwork_factory):
        client.force_login(user)
        art = artwork_factory(title="Instantané", price=15000, stock=3)
        order = make_order(user, art, quantity=2)

        art.price_xaf = 99000  # le prix bouge après achat
        art.save()

        data = client.get(f"{ORDERS}{order.reference}/").json()
        assert data["reference"] == order.reference
        assert data["status"] == "PENDING_PAYMENT"
        assert data["subtotal_items_xaf"] == 30000
        assert data["shipping_address_snapshot"]["city"] == "Yaoundé"
        assert data["buyer_note"] == ""
        assert data["payment"] == {
            "provider": "MOCK",
            "status": "CREATED",
            "external_reference": order.payments.get().external_reference,
            "failure_reason": "",
        }
        assert data["shipments"] == []
        assert data["disputes"] == []

        item = data["items"][0]
        assert item["title_snapshot"] == "Instantané"
        assert item["unit_price_xaf"] == 15000  # figé, pas 99000
        assert item["quantity"] == 2
        assert item["line_total_xaf"] == 30000
        assert item["commission_rate_bps"] == 1000
        assert item["commission_xaf"] == 3000
        assert item["artist_net_xaf"] == 27000
        assert item["artist"]["display_name"] == "Awa Ndiaye"

    def test_detail_other_buyer_404(self, client, user, other_user, artwork_factory):
        foreign = make_order(other_user, artwork_factory(price=10000, stock=2))
        client.force_login(user)
        assert (
            client.get(f"{ORDERS}{foreign.reference}/").status_code
            == status.HTTP_404_NOT_FOUND
        )

    def test_detail_unknown_404(self, client, user):
        client.force_login(user)
        assert (
            client.get(f"{ORDERS}ORD-2026-000000/").status_code
            == status.HTTP_404_NOT_FOUND
        )


@pytest.mark.django_db
class TestOrderCancel:
    def test_unauthenticated_401(self, client):
        assert (
            client.post(f"{ORDERS}ORD-X/cancel/").status_code
            == status.HTTP_401_UNAUTHORIZED
        )

    def test_cancel_pending_releases_everything(self, client, user, artwork_factory):
        client.force_login(user)
        order = make_order(user, artwork_factory(price=10000, stock=2))

        resp = client.post(f"{ORDERS}{order.reference}/cancel/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "CANCELLED"
        order.refresh_from_db()
        assert order.cancelled_at is not None
        reservation = order.reservations.get()
        assert reservation.status == StockReservation.Status.RELEASED
        assert reservation.released_at is not None
        assert order.payments.get().status == "CANCELLED"

    def test_cancel_twice_second_409(self, client, user, artwork_factory):
        client.force_login(user)
        order = make_order(user, artwork_factory(price=10000, stock=2))
        first = client.post(f"{ORDERS}{order.reference}/cancel/")
        second = client.post(f"{ORDERS}{order.reference}/cancel/")
        assert first.status_code == status.HTTP_200_OK
        assert second.status_code == status.HTTP_409_CONFLICT
        assert second.json()["error"]["code"] == "conflict"

    def test_cancel_paid_409(self, client, user, artwork_factory):
        client.force_login(user)
        order = make_order(user, artwork_factory(price=10000, stock=2), status=Order.Status.PAID)

        resp = client.post(f"{ORDERS}{order.reference}/cancel/")
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.json()["error"]["code"] == "conflict"

    def test_cancel_other_order_404(self, client, user, other_user, artwork_factory):
        foreign = make_order(other_user, artwork_factory(price=10000, stock=2))
        client.force_login(user)
        resp = client.post(f"{ORDERS}{foreign.reference}/cancel/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        foreign.refresh_from_db()
        assert foreign.status == Order.Status.PENDING_PAYMENT
