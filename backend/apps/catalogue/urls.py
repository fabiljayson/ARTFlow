"""Catalogue URL routes (docs/api.md §3, §5, §8)."""
from django.urls import path

from apps.catalogue import views

urlpatterns = [
    # Public catalogue
    path("catalog/artworks/", views.CatalogArtworkList.as_view(), name="catalog-artworks"),
    path("catalog/artworks/<slug:slug>/", views.CatalogArtworkDetail.as_view(), name="catalog-artwork"),
    path(
        "catalog/artworks/<slug:slug>/similar/",
        views.CatalogArtworkSimilar.as_view(),
        name="catalog-artwork-similar",
    ),
    path(
        "catalog/artworks/<slug:slug>/media/<int:media_id>/<str:variant>/",
        views.ArtworkMediaStream.as_view(),
        name="catalog-artwork-media-variant",
    ),
    path(
        "catalog/artworks/<slug:slug>/media/<int:media_id>/",
        views.ArtworkMediaStream.as_view(),
        name="catalog-artwork-media",
    ),
    path("catalog/artworks/<int:pk>/favorite/", views.FavoriteToggle.as_view(), name="catalog-favorite"),
    path("catalog/favorites/", views.FavoriteList.as_view(), name="catalog-favorites"),
    path("catalog/categories/", views.CatalogCategoryList.as_view(), name="catalog-categories"),
    path("catalog/artists/", views.CatalogArtistList.as_view(), name="catalog-artists"),
    path("catalog/artists/<slug:slug>/", views.CatalogArtistDetail.as_view(), name="catalog-artist"),
    path("videos/feed/", views.VideosFeed.as_view(), name="videos-feed"),
    # Artist space
    path("artist/artworks/", views.ArtistArtworkListCreate.as_view(), name="artist-artworks"),
    path("artist/dashboard/", views.ArtistDashboard.as_view(), name="artist-dashboard"),
    path("artist/artworks/<int:pk>/", views.ArtistArtworkDetail.as_view(), name="artist-artwork"),
    path("artist/artworks/<int:pk>/media/", views.ArtistMediaUpload.as_view(), name="artist-artwork-media"),
    path(
        "artist/artworks/<int:pk>/media/<int:media_id>/",
        views.ArtistMediaDelete.as_view(),
        name="artist-artwork-media-delete",
    ),
    path("artist/artworks/<int:pk>/publish/", views.ArtistPublish.as_view(), name="artist-artwork-publish"),
    path(
        "artist/artworks/<int:pk>/unpublish/", views.ArtistUnpublish.as_view(), name="artist-artwork-unpublish"
    ),
    # Admin moderation
    path("admin/artworks/", views.AdminArtworkList.as_view(), name="admin-artworks"),
    path("admin/artworks/<int:pk>/moderate/", views.AdminArtworkModerate.as_view(), name="admin-artwork-moderate"),
]
