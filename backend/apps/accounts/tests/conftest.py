"""Fixtures specific to the accounts app."""
import pytest

from apps.accounts.models import Address


@pytest.fixture
def address(user):
    return Address.objects.create(
        user=user,
        label="Domicile",
        recipient_name="Test User",
        line1="123 Rue Exemple",
        city="Yaoundé",
        phone=user.phone or "+237690000000",
        is_default=True,
    )
