"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/button";
import { ApiError, addCartItem } from "@/lib/api";
import { CART_UPDATED_EVENT } from "@/components/cart/cart-events";

/**
 * Bouton « Ajouter au panier » de la fiche œuvre (docs/screens.md §2).
 * Anonyme → redirection vers la connexion ; erreur serveur (stock…) → message affiché.
 */
export function AddToCartButton({ artworkId }: { artworkId: number }) {
  const router = useRouter();
  const pathname = usePathname();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAdd() {
    setBusy(true);
    setError(null);
    try {
      await addCartItem(artworkId, 1);
      setDone(true);
      window.dispatchEvent(new Event(CART_UPDATED_EVENT));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.replace(`/connexion?next=${encodeURIComponent(pathname)}`);
        return;
      }
      setError(err instanceof ApiError ? err.message : "Impossible d'ajouter cette œuvre.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-6 space-y-2">
      <Button onClick={() => void handleAdd()} disabled={busy} className="w-full">
        {busy ? "Ajout en cours…" : done ? "Ajouté au panier ✓" : "Ajouter au panier"}
      </Button>
      {error ? (
        <p role="alert" className="text-sm font-semibold ink-danger">
          {error}
        </p>
      ) : null}
      {done && !error ? (
        <Link
          href="/panier"
          className="block text-center text-sm font-semibold text-primary-strong hover:underline"
        >
          Voir mon panier
        </Link>
      ) : null}
    </div>
  );
}
