import type { Metadata } from "next";
import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { listVideos, proxiedUrl } from "@/lib/api";

export const metadata: Metadata = {
  title: "Vidéos — ArtFlow",
  description: "Les œuvres en vidéo : ateliers, détails et présentations d'artistes.",
};

export default async function VideosPage() {
  const videos = await listVideos().catch(() => []);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <div className="border-b border-border/20 pb-5">
        <h1 className="text-3xl font-bold tracking-tight text-primary-strong">Vidéos</h1>
        <p className="mt-1.5 text-sm text-text/80">
          {videos.length > 0
            ? `${videos.length} vidéo${videos.length > 1 ? "s" : ""} publiée${videos.length > 1 ? "s" : ""}.`
            : "Les vidéos des artistes arrivent bientôt."}
        </p>
      </div>

      <div className="mt-8">
        {videos.length === 0 ? (
          <EmptyState
            title="Aucune vidéo pour le moment."
            hint="Les artistes peuvent publier une vidéo par œuvre depuis leur espace."
            actionLabel="Explorer le catalogue"
            actionHref="/catalogue"
          />
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {videos.map((video) => (
              <article
                key={video.id}
                className="overflow-hidden rounded-xl glass-card transition-all duration-200 hover:-translate-y-0.5"
              >
                <div className="bg-black/90 aspect-video w-full overflow-hidden">
                  <video
                    controls
                    muted
                    playsInline
                    preload="metadata"
                    poster={proxiedUrl(video.poster_url) ?? undefined}
                    aria-label={video.alt_text_fr || video.artwork_title}
                    className="h-full w-full object-cover"
                  >
                    <source
                      src={video.stream_url ?? undefined}
                      type={video.content_type || "video/mp4"}
                    />
                  </video>
                </div>
                <div className="space-y-1.5 p-4">
                  <Link
                    href={`/oeuvre/${video.artwork_slug}`}
                    className="block truncate text-sm font-bold text-primary-strong hover:text-primary transition-colors"
                  >
                    {video.artwork_title}
                  </Link>
                  <Link
                    href={`/artistes/${video.artist_slug}`}
                    className="block truncate text-xs font-medium text-text/75 hover:text-primary-strong transition-colors"
                  >
                    {video.artist_display_name}
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
