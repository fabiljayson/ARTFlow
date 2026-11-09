from datetime import timedelta

from django.db.models import Count, F, IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.catalogue.models import Artwork, ArtworkStatus, ArtworkView, Favorite
from apps.commerce.models import OrderItem

PAID_ORDER_STATUSES = ("PAID", "PROCESSING", "SHIPPED", "DELIVERED", "PARTIALLY_REFUNDED")


def with_stats(queryset):
    now = timezone.now()
    since = now - timedelta(days=7)
    favorites = Favorite.objects.filter(artwork_id=OuterRef("pk"))
    views = ArtworkView.objects.filter(artwork_id=OuterRef("pk"))
    sold = OrderItem.objects.filter(artwork_id=OuterRef("pk"), order__status__in=PAID_ORDER_STATUSES)
    return queryset.annotate(
        favorite_count=Coalesce(Subquery(favorites.order_by().values("artwork_id").annotate(n=Count("pk")).values("n")[:1]), Value(0), output_field=IntegerField()),
        sold_count=Coalesce(Subquery(sold.order_by().values("artwork_id").annotate(n=Sum("quantity")).values("n")[:1]), Value(0), output_field=IntegerField()),
        views_7d=Coalesce(Subquery(views.filter(created_at__gte=since).order_by().values("artwork_id").annotate(n=Count("pk")).values("n")[:1]), Value(0), output_field=IntegerField()),
        favs_7d=Coalesce(Subquery(favorites.filter(created_at__gte=since).order_by().values("artwork_id").annotate(n=Count("pk")).values("n")[:1]), Value(0), output_field=IntegerField()),
    ).annotate(trending_score=F("views_7d") + 3 * F("favs_7d"))


def artist_stats(artist):
    artworks = artist.artworks.filter(status=ArtworkStatus.PUBLISHED)
    return {
        "works": artworks.count(),
        "sold": OrderItem.objects.filter(artwork__in=artworks, order__status__in=PAID_ORDER_STATUSES).aggregate(total=Sum("quantity"))["total"] or 0,
        "views": artworks.aggregate(total=Sum("view_count"))["total"] or 0,
        "favorites": Favorite.objects.filter(artwork__in=artworks).count(),
    }
