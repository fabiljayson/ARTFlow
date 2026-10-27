"""Upload validation by magic bytes (EX-6, docs/security.md #8).

Allowlist per content type; sniffed bytes must match. No MIME trust from client.
"""
from rest_framework.exceptions import ValidationError

ALLOWED_UPLOADS = {
    "application/pdf": (b"%PDF",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB (docs: configurable)


def validate_upload(uploaded_file, *, allowed: dict | None = None) -> str:
    """Validate size + magic bytes. Returns the sniffed content type.

    Raises ValidationError with a stable message on rejection.
    """
    allowed = allowed if allowed is not None else ALLOWED_UPLOADS
    size = getattr(uploaded_file, "size", None)
    if size is None or size <= 0:
        raise ValidationError({"file": "Fichier vide ou illisible."})
    if size > MAX_UPLOAD_BYTES:
        raise ValidationError({"file": f"Fichier trop volumineux (max {MAX_UPLOAD_BYTES // (1024 * 1024)} Mo)."})

    head = uploaded_file.read(16)
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    for content_type, signatures in allowed.items():
        if any(head.startswith(sig) for sig in signatures):
            return content_type
    raise ValidationError({"file": "Type de fichier non autorisé (PDF, JPEG ou PNG uniquement)."})
