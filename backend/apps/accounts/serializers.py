"""Account serializers."""
from django.contrib.auth import password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers

from apps.accounts.models import CM_PHONE_REGEX, Address, User


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    phone = serializers.CharField(
        max_length=15, required=False, allow_null=True, default=None, validators=[CM_PHONE_REGEX]
    )
    # Accepted for API contract compliance (docs/api.md §2). Terms themselves ship in Phase F;
    # until published versions exist, the value is accepted and not validated (choice: Phase C).
    accepted_terms_version = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return email

    def validate_password(self, value):
        user = User(email=self.initial_data.get("email", ""))
        password_validation.validate_password(value, user=user)
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(trim_whitespace=False)

    def validate_email(self, value):
        return value.lower()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone", "created_at"]
        read_only_fields = ["id", "email", "created_at"]


class MeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    is_artist = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "phone",
            "roles", "is_artist", "email_verified_at", "created_at",
        ]
        read_only_fields = fields

    def get_roles(self, obj):
        return list(obj.roles.values_list("role", flat=True))

    def get_is_artist(self, obj):
        return obj.has_role("ARTIST")


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id", "label", "recipient_name", "line1", "line2",
            "city", "region", "phone", "is_default", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.lower()
        self.user = User.objects.filter(email__iexact=email, is_active=True).first()
        return email

    def save(self, request=None):
        # Always 200 even when unknown (no account enumeration).
        if getattr(self, "user", None) is None:
            return
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        reset_url = f"/mot-de-passe/reinitialiser?uid={uid}&token={token}"
        send_mail(
            "Réinitialisation de votre mot de passe ArtFlow",
            f"Utilisez ce lien pour choisir un nouveau mot de passe : {reset_url}",
            None,
            [self.user.email],
        )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        try:
            pk = urlsafe_base64_decode(attrs["uid"]).decode()
            user = User.objects.get(pk=pk, is_active=True)
        except (ValueError, TypeError, User.DoesNotExist):
            raise serializers.ValidationError({"uid": "Lien de réinitialisation invalide."}) from None
        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "Jeton expiré ou invalide."})
        password_validation.validate_password(attrs["new_password"], user=user)
        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value

    def validate_new_password(self, value):
        password_validation.validate_password(value, user=self.context["request"].user)
        return value

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user
