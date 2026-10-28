from django.contrib import admin

from apps.payments.models import PaymentEvent


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "payment", "kind", "status_after", "signature_valid", "received_at")
    list_filter = ("kind", "status_after")
    readonly_fields = [f.name for f in PaymentEvent._meta.fields]

    def has_change_permission(self, request, obj=None):
        return False  # append-only (database.md §4.10)
