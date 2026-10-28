"""Checkout API — POST /checkout/ (docs/api.md §6, plan D2 Task 3)."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Address
from apps.catalogue.models import ArtworkStatus
from apps.commerce.models import Order, Payment, StockReservation
from apps.conftest import add_item

CHECKOUT = "/api/v1/checkout/"

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def address(user, db):
    return Address.objects.create(
        user=user,
        label="Maison",
        recipient_name="Jean Kamga",
        line1="Rue 1.23, quartier Bastos",
        city="Yaoundé",
        region="Centre",
        phone="+237690000001",
    )


def post_checkout(client, body, key="idem-key-1"):
    return client.post(CHECKOUT, body, format="json", HTTP_IDEMPOTENCY_KEY=key)


@pytest.mark.django_db
class TestCheckout:
    def test_unauthenticated_401(self, client):
        resp = client.post(CHECKOUT, {"address_id": 1}, format="json", HTTP_IDEMPOTENCY_KEY="k")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_idempotency_key_400(self, client, user, address):
        client.force_login(user)
        resp = client.post(CHECKOUT, {"address_id": address.pk}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        error = resp.json()["error"]
        assert error["code"] == "validation_error"
        assert "idempotency_key" in error["details"]

    def test_checkout_creates_order(self, client, user, cart, artwork_factory, address):
        client.force_login(user)
        art = artwork_factory(title="Lagune", price=15000, stock=5)
        add_item(cart, art, qty=2)

        resp = post_checkout(client, {"address_id": address.pk, "buyer_note": "Fragile"})

        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        import re

        assert re.fullmatch(r"ORD-\d{4}-\d{6}", data["order_reference"])
        assert data["status"] == "PENDING_PAYMENT"
        assert data["grand_total_xaf"] == 30000
        assert data["payment"] == {"provider": "MOCK", "status": "CREATED", "redirect_info": None}

        order = Order.objects.get(reference=data["order_reference"])
        assert order.buyer == user
        assert order.buyer_note == "Fragile"
        assert order.shipping_address_snapshot["city"] == "Yaoundé"
        assert order.shipping_address_snapshot["recipient_name"] == "Jean Kamga"
        assert order.idempotency_key == "idem-key-1"
        assert len(order.request_fingerprint) == 64

        item = order.items.get()
        assert item.title_snapshot == "Lagune"
        assert item.unit_price_xaf == 15000
        assert item.quantity == 2
        assert item.commission_rate_bps == 1000
        assert item.commission_xaf == 3000  # floor(30000 * 10 %)
        assert item.artist_net_xaf == 27000

        reservation = order.reservations.get()
        assert reservation.status == StockReservation.Status.ACTIVE
        assert reservation.quantity == 2
        now = timezone.now()
        assert now + timedelta(minutes=28) <= reservation.expires_at <= now + timedelta(minutes=32)

        payment = order.payments.get()
        assert payment.provider == Payment.Provider.MOCK
        assert payment.status == Payment.Status.CREATED
        assert payment.amount_xaf == 30000

        # Panier vidé dans la même transaction
        assert not cart.items.exists()

    def test_replay_returns_same_order(self, client, user, cart, artwork_factory, address):
        client.force_login(user)
        add_item(cart, artwork_factory(price=10000, stock=3), qty=1)
        body = {"address_id": address.pk}

        first = post_checkout(client, body, key="replay-key")
        second = post_checkout(client, body, key="replay-key")

        assert first.status_code == status.HTTP_201_CREATED
        assert second.status_code == status.HTTP_200_OK
        assert second.json()["order_reference"] == first.json()["order_reference"]
        assert Order.objects.filter(buyer=user).count() == 1
        assert StockReservation.objects.filter(order__buyer=user).count() == 1

    def test_same_key_different_body_409(self, client, user, cart, artwork_factory, address):
        client.force_login(user)
        add_item(cart, artwork_factory(price=10000, stock=3), qty=1)
        first = post_checkout(
            client, {"address_id": address.pk, "buyer_note": "A"}, key="body-key"
        )
        assert first.status_code == status.HTTP_201_CREATED

        second = post_checkout(
            client, {"address_id": address.pk, "buyer_note": "B"}, key="body-key"
        )
        assert second.status_code == status.HTTP_409_CONFLICT
        assert second.json()["error"]["code"] == "idempotency_conflict"

    def test_key_of_another_user_409(self, client, user, cart, artwork_factory, address, other_user):
        Order.objects.create(
            buyer=other_user,
            reference="ORD-2026-999998",
            idempotency_key="shared-key",
            request_fingerprint="f" * 64,
        )
        client.force_login(user)
        add_item(cart, artwork_factory(price=10000, stock=3), qty=1)

        resp = post_checkout(client, {"address_id": address.pk}, key="shared-key")
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.json()["error"]["code"] == "idempotency_conflict"
        assert Order.objects.filter(buyer=user).count() == 0

    def test_foreign_address_404(self, client, user, cart, artwork_factory, other_user, db):
        foreign = Address.objects.create(
            user=other_user,
            label="Chez lui",
            recipient_name="Autre",
            line1="Rue 9",
            city="Douala",
            phone="+237690000002",
        )
        client.force_login(user)
        add_item(cart, artwork_factory(price=10000, stock=3), qty=1)
        resp = post_checkout(client, {"address_id": foreign.pk}, key="foreign-addr")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_missing_address_400(self, client, user, cart, artwork_factory):
        client.force_login(user)
        add_item(cart, artwork_factory(price=10000, stock=3), qty=1)
        resp = post_checkout(client, {}, key="no-addr")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "address_id" in resp.json()["error"]["details"]

    def test_empty_cart_400(self, client, user, address):
        client.force_login(user)
        resp = post_checkout(client, {"address_id": address.pk}, key="empty-cart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "cart" in resp.json()["error"]["details"]

    def test_stale_stock_400(self, client, user, cart, artwork_factory, address):
        client.force_login(user)
        art = artwork_factory(price=15000, stock=3)
        add_item(cart, art, qty=3)
        art.stock_quantity = 1
        art.save()

        resp = post_checkout(client, {"address_id": address.pk}, key="stale-stock")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        issues = resp.json()["error"]["details"]["items"]
        # DRF coerce les ids des messages d'erreur en chaînes — le front les reconvertit.
        assert int(issues[0]["artwork_id"]) == art.pk
        assert issues[0]["code"] == "stock_insufficient"
        assert Order.objects.count() == 0

    def test_unpublished_artwork_400(self, client, user, cart, artwork_factory, address):
        client.force_login(user)
        art = artwork_factory(price=15000, stock=3)
        add_item(cart, art, qty=1)
        art.status = ArtworkStatus.HIDDEN
        art.save()

        resp = post_checkout(client, {"address_id": address.pk}, key="unpublished")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        issues = resp.json()["error"]["details"]["items"]
        assert issues[0]["code"] == "artwork_unavailable"
        assert Order.objects.count() == 0

    def test_commission_frozen_from_settings(
        self, client, user, cart, artwork_factory, address
    ):
        from apps.core.models import PlatformSettings

        client.force_login(user)
        add_item(cart, artwork_factory(price=10000, stock=3), qty=1)
        resp = post_checkout(client, {"address_id": address.pk}, key="frozen-bps")
        assert resp.status_code == status.HTTP_201_CREATED

        settings = PlatformSettings.get()
        settings.commission_rate_bps = 2000
        settings.save()

        item = Order.objects.get(reference=resp.json()["order_reference"]).items.get()
        assert item.commission_rate_bps == 1000  # jamais relu
        assert item.commission_xaf == 1000

    def test_throttle_checkout(self, client, user):
        client.force_login(user)
        codes = [
            client.post(CHECKOUT, {}, format="json", HTTP_IDEMPOTENCY_KEY=f"t{i}").status_code
            for i in range(21)
        ]
        assert codes[:20] != [status.HTTP_429_TOO_MANY_REQUESTS] * 20
        assert all(code != status.HTTP_429_TOO_MANY_REQUESTS for code in codes[:20])
        assert codes[20] == status.HTTP_429_TOO_MANY_REQUESTS
        resp = client.post(CHECKOUT, {}, format="json", HTTP_IDEMPOTENCY_KEY="t22")
        assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert resp.json()["error"]["code"] == "rate_limited"
