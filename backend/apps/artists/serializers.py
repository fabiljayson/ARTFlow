"""Artist application serializers."""
from rest_framework import serializers

from apps.artists.models import ArtistProfile, ArtistVerificationDocument


class ArtistProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    document_count = serializers.IntegerField(source="verification_documents.count", read_only=True)

    class Meta:
        model = ArtistProfile
        fields = [
            "id", "user_email", "display_name", "bio", "city", "region",
            "status", "document_count", "shipping_base_fee_xaf", "payout_method",
            "submitted_at", "reviewed_at", "rejection_reason", "info_request",
            "suspension_reason", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_email", "status", "document_count", "submitted_at",
            "reviewed_at", "rejection_reason", "info_request", "suspension_reason",
            "created_at", "updated_at",
        ]


class ApplicationCreateSerializer(serializers.Serializer):
    """Initial draft fields on POST /artists/application/."""

    display_name = serializers.CharField(max_length=120)
    bio = serializers.CharField(required=False, allow_blank=True, default="")
    city = serializers.CharField(max_length=80)
    region = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    shipping_base_fee_xaf = serializers.IntegerField(min_value=0, required=False, default=0)


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtistVerificationDocument
        fields = ["id", "kind", "original_filename", "content_type", "size_bytes", "uploaded_at"]
        read_only_fields = fields


class ApproveSerializer(serializers.Serializer):
    """Approve can carry optional internal note (not required by spec)."""


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField()


class RequestInfoSerializer(serializers.Serializer):
    message = serializers.CharField()


class SuspendSerializer(serializers.Serializer):
    reason = serializers.CharField()
