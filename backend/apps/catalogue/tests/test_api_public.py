"""Public catalogue — only PUBLISHED visible (EF-2, EF-3, docs/api.md §3)."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalogue.models import ArtworkMedia, ArtworkStatus, Favorite
from apps.catalogue.tests.conftest import make_artwork

LIST = "/api/v1/catalog/artworks/"
CATEGORIES = "/api/v1/catalog/categories/"
ARTISTS = "/api/v1/catalog/artists/"


def detail(slug):
    return f"{LIST}{slug}/"


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestCatalogVisibility:
    def test_only_published_listed(self, client, artwork_factory, category, second_artist):
        artwork_factory(title="Draft", status=ArtworkStatus.DRAFT)
        artwork_factory(title="Mod", status=ArtworkStatus.IN_MODERATION)
        artwork_factory(title="Hidden", status=ArtworkStatus.HIDDEN)
        artwork_factory(title="Refused", status=ArtworkStatus.REFUSED)
        artwork_factory(title="Publie", status=ArtworkStatus.PUBLISHED, price=15000)
        make_artwork(second_artist, category, title="Publie 2", status=ArtworkStatus.PUBLISHED, price=25000)
        data = client.get(LIST).json()
        titles = [r["title"] for r in data["results"]]
        assert data["count"] == 2
        assert sorted(titles) == ["Publie", "Publie 2"]

    def test_detail_404_for_non_published(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.DRAFT)
        assert client.get(detail(art.slug)).status_code == status.HTTP_404_NOT_FOUND

    def test_detail_200_for_published(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED)
        resp = client.get(detail(art.slug))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["title"] == art.title
        assert data["description"]
        assert data["price_xaf"] == art.price_xaf

    def test_filter_by_category_slug(self, client, artwork_factory, other_category):
        artwork_factory(title="Peinture", status=ArtworkStatus.PUBLISHED)
        make_artwork(artwork_factory().artist, other_category, title="Sculpture", status=ArtworkStatus.PUBLISHED)
        data = client.get(f"{LIST}?category=sculpture").json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "Sculpture"

    def test_search_q(self, client, artwork_factory):
        artwork_factory(title="Lion royal", status=ArtworkStatus.PUBLISHED)
        artwork_factory(title="Paysage", status=ArtworkStatus.PUBLISHED)
        data = client.get(f"{LIST}?q=lion").json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "Lion royal"

    def test_price_filters(self, client, artwork_factory):
        artwork_factory(title="Cher", status=ArtworkStatus.PUBLISHED, price=50000)
        artwork_factory(title="Moins cher", status=ArtworkStatus.PUBLISHED, price=5000)
        data = client.get(f"{LIST}?price_max=10000").json()
        assert [r["title"] for r in data["results"]] == ["Moins cher"]
        data = client.get(f"{LIST}?price_min=40000").json()
        assert [r["title"] for r in data["results"]] == ["Cher"]

    def test_available_filter(self, client, artwork_factory):
        artwork_factory(title="En stock", status=ArtworkStatus.PUBLISHED, stock=1)
        artwork_factory(title="Epuise", status=ArtworkStatus.PUBLISHED, stock=0)
        data = client.get(f"{LIST}?available=true").json()
        assert [r["title"] for r in data["results"]] == ["En stock"]

    def test_sort_price_asc(self, client, artwork_factory):
        artwork_factory(title="B", status=ArtworkStatus.PUBLISHED, price=20000)
        artwork_factory(title="A", status=ArtworkStatus.PUBLISHED, price=10000)
        data = client.get(f"{LIST}?sort=price").json()
        assert [r["title"] for r in data["results"]] == ["A", "B"]

    def test_pagination(self, client, artwork_factory):
        for i in range(25):
            artwork_factory(title=f"Oeuvre {i}", status=ArtworkStatus.PUBLISHED, price=1000 + i)
        data = client.get(LIST).json()
        assert data["count"] == 25
        assert len(data["results"]) == 20
        assert data["next"] is not None

    def test_similar_by_category(self, client, artwork_factory):
        art = artwork_factory(title="Orig", status=ArtworkStatus.PUBLISHED)
        artwork_factory(title="Same cat", status=ArtworkStatus.PUBLISHED)
        resp = client.get(f"{detail(art.slug)}similar/").json()
        titles = [r["title"] for r in resp]
        assert "Same cat" in titles
        assert "Orig" not in titles


@pytest.mark.django_db
class TestCategoriesArtists:
    def test_categories_tree_root_only(self, client, category):
        from apps.catalogue.models import Category

        Category.objects.create(slug="sculpture", name_fr="Sculpture")
        Category.objects.create(slug="huile", name_fr="Huile", parent=category)
        data = client.get(CATEGORIES).json()
        slugs = [c["slug"] for c in data["results"]] if isinstance(data, dict) else [c["slug"] for c in data]
        assert "huile" not in slugs
        assert set(slugs) == {"peinture", "sculpture"}
        peinture = next(c for c in data["results"] if c["slug"] == "peinture")
        assert [ch["slug"] for ch in peinture["children"]] == ["huile"]

    def test_artists_public_only_approved(self, client, approved_artist, other_user, db):
        from apps.artists.models import ArtistProfile

        ArtistProfile.objects.create(user=other_user, display_name="En attente", city="Yaoundé")
        data = client.get(ARTISTS).json()
        names = [a["display_name"] for a in data["results"]]
        assert names == ["Awa Ndiaye"]

    def test_artist_detail_with_published_works(self, client, approved_artist, artwork_factory):
        artwork_factory(status=ArtworkStatus.PUBLISHED)
        artwork_factory(title="Brouillon", status=ArtworkStatus.DRAFT)
        data = client.get(f"{ARTISTS}{approved_artist.slug}/").json()
        assert data["display_name"] == "Awa Ndiaye"
        assert data["artwork_count"] == 1
        assert all(a["status"] == "PUBLISHED" for a in data["artworks"])


@pytest.mark.django_db
class TestFavorites:
    def test_toggle_on_off(self, client, user, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED)
        client.force_login(user)
        resp = client.post(f"{LIST}{art.pk}/favorite/")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["favorited"] is True
        resp = client.post(f"{LIST}{art.pk}/favorite/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["favorited"] is False
        assert not Favorite.objects.filter(user=user, artwork=art).exists()

    def test_favorite_list(self, client, user, artwork_factory):
        art = artwork_factory(title="Mon coup de coeur", status=ArtworkStatus.PUBLISHED)
        client.force_login(user)
        client.post(f"{LIST}{art.pk}/favorite/")
        data = client.get("/api/v1/catalog/favorites/").json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "Mon coup de coeur"

    def test_favorite_requires_auth(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED)
        assert client.post(f"{LIST}{art.pk}/favorite/").status_code == status.HTTP_401_UNAUTHORIZED

    def test_cannot_favorite_unpublished(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.DRAFT)
        client.force_login(art.artist.user)
        assert client.post(f"{LIST}{art.pk}/favorite/").status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestMediaStream:
    def _publish_with_image(self, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED)
        from apps.catalogue.tests.conftest import png_file

        media = ArtworkMedia(
            artwork=art, kind="IMAGE", position=0, alt_text_fr="Une peinture", content_type="image/png"
        )
        media.file.save("oeuvre.png", png_file(), save=True)
        return art, media

    def test_published_media_streams_publicly(self, client, artwork_factory):
        art, media = self._publish_with_image(artwork_factory)
        resp = client.get(f"{detail(art.slug)}media/{media.pk}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "image/png"
        assert resp["Cache-Control"] == "public, max-age=3600"

    def test_unpublished_media_404_anonymous(self, client, artwork_factory):
        from apps.catalogue.tests.conftest import png_file

        art = artwork_factory(status=ArtworkStatus.DRAFT)
        media = ArtworkMedia(artwork=art, kind="IMAGE", position=0, alt_text_fr="x", content_type="image/png")
        media.file.save("brouillon.png", png_file(), save=True)
        resp = client.get(f"{detail(art.slug)}media/{media.pk}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unknown_media_404(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED)
        assert client.get(f"{detail(art.slug)}media/99999/").status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestVideosFeed:
    def test_feed_lists_video_of_published_only(self, client, artwork_factory):
        art_pub = artwork_factory(status=ArtworkStatus.PUBLISHED)
        art_draft = artwork_factory(title="B", status=ArtworkStatus.DRAFT)
        for art in (art_pub, art_draft):
            ArtworkMedia.objects.create(artwork=art, kind="VIDEO", position=0, content_type="video/mp4")
        data = client.get("/api/v1/videos/feed/").json()
        assert len(data) == 1
        assert data[0]["artwork_slug"] == art_pub.slug
