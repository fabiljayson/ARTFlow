"""Model-level tests: phone validation, role helpers, address default rule."""
import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import CM_PHONE_REGEX, Address, Role


@pytest.mark.django_db
class TestPhoneValidator:
    @pytest.mark.parametrize(
        "phone",
        ["+237690000001", "+237233445566", "+237671234567"],
    )
    def test_valid_cm_numbers(self, phone):
        CM_PHONE_REGEX(phone)

    @pytest.mark.parametrize(
        "phone",
        ["+33612345678", "0612345678", "+23769000001", "+2371234567890"],
    )
    def test_invalid_numbers(self, phone):
        with pytest.raises(ValidationError):
            CM_PHONE_REGEX(phone)


@pytest.mark.django_db
class TestUserHelpers:
    def test_has_role(self, user):
        assert user.has_role("BUYER") is True
        assert user.has_role("ARTIST") is False

    def test_primary_role_buyer(self, user):
        assert user.primary_role() == Role.BUYER

    def test_email_lowercased_on_save(self, user_factory):
        u = user_factory(email="UPPER@Example.test")
        u.refresh_from_db()
        assert u.email == "upper@example.test"


@pytest.mark.django_db
class TestAddress:
    def test_default_demotes_previous(self, user):
        a1 = Address.objects.create(
            user=user, label="A", recipient_name="T", line1="L", city="Yaoundé", phone=user.phone, is_default=True
        )
        a2 = Address.objects.create(
            user=user, label="B", recipient_name="T", line1="L", city="Douala", phone="+237691234567", is_default=True
        )
        a1.refresh_from_db()
        assert a1.is_default is False
        assert a2.is_default is True
