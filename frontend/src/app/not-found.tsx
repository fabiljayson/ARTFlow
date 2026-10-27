import Link from "next/link";

/** Page 404 — Next la sert pour les routes inconnues (artwork/artiste introuvable). */
export default function NotFound() {
  return (
    <main className="mx-auto flex max-w-2xl flex-col items-center px-4 py-24 text-center">
      <p className="text-6xl font-bold text-primary">404</p>
      <h1 className="mt-4 text-2xl font-bold text-primary-strong">Page introuvable</h1>
      <p className="mt-3 text-text/70">
        Cette page n&apos;existe pas ou n&apos;est plus disponible. L&apos;œuvre peut avoir été
        retirée par son artiste ou refusée à la modération.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link
          href="/catalogue"
          className="rounded-md bg-primary px-5 py-2.5 font-semibold text-white transition hover:bg-primary-strong"
        >
          Voir le catalogue
        </Link>
        <Link
          href="/"
          className="rounded-md border border-border/50 bg-white/70 px-5 py-2.5 font-semibold transition hover:bg-surface-muted"
        >
          Retour à l&apos;accueil
        </Link>
      </div>
    </main>
  );
}
