import type { ArtworkStatus } from "@/lib/api";

const TONES: Record<ArtworkStatus, string> = {
  DRAFT: "bg-text/10 text-text/70 border-border/40",
  IN_MODERATION: "bg-warning/15 text-warning border-warning/40",
  PUBLISHED: "bg-success/15 text-success border-success/40",
  REFUSED: "bg-danger/15 text-danger border-danger/40",
  HIDDEN: "bg-text/10 text-text/60 border-border/40",
  ARCHIVED: "bg-text/10 text-text/50 border-border/30",
};

const LABELS: Record<ArtworkStatus, string> = {
  DRAFT: "Brouillon",
  IN_MODERATION: "En modération",
  PUBLISHED: "Publié",
  REFUSED: "Refusé",
  HIDDEN: "Masqué",
  ARCHIVED: "Archivé",
};

/** Badge de statut d'œuvre — libellés FR alignés sur ArtworkStatus. */
export function StatusBadge({ status }: { status: ArtworkStatus }) {
  return (
    <span
      className={`inline-block rounded-md border px-2 py-0.5 text-xs font-medium ${TONES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}
