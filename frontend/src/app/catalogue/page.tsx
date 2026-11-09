import type { Metadata } from "next";
import Link from "next/link";
import { ArtworkCard } from "@/components/artwork-card";
import { EmptyState } from "@/components/empty-state";
import { Pagination } from "@/components/pagination";
import { buildCatalogQuery, listCatalogue, listCategories } from "@/lib/api";

export const metadata: Metadata = {
  title: "Catalogue — ArtFlow",
  description: "Parcourez les œuvres d'art camerounaises disponibles sur ArtFlow.",
};

const PAGE_SIZE = 20;

type SearchParams = Promise<{
  q?: string;
  category?: string;
  price_min?: string;
  price_max?: string;
  available?: string;
  sort?: string;
  page?: string;
}>;

export default async function CataloguePage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;

  const filters = {
    q: params.q,
    category: params.category,
    price_min: params.price_min,
    price_max: params.price_max,
    available: params.available,
    sort: params.sort,
    page: params.page,
  };

  const [page, categories] = await Promise.all([
    listCatalogue(filters),
    listCategories()
      .then((c) => c.results)
      .catch(() => []),
  ]);

  const current = Number(params.page ?? "1") || 1;
  // Query string sans `page` — conservée par la pagination.
  const query = buildCatalogQuery({ ...filters, page: undefined });

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 border-b border-border/20 pb-5">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-primary-strong">Catalogue</h1>
          <p className="mt-1.5 text-sm text-text/80">
            {page.count} œuvre{page.count > 1 ? "s" : ""} disponible{page.count > 1 ? "s" : ""}
          </p>
        </div>
      </div>

      <form method="GET" action="/catalogue" className="mt-6 rounded-xl glass-strong p-5">
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-5">
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium text-text/85">Recherche</span>
            <input
              type="text"
              name="q"
              defaultValue={params.q ?? ""}
              placeholder="Titre, description…"
              className="rounded-lg border border-border/30 bg-white/95 px-3 py-2 text-sm text-text shadow-xs placeholder:text-text/45 transition focus:border-primary focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium text-text/85">Catégorie</span>
            <select
              name="category"
              defaultValue={params.category ?? ""}
              className="rounded-lg border border-border/30 bg-white/95 px-3 py-2 text-sm text-text shadow-xs transition focus:border-primary focus:outline-none"
            >
              <option value="">Toutes</option>
              {categories.map((c) => (
                <option key={c.slug} value={c.slug}>
                  {c.name_fr}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium text-text/85">Prix min (XAF)</span>
            <input
              type="text"
              inputMode="numeric"
              name="price_min"
              defaultValue={params.price_min ?? ""}
              placeholder="0"
              className="rounded-lg border border-border/30 bg-white/95 px-3 py-2 text-sm text-text shadow-xs placeholder:text-text/45 transition focus:border-primary focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium text-text/85">Prix max (XAF)</span>
            <input
              type="text"
              inputMode="numeric"
              name="price_max"
              defaultValue={params.price_max ?? ""}
              placeholder="500000"
              className="rounded-lg border border-border/30 bg-white/95 px-3 py-2 text-sm text-text shadow-xs placeholder:text-text/45 transition focus:border-primary focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium text-text/85">Tri</span>
            <select
              name="sort"
              defaultValue={params.sort ?? "-date"}
              className="rounded-lg border border-border/30 bg-white/95 px-3 py-2 text-sm text-text shadow-xs transition focus:border-primary focus:outline-none"
            >
              <option value="-date">Plus récentes</option>
              <option value="date">Plus anciennes</option>
              <option value="price">Prix croissant</option>
              <option value="-price">Prix décroissant</option>
              <option value="title">Titre A → Z</option>
              <option value="trending">Tendances · 7 jours</option>
            </select>
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border/15">
          <label className="flex items-center gap-2 text-sm font-medium text-text/80 cursor-pointer">
            <input
              type="checkbox"
              name="available"
              value="true"
              defaultChecked={params.available === "true"}
              className="h-4 w-4 rounded accent-primary cursor-pointer"
            />
            Disponibles uniquement
          </label>
          <div className="flex gap-2">
            <button
              type="submit"
              className="btn btn-primary px-4 py-2 text-sm shadow-sm"
            >
              Appliquer
            </button>
            <Link
              href="/catalogue"
              className="btn btn-secondary px-4 py-2 text-sm"
            >
              Réinitialiser
            </Link>
          </div>
        </div>
      </form>

      <div className="mt-8">
        {page.results.length === 0 ? (
          <EmptyState
            title="Aucune œuvre ne correspond à ces critères."
            hint="Essayez d'élargir la fourchette de prix ou de retirer un filtre."
            actionLabel="Réinitialiser les filtres"
            actionHref="/catalogue"
          />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {page.results.map((artwork) => (
                <ArtworkCard key={artwork.id} artwork={artwork} />
              ))}
            </div>
            <Pagination
              count={page.count}
              pageSize={PAGE_SIZE}
              current={current}
              query={query}
            />
          </>
        )}
      </div>
    </main>
  );
}
