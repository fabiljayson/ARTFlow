"""Artist space — CRUD isolation, media upload, workflow (EF-7, docs/api.md §5)."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, UserRole
from apps.artists.models import ApplicationStatus, ArtistProfile
from apps.catalogue.models import Artwork, ArtworkMedia, ArtworkStatus
from apps.catalogue.tests.conftest import make_artwork, mp4_file, png_file

ARTIST_LIST = "/api/v1/artist/artworks/"
DASHBOARD = "/api/v1/artist/dashboard/"


def own(pk):
    return f"{ARTIST_LIST}{pk}/"


@pytest.fixture
def client():
    return APIClient()


def upload_image(client, artwork_pk, *, alt="Une peinture", name="p.png"):
    return client.post(
        f"{own(artwork_pk)}media/",
        {"kind": "IMAGE", "file": png_file(name), "alt_text_fr": alt},
        format="multipart",
    )


def create_artwork(client, *, category, title="Nouvelle œuvre", price=20000, stock=1, **extra):
    payload = {
        "title": title,
        "description": "Description de démo.",
        "category": category,
        "price_xaf": price,
        "stock_quantity": stock,
    }
    payload.update(extra)
    return client.post(ARTIST_LIST, payload, format="json")


@pytest.mark.django_db
class TestArtistCrud:
    def test_list_only_own_artworks(self, client, approved_artist, second_artist, artwork_factory, category):
        artwork_factory(title="La mienne", status=ArtworkStatus.DRAFT)
        make_artwork(second_artist, category, title="Des autres", status=ArtworkStatus.PUBLISHED)
        client.force_login(approved_artist.user)
        data = client.get(ARTIST_LIST).json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "La mienne"

    def test_create_draft(self, client, approved_artist, category):
        from apps.core.models import AuditLog

        client.force_login(approved_artist.user)
        resp = create_artwork(client, category=category.pk)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        # client must learn reference/slug/status without a follow-up GET
        assert data["status"] == "DRAFT"
        assert data["reference"].startswith("ART-")
        assert data["slug"]
        art = Artwork.objects.get(pk=data["id"])
        assert art.slug == data["slug"]
        assert AuditLog.objects.filter(action="artwork.created", actor=approved_artist.user).exists()

    def test_create_forbidden_without_artist_role(self, client, user, category):
        client.force_login(user)
        resp = create_artwork(client, category=category.pk)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_forbidden_when_profile_not_approved(self, client, user, category):
        ArtistProfile.objects.create(
            user=user, display_name="Attente", city="Yaoundé", status=ApplicationStatus.PENDING_REVIEW
        )
        UserRole.objects.create(user=user, role=Role.ARTIST)  # stale role kept
        client.force_login(user)
        resp = create_artwork(client, category=category.pk)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_own_artwork(self, client, artwork_factory):
        art = artwork_factory(title="Avant")
        client.force_login(art.artist.user)
        resp = client.patch(own(art.pk), {"title": "Après"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        art.refresh_from_db()
        assert art.title == "Après"

    def test_update_other_artist_artwork_404(self, client, artwork_factory, second_artist):
        art = artwork_factory()
        client.force_login(second_artist.user)
        resp = client.patch(own(art.pk), {"title": "Piraté"}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        art.refresh_from_db()
        assert art.title != "Piraté"

    def test_delete_is_archived_not_removed(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.DRAFT)
        client.force_login(art.artist.user)
        resp = client.delete(own(art.pk))
        assert resp.status_code == status.HTTP_204_NO_CONTENT  # DRF destroy
        art.refresh_from_db()
        assert art.status == ArtworkStatus.ARCHIVED
        assert Artwork.objects.filter(pk=art.pk).exists()

    def test_reprice_beyond_threshold_remoderation(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED, price=10000)
        client.force_login(art.artist.user)
        # +30% > seuil 20% (PlatformSettings.moderation_reprice_threshold_pct)
        resp = client.patch(own(art.pk), {"price_xaf": 13000}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        art.refresh_from_db()
        assert art.status == ArtworkStatus.IN_MODERATION

    def test_small_reprice_stays_published(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.PUBLISHED, price=10000)
        client.force_login(art.artist.user)
        resp = client.patch(own(art.pk), {"price_xaf": 11000}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        art.refresh_from_db()
        assert art.status == ArtworkStatus.PUBLISHED


@pytest.mark.django_db
class TestPublishWorkflow:
    def test_publish_requires_image(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.DRAFT)
        client.force_login(art.artist.user)
        resp = client.post(f"{own(art.pk)}publish/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_publish_flow_to_moderation_then_unpublish(self, client, artwork_factory):
        art = artwork_factory(status=ArtworkStatus.DRAFT)
        client.force_login(art.artist.user)
        assert upload_image(client, art.pk).status_code == status.HTTP_201_CREATED

        resp = client.post(f"{own(art.pk)}publish/")
        assert resp.status_code == status.HTTP_200_OK
        art.refresh_from_db()
        assert art.status == ArtworkStatus.IN_MODERATION

        # unpublish is only legal from PUBLISHED — moderator approves first (simulated).
        art.status = ArtworkStatus.PUBLISHED
        art.save()
        resp = client.post(f"{own(art.pk)}unpublish/")
        assert resp.status_code == status.HTTP_200_OK
        art.refresh_from_db()
        assert art.status == ArtworkStatus.HIDDEN

    def test_publish_forbidden_without_artist_role(self, client, other_user, artwork_factory):
        art = artwork_factory()
        client.force_login(other_user)  # not the owner, no ARTIST role
        assert client.post(f"{own(art.pk)}publish/").status_code == status.HTTP_403_FORBIDDEN

    def test_dashboard_counts(self, client, artwork_factory, approved_artist):
        artwork_factory(title="P", status=ArtworkStatus.PUBLISHED)
        artwork_factory(title="M", status=ArtworkStatus.IN_MODERATION)
        artwork_factory(title="D", status=ArtworkStatus.DRAFT)
        client.force_login(approved_artist.user)
        data = client.get(DASHBOARD).json()
        assert data["total_artworks"] == 3
        assert data["published"] == 1
        assert data["in_moderation"] == 1
        assert data["drafts"] == 1


@pytest.mark.django_db
class TestMediaUpload:
    def test_upload_image_generates_thumbnail(self, client, artwork_factory):
        art = artwork_factory()
        client.force_login(art.artist.user)
        resp = upload_image(client, art.pk, alt="Toile dorée")
        assert resp.status_code == status.HTTP_201_CREATED
        media = ArtworkMedia.objects.get(pk=resp.json()["id"])
        assert media.thumbnail_file
        assert media.checksum_sha256
        assert media.width_px == 1
        assert media.content_type == "image/png"
        data = resp.json()
        assert data["thumbnail_url"] and data["stream_url"]

    def test_upload_requires_alt_text_for_images(self, client, artwork_factory):
        art = artwork_factory()
        client.force_login(art.artist.user)
        resp = client.post(
            f"{own(art.pk)}media/", {"kind": "IMAGE", "file": png_file()}, format="multipart"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_video_does_not_require_alt_text(self, client, artwork_factory):
        art = artwork_factory()
        client.force_login(art.artist.user)
        resp = client.post(
            f"{own(art.pk)}media/",
            {"kind": "VIDEO", "file": mp4_file()},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_upload_rejects_wrong_magic(self, client, artwork_factory):
        from django.core.files.uploadedfile import SimpleUploadedFile

        art = artwork_factory()
        client.force_login(art.artist.user)
        resp = client.post(
            f"{own(art.pk)}media/",
            {
                "kind": "IMAGE",
                "file": SimpleUploadedFile("x.png", b"MZ\x90\x00" + b"\x00" * 16),
                "alt_text_fr": "x",
            },
            format="multipart",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_image_quota_10(self, client, artwork_factory):
        art = artwork_factory()
        client.force_login(art.artist.user)
        for i in range(10):
            resp = upload_image(client, art.pk, alt=f"img {i}", name=f"p{i}.png")
            assert resp.status_code == status.HTTP_201_CREATED, resp.content
        resp = upload_image(client, art.pk, alt="encore", name="p11.png")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Quota" in str(resp.json())

    def test_video_quota_1(self, client, artwork_factory):
        art = artwork_factory()
        client.force_login(art.artist.user)
        resp = client.post(
            f"{own(art.pk)}media/", {"kind": "VIDEO", "file": mp4_file("clip.mp4")}, format="multipart"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        resp = client.post(
            f"{own(art.pk)}media/", {"kind": "VIDEO", "file": mp4_file("clip2.mp4")}, format="multipart"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_media(self, client, artwork_factory):
        art = artwork_factory()
        client.force_login(art.artist.user)
        media_id = upload_image(client, art.pk).json()["id"]
        resp = client.delete(f"{own(art.pk)}media/{media_id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not ArtworkMedia.objects.filter(pk=media_id).exists()

    def test_delete_other_artist_media_404(self, client, artwork_factory, second_artist):
        art = artwork_factory()
        client.force_login(art.artist.user)
        media_id = upload_image(client, art.pk).json()["id"]
        client.force_login(second_artist.user)
        resp = client.delete(f"{own(art.pk)}media/{media_id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND  # _own_artwork filters by owner
        assert ArtworkMedia.objects.filter(pk=media_id).exists()
