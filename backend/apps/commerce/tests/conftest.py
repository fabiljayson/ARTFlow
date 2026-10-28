"""Fixtures for commerce tests — buyer owns `user`, artworks live on a separate artist."""
import pytest

from apps.accounts.models import Role, UserRole
from apps.artists.models import ApplicationStatus, ArtistProfile
from apps.catalogue.models import Artwork, ArtworkStatus, Category
from apps.commerce.models import Cart, CartItem


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
