"""
Stable API exception handler.

Wraps DRF exceptions in the envelope documented in docs/api.md:
{"error": {"code": "...", "message": "...", "details": {...}}}
"""
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class IdempotencyConflict(APIException):
    """Clé Idempotency-Key réutilisée avec un corps différent ou appartenant à un autre user.

    Le code métier `idempotency_conflict` est porté par l'attribut `artflow_code`
    (docs/api.md §11).
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Clé Idempotency-Key déjà utilisée avec un corps différent."
    artflow_code = "idempotency_conflict"


class Conflict(APIException):
    """Transition d'état illégale — code `conflict` (docs/api.md §11)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Transition non autorisée."


class InvalidSignature(APIException):
    """Signature webhook invalide ou absente — code `invalid_signature` (docs/api.md §11)."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Signature de webhook invalide."
    artflow_code = "invalid_signature"


def api_exception_handler(exc, context):
    """Convert DRF/Django exceptions to the ArtFlow error envelope."""
    if isinstance(exc, Http404):
        exc = APIException(detail="Ressource introuvable.")
        exc.status_code = status.HTTP_404_NOT_FOUND
        code = "not_found"
    elif isinstance(exc, DjangoPermissionDenied):
        exc = APIException(detail="Accès refusé.")
        exc.status_code = status.HTTP_403_FORBIDDEN
        code = "permission_denied"
    else:
        response = exception_handler(exc, context)
        if response is None:
            return None
        code = getattr(exc, "artflow_code", None) or _status_to_code(response.status_code)
        # Normalize detail to message + details
        detail = response.data
        if isinstance(detail, dict) and "detail" in detail:
            message = str(detail.pop("detail"))
            response.data = {"error": {"code": code, "message": message, "details": detail or {}}}
            return response
        response.data = {
            "error": {
                "code": code,
                "message": "Erreur de validation.",
                "details": detail if isinstance(detail, dict) else {},
            }
        }
        return response

    return Response(
        {"error": {"code": code, "message": str(exc.detail), "details": {}}},
        status=exc.status_code,
    )


def _status_to_code(status_code: int) -> str:
    mapping = {
        status.HTTP_400_BAD_REQUEST: "validation_error",
        status.HTTP_401_UNAUTHORIZED: "unauthenticated",
        status.HTTP_403_FORBIDDEN: "permission_denied",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_409_CONFLICT: "conflict",
        status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
        status.HTTP_502_BAD_GATEWAY: "provider_error",
        status.HTTP_503_SERVICE_UNAVAILABLE: "provider_error",
    }
    return mapping.get(status_code, "error")
