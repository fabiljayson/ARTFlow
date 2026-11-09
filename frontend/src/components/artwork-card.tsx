import Link from "next/link";
import { PriceTag } from "@/components/price-tag";
import { MediaImage } from "@/components/media-image";
import { VerifiedBadge } from "@/components/verified-badge";
import type { ArtworkSummary } from "@/lib/api";

/**
 * Carte d'œuvre pour la grille du catalogue (docs/screens.md §2).
 * Grille responsive 4/5 comme spécifié dans docs/design.md §4.
 */
export function ArtworkCard({ artwork }: { artwork: ArtworkSummary }) {
  const soldOut = !artwork.is_available;

  return (
    <Link
      href={`/oeuvre/${artwork.slug}`}
      className="group block overflow-hidden rounded-lg glass-card transition-all duration-200 hover:-translate-y-0.5"
    >
      <div className="relative aspect-[4/5] w-full overflow-hidden bg-surface-muted/60">
        <MediaImage
          src={artwork.primary_image_url}
          alt={artwork.title}
          fill
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
          className="object-cover transition duration-300 group-hover:scale-[1.03]"
        />
        {soldOut ? (
          <span className="absolute left-2.5 top-2.5 rounded-full bg-danger/90 px-2.5 py-0.5 text-xs font-semibold text-white shadow-md backdrop-blur-sm">
            Épuisé
          </span>
        ) : null}
      </div>

      <div className="space-y-1.5 p-3.5">
        <p className="truncate text-sm font-semibold text-text group-hover:text-primary-strong transition-colors">
          {artwork.title}
        </p>
        <p className="flex items-center gap-1.5 text-xs text-text/75">
          <span className="truncate">{artwork.artist_display_name}</span>
          {artwork.artist_verified ? <VerifiedBadge /> : null}
        </p>
        <div className="pt-0.5">
          <PriceTag amount={artwork.price_xaf} className="text-sm font-bold text-primary-strong" />
        </div>
        {(artwork.favorite_count > 0 || artwork.sold_count > 0 || artwork.views_7d > 0) ? (
          <p className="flex flex-wrap gap-x-3 pt-1 text-xs text-text/70" aria-label="Popularité de l’œuvre">
            {artwork.views_7d > 0 ? <span>{artwork.views_7d} vue{artwork.views_7d > 1 ? "s" : ""} · 7 j</span> : null}
            {artwork.favorite_count > 0 ? <span>♡ {artwork.favorite_count}</span> : null}
            {artwork.sold_count > 0 ? <span className="font-semibold text-primary-strong">{artwork.sold_count} vendue{artwork.sold_count > 1 ? "s" : ""}</span> : null}
          </p>
        ) : null}
      </div>
    </Link>
  );
}
