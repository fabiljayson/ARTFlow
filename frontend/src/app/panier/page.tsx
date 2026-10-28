"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/button";
import { CartLine } from "@/components/cart/cart-line";
import { EmptyState } from "@/components/empty-state";
import { ApiError, getCart, removeCartItem, updateCartItem, type Cart } from "@/lib/api";
import { formatXAF } from "@/lib/money";

type Load = "loading" | "ready" | "error";

/**
 * Panier (docs/screens.md /panier) — relecture serveur : les prix et les totaux
 * viennent toujours de `GET /cart/`, jamais calculés côté client.
 */
export default function PanierPage() {
  const router = useRouter();
  const [state, setState] = useState<Load>("loading");
  const [cart, setCart] = useState<Cart | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getCart();
      setCart(data);
      setState("ready");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.replace(`/connexion?next=${encodeURIComponent("/panier")}`);
        return;
      }
      setState("error");
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleQuantity(itemId: number, quantity: number) {
    setBusy(true);
    setActionError(null);
    try {
      await updateCartItem(itemId, quantity);
      await load();
    } catch (error) {
      setActionError(
        error instanceof ApiError ? error.message : "Impossible de mettre à jour la quantité.",
      );
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove(itemId: number) {
    setBusy(true);
    setActionError(null);
    try {
      await removeCartItem(itemId);
      await load();
    } catch (error) {
      setActionError(
        error instanceof ApiError ? error.message : "Impossible de retirer l'article.",
      );
      await load();
    } finally {
      setBusy(false);
    }
  }

  if (state === "loading") {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Panier</h1>
        <div className="mt-6 h-40 animate-pulse rounded-lg bg-surface-muted" aria-busy="true" />
      </main>
    );
  }

  if (state === "error") {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Panier</h1>
        <div className="mt-6 rounded-lg border border-border/40 bg-white/60 p-6 text-center">
          <p className="font-semibold text-text">Impossible de charger votre panier.</p>
          <p className="mt-1 text-sm text-text/70">Vérifiez votre connexion puis réessayez.</p>
          <Button variant="secondary" className="mt-4" onClick={() => void load()}>
            Réessayer
          </Button>
        </div>
      </main>
    );
  }

  const isEmpty = !cart || cart.items.length === 0;

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-bold text-primary-strong">Panier</h1>

      {isEmpty ? (
        <div className="mt-6">
          <EmptyState
            title="Votre panier est vide"
            hint="Parcourez le catalogue pour découvrir les œuvres de nos artistes."
            actionLabel="Parcourir le catalogue"
            actionHref="/catalogue"
          />
        </div>
      ) : (
        <>
          {actionError ? (
            <p role="alert" className="mt-4 rounded-md bg-danger/10 p-3 text-sm font-semibold ink-danger">
              {actionError}
            </p>
          ) : null}

          <ul className="mt-6 space-y-4">
            {cart?.items.map((item) => (
              <CartLine
                key={item.id}
                item={item}
                busy={busy}
                onQuantityChange={(id, qty) => void handleQuantity(id, qty)}
                onRemove={(id) => void handleRemove(id)}
              />
            ))}
          </ul>

          <section className="glass-card mt-6 space-y-3 p-5" aria-label="Récapitulatif">
            <div className="flex justify-between text-sm text-text/75">
              <span>Articles ({cart?.items_count ?? 0})</span>
              <span className="font-semibold text-text">{formatXAF(cart?.items_total_xaf ?? 0)}</span>
            </div>
            <div className="flex justify-between text-sm text-text/75">
              <span>Livraison</span>
              <span>Calculée au checkout</span>
            </div>
            <div className="flex justify-between border-t border-border/30 pt-3">
              <span className="font-semibold text-text">Sous-total</span>
              <span className="text-lg font-bold text-primary-strong">
                {formatXAF(cart?.items_total_xaf ?? 0)}
              </span>
            </div>
            <Button className="w-full" onClick={() => router.push("/checkout")}>
              Passer la commande
            </Button>
            <p className="text-center text-xs text-text/70">
              Le paiement arrive en phase suivante — vous ne serez pas débité pour
              l&apos;instant.
            </p>
            <Link
              href="/catalogue"
              className="block text-center text-sm font-semibold text-primary-strong hover:underline"
            >
              Continuer mes achats
            </Link>
          </section>
        </>
      )}
    </main>
  );
}
