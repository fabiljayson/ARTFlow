"""Fixtures for commerce tests — buyer owns `user`, artworks live on a separate artist."""
from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from apps.accounts.models import Role, UserRole
from apps.artists.models import ApplicationStatus, ArtistProfile
from apps.catalogue.models import Artwork, ArtworkStatus, Category
from apps.commerce.models import Cart, CartItem, Order, OrderItem, Payment, StockReservation
from apps.core.models import PlatformSettings


@pytest.fixture
def category(db):
    return Category.objects.create(slug="peinture", name_fr="Peinture")


@pytest.fixture
def seller_profile(other_user, db):
    """APPROVED artist on other_user — keeps `user` a plain buyer."""
    profile = ArtistProfile.objects.create(
        user=other_user, display_name="Awa Ndiaye", city="Yaoundé", status=ApplicationStatus.APPROVED
    )
    UserRole.objects.get_or_create(user=other_user, role=Role.ARTIST)
    return profile


@pytest.fixture
def artwork_factory(seller_profile, category):
    def _make(*, status=ArtworkStatus.PUBLISHED, title="Œuvre", price=15000, stock=2, **extra):
        return Artwork.objects.create(
            artist=seller_profile,
            category=category,
            title=title,
            description="Une belle œuvre de démonstration.",
            price_xaf=price,
            stock_quantity=stock,
            status=status,
            **extra,
        )

    return _make


@pytest.fixture
def cart(user, db):
    return Cart.objects.create(user=user)


def add_item(cart, artwork, qty=1):
    return CartItem.objects.create(cart=cart, artwork=artwork, quantity=qty)


def make_order(buyer, artwork, *, quantity=1, status=Order.Status.PENDING_PAYMENT,
               reservation_status=None):
    """Commande de test complète : ligne figée, réservation, payment MOCK."""
    now = timezone.now()
    bps = PlatformSettings.get().commission_rate_bps
    line_total = artwork.price_xaf * quantity
    commission = (line_total * bps) // 10000
    if reservation_status is None:
        reservation_status = (
            StockReservation.Status.CONVERTED
            if status == Order.Status.PAID
            else StockReservation.Status.ACTIVE
        )
    order = Order.objects.create(
        buyer=buyer,
        reference=f"ORD-{now.year}-{uuid4().hex[:6].upper()}",
        idempotency_key=f"test-{uuid4().hex}",
        request_fingerprint="0" * 64,
        status=status,
        subtotal_items_xaf=line_total,
        grand_total_xaf=line_total,
        shipping_address_snapshot={"city": "Yaoundé", "recipient_name": "Acheteur Test"},
        placed_at=now,
        paid_at=now if status == Order.Status.PAID else None,
    )
    OrderItem.objects.create(
        order=order,
        artwork=artwork,
        artist=artwork.artist,
        title_snapshot=artwork.title,
        unit_price_xaf=artwork.price_xaf,
        quantity=quantity,
        line_total_xaf=line_total,
        commission_rate_bps=bps,
        commission_xaf=commission,
        artist_net_xaf=line_total - commission,
    )
    StockReservation.objects.create(
        artwork=artwork,
        order=order,
        quantity=quantity,
        status=reservation_status,
        expires_at=now + timedelta(minutes=30),
    )
    Payment.objects.create(
        order=order, external_reference=uuid4().hex, amount_xaf=line_total
    )
    return order
