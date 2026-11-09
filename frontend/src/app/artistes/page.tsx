import type { Metadata } from "next";
import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { VerifiedBadge } from "@/components/verified-badge";
import { listArtists } from "@/lib/api";

export const metadata: Metadata = {
  title: "Artistes — ArtFlow",
  description: "Découvrez les artistes camerounais présents sur ArtFlow.",
};

export default async function ArtistsPage() {
  const artists = await listArtists()
    .then((page) => page.results)
    .catch(() => []);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <div className="border-b border-border/20 pb-5">
        <h1 className="text-3xl font-bold tracking-tight text-primary-strong">Artistes</h1>
        <p className="mt-1.5 text-sm text-text/80">
          {artists.length} artiste{artists.length > 1 ? "s" : ""} approuvé{artists.length > 1 ? "s" : ""}.
        </p>
      </div>

      <div className="mt-8">
        {artists.length === 0 ? (
          <EmptyState
            title="Aucun artiste pour le moment."
            hint="Les profils approuvés apparaissent ici."
            actionLabel="Devenir artiste"
            actionHref="/devenir-artiste"
          />
        ) : (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {artists.map((artist) => (
              <Link
                key={artist.slug}
                href={`/artistes/${artist.slug}`}
                className="group rounded-xl glass-card p-6 transition-all duration-200 hover:-translate-y-0.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <h2 className="flex items-center gap-1.5 text-lg font-bold text-primary-strong group-hover:text-primary transition-colors">
                    <span>{artist.display_name}</span>
                    {artist.is_verified ? <VerifiedBadge /> : null}
                  </h2>
                  <span className="glass-pill px-2.5 py-0.5 text-xs font-semibold text-primary-strong">
                    {artist.artwork_count} œuvre{artist.artwork_count > 1 ? "s" : ""}
                  </span>
                </div>
                {(artist.city || artist.region) && (
                  <p className="mt-1.5 text-xs font-medium text-text/75">
                    {[artist.city, artist.region].filter(Boolean).join(", ")}
                  </p>
                )}
                {artist.bio ? (
                  <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-text/85">{artist.bio}</p>
                ) : null}
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
