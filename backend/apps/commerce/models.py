"""Commerce models: cart (docs/database.md §3). Orders/reservations arrive in D2+."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Cart(models.Model):
    """1 panier actif par user (OneToOne)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart#{self.pk} ({self.user_id})"


class CartItem(models.Model):
    """Ligne de panier — aucun prix stocké : relu au quote/checkout (docs/database.md)."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    artwork = models.ForeignKey("catalogue.Artwork", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "artwork"], name="uniq_cart_artwork"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="cart_item_quantity_gte_1"),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"CartItem#{self.pk} art={self.artwork_id} x{self.quantity}"

    @property
    def line_total_xaf(self) -> int:
        return self.artwork.price_xaf * self.quantity
