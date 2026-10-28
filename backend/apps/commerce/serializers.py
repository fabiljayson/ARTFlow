"""Commerce serializers (docs/api.md §6 — responses are flat, no success envelope)."""
from rest_framework import serializers

from apps.catalogue.models import ArtworkStatus
from apps.commerce.models import Cart, CartItem, Order, OrderItem


def artwork_primary_image_url(artwork, request=None) -> str | None:
    """Chemin de la vignette (thumb 480px) — partagé par le panier et le quote."""
    media = next((m for m in artwork.media.all() if m.is_primary and m.thumbnail_file), None)
    if media is None:
        media = next((m for m in artwork.media.all() if m.thumbnail_file), None)
    if media is None:
        return None
    path = f"/api/v1/catalog/artworks/{artwork.slug}/media/{media.pk}/thumb/"
    return request.build_absolute_uri(path) if request else path


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
        return artwork_primary_image_url(obj, self.context.get("request"))


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


class CartItemCreateSerializer(serializers.Serializer):
    artwork_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class CartItemPatchSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    """Corps de POST /checkout/ — aucun montant n'est accepté du client."""

    address_id = serializers.IntegerField()
    buyer_note = serializers.CharField(required=False, allow_blank=True, default="")


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


class OrderSummarySerializer(serializers.ModelSerializer):
    """GET /orders/ — une ligne par commande (items_count vient de l'annotate du queryset)."""

    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "reference",
            "status",
            "placed_at",
            "paid_at",
            "subtotal_items_xaf",
            "shipping_total_xaf",
            "grand_total_xaf",
            "items_count",
        ]


class OrderItemDetailSerializer(serializers.ModelSerializer):
    """Instantané de ligne (EF-9.1) — prix/commission figés, jamais recalculés."""

    artwork_id = serializers.IntegerField(read_only=True)
    artist = serializers.SerializerMethodField()
    primary_image_url = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "artwork_id",
            "title_snapshot",
            "unit_price_xaf",
            "quantity",
            "line_total_xaf",
            "commission_rate_bps",
            "commission_xaf",
            "artist_net_xaf",
            "artist",
            "primary_image_url",
        ]

    def get_artist(self, obj) -> dict:
        return {"id": obj.artist_id, "display_name": obj.artist.display_name}

    def get_primary_image_url(self, obj):
        return artwork_primary_image_url(obj.artwork, self.context.get("request"))


class OrderDetailSerializer(serializers.ModelSerializer):
    """GET /orders/{ref}/ + payload d'annulation — instantanés +/adresses/paiement."""

    items = OrderItemDetailSerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()
    shipments = serializers.SerializerMethodField()
    disputes = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "reference",
            "status",
            "placed_at",
            "paid_at",
            "cancelled_at",
            "subtotal_items_xaf",
            "shipping_total_xaf",
            "fees_total_xaf",
            "grand_total_xaf",
            "currency",
            "shipping_address_snapshot",
            "buyer_note",
            "items",
            "payment",
            "shipments",
            "disputes",
        ]

    def get_payment(self, obj):
        payment = obj.payments.order_by("-created_at").first()
        if payment is None:
            return None
        return {
            "provider": payment.provider,
            "status": payment.status,
            "external_reference": payment.external_reference,
            "failure_reason": payment.failure_reason,
        }

    def get_shipments(self, obj) -> list:
        return []  # expéditions arrivent en D4

    def get_disputes(self, obj) -> list:
        return []  # litiges arrivent en D4
