"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { ApiError, getArtistDashboard, listMyArtworks, type ArtistDashboard, type ArtworkSummary } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border/25 bg-white/70 p-4">
      <p className="text-2xl font-bold text-primary-strong">{value}</p>
      <p className="mt-1 text-sm text-text/60">{label}</p>
    </div>
  );
}

function DashboardContent() {
  const [stats, setStats] = useState<ArtistDashboard | null>(null);
  const [recent, setRecent] = useState<ArtworkSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const [dashboard, list] = await Promise.all([
          getArtistDashboard(),
          listMyArtworks(),
        ]);
        if (cancelled) return;
        setStats(dashboard);
        setRecent(list.results.slice(0, 5));
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Chargement impossible.");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
        {error}
      </p>
    );
  }

  if (!stats) {
    return <div className="h-40 animate-pulse rounded-lg bg-surface-muted" />;
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Total œuvres" value={stats.total_artworks} />
        <StatTile label="Publiées" value={stats.published} />
        <StatTile label="En modération" value={stats.in_moderation} />
        <StatTile label="Brouillons" value={stats.drafts} />
        <StatTile label="Épuisées" value={stats.unavailable} />
        <StatTile label="Favoris" value={stats.total_favorites} />
      </div>

      <section className="mt-10">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">Dernières œuvres</h2>
          <div className="flex gap-3 text-sm">
            <Link href="/artiste/oeuvres" className="text-primary hover:underline">
              Tout voir
            </Link>
            <Link
              href="/artiste/oeuvres/nouvelle"
              className="rounded-md bg-primary px-3 py-1.5 font-semibold text-white transition hover:bg-primary-strong"
            >
              Nouvelle œuvre
            </Link>
          </div>
        </div>

        {recent.length === 0 ? (
          <p className="mt-4 text-sm text-text/60">
            Aucune œuvre pour l&apos;instant — commencez par en créer une.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-border/20 border-y border-border/20">
            {recent.map((artwork) => (
              <li key={artwork.id} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <Link
                    href={`/artiste/oeuvres/${artwork.id}`}
                    className="block truncate font-medium text-text hover:text-primary"
                  >
                    {artwork.title}
                  </Link>
                  <p className="text-xs text-text/50">{artwork.reference}</p>
                </div>
                <StatusBadge status={artwork.status} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

export default function ArtistDashboardPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <RequireAuth role="artist">
        <h1 className="text-3xl font-bold text-primary-strong">Espace artiste</h1>
        <p className="mt-2 text-text/70">Suivi de vos œuvres et de leur modération.</p>
        <div className="mt-8">
          <DashboardContent />
        </div>
      </RequireAuth>
    </main>
  );
}
