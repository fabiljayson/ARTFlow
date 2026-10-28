"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/button";
import { ApiError, cancelOrder, getOrder, type OrderDetail } from "@/lib/api";
import { formatXAF } from "@/lib/money";
import { orderStatusInk, orderStatusLabel } from "@/lib/order-status";

type Load = "loading" | "ready" | "error";

/**
 * Détail d'une commande (docs/screens.md /commandes/[ref]) — prix
 * instantanés figés, bannière d'attente de paiement et action Annuler.
 */
export default function CommandeDetailPage() {
  const router = useRouter();
  const params = useParams<{ ref: string }>();
  const reference = params.ref;
  const [state, setState] = useState<Load>("loading");
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getOrder(reference);
      setOrder(data);
      setState("ready");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.replace(`/connexion?next=${encodeURIComponent(`/commandes/${reference}`)}`);
        return;
      }
      if (error instanceof ApiError && error.status === 404) {
        setState("error");
        return;
      }
      setState("error");
    }
  }, [reference, router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCancel() {
    setBusy(true);
    setActionError(null);
    try {
      const updated = await cancelOrder(reference);
      setOrder(updated);
    } catch (error) {
      setActionError(
        error instanceof ApiError
          ? error.message
          : "Impossible d'annuler cette commande.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (state === "loading") {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Commande</h1>
        <div className="mt-6 h-40 animate-pulse rounded-lg bg-surface-muted" aria-busy="true" />
      </main>
    );
  }

  if (state === "error" || !order) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Commande</h1>
        <div className="mt-6 rounded-lg border border-border/40 bg-white/60 p-6 text-center">
          <p className="font-semibold text-text">Commande introuvable.</p>
          <Link
            href="/commandes"
            className="mt-3 inline-block font-semibold text-primary-strong hover:underline"
          >
            Retour à mes commandes
          </Link>
        </div>
      </main>
    );
  }

  const address = order.shipping_address_snapshot;
  const canCancel = order.status === "PENDING_PAYMENT";

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-primary-strong">Commande {order.reference}</h1>
        <span
          className={`rounded-full bg-surface-muted px-3 py-1 text-sm font-semibold ${orderStatusInk(order.status)}`}
        >
          {orderStatusLabel(order.status)}
        </span>
      </div>

      {canCancel ? (
        <div
          role="status"
          className="mt-4 rounded-md border border-warning/40 bg-warning/10 p-4 text-sm"
        >
          <p className="font-semibold ink-warning">Paiement en attente.</p>
          <p className="mt-1 text-text/80">
            Cette commande n&apos;est pas encore payée : les articles sont réservés
            temporairement. Vous pouvez l&apos;annuler tant que le paiement n&apos;est pas
            effectué.
          </p>
          <Link
            href={`/commandes/${order.reference}/paiement`}
            className="btn btn-primary mt-3 inline-flex px-4 py-2 text-sm"
          >
            Payer maintenant
          </Link>
        </div>
      ) : null}

      {actionError ? (
        <p role="alert" className="mt-4 rounded-md bg-danger/10 p-3 text-sm font-semibold ink-danger">
          {actionError}
        </p>
      ) : null}

      <section className="glass-card mt-6 space-y-3 p-5" aria-labelledby="order-items">
        <h2 id="order-items" className="font-semibold text-primary-strong">
          Articles ({order.items.length})
        </h2>
        <ul className="space-y-3">
          {order.items.map((item) => (
            <li key={item.id} className="flex justify-between gap-3 text-sm">
              <span className="text-text">
                {item.title_snapshot}
                <span className="block text-xs text-text/60">
                  {item.artist.display_name} · ×{item.quantity}
                </span>
              </span>
              <span className="font-semibold text-text">{formatXAF(item.line_total_xaf)}</span>
            </li>
          ))}
        </ul>
        <div className="space-y-1 border-t border-border/30 pt-3 text-sm text-text/75">
          <div className="flex justify-between">
            <span>Articles</span>
            <span>{formatXAF(order.subtotal_items_xaf)}</span>
          </div>
          <div className="flex justify-between">
            <span>Livraison</span>
            <span>{formatXAF(order.shipping_total_xaf)}</span>
          </div>
          <div className="flex justify-between border-t border-border/30 pt-3 font-semibold text-text">
            <span>Total</span>
            <span className="text-lg font-bold text-primary-strong">
              {formatXAF(order.grand_total_xaf)}
            </span>
          </div>
        </div>
      </section>

      <section className="glass-card mt-6 space-y-2 p-5 text-sm" aria-labelledby="order-shipping">
        <h2 id="order-shipping" className="font-semibold text-primary-strong">
          Livraison
        </h2>
        <p className="text-text/80">
          {address.recipient_name ?? "—"} — {address.line1 ?? ""}
          {address.line2 ? `, ${address.line2}` : ""}
        </p>
        <p className="text-text/80">
          {address.city ?? ""}
          {address.region ? `, ${address.region}` : ""}
          {address.phone ? ` · ${address.phone}` : ""}
        </p>
        {order.buyer_note ? (
          <p className="text-text/70 italic">Note : {order.buyer_note}</p>
        ) : null}
        {order.payment ? (
          <p className="text-text/70">
            Paiement : {order.payment.provider} — {order.payment.status}
          </p>
        ) : null}
      </section>

      <section className="mt-6 flex flex-wrap gap-3">
        {canCancel ? (
          <Button variant="danger" onClick={() => void handleCancel()} disabled={busy}>
            {busy ? "Annulation…" : "Annuler la commande"}
          </Button>
        ) : null}
        <Link
          href="/commandes"
          className="inline-flex items-center rounded-md border border-border/50 px-4 py-2 text-sm font-semibold text-text hover:bg-surface-muted"
        >
          Retour à mes commandes
        </Link>
      </section>
    </main>
  );
}
