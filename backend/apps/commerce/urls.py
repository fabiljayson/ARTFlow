"""Commerce URL routes (docs/api.md §6)."""
from django.urls import path

from apps.commerce import views

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/items/", views.CartItemCreateView.as_view(), name="cart-items"),
    path("cart/items/<int:pk>/", views.CartItemDetailView.as_view(), name="cart-item"),
    path("checkout/quote/", views.QuoteView.as_view(), name="checkout-quote"),
]
