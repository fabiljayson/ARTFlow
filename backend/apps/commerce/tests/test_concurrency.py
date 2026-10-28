"""Checkout concurrency — 2 acheteurs en parallèle, stock jamais négatif (plan D2 Task 3, §5 E)."""
import threading

import pytest
from django.db import connection, models
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Address
from apps.commerce.models import Order, StockReservation

CHECKOUT = "/api/v1/checkout/"


@pytest.mark.django_db(transaction=True)
def test_two_parallel_checkouts_exactly_one_wins(
    user_factory, artwork_factory, category, seller_profile
):
    """Stock 2, deux acheteurs qui réclament 2 exemplaires chacun → 1×201 + 1×400, stock ≥ 0."""
    art = artwork_factory(title="Pièce unique en double", price=50000, stock=2)
    assert art.stock_quantity == 2

    buyers = [user_factory(), user_factory()]
    for i, buyer in enumerate(buyers):
        from apps.commerce.models import Cart, CartItem

        cart = Cart.objects.create(user=buyer)
        CartItem.objects.create(cart=cart, artwork=art, quantity=2)
        Address.objects.create(
            user=buyer,
            label=f"Maison {i}",
            recipient_name=f"Acheteur {i}",
            line1="Rue 1",
            city="Yaoundé",
            phone=f"+23769000001{i}",
        )

    barrier = threading.Barrier(2, timeout=15)
    results: list[int] = []
    results_lock = threading.Lock()

    def worker(buyer):
        try:
            client = APIClient()
            client.force_login(buyer)
            address = buyer.addresses.first()
            barrier.wait()
            resp = client.post(
                CHECKOUT,
                {"address_id": address.pk},
                format="json",
                HTTP_IDEMPOTENCY_KEY=f"race-{buyer.pk}",
            )
            with results_lock:
                results.append(resp.status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(b,)) for b in buyers]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sorted(results) == [
        status.HTTP_201_CREATED,
        status.HTTP_400_BAD_REQUEST,
    ], f"résultats inattendus : {results}"
    art.refresh_from_db()
    assert art.stock_quantity >= 0
    active_total = StockReservation.objects.filter(
        artwork=art, status=StockReservation.Status.ACTIVE
    ).aggregate(total=models.Sum("quantity"))["total"] or 0
    assert active_total <= 2
    assert Order.objects.count() == 1
