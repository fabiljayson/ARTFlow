"""Payments URL routes — montées sous /api/v1/payments/ (config/urls.py)."""
from django.urls import path

from apps.payments.views import (
    InitiatePaymentView,
    PaymentWebhookView,
    SimulatePaymentView,
)

urlpatterns = [
    path("webhook/", PaymentWebhookView.as_view()),
    path("dev/simulate/", SimulatePaymentView.as_view()),
    path("<str:external_reference>/initiate/", InitiatePaymentView.as_view()),
]
