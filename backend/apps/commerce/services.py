"""Order/quote services — server-side money rules (docs/payments.md §3, ADR-0006)."""
from apps.catalogue.models import ArtworkStatus
from apps.commerce.models import Cart
from apps.commerce.serializers import artwork_primary_image_url
from apps.core.models import PlatformSettings


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
