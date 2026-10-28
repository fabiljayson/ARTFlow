"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/button";
import { EmptyState } from "@/components/empty-state";
import { ApiError, listOrders, type OrderSummary } from "@/lib/api";
import { formatXAF } from "@/lib/money";
import { orderStatusInk, orderStatusLabel } from "@/lib/order-status";

type Load = "loading" | "ready" | "error";

/** Historique des commandes de l'acheteur (docs/screens.md /commandes). */
export default function CommandesPage() {
  const router = useRouter();
  const [state, setState] = useState<Load>("loading");
  const [orders, setOrders] = useState<OrderSummary[]>([]);

  const load = useCallback(async () => {
    try {
      const data = await listOrders();
      setOrders(data.results);
      setState("ready");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.replace(`/connexion?next=${encodeURIComponent("/commandes")}`);
        return;
      }
      setState("error");
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (state === "loading") {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Mes commandes</h1>
        <div className="mt-6 h-40 animate-pulse rounded-lg bg-surface-muted" aria-busy="true" />
      </main>
    );
  }

  if (state === "error") {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Mes commandes</h1>
        <div className="mt-6 rounded-lg border border-border/40 bg-white/60 p-6 text-center">
          <p className="font-semibold text-text">Impossible de charger vos commandes.</p>
          <Button variant="secondary" className="mt-4" onClick={() => void load()}>
            Réessayer
          </Button>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-bold text-primary-strong">Mes commandes</h1>

      {orders.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="Aucune commande"
            hint="Vos commandes apparaîtront ici une fois confirmées."
            actionLabel="Parcourir le catalogue"
            actionHref="/catalogue"
          />
        </div>
      ) : (
        <ul className="mt-6 space-y-3">
          {orders.map((order) => (
            <li key={order.reference}>
              <Link
                href={`/commandes/${order.reference}`}
                className="glass-card flex flex-wrap items-center justify-between gap-3 p-4 hover:border-primary/50"
              >
                <span>
                  <span className="block font-semibold text-primary-strong">{order.reference}</span>
                  <span className="block text-xs text-text/60">
                    {new Date(order.placed_at).toLocaleDateString("fr-FR", {
                      day: "2-digit",
                      month: "long",
                      year: "numeric",
                    })}
                    {" · "}
                    {order.items_count} article{order.items_count > 1 ? "s" : ""}
                  </span>
                </span>
                <span className="text-right">
                  <span className="block font-semibold text-text">
                    {formatXAF(order.grand_total_xaf)}
                  </span>
                  <span className={`block text-xs font-semibold ${orderStatusInk(order.status)}`}>
                    {orderStatusLabel(order.status)}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
