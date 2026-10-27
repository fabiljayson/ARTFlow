"""Custom authentication classes."""
from rest_framework.authentication import SessionAuthentication


class ArtflowSessionAuthentication(SessionAuthentication):
    """Session auth that advertises a WWW-Authenticate header so DRF returns 401
    (not 403) for unauthenticated requests — matches docs/api.md §11 contract."""

    def authenticate_header(self, request):
        return 'Session realm="api"'
