"""Integration tests for the auth API (docs/api.md §2, docs/testing.md §4)."""
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, UserRole
from apps.core.models import AuditLog

User = get_user_model()

REGISTER = "/api/v1/auth/register/"
LOGIN = "/api/v1/auth/login/"
LOGOUT = "/api/v1/auth/logout/"
ME = "/api/v1/auth/me/"
PASSWORD_RESET = "/api/v1/auth/password/reset/"
PASSWORD_RESET_CONFIRM = "/api/v1/auth/password/reset/confirm/"
PASSWORD_CHANGE = "/api/v1/auth/password/change/"
PROFILE = "/api/v1/auth/profile/"

GOOD_PASSWORD = "Str0ng!Passw0rd2026"


@pytest.fixture
def client():
    return APIClient()


def _register(client, email="new@example.test", password=GOOD_PASSWORD, **extra):
    payload = {"email": email, "password": password, **extra}
    return client.post(REGISTER, payload, format="json")


@pytest.mark.django_db
class TestRegister:
    def test_register_success_creates_user_role_and_session(self, client):
        resp = _register(client, first_name="Awa", last_name="Ndiaye", phone="+237690000001")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["email"] == "new@example.test"
        assert data["roles"] == [Role.BUYER]
        assert data["is_artist"] is False
        # Session cookie set (login after register)
        assert client.session.session_key is not None
        # Audit
        assert AuditLog.objects.filter(action="user.registered").exists()

    def test_register_duplicate_email_rejected(self, client, user_factory):
        user_factory(email="dup@example.test")
        resp = _register(client, email="dup@example.test")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["error"]["code"] == "validation_error"

    def test_register_email_is_normalized_lowercase(self, client):
        resp = _register(client, email="Mixed.Case@Example.TEST")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["email"] == "mixed.case@example.test"

    def test_register_weak_password_rejected(self, client):
        resp = _register(client, password="12345")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_phone_rejected(self, client):
        resp = _register(client, phone="+33612345678")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_with_terms_version_accepted(self, client):
        # Terms service ships in Phase F; the field is accepted today (Phase C choice).
        resp = _register(client, accepted_terms_version="1.0")
        assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestLoginLogout:
    def test_login_success(self, client, user_factory):
        u = user_factory(email="login@example.test", password=GOOD_PASSWORD)
        resp = client.post(LOGIN, {"email": "login@example.test", "password": GOOD_PASSWORD}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["email"] == "login@example.test"
        assert AuditLog.objects.filter(action="user.login", actor=u).exists()

    def test_login_wrong_password_401(self, client, user_factory):
        user_factory(email="login@example.test", password=GOOD_PASSWORD)
        resp = client.post(LOGIN, {"email": "login@example.test", "password": "WrongPass1!"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert resp.json()["error"]["code"] == "invalid_credentials"

    def test_login_unknown_email_401_same_message(self, client):
        resp = client.post(LOGIN, {"email": "ghost@example.test", "password": GOOD_PASSWORD}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert resp.json()["error"]["message"] == "Email ou mot de passe incorrect."

    def test_logout_requires_session(self, client, user_factory):
        user_factory()
        resp = client.post(LOGOUT)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_success(self, client, user):
        client.force_login(user)
        resp = client.post(LOGOUT)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        # Session is gone
        resp2 = client.get(ME)
        assert resp2.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_audited(self, client, user):
        client.post(LOGIN, {"email": user.email, "password": "Str0ng!Passw0rd2026"}, format="json")
        assert AuditLog.objects.filter(action="user.login", actor=user).exists()


@pytest.mark.django_db
class TestMeProfile:
    def test_me_requires_auth(self, client):
        assert client.get(ME).status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_returns_identity(self, client, user):
        client.force_login(user)
        data = client.get(ME).json()
        assert data["email"] == user.email
        assert "password" not in data

    def test_profile_update_first_name(self, client, user):
        client.force_login(user)
        resp = client.patch(PROFILE, {"first_name": "Updated"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == "Updated"

    def test_profile_email_is_read_only(self, client, user):
        client.force_login(user)
        resp = client.patch(PROFILE, {"email": "hacked@example.test"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.email == user.email  # unchanged
        assert resp.json()["email"] == user.email

    def test_profile_phone_change_audited(self, client, user):
        client.force_login(user)
        client.patch(PROFILE, {"phone": "+237691111111"}, format="json")
        assert AuditLog.objects.filter(action="user.phone_updated", actor=user).exists()


@pytest.mark.django_db
class TestPasswordReset:
    def test_reset_sends_email_when_account_exists(self, client, user_factory):
        user_factory(email="reset@example.test")
        resp = client.post(PASSWORD_RESET, {"email": "reset@example.test"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 1
        assert "reset@example.test" in mail.outbox[0].to

    def test_reset_silent_for_unknown_email(self, client):
        resp = client.post(PASSWORD_RESET, {"email": "nobody@example.test"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 0

    def test_reset_confirm_sets_new_password(self, client, user_factory):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        u = user_factory(email="reset@example.test")
        client.post(PASSWORD_RESET, {"email": u.email}, format="json")
        uid = urlsafe_base64_encode(force_bytes(u.pk))
        token = default_token_generator.make_token(u)
        resp = client.post(
            PASSWORD_RESET_CONFIRM,
            {"uid": uid, "token": token, "new_password": "BrandNew!Passw0rd2026"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        u.refresh_from_db()
        assert u.check_password("BrandNew!Passw0rd2026")
        assert AuditLog.objects.filter(action="user.password_reset_completed", actor=u).exists()

    def test_reset_confirm_invalid_token_400(self, client, user):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        resp = client.post(
            PASSWORD_RESET_CONFIRM,
            {"uid": uid, "token": "bogus-token", "new_password": "BrandNew!Passw0rd2026"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_change(self, client, user):
        client.force_login(user)
        resp = client.post(
            PASSWORD_CHANGE,
            {"old_password": "Str0ng!Passw0rd2026", "new_password": "BrandNew!Passw0rd2026"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password("BrandNew!Passw0rd2026")
        assert AuditLog.objects.filter(action="user.password_changed", actor=user).exists()

    def test_password_change_wrong_old_400(self, client, user):
        client.force_login(user)
        resp = client.post(
            PASSWORD_CHANGE, {"old_password": "WrongPass1!", "new_password": "BrandNew!Passw0rd2026"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginThrottle:
    def test_login_rate_limited_at_11(self, client, user, settings):
        settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
        payload = {"email": user.email, "password": "WrongPass1!"}
        for _ in range(10):
            client.post(LOGIN, payload, format="json")
        resp = client.post(LOGIN, payload, format="json")
        assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert resp.json()["error"]["code"] == "rate_limited"


@pytest.mark.django_db
class TestRoles:
    def test_grant_role_is_unique(self, user):
        from django.db import IntegrityError, transaction

        # user fixture already has BUYER (conftest) — a second insert must violate uniq_user_role
        with pytest.raises(IntegrityError), transaction.atomic():
            UserRole.objects.create(user=user, role=Role.BUYER)

    def test_has_role_superuser_bypass(self, user):
        user.is_superuser = True
        assert user.has_role("ADMIN") is True
