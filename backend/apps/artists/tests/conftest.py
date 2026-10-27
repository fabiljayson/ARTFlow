"""Shared fixtures for artists tests."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import Role, UserRole
from apps.artists.models import ApplicationStatus, ArtistProfile

PDF = b"%PDF-1.7\n1 0 obj\n<< >>\nendobj\ntrailer\n<< >>\n%%EOF\n"


def pdf_file(name="id.pdf"):
    return SimpleUploadedFile(name, PDF, content_type="application/pdf")


def png_file(name="art.png"):
    return SimpleUploadedFile(name, b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, content_type="image/png")


@pytest.fixture
def applicant(user):
    """User with a minimal submitted-ready draft profile (no documents)."""
    return ArtistProfile.objects.create(
        user=user, display_name="Awa Art", city="Yaoundé", region="Centre"
    )


@pytest.fixture
def submitted(applicant):
    """Profile with one document, in PENDING_REVIEW."""
    applicant.verification_documents.create(
        kind="ID_CARD",
        file="verification/test/id.pdf",
        original_filename="id.pdf",
        content_type="application/pdf",
        size_bytes=100,
        uploaded_by=applicant.user,
    )
    applicant.status = ApplicationStatus.PENDING_REVIEW
    applicant.save()
    return applicant


@pytest.fixture
def approved_artist(submitted):
    """Approved profile + ARTIST role granted (as the service does)."""
    submitted.status = ApplicationStatus.APPROVED
    submitted.save()
    UserRole.objects.get_or_create(user=submitted.user, role=Role.ARTIST)
    return submitted
