"""Artwork lifecycle transitions (EF-6.4, EF-7, docs/api.md §5/§8).

All transitions audited; publish is gated on an APPROVED artist profile.
"""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.artists.models import ApplicationStatus
from apps.catalogue.models import Artwork, ArtworkStatus
from apps.core.audit import log_audit
from apps.core.models import PlatformSettings


def _require_artist_approved(artwork: Artwork) -> None:
    if artwork.artist.status != ApplicationStatus.APPROVED:
        raise ValidationError({"detail": "Artiste non approuvé : publication impossible."})


def publish(*, artwork: Artwork, actor, request=None) -> Artwork:
    _require_artist_approved(artwork)
    if artwork.status not in (
        ArtworkStatus.DRAFT,
        ArtworkStatus.REFUSED,
        ArtworkStatus.HIDDEN,
    ):
        raise ValidationError({"detail": f"Transition impossible depuis {artwork.status}."})
    if not artwork.media.filter(kind="IMAGE").exists():
        raise ValidationError({"detail": "Au moins une image est requise pour publier."})
    artwork.status = ArtworkStatus.IN_MODERATION
    artwork.refusal_reason = ""
    artwork.save(update_fields=["status", "refusal_reason", "updated_at"])
    log_audit(
        "artwork.submitted_for_moderation",
        actor=actor,
        object_type="artwork",
        object_id=artwork.pk,
        metadata={"slug": artwork.slug},
        request=request,
    )
    return artwork


def unpublish(*, artwork: Artwork, actor, request=None) -> Artwork:
    if artwork.status != ArtworkStatus.PUBLISHED:
        raise ValidationError({"detail": "Seule une œuvre publiée peut être dépubliée."})
    artwork.status = ArtworkStatus.HIDDEN
    artwork.save(update_fields=["status", "updated_at"])
    log_audit(
        "artwork.unpublished",
        actor=actor,
        object_type="artwork",
        object_id=artwork.pk,
        request=request,
    )
    return artwork


def archive(*, artwork: Artwork, actor, request=None) -> Artwork:
    """Artist delete → logical ARCHIVED (docs/database.md: jamais de DELETE)."""
    if artwork.status in (ArtworkStatus.PUBLISHED, ArtworkStatus.IN_MODERATION):
        raise ValidationError({"detail": "Désarchivez d'abord (dépublier) avant l'archivage."})
    artwork.status = ArtworkStatus.ARCHIVED
    artwork.save(update_fields=["status", "updated_at"])
    log_audit(
        "artwork.archived", actor=actor, object_type="artwork", object_id=artwork.pk, request=request
    )
    return artwork


def moderate(*, artwork: Artwork, moderator, decision: str, reason: str = "", request=None) -> Artwork:
    """Admin/moderator decision: approve | refuse | hide (motif requis sauf approve)."""
    if decision == "approve":
        if artwork.status != ArtworkStatus.IN_MODERATION:
            raise ValidationError({"detail": "Seule une œuvre en modération peut être approuvée."})
        with transaction.atomic():
            artwork.status = ArtworkStatus.PUBLISHED
            artwork.published_at = artwork.published_at or timezone.now()
            artwork.refusal_reason = ""
            artwork.save()
        action = "artwork.approved"
    elif decision == "refuse":
        if artwork.status != ArtworkStatus.IN_MODERATION:
            raise ValidationError({"detail": "Seule une œuvre en modération peut être refusée."})
        if not reason.strip():
            raise ValidationError({"detail": "Un motif de refus est obligatoire."})
        artwork.status = ArtworkStatus.REFUSED
        artwork.refusal_reason = reason
        artwork.save()
        action = "artwork.refused"
    elif decision == "hide":
        if artwork.status not in (ArtworkStatus.PUBLISHED, ArtworkStatus.IN_MODERATION):
            raise ValidationError({"detail": "Seule une œuvre visible peut être masquée."})
        if not reason.strip():
            raise ValidationError({"detail": "Un motif de masquage est obligatoire."})
        artwork.status = ArtworkStatus.HIDDEN
        artwork.moderation_note = reason
        artwork.save()
        action = "artwork.hidden"
    else:
        raise ValidationError({"detail": "Décision inconnue (approve|refuse|hide)."})
    log_audit(
        action,
        actor=moderator,
        object_type="artwork",
        object_id=artwork.pk,
        metadata={"reason": reason} if reason else {},
        request=request,
    )
    return artwork


def maybe_reprice_remoderation(*, artwork: Artwork, old_price: int, actor, request=None) -> None:
    """EF-7.3: raising the price beyond the platform threshold re-enters moderation."""
    if artwork.status != ArtworkStatus.PUBLISHED or old_price <= 0:
        return
    settings = PlatformSettings.get()
    threshold = settings.moderation_reprice_threshold_pct
    if artwork.price_xaf <= old_price * (100 + threshold) / 100:
        return
    artwork.status = ArtworkStatus.IN_MODERATION
    artwork.save(update_fields=["status", "updated_at"])
    log_audit(
        "artwork.reprice_remoderation",
        actor=actor,
        object_type="artwork",
        object_id=artwork.pk,
        metadata={"old_price_xaf": old_price, "new_price_xaf": artwork.price_xaf},
        request=request,
    )
