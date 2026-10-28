"""Payment endpoints — webhook fournisseur + initiation USSD simulée (payments.md §2.1)."""
import json

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.exceptions import InvalidSignature
from apps.payments import gateway, services
from apps.payments.serializers import InitiateSerializer, WebhookSerializer


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
