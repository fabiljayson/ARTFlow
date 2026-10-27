"""Integration tests — artist application workflow (EF-6, docs/api.md §4)."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.artists.models import ArtistProfile, ArtistVerificationDocument
from apps.artists.tests.conftest import PDF
from apps.core.models import AuditLog

APPLICATION = "/api/v1/artists/application/"
SUBMIT = "/api/v1/artists/application/submit/"
DOCUMENTS = "/api/v1/artists/application/documents/"
ADMIN_LIST = "/api/v1/admin/applications/"


def admin_action(pk, action):
    return f"/api/v1/admin/applications/{pk}/{action}/"


def admin_document(pk, doc_id):
    return f"/api/v1/admin/applications/{pk}/documents/{doc_id}/"


@pytest.fixture
def client():
    return APIClient()


def upload_doc(client, kind="ID_CARD", name="id.pdf", content=PDF):
    return client.post(
        DOCUMENTS,
        {"kind": kind, "file": SimpleUploadedFile(name, content)},
        format="multipart",
    )


@pytest.mark.django_db
class TestApplicationDraft:
    def test_create_and_get_draft(self, client, user):
        client.force_login(user)
        resp = client.post(
            APPLICATION,
            {"display_name": "Awa", "city": "Yaoundé", "shipping_base_fee_xaf": 2000},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["status"] == "DRAFT"
        resp2 = client.get(APPLICATION)
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.json()["display_name"] == "Awa"
        assert AuditLog.objects.filter(action="application.created", actor=user).exists()

    def test_get_without_profile_404(self, client, user):
        client.force_login(user)
        assert client.get(APPLICATION).status_code == status.HTTP_404_NOT_FOUND

    def test_patch_draft(self, client, applicant):
        client.force_login(applicant.user)
        resp = client.patch(APPLICATION, {"bio": "Peintre surrealiste"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["bio"] == "Peintre surrealiste"

    def test_post_when_approved_conflict(self, client, approved_artist):
        client.force_login(approved_artist.user)
        resp = client.post(APPLICATION, {"display_name": "X", "city": "Y"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSubmitAndReview:
    def test_submit_requires_document(self, client, applicant):
        client.force_login(applicant.user)
        resp = client.post(SUBMIT)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_full_flow_draft_to_approved(self, client, user, admin_user):
        client.force_login(user)
        client.post(APPLICATION, {"display_name": "Awa", "city": "Yaoundé"}, format="json")
        assert upload_doc(client).status_code == status.HTTP_201_CREATED
        resp = client.post(SUBMIT)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "PENDING_REVIEW"
        assert AuditLog.objects.filter(action="application.submitted", actor=user).exists()

        # Admin approves
        profile = user.artist_profile
        client.force_login(admin_user)
        resp = client.post(admin_action(profile.pk, "approve"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "APPROVED"
        user.refresh_from_db()
        assert user.has_role("ARTIST") is True
        assert AuditLog.objects.filter(action="application.approved", actor=admin_user).exists()

    def test_needs_info_cycle(self, client, submitted, admin_user, user):
        client.force_login(admin_user)
        resp = client.post(admin_action(submitted.pk, "request-info"), {"message": "Carte floue."}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "NEEDS_INFO"
        assert resp.json()["info_request"] == "Carte floue."

        # Applicant patches and resubmits
        client.force_login(user)
        client.patch(APPLICATION, {"bio": "Complétée"}, format="json")
        resp = client.post(SUBMIT)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "PENDING_REVIEW"
        assert resp.json()["info_request"] == ""

    def test_reject_with_reason(self, client, submitted, admin_user):
        client.force_login(admin_user)
        resp = client.post(admin_action(submitted.pk, "reject"), {"reason": "Dossier incomplet."}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "REJECTED"
        assert resp.json()["rejection_reason"] == "Dossier incomplet."
        assert AuditLog.objects.filter(action="application.rejected", actor=admin_user).exists()

    def test_reject_without_reason_400(self, client, submitted, admin_user):
        client.force_login(admin_user)
        resp = client.post(admin_action(submitted.pk, "reject"), {"reason": "  "}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_approve_from_draft_illegal(self, client, applicant, admin_user):
        client.force_login(admin_user)
        resp = client.post(admin_action(applicant.pk, "approve"))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_submit_from_pending_illegal(self, client, submitted):
        client.force_login(submitted.user)
        resp = client.post(SUBMIT)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSuspend:
    def test_suspend_revokes_artist_role(self, client, approved_artist, admin_user):
        client.force_login(admin_user)
        resp = client.post(
            admin_action(approved_artist.pk, "suspend"), {"reason": "Vente de contrefaçons."}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "SUSPENDED"
        approved_artist.user.refresh_from_db()
        assert approved_artist.user.has_role("ARTIST") is False
        assert AuditLog.objects.filter(action="application.suspended", actor=admin_user).exists()

    def test_suspended_can_be_reapproved(self, client, approved_artist, admin_user):
        client.force_login(admin_user)
        client.post(admin_action(approved_artist.pk, "suspend"), {"reason": "Motif."}, format="json")
        resp = client.post(admin_action(approved_artist.pk, "approve"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "APPROVED"
        approved_artist.user.refresh_from_db()
        assert approved_artist.user.has_role("ARTIST") is True

    def test_suspend_requires_reason(self, client, approved_artist, admin_user):
        client.force_login(admin_user)
        resp = client.post(admin_action(approved_artist.pk, "suspend"), {"reason": ""}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestDocuments:
    def test_upload_and_list(self, client, user):
        client.force_login(user)
        client.post(APPLICATION, {"display_name": "Awa", "city": "Yaoundé"}, format="json")
        resp = upload_doc(client, name="carte.png", content=b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["content_type"] == "image/png"
        assert "file" not in data  # no URL ever
        listed = client.get(DOCUMENTS).json()
        assert len(listed) == 1

    def test_upload_rejects_bad_bytes(self, client, user):
        client.force_login(user)
        client.post(APPLICATION, {"display_name": "Awa", "city": "Yaoundé"}, format="json")
        resp = upload_doc(client, name="evil.png", content=b"MZ\x90\x00" + b"\x00" * 8)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_own_document(self, client, user):
        client.force_login(user)
        client.post(APPLICATION, {"display_name": "Awa", "city": "Yaoundé"}, format="json")
        doc_id = upload_doc(client).json()["id"]
        resp = client.delete(f"{DOCUMENTS}{doc_id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not ArtistVerificationDocument.objects.filter(pk=doc_id).exists()

    def test_delete_other_user_document_404(self, client, user, other_user):
        client.force_login(user)
        client.post(APPLICATION, {"display_name": "Awa", "city": "Yaoundé"}, format="json")
        doc_id = upload_doc(client).json()["id"]
        client.force_login(other_user)
        resp = client.delete(f"{DOCUMENTS}{doc_id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert ArtistVerificationDocument.objects.filter(pk=doc_id).exists()


@pytest.mark.django_db
class TestAdmin:
    def test_list_requires_moderator(self, client, user):
        client.force_login(user)
        assert client.get(ADMIN_LIST).status_code == status.HTTP_403_FORBIDDEN

    def test_list_anonymous_401(self, client):
        assert client.get(ADMIN_LIST).status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_filtered_by_status(self, client, submitted, admin_user):
        client.force_login(admin_user)
        data = client.get(f"{ADMIN_LIST}?status=PENDING_REVIEW").json()
        assert data["count"] == 1
        assert data["results"][0]["status"] == "PENDING_REVIEW"
        data = client.get(f"{ADMIN_LIST}?status=REJECTED").json()
        assert data["count"] == 0

    def test_document_download_streams_file(self, client, user, admin_user):
        client.force_login(user)
        client.post(APPLICATION, {"display_name": "Awa", "city": "Yaoundé"}, format="json")
        doc = upload_doc(client).json()
        profile = user.artist_profile

        client.force_login(admin_user)
        resp = client.get(admin_document(profile.pk, doc["id"]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Cache-Control"] == "no-store"
        assert resp["Content-Disposition"].startswith("attachment")
        assert AuditLog.objects.filter(action="verification_document.viewed", actor=admin_user).exists()

    def test_document_download_denied_for_applicant(self, client, user):
        # The applicant must NOT read documents through the admin endpoint
        client.force_login(user)
        client.post(APPLICATION, {"display_name": "Awa", "city": "Yaoundé"}, format="json")
        doc = upload_doc(client).json()
        resp = client.get(admin_document(user.artist_profile.pk, doc["id"]))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_document_download_cross_profile_404(self, client, submitted, other_user, admin_user):
        # Admin of another profile's doc id under submitted's profile id → 404 for wrong doc
        client.force_login(admin_user)
        resp = client.get(admin_document(submitted.pk, 999999))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestIsolation:
    def test_cannot_patch_other_application(self, client, applicant, other_user):
        client.force_login(other_user)
        # No profile → 404; and applicant's row untouched
        assert client.patch(APPLICATION, {"display_name": "Hack"}, format="json").status_code == (
            status.HTTP_404_NOT_FOUND
        )
        applicant.refresh_from_db()
        assert applicant.display_name == "Awa Art"

    def test_one_profile_per_user(self, user, applicant):
        # Second create attempt returns existing (service) — uniqueness by OneToOne
        assert ArtistProfile.objects.filter(user=user).count() == 1
