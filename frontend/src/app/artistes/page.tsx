import type { Metadata } from "next";
import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
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
      <h1 className="text-3xl font-bold text-primary-strong">Artistes</h1>
      <p className="mt-2 text-text/70">
        {artists.length} artiste{artists.length > 1 ? "s" : ""} approuvé
        {artists.length > 1 ? "s" : ""}.
      </p>

      <div className="mt-8">
        {artists.length === 0 ? (
          <EmptyState
            title="Aucun artiste pour le moment."
            hint="Les profils approuvés apparaissent ici."
            actionLabel="Devenir artiste"
            actionHref="/devenir-artiste"
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {artists.map((artist) => (
              <Link
                key={artist.slug}
                href={`/artistes/${artist.slug}`}
                className="rounded-lg glass-card p-5"
              >
                <h2 className="text-lg font-semibold text-text">{artist.display_name}</h2>
                {(artist.city || artist.region) && (
                  <p className="mt-1 text-sm text-text/70">
                    {[artist.city, artist.region].filter(Boolean).join(", ")}
                  </p>
                )}
                {artist.bio ? (
                  <p className="mt-2 line-clamp-3 text-sm text-text/70">{artist.bio}</p>
                ) : null}
                <p className="mt-3 text-sm font-medium text-primary-strong">
                  {artist.artwork_count} œuvre{artist.artwork_count > 1 ? "s" : ""}
                </p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
