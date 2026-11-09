"""View tracking — cookie visiteur `af_visitor`, dédup24 h (design preuve sociale §2)."""
import hashlib

import pytest
from rest_framework.test import APIClient

from apps.catalogue.models import ArtworkStatus, ArtworkView


def view_url(slug):
    return f"/api/v1/catalog/artworks/{slug}/view/"


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestArtworkViewTrack:
    def test_first_view_sets_visitor_cookie_and_counts(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED)
        resp = client.post(view_url(art.slug))
        assert resp.status_code == 200
        assert resp.json() == {"view_count": 1, "counted": True}
        token = client.cookies["af_visitor"].value
        assert token  # présent
        art.refresh_from_db()
        assert art.view_count == 1
        ev = ArtworkView.objects.get(artwork=art)
        assert ev.viewer_key == hashlib.sha256(token.encode()).hexdigest()[:32]

    def test_same_visitor_within_24h_not_counted(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED)
        client.post(view_url(art.slug))
        resp = client.post(view_url(art.slug))
        assert resp.json() == {"view_count": 1, "counted": False}
        assert ArtworkView.objects.count() == 1

    def test_new_visitor_counts_separately(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED)
        client.post(view_url(art.slug))
        resp = APIClient().post(view_url(art.slug))
        assert resp.json() == {"view_count": 2, "counted": True}

    def test_unpublished_returns_404_and_creates_nothing(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.DRAFT)
        assert client.post(view_url(art.slug)).status_code == 404
        assert not ArtworkView.objects.exists()

    def test_throttle_scope_declared(self):
        from rest_framework.settings import api_settings

        from apps.catalogue.views import ArtworkViewTrack

        assert ArtworkViewTrack.throttle_scope == "artwork-view"
        assert api_settings.DEFAULT_THROTTLE_RATES["artwork-view"] == "120/min"
