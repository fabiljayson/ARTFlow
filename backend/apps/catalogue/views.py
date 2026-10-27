"""Catalogue API views — public read, artist CRUD, moderation (docs/api.md §3/§5/§8)."""
from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.artists.models import ApplicationStatus, ArtistProfile
from apps.catalogue import media_service, workflows
from apps.catalogue.models import Artwork, ArtworkMedia, ArtworkStatus, Category, Favorite
from apps.catalogue.serializers import (
    ArtistPublicDetailSerializer,
    ArtistPublicSerializer,
    ArtworkCreateSerializer,
    ArtworkDetailSerializer,
    ArtworkSummarySerializer,
    CategorySerializer,
    DashboardSerializer,
    MediaSerializer,
    MediaUploadSerializer,
    ModerateSerializer,
)
from apps.core.audit import log_audit
from apps.core.permissions import IsArtist, IsModeratorOrAdmin

# ---------------------------------------------------------------------------
# Artist space (/artist/artworks/)
# ---------------------------------------------------------------------------


class ArtistArtworkListCreate(generics.ListCreateAPIView):
    permission_classes = [IsArtist]
    serializer_class = ArtworkCreateSerializer

    def get_queryset(self):
        return Artwork.objects.filter(artist__user=self.request.user).prefetch_related("media")

    def perform_create(self, serializer):
        try:
            profile = ArtistProfile.objects.get(user=self.request.user, status=ApplicationStatus.APPROVED)
        except ArtistProfile.DoesNotExist:
            raise ValidationError({"detail": "Profil artiste approuvé requis."}) from None
        artwork = serializer.save(artist=profile)
        log_audit(
            "artwork.created",
            actor=self.request.user,
            object_type="artwork",
            object_id=artwork.pk,
            metadata={"slug": artwork.slug},
            request=self.request,
        )


class ArtistArtworkDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsArtist]
    serializer_class = ArtworkCreateSerializer

    def get_queryset(self):
        return Artwork.objects.filter(artist__user=self.request.user).prefetch_related("media")

    def perform_update(self, serializer):
        artwork = self.get_object()
        old_price = artwork.price_xaf
        artwork = serializer.save()
        workflows.maybe_reprice_remoderation(
            artwork=artwork, old_price=old_price, actor=self.request.user, request=self.request
        )
        log_audit(
            "artwork.updated",
            actor=self.request.user,
            object_type="artwork",
            object_id=artwork.pk,
            request=self.request,
        )

    def perform_destroy(self, instance):
        """DELETE is an archive (logical) — EF-7: never a hard delete."""
        workflows.archive(artwork=instance, actor=self.request.user, request=self.request)


class ArtistMediaUpload(APIView):
    permission_classes = [IsArtist]

    def post(self, request, pk):
        artwork = _own_artwork(request.user, pk)
        serializer = MediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            media = media_service.store_media(
                artwork=artwork,
                uploaded_file=serializer.validated_data["file"],
                kind=serializer.validated_data["kind"],
                alt_text_fr=serializer.validated_data["alt_text_fr"],
                alt_text_en=serializer.validated_data["alt_text_en"],
                is_primary=serializer.validated_data["is_primary"],
                request=request,
            )
        except ValidationError as exc:
            return Response(
                {"error": {"code": "validation_error", "message": "Média refusé.", "details": exc.detail}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(MediaSerializer(media, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ArtistMediaDelete(APIView):
    permission_classes = [IsArtist]

    def delete(self, request, pk, media_id):
        artwork = _own_artwork(request.user, pk)
        deleted, _ = ArtworkMedia.objects.filter(pk=media_id, artwork=artwork).delete()
        if not deleted:
            raise Http404
        log_audit(
            "artwork_media.deleted",
            actor=request.user,
            object_type="artwork_media",
            object_id=media_id,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ArtistPublish(APIView):
    permission_classes = [IsArtist]

    def post(self, request, pk):
        artwork = _own_artwork(request.user, pk)
        artwork = workflows.publish(artwork=artwork, actor=request.user, request=request)
        return Response(ArtworkSummarySerializer(artwork, context={"request": request}).data)


class ArtistUnpublish(APIView):
    permission_classes = [IsArtist]

    def post(self, request, pk):
        artwork = _own_artwork(request.user, pk)
        artwork = workflows.unpublish(artwork=artwork, actor=request.user, request=request)
        return Response(ArtworkSummarySerializer(artwork, context={"request": request}).data)


class ArtistDashboard(APIView):
    permission_classes = [IsArtist]

    def get(self, request):
        qs = Artwork.objects.filter(artist__user=request.user)
        data = {
            "total_artworks": qs.count(),
            "published": qs.filter(status=ArtworkStatus.PUBLISHED).count(),
            "in_moderation": qs.filter(status=ArtworkStatus.IN_MODERATION).count(),
            "drafts": qs.filter(status=ArtworkStatus.DRAFT).count(),
            "unavailable": qs.filter(status=ArtworkStatus.PUBLISHED, stock_quantity=0).count(),
            "total_favorites": Favorite.objects.filter(artwork__in=qs).count(),
        }
        return Response(DashboardSerializer(data).data)


def _own_artwork(user, pk) -> Artwork:
    try:
        return Artwork.objects.get(pk=pk, artist__user=user)
    except Artwork.DoesNotExist:
        raise Http404 from None


# ---------------------------------------------------------------------------
# Public catalogue (/catalog/, /videos/)
# ---------------------------------------------------------------------------


class CatalogArtworkList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ArtworkSummarySerializer

    def get_queryset(self):
        qs = (
            Artwork.objects.filter(status=ArtworkStatus.PUBLISHED)
            .select_related("artist", "category")
            .prefetch_related("media")
        )
        params = self.request.query_params
        q = params.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        category = params.get("category")
        if category:
            qs = qs.filter(category__slug=category)
        price_min = params.get("price_min")
        if price_min and price_min.isdigit():
            qs = qs.filter(price_xaf__gte=int(price_min))
        price_max = params.get("price_max")
        if price_max and price_max.isdigit():
            qs = qs.filter(price_xaf__lte=int(price_max))
        if params.get("available") in ("true", "1"):
            qs = qs.filter(stock_quantity__gt=0)
        artist = params.get("artist")
        if artist:
            qs = qs.filter(artist__slug=artist)
        sort = params.get("sort", "-date")
        sort_map = {
            "date": "published_at",
            "-date": "-published_at",
            "price": "price_xaf",
            "-price": "-price_xaf",
            "title": "title",
            "-title": "-title",
        }
        return qs.order_by(sort_map.get(sort, "-published_at"))


class CatalogArtworkDetail(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ArtworkDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Artwork.objects.filter(status=ArtworkStatus.PUBLISHED)
            .select_related("artist", "category")
            .prefetch_related("media")
        )


class CatalogArtworkSimilar(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ArtworkSummarySerializer

    pagination_class = None  # fixed max of 6 — not a paginated collection

    def get_queryset(self):
        slug = self.kwargs["slug"]
        try:
            artwork = Artwork.objects.get(slug=slug, status=ArtworkStatus.PUBLISHED)
        except Artwork.DoesNotExist:
            raise Http404 from None
        return (
            Artwork.objects.filter(status=ArtworkStatus.PUBLISHED, category=artwork.category)
            .exclude(pk=artwork.pk)
            .select_related("artist", "category")
            .prefetch_related("media")
            .order_by("-published_at")[:6]
        )


class CatalogCategoryList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(is_active=True, parent__isnull=True)


class CatalogArtistList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ArtistPublicSerializer

    def get_queryset(self):
        return ArtistProfile.objects.filter(status=ApplicationStatus.APPROVED)


class CatalogArtistDetail(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ArtistPublicDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return ArtistProfile.objects.filter(status=ApplicationStatus.APPROVED)


class VideosFeed(generics.ListAPIView):
    """Video feed of PUBLISHED artworks (docs/api.md §3)."""

    permission_classes = [AllowAny]

    def get_queryset(self):
        return ArtworkMedia.objects.filter(
            kind="VIDEO", artwork__status=ArtworkStatus.PUBLISHED
        ).select_related("artwork", "artwork__artist")

    def get_serializer_class(self):
        return MediaSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        items = []
        for media in qs[:50]:
            items.append(
                {
                    **MediaSerializer(media, context={"request": request}).data,
                    "artwork_slug": media.artwork.slug,
                    "artwork_title": media.artwork.title,
                    "artist_display_name": media.artwork.artist.display_name,
                    "artist_slug": media.artwork.artist.slug,
                }
            )
        return Response(items)


class ArtworkMediaStream(APIView):
    """Stream a media file: public for PUBLISHED artworks, owner/moderator otherwise.

    Variants: `stream` (original), `thumb` (image thumbnail), `poster` (video poster).
    """

    permission_classes = [AllowAny]

    VARIANT_FIELDS = {"stream": "file", "thumb": "thumbnail_file", "poster": "poster_file"}

    def get(self, request, slug, media_id, variant="stream"):
        field = self.VARIANT_FIELDS.get(variant)
        if field is None:
            raise Http404
        try:
            artwork = Artwork.objects.get(slug=slug)
        except Artwork.DoesNotExist:
            raise Http404 from None
        try:
            media = artwork.media.get(pk=media_id)
        except ArtworkMedia.DoesNotExist:
            raise Http404 from None

        allowed = artwork.status == ArtworkStatus.PUBLISHED
        user = request.user
        if not allowed and user.is_authenticated:
            allowed = artwork.artist.user_id == user.id or (
                artwork.artist.status == ApplicationStatus.APPROVED
                and user.has_any_role("MODERATOR", "ADMIN")
            )
        if not allowed:
            raise Http404
        file_handle = getattr(media, field)
        if not file_handle:
            raise Http404

        cache = "public, max-age=3600" if artwork.status == ArtworkStatus.PUBLISHED else "no-store"
        content_type = (
            "image/png" if field in ("thumbnail_file", "poster_file") else (media.content_type or "application/octet-stream")
        )
        response = FileResponse(file_handle.open("rb"), content_type=content_type)
        response["Cache-Control"] = cache
        return response


# ---------------------------------------------------------------------------
# Favorites (authenticated)
# ---------------------------------------------------------------------------


class FavoriteToggle(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            artwork = Artwork.objects.get(pk=pk, status=ArtworkStatus.PUBLISHED)
        except Artwork.DoesNotExist:
            raise Http404 from None
        fav, created = Favorite.objects.get_or_create(user=request.user, artwork=artwork)
        if not created:
            fav.delete()
            return Response({"favorited": False}, status=status.HTTP_200_OK)
        return Response({"favorited": True}, status=status.HTTP_201_CREATED)


class FavoriteList(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ArtworkSummarySerializer

    def get_queryset(self):
        return (
            Artwork.objects.filter(favorited_by__user=self.request.user)
            .select_related("artist", "category")
            .prefetch_related("media")
            .order_by("-favorited_by__created_at")
        )


# ---------------------------------------------------------------------------
# Admin moderation (/admin/artworks/)
# ---------------------------------------------------------------------------


class AdminArtworkList(generics.ListAPIView):
    permission_classes = [IsModeratorOrAdmin]
    serializer_class = ArtworkSummarySerializer

    def get_queryset(self):
        qs = Artwork.objects.select_related("artist", "category").prefetch_related("media")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by("-updated_at")


class AdminArtworkModerate(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, pk):
        serializer = ModerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            artwork = Artwork.objects.get(pk=pk)
        except Artwork.DoesNotExist:
            raise Http404 from None
        artwork = workflows.moderate(
            artwork=artwork,
            moderator=request.user,
            decision=serializer.validated_data["decision"],
            reason=serializer.validated_data["reason"],
            request=request,
        )
        return Response(ArtworkSummarySerializer(artwork, context={"request": request}).data)

