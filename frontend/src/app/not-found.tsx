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
          className="btn btn-primary px-5 py-2.5"
        >
          Voir le catalogue
        </Link>
        <Link
          href="/"
          className="btn btn-secondary px-5 py-2.5"
        >
          Retour à l&apos;accueil
        </Link>
      </div>
    </main>
  );
}
