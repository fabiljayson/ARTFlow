"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { ApiError, getArtistDashboard, listMyArtworks, type ArtistDashboard, type ArtworkSummary } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl glass-card p-4 transition-all duration-200 hover:-translate-y-0.5">
      <p className="text-2xl sm:text-3xl font-extrabold text-primary-strong">{value}</p>
      <p className="mt-1 text-xs font-semibold text-text/75">{label}</p>
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
      <p role="alert" className="rounded-lg border border-danger/40 bg-danger/10 px-3.5 py-2.5 text-sm font-semibold ink-danger">
        {error}
      </p>
    );
  }

  if (!stats) {
    return <div className="h-40 animate-pulse rounded-xl bg-surface-muted/60" />;
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Total œuvres" value={stats.total_artworks} />
        <StatTile label="Publiées" value={stats.published} />
        <StatTile label="En modération" value={stats.in_moderation} />
        <StatTile label="Brouillons" value={stats.drafts} />
        <StatTile label="Épuisées" value={stats.unavailable} />
        <StatTile label="Favoris" value={stats.total_favorites} />
      </div>

      <section className="mt-10 rounded-2xl glass-strong p-6 sm:p-7 shadow-md">
        <div className="flex items-center justify-between pb-4 border-b border-border/20">
          <h2 className="text-lg font-bold text-primary-strong">Dernières œuvres</h2>
          <div className="flex items-center gap-3 text-sm">
            <Link href="/artiste/oeuvres" className="font-semibold text-primary-strong hover:text-primary transition-colors">
              Tout voir
            </Link>
            <Link
              href="/artiste/oeuvres/nouvelle"
              className="btn btn-primary px-3.5 py-1.5 text-xs sm:text-sm shadow-sm"
            >
              Nouvelle œuvre
            </Link>
          </div>
        </div>

        {recent.length === 0 ? (
          <p className="mt-5 text-sm text-text/75">
            Aucune œuvre pour l&apos;instant — commencez par en créer une.
          </p>
        ) : (
          <ul className="divide-y divide-border/15">
            {recent.map((artwork) => (
              <li key={artwork.id} className="flex items-center justify-between gap-3 py-3.5">
                <div className="min-w-0">
                  <Link
                    href={`/artiste/oeuvres/${artwork.id}`}
                    className="block truncate font-semibold text-text hover:text-primary-strong transition-colors"
                  >
                    {artwork.title}
                  </Link>
                  <p className="text-xs text-text/70">{artwork.reference}</p>
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
        <div className="border-b border-border/20 pb-5">
          <h1 className="text-3xl font-bold tracking-tight text-primary-strong">Espace artiste</h1>
          <p className="mt-1.5 text-sm text-text/80">Suivi de vos œuvres et de leur modération.</p>
        </div>
        <div className="mt-8">
          <DashboardContent />
        </div>
      </RequireAuth>
    </main>
  );
}
