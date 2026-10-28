"""Initiate API — POST /api/v1/payments/{ref}/initiate/ (docs/payments.md §2.1.1, plan D3 Task 3)."""
import threading

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.commerce.models import Payment
from apps.conftest import make_order

BASE = "/api/v1/payments/"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def created_payment(db, user, artwork_factory):
    art = artwork_factory(title="À initier", price=25000, stock=5)
    return make_order(user, art).payments.get()


def initiate(client, payment, body=None, user=None):
    if user is not None:
        client.force_login(user)
    return client.post(
        f"{BASE}{payment.external_reference}/initiate/",
        body or {"phone": "+237690000001", "operator": "MTN"},
        format="json",
    )


class TestInitiateHappyPath:
    def test_initiate_sets_pending_with_reference(self, client, created_payment, user):
        resp = initiate(client, created_payment, user=user)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == Payment.Status.PENDING
        assert data["external_reference"] == created_payment.external_reference
        assert data["provider_reference"].startswith("MOCK-")
        assert data["initiated_at"]
        created_payment.refresh_from_db()
        assert created_payment.status == Payment.Status.PENDING
        assert created_payment.phone == "+237690000001"
        assert created_payment.operator == "MTN"

    def test_initiate_idempotent_when_already_pending(
        self, client, created_payment, user
    ):
        first = initiate(client, created_payment, user=user)
        second = initiate(client, created_payment, user=user)

        assert first.status_code == second.status_code == 200
        assert first.json()["provider_reference"] == second.json()["provider_reference"]
        assert Payment.objects.filter(order=created_payment.order).count() == 1

    def test_initiate_terminal_conflict(self, client, created_payment, user):
        created_payment.status = Payment.Status.SUCCEEDED
        created_payment.save(update_fields=["status", "updated_at"])

        resp = initiate(client, created_payment, user=user)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "conflict"


class TestInitiateErrors:
    def test_anonymous_401(self, client, created_payment):
        resp = initiate(client, created_payment)

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "unauthenticated"

    def test_other_users_order_404(self, client, created_payment, user_factory):
        other = user_factory()
        resp = initiate(client, created_payment, user=other)

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"

    def test_unknown_reference_404(self, client, db, user):
        client.force_login(user)
        resp = client.post(
            f"{BASE}pas-la-bonne/initiate/",
            {"phone": "+237690000001", "operator": "MTN"},
            format="json",
        )
        assert resp.status_code == 404

    def test_invalid_operator_400(self, client, created_payment, user):
        resp = initiate(
            client,
            created_payment,
            {"phone": "+237690000001", "operator": "NEFARIOUS"},
            user=user,
        )

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "validation_error"

    def test_invalid_phone_400(self, client, created_payment, user):
        resp = initiate(
            client, created_payment, {"phone": "abc", "operator": "MTN"}, user=user
        )

        assert resp.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_initiate_concurrent_single_pending(user_factory, artwork_factory):
    """Deux initiations simultanées → la même référence fournisseur (un seul verrou gagne)."""
    buyer = user_factory()
    art = artwork_factory(title="Concurrence", price=25000, stock=5)
    order = make_order(buyer, art)
    payment = order.payments.get()

    barrier = threading.Barrier(2, timeout=15)
    results: list[tuple[int, str | None]] = []
    results_lock = threading.Lock()

    def worker():
        try:
            client = APIClient()
            client.force_login(buyer)
            barrier.wait()
            resp = client.post(
                f"{BASE}{payment.external_reference}/initiate/",
                {"phone": "+237690000001", "operator": "MTN"},
                format="json",
            )
            data = resp.json() if resp.status_code == 200 else {}
            with results_lock:
                results.append((resp.status_code, data.get("provider_reference")))
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert [code for code, _ in results] == [200, 200]
    references = {ref for _, ref in results}
    assert len(references) == 1, "un seul initiate doit produire la référence"
    payment.refresh_from_db()
    assert payment.status == Payment.Status.PENDING
    assert payment.provider_reference == references.pop()
    assert order.payments.count() == 1
