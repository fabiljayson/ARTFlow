import Link from "next/link";
import { formatXAF } from "@/lib/money";

const CATEGORIES = ["Peinture", "Sculpture", "Artisanat", "Contemporain"];

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <header className="border-b border-border/30 bg-surface-muted/60 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <span className="text-xl font-bold tracking-tight text-primary">ArtFlow</span>
          <nav aria-label="Navigation principale" className="flex gap-4 text-sm font-medium">
            <Link href="/catalogue">Œuvres</Link>
            <Link href="/videos">Vidéos</Link>
            <Link href="/devenir-artiste">Devenir artiste</Link>
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h1 className="text-4xl font-bold text-primary-strong sm:text-5xl">
          L&apos;art camerounais, en un flux.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-text/80">
          Découvrez des œuvres uniques — peintures, sculptures, créations artisanales — et
          soutenez les artistes du Cameroun. Exemple de prix :{" "}
          <strong className="text-primary">{formatXAF(100000)}</strong>.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/catalogue"
            className="rounded-md bg-primary px-5 py-2.5 font-semibold text-white transition hover:bg-primary-strong"
          >
            Explorer le catalogue
          </Link>
          <Link
            href="/devenir-artiste"
            className="rounded-md border border-border px-5 py-2.5 font-semibold text-text transition hover:bg-surface-muted"
          >
            Vendre mes œuvres
          </Link>
        </div>

        <nav aria-label="Catégories" className="mt-12">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-text/60">
            Catégories
          </h2>
          <ul className="mt-3 flex flex-wrap gap-2">
            {CATEGORIES.map((c) => (
              <li key={c}>
                <span className="rounded-full border border-border/40 bg-surface-muted px-4 py-1.5 text-sm">
                  {c}
                </span>
              </li>
            ))}
          </ul>
        </nav>
      </section>

      <footer className="border-t border-border/30 py-8 text-center text-sm text-text/60">
        ArtFlow — Phase B (fondation). Toutes les fonctionnalités arrivent en Phase C+.
      </footer>
    </main>
  );
}
