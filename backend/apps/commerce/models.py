"""Commerce models: cart, orders, reservations, payments, ledger (docs/database.md §3)."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone as django_timezone


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


class Order(models.Model):
    """Commande multi-vendeur — instantanés figés au checkout (docs/database.md §3)."""

    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT"
        PAID = "PAID"
        PROCESSING = "PROCESSING"
        SHIPPED = "SHIPPED"
        DELIVERED = "DELIVERED"
        CANCELLED = "CANCELLED"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
        REFUNDED = "REFUNDED"

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    reference = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PENDING_PAYMENT)
    subtotal_items_xaf = models.BigIntegerField(default=0)
    shipping_total_xaf = models.BigIntegerField(default=0)
    fees_total_xaf = models.BigIntegerField(default=0)
    grand_total_xaf = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="XAF")
    shipping_address_snapshot = models.JSONField(default=dict, blank=True)
    buyer_note = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True)
    request_fingerprint = models.CharField(max_length=64, db_index=True)
    placed_at = models.DateTimeField(default=django_timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["buyer", "-placed_at"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-placed_at"]

    def __str__(self):
        return f"{self.reference} ({self.status})"


class OrderItem(models.Model):
    """Ligne de commande — prix et commission figés, jamais recalculés (ADR-0006)."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    artwork = models.ForeignKey("catalogue.Artwork", on_delete=models.PROTECT)
    artist = models.ForeignKey(
        "artists.ArtistProfile", on_delete=models.PROTECT, related_name="order_items"
    )
    title_snapshot = models.CharField(max_length=200)
    unit_price_xaf = models.BigIntegerField()
    quantity = models.PositiveIntegerField()
    line_total_xaf = models.BigIntegerField()
    commission_rate_bps = models.PositiveIntegerField()
    commission_xaf = models.BigIntegerField()
    artist_net_xaf = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "artwork"], name="uniq_order_artwork"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="order_item_quantity_gte_1"),
        ]

    def __str__(self):
        return f"OrderItem#{self.pk} {self.title_snapshot} x{self.quantity}"


class StockReservation(models.Model):
    """Réservation temporaire de stock liée à une commande (TTL via platform_settings)."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        CONVERTED = "CONVERTED"
        RELEASED = "RELEASED"
        EXPIRED = "EXPIRED"

    artwork = models.ForeignKey("catalogue.Artwork", on_delete=models.PROTECT)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reservations")
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "expires_at"])]

    def __str__(self):
        return f"Reservation#{self.pk} art={self.artwork_id} x{self.quantity} {self.status}"


class Payment(models.Model):
    """Paiement d'une commande — statuts gérés par PaymentService (D3, docs/payments.md §2.2)."""

    class Provider(models.TextChoices):
        MOCK = "MOCK"
        CAMPAY = "CAMPAY"

    class Status(models.TextChoices):
        CREATED = "CREATED"
        PENDING = "PENDING"
        SUCCEEDED = "SUCCEEDED"
        FAILED = "FAILED"
        EXPIRED = "EXPIRED"
        CANCELLED = "CANCELLED"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.MOCK)
    provider_reference = models.CharField(max_length=120, null=True, blank=True)
    external_reference = models.CharField(max_length=64, unique=True)
    amount_xaf = models.BigIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CREATED)
    operator = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    initiated_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    raw_last_status = models.JSONField(null=True, blank=True)
    poll_count = models.PositiveIntegerField(default=0)  # tentatives de réconciliation (cron poll)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["order"])]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_reference"],
                name="uniq_provider_reference",
                condition=models.Q(provider_reference__isnull=False),
            ),
        ]

    def __str__(self):
        return f"Payment#{self.pk} {self.provider} {self.status} {self.amount_xaf}"


class CommissionLedger(models.Model):
    """Écriture append-only des commissions (docs/database.md §3, ADR-0006)."""

    class Kind(models.TextChoices):
        CHARGE = "CHARGE"
        REFUND_ADJUSTMENT = "REFUND_ADJUSTMENT"

    order_item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name="ledger_entries")
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="ledger_entries")
    artist = models.ForeignKey(
        "artists.ArtistProfile", on_delete=models.PROTECT, related_name="ledger_entries"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    gross_xaf = models.BigIntegerField()
    commission_xaf = models.BigIntegerField()
    artist_net_xaf = models.BigIntegerField()
    commission_rate_bps = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order_item", "kind"], name="uniq_ledger_item_kind"
            ),
        ]

    def __str__(self):
        return f"Ledger#{self.pk} {self.kind} item={self.order_item_id}"
