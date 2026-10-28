"""Order/quote services — server-side money rules (docs/payments.md §3, ADR-0006)."""
import hashlib
import json
import secrets
from datetime import timedelta
from uuid import uuid4

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.catalogue.models import Artwork, ArtworkStatus
from apps.commerce.models import Cart, CartItem, Order, OrderItem, Payment, StockReservation
from apps.commerce.serializers import artwork_primary_image_url
from apps.core.exceptions import IdempotencyConflict
from apps.core.models import PlatformSettings


def get_or_create_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def compute_fingerprint(data) -> str:
    """sha256 du corps checkout canonique (clés triées) — détection replay à corps modifié."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def address_snapshot(address) -> dict:
    fields = ["label", "recipient_name", "line1", "line2", "city", "region", "phone"]
    return {f: getattr(address, f) for f in fields}


def _generate_reference() -> str:
    year = timezone.now().year
    for _ in range(20):
        candidate = f"ORD-{year}-{secrets.randbelow(1_000_000):06d}"
        if not Order.objects.filter(reference=candidate).exists():
            return candidate
    raise RuntimeError("Impossible de générer une référence de commande unique.")


def checkout_payload(order: Order) -> dict:
    payment = order.payments.order_by("created_at").first()
    return {
        "order_reference": order.reference,
        "status": order.status,
        "grand_total_xaf": order.grand_total_xaf,
        "placed_at": order.placed_at.isoformat(),
        "payment": {
            "provider": payment.provider if payment else None,
            "status": payment.status if payment else None,
            "redirect_info": None,  # initiation CamPay/Mock arrive en D3
        },
    }


def create_checkout(
    user, *, idempotency_key: str, address, buyer_note: str, fingerprint: str
) -> tuple[dict, bool]:
    """Crée la commande multi-vendeur : verrou artworks, réservations TTL, instantanés figés.

    Retourne (payload, created) — created=False pour un replay idempotent (HTTP 200).
    """
    existing = Order.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        if existing.buyer_id != user.pk or existing.request_fingerprint != fingerprint:
            raise IdempotencyConflict()
        return checkout_payload(existing), False

    cart = get_or_create_cart(user)
    with transaction.atomic():
        artwork_ids = sorted(cart.items.values_list("artwork_id", flat=True))
        if not artwork_ids:
            raise ValidationError({"cart": "Le panier est vide."})

        # Verrou lignes triées par pk (anti-deadlock) — la base d'une concurrence sûre.
        artworks = {
            a.pk: a
            for a in Artwork.objects.select_for_update()
            .select_related("artist")
            .filter(pk__in=artwork_ids)
            .order_by("pk")
        }
        items = list(cart.items.select_related("artwork__artist").order_by("artwork_id"))

        blocking = []
        for item in items:
            artwork = artworks[item.artwork_id]
            if artwork.status != ArtworkStatus.PUBLISHED:
                blocking.append(
                    {
                        "artwork_id": artwork.pk,
                        "code": "artwork_unavailable",
                        "message": f"« {artwork.title} » n'est plus disponible.",
                        "quantity_demandee": item.quantity,
                    }
                )
                continue
            # Stock libre = stock − réservations ACTIVE (même expirées : conservateur,
            # le cron expire_stock_reservations purge toutes les 5 min).
            reserved = (
                StockReservation.objects.filter(
                    artwork_id=artwork.pk, status=StockReservation.Status.ACTIVE
                ).aggregate(total=Sum("quantity"))["total"]
                or 0
            )
            free = artwork.stock_quantity - reserved
            if item.quantity > free:
                blocking.append(
                    {
                        "artwork_id": artwork.pk,
                        "code": "stock_insufficient",
                        "message": f"Stock insuffisant pour « {artwork.title} » : "
                        f"{free} exemplaire(s) encore disponible(s).",
                        "quantity_demandee": item.quantity,
                    }
                )
        if blocking:
            raise ValidationError({"items": blocking})

        quote = compute_quote(cart)
        quote_by_artwork = {i["artwork_id"]: i for i in quote["items"]}
        now = timezone.now()
        ttl_minutes = PlatformSettings.get().reservation_ttl_minutes

        order = Order.objects.create(
            buyer=user,
            reference=_generate_reference(),
            status=Order.Status.PENDING_PAYMENT,
            subtotal_items_xaf=quote["subtotal_items_xaf"],
            shipping_total_xaf=quote["shipping_total_xaf"],
            fees_total_xaf=quote["fees_total_xaf"],
            grand_total_xaf=quote["grand_total_xaf"],
            shipping_address_snapshot=address_snapshot(address),
            buyer_note=buyer_note or "",
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            placed_at=now,
        )
        for item in items:
            artwork = artworks[item.artwork_id]
            line = quote_by_artwork[artwork.pk]
            OrderItem.objects.create(
                order=order,
                artwork=artwork,
                artist=artwork.artist,
                title_snapshot=artwork.title[:200],
                unit_price_xaf=line["unit_price_xaf"],
                quantity=item.quantity,
                line_total_xaf=line["line_total_xaf"],
                commission_rate_bps=line["commission_rate_bps"],
                commission_xaf=line["commission_xaf"],
                artist_net_xaf=line["artist_net_xaf"],
            )
            StockReservation.objects.create(
                artwork=artwork,
                order=order,
                quantity=item.quantity,
                expires_at=now + timedelta(minutes=ttl_minutes),
            )
        Payment.objects.create(
            order=order,
            provider=Payment.Provider.MOCK,
            external_reference=uuid4().hex,
            amount_xaf=order.grand_total_xaf,
        )
        CartItem.objects.filter(cart=cart).delete()

    return checkout_payload(order), True


def commission_for(unit_price_xaf: int, quantity: int, rate_bps: int) -> int:
    """floor() — arrondi inférieur, favorise l'artiste d'au plus 1 XAF (ADR-0006)."""
    return (unit_price_xaf * quantity * rate_bps) // 10000


def compute_quote(cart: Cart, request=None) -> dict:
    """Recalcule tous les montants depuis la base — aucun prix n'est stocké ni accepté du client."""
    rate_bps = PlatformSettings.get().commission_rate_bps
    items = list(
        cart.items.select_related("artwork", "artwork__artist").prefetch_related("artwork__media")
    )

    quote_items = []
    blocking_issues = []
    for item in items:
        artwork = item.artwork
        unit_price = artwork.price_xaf
        line_total = unit_price * item.quantity
        commission = commission_for(unit_price, item.quantity, rate_bps)
        quote_items.append(
            {
                "artwork_id": artwork.pk,
                "slug": artwork.slug,
                "title": artwork.title,
                "quantity": item.quantity,
                "unit_price_xaf": unit_price,
                "line_total_xaf": line_total,
                "artist": {
                    "id": artwork.artist_id,
                    "display_name": artwork.artist.display_name,
                },
                "commission_rate_bps": rate_bps,
                "commission_xaf": commission,
                "artist_net_xaf": line_total - commission,
                "primary_image_url": artwork_primary_image_url(artwork, request),
            }
        )
        if artwork.status != ArtworkStatus.PUBLISHED:
            blocking_issues.append(
                {
                    "artwork_id": artwork.pk,
                    "code": "artwork_unavailable",
                    "message": f"« {artwork.title} » n'est plus disponible.",
                    "quantity_demandee": item.quantity,
                }
            )
        elif item.quantity > artwork.stock_quantity:
            blocking_issues.append(
                {
                    "artwork_id": artwork.pk,
                    "code": "stock_insufficient",
                    "message": f"Stock insuffisant pour « {artwork.title} » : il reste "
                    f"{artwork.stock_quantity} exemplaire(s).",
                    "quantity_demandee": item.quantity,
                }
            )

    # 1 frais de livraison par vendeur distinct, dans l'ordre d'apparition du panier.
    shipping = []
    seen_artist_ids = set()
    for item in items:
        artist = item.artwork.artist
        if artist.pk in seen_artist_ids:
            continue
        seen_artist_ids.add(artist.pk)
        shipping.append(
            {
                "artist_id": artist.pk,
                "display_name": artist.display_name,
                "shipping_fee_xaf": artist.shipping_base_fee_xaf,
            }
        )

    subtotal = sum(i["line_total_xaf"] for i in quote_items)
    shipping_total = sum(s["shipping_fee_xaf"] for s in shipping)
    return {
        "items": quote_items,
        "shipping": shipping,
        "subtotal_items_xaf": subtotal,
        "shipping_total_xaf": shipping_total,
        "fees_total_xaf": 0,
        "grand_total_xaf": subtotal + shipping_total,
        "items_count": sum(i["quantity"] for i in quote_items),
        "blocking_issues": blocking_issues,
    }
