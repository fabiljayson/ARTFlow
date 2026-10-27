"""Health check endpoint."""
from django.db import connection
from django.db.utils import OperationalError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Liveness + readiness: DB connectivity included."""
    db_ok = True
    try:
        connection.ensure_connection()
    except OperationalError:
        db_ok = False

    payload = {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}
    code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(payload, status=code)
