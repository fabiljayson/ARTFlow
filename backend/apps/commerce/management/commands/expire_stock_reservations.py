"""Libère les réservations expirées et annule les commandes jamais payées (ADR-0005 : cron).

D3 v2 (payments.md §2.3) :
- partie 1 — commandes impayées : réservations expirées, paiements encore `CREATED`
  annulés via `apply_status` ; un paiement `PENDING` est laissé au joueur/poll ;
- partie 2 — tentatives `PENDING` plus vieilles que TTL + 15 min → `EXPIRED`
  (effet de bord : libération de la commande si elle est toujours impayée).
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.commerce.models import Order, Payment, StockReservation
from apps.core.models import PlatformSettings
from apps.payments.services import apply_status


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
                # Paiements jamais initiés → annulés ; un PENDING appartient au joueur/poll.
                for payment in order.payments.select_for_update().filter(
                    status=Payment.Status.CREATED
                ):
                    apply_status(payment, Payment.Status.CANCELLED)
                order.status = Order.Status.CANCELLED
                order.cancelled_at = now
                order.save(update_fields=["status", "cancelled_at", "updated_at"])
                processed += 1

        # Partie 2 : tentatives d'initiation trop vieilles → EXPIRED (marge 15 min).
        ttl = PlatformSettings.get().reservation_ttl_minutes
        cutoff = now - timedelta(minutes=ttl + 15)
        stale_ids = list(
            Payment.objects.filter(
                status=Payment.Status.PENDING,
                initiated_at__lt=cutoff,
            )
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        expired_payments = 0
        for payment_id in stale_ids:
            with transaction.atomic():
                found = Payment.objects.select_related("order").get(pk=payment_id)
                Order.objects.select_for_update().get(pk=found.order_id)
                payment = Payment.objects.select_for_update().get(pk=payment_id)
                if payment.status != Payment.Status.PENDING:
                    continue
                apply_status(
                    payment,
                    Payment.Status.EXPIRED,
                    failure_reason="Délai de confirmation dépassé.",
                )
                expired_payments += 1
        self.stdout.write(
            f"{processed} commande(s) annulée(s), réservations libérées, "
            f"{expired_payments} paiement(s) expiré(s)."
        )
