"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/button";
import { CART_UPDATED_EVENT } from "@/components/cart/cart-events";
import { EmptyState } from "@/components/empty-state";
import {
  ApiError,
  checkout,
  createAddress,
  listAddresses,
  quoteCheckout,
  type Address,
  type Quote,
} from "@/lib/api";
import { formatXAF } from "@/lib/money";

type Load = "loading" | "ready" | "error";

const EMPTY_ADDRESS_FORM = {
  label: "",
  recipient_name: "",
  line1: "",
  line2: "",
  city: "",
  region: "",
  phone: "",
};

/**
 * Checkout (docs/screens.md /checkout) — mini-form d'adresse intégré,
 * totaux serveur (quote) et commande idempotente (clé UUID au clic).
 */
export default function CheckoutPage() {
  const router = useRouter();
  const [state, setState] = useState<Load>("loading");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [addressId, setAddressId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_ADDRESS_FORM);
  const [buyerNote, setBuyerNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [q, a] = await Promise.all([quoteCheckout(), listAddresses()]);
      setQuote(q);
      setAddresses(a.results);
      setAddressId((current) =>
        current ?? a.results.find((addr) => addr.is_default)?.id ?? a.results[0]?.id ?? null,
      );
      setShowForm(a.results.length === 0);
      setState("ready");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.replace(`/connexion?next=${encodeURIComponent("/checkout")}`);
        return;
      }
      setState("error");
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCreateAddress(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setActionError(null);
    try {
      const created = await createAddress(form);
      setAddresses((prev) => [created, ...prev]);
      setAddressId(created.id);
      setForm(EMPTY_ADDRESS_FORM);
      setShowForm(false);
    } catch (error) {
      setActionError(
        error instanceof ApiError ? error.message : "Impossible d'enregistrer l'adresse.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirm() {
    if (addressId === null || !quote) return;
    setBusy(true);
    setActionError(null);
    try {
      const result = await checkout(
        { address_id: addressId, buyer_note: buyerNote.trim() || undefined },
        crypto.randomUUID(),
      );
      window.dispatchEvent(new Event(CART_UPDATED_EVENT));
      router.push(`/commandes/${result.order_reference}`);
    } catch (error) {
      setActionError(
        error instanceof ApiError
          ? error.message
          : "La commande n'a pas pu être confirmée. Réessayez.",
      );
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

  if (state === "error") {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-2xl font-bold text-primary-strong">Commande</h1>
        <div className="mt-6 rounded-lg border border-border/40 bg-white/60 p-6 text-center">
          <p className="font-semibold text-text">Impossible de préparer votre commande.</p>
          <p className="mt-1 text-sm text-text/70">Vérifiez votre connexion puis réessayez.</p>
          <Button variant="secondary" className="mt-4" onClick={() => void load()}>
            Réessayer
          </Button>
        </div>
      </main>
    );
  }

  const isEmpty = !quote || quote.items.length === 0;
  const hasBlocking = (quote?.blocking_issues.length ?? 0) > 0;

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-bold text-primary-strong">Commande</h1>

      {isEmpty ? (
        <div className="mt-6">
          <EmptyState
            title="Rien à commander"
            hint="Votre panier est vide — ajoutez des œuvres pour continuer."
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

          {hasBlocking ? (
            <div
              role="alert"
              className="mt-4 rounded-md border border-warning/40 bg-warning/10 p-4 text-sm"
            >
              <p className="font-semibold ink-warning">Stock insuffisant :</p>
              <ul className="mt-1 list-disc pl-5 text-text/80">
                {quote?.blocking_issues.map((issue) => (
                  <li key={`${issue.artwork_id}-${issue.code}`}>{issue.message}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <section className="glass-card mt-6 space-y-4 p-5" aria-labelledby="checkout-address">
            <h2 id="checkout-address" className="font-semibold text-primary-strong">
              Adresse de livraison
            </h2>

            {addresses.length > 0 ? (
              <fieldset>
                <legend className="sr-only">Choisir une adresse</legend>
                <ul className="space-y-2">
                  {addresses.map((address) => (
                    <li key={address.id}>
                      <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border/40 bg-white/70 p-3 hover:border-primary/50">
                        <input
                          type="radio"
                          name="address"
                          value={address.id}
                          checked={addressId === address.id}
                          onChange={() => setAddressId(address.id)}
                          className="mt-1"
                        />
                        <span className="text-sm">
                          <span className="block font-semibold text-text">
                            {address.label}
                            {address.is_default ? (
                              <span className="ml-2 text-xs text-text/60">(défaut)</span>
                            ) : null}
                          </span>
                          <span className="block text-text/75">
                            {address.recipient_name} — {address.line1}
                            {address.line2 ? `, ${address.line2}` : ""}
                          </span>
                          <span className="block text-text/75">
                            {address.city}
                            {address.region ? `, ${address.region}` : ""} · {address.phone}
                          </span>
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </fieldset>
            ) : (
              <p className="text-sm text-text/70">Aucune adresse enregistrée pour l&apos;instant.</p>
            )}

            {showForm ? (
              <form onSubmit={(event) => void handleCreateAddress(event)} className="space-y-3">
                <p className="text-sm font-semibold text-text">Ajouter une adresse</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="text-sm">
                    <span className="block text-text/75">Libellé</span>
                    <input
                      required
                      value={form.label}
                      onChange={(e) => setForm({ ...form, label: e.target.value })}
                      placeholder="Maison"
                      className="mt-1 w-full rounded-md border border-border/50 bg-white/80 px-3 py-2"
                    />
                  </label>
                  <label className="text-sm">
                    <span className="block text-text/75">Destinataire</span>
                    <input
                      required
                      value={form.recipient_name}
                      onChange={(e) => setForm({ ...form, recipient_name: e.target.value })}
                      className="mt-1 w-full rounded-md border border-border/50 bg-white/80 px-3 py-2"
                    />
                  </label>
                  <label className="text-sm sm:col-span-2">
                    <span className="block text-text/75">Rue</span>
                    <input
                      required
                      value={form.line1}
                      onChange={(e) => setForm({ ...form, line1: e.target.value })}
                      className="mt-1 w-full rounded-md border border-border/50 bg-white/80 px-3 py-2"
                    />
                  </label>
                  <label className="text-sm sm:col-span-2">
                    <span className="block text-text/75">Complément (optionnel)</span>
                    <input
                      value={form.line2}
                      onChange={(e) => setForm({ ...form, line2: e.target.value })}
                      className="mt-1 w-full rounded-md border border-border/50 bg-white/80 px-3 py-2"
                    />
                  </label>
                  <label className="text-sm">
                    <span className="block text-text/75">Ville</span>
                    <input
                      required
                      value={form.city}
                      onChange={(e) => setForm({ ...form, city: e.target.value })}
                      placeholder="Douala"
                      className="mt-1 w-full rounded-md border border-border/50 bg-white/80 px-3 py-2"
                    />
                  </label>
                  <label className="text-sm">
                    <span className="block text-text/75">Région (optionnel)</span>
                    <input
                      value={form.region}
                      onChange={(e) => setForm({ ...form, region: e.target.value })}
                      className="mt-1 w-full rounded-md border border-border/50 bg-white/80 px-3 py-2"
                    />
                  </label>
                  <label className="text-sm">
                    <span className="block text-text/75">Téléphone</span>
                    <input
                      required
                      value={form.phone}
                      onChange={(e) => setForm({ ...form, phone: e.target.value })}
                      placeholder="6XXXXXXXX"
                      className="mt-1 w-full rounded-md border border-border/50 bg-white/80 px-3 py-2"
                    />
                  </label>
                </div>
                <div className="flex gap-3">
                  <Button type="submit" variant="secondary" disabled={busy}>
                    Enregistrer l&apos;adresse
                  </Button>
                  {addresses.length > 0 ? (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setShowForm(false)}
                      disabled={busy}
                    >
                      Annuler
                    </Button>
                  ) : null}
                </div>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => setShowForm(true)}
                className="text-sm font-semibold text-primary-strong hover:underline"
              >
                + Ajouter une adresse
              </button>
            )}
          </section>

          <section className="glass-card mt-6 space-y-3 p-5" aria-labelledby="checkout-items">
            <h2 id="checkout-items" className="font-semibold text-primary-strong">
              Articles ({quote?.items_count ?? 0})
            </h2>
            <ul className="space-y-3">
              {quote?.items.map((item) => (
                <li key={item.artwork_id} className="flex justify-between gap-3 text-sm">
                  <span className="text-text">
                    {item.title}
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
                <span>{formatXAF(quote?.subtotal_items_xaf ?? 0)}</span>
              </div>
              <div className="flex justify-between">
                <span>Livraison</span>
                <span>{formatXAF(quote?.shipping_total_xaf ?? 0)}</span>
              </div>
              <div className="flex justify-between border-t border-border/30 pt-3 font-semibold text-text">
                <span>Total</span>
                <span className="text-lg font-bold text-primary-strong">
                  {formatXAF(quote?.grand_total_xaf ?? 0)}
                </span>
              </div>
            </div>
          </section>

          <section className="glass-card mt-6 space-y-3 p-5" aria-labelledby="checkout-confirm">
            <h2 id="checkout-confirm" className="font-semibold text-primary-strong">
              Confirmation
            </h2>
            <label className="block text-sm">
              <span className="block text-text/75">Note pour le vendeur (optionnel)</span>
              <textarea
                value={buyerNote}
                onChange={(e) => setBuyerNote(e.target.value)}
                rows={2}
                className="mt-1 w-full rounded-md border border-border/50 bg-white/80 px-3 py-2"
              />
            </label>
            <Button
              onClick={() => void handleConfirm()}
              disabled={busy || hasBlocking || addressId === null}
              className="w-full"
            >
              {busy ? "Confirmation…" : "Confirmer la commande"}
            </Button>
            {addressId === null && addresses.length === 0 && !showForm ? (
              <p className="text-center text-xs ink-danger">Ajoutez une adresse pour continuer.</p>
            ) : null}
            <p className="text-center text-xs text-text/70">
              Le paiement arrive en phase suivante — vous ne serez pas débité pour
              l&apos;instant.
            </p>
            <Link
              href="/panier"
              className="block text-center text-sm font-semibold text-primary-strong hover:underline"
            >
              Retour au panier
            </Link>
          </section>
        </>
      )}
    </main>
  );
}
