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
    <header className="glass-bar">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="text-xl font-bold tracking-tight text-primary">
          ArtFlow
        </Link>

        <nav aria-label="Navigation principale" className="flex gap-4 text-sm font-semibold">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-text/80 transition hover:text-primary-strong"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <nav aria-label="Navigation secondaire" className="flex items-center gap-3 text-sm font-semibold">
          <CartLink />
          {SECONDARY.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-text/75 transition hover:text-primary-strong"
            >
              {item.label}
            </Link>
          ))}
          <Link
            href="/artiste"
            className="btn btn-primary px-3 py-1.5"
          >
            Espace artiste
          </Link>
        </nav>
      </div>
    </header>
  );
}

/** Pied de site. */
export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-border/30 py-8 text-center text-sm text-text/70">
      ArtFlow — Marketplace d&apos;art au Cameroun. Prix affichés en francs CFA (XAF).
    </footer>
  );
}
