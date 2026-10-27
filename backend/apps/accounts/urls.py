"""Accounts URL routes (docs/api.md §2)."""
from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/password/reset/", views.PasswordResetView.as_view(), name="auth-password-reset"),
    path(
        "auth/password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("auth/password/change/", views.PasswordChangeView.as_view(), name="auth-password-change"),
    path("auth/profile/", views.ProfileView.as_view(), name="auth-profile"),
    path("auth/addresses/", views.AddressListCreateView.as_view(), name="auth-addresses"),
    path("auth/addresses/<int:pk>/", views.AddressDetailView.as_view(), name="auth-address-detail"),
]
