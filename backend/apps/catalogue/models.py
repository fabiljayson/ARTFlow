"""Catalogue models: categories, artworks, media, favorites (docs/database.md §2)."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.artists.models import ArtistProfile
from apps.core.storage import PrivateMediaStorage


class Category(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    name_fr = models.CharField(max_length=120)
    name_en = models.CharField(max_length=120, blank=True)
    description_fr = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    is_active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "name_fr"]

    def __str__(self):
        return self.name_fr

    def clean(self):
        if self.parent and self.parent.parent_id:
            raise ValidationError({"parent": "Arborescence limitée à 2 niveaux."})


class ArtworkStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    IN_MODERATION = "IN_MODERATION", "En modération"
    PUBLISHED = "PUBLISHED", "Publiée"
    REFUSED = "REFUSED", "Refusée"
    HIDDEN = "HIDDEN", "Masquée"
    ARCHIVED = "ARCHIVED", "Archivée"


class Artwork(models.Model):
    reference = models.CharField(max_length=20, unique=True, blank=True)
    artist = models.ForeignKey(ArtistProfile, on_delete=models.PROTECT, related_name="artworks")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="artworks")
    price_xaf = models.BigIntegerField(validators=[MinValueValidator(1)])
    stock_quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=ArtworkStatus.choices, default=ArtworkStatus.DRAFT)
    refusal_reason = models.TextField(blank=True)
    moderation_note = models.TextField(blank=True)
    dimensions = models.CharField(max_length=120, blank=True)
    materials = models.CharField(max_length=255, blank=True)
    technique = models.CharField(max_length=120, blank=True)
    year_created = models.PositiveIntegerField(null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    is_unique_piece = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["artist", "status"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["price_xaf"]),
        ]

    def __str__(self):
        return f"{self.reference} {self.title}"

    @property
    def is_available(self) -> bool:
        return self.status == ArtworkStatus.PUBLISHED and self.stock_quantity > 0

    def save(self, *args, **kwargs):
        if not self.reference:
            year = timezone.now().year
            last = (
                Artwork.objects.filter(reference__startswith=f"ART-{year}-")
                .order_by("-reference")
                .values_list("reference", flat=True)
                .first()
            )
            seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
            self.reference = f"ART-{year}-{seq:06d}"
        if not self.slug:
            base = slugify(self.title)[:200] or "oeuvre"
            candidate = base
            n = Artwork.objects.filter(slug=candidate).count()
            if n:
                candidate = f"{base}-{n + 1}"
            self.slug = candidate[:220]
        super().save(*args, **kwargs)


class MediaKind(models.TextChoices):
    IMAGE = "IMAGE", "Image"
    VIDEO = "VIDEO", "Vidéo"


class ArtworkMedia(models.Model):
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name="media")
    kind = models.CharField(max_length=10, choices=MediaKind.choices)
    source = models.CharField(max_length=20, default="UPLOAD")
    file = models.FileField(upload_to="artworks/%Y/%m/", storage=PrivateMediaStorage(), blank=True)
    poster_file = models.FileField(
        upload_to="artworks/posters/%Y/%m/", storage=PrivateMediaStorage(), blank=True
    )
    thumbnail_file = models.FileField(
        upload_to="artworks/thumbs/%Y/%m/", storage=PrivateMediaStorage(), blank=True
    )
    position = models.PositiveIntegerField(default=0)
    alt_text_fr = models.CharField(max_length=255, blank=True)
    alt_text_en = models.CharField(max_length=255, blank=True)
    width_px = models.PositiveIntegerField(null=True, blank=True)
    height_px = models.PositiveIntegerField(null=True, blank=True)
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["artwork", "position"], name="uniq_artwork_position"),
        ]

    def __str__(self):
        return f"{self.kind} media#{self.pk} ({self.artwork.slug})"


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "artwork"], name="uniq_user_artwork_favorite")]
        indexes = [models.Index(fields=["user"])]
