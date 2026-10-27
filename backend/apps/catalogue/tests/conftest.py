"""Fixtures for catalogue tests."""
import base64

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import Role, UserRole
from apps.artists.models import ApplicationStatus, ArtistProfile
from apps.catalogue.models import Artwork, ArtworkStatus, Category

# A real 1×1 PNG (Pillow needs valid image data to build a thumbnail).
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGM4IScHAAK2AQU0pnWqAAAAAElFTkSuQmCC"
)


def png_file(name="oeuvre.png"):
    return SimpleUploadedFile(name, PNG_1PX, content_type="image/png")


def mp4_file(name="clip.mp4"):
    # Minimal ISO-BMFF header: 4-byte size + 'ftyp' + brand.
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 16, content_type="video/mp4")


@pytest.fixture
def category(db):
    return Category.objects.create(slug="peinture", name_fr="Peinture")


@pytest.fixture
def other_category(db):
    return Category.objects.create(slug="sculpture", name_fr="Sculpture")


@pytest.fixture
def approved_artist(user, db):
    """User with APPROVED profile + ARTIST role (post-approval state)."""
    profile = ArtistProfile.objects.create(
        user=user, display_name="Awa Ndiaye", city="Yaoundé", status=ApplicationStatus.APPROVED
    )
    UserRole.objects.get_or_create(user=user, role=Role.ARTIST)
    return profile


@pytest.fixture
def second_artist(other_user, db):
    profile = ArtistProfile.objects.create(
        user=other_user, display_name="Kofi Art", city="Douala", status=ApplicationStatus.APPROVED
    )
    UserRole.objects.get_or_create(user=other_user, role=Role.ARTIST)
    return profile


def make_artwork(artist, category, *, status=ArtworkStatus.DRAFT, title="Œuvre", price=10000, stock=1, **extra):
    return Artwork.objects.create(
        artist=artist,
        category=category,
        title=title,
        description="Une belle œuvre de démonstration.",
        price_xaf=price,
        stock_quantity=stock,
        status=status,
        **extra,
    )


@pytest.fixture
def artwork_factory(approved_artist, category):
    def _make(**kwargs):
        artist = kwargs.pop("artist", approved_artist)
        cat = kwargs.pop("category", category)
        return make_artwork(artist, cat, **kwargs)

    return _make


@pytest.fixture
def png_upload():
    def _upload(name="oeuvre.png"):
        return png_file(name)

    return _upload
