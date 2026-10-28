"""Payment endpoints — webhook fournisseur + initiation USSD simulée (payments.md §2.1)."""
import json

from django.conf import settings
from django.db import transaction
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.commerce.models import Order, Payment
from apps.core.exceptions import Conflict, InvalidSignature
from apps.payments import gateway, services
from apps.payments.serializers import (
    InitiateSerializer,
    SimulatePayloadSerializer,
    WebhookSerializer,
)

# Statut fournisseur livré par chaque scénario qui délivre (payments.md §5).
SIMULATE_PROVIDER_STATUS = {
    "success": "SUCCESSFUL",
    "fail": "FAILED",
    "duplicate_webhook": "SUCCESSFUL",
}


class PaymentWebhookView(APIView):
    """POST /api/v1/payments/webhook/ — événement signé du fournisseur.

    AllowAny (signature = authN), aucun throttle (le fournisseur ne doit jamais être
    throttled) ; corps brut vérifié avant parse (payments.md §2.1.1).
    """

    permission_classes = [AllowAny]
    throttle_classes = []

    def post(self, request):
        raw = request.body
        header = request.headers.get(gateway.SIGNATURE_HEADER)
        if not gateway.verify_signature(raw, header):
            raise InvalidSignature()
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as err:
            raise ValidationError({"detail": "Corps JSON invalide."}) from err
        incoming = WebhookSerializer(data=data)
        incoming.is_valid(raise_exception=True)
        result = services.ingest_event(
            event_id=incoming.validated_data["event_id"],
            external_reference=incoming.validated_data["external_reference"],
            status=incoming.validated_data["status"],
            amount_xaf=incoming.validated_data["amount_xaf"],
            payload=dict(incoming.validated_data),
            source="WEBHOOK",
        )
        return Response(result, status=status.HTTP_200_OK)


class InitiatePaymentView(APIView):
    """POST /api/v1/payments/{external_reference}/initiate/ — démarrage de la tentative.

    IsAuthenticated + throttle `payment-initiate` (30/h/user, docs/api.md §1).
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment-initiate"

    def post(self, request, external_reference):
        incoming = InitiateSerializer(data=request.data)
        incoming.is_valid(raise_exception=True)
        payment = services.initiate_payment(
            external_reference=external_reference,
            user=request.user,
            phone=incoming.validated_data["phone"],
            operator=incoming.validated_data["operator"],
        )
        return Response(
            {
                "external_reference": payment.external_reference,
                "status": payment.status,
                "provider_reference": payment.provider_reference,
                "initiated_at": payment.initiated_at,
            },
            status=status.HTTP_200_OK,
        )


class SimulatePaymentView(APIView):
    """POST /api/v1/payments/dev/simulate/ — scénarios sandbox (payments.md §5).

    404 si `PAYMENT_PROVIDER != "mock"` (le simulateur n'existe que pour le mock) ;
    propriétaire requis ; paiement `PENDING` sinon 409. Les événements « livrés »
    passent par la même `ingest_event` signée que le webhook HTTP.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if settings.PAYMENT_PROVIDER != "mock":
            raise Http404
        incoming = SimulatePayloadSerializer(data=request.data)
        incoming.is_valid(raise_exception=True)
        reference = incoming.validated_data["external_reference"]
        scenario = incoming.validated_data["scenario"]
        found = (
            Payment.objects.select_related("order")
            .filter(external_reference=reference)
            .first()
        )
        if found is None or found.order.buyer_id != request.user.pk:
            raise Http404
        with transaction.atomic():
            Order.objects.select_for_update().get(pk=found.order_id)
            payment = Payment.objects.select_for_update().get(pk=found.pk)
            if payment.status != Payment.Status.PENDING:
                raise Conflict("Le paiement n'est pas en attente de confirmation.")
            if scenario == "timeout":
                return Response({"delivered": 0})
            if scenario == "webhook_lost_then_late":
                payment.raw_last_status = {
                    **(payment.raw_last_status or {}),
                    "simulated_status": "SUCCESSFUL",
                }
                payment.save(update_fields=["raw_last_status", "updated_at"])
                return Response({"delivered": 0})
            provider_status = SIMULATE_PROVIDER_STATUS[scenario]
            payload = services.mock_event_payload(
                payment,
                provider_status,
                failure_reason=(
                    "Échec simulé (scénario fail)."
                    if scenario == "fail"
                    else ""
                ),
            )
            if scenario == "duplicate_webhook":
                services.deliver(payload)
                second = services.deliver(payload)
                return Response(
                    {"delivered": 2, "duplicates": 1 if second["duplicate"] else 0}
                )
            services.deliver(payload)
            return Response({"delivered": 1})
