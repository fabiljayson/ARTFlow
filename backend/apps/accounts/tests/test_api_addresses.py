"""Address CRUD tests — owner isolation (docs/api.md §2, EX-5)."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Address

LIST = "/api/v1/auth/addresses/"


def detail(pk):
    return f"{LIST}{pk}/"


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestAddresses:
    def test_list_only_own_addresses(self, client, user, other_user, address):
        Address.objects.create(
            user=other_user,
            label="Autre",
            recipient_name="Autre",
            line1="Chez l'autre",
            city="Douala",
            phone=other_user.phone,
        )
        client.force_login(user)
        data = client.get(LIST).json()
        assert data["count"] == 1
        assert data["results"][0]["label"] == "Domicile"

    def test_create_address(self, client, user):
        client.force_login(user)
        resp = client.post(
            LIST,
            {
                "label": "Bureau",
                "recipient_name": "Test User",
                "line1": "Avenue Kennedy",
                "city": "Douala",
                "phone": "+237691234567",
                "is_default": False,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert Address.objects.filter(user=user, label="Bureau").exists()

    def test_update_other_user_address_404(self, client, user, other_user, address):
        # address belongs to `user`; other_user must not see it
        client.force_login(other_user)
        resp = client.patch(detail(address.pk), {"label": "Piraté"}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_other_user_address_404(self, client, user, other_user, address):
        client.force_login(other_user)
        resp = client.delete(detail(address.pk))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert Address.objects.filter(pk=address.pk).exists()

    def test_default_address_is_exclusive(self, client, user, address):
        client.force_login(user)
        resp = client.post(
            LIST,
            {
                "label": "Domicile 2",
                "recipient_name": "Test User",
                "line1": "Autre rue",
                "city": "Yaoundé",
                "phone": "+237691234568",
                "is_default": True,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        defaults = Address.objects.filter(user=user, is_default=True)
        assert defaults.count() == 1
        assert defaults.first().label == "Domicile 2"

    def test_invalid_phone_rejected(self, client, user):
        client.force_login(user)
        resp = client.post(
            LIST,
            {
                "label": "Maison",
                "recipient_name": "Test",
                "line1": "Rue 1",
                "city": "Yaoundé",
                "phone": "0612345678",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_requires_auth(self, client, address):
        assert client.get(LIST).status_code == status.HTTP_401_UNAUTHORIZED
