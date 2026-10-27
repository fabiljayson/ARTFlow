import Link from "next/link";

/**
 * Pagination du catalogue — liens serveur (pas de JS requis).
 * Conserve les filtres existants via `query` (query string sans `page`).
 */
export function Pagination({
  count,
  pageSize,
  current,
  query,
}: {
  count: number;
  pageSize: number;
  current: number;
  query: string;
}) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  if (totalPages <= 1) return null;

  const linkFor = (page: number) => {
    const params = new URLSearchParams(query);
    params.set("page", String(page));
    return `?${params.toString()}`;
  };

  const pageWindow = [];
  for (let p = Math.max(1, current - 2); p <= Math.min(totalPages, current + 2); p++) {
    pageWindow.push(p);
  }

  return (
    <nav aria-label="Pagination" className="mt-8 flex items-center justify-center gap-2 text-sm">
      {current > 1 ? (
        <Link
          href={linkFor(current - 1)}
          className="rounded-md border border-border/40 bg-white/70 px-3 py-1.5 transition hover:bg-surface-muted"
        >
          Précédent
        </Link>
      ) : null}

      {pageWindow.map((page) =>
        page === current ? (
          <span
            key={page}
            aria-current="page"
            className="rounded-md bg-primary px-3 py-1.5 font-semibold text-white"
          >
            {page}
          </span>
        ) : (
          <Link
            key={page}
            href={linkFor(page)}
            className="rounded-md border border-border/40 bg-white/70 px-3 py-1.5 transition hover:bg-surface-muted"
          >
            {page}
          </Link>
        ),
      )}

      {current < totalPages ? (
        <Link
          href={linkFor(current + 1)}
          className="rounded-md border border-border/40 bg-white/70 px-3 py-1.5 transition hover:bg-surface-muted"
        >
          Suivant
        </Link>
      ) : null}
    </nav>
  );
}
