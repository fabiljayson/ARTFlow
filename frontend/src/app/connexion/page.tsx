"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { Button } from "@/components/button";
import { ApiError, getCsrf, login } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      // Pose le cookie CSRF avant le POST (double submit).
      await getCsrf();
      await login({ email: email.trim(), password });
      // `next` est un chemin interne relatif — on ne laisse pas un URL externe fuiter.
      const target = next && next.startsWith("/") && !next.startsWith("//") ? next : "/artiste";
      router.replace(target);
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Connexion impossible pour le moment. Réessayez.",
      );
      setPending(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-4 py-14">
      <div className="rounded-2xl glass-strong p-6 sm:p-8 shadow-xl border border-border/25">
        <h1 className="text-3xl font-bold tracking-tight text-primary-strong">Connexion</h1>
        <p className="mt-2 text-sm text-text/80">
          Accédez à votre espace artiste ou à vos favoris.
        </p>

        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-sm">
            <span className="font-medium text-text/85">Adresse e-mail</span>
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-border/30 bg-white/95 px-3.5 py-2.5 text-sm text-text shadow-xs placeholder:text-text/45 transition focus:border-primary focus:outline-none"
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium text-text/85">Mot de passe</span>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-border/30 bg-white/95 px-3.5 py-2.5 text-sm text-text shadow-xs placeholder:text-text/45 transition focus:border-primary focus:outline-none"
            />
          </label>

          {error ? (
            <p role="alert" className="rounded-lg border border-danger/40 bg-danger/10 px-3.5 py-2.5 text-sm font-semibold ink-danger">
              {error}
            </p>
          ) : null}

          <Button type="submit" disabled={pending} className="w-full py-2.5 mt-2 shadow-md">
            {pending ? "Connexion en cours…" : "Se connecter"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-text/80">
          Pas encore de compte ?{" "}
          <Link href="/inscription" className="font-semibold text-primary-strong hover:text-primary underline">
            Créer un compte
          </Link>
        </p>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
