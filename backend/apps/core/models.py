"""Shared core models."""
from django.conf import settings
from django.db import models


class PlatformSettings(models.Model):
    """Singleton platform parameters (docs/database.md §5). Admin-editable, audited."""

    commission_rate_bps = models.PositiveIntegerField(default=1000)  # 10 %
    reservation_ttl_minutes = models.PositiveIntegerField(default=30)
    moderation_reprice_threshold_pct = models.PositiveIntegerField(default=20)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Platform settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        # enforce singleton
        if self.__class__.objects.count() > 1:
            self.__class__.objects.exclude(pk=1).delete()

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AuditLog(models.Model):
    """Append-only audit trail. Never update or delete rows (see docs/database.md §7)."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="audit_events"
    )
    actor_role = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=60)
    object_type = models.CharField(max_length=40)
    object_id = models.CharField(max_length=40)
    metadata = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.object_type}#{self.object_id}"
