"""Catalogue serializers (public + artist space + moderation)."""
from rest_framework import serializers

from apps.artists.models import ArtistProfile
from apps.catalogue.models import Artwork, ArtworkMedia, ArtworkStatus, Category


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "slug", "name_fr", "name_en", "description_fr", "parent", "children", "position"]
        read_only_fields = fields

    def get_children(self, obj):
        kids = obj.children.filter(is_active=True)
        return CategorySerializer(kids, many=True).data


class MediaSerializer(serializers.ModelSerializer):
    stream_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    poster_url = serializers.SerializerMethodField()

    class Meta:
        model = ArtworkMedia
        fields = [
            "id", "kind", "position", "alt_text_fr", "alt_text_en",
            "is_primary", "width_px", "height_px", "content_type",
            "thumbnail_url", "poster_url", "stream_url",
        ]
        read_only_fields = fields

    def get_stream_url(self, obj):
        return self._media_url(obj, "stream")

    def get_thumbnail_url(self, obj):
        return self._media_url(obj, "thumb")

    def get_poster_url(self, obj):
        return self._media_url(obj, "poster")

    def _media_url(self, obj, which: str):
        field = {"stream": "file", "thumb": "thumbnail_file", "poster": "poster_file"}[which]
        if not getattr(obj, field):
            return None
        request = self.context.get("request")
        path = f"/api/v1/catalog/artworks/{obj.artwork.slug}/media/{obj.pk}/{which}/"
        return request.build_absolute_uri(path) if request else path


class ArtworkSummarySerializer(serializers.ModelSerializer):
    """Catalogue grid card + artist space list."""

    artist_display_name = serializers.CharField(source="artist.display_name", read_only=True)
    artist_slug = serializers.CharField(source="artist.slug", read_only=True)
    primary_image_url = serializers.SerializerMethodField()
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Artwork
        fields = [
            "id", "reference", "slug", "title", "price_xaf", "status",
            "stock_quantity", "is_available", "artist_display_name", "artist_slug",
            "category", "primary_image_url", "published_at", "created_at",
        ]
        read_only_fields = fields

    def get_primary_image_url(self, obj):
        media = next((m for m in obj.media.all() if m.is_primary and m.kind == "IMAGE"), None)
        if media is None:
            media = next((m for m in obj.media.all() if m.kind == "IMAGE"), None)
        if media is None:
            return None
        request = self.context.get("request")
        path = f"/api/v1/catalog/artworks/{obj.slug}/media/{media.pk}/"
        return request.build_absolute_uri(path) if request else path


class ArtworkDetailSerializer(ArtworkSummarySerializer):
    media = MediaSerializer(many=True, read_only=True)
    category_detail = CategorySerializer(source="category", read_only=True)

    class Meta(ArtworkSummarySerializer.Meta):
        fields = ArtworkSummarySerializer.Meta.fields + [
            "description", "dimensions", "materials", "technique",
            "year_created", "weight_kg", "is_unique_piece", "category_detail", "media",
        ]


class ArtworkCreateSerializer(serializers.ModelSerializer):
    """Create/update artist-side artwork."""

    class Meta:
        model = Artwork
        fields = [
            "id", "reference", "slug", "status", "title", "description", "category",
            "price_xaf", "stock_quantity", "dimensions", "materials", "technique",
            "year_created", "weight_kg", "is_unique_piece",
        ]
        read_only_fields = ["id", "reference", "slug", "status"]

    def validate_price_xaf(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le prix doit être strictement positif.")
        return value

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Le stock ne peut pas être négatif.")
        return value


class MediaUploadSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["IMAGE", "VIDEO"])
    file = serializers.FileField()
    alt_text_fr = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    alt_text_en = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    is_primary = serializers.BooleanField(required=False, default=False)


class FavoriteToggleSerializer(serializers.Serializer):
    artwork_id = serializers.IntegerField()


class ArtistPublicSerializer(serializers.ModelSerializer):
    artwork_count = serializers.SerializerMethodField()

    class Meta:
        model = ArtistProfile
        fields = ["slug", "display_name", "bio", "city", "region", "artwork_count"]
        read_only_fields = fields

    def get_artwork_count(self, obj):
        return obj.artworks.filter(status=ArtworkStatus.PUBLISHED).count()


class ArtistPublicDetailSerializer(ArtistPublicSerializer):
    artworks = serializers.SerializerMethodField()

    class Meta(ArtistPublicSerializer.Meta):
        fields = ArtistPublicSerializer.Meta.fields + ["artworks"]

    def get_artworks(self, obj):

        qs = obj.artworks.filter(status=ArtworkStatus.PUBLISHED).order_by("-published_at")
        return ArtworkSummarySerializer(qs, many=True, context=self.context).data


class ModerateSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "refuse", "hide"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class DashboardSerializer(serializers.Serializer):
    total_artworks = serializers.IntegerField()
    published = serializers.IntegerField()
    in_moderation = serializers.IntegerField()
    drafts = serializers.IntegerField()
    unavailable = serializers.IntegerField()
    total_favorites = serializers.IntegerField()
