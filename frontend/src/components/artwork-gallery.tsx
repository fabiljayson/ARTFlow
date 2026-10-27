"use client";

import { useState } from "react";
import { MediaImage } from "@/components/media-image";
import { proxiedUrl, type Media } from "@/lib/api";

/**
 * Galerie d'une œuvre : images en 4/5 (une principale + vignettes) et vidéo
 * jouable en dessous. Purement client — le changement de vignette n'est pas
 * une navigation.
 */
export function ArtworkGallery({
  images,
  videos,
  title,
}: {
  images: Media[];
  videos: Media[];
  title: string;
}) {
  const [selected, setSelected] = useState(0);
  const current = images[selected];

  if (images.length === 0 && videos.length === 0) {
    return (
      <div className="flex aspect-[4/5] items-center justify-center rounded-lg border border-dashed border-border/40 bg-white/50 text-sm text-text/50">
        Aucun média pour cette œuvre.
      </div>
    );
  }

  return (
    <div>
      <div className="relative aspect-[4/5] w-full overflow-hidden rounded-lg border border-border/25 bg-surface-muted">
        <MediaImage
          src={current?.thumbnail_url ?? current?.stream_url ?? null}
          alt={current?.alt_text_fr || title}
          fill
          sizes="(max-width: 1024px) 100vw, 50vw"
          priority
          className="object-cover"
        />
      </div>

      {images.length > 1 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {images.map((image, index) => (
            <button
              key={image.id}
              type="button"
              onClick={() => setSelected(index)}
              aria-label={`Voir l'image ${index + 1}`}
              aria-pressed={index === selected}
              className={`relative h-20 w-16 overflow-hidden rounded-md border-2 transition ${
                index === selected ? "border-primary" : "border-transparent opacity-70 hover:opacity-100"
              }`}
            >
              <MediaImage
                src={image.thumbnail_url ?? image.stream_url}
                alt={image.alt_text_fr}
                fill
                sizes="64px"
                className="object-cover"
              />
            </button>
          ))}
        </div>
      ) : null}

      {videos.length > 0 ? (
        <div className="mt-4 space-y-3">
          {videos.map((video) => (
            <div key={video.id} className="overflow-hidden rounded-lg border border-border/25 bg-black">
              <video
                controls
                muted
                playsInline
                preload="metadata"
                poster={proxiedUrl(video.poster_url) ?? undefined}
                aria-label={video.alt_text_fr || `Vidéo de ${title}`}
                className="aspect-video w-full"
              >
                <source src={video.stream_url ?? undefined} type={video.content_type || "video/mp4"} />
              </video>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
