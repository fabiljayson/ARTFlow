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
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/20 pb-5">
        <h1 className="text-3xl font-bold tracking-tight text-primary-strong">Commande {order.reference}</h1>
        <span
          className={`rounded-full glass-pill px-3.5 py-1 text-sm font-bold shadow-xs ${orderStatusInk(order.status)}`}
        >
          {orderStatusLabel(order.status)}
        </span>
      </div>

      {canCancel ? (
        <div
          role="status"
          className="mt-6 rounded-2xl border border-warning/40 bg-warning/10 p-5 text-sm shadow-sm"
        >
          <p className="font-bold ink-warning">Paiement en attente.</p>
          <p className="mt-1 leading-relaxed text-text/85">
            Cette commande n&apos;est pas encore payée : les articles sont réservés
            temporairement. Vous pouvez l&apos;annuler tant que le paiement n&apos;est pas
            effectué.
          </p>
          <Link
            href={`/commandes/${order.reference}/paiement`}
            className="btn btn-primary mt-4 inline-flex px-5 py-2.5 text-sm shadow-md"
          >
            Payer maintenant
          </Link>
        </div>
      ) : null}

      {actionError ? (
        <p role="alert" className="mt-4 rounded-xl border border-danger/40 bg-danger/10 p-3.5 text-sm font-semibold ink-danger">
          {actionError}
        </p>
      ) : null}

      <section className="glass-strong rounded-2xl mt-6 space-y-4 p-6 shadow-md" aria-labelledby="order-items">
        <h2 id="order-items" className="text-lg font-bold text-primary-strong">
          Articles ({order.items.length})
        </h2>
        <ul className="space-y-3">
          {order.items.map((item) => (
            <li key={item.id} className="flex justify-between gap-3 text-sm">
              <span className="text-text font-medium">
                {item.title_snapshot}
                <span className="block text-xs text-text/70">
                  {item.artist.display_name} · ×{item.quantity}
                </span>
              </span>
              <span className="font-bold text-primary-strong">{formatXAF(item.line_total_xaf)}</span>
            </li>
          ))}
        </ul>
        <div className="space-y-1.5 border-t border-border/20 pt-3.5 text-sm text-text/80">
          <div className="flex justify-between">
            <span>Articles</span>
            <span className="font-semibold text-text">{formatXAF(order.subtotal_items_xaf)}</span>
          </div>
          <div className="flex justify-between">
            <span>Livraison</span>
            <span className="font-semibold text-text">{formatXAF(order.shipping_total_xaf)}</span>
          </div>
          <div className="flex justify-between border-t border-border/20 pt-3 font-bold text-text">
            <span className="text-base">Total</span>
            <span className="text-xl font-extrabold text-primary-strong">
              {formatXAF(order.grand_total_xaf)}
            </span>
          </div>
        </div>
      </section>

      <section className="glass-strong rounded-2xl mt-6 space-y-3 p-6 text-sm shadow-md" aria-labelledby="order-shipping">
        <h2 id="order-shipping" className="text-lg font-bold text-primary-strong">
          Livraison
        </h2>
        <p className="text-text/85">
          {address.recipient_name ?? "—"} — {address.line1 ?? ""}
          {address.line2 ? `, ${address.line2}` : ""}
        </p>
        <p className="text-text/85">
          {address.city ?? ""}
          {address.region ? `, ${address.region}` : ""}
          {address.phone ? ` · ${address.phone}` : ""}
        </p>
        {order.buyer_note ? (
          <p className="text-text/75 italic border-t border-border/20 pt-2">Note : {order.buyer_note}</p>
        ) : null}
        {order.payment ? (
          <p className="text-text/80 border-t border-border/20 pt-2">
            Paiement : {order.payment.provider} — {order.payment.status}
          </p>
        ) : null}
      </section>

      <section className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <Link
          href="/commandes"
          className="text-sm font-semibold text-primary-strong hover:text-primary transition-colors"
        >
          ← Retour à mes commandes
        </Link>
        {canCancel ? (
          <Button variant="danger" onClick={() => void handleCancel()} disabled={busy} className="shadow-sm">
            {busy ? "Annulation…" : "Annuler la commande"}
          </Button>
        ) : null}
      </section>
    </main>
  );
}
