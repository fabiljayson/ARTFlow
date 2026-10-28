"""Payment API serializers (docs/payments.md §2.1, plan D3 Task 3)."""
from rest_framework import serializers

from apps.payments.gateway import MOCK_STATUS_MAP


class WebhookSerializer(serializers.Serializer):
    """Corps d'un webhook fournisseur (schéma mock signé, payments.md §2.1.1)."""

    event_id = serializers.CharField(max_length=120)
    external_reference = serializers.CharField(max_length=64)
    status = serializers.ChoiceField(choices=tuple(MOCK_STATUS_MAP))
    amount_xaf = serializers.IntegerField(min_value=0)
    failure_reason = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )


class InitiateSerializer(serializers.Serializer):
    """Corps d'initiation USSD simulée : {phone, operator} (payments.md §2.1.1)."""

    phone = serializers.RegexField(regex=r"^\+237[6-9]\d{8}$")
    operator = serializers.ChoiceField(choices=("MTN", "ORANGE"))
