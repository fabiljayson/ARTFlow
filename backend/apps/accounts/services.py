"""Account services — transactional registration and role grants."""
from django.db import transaction

from apps.accounts.models import Role, User, UserRole
from apps.core.audit import log_audit


def register_user(*, email: str, password: str, first_name: str = "", last_name: str = "",
                  phone: str | None = None, request=None) -> User:
    """Create the user, grant BUYER, audit. Phone uniqueness raises IntegrityError upstream."""
    with transaction.atomic():
        user = User.objects.create_user(
            email=email, password=password, first_name=first_name, last_name=last_name, phone=phone or None
        )
        UserRole.objects.create(user=user, role=Role.BUYER)
    log_audit("user.registered", actor=user, object_type="user", object_id=user.pk, request=request)
    return user


def grant_role(*, user: User, role: str, granted_by: User | None = None, request=None) -> UserRole:
    obj, created = UserRole.objects.get_or_create(
        user=user, role=role, defaults={"granted_by": granted_by}
    )
    if created:
        log_audit(
            "role.granted",
            actor=granted_by or user,
            object_type="user",
            object_id=user.pk,
            metadata={"role": role},
            request=request,
        )
    return obj


def revoke_role(*, user: User, role: str, revoked_by: User | None = None, request=None) -> bool:
    deleted, _ = UserRole.objects.filter(user=user, role=role).delete()
    if deleted:
        log_audit(
            "role.revoked",
            actor=revoked_by,
            object_type="user",
            object_id=user.pk,
            metadata={"role": role},
            request=request,
        )
    return bool(deleted)
