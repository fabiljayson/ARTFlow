"""MockPaymentGateway — signature HMAC réelle pour exercer la vérification (payments.md §5).

Le schéma exact des webhooks CamPay est à confirmer à la création du compte sandbox ;
ce schéma (`X-ArtFlow-Signature: sha256=<hex>`, HMAC-SHA256 du corps brut) fait foi
pendant toute la phase D3.
"""
import hashlib
import hmac
import uuid

from django.conf import settings

SIGNATURE_HEADER = "X-ArtFlow-Signature"

# Statuts « fournisseur » (style CamPay) → statuts internes Payment.Status.
MOCK_STATUS_MAP = {
    "SUCCESSFUL": "SUCCEEDED",
    "FAILED": "FAILED",
    "PENDING": "PENDING",
    "EXPIRED": "EXPIRED",
}


def sign(body: bytes) -> str:
    """Signature du corps brut : `sha256=<hex HMAC-SHA256(body, PAYMENT_WEBHOOK_SECRET)`."""
    digest = hmac.new(
        settings.PAYMENT_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return f"sha256={digest}"


def verify_signature(body: bytes, header: str | None) -> bool:
    """Comparaison constante du header fourni avec la signature recalculée du corps."""
    if not header or not header.startswith("sha256="):
        return False
    expected = sign(body)
    return hmac.compare_digest(expected, header)


def provider_to_internal(status: str) -> str:
    try:
        return MOCK_STATUS_MAP[status]
    except KeyError as exc:
        raise ValueError(f"Statut fournisseur inconnu : {status!r}") from exc


def initiate() -> str:
    """Référence externe unique par tentative de paiement."""
    return f"MOCK-{uuid.uuid4().hex}"


class MockPaymentGateway:
    """Passerelle simulée — aucune dépendance réseau (CI déterministe)."""

    def get_status(self, payment) -> str | None:
        """Statut simulé connu (format fournisseur) ou None si jamais tranché.

        Lu depuis `payment.raw_last_status["simulated_status"]`, écrit par le
        scénario `webhook_lost_then_late` du simulateur.
        """
        raw = payment.raw_last_status or {}
        status = raw.get("simulated_status")
        return status if status in MOCK_STATUS_MAP else None


def get_gateway() -> MockPaymentGateway:
    if settings.PAYMENT_PROVIDER != "mock":
        raise NotImplementedError(
            f"PAYMENT_PROVIDER={settings.PAYMENT_PROVIDER} non supporté en D3 (mock uniquement)."
        )
    return MockPaymentGateway()
