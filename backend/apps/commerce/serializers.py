"""Commerce serializers (docs/api.md §6 — responses are flat, no success envelope)."""
from rest_framework import serializers

from apps.catalogue.models import ArtworkStatus
from apps.commerce.models import Cart, CartItem


class CartArtworkSerializer(serializers.Serializer):
    """Read-only projection of an artwork inside a cart line."""

    id = serializers.IntegerField()
    slug = serializers.CharField()
    title = serializers.CharField()
    price_xaf = serializers.IntegerField()
    stock_quantity = serializers.IntegerField()
    is_available = serializers.BooleanField()
    artist_display_name = serializers.SerializerMethodField()
    primary_image_url = serializers.SerializerMethodField()

    def get_artist_display_name(self, obj) -> str:
        return obj.artist.display_name

    def get_primary_image_url(self, obj):
        media = next((m for m in obj.media.all() if m.is_primary and m.thumbnail_file), None)
        if media is None:
            media = next((m for m in obj.media.all() if m.thumbnail_file), None)
        if media is None:
            return None
        path = f"/api/v1/catalog/artworks/{obj.slug}/media/{media.pk}/thumb/"
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


class CartItemSerializer(serializers.ModelSerializer):
    artwork = CartArtworkSerializer(read_only=True)
    line_total_xaf = serializers.SerializerMethodField()
    quantity_exceeds_stock = serializers.SerializerMethodField()
    artwork_unavailable = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "artwork",
            "quantity",
            "line_total_xaf",
            "quantity_exceeds_stock",
            "artwork_unavailable",
        ]

    def get_line_total_xaf(self, obj) -> int:
        return obj.artwork.price_xaf * obj.quantity

    def get_quantity_exceeds_stock(self, obj) -> bool:
        return obj.quantity > obj.artwork.stock_quantity

    def get_artwork_unavailable(self, obj) -> bool:
        return obj.artwork.status != ArtworkStatus.PUBLISHED


class CartSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    items_total_xaf = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items_count", "items_total_xaf", "items"]

    def _fetched_items(self, obj):
        if not hasattr(self, "_cached_items"):
            self._cached_items = list(
                obj.items.select_related("artwork", "artwork__artist").prefetch_related("artwork__media")
            )
        return self._cached_items

    def get_items(self, obj):
        return CartItemSerializer(self._fetched_items(obj), many=True, context=self.context).data

    def get_items_count(self, obj) -> int:
        """Total units (header badge), not line count."""
        return sum(item.quantity for item in self._fetched_items(obj))

    def get_items_total_xaf(self, obj) -> int:
        return sum(item.artwork.price_xaf * item.quantity for item in self._fetched_items(obj))
