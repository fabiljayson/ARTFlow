"""PaymentEvent model tests (docs/payments.md §2.1.2, database.md §3)."""
import pytest
from django.db import IntegrityError

from apps.conftest import make_order
from apps.payments.models import PaymentEvent


@pytest.mark.django_db
def test_event_id_unique(db, artwork_factory, user):
    art = artwork_factory(title="Œuvre E", price=10000)
    order = make_order(user, art)
    payment = order.payments.first()

    PaymentEvent.objects.create(
        payment=payment,
        event_id="mock:MOCK-abc:SUCCEEDED",
        kind=PaymentEvent.Kind.WEBHOOK_RECEIVED,
        status_after="SUCCEEDED",
        signature_valid=True,
        payload={"event_id": "mock:MOCK-abc:SUCCEEDED"},
    )

    with pytest.raises(IntegrityError):
        PaymentEvent.objects.create(
            payment=payment,
            event_id="mock:MOCK-abc:SUCCEEDED",
            kind=PaymentEvent.Kind.STATUS_POLL,
            status_after="FAILED",
            payload={},
        )


@pytest.mark.django_db
def test_event_fields_and_ordering(db, artwork_factory, user):
    art = artwork_factory(title="Œuvre F", price=10000)
    order = make_order(user, art)
    payment = order.payments.first()

    event = PaymentEvent.objects.create(
        payment=payment,
        event_id="evt-1",
        kind=PaymentEvent.Kind.WEBHOOK_RECEIVED,
        status_after="PENDING",
        signature_valid=True,
        payload={"event_id": "evt-1"},
    )
    assert event.received_at is not None
    assert event.payment_id == payment.pk
    assert list(payment.events.all()) == [event]
    # Par défaut, une transition locale sans signature.
    local = PaymentEvent.objects.create(
        payment=payment,
        event_id="local:xyz",
        kind=PaymentEvent.Kind.STATE_CHANGE,
        status_after="PENDING",
    )
    assert local.signature_valid is False
    assert local.payload == {}
