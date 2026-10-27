"""Artist application workflow (EF-6, docs/api.md §4).

Transitions légales uniquement ; toutes auditées (traçabilité EF-6.2).
Approbation ⇒ rôle ARTIST granté ; suspension ⇒ rôle ARTIST révoqué (EF-6.4).
"""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import Role
from apps.accounts.services import grant_role, revoke_role
from apps.artists.models import ApplicationStatus, ArtistProfile
from apps.core.audit import log_audit


def get_or_create_draft(*, user, data: dict, request=None) -> ArtistProfile:
    profile = ArtistProfile.objects.filter(user=user).first()
    if profile is None:
        profile = ArtistProfile.objects.create(user=user, **data)
        log_audit(
            "application.created",
            actor=user,
            object_type="artist_profile",
            object_id=profile.pk,
            request=request,
        )
        return profile
    if profile.status not in (ApplicationStatus.DRAFT, ApplicationStatus.NEEDS_INFO):
        raise ValidationError({"detail": "Une candidature existe déjà et n'est plus modifiable."})
    return profile


def update_draft(*, profile: ArtistProfile, data: dict) -> ArtistProfile:
    if profile.status not in (ApplicationStatus.DRAFT, ApplicationStatus.NEEDS_INFO):
        raise ValidationError({"detail": "Seuls les brouillons ou demandes d'info peuvent être modifiés."})
    for field, value in data.items():
        setattr(profile, field, value)
    profile.save()
    return profile


def submit_application(*, profile: ArtistProfile, user, request=None) -> ArtistProfile:
    if profile.status not in (ApplicationStatus.DRAFT, ApplicationStatus.NEEDS_INFO):
        raise ValidationError({"detail": "Transition impossible depuis ce statut."})
    if not profile.display_name or not profile.city:
        raise ValidationError({"detail": "Nom public et ville requis avant soumission."})
    if not profile.verification_documents.exists():
        raise ValidationError({"detail": "Au moins un document de vérification est requis."})
    profile.status = ApplicationStatus.PENDING_REVIEW
    profile.submitted_at = timezone.now()
    profile.info_request = ""
    profile.save()
    log_audit(
        "application.submitted",
        actor=user,
        object_type="artist_profile",
        object_id=profile.pk,
        request=request,
    )
    return profile


def approve_application(*, profile: ArtistProfile, admin, request=None) -> ArtistProfile:
    if profile.status not in (ApplicationStatus.PENDING_REVIEW, ApplicationStatus.SUSPENDED):
        raise ValidationError({"detail": "Seule une candidature en attente (ou suspendue) peut être approuvée."})
    with transaction.atomic():
        profile.status = ApplicationStatus.APPROVED
        profile.reviewed_at = timezone.now()
        profile.reviewed_by = admin
        profile.rejection_reason = ""
        profile.suspension_reason = ""
        profile.save()
        grant_role(user=profile.user, role=Role.ARTIST, granted_by=admin, request=request)
    log_audit(
        "application.approved",
        actor=admin,
        object_type="artist_profile",
        object_id=profile.pk,
        request=request,
    )
    return profile


def reject_application(*, profile: ArtistProfile, admin, reason: str, request=None) -> ArtistProfile:
    if profile.status != ApplicationStatus.PENDING_REVIEW:
        raise ValidationError({"detail": "Seule une candidature en attente peut être refusée."})
    if not reason.strip():
        raise ValidationError({"detail": "Un motif de refus est obligatoire."})
    profile.status = ApplicationStatus.REJECTED
    profile.reviewed_at = timezone.now()
    profile.reviewed_by = admin
    profile.rejection_reason = reason
    profile.save()
    log_audit(
        "application.rejected",
        actor=admin,
        object_type="artist_profile",
        object_id=profile.pk,
        metadata={"reason": reason},
        request=request,
    )
    return profile


def request_info(*, profile: ArtistProfile, moderator, message: str, request=None) -> ArtistProfile:
    if profile.status != ApplicationStatus.PENDING_REVIEW:
        raise ValidationError({"detail": "Seule une candidature en attente peut être renvoyée pour info."})
    if not message.strip():
        raise ValidationError({"detail": "Le message de demande d'information est obligatoire."})
    profile.status = ApplicationStatus.NEEDS_INFO
    profile.info_request = message
    profile.save()
    log_audit(
        "application.info_requested",
        actor=moderator,
        object_type="artist_profile",
        object_id=profile.pk,
        request=request,
    )
    return profile


def suspend_application(*, profile: ArtistProfile, admin, reason: str, request=None) -> ArtistProfile:
    if profile.status != ApplicationStatus.APPROVED:
        raise ValidationError({"detail": "Seule une artiste approuvé peut être suspendu."})
    if not reason.strip():
        raise ValidationError({"detail": "Un motif de suspension est obligatoire."})
    with transaction.atomic():
        profile.status = ApplicationStatus.SUSPENDED
        profile.suspension_reason = reason
        profile.save()
        revoke_role(user=profile.user, role=Role.ARTIST, revoked_by=admin, request=request)
    log_audit(
        "application.suspended",
        actor=admin,
        object_type="artist_profile",
        object_id=profile.pk,
        metadata={"reason": reason},
        request=request,
    )
    return profile
