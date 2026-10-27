"""Shared fixtures: user factory (each test creates its own users — docs/testing.md)."""
import factory
import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Address, Role, UserRole

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.test")
    first_name = "Test"
    last_name = "User"
    password = factory.PostGenerationMethodCall("set_password", "Str0ng!Passw0rd2026")
    phone = factory.Sequence(lambda n: f"+2376{n:08d}")

    @factory.post_generation
    def with_buyer_role(self, create, extracted, **kwargs):
        if create and extracted is not False:
            UserRole.objects.get_or_create(user=self, role=Role.BUYER)


@pytest.fixture
def user_factory():
    return UserFactory


@pytest.fixture
def user(user_factory):
    return user_factory()


@pytest.fixture
def other_user(user_factory):
    return user_factory()


@pytest.fixture
def admin_user(user_factory):
    u = user_factory()
    UserRole.objects.create(user=u, role=Role.ADMIN)
    return u


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
