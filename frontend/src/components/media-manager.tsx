"use client";

import { useState, type ChangeEvent } from "react";
import { MediaImage } from "@/components/media-image";
import {
  ApiError,
  deleteArtworkMedia,
  uploadArtworkMedia,
  type Media,
} from "@/lib/api";

/**
 * Gestionnaire de médias d'une œuvre — upload (image/vidéo) et suppression.
 * Les quotas (10 images / 1 vidéo) et le texte alternatif sont validés côté backend.
 */
export function MediaManager({ artworkId }: { artworkId: number }) {
  const [media, setMedia] = useState<Media[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setError(null);
    setInfo(null);

    const isVideo = file.type.startsWith("video/");
    const alt = window.prompt(
      isVideo
        ? "Description de la vidéo (facultatif) :"
        : "Texte alternatif de l'image (obligatoire, décrit l'œuvre) :",
      "",
    );
    if (alt === null) return;
    if (!isVideo && !alt.trim()) {
      setError("Le texte alternatif est obligatoire pour les images.");
      return;
    }

    const form = new FormData();
    form.append("kind", isVideo ? "VIDEO" : "IMAGE");
    form.append("file", file);
    if (alt.trim()) form.append("alt_text_fr", alt.trim());
    if (media.length === 0) form.append("is_primary", "true");

    setPending(true);
    try {
      const created = await uploadArtworkMedia(artworkId, form);
      setMedia((prev) => [...prev, created]);
      setInfo(isVideo ? "Vidéo ajoutée." : "Image ajoutée.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Envoi impossible.");
    } finally {
      setPending(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Supprimer ce média ?")) return;
    setBusyId(id);
    setError(null);
    try {
      await deleteArtworkMedia(artworkId, id);
      setMedia((prev) => prev.filter((item) => item.id !== id));
      setInfo("Média supprimé.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Suppression impossible.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-text">Médias</h2>
        <label
          className={`btn btn-primary px-4 py-2 text-sm ${
            pending ? "pointer-events-none opacity-60" : ""
          }`}
        >
          {pending ? "Envoi en cours…" : "Ajouter un fichier"}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,video/mp4,video/webm"
            className="hidden"
            disabled={pending}
            onChange={(e) => void handleUpload(e)}
          />
        </label>
      </div>

      <p className="text-xs text-text/70">
        Images : JPEG, PNG ou WebP (texte alternatif obligatoire, 10 max). Vidéo : MP4 ou
        WebM, 1 max.
      </p>

      {error ? (
        <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm ink-danger">
          {error}
        </p>
      ) : null}
      {info ? <p className="text-sm ink-success">{info}</p> : null}

      {media.length === 0 ? (
        <p className="rounded-md border border-dashed border-border/40 bg-white/50 px-4 py-6 text-sm text-text/70">
          Aucun média ajouté depuis l&apos;ouverture de cette page. Ajoutez au moins une image
          pour pouvoir soumettre l&apos;œuvre à la modération.
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {media.map((item) => (
            <li key={item.id} className="overflow-hidden rounded-lg glass-card">
              <div className="relative aspect-[4/5] bg-surface-muted">
                {item.kind === "IMAGE" ? (
                  <MediaImage
                    src={item.thumbnail_url ?? item.stream_url}
                    alt={item.alt_text_fr || "Image de l'œuvre"}
                    fill
                    sizes="200px"
                    className="object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-xs text-text/75">
                    Vidéo
                    {item.is_primary ? (
                      <span className="absolute left-1 top-1 rounded-full bg-primary-strong px-1.5 py-0.5 text-[10px] font-medium text-white">
                        Principale
                      </span>
                    ) : null}
                  </div>
                )}
                {item.kind === "IMAGE" && item.is_primary ? (
                  <span className="absolute left-1 top-1 rounded-full bg-primary-strong px-1.5 py-0.5 text-[10px] font-medium text-white">
                    Principale
                  </span>
                ) : null}
              </div>
              <div className="flex items-center justify-between gap-2 p-2">
                <span className="truncate text-xs text-text/70">
                  {item.kind === "IMAGE" ? "Image" : "Vidéo"}
                </span>
                <button
                  type="button"
                  onClick={() => void handleDelete(item.id)}
                  disabled={busyId === item.id}
                  className="text-xs font-medium text-danger hover:underline disabled:opacity-50"
                >
                  {busyId === item.id ? "…" : "Supprimer"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
