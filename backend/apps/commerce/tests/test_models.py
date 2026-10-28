"""Cart model constraints (docs/database.md §3: 1 panier/user, unique ligne, quantity > 0)."""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.artists.models import ApplicationStatus, ArtistProfile
from apps.catalogue.models import Artwork, ArtworkStatus, Category
from apps.commerce.models import Cart, CartItem

User = get_user_model()


@pytest.fixture
def artwork(db):
    user = User.objects.create(email="artist@example.test", first_name="A", last_name="N")
    profile = ArtistProfile.objects.create(
        user=user, display_name="Awa Ndiaye", city="Yaoundé", status=ApplicationStatus.APPROVED
    )
    category = Category.objects.create(slug="peinture", name_fr="Peinture")
    return Artwork.objects.create(
        artist=profile,
        category=category,
        title="Portrait",
        description="Une belle œuvre.",
        price_xaf=15000,
        stock_quantity=2,
        status=ArtworkStatus.PUBLISHED,
    )


@pytest.mark.django_db
class TestCartConstraints:
    def test_cart_one_to_one_user(self, user):
        Cart.objects.create(user=user)
        with pytest.raises(IntegrityError), transaction.atomic():
            Cart.objects.create(user=user)

    def test_get_or_create_second_call_returns_same(self, user):
        cart1, created1 = Cart.objects.get_or_create(user=user)
        cart2, created2 = Cart.objects.get_or_create(user=user)
        assert created1 is True
        assert created2 is False
        assert cart1.pk == cart2.pk
        assert Cart.objects.filter(user=user).count() == 1


@pytest.mark.django_db
class TestCartItemConstraints:
    def test_item_unique_per_cart_artwork(self, user, artwork):
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, artwork=artwork, quantity=1)
        with pytest.raises(IntegrityError), transaction.atomic():
            CartItem.objects.create(cart=cart, artwork=artwork, quantity=1)

    def test_item_quantity_positive(self, user, artwork):
        cart = Cart.objects.create(user=user)
        with pytest.raises(IntegrityError), transaction.atomic():
            CartItem.objects.create(cart=cart, artwork=artwork, quantity=0)
