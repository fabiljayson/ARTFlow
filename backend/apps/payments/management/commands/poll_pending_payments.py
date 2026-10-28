"""Réconciliation des paiements PENDING — poll du fournisseur simulé (payments.md §2.1.3)."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.commerce.models import Payment
from apps.payments import gateway, services


class Command(BaseCommand):
    help = (
        "Interroge la passerelle pour les paiements PENDING de plus de 60 s "
        "(cron : toutes les 2 min) et ingère le résultat."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        candidates = Payment.objects.filter(
            status=Payment.Status.PENDING,
            provider_reference__isnull=False,
            initiated_at__lt=now - timedelta(seconds=60),
            poll_count__lt=20,
        ).order_by("pk")
        gw = gateway.get_gateway()
        reconciled = 0
        for payment in candidates:
            # Compteur écrit avant livraison : une livraison qui échoue reste comptée.
            payment.poll_count += 1
            payment.save(update_fields=["poll_count", "updated_at"])
            provider_status = gw.get_status(payment)
            if provider_status is None:
                continue
            payload = services.mock_event_payload(payment, provider_status)
            services.ingest_event(
                event_id=payload["event_id"],
                external_reference=payload["external_reference"],
                status=payload["status"],
                amount_xaf=payload["amount_xaf"],
                payload=payload,
                source="POLL",
            )
            reconciled += 1
        self.stdout.write(f"{reconciled} paiement(s) réconcilié(s).")
