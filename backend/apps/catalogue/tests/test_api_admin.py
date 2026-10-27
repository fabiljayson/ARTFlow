"""Admin moderation — list filters, approve/refuse/hide, permissions (docs/api.md §8)."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, UserRole
from apps.catalogue.models import ArtworkStatus

ADMIN_LIST = "/api/v1/admin/artworks/"


def moderate(pk, **body):
    return f"{ADMIN_LIST}{pk}/moderate/"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def moderator(user_factory, db):
    u = user_factory()
    UserRole.objects.create(user=u, role=Role.MODERATOR)
    return u


@pytest.fixture
def in_moderation(artwork_factory):
    return artwork_factory(title="À modérer", status=ArtworkStatus.IN_MODERATION)


@pytest.mark.django_db
class TestAdminPermissions:
    def test_list_requires_auth(self, client):
        assert client.get(ADMIN_LIST).status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_forbidden_for_artist(self, client, approved_artist):
        client.force_login(approved_artist.user)
        assert client.get(ADMIN_LIST).status_code == status.HTTP_403_FORBIDDEN

    def test_list_ok_for_moderator(self, client, moderator):
        client.force_login(moderator)
        assert client.get(ADMIN_LIST).status_code == status.HTTP_200_OK

    def test_list_ok_for_admin(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(ADMIN_LIST).status_code == status.HTTP_200_OK

    def test_moderate_forbidden_for_artist(self, client, approved_artist, in_moderation):
        client.force_login(approved_artist.user)
        resp = client.post(moderate(in_moderation.pk), {"decision": "approve"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAdminListFilters:
    def test_status_filter(self, client, moderator, artwork_factory):
        artwork_factory(title="Draft", status=ArtworkStatus.DRAFT)
        artwork_factory(title="Mod", status=ArtworkStatus.IN_MODERATION)
        artwork_factory(title="Pub", status=ArtworkStatus.PUBLISHED)
        client.force_login(moderator)
        data = client.get(f"{ADMIN_LIST}?status=IN_MODERATION").json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "Mod"

    def test_admin_list_shows_all_statuses(self, client, moderator, artwork_factory):
        artwork_factory(title="D", status=ArtworkStatus.DRAFT)
        artwork_factory(title="R", status=ArtworkStatus.REFUSED)
        client.force_login(moderator)
        data = client.get(ADMIN_LIST).json()
        assert data["count"] == 2  # unlike public catalogue


@pytest.mark.django_db
class TestModerationDecisions:
    def test_approve_publishes_and_makes_public(self, client, moderator, in_moderation, artwork_factory):
        client.force_login(moderator)
        resp = client.post(moderate(in_moderation.pk), {"decision": "approve"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        in_moderation.refresh_from_db()
        assert in_moderation.status == ArtworkStatus.PUBLISHED
        assert in_moderation.published_at is not None
        # now visible on the public catalogue
        pub = client.get("/api/v1/catalog/artworks/").json()
        assert pub["count"] >= 1
        assert any(r["title"] == "À modérer" for r in pub["results"])

    def test_refuse_requires_reason(self, client, moderator, in_moderation):
        client.force_login(moderator)
        resp = client.post(moderate(in_moderation.pk), {"decision": "refuse"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        in_moderation.refresh_from_db()
        assert in_moderation.status == ArtworkStatus.IN_MODERATION

    def test_refuse_with_reason(self, client, moderator, in_moderation):
        client.force_login(moderator)
        resp = client.post(
            moderate(in_moderation.pk),
            {"decision": "refuse", "reason": "Photos floues, prix incohérent."},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        in_moderation.refresh_from_db()
        assert in_moderation.status == ArtworkStatus.REFUSED
        assert "floues" in in_moderation.refusal_reason

    def test_hide_published_requires_reason(self, client, moderator, artwork_factory):
        art = artwork_factory(title="Cachée", status=ArtworkStatus.PUBLISHED)
        client.force_login(moderator)
        resp = client.post(moderate(art.pk), {"decision": "hide"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        resp = client.post(
            moderate(art.pk), {"decision": "hide", "reason": "Contenu signalé."}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        art.refresh_from_db()
        assert art.status == ArtworkStatus.HIDDEN
        assert "signalé" in art.moderation_note

    def test_approve_only_from_in_moderation(self, client, moderator, artwork_factory):
        art = artwork_factory(title="Brouillon", status=ArtworkStatus.DRAFT)
        client.force_login(moderator)
        resp = client.post(moderate(art.pk), {"decision": "approve"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_decision_logged_in_audit(self, client, moderator, in_moderation):
        from apps.core.models import AuditLog

        client.force_login(moderator)
        client.post(moderate(in_moderation.pk), {"decision": "approve"}, format="json")
        assert AuditLog.objects.filter(
            action="artwork.approved", actor=moderator, object_id=in_moderation.pk
        ).exists()
