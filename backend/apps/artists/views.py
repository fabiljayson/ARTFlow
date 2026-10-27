"""Artist application API views (docs/api.md §4)."""
from django.http import FileResponse, Http404
from django.utils.text import get_valid_filename
from rest_framework import generics, serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.artists import services
from apps.artists.file_validation import validate_upload
from apps.artists.models import ArtistProfile, ArtistVerificationDocument, DocumentKind
from apps.artists.serializers import (
    ApplicationCreateSerializer,
    ArtistProfileSerializer,
    DocumentSerializer,
    RejectSerializer,
    RequestInfoSerializer,
    SuspendSerializer,
)
from apps.core.audit import log_audit
from apps.core.permissions import IsModeratorOrAdmin


def _profile_or_404(user):
    try:
        return user.artist_profile
    except (ArtistProfile.DoesNotExist, AttributeError):
        # AttributeError: AnonymousUser has no related profile at all.
        raise Http404 from None


class ApplicationView(APIView):
    """GET my application (404 if none) · POST create draft · PATCH update draft."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = _profile_or_404(request.user)
        return Response(ArtistProfileSerializer(profile).data)

    def post(self, request):
        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = services.get_or_create_draft(
            user=request.user, data=serializer.validated_data, request=request
        )
        return Response(ArtistProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        profile = _profile_or_404(request.user)
        serializer = ApplicationCreateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = services.update_draft(profile=profile, data=serializer.validated_data)
        return Response(ArtistProfileSerializer(profile).data)


class ApplicationSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = _profile_or_404(request.user)
        profile = services.submit_application(profile=profile, user=request.user, request=request)
        return Response(ArtistProfileSerializer(profile).data)


class DocumentUploadView(generics.ListCreateAPIView):
    """List/upload verification documents (owner). Multipart: kind + file."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        class DocumentUploadSerializer(serializers.Serializer):
            kind = serializers.ChoiceField(choices=DocumentKind.choices)
            file = serializers.FileField()

        return DocumentUploadSerializer

    def get_queryset(self):
        return ArtistVerificationDocument.objects.filter(artist_profile__user=self.request.user)

    def list(self, request, *args, **kwargs):
        return Response(DocumentSerializer(self.get_queryset(), many=True).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = _profile_or_404(request.user)
        uploaded = serializer.validated_data["file"]
        content_type = validate_upload(uploaded)
        doc = ArtistVerificationDocument.objects.create(
            artist_profile=profile,
            kind=serializer.validated_data["kind"],
            file=uploaded,
            original_filename=get_valid_filename(uploaded.name) or "document",
            content_type=content_type,
            size_bytes=uploaded.size,
            uploaded_by=request.user,
        )
        log_audit(
            "verification_document.uploaded",
            actor=request.user,
            object_type="verification_document",
            object_id=doc.pk,
            request=request,
        )
        return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class DocumentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = ArtistVerificationDocument.objects.filter(
            pk=pk, artist_profile__user=request.user
        ).delete()
        if not deleted:
            raise Http404 from None
        log_audit(
            "verification_document.deleted",
            actor=request.user,
            object_type="verification_document",
            object_id=pk,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminApplicationListView(generics.ListAPIView):
    permission_classes = [IsModeratorOrAdmin]

    def get_queryset(self):
        qs = ArtistProfile.objects.select_related("user", "reviewed_by").order_by("-updated_at")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(ArtistProfileSerializer(page, many=True).data)


class _AdminActionView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def _get_profile(self, pk):
        try:
            return ArtistProfile.objects.get(pk=pk)
        except ArtistProfile.DoesNotExist:
            raise Http404 from None


class AdminApproveView(_AdminActionView):
    def post(self, request, pk):
        profile = self._get_profile(pk)
        profile = services.approve_application(profile=profile, admin=request.user, request=request)
        return Response(ArtistProfileSerializer(profile).data)


class AdminRejectView(_AdminActionView):
    def post(self, request, pk):
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = self._get_profile(pk)
        profile = services.reject_application(
            profile=profile, admin=request.user, reason=serializer.validated_data["reason"], request=request
        )
        return Response(ArtistProfileSerializer(profile).data)


class AdminRequestInfoView(_AdminActionView):
    def post(self, request, pk):
        serializer = RequestInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = self._get_profile(pk)
        profile = services.request_info(
            profile=profile,
            moderator=request.user,
            message=serializer.validated_data["message"],
            request=request,
        )
        return Response(ArtistProfileSerializer(profile).data)


class AdminSuspendView(_AdminActionView):
    def post(self, request, pk):
        serializer = SuspendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = self._get_profile(pk)
        profile = services.suspend_application(
            profile=profile,
            admin=request.user,
            reason=serializer.validated_data["reason"],
            request=request,
        )
        return Response(ArtistProfileSerializer(profile).data)


class AdminDocumentDownloadView(_AdminActionView):
    """Stream a verification document — admin/moderator only, no-store (EX-6)."""

    def get(self, request, pk, doc_id):
        profile = self._get_profile(pk)
        try:
            doc = profile.verification_documents.get(pk=doc_id)
        except ArtistVerificationDocument.DoesNotExist:
            raise Http404 from None
        log_audit(
            "verification_document.viewed",
            actor=request.user,
            object_type="verification_document",
            object_id=doc.pk,
            request=request,
        )
        response = FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.original_filename)
        response["Content-Type"] = doc.content_type
        response["Cache-Control"] = "no-store"
        return response
