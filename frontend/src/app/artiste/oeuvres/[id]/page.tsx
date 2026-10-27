"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArtworkForm, type ArtworkFormValues } from "@/components/artwork-form";
import { Button } from "@/components/button";
import { MediaManager } from "@/components/media-manager";
import { StatusBadge } from "@/components/status-badge";
import { RequireAuth } from "@/components/require-auth";
import {
  ApiError,
  archiveArtwork,
  getMyArtwork,
  listCategories,
  publishArtwork,
  unpublishArtwork,
  updateArtwork,
  type ArtworkEditable,
  type Category,
} from "@/lib/api";
import { formatXAF } from "@/lib/money";

function EditArtwork() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const [artwork, setArtwork] = useState<ArtworkEditable | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [data, cats] = await Promise.all([getMyArtwork(id), listCategories()]);
      setArtwork(data);
      setCategories(cats.results);
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 404
            ? "Cette œuvre n'existe pas ou ne vous appartient pas."
            : err.message
          : "Chargement impossible.",
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleUpdate(values: ArtworkFormValues) {
    await updateArtwork(id, values);
    await load();
    router.refresh();
  }

  async function runAction(action: "publish" | "unpublish" | "archive") {
    setBusy(true);
    setError(null);
    try {
      if (action === "publish") await publishArtwork(id);
      else if (action === "unpublish") await unpublishArtwork(id);
      else {
        if (!window.confirm("Archiver cette œuvre ? Elle ne sera plus visible.")) return;
        await archiveArtwork(id);
      }
      await load();
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action impossible.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <div className="h-72 animate-pulse rounded-lg bg-surface-muted" />;
  }

  if (!artwork) {
    return (
      <div>
        <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error ?? "Œuvre introuvable."}
        </p>
        <Link href="/artiste/oeuvres" className="mt-4 inline-block text-sm text-primary hover:underline">
          Retour à mes œuvres
        </Link>
      </div>
    );
  }

  const status = artwork.status;
  const canPublish = status === "DRAFT" || status === "REFUSED" || status === "HIDDEN";
  const canUnpublish = status === "PUBLISHED";
  const canArchive = status !== "ARCHIVED" && status !== "PUBLISHED";

  return (
    <div className="space-y-10">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-border/25 pb-5">
        <div>
          <p className="text-sm text-text/50">{artwork.reference}</p>
          <h1 className="text-2xl font-bold text-primary-strong">{artwork.title}</h1>
          <div className="mt-2 flex items-center gap-3">
            <StatusBadge status={status} />
            <span className="text-sm text-text/70">{formatXAF(artwork.price_xaf)}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {canPublish ? (
            <Button disabled={busy} onClick={() => void runAction("publish")}>
              Soumettre à la modération
            </Button>
          ) : null}
          {canUnpublish ? (
            <Button variant="secondary" disabled={busy} onClick={() => void runAction("unpublish")}>
              Dépublier
            </Button>
          ) : null}
          {canArchive ? (
            <Button variant="danger" disabled={busy} onClick={() => void runAction("archive")}>
              Archiver
            </Button>
          ) : null}
        </div>
      </header>

      {error ? (
        <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      ) : null}

      <section>
        <h2 className="text-lg font-semibold text-text">Fiche</h2>
        <div className="mt-4">
          <ArtworkForm
            categories={categories}
            initial={{
              title: artwork.title,
              description: artwork.description ?? "",
              category: artwork.category,
              price_xaf: artwork.price_xaf,
              stock_quantity: artwork.stock_quantity,
              dimensions: artwork.dimensions,
              materials: artwork.materials,
              technique: artwork.technique,
              year_created: artwork.year_created,
              is_unique_piece: artwork.is_unique_piece,
            }}
            submitLabel="Enregistrer"
            onSubmit={handleUpdate}
          />
        </div>
      </section>

      <div className="border-t border-border/25 pt-8">
        <MediaManager artworkId={id} />
      </div>
    </div>
  );
}

export default function EditArtworkPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <RequireAuth role="artist">
        <nav aria-label="Fil d'ariane" className="mb-6 text-sm text-text/60">
          <Link href="/artiste/oeuvres" className="hover:text-primary">
            Mes œuvres
          </Link>
          <span aria-hidden="true"> / </span>
          <span className="text-text/80">Édition</span>
        </nav>
        <EditArtwork />
      </RequireAuth>
    </main>
  );
}
