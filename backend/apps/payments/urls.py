"""Payments URL routes — montées sous /api/v1/ (config/urls.py)."""
from django.urls import path

from apps.payments.views import InitiatePaymentView, PaymentWebhookView

urlpatterns = [
    path("webhook/", PaymentWebhookView.as_view()),
    path("<str:external_reference>/initiate/", InitiatePaymentView.as_view()),
]
