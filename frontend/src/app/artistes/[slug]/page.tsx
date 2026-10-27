import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArtworkCard } from "@/components/artwork-card";
import { EmptyState } from "@/components/empty-state";
import { ApiError, getArtist } from "@/lib/api";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  try {
    const artist = await getArtist(slug);
    return {
      title: `${artist.display_name} — ArtFlow`,
      description: artist.bio.slice(0, 160) || `Œuvres de ${artist.display_name} sur ArtFlow.`,
    };
  } catch {
    return { title: "Artiste introuvable — ArtFlow" };
  }
}

export default async function ArtistPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  let artist;
  try {
    artist = await getArtist(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <nav aria-label="Fil d'ariane" className="text-sm text-text/70">
        <Link href="/artistes" className="hover:text-primary-strong">
          Artistes
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-text/80">{artist.display_name}</span>
      </nav>

      <header className="mt-6 border-b border-border/25 pb-6">
        <h1 className="text-3xl font-bold text-primary-strong">{artist.display_name}</h1>
        {(artist.city || artist.region) && (
          <p className="mt-1 text-text/70">
            {[artist.city, artist.region].filter(Boolean).join(", ")}
          </p>
        )}
        {artist.bio ? <p className="mt-4 max-w-2xl leading-relaxed text-text/80">{artist.bio}</p> : null}
        <p className="mt-3 text-sm font-medium text-primary-strong">
          {artist.artwork_count} œuvre{artist.artwork_count > 1 ? "s" : ""} publiée
          {artist.artwork_count > 1 ? "s" : ""}
        </p>
      </header>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-text">Œuvres</h2>
        {artist.artworks.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              title="Aucune œuvre publiée."
              hint="Cette artiste n'a encore rien mis en ligne."
              actionLabel="Voir tout le catalogue"
              actionHref="/catalogue"
            />
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {artist.artworks.map((artwork) => (
              <ArtworkCard key={artwork.id} artwork={artwork} />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
