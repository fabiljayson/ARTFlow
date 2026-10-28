"""Commerce URL routes (docs/api.md §6)."""
from django.urls import path

from apps.commerce import views

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/items/", views.CartItemCreateView.as_view(), name="cart-items"),
    path("cart/items/<int:pk>/", views.CartItemDetailView.as_view(), name="cart-item"),
    path("checkout/quote/", views.QuoteView.as_view(), name="checkout-quote"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("orders/", views.OrderListView.as_view(), name="orders"),
    path("orders/<str:reference>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("orders/<str:reference>/cancel/", views.OrderCancelView.as_view(), name="order-cancel"),
]
