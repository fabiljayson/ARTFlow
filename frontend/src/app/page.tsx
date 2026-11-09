import Link from "next/link";
import { formatXAF } from "@/lib/money";
import { listCategories } from "@/lib/api";

export default async function HomePage() {
  const categories = await listCategories()
    .then((page) => page.results)
    .catch(() => []);

  return (
    <main className="relative overflow-hidden">
      {/* ── Lentille liquide d'atmosphère en arrière-plan (DESIGN.md: optical material layer) ── */}
      <div
        aria-hidden="true"
        className="liquid-lens -top-32 left-1/2 -translate-x-1/2 h-[480px] w-[720px] max-w-[95vw] opacity-80"
      />
      <div
        aria-hidden="true"
        className="liquid-lens top-56 -right-24 h-[360px] w-[360px] opacity-40"
      />

      <section className="relative z-10 mx-auto max-w-6xl px-4 py-16 sm:py-24">
        {/* Enveloppe de verre liquide pour ancrer le contenu du héros */}
        <div className="relative rounded-2xl glass-strong p-6 sm:p-10 lg:p-12 overflow-hidden shadow-xl">
          {/* Reflet spéculaire interne au bord supérieur */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/80 to-transparent"
          />

          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full glass-pill px-3 py-1 text-xs font-semibold text-primary-strong mb-4">
              <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
              Place de marché d&apos;art contemporain &amp; traditionnel
            </div>

            <h1 className="text-4xl font-bold tracking-tight text-primary-strong sm:text-5xl lg:text-6xl">
              L&apos;art camerounais, en un flux.
            </h1>

            <p className="mt-5 text-lg leading-relaxed text-text/85 max-w-2xl">
              Découvrez des œuvres uniques — peintures, sculptures, créations artisanales — et
              soutenez les artistes du Cameroun. Exemple de prix :{" "}
              <strong className="font-bold text-primary-strong">{formatXAF(100000)}</strong>.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                href="/catalogue"
                className="btn btn-primary px-6 py-3 text-base shadow-md"
              >
                Explorer le catalogue
              </Link>
              <Link
                href="/devenir-artiste"
                className="btn btn-secondary px-6 py-3 text-base"
              >
                Vendre mes œuvres
              </Link>
            </div>
          </div>

          <nav aria-label="Catégories" className="mt-14 pt-8 border-t border-border/20">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-text/75">
              Catégories
            </h2>
            <ul className="mt-4 flex flex-wrap gap-2.5">
              {categories.map((c) => (
                <li key={c.slug}>
                  <Link
                    href={`/catalogue?category=${c.slug}`}
                    className="glass-pill inline-block px-4 py-2 text-sm font-semibold text-text/90 transition hover:border-primary hover:text-primary-strong hover:scale-[1.02]"
                  >
                    {c.name_fr}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </section>
    </main>
  );
}
