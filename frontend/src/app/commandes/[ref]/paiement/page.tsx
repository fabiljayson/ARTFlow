"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/button";
import {
  ApiError,
  getOrder,
  initiatePayment,
  simulatePayment,
  type OrderDetail,
} from "@/lib/api";
import { formatXAF } from "@/lib/money";

type Load = "loading" | "ready" | "error";
type Operator = "MTN" | "ORANGE";

const POLL_MS = 3000;
const REDIRECT_MS = 1500;

/**
 * Page de paiement d'une commande (docs/screens.md /commandes/[ref]/paiement) —
 * initiation USSD simulée, polling toutes les 3 s et simulateur MOCK.
 */
export default function PaiementPage() {
  const router = useRouter();
  const params = useParams<{ ref: string }>();
  const reference = params.ref;
  const [state, setState] = useState<Load>("loading");
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [phone, setPhone] = useState("+237");
  const [operator, setOperator] = useState<Operator>("MTN");
  const [initiating, setInitiating] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  // Le flux n'est actif que si la commande était impayée au montage ;
  // sinon (déjà payée) on repousse vers le détail sans afficher l'écran succès.
  const flowRef = useRef(false);
  const pushedRef = useRef(false);

  const load = useCallback(async () => {
    try {
      const data = await getOrder(reference);
      setOrder(data);
      setState("ready");
      if (!flowRef.current) {
        if (data.status !== "PENDING_PAYMENT") {
          router.replace(`/commandes/${reference}`);
        } else {
          flowRef.current = true;
        }
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.replace(
          `/connexion?next=${encodeURIComponent(`/commandes/${reference}/paiement`)}`,
        );
        return;
      }
      setState("error");
    }
  }, [reference, router]);

  useEffect(() => {
    void load();
  }, [load]);

  const payment = order?.payment ?? null;
  const paymentStatus = payment?.status ?? null;
  const paid =
    !!order && (order.status === "PAID" || paymentStatus === "SUCCEEDED");
  const failed = paymentStatus === "FAILED";

  // Poll toutes les 3 s tant que le paiement n'est pas tranché.
  useEffect(() => {
    if (state !== "ready") return;
    if (paymentStatus !== "CREATED" && paymentStatus !== "PENDING") return;
    const id = setInterval(() => {
      void load();
    }, POLL_MS);
    return () => clearInterval(id);
  }, [state, paymentStatus, load]);

  // Succès : écran confirmé, puis poussée vers le détail.
  useEffect(() => {
    if (!paid || !flowRef.current || pushedRef.current) return;
    pushedRef.current = true;
    const id = setTimeout(() => router.push(`/commandes/${reference}`), REDIRECT_MS);
    return () => clearTimeout(id);
  }, [paid, reference, router]);

  async function handleInitiate(event: React.FormEvent) {
    event.preventDefault();
    if (!payment) return;
    setInitiating(true);
    setActionError(null);
    try {
      await initiatePayment(payment.external_reference, {
        phone: phone.trim(),
        operator,
      });
      await load();
    } catch (error) {
      setActionError(
        error instanceof ApiError
          ? error.message
          : "Impossible de démarrer le paiement. Réessayez.",
      );
    } finally {
      setInitiating(false);
    }
  }

  async function handleSimulate(scenario: "success" | "fail") {
    if (!payment) return;
    setSimulating(true);
    setActionError(null);
    try {
      await simulatePayment(payment.external_reference, scenario);
      await load();
    } catch (error) {
      setActionError(
        error instanceof ApiError
          ? error.message
          : "Le scénario simulé n'a pas pu être exécuté.",
      );
    } finally {
      setSimulating(false);
    }
  }

  if (state === "loading") {
    return (
      <main className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Paiement</h1>
        <div
          className="mt-6 h-40 animate-pulse rounded-lg bg-surface-muted"
          aria-busy="true"
        />
      </main>
    );
  }

  if (state === "error" || !order) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Paiement</h1>
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

  if (paid) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Paiement</h1>
        <div
          role="status"
          className="mt-6 rounded-lg border border-success/40 bg-success/10 p-6 text-center"
        >
          <p className="text-lg font-bold ink-success">Paiement confirmé !</p>
          <p className="mt-2 text-sm text-text/80">
            Votre commande {order.reference} est payée — {formatXAF(order.grand_total_xaf)}{" "}
            réglés.
          </p>
          <Link
            href={`/commandes/${reference}`}
            className="mt-4 inline-block font-semibold text-primary-strong hover:underline"
          >
            Voir ma commande
          </Link>
        </div>
      </main>
    );
  }

  if (failed) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Paiement</h1>
        <div
          role="alert"
          className="mt-6 rounded-lg border border-danger/40 bg-danger/10 p-6 text-center"
        >
          <p className="text-lg font-bold ink-danger">Le paiement a échoué.</p>
          {payment?.failure_reason ? (
            <p className="mt-2 text-sm text-text/80">{payment.failure_reason}</p>
          ) : null}
          <p className="mt-2 text-sm text-text/70">
            Le stock réservé a été libéré : vos articles sont de nouveau disponibles.
          </p>
          <Link
            href="/panier"
            className="mt-4 inline-block font-semibold text-primary-strong hover:underline"
          >
            Retour au panier
          </Link>
        </div>
      </main>
    );
  }

  if (order.status !== "PENDING_PAYMENT") {
    // Remplacement déjà en route (annulée entre-temps) : ne rien afficher.
    return null;
  }

  const mockSimulator =
    payment?.provider === "MOCK" && payment.status === "PENDING";

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-primary-strong">Payer la commande</h1>
        <span className="rounded-full bg-surface-muted px-3 py-1 text-sm font-semibold text-text">
          {order.reference}
        </span>
      </div>

      <div className="glass-card mt-6 p-5">
        <p className="text-sm text-text/75">Montant à régler</p>
        <p className="text-3xl font-bold text-primary-strong">
          {formatXAF(order.grand_total_xaf)}
        </p>
        <p className="mt-1 text-xs text-text/60">{order.currency} · livraison incluse</p>
      </div>

      {paymentStatus === "PENDING" ? (
        <div className="mt-6 space-y-4">
          <div
            role="status"
            className="rounded-md border border-warning/40 bg-warning/10 p-4 text-sm"
          >
            <p className="font-semibold ink-warning">En attente de confirmation…</p>
            <p className="mt-1 text-text/80">
              Un message USSD vient d&apos;être envoyé sur votre téléphone. Confirmez la
              demande, cette page se met à jour toute seule.
            </p>
          </div>

          {mockSimulator ? (
            <div className="glass-card p-5">
              <p className="text-sm font-semibold text-text">
                Mode démo — passerelle simulée
              </p>
              <p className="mt-1 text-xs text-text/60">
                Aucun paiement réel : déclenchez un scénario pour voir le cycle complet.
              </p>
              <div className="mt-3 flex flex-wrap gap-3">
                <Button
                  variant="secondary"
                  onClick={() => void handleSimulate("success")}
                  disabled={simulating}
                >
                  Simuler un paiement réussi
                </Button>
                <Button
                  variant="danger"
                  onClick={() => void handleSimulate("fail")}
                  disabled={simulating}
                >
                  Simuler un échec
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <form onSubmit={(event) => void handleInitiate(event)} className="glass-card mt-6 space-y-4 p-5">
          <label className="block text-sm">
            <span className="block text-text/75">Téléphone</span>
            <input
              id="phone"
              type="tel"
              required
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="+237690000001"
              className="mt-1 w-full rounded-md border border-border/50 bg-white/80 px-3 py-2"
            />
          </label>

          <fieldset>
            <legend className="text-sm text-text/75">Opérateur</legend>
            <div className="mt-2 flex gap-4">
              <label className="flex cursor-pointer items-center gap-2 rounded-md border border-border/40 bg-white/70 px-3 py-2 text-sm">
                <input
                  type="radio"
                  name="operator"
                  value="MTN"
                  checked={operator === "MTN"}
                  onChange={() => setOperator("MTN")}
                />
                MTN
              </label>
              <label className="flex cursor-pointer items-center gap-2 rounded-md border border-border/40 bg-white/70 px-3 py-2 text-sm">
                <input
                  type="radio"
                  name="operator"
                  value="ORANGE"
                  checked={operator === "ORANGE"}
                  onChange={() => setOperator("ORANGE")}
                />
                ORANGE
              </label>
            </div>
          </fieldset>

          {actionError ? (
            <p role="alert" className="rounded-md bg-danger/10 p-3 text-sm font-semibold ink-danger">
              {actionError}
            </p>
          ) : null}

          <Button type="submit" disabled={initiating}>
            {initiating ? "Demande en cours…" : "Payer"}
          </Button>
        </form>
      )}
    </main>
  );
}
