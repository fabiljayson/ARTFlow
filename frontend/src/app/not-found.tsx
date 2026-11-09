import Link from "next/link";

/** Page 404 — Next la sert pour les routes inconnues (artwork/artiste introuvable). */
export default function NotFound() {
  return (
    <main className="mx-auto flex max-w-2xl flex-col items-center px-4 py-24 text-center">
      <div className="rounded-2xl glass-strong p-8 sm:p-12 shadow-xl border border-border/25 flex flex-col items-center">
        <p className="text-7xl font-extrabold tracking-tight text-primary-strong">404</p>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-primary-strong">Page introuvable</h1>
        <p className="mt-3 text-base leading-relaxed text-text/80 max-w-md">
          Cette page n&apos;existe pas ou n&apos;est plus disponible. L&apos;œuvre peut avoir été
          retirée par son artiste ou refusée à la modération.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            href="/catalogue"
            className="btn btn-primary px-6 py-2.5 text-sm shadow-md"
          >
            Voir le catalogue
          </Link>
          <Link
            href="/"
            className="btn btn-secondary px-6 py-2.5 text-sm"
          >
            Retour à l&apos;accueil
          </Link>
        </div>
      </div>
    </main>
  );
}
