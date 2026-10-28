"""Payments app models — external payment events (docs/payments.md §2.1.2, database.md §3)."""
from django.db import models

from apps.commerce.models import Payment


class PaymentEvent(models.Model):
    """Notification ou transition — `event_id` unique : tout rejeu est un no-op (EX-4).

    Table append-only (database.md §4.10) : jamais d'update ni de delete.
    """

    class Kind(models.TextChoices):
        WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"
        STATUS_POLL = "STATUS_POLL"
        STATE_CHANGE = "STATE_CHANGE"

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="events")
    event_id = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=30, choices=Kind.choices)
    status_after = models.CharField(max_length=12, choices=Payment.Status.choices)
    signature_valid = models.BooleanField(default=False)
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [models.Index(fields=["payment", "received_at"])]

    def __str__(self):
        return f"PaymentEvent#{self.pk} {self.event_id} {self.status_after}"
