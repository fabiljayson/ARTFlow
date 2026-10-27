"""Artwork media upload service: magic-byte sniffing, quotas, thumbnails (EX-6, EF-7.1).

Reuse artists.file_validation for size limits; content sniffing here supports
image/webp and mp4/webm (signatures at fixed offsets).
"""
import hashlib
import io

from django.db.models import Max
from django.utils.text import get_valid_filename
from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.artists.file_validation import MAX_UPLOAD_BYTES
from apps.catalogue.models import ArtworkMedia, MediaKind

MAX_IMAGES_PER_ARTWORK = 10
MAX_VIDEOS_PER_ARTWORK = 1
THUMB_SIZE = (480, 480)


def _sniff_image(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def _sniff_video(head: bytes) -> str | None:
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return "video/mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    return None


def validate_media_upload(uploaded_file, *, kind: str) -> str:
    """Validate size + magic bytes for the given media kind. Returns sniffed content type."""
    size = getattr(uploaded_file, "size", None)
    if size is None or size <= 0:
        raise ValidationError({"file": "Fichier vide ou illisible."})
    if size > MAX_UPLOAD_BYTES:
        raise ValidationError({"file": f"Fichier trop volumineux (max {MAX_UPLOAD_BYTES // (1024 * 1024)} Mo)."})

    head = uploaded_file.read(32)
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    content_type = _sniff_image(head) if kind == MediaKind.IMAGE else _sniff_video(head)
    if content_type is None:
        raise ValidationError({"file": "Type de fichier non autorisé pour ce type de média."})
    return content_type


def make_thumbnail(image_file) -> bytes:
    """Generate a square-ish PNG thumbnail (max 480px, preserve ratio)."""
    image_file.seek(0)
    with Image.open(image_file) as img:
        img = img.convert("RGB")
        img.thumbnail(THUMB_SIZE)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
    image_file.seek(0)
    return buffer.getvalue()


def next_position(artwork) -> int:
    current = artwork.media.aggregate(m=Max("position"))["m"]
    return (current + 1) if current is not None else 0


def check_quotas(artwork, kind: str) -> None:
    count = artwork.media.filter(kind=kind).count()
    limit = MAX_IMAGES_PER_ARTWORK if kind == MediaKind.IMAGE else MAX_VIDEOS_PER_ARTWORK
    if count >= limit:
        label = "images" if kind == MediaKind.IMAGE else "vidéos"
        raise ValidationError({"file": f"Quota atteint ({limit} max par œuvre pour les {label})."})


def store_media(*, artwork, uploaded_file, kind: str, alt_text_fr: str, alt_text_en: str = "",
                is_primary: bool, request=None) -> ArtworkMedia:
    """Full upload flow: validate → quota → checksum → save → thumbnail."""
    from django.core.files.base import ContentFile

    from apps.core.audit import log_audit

    content_type = validate_media_upload(uploaded_file, kind=kind)
    check_quotas(artwork, kind)

    if kind == MediaKind.IMAGE and not alt_text_fr.strip():
        raise ValidationError({"alt_text_fr": "Le texte alternatif (FR) est obligatoire pour les images."})

    uploaded_file.seek(0)
    checksum = hashlib.sha256(uploaded_file.read()).hexdigest()
    uploaded_file.seek(0)

    media = ArtworkMedia(
        artwork=artwork,
        kind=kind,
        file="",
        position=next_position(artwork),
        alt_text_fr=alt_text_fr,
        alt_text_en=alt_text_en,
        is_primary=is_primary,
        content_type=content_type,
        size_bytes=uploaded_file.size,
        checksum_sha256=checksum,
    )

    if is_primary:
        artwork.media.filter(is_primary=True).update(is_primary=False)

    media.file.save(get_valid_filename(uploaded_file.name or "media"), uploaded_file, save=False)

    if kind == MediaKind.IMAGE:
        thumb_bytes = make_thumbnail(uploaded_file)
        media.thumbnail_file.save(
            f"thumb_{media.file.name.rsplit('/', 1)[-1]}.png",
            ContentFile(thumb_bytes),
            save=False,
        )
        uploaded_file.seek(0)
        try:
            with Image.open(uploaded_file) as img:
                media.width_px, media.height_px = img.size
        except Exception:
            pass
        uploaded_file.seek(0)

    media.save()
    log_audit(
        "artwork_media.uploaded",
        actor=artwork.artist.user,
        object_type="artwork_media",
        object_id=media.pk,
        metadata={"artwork": artwork.slug, "kind": kind},
        request=request,
    )
    return media
