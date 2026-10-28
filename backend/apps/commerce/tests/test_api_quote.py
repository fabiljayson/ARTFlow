"""Checkout quote API — POST /checkout/quote/ (docs/api.md §6, plan D2 Task 2)."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.artists.models import ApplicationStatus, ArtistProfile
from apps.catalogue.models import Artwork, ArtworkStatus
from apps.conftest import add_item

QUOTE = "/api/v1/checkout/quote/"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def second_seller(user_factory, db):
    profile = ArtistProfile.objects.create(
        user=user_factory(),
        display_name="Kouamé Sculpteur",
        city="Douala",
        status=ApplicationStatus.APPROVED,
        shipping_base_fee_xaf=3500,
    )
    return profile


def make_artwork(artist, category, *, title, price, stock, status=ArtworkStatus.PUBLISHED):
    return Artwork.objects.create(
        artist=artist,
        category=category,
        title=title,
        description="Une œuvre de démonstration.",
        price_xaf=price,
        stock_quantity=stock,
        status=status,
    )


@pytest.mark.django_db
class TestCheckoutQuote:
    def test_unauthenticated_401(self, client):
        assert client.post(QUOTE, {}, format="json").status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_cart_returns_zeros(self, client, user, cart):
        client.force_login(user)
        data = client.post(QUOTE, {}, format="json").json()
        assert data["items"] == []
        assert data["shipping"] == []
        assert data["subtotal_items_xaf"] == 0
        assert data["shipping_total_xaf"] == 0
        assert data["fees_total_xaf"] == 0
        assert data["grand_total_xaf"] == 0
        assert data["items_count"] == 0
        assert data["blocking_issues"] == []

    def test_multi_seller_totals(
        self, client, user, cart, artwork_factory, second_seller, category, seller_profile
    ):
        client.force_login(user)
        seller_profile.shipping_base_fee_xaf = 2000
        seller_profile.save()
        painting = artwork_factory(title="Peinture", price=15000, stock=2)
        sculpture = make_artwork(
            second_seller, category, title="Statuette", price=30000, stock=2
        )
        add_item(cart, painting, qty=1)
        add_item(cart, sculpture, qty=1)

        data = client.post(QUOTE, {}, format="json").json()

        assert data["subtotal_items_xaf"] == 45000
        assert len(data["shipping"]) == 2  # un frais par vendeur distinct
        assert data["shipping_total_xaf"] == 2000 + 3500
        assert data["fees_total_xaf"] == 0
        assert data["grand_total_xaf"] == 45000 + 5500
        assert data["items_count"] == 2
        fees_by_artist = {s["artist_id"]: s["shipping_fee_xaf"] for s in data["shipping"]}
        assert fees_by_artist[seller_profile.pk] == 2000
        assert fees_by_artist[second_seller.pk] == 3500
        # commission figée dans la simulation : 10 %
        line = next(i for i in data["items"] if i["title"] == "Peinture")
        assert line["commission_rate_bps"] == 1000
        assert line["commission_xaf"] == 1500
        assert line["artist_net_xaf"] == 13500
        assert line["artist"] == {"id": seller_profile.pk, "display_name": "Awa Ndiaye"}

    def test_one_shipping_fee_per_seller(self, client, user, cart, artwork_factory):
        client.force_login(user)
        art1 = artwork_factory(title="A", price=10000, stock=2)
        art2 = artwork_factory(title="B", price=5000, stock=2)
        add_item(cart, art1, qty=1)
        add_item(cart, art2, qty=1)

        data = client.post(QUOTE, {}, format="json").json()

        assert len(data["shipping"]) == 1  # même artiste → un seul frais
        assert data["subtotal_items_xaf"] == 15000
        assert data["grand_total_xaf"] == 15000  # frais par défaut 0

    def test_commission_floor(self, client, user, cart, artwork_factory):
        client.force_login(user)
        add_item(cart, artwork_factory(title="Petite", price=999, stock=1), qty=1)
        data = client.post(QUOTE, {}, format="json").json()
        line = data["items"][0]
        assert line["commission_xaf"] == 99  # floor(999 * 1000 / 10000) = 99
        assert line["artist_net_xaf"] == 900

    def test_client_prices_ignored(self, client, user, cart, artwork_factory):
        client.force_login(user)
        add_item(cart, artwork_factory(title="Vrai", price=15000, stock=2), qty=1)
        honest = client.post(QUOTE, {}, format="json").json()
        forged = client.post(
            QUOTE,
            {"grand_total_xaf": 1, "items": [{"artwork_id": 999, "unit_price_xaf": 1}]},
            format="json",
        ).json()
        assert forged == honest
        assert forged["grand_total_xaf"] == 15000

    def test_blocking_stock_issue(self, client, user, cart, artwork_factory):
        client.force_login(user)
        art = artwork_factory(title="Rare", price=15000, stock=3)
        add_item(cart, art, qty=3)
        art.stock_quantity = 1
        art.save()

        data = client.post(QUOTE, {}, format="json").json()

        issues = data["blocking_issues"]
        assert len(issues) == 1
        assert issues[0]["artwork_id"] == art.pk
        assert issues[0]["code"] == "stock_insufficient"
        assert issues[0]["quantity_demandee"] == 3
        assert "Stock" in issues[0]["message"]
        assert data["grand_total_xaf"] == 45000  # totaux restent affichés

    def test_blocking_unavailable_issue(self, client, user, cart, artwork_factory):
        client.force_login(user)
        art = artwork_factory(title="Cachée", price=8000, stock=2)
        add_item(cart, art, qty=1)
        art.status = ArtworkStatus.HIDDEN
        art.save()

        data = client.post(QUOTE, {}, format="json").json()

        issues = data["blocking_issues"]
        assert len(issues) == 1
        assert issues[0]["code"] == "artwork_unavailable"
        assert issues[0]["artwork_id"] == art.pk
