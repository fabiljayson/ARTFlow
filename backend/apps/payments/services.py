"""Payment state machine + external event ingestion (docs/payments.md §2)."""
import json
import logging

from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.commerce.models import Order, Payment
from apps.commerce.services import mark_paid, release_order_after_payment_failure
from apps.core.exceptions import Conflict
from apps.payments import gateway
from apps.payments.models import PaymentEvent

logger = logging.getLogger(__name__)

TRANSITIONS = {
    Payment.Status.CREATED: {Payment.Status.PENDING, Payment.Status.CANCELLED},
    Payment.Status.PENDING: {
        Payment.Status.SUCCEEDED,
        Payment.Status.FAILED,
        Payment.Status.EXPIRED,
        Payment.Status.CANCELLED,
    },
    Payment.Status.SUCCEEDED: set(),
    Payment.Status.FAILED: set(),
    Payment.Status.EXPIRED: set(),
    Payment.Status.CANCELLED: set(),
}


def apply_status(
    payment: Payment, new_status: str, *, failure_reason: str = ""
) -> Payment:
    """Applique une transition de paiement + ses effets de bord.

    Verrous order→payment déjà tenus par l'appelant (anti-deadlock, docs/payments.md §2.1).
    Re-reçu du même état = no-op ; transition illégale = Conflict + logger.warning.
    Effets de bord : SUCCEEDED → mark_paid (late si commande déjà annulée) ;
    FAILED/EXPIRED → libération de la commande ; CANCELLED → aucun (l'appelant gère).
    """
    if payment.status == new_status:
        return payment
    if new_status not in TRANSITIONS[payment.status]:
        logger.warning(
            "Transition paiement illégale: %s -> %s (payment=%s, order=%s)",
            payment.status,
            new_status,
            payment.pk,
            payment.order_id,
        )
        raise Conflict(
            f"Transition de paiement non autorisée : {payment.status} → {new_status}."
        )
    payment.status = new_status
    update_fields = ["status", "updated_at"]
    if new_status == Payment.Status.SUCCEEDED:
        payment.confirmed_at = timezone.now()
        update_fields.append("confirmed_at")
    elif new_status in (Payment.Status.FAILED, Payment.Status.EXPIRED):
        if failure_reason:
            payment.failure_reason = failure_reason
            update_fields.append("failure_reason")
    payment.save(update_fields=update_fields)
    order = payment.order
    if new_status == Payment.Status.SUCCEEDED:
        mark_paid(order, late=order.status == Order.Status.CANCELLED)
    elif new_status in (Payment.Status.FAILED, Payment.Status.EXPIRED):
        release_order_after_payment_failure(order)
    return payment


def mock_event_payload(
    payment: Payment, provider_status: str, *, failure_reason: str = ""
) -> dict:
    """Corps webhook mock pour `payment` — `event_id` stable pour que le rejeu soit détecté."""
    body = {
        "event_id": f"mock:{payment.provider_reference}:{provider_status}",
        "external_reference": payment.external_reference,
        "status": provider_status,
        "amount_xaf": payment.amount_xaf,
    }
    if failure_reason:
        body["failure_reason"] = failure_reason
    return body


def deliver(payload: dict) -> dict:
    """Livraison interne d'un webhook mock signé (simulateur — payments.md §5).

    Passe par la même `ingest_event` que le webhook HTTP : idempotence et verrous
    identiques, sans requête réseau.
    """
    raw = json.dumps(payload).encode()
    logger.debug("mock webhook signé : %s", gateway.sign(raw))
    return ingest_event(
        event_id=payload["event_id"],
        external_reference=payload["external_reference"],
        status=payload["status"],
        amount_xaf=payload["amount_xaf"],
        payload=payload,
        source="WEBHOOK",
    )


def initiate_payment(
    *, external_reference: str, user, phone: str, operator: str
) -> Payment:
    """Initie le paiement : CREATED → PENDING sous verrou order→payment.

    Idempotent (re-POST sur PENDING = retour courant) ; terminal/CANCELLED → Conflict ;
    commande d'un autre user ou référence inconnue → Http404 (pas de fuite d'existence).
    `provider_reference` est généré ici (aucun appel réseau — gateway mock).
    """
    found = (
        Payment.objects.select_related("order")
        .filter(external_reference=external_reference)
        .first()
    )
    if found is None or found.order.buyer_id != user.pk:
        raise Http404
    with transaction.atomic():
        Order.objects.select_for_update().get(pk=found.order_id)  # lock order d'abord
        payment = Payment.objects.select_for_update().get(pk=found.pk)
        if payment.status == Payment.Status.PENDING:
            return payment
        if payment.status != Payment.Status.CREATED:
            raise Conflict("Ce paiement ne peut plus être initié.")
        payment.phone = phone
        payment.operator = operator
        payment.provider_reference = gateway.initiate()
        payment.initiated_at = timezone.now()
        payment.save(
            update_fields=[
                "phone",
                "operator",
                "provider_reference",
                "initiated_at",
                "updated_at",
            ]
        )
        apply_status(payment, Payment.Status.PENDING)
        return payment


def ingest_event(
    *,
    event_id: str,
    external_reference: str,
    status: str,
    amount_xaf: int,
    payload: dict,
    source: str = "WEBHOOK",
) -> dict:
    """Ingeste un événement de paiement externe (webhook vérifié ou résultat de poll).

    Idempotent par event_id, sous verrous order→payment. Retour :
    {"event_id", "payment_status", "order_status", "duplicate"}.
    """
    found = (
        Payment.objects.select_related("order")
        .filter(external_reference=external_reference)
        .first()
    )
    if found is None:
        raise Http404
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=found.order_id)
        payment = Payment.objects.select_for_update().get(pk=found.pk)
        if PaymentEvent.objects.filter(event_id=event_id).exists():
            return {
                "event_id": event_id,
                "payment_status": payment.status,
                "order_status": order.status,
                "duplicate": True,
            }
        if int(amount_xaf) != payment.amount_xaf:
            logger.warning(
                "Montant webhook ≠ commande: %s != %s (payment=%s, order=%s)",
                amount_xaf,
                payment.amount_xaf,
                payment.pk,
                payment.order_id,
            )
            raise Conflict("Montant du webhook incompatible avec la commande.")
        try:
            internal = gateway.provider_to_internal(status)
        except ValueError as err:
            raise ValidationError({"status": "Statut fournisseur inconnu."}) from err
        # Transition (no-op si même état, Conflict si illégal) + effets de bord.
        apply_status(
            payment,
            internal,
            failure_reason=str(payload.get("failure_reason") or ""),
        )
        payment.raw_last_status = payload
        payment.save(update_fields=["raw_last_status", "updated_at"])
        PaymentEvent.objects.create(
            payment=payment,
            event_id=event_id,
            kind=(
                PaymentEvent.Kind.WEBHOOK_RECEIVED
                if source == "WEBHOOK"
                else PaymentEvent.Kind.STATUS_POLL
            ),
            status_after=payment.status,
            signature_valid=source == "WEBHOOK",
            payload=payload,
        )
        order.refresh_from_db()  # effets de bord écrits via une autre instance verrouillée
        return {
            "event_id": event_id,
            "payment_status": payment.status,
            "order_status": order.status,
            "duplicate": False,
        }
