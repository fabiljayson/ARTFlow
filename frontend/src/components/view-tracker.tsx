"use client";

import { useEffect } from "react";
import { recordView } from "@/lib/api";

/**
 * Enregistre la vue de l'œuvre au montage (design preuve sociale §2).
 * Rend `null` : effet uniquement, aucun état, aucune erreur affichée.
 */
export function ViewTracker({ slug }: { slug: string }) {
  useEffect(() => {
    recordView(slug).catch(() => {});
  }, [slug]);
  return null;
}
