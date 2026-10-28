"""Commerce views — cart endpoints (docs/api.md §6)."""
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from apps.commerce.models import Cart
from apps.commerce.serializers import CartSerializer


def get_or_create_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class CartView(RetrieveAPIView):
    """GET /cart/ — panier courant, prix recalculés côté serveur."""

    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_object(self):
        return get_or_create_cart(self.request.user)


def validate_quantity(value) -> int:
    """Shared quantity guard for cart writes (D1)."""
    try:
        quantity = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"quantity": "Quantité invalide."}) from exc
    if quantity < 1:
        raise ValidationError({"quantity": "La quantité doit être au moins 1."})
    return quantity
