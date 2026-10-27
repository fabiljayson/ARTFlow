import { ArtworkCard } from "@/components/artwork-card";
import { getSimilarArtworks } from "@/lib/api";

/**
 * Œuvres similaires — composant serveur isolé dans un `Suspense` de la page
 * détaillée, pour ne pas bloquer l'affichage de l'œuvre principale.
 */
export async function SimilarWorks({ slug }: { slug: string }) {
  let artworks;
  try {
    artworks = await getSimilarArtworks(slug);
  } catch {
    return null;
  }

  if (artworks.length === 0) return null;

  return (
    <section className="mt-14 border-t border-border/25 pt-8">
      <h2 className="text-lg font-semibold text-text">Œuvres similaires</h2>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {artworks.map((artwork) => (
          <ArtworkCard key={artwork.id} artwork={artwork} />
        ))}
      </div>
    </section>
  );
}
