"""Buyer cart API — GET /cart/ (docs/api.md §6, screens.md /panier)."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalogue.models import ArtworkStatus
from apps.commerce.models import Cart
from apps.commerce.tests.conftest import add_item

CART = "/api/v1/cart/"
ITEMS = "/api/v1/cart/items/"


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestCartGet:
    def test_unauthenticated_401(self, client):
        assert client.get(CART).status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_cart(self, client, user):
        client.force_login(user)
        resp = client.get(CART)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["items"] == []
        assert data["items_count"] == 0
        assert data["items_total_xaf"] == 0

    def test_totals_and_line_shape(self, client, user, cart, artwork_factory):
        client.force_login(user)
        cheap = artwork_factory(title="Petit portrait", price=15000, stock=3)
        rich = artwork_factory(title="Grand format", price=30000, stock=2)
        add_item(cart, cheap, qty=1)
        add_item(cart, rich, qty=2)
        data = client.get(CART).json()
        assert data["items_count"] == 3  # total units: 1 + 2
        assert data["items_total_xaf"] == 75000
        by_title = {i["artwork"]["title"]: i for i in data["items"]}
        line = by_title["Grand format"]
        assert line["quantity"] == 2
        assert line["line_total_xaf"] == 60000
        assert line["artwork"]["price_xaf"] == 30000
        assert line["artwork"]["slug"] == rich.slug
        assert line["artwork"]["stock_quantity"] == 2
        assert line["artwork"]["is_available"] is True
        assert line["artwork"]["artist_display_name"] == "Awa Ndiaye"
        assert line["quantity_exceeds_stock"] is False
        assert line["artwork_unavailable"] is False

    def test_price_reloaded_not_stored(self, client, user, cart, artwork_factory):
        client.force_login(user)
        art = artwork_factory(price=15000)
        add_item(cart, art, qty=1)
        art.price_xaf = 22000
        art.save()
        data = client.get(CART).json()
        assert data["items"][0]["artwork"]["price_xaf"] == 22000
        assert data["items"][0]["line_total_xaf"] == 22000

    def test_flags_after_stock_drop(self, client, user, cart, artwork_factory):
        client.force_login(user)
        art = artwork_factory(stock=2)
        add_item(cart, art, qty=2)
        art.stock_quantity = 1
        art.save()
        data = client.get(CART).json()
        assert data["items"][0]["quantity_exceeds_stock"] is True
        art.status = ArtworkStatus.HIDDEN
        art.save()
        data = client.get(CART).json()
        assert data["items"][0]["artwork_unavailable"] is True

    def test_cart_scoped_per_user(self, client, user, other_user, artwork_factory):
        other_cart = Cart.objects.create(user=other_user)
        add_item(other_cart, artwork_factory(), qty=1)
        client.force_login(user)
        data = client.get(CART).json()
        assert data["items"] == []
        assert data["items_count"] == 0


@pytest.mark.django_db
class TestCartAdd:
    def test_unauthenticated_401(self, client, artwork_factory):
        art = artwork_factory()
        assert client.post(ITEMS, {"artwork_id": art.pk, "quantity": 1}).status_code == status.HTTP_401_UNAUTHORIZED

    def test_add_creates_line(self, client, user, artwork_factory):
        client.force_login(user)
        art = artwork_factory(price=15000, stock=3)
        resp = client.post(ITEMS, {"artwork_id": art.pk, "quantity": 1}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["quantity"] == 1
        assert data["line_total_xaf"] == 15000
        assert data["artwork"]["id"] == art.pk
        assert Cart.objects.get(user=user).items.count() == 1

    def test_add_increments_existing(self, client, user, artwork_factory):
        client.force_login(user)
        art = artwork_factory(stock=5)
        client.post(ITEMS, {"artwork_id": art.pk, "quantity": 1}, format="json")
        resp = client.post(ITEMS, {"artwork_id": art.pk, "quantity": 1}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        cart = Cart.objects.get(user=user)
        assert cart.items.count() == 1
        assert cart.items.get().quantity == 2

    def test_add_caps_at_stock(self, client, user, artwork_factory):
        client.force_login(user)
        art = artwork_factory(stock=1)
        client.post(ITEMS, {"artwork_id": art.pk, "quantity": 1}, format="json")
        resp = client.post(ITEMS, {"artwork_id": art.pk, "quantity": 1}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["error"]["code"] == "validation_error"
        assert "quantity" in resp.json()["error"]["details"]

    def test_quantity_zero_or_negative_400(self, client, user, artwork_factory):
        client.force_login(user)
        art = artwork_factory()
        resp = client.post(ITEMS, {"artwork_id": art.pk, "quantity": 0}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        resp = client.post(ITEMS, {"artwork_id": art.pk, "quantity": -2}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_over_stock_first_add_400(self, client, user, artwork_factory):
        client.force_login(user)
        art = artwork_factory(stock=2)
        resp = client.post(ITEMS, {"artwork_id": art.pk, "quantity": 5}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "quantity" in resp.json()["error"]["details"]

    def test_unknown_artwork_404(self, client, user):
        client.force_login(user)
        resp = client.post(ITEMS, {"artwork_id": 999999, "quantity": 1}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_draft_artwork_404(self, client, user, artwork_factory):
        client.force_login(user)
        art = artwork_factory(status=ArtworkStatus.DRAFT)
        resp = client.post(ITEMS, {"artwork_id": art.pk, "quantity": 1}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_out_of_stock_artwork_400(self, client, user, artwork_factory):
        client.force_login(user)
        art = artwork_factory(stock=0)
        resp = client.post(ITEMS, {"artwork_id": art.pk, "quantity": 1}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
