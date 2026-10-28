"""Commerce views — cart + checkout endpoints (docs/api.md §6)."""
from django.db.models import Prefetch, Sum
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import Address
from apps.catalogue.models import Artwork, ArtworkStatus
from apps.commerce.models import CartItem, Order, OrderItem
from apps.commerce.serializers import (
    CartItemCreateSerializer,
    CartItemPatchSerializer,
    CartItemSerializer,
    CartSerializer,
    CheckoutSerializer,
    OrderDetailSerializer,
    OrderSummarySerializer,
)
from apps.commerce.services import (
    cancel_order,
    compute_fingerprint,
    compute_quote,
    create_checkout,
    get_or_create_cart,
)


def validate_quantity(value) -> int:
    """Shared quantity guard for cart writes (D1)."""
    try:
        quantity = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"quantity": "Quantité invalide."}) from exc
    if quantity < 1:
        raise ValidationError({"quantity": "La quantité doit être au moins 1."})
    return quantity


def get_published_artwork(artwork_id) -> Artwork:
    """Only PUBLISHED artworks can enter a cart — same visibility as the catalogue."""
    artwork = Artwork.objects.filter(pk=artwork_id, status=ArtworkStatus.PUBLISHED).first()
    if artwork is None:
        raise Http404
    return artwork


def check_stock(artwork: Artwork, quantity: int) -> None:
    if quantity > artwork.stock_quantity:
        raise ValidationError(
            {"quantity": f"Stock insuffisant : il reste {artwork.stock_quantity} exemplaire(s)."}
        )


class CartView(APIView):
    """GET /cart/ — panier courant, prix recalculés côté serveur."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_or_create_cart(request.user)
        return Response(CartSerializer(cart, context={"request": request}).data)


class CartItemCreateView(APIView):
    """POST /cart/items/ — ajoute une ligne, ou incrémente si déjà présente."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        artwork = get_published_artwork(serializer.validated_data["artwork_id"])
        quantity = validate_quantity(serializer.validated_data["quantity"])
        check_stock(artwork, quantity)

        cart = get_or_create_cart(request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart, artwork=artwork, defaults={"quantity": quantity}
        )
        if not created:
            new_quantity = item.quantity + quantity
            check_stock(artwork, new_quantity)
            item.quantity = new_quantity
            item.save(update_fields=["quantity"])
        return Response(
            CartItemSerializer(item, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemDetailView(APIView):
    """PATCH/DELETE /cart/items/{id}/ — owner scope: 404 si la ligne n'est pas au panier du user."""

    permission_classes = [IsAuthenticated]

    def _get_item(self, request, pk) -> CartItem:
        item = CartItem.objects.filter(pk=pk, cart__user=request.user).select_related(
            "artwork", "artwork__artist"
        ).first()
        if item is None:
            raise Http404
        return item

    def patch(self, request, pk):
        item = self._get_item(request, pk)
        serializer = CartItemPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = validate_quantity(serializer.validated_data["quantity"])
        check_stock(item.artwork, quantity)
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        return Response(CartItemSerializer(item, context={"request": request}).data)

    def delete(self, request, pk):
        item = self._get_item(request, pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuoteView(APIView):
    """POST /checkout/quote/ — simulation des totaux, toujours recalculée côté serveur.

    Le corps de la requête est accepté mais ignoré : aucun montant client n'est de confiance.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_or_create_cart(request.user)
        return Response(compute_quote(cart, request=request))


class CheckoutView(APIView):
    """POST /checkout/ — commande idempotente (docs/api.md §1 Idempotency-Key, §6)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "checkout"

    def post(self, request):
        idempotency_key = (request.headers.get("Idempotency-Key") or "").strip()
        if not idempotency_key:
            raise ValidationError({"idempotency_key": "En-tête « Idempotency-Key » requis."})
        if len(idempotency_key) > 64:
            raise ValidationError({"idempotency_key": "Clé trop longue (64 caractères max)."})

        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = Address.objects.filter(
            pk=serializer.validated_data["address_id"], user=request.user
        ).first()
        if address is None:
            raise Http404

        payload, created = create_checkout(
            request.user,
            idempotency_key=idempotency_key,
            address=address,
            buyer_note=serializer.validated_data.get("buyer_note", ""),
            fingerprint=compute_fingerprint(request.data),
        )
        return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class OrderListView(ListAPIView):
    """GET /orders/ — mes commandes (paginées, scope buyer)."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrderSummarySerializer

    def get_queryset(self):
        return Order.objects.filter(buyer=self.request.user).annotate(
            items_count=Sum("items__quantity")
        )


def _order_queryset():
    return Order.objects.prefetch_related(
        Prefetch(
            "items",
            queryset=OrderItem.objects.select_related("artwork", "artwork__artist").prefetch_related(
                "artwork__media"
            ),
        ),
        "payments",
    )


class OrderDetailView(RetrieveAPIView):
    """GET /orders/{reference}/ — instantanés figés, owner scope (404 sinon)."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer
    lookup_field = "reference"

    def get_queryset(self):
        return _order_queryset().filter(buyer=self.request.user)


class OrderCancelView(APIView):
    """POST /orders/{reference}/cancel/ — PENDING_PAYMENT uniquement (sinon 409)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, reference):
        order = Order.objects.filter(reference=reference, buyer=request.user).first()
        if order is None:
            raise Http404
        cancel_order(order)
        fresh = _order_queryset().get(pk=order.pk)
        return Response(OrderDetailSerializer(fresh, context={"request": request}).data)
