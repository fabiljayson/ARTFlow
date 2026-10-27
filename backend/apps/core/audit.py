"""Audit helper — single entry point to record traceable actions."""
from apps.core.models import AuditLog


def client_ip(request):
    """Best-effort client IP (dev proxy aware; prod must set a trusted header)."""
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit(action, *, actor=None, object_type="", object_id="", metadata=None, request=None):
    """Record an audit event. Never raises: auditing must not break the main flow silently,
    but failures in tests should surface — kept simple and synchronous for the MVP."""
    AuditLog.objects.create(
        actor=actor if actor and actor.is_authenticated else None,
        actor_role=_actor_role(actor),
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id != "" else "",
        metadata=metadata or {},
        ip=client_ip(request),
    )


def _actor_role(actor):
    if actor is None or not actor.is_authenticated:
        return ""
    if actor.is_superuser:
        return "ADMIN"
    role = actor.roles.order_by("created_at").values_list("role", flat=True).first()
    return role or "BUYER"
