"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, getCart } from "@/lib/api";
import { CART_UPDATED_EVENT } from "@/components/cart/cart-events";

/**
 * Lien panier du header (docs/screens.md §1 shell) — affiche le nombre
 * d'articles si connecté, reste invisible pour un visiteur anonyme.
 */
export function CartLink() {
  const [count, setCount] = useState<number | null>(null);
  const [visible, setVisible] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const cart = await getCart();
      setCount(cart.items_count);
      setVisible(true);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setVisible(false);
        return;
      }
      // Erreur réseau : on masque le badge, sans casser le header.
      setVisible(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    window.addEventListener(CART_UPDATED_EVENT, refresh);
    return () => window.removeEventListener(CART_UPDATED_EVENT, refresh);
  }, [refresh]);

  if (!visible) return null;

  return (
    <Link
      href="/panier"
      aria-label={`Panier, ${count ?? 0} article(s)`}
      className="relative inline-flex items-center gap-1 rounded-full px-2 py-1 text-sm font-semibold text-text/80 transition hover:text-primary-strong"
    >
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        className="h-5 w-5"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 0 0-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 0 0-16.536-1.84M7.5 14.25 5.106 5.272M6 20.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm12.75 0a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
        />
      </svg>
      <span className="hidden sm:inline">Panier</span>
      {count !== null && count > 0 ? (
        <span
          data-testid="cart-count"
          className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary-strong px-1 text-[10px] font-bold text-white"
        >
          {count > 99 ? "99+" : count}
        </span>
      ) : null}
    </Link>
  );
}
