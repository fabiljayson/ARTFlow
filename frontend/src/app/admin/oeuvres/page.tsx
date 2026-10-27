"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/button";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { MediaImage } from "@/components/media-image";
import { RequireAuth } from "@/components/require-auth";
import {
  ApiError,
  listAdminArtworks,
  moderateArtwork,
  type ArtworkStatus,
  type ArtworkSummary,
  type ModerationDecision,
} from "@/lib/api";
import { formatXAF } from "@/lib/money";

const FILTERS: { label: string; value: ArtworkStatus | "" }[] = [
  { label: "Toutes", value: "" },
  { label: "En modération", value: "IN_MODERATION" },
  { label: "Publiées", value: "PUBLISHED" },
  { label: "Refusées", value: "REFUSED" },
  { label: "Masquées", value: "HIDDEN" },
  { label: "Brouillons", value: "DRAFT" },
  { label: "Archivées", value: "ARCHIVED" },
];

function ModerationList() {
  const router = useRouter();
  const [status, setStatus] = useState<ArtworkStatus | "">("");
  const [items, setItems] = useState<ArtworkSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async (next: ArtworkStatus | "") => {
    setLoading(true);
    try {
      const page = await listAdminArtworks(next || undefined);
      setItems(page.results);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(status);
  }, [status, load]);

  async function decide(id: number, decision: ModerationDecision) {
    let reason = "";
    if (decision !== "approve") {
      const label = decision === "refuse" ? "refus" : "masquage";
      reason = window.prompt(`Motif de ${label} (obligatoire) :`, "") ?? "";
      if (!reason.trim()) {
        setError(`Un motif est obligatoire pour le ${label}.`);
        return;
      }
    } else if (!window.confirm("Approuver cette œuvre ? Elle deviendra publique.")) {
      return;
    }

    setBusyId(id);
    setError(null);
    setInfo(null);
    try {
      await moderateArtwork(id, decision, reason.trim());
      setInfo(
        decision === "approve"
          ? "Œuvre approuvée et publiée."
          : decision === "refuse"
            ? "Œuvre refusée — le motif est transmis à l'artiste."
            : "Œuvre masquée.",
      );
      await load(status);
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Décision impossible.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <nav aria-label="Filtres par statut" className="flex flex-wrap gap-2">
        {FILTERS.map((filter) => (
          <button
            key={filter.value || "all"}
            type="button"
            onClick={() => setStatus(filter.value)}
            aria-pressed={status === filter.value}
            className={`rounded-full border px-3 py-1.5 text-sm transition ${
              status === filter.value
                ? "border-primary-strong bg-primary-strong text-white shadow-sm"
                : "border-border/40 bg-white/70 text-text/70 hover:bg-surface-muted"
            }`}
          >
            {filter.label}
          </button>
        ))}
      </nav>

      {error ? (
        <p role="alert" className="mt-4 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm ink-danger">
          {error}
        </p>
      ) : null}
      {info ? <p className="mt-4 text-sm ink-success">{info}</p> : null}

      <div className="mt-6">
        {loading ? (
          <div className="h-48 animate-pulse rounded-lg bg-surface-muted" />
        ) : items.length === 0 ? (
          <EmptyState
            title="Aucune œuvre dans ce filtre."
            hint="Les soumissions d'artistes apparaissent ici dès leur envoi."
            actionLabel="Voir les soumissions"
            actionHref="/admin/oeuvres?status=IN_MODERATION"
          />
        ) : (
          <ul className="space-y-4">
            {items.map((artwork) => (
              <li
                key={artwork.id}
                className="flex flex-wrap items-start gap-4 rounded-lg glass-card p-4"
              >
                <Link
                  href={`/oeuvre/${artwork.slug}`}
                  className="relative h-24 w-20 shrink-0 overflow-hidden rounded-md bg-surface-muted"
                >
                  <MediaImage
                    src={artwork.primary_image_url}
                    alt={artwork.title}
                    fill
                    sizes="80px"
                    className="object-cover"
                  />
                </Link>

                <div className="min-w-[200px] flex-1">
                  <Link
                    href={`/oeuvre/${artwork.slug}`}
                    className="font-semibold text-text hover:text-primary-strong"
                  >
                    {artwork.title}
                  </Link>
                  <p className="text-xs text-text/70">{artwork.reference}</p>
                  <p className="mt-1 text-sm text-text/70">{artwork.artist_display_name}</p>
                  <div className="mt-2 flex items-center gap-3">
                    <StatusBadge status={artwork.status} />
                    <span className="text-sm text-text/70">{formatXAF(artwork.price_xaf)}</span>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {artwork.status === "IN_MODERATION" ? (
                    <>
                      <Button
                        disabled={busyId === artwork.id}
                        onClick={() => void decide(artwork.id, "approve")}
                      >
                        Approuver
                      </Button>
                      <Button
                        variant="secondary"
                        disabled={busyId === artwork.id}
                        onClick={() => void decide(artwork.id, "refuse")}
                      >
                        Refuser
                      </Button>
                    </>
                  ) : null}

                  {artwork.status === "PUBLISHED" ? (
                    <Button
                      variant="danger"
                      disabled={busyId === artwork.id}
                      onClick={() => void decide(artwork.id, "hide")}
                    >
                      Masquer
                    </Button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}

export default function AdminModerationPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <RequireAuth role="admin">
        <h1 className="text-3xl font-bold text-primary-strong">Modération des œuvres</h1>
        <p className="mt-2 text-text/70">
          Approuvez, refusez ou masquez les œuvres soumises par les artistes.
        </p>
        <div className="mt-8">
          <ModerationList />
        </div>
      </RequireAuth>
    </main>
  );
}
