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
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border/30 bg-surface/50 p-8 text-center backdrop-blur-md">
      <div className="h-10 w-10 rounded-full glass-pill flex items-center justify-center text-primary-strong mb-2 shadow-xs">
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          className="h-5 w-5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
          />
        </svg>
      </div>
      <p className="text-base font-bold text-primary-strong">{title}</p>
      {hint ? <p className="max-w-md text-sm text-text/80">{hint}</p> : null}
      {actionLabel && actionHref ? (
        <Link
          href={actionHref}
          className="btn btn-primary mt-3 px-5 py-2 text-sm shadow-sm"
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}
