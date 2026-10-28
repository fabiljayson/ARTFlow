"use client";

import Link from "next/link";
import { MediaImage } from "@/components/media-image";
import { formatXAF } from "@/lib/money";
import type { CartItem } from "@/lib/api";

/**
 * Ligne du panier (docs/screens.md /panier) — la quantité est pilotée par le
 * serveur (stock bornant), ce composant n'affiche que l'état reçu.
 */
export function CartLine({
  item,
  onQuantityChange,
  onRemove,
  busy = false,
}: {
  item: CartItem;
  onQuantityChange: (itemId: number, quantity: number) => void;
  onRemove: (itemId: number) => void;
  busy?: boolean;
}) {
  const { artwork } = item;
  const atMax = item.quantity >= artwork.stock_quantity;
  const atMin = item.quantity <= 1;

  return (
    <li
      className={`glass-card flex flex-col gap-4 p-4 sm:flex-row sm:items-center ${
        item.artwork_unavailable ? "opacity-70" : ""
      }`}
      data-testid={`cart-line-${item.id}`}
    >
      <div className="relative h-24 w-20 shrink-0 overflow-hidden rounded-md bg-surface-muted sm:h-20">
        <MediaImage src={artwork.primary_image_url} alt={artwork.title} fill sizes="80px" />
      </div>

      <div className="min-w-0 flex-1">
        <Link
          href={`/oeuvre/${artwork.slug}`}
          className="font-semibold text-text hover:text-primary-strong"
        >
          {artwork.title}
        </Link>
        <p className="text-sm text-text/70">{artwork.artist_display_name}</p>
        <p className="text-sm font-semibold text-primary-strong">{formatXAF(artwork.price_xaf)}</p>

        {item.artwork_unavailable ? (
          <p className="mt-1 text-xs font-semibold ink-danger">
            Cette œuvre n&apos;est plus disponible — retirez-la du panier.
          </p>
        ) : item.quantity_exceeds_stock ? (
          <p className="mt-1 text-xs font-semibold ink-warning">
            Stock modifié : il ne reste que {artwork.stock_quantity} exemplaire(s).
          </p>
        ) : null}
      </div>

      <div className="flex items-center gap-2" role="group" aria-label={`Quantité — ${artwork.title}`}>
        <button
          type="button"
          aria-label="Diminuer la quantité"
          disabled={busy || atMin}
          onClick={() => onQuantityChange(item.id, item.quantity - 1)}
          className="btn btn-secondary h-8 w-8 px-0 text-base leading-none"
        >
          −
        </button>
        <span className="w-8 text-center font-semibold tabular-nums text-text" aria-live="polite">
          {item.quantity}
        </span>
        <button
          type="button"
          aria-label="Augmenter la quantité"
          disabled={busy || atMax}
          onClick={() => onQuantityChange(item.id, item.quantity + 1)}
          className="btn btn-secondary h-8 w-8 px-0 text-base leading-none"
        >
          +
        </button>
      </div>

      <div className="flex flex-col items-end gap-2">
        <span className="font-bold text-primary-strong" data-testid={`line-total-${item.id}`}>
          {formatXAF(item.line_total_xaf)}
        </span>
        <button
          type="button"
          aria-label="Retirer du panier"
          disabled={busy}
          onClick={() => onRemove(item.id)}
          className="text-sm font-semibold text-text/70 underline-offset-2 hover:text-danger hover:underline"
        >
          Retirer
        </button>
      </div>
    </li>
  );
}
