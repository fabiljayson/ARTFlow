import Link from "next/link";

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
    <header className="border-b border-border/30 bg-surface-muted/60 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="text-xl font-bold tracking-tight text-primary">
          ArtFlow
        </Link>

        <nav aria-label="Navigation principale" className="flex gap-4 text-sm font-medium">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-text/80 transition hover:text-primary"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <nav aria-label="Navigation secondaire" className="flex gap-3 text-sm">
          {SECONDARY.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-text/60 transition hover:text-primary"
            >
              {item.label}
            </Link>
          ))}
          <Link
            href="/artiste"
            className="rounded-md bg-primary px-3 py-1.5 font-semibold text-white transition hover:bg-primary-strong"
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
    <footer className="mt-16 border-t border-border/30 py-8 text-center text-sm text-text/60">
      ArtFlow — Marketplace d&apos;art au Cameroun. Prix affichés en francs CFA (XAF).
    </footer>
  );
}
