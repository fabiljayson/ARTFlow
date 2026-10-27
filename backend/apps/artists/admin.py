"""Django admin for artists."""
from django.contrib import admin

from apps.artists.models import ArtistProfile, ArtistVerificationDocument


class VerificationDocumentInline(admin.TabularInline):
    model = ArtistVerificationDocument
    extra = 0
    readonly_fields = ("original_filename", "content_type", "size_bytes", "uploaded_at", "uploaded_by")
    can_delete = False


@admin.register(ArtistProfile)
class ArtistProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "status", "city", "updated_at")
    list_filter = ("status",)
    search_fields = ("display_name", "user__email", "city")
    inlines = (VerificationDocumentInline,)


@admin.register(ArtistVerificationDocument)
class ArtistVerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ("kind", "artist_profile", "original_filename", "content_type", "size_bytes", "uploaded_at")
    search_fields = ("original_filename", "artist_profile__display_name")
    readonly_fields = ("original_filename", "content_type", "size_bytes", "uploaded_at", "uploaded_by")
