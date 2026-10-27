import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { SimilarWorks } from "@/components/similar-works";
import { ArtworkGallery } from "@/components/artwork-gallery";
import { ApiError, getArtwork } from "@/lib/api";
import { formatXAF } from "@/lib/money";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  try {
    const artwork = await getArtwork(slug);
    return {
      title: `${artwork.title} — ArtFlow`,
      description: artwork.description.slice(0, 160),
    };
  } catch {
    return { title: "Œuvre introuvable — ArtFlow" };
  }
}

export default async function ArtworkPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  let artwork;
  try {
    artwork = await getArtwork(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const images = artwork.media.filter((m) => m.kind === "IMAGE");
  const videos = artwork.media.filter((m) => m.kind === "VIDEO");
  const soldOut = !artwork.is_available;

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <nav aria-label="Fil d'ariane" className="text-sm text-text/60">
        <Link href="/catalogue" className="hover:text-primary">
          Catalogue
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-text/80">{artwork.title}</span>
      </nav>

      <div className="mt-6 grid gap-8 lg:grid-cols-2">
        <ArtworkGallery images={images} videos={videos} title={artwork.title} />

        <div>
          <p className="text-sm text-text/60">{artwork.reference}</p>
          <h1 className="mt-1 text-3xl font-bold text-primary-strong">{artwork.title}</h1>

          <Link
            href={`/artistes/${artwork.artist_slug}`}
            className="mt-2 inline-block text-sm text-primary hover:underline"
          >
            {artwork.artist_display_name}
          </Link>

          <div className="mt-4 flex items-baseline gap-3">
            <span className="text-2xl font-bold text-primary">{formatXAF(artwork.price_xaf)}</span>
            {soldOut ? (
              <span className="rounded-md bg-danger/15 px-2 py-0.5 text-sm font-semibold text-danger">
                Épuisé
              </span>
            ) : (
              <span className="text-sm text-success">
                {artwork.stock_quantity} en stock
              </span>
            )}
          </div>

          <p className="mt-5 whitespace-pre-line leading-relaxed text-text/80">
            {artwork.description}
          </p>

          <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-text/60">
            Caractéristiques
          </h2>
          <dl className="mt-3 divide-y divide-border/20 border-y border-border/20 text-sm">
            {artwork.category_detail ? (
              <div className="flex justify-between py-2">
                <dt className="text-text/60">Catégorie</dt>
                <dd className="font-medium">{artwork.category_detail.name_fr}</dd>
              </div>
            ) : null}
            {artwork.dimensions ? (
              <div className="flex justify-between py-2">
                <dt className="text-text/60">Dimensions</dt>
                <dd className="font-medium">{artwork.dimensions}</dd>
              </div>
            ) : null}
            {artwork.materials ? (
              <div className="flex justify-between py-2">
                <dt className="text-text/60">Matériaux</dt>
                <dd className="font-medium">{artwork.materials}</dd>
              </div>
            ) : null}
            {artwork.technique ? (
              <div className="flex justify-between py-2">
                <dt className="text-text/60">Technique</dt>
                <dd className="font-medium">{artwork.technique}</dd>
              </div>
            ) : null}
            {artwork.year_created ? (
              <div className="flex justify-between py-2">
                <dt className="text-text/60">Année</dt>
                <dd className="font-medium">{artwork.year_created}</dd>
              </div>
            ) : null}
            <div className="flex justify-between py-2">
              <dt className="text-text/60">Pièce unique</dt>
              <dd className="font-medium">{artwork.is_unique_piece ? "Oui" : "Non"}</dd>
            </div>
          </dl>

          <p className="mt-6 rounded-md border border-border/30 bg-surface-muted/50 p-3 text-xs text-text/60">
            L&apos;achat et la livraison arrivent en Phase D. Pour l&apos;instant, contactez
            l&apos;artiste via son profil.
          </p>
        </div>
      </div>

      <Suspense fallback={<div className="mt-14 h-48 animate-pulse rounded-lg bg-surface-muted" />}>
        <SimilarWorks slug={slug} />
      </Suspense>
    </main>
  );
}
