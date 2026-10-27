import Link from "next/link";
import { PriceTag } from "@/components/price-tag";
import { MediaImage } from "@/components/media-image";
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
      className="group block overflow-hidden rounded-lg border border-border/25 bg-white/70 transition hover:border-primary/40 hover:shadow-sm"
    >
      <div className="relative aspect-[4/5] w-full overflow-hidden bg-surface-muted">
        <MediaImage
          src={artwork.primary_image_url}
          alt={artwork.title}
          fill
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
          className="transition duration-300 group-hover:scale-[1.02]"
        />
        {soldOut ? (
          <span className="absolute left-2 top-2 rounded-md bg-danger/90 px-2 py-0.5 text-xs font-semibold text-white">
            Épuisé
          </span>
        ) : null}
      </div>

      <div className="space-y-1 p-3">
        <p className="truncate text-sm font-semibold text-text">{artwork.title}</p>
        <p className="truncate text-xs text-text/60">{artwork.artist_display_name}</p>
        <PriceTag amount={artwork.price_xaf} className="text-sm" />
      </div>
    </Link>
  );
}
