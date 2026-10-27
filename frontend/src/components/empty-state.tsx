import Link from "next/link";

/** État vide réutilisable (aucun résultat, aucun favori, aucune vidéo…). */
export function EmptyState({
  title,
  hint,
  actionLabel,
  actionHref,
}: {
  title: string;
  hint?: string;
  actionLabel?: string;
  actionHref?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border/40 bg-white/50 px-6 py-12 text-center">
      <p className="text-base font-semibold text-text">{title}</p>
      {hint ? <p className="max-w-md text-sm text-text/60">{hint}</p> : null}
      {actionLabel && actionHref ? (
        <Link
          href={actionHref}
          className="mt-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-strong"
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}
