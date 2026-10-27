"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArtworkForm, type ArtworkFormValues } from "@/components/artwork-form";
import { RequireAuth } from "@/components/require-auth";
import { ApiError, createArtwork, listCategories, type Category } from "@/lib/api";

function CreateForm() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listCategories()
      .then((page) => {
        if (!cancelled) setCategories(page.results);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Catégories indisponibles.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(values: ArtworkFormValues) {
    const artwork = await createArtwork(values);
    // Redirige vers la fiche d'édition pour ajouter les images (requis pour publier).
    router.replace(`/artiste/oeuvres/${artwork.id}`);
    router.refresh();
  }

  if (error) {
    return (
        <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm ink-danger">
        {error}
      </p>
    );
  }

  if (categories.length === 0) {
    return <div className="h-64 animate-pulse rounded-lg bg-surface-muted" />;
  }

  return <ArtworkForm categories={categories} submitLabel="Créer l'œuvre" onSubmit={handleSubmit} />;
}

export default function NewArtworkPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <RequireAuth role="artist">
        <h1 className="text-3xl font-bold text-primary-strong">Nouvelle œuvre</h1>
        <p className="mt-2 text-text/70">
          Renseignez la fiche, puis ajoutez au moins une image avant de la soumettre à la
          modération.
        </p>
        <div className="mt-8">
          <CreateForm />
        </div>
      </RequireAuth>
    </main>
  );
}
