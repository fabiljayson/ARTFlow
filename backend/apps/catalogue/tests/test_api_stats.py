"""Stats sociales — favorite_count/sold_count, tri trending 7 j, stats artiste (design §5)."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalogue.models import ArtworkStatus, ArtworkView, Favorite
from apps.commerce.models import Order
from apps.conftest import make_order

LIST = "/api/v1/catalog/artworks/"


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestSocialStats:
    def test_summary_exposes_counts(self, client, artwork_factory, user_factory, user):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED)
        Favorite.objects.create(user=user, artwork=art)
        make_order(user_factory(), art, status=Order.Status.PAID, quantity=2)
        row = client.get(LIST).json()["results"][0]
        assert row["favorite_count"] == 1
        assert row["sold_count"] == 2

    def test_sold_excludes_pending_cancelled_refunded(self, client, artwork_factory, user_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED)
        for st in (Order.Status.PENDING_PAYMENT, Order.Status.CANCELLED, Order.Status.REFUNDED):
            make_order(user_factory(), art, status=st, quantity=1)
        assert client.get(LIST).json()["results"][0]["sold_count"] == 0

    def test_trending_orders_by_view_score(self, client, artwork_factory, db):
        """5 vues dans la fenêtre (j-6) l'emportent sur 2 vues fraîches.

        Le score = vues 7 j (+3× favoris), sans décroissance intra-fenêtre
        (décision design §5) — la borne exacte est couverte par le test suivant.
        """
        old, new = (
            artwork_factory(status=ArtworkStatus.PUBLISHED, title=t) for t in ("Ancien", "Recent")
        )
        now = timezone.now()
        for i in range(5):
            ArtworkView.objects.create(
                artwork=old, viewer_key=f"o{i}", created_at=now - timedelta(days=6)
            )
        ArtworkView.objects.create(artwork=new, viewer_key="n1", created_at=now - timedelta(hours=1))
        ArtworkView.objects.create(artwork=new, viewer_key="n2", created_at=now - timedelta(hours=2))
        titles = [r["title"] for r in client.get(f"{LIST}?sort=trending").json()["results"]]
        assert titles.index("Ancien") < titles.index("Recent")

    def test_trending_window_is_7_days(self, client, artwork_factory, db):
        stale = artwork_factory(status=ArtworkStatus.PUBLISHED, title="Vieux")
        fresh = artwork_factory(status=ArtworkStatus.PUBLISHED, title="Frais")
        ArtworkView.objects.create(
            artwork=stale, viewer_key="s", created_at=timezone.now() - timedelta(days=7, hours=1)
        )
        ArtworkView.objects.create(
            artwork=fresh, viewer_key="f", created_at=timezone.now() - timedelta(days=1)
        )
        rows = client.get(f"{LIST}?sort=trending").json()["results"]
        assert rows[0]["title"] == "Frais"

    def test_trending_fav_weights_3(self, client, artwork_factory, user_factory, user):
        two_views = artwork_factory(status=ArtworkStatus.PUBLISHED, title="2v")
        one_fav = artwork_factory(status=ArtworkStatus.PUBLISHED, title="1f")
        now = timezone.now()
        ArtworkView.objects.create(artwork=two_views, viewer_key="a", created_at=now)
        ArtworkView.objects.create(artwork=two_views, viewer_key="b", created_at=now)
        Favorite.objects.create(user=user_factory(), artwork=one_fav, created_at=now)
        rows = client.get(f"{LIST}?sort=trending").json()["results"]
        assert rows[0]["title"] == "1f"

    def test_artist_detail_stats(self, client, artwork_factory, user, user_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED, stock=3)
        make_order(user_factory(), art, status=Order.Status.PAID, quantity=1)
        Favorite.objects.create(user=user, artwork=art)
        stats = client.get(f"/api/v1/catalog/artists/{art.artist.slug}/").json()["stats"]
        assert stats == {"works": 1, "sold": 1, "views": 0, "favorites": 1}
