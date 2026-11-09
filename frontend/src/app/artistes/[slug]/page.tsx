import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArtworkCard } from "@/components/artwork-card";
import { EmptyState } from "@/components/empty-state";
import { VerifiedBadge } from "@/components/verified-badge";
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
      <nav aria-label="Fil d'ariane" className="text-sm font-medium text-text/75">
        <Link href="/artistes" className="hover:text-primary-strong transition-colors">
          Artistes
        </Link>
        <span aria-hidden="true" className="mx-1 text-border/40">/</span>
        <span className="text-primary-strong">{artist.display_name}</span>
      </nav>

      <header className="mt-6 rounded-2xl glass-strong p-6 sm:p-8 shadow-md">
        <h1 className="text-3xl font-bold tracking-tight text-primary-strong sm:text-4xl">
          <span className="inline-flex items-center gap-2">
            {artist.display_name}
            {artist.is_verified ? <VerifiedBadge /> : null}
          </span>
        </h1>
        {(artist.city || artist.region) && (
          <p className="mt-1 text-sm font-medium text-text/80">
            {[artist.city, artist.region].filter(Boolean).join(", ")}
          </p>
        )}
        {artist.bio ? <p className="mt-4 max-w-2xl leading-relaxed text-text/85">{artist.bio}</p> : null}
        <div className="mt-6 flex flex-wrap gap-2.5" aria-label="Statistiques de l’artiste">
          {[
            [`${artist.stats?.works ?? artist.artwork_count} œuvres`, "œuvres publiées"],
            [`${artist.stats?.sold ?? 0} vendues`, "ventes confirmées"],
            [`${artist.stats?.views ?? 0} vues`, "vues cumulées"],
            [`${artist.stats?.favorites ?? 0} favoris`, "ajouts aux favoris"],
          ].map(([value, label]) => (
            <span key={label} title={label} className="glass-pill px-3.5 py-1.5 text-xs font-bold text-primary-strong">
              {value}
            </span>
          ))}
        </div>
      </header>

      <section className="mt-10">
        <h2 className="text-xl font-bold text-primary-strong">Œuvres</h2>
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
