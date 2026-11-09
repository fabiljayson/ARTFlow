import type { ArtworkStatus } from "@/lib/api";

const TONES: Record<ArtworkStatus, string> = {
  DRAFT: "bg-surface-muted/60 text-text/85 border-border/30",
  IN_MODERATION: "bg-warning/15 ink-warning border-warning/40",
  PUBLISHED: "bg-success/15 ink-success border-success/40",
  REFUSED: "bg-danger/15 ink-danger border-danger/40",
  HIDDEN: "bg-surface-muted/50 text-text/75 border-border/25",
  ARCHIVED: "bg-surface-muted/40 text-text/70 border-border/20",
};

const LABELS: Record<ArtworkStatus, string> = {
  DRAFT: "Brouillon",
  IN_MODERATION: "En modération",
  PUBLISHED: "Publié",
  REFUSED: "Refusé",
  HIDDEN: "Masqué",
  ARCHIVED: "Archivé",
};

/** Badge de statut d'œuvre — libellés FR alignés sur ArtworkStatus (DESIGN.md glass widget). */
export function StatusBadge({ status }: { status: ArtworkStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold shadow-xs backdrop-blur-xs ${TONES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}
