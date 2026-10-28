"""Commerce views — cart endpoints (docs/api.md §6)."""
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogue.models import Artwork, ArtworkStatus
from apps.commerce.models import Cart, CartItem
from apps.commerce.serializers import (
    CartItemCreateSerializer,
    CartItemPatchSerializer,
    CartItemSerializer,
    CartSerializer,
)
from apps.commerce.services import compute_quote


def get_or_create_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


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
