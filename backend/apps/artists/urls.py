"""Artists URL routes (docs/api.md §4)."""
from django.urls import path

from apps.artists import views

urlpatterns = [
    # Applicant
    path("artists/application/", views.ApplicationView.as_view(), name="application"),
    path("artists/application/submit/", views.ApplicationSubmitView.as_view(), name="application-submit"),
    path(
        "artists/application/documents/",
        views.DocumentUploadView.as_view(),
        name="application-documents",
    ),
    path(
        "artists/application/documents/<int:pk>/",
        views.DocumentDeleteView.as_view(),
        name="application-document-delete",
    ),
    # Admin / moderation
    path("admin/applications/", views.AdminApplicationListView.as_view(), name="admin-applications"),
    path("admin/applications/<int:pk>/approve/", views.AdminApproveView.as_view(), name="admin-application-approve"),
    path("admin/applications/<int:pk>/reject/", views.AdminRejectView.as_view(), name="admin-application-reject"),
    path(
        "admin/applications/<int:pk>/request-info/",
        views.AdminRequestInfoView.as_view(),
        name="admin-application-request-info",
    ),
    path(
        "admin/applications/<int:pk>/suspend/",
        views.AdminSuspendView.as_view(),
        name="admin-application-suspend",
    ),
    path(
        "admin/applications/<int:pk>/documents/<int:doc_id>/",
        views.AdminDocumentDownloadView.as_view(),
        name="admin-application-document",
    ),
]
