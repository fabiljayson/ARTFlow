"""Libère les réservations expirées et annule les commandes jamais payées (ADR-0005 : cron)."""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.commerce.models import Order, Payment, StockReservation


class Command(BaseCommand):
    help = "Expire les réservations de stock dépassées et annule les commandes impayées (cron : toutes les 5 min)."

    def handle(self, *args, **options):
        now = timezone.now()
        order_ids = list(
            Order.objects.filter(
                status=Order.Status.PENDING_PAYMENT,
                reservations__status=StockReservation.Status.ACTIVE,
                reservations__expires_at__lt=now,
            )
            .order_by("pk")
            .values_list("pk", flat=True)
            .distinct()
        )
        processed = 0
        for order_id in order_ids:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=order_id)
                if order.status != Order.Status.PENDING_PAYMENT:
                    continue
                # Re-sous le verrou : une autre exécution a pu traiter la commande entre-temps.
                expired = order.reservations.select_for_update().filter(
                    status=StockReservation.Status.ACTIVE, expires_at__lt=now
                )
                if not expired.exists():
                    continue
                expired.update(status=StockReservation.Status.EXPIRED, released_at=now)
                order.reservations.filter(status=StockReservation.Status.ACTIVE).update(
                    status=StockReservation.Status.RELEASED, released_at=now
                )
                order.payments.filter(
                    status__in=[Payment.Status.CREATED, Payment.Status.PENDING]
                ).update(status=Payment.Status.CANCELLED)
                order.status = Order.Status.CANCELLED
                order.cancelled_at = now
                order.save(update_fields=["status", "cancelled_at", "updated_at"])
                processed += 1
        self.stdout.write(f"{processed} commande(s) annulée(s), réservations libérées.")
