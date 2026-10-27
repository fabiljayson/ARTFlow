"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/button";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { RequireAuth } from "@/components/require-auth";
import {
  ApiError,
  archiveArtwork,
  listMyArtworks,
  publishArtwork,
  unpublishArtwork,
  type ArtworkSummary,
} from "@/lib/api";
import { formatXAF } from "@/lib/money";

type BusyId = number | null;

function ArtworkList() {
  const router = useRouter();
  const [items, setItems] = useState<ArtworkSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<BusyId>(null);

  const load = useCallback(async () => {
    try {
      const page = await listMyArtworks();
      setItems(page.results);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function runAction(id: number, action: "publish" | "unpublish" | "archive") {
    setBusy(id);
    setError(null);
    try {
      if (action === "publish") await publishArtwork(id);
      else if (action === "unpublish") await unpublishArtwork(id);
      else {
        // Confirmation : l'archivage est logique mais l'œuvre quitte l'espace public.
        if (!window.confirm("Archiver cette œuvre ? Elle ne sera plus visible.")) return;
        await archiveArtwork(id);
      }
      await load();
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action impossible.");
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return <div className="h-48 animate-pulse rounded-lg bg-surface-muted" />;
  }

  if (error) {
    return (
      <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
        {error}
      </p>
    );
  }

  if (items.length === 0) {
    return (
      <EmptyState
        title="Vous n'avez encore aucune œuvre."
        hint="Créez votre première fiche : titre, catégorie, prix, puis des images."
        actionLabel="Créer une œuvre"
        actionHref="/artiste/oeuvres/nouvelle"
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border/25">
      <table className="w-full min-w-[720px] text-sm">
        <thead className="bg-surface-muted/60 text-left text-xs uppercase tracking-wide text-text/60">
          <tr>
            <th className="px-4 py-3 font-semibold">Œuvre</th>
            <th className="px-4 py-3 font-semibold">Prix</th>
            <th className="px-4 py-3 font-semibold">Stock</th>
            <th className="px-4 py-3 font-semibold">Statut</th>
            <th className="px-4 py-3 text-right font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/20 bg-white/70">
          {items.map((artwork) => (
            <tr key={artwork.id}>
              <td className="px-4 py-3">
                <Link
                  href={`/artiste/oeuvres/${artwork.id}`}
                  className="font-medium text-text hover:text-primary"
                >
                  {artwork.title}
                </Link>
                <p className="text-xs text-text/50">{artwork.reference}</p>
              </td>
              <td className="px-4 py-3">{formatXAF(artwork.price_xaf)}</td>
              <td className="px-4 py-3">
                {artwork.stock_quantity === 0 ? (
                  <span className="font-medium text-danger">0</span>
                ) : (
                  artwork.stock_quantity
                )}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={artwork.status} />
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap justify-end gap-2">
                  <Link
                    href={`/artiste/oeuvres/${artwork.id}`}
                    className="rounded-md border border-border/40 px-2.5 py-1 text-xs font-medium transition hover:bg-surface-muted"
                  >
                    Modifier
                  </Link>

                  {artwork.status === "DRAFT" ||
                  artwork.status === "REFUSED" ||
                  artwork.status === "HIDDEN" ? (
                    <Button
                      variant="primary"
                      className="px-2.5 py-1 text-xs"
                      disabled={busy === artwork.id}
                      onClick={() => void runAction(artwork.id, "publish")}
                    >
                      Soumettre
                    </Button>
                  ) : null}

                  {artwork.status === "PUBLISHED" ? (
                    <Button
                      variant="secondary"
                      className="px-2.5 py-1 text-xs"
                      disabled={busy === artwork.id}
                      onClick={() => void runAction(artwork.id, "unpublish")}
                    >
                      Dépublier
                    </Button>
                  ) : null}

                  {artwork.status !== "ARCHIVED" && artwork.status !== "PUBLISHED" ? (
                    <Button
                      variant="danger"
                      className="px-2.5 py-1 text-xs"
                      disabled={busy === artwork.id}
                      onClick={() => void runAction(artwork.id, "archive")}
                    >
                      Archiver
                    </Button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function MyArtworksPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <RequireAuth role="artist">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold text-primary-strong">Mes œuvres</h1>
            <p className="mt-2 text-text/70">Gérez vos fiches, images et soumissions.</p>
          </div>
          <Link
            href="/artiste/oeuvres/nouvelle"
            className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-strong"
          >
            Nouvelle œuvre
          </Link>
        </div>

        <div className="mt-8">
          <ArtworkList />
        </div>
      </RequireAuth>
    </main>
  );
}
