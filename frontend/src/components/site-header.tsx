import Link from "next/link";
import { CartLink } from "@/components/cart/cart-link";

const NAV = [
  { href: "/catalogue", label: "Œuvres" },
  { href: "/videos", label: "Vidéos" },
  { href: "/artistes", label: "Artistes" },
];

const SECONDARY = [
  { href: "/devenir-artiste", label: "Devenir artiste" },
  { href: "/connexion", label: "Connexion" },
];

/** En-tête de site — composant serveur (aucune donnée privée exposée ici). */
export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 glass-bar">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="text-xl font-bold tracking-tight text-primary-strong transition hover:text-primary">
          ArtFlow
        </Link>

        <nav aria-label="Navigation principale" className="flex gap-4 text-sm font-semibold">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-full px-2.5 py-1 text-text/85 transition hover:bg-surface-muted/60 hover:text-primary-strong"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <nav aria-label="Navigation secondaire" className="flex items-center gap-2 sm:gap-3 text-sm font-semibold">
          <CartLink />
          {SECONDARY.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="hidden sm:inline-block rounded-full px-2.5 py-1 text-text/80 transition hover:bg-surface-muted/60 hover:text-primary-strong"
            >
              {item.label}
            </Link>
          ))}
          <Link
            href="/artiste"
            className="btn btn-primary px-3.5 py-1.5 text-xs sm:text-sm shadow-sm"
          >
            Espace artiste
          </Link>
        </nav>
      </div>
    </header>
  );
}

// ── Footer ──

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-border/25 py-8 text-center text-sm text-text/75">
      <div className="mx-auto max-w-6xl px-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs sm:text-sm">
        <p className="font-semibold text-primary-strong">
          ArtFlow — Marketplace d&apos;art au Cameroun.
        </p>
        <p className="text-text/70">
          Prix affichés en francs CFA (XAF).
        </p>
      </div>
    </footer>
  );
}
