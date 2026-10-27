"""Artist application models (docs/database.md §1)."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.storage import PrivateMediaStorage


class ApplicationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    PENDING_REVIEW = "PENDING_REVIEW", "En attente d'examen"
    NEEDS_INFO = "NEEDS_INFO", "Informations demandées"
    APPROVED = "APPROVED", "Approuvée"
    REJECTED = "REJECTED", "Refusée"
    SUSPENDED = "SUSPENDED", "Suspendue"


class PayoutMethod(models.TextChoices):
    MANUAL = "MANUAL", "Manuel (MVP)"


class ArtistProfile(models.Model):
    """One profile per user; the application workflow lives on this row."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artist_profile")
    display_name = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    city = models.CharField(max_length=80)
    region = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_applications"
    )
    rejection_reason = models.TextField(blank=True)
    info_request = models.TextField(blank=True)
    suspension_reason = models.TextField(blank=True)
    shipping_base_fee_xaf = models.PositiveBigIntegerField(
        default=0, validators=[MinValueValidator(0)], help_text="Frais d'expédition par défaut du vendeur (XAF)."
    )
    payout_method = models.CharField(max_length=20, choices=PayoutMethod.choices, default=PayoutMethod.MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.display_name} ({self.status})"


class DocumentKind(models.TextChoices):
    ID_CARD = "ID_CARD", "Pièce d'identité"
    PASSPORT = "PASSPORT", "Passeport"
    ART_PROOF = "ART_PROOF", "Preuve de création artistique"
    OTHER = "OTHER", "Autre"


class ArtistVerificationDocument(models.Model):
    """Verification documents — private storage, admin-only download (docs/api.md §4)."""

    artist_profile = models.ForeignKey(
        ArtistProfile, on_delete=models.CASCADE, related_name="verification_documents"
    )
    kind = models.CharField(max_length=30, choices=DocumentKind.choices)
    file = models.FileField(upload_to="verification/%Y/%m/", storage=PrivateMediaStorage())
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_verification_documents"
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.kind} — {self.original_filename}"
