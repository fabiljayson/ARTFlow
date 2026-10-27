"""Identity models: User, roles, addresses (docs/database.md §1)."""
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

CM_PHONE_REGEX = RegexValidator(
    regex=r"^\+237[2-9]\d{8}$",
    message="Numéro camerounais attendu au format +237XXXXXXXX.",
)


class Role(models.TextChoices):
    BUYER = "BUYER", "Acheteur"
    ARTIST = "ARTIST", "Artiste"
    MODERATOR = "MODERATOR", "Modérateur"
    ADMIN = "ADMIN", "Administrateur"
    FINANCE = "FINANCE", "Opérations financières"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("L'email est obligatoire.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True:
            raise ValueError("Le superuser doit avoir is_staff et is_superuser à True.")
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Email as identifier. Roles live in UserRole (many-to-many with grant trace)."""

    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(
        max_length=15, validators=[CM_PHONE_REGEX], null=True, blank=True, unique=True
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Django admin access only
    email_verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email"])]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email).lower()
        super().save(*args, **kwargs)

    # --- role helpers -----------------------------------------------------
    def has_role(self, role: str) -> bool:
        if self.is_superuser:
            return True
        return self.roles.filter(role=role).exists()

    def has_any_role(self, *roles: str) -> bool:
        if self.is_superuser:
            return True
        return self.roles.filter(role__in=roles).exists()

    def primary_role(self) -> str:
        if self.is_superuser:
            return Role.ADMIN
        return self.roles.order_by("created_at").values_list("role", flat=True).first() or Role.BUYER


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role = models.CharField(max_length=20, choices=Role.choices)
    granted_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="granted_roles"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="uniq_user_role"),
        ]

    def __str__(self):
        return f"{self.user.email}:{self.role}"


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=40)
    recipient_name = models.CharField(max_length=120)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80)
    region = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=15, validators=[CM_PHONE_REGEX])
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]
        indexes = [models.Index(fields=["user", "is_default"])]

    def __str__(self):
        return f"{self.label} — {self.city}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            (
                Address.objects.filter(user=self.user, is_default=True)
                .exclude(pk=self.pk)
                .update(is_default=False)
            )
