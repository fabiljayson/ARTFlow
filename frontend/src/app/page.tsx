import Link from "next/link";
import { formatXAF } from "@/lib/money";
import { listCategories } from "@/lib/api";

export default async function HomePage() {
  const categories = await listCategories()
    .then((page) => page.results)
    .catch(() => []);

  return (
    <main>
      <section className="mx-auto max-w-6xl px-4 py-16">
        <h1 className="text-4xl font-bold text-primary-strong sm:text-5xl">
          L&apos;art camerounais, en un flux.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-text/80">
          Découvrez des œuvres uniques — peintures, sculptures, créations artisanales — et
          soutenez les artistes du Cameroun. Exemple de prix :{" "}
          <strong className="text-primary-strong">{formatXAF(100000)}</strong>.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/catalogue"
            className="btn btn-primary px-5 py-2.5"
          >
            Explorer le catalogue
          </Link>
          <Link
            href="/devenir-artiste"
            className="btn btn-secondary px-5 py-2.5"
          >
            Vendre mes œuvres
          </Link>
        </div>

        <nav aria-label="Catégories" className="mt-12">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-text/70">
            Catégories
          </h2>
          <ul className="mt-3 flex flex-wrap gap-2">
            {categories.map((c) => (
              <li key={c.slug}>
                <Link
                  href={`/catalogue?category=${c.slug}`}
                  className="inline-block rounded-full border border-border/40 bg-surface-muted px-4 py-1.5 text-sm transition hover:border-primary/50 hover:text-primary-strong"
                >
                  {c.name_fr}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </section>
    </main>
  );
}
