import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { SimilarWorks } from "@/components/similar-works";
import { ArtworkGallery } from "@/components/artwork-gallery";
import { AddToCartButton } from "@/components/cart/add-to-cart-button";
import { VerifiedBadge } from "@/components/verified-badge";
import { ViewTracker } from "@/components/view-tracker";
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
      <nav aria-label="Fil d'ariane" className="text-sm text-text/75 font-medium">
        <Link href="/catalogue" className="hover:text-primary-strong transition-colors">
          Catalogue
        </Link>
        <span aria-hidden="true" className="mx-1 text-border/40">/</span>
        <span className="text-primary-strong">{artwork.title}</span>
      </nav>

      <div className="mt-6 grid gap-8 lg:grid-cols-2 lg:items-start">
        <ArtworkGallery images={images} videos={videos} title={artwork.title} />

        <div className="rounded-xl glass-card p-6 sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="glass-pill px-2.5 py-0.5 text-xs font-medium text-text/75">
              {artwork.reference}
            </span>
            {soldOut ? (
              <span className="rounded-full bg-danger/15 border border-danger/30 px-3 py-0.5 text-xs font-bold ink-danger">
                Épuisé
              </span>
            ) : (
              <span className="rounded-full bg-success/15 border border-success/30 px-3 py-0.5 text-xs font-semibold ink-success">
                {artwork.stock_quantity} en stock
              </span>
            )}
          </div>

          <h1 className="mt-3 text-3xl font-bold tracking-tight text-primary-strong sm:text-4xl">
            {artwork.title}
          </h1>

          <Link
            href={`/artistes/${artwork.artist_slug}`}
            className="mt-2.5 inline-flex items-center gap-1.5 text-sm font-semibold text-primary-strong hover:text-primary transition-colors"
          >
            <span>{artwork.artist_display_name}</span>
            {artwork.artist_verified ? <VerifiedBadge /> : null}
          </Link>

          <div className="mt-4 flex items-baseline gap-3">
            <span className="text-3xl font-extrabold text-primary-strong">
              {formatXAF(artwork.price_xaf)}
            </span>
          </div>

          <p className="mt-5 whitespace-pre-line leading-relaxed text-text/85">
            {artwork.description}
          </p>

          <h2 className="mt-8 text-xs font-bold uppercase tracking-wider text-text/75">
            Caractéristiques
          </h2>
          <dl className="mt-3 divide-y divide-border/20 border-y border-border/20 text-sm">
            {artwork.category_detail ? (
              <div className="flex justify-between py-2.5">
                <dt className="text-text/75">Catégorie</dt>
                <dd className="font-semibold text-text">{artwork.category_detail.name_fr}</dd>
              </div>
            ) : null}
            {artwork.dimensions ? (
              <div className="flex justify-between py-2.5">
                <dt className="text-text/75">Dimensions</dt>
                <dd className="font-semibold text-text">{artwork.dimensions}</dd>
              </div>
            ) : null}
            {artwork.materials ? (
              <div className="flex justify-between py-2.5">
                <dt className="text-text/75">Matériaux</dt>
                <dd className="font-semibold text-text">{artwork.materials}</dd>
              </div>
            ) : null}
            {artwork.technique ? (
              <div className="flex justify-between py-2.5">
                <dt className="text-text/75">Technique</dt>
                <dd className="font-semibold text-text">{artwork.technique}</dd>
              </div>
            ) : null}
            {artwork.year_created ? (
              <div className="flex justify-between py-2.5">
                <dt className="text-text/75">Année</dt>
                <dd className="font-semibold text-text">{artwork.year_created}</dd>
              </div>
            ) : null}
            <div className="flex justify-between py-2.5">
              <dt className="text-text/75">Pièce unique</dt>
              <dd className="font-semibold text-text">{artwork.is_unique_piece ? "Oui" : "Non"}</dd>
            </div>
          </dl>

          {soldOut ? null : <AddToCartButton artworkId={artwork.id} />}

          <p className="mt-6 rounded-lg border border-border/25 bg-surface-muted/40 p-3.5 text-xs leading-relaxed text-text/80 backdrop-blur-xs">
            Le paiement en ligne arrive dans la phase suivante : vous pouvez déjà ajouter
            l&apos;œuvre à votre panier. En attendant, contactez l&apos;artiste via son profil.
          </p>
        </div>
      </div>

      <Suspense fallback={<div className="mt-14 h-48 animate-pulse rounded-lg bg-surface-muted" />}>
        <SimilarWorks slug={slug} />
      </Suspense>

      <ViewTracker slug={slug} />
    </main>
  );
}
