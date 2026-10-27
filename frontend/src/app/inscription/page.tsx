"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/button";
import { ApiError, getCsrf, register } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    phone: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function update(field: keyof typeof form) {
    return (event: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: event.target.value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await getCsrf();
      await register({
        email: form.email.trim(),
        password: form.password,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim() || undefined,
      });
      router.replace("/artiste");
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Inscription impossible pour le moment.",
      );
      setPending(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-4 py-14">
      <h1 className="text-3xl font-bold text-primary-strong">Créer un compte</h1>
      <p className="mt-2 text-sm text-text/70">
        Aucune case à cocher ici : les conditions générales arrivent en Phase F.
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-sm">
            <span className="text-text/70">Prénom</span>
            <input
              type="text"
              autoComplete="given-name"
              value={form.first_name}
              onChange={update("first_name")}
              className="mt-1 w-full rounded-md border border-border/40 bg-white px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            <span className="text-text/70">Nom</span>
            <input
              type="text"
              autoComplete="family-name"
              value={form.last_name}
              onChange={update("last_name")}
              className="mt-1 w-full rounded-md border border-border/40 bg-white px-3 py-2"
            />
          </label>
        </div>

        <label className="block text-sm">
          <span className="text-text/70">Adresse e-mail</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={form.email}
            onChange={update("email")}
            className="mt-1 w-full rounded-md border border-border/40 bg-white px-3 py-2"
          />
        </label>

        <label className="block text-sm">
          <span className="text-text/70">Téléphone (optionnel)</span>
          <input
            type="tel"
            autoComplete="tel"
            placeholder="+2376XXXXXXXX"
            value={form.phone}
            onChange={update("phone")}
            className="mt-1 w-full rounded-md border border-border/40 bg-white px-3 py-2"
          />
        </label>

        <label className="block text-sm">
          <span className="text-text/70">Mot de passe</span>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={form.password}
            onChange={update("password")}
            className="mt-1 w-full rounded-md border border-border/40 bg-white px-3 py-2"
          />
          <span className="mt-1 block text-xs text-text/60">
            8 caractères minimum — ni un mot courant, ni uniquement des chiffres.
          </span>
        </label>

        {error ? (
          <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </p>
        ) : null}

        <Button type="submit" disabled={pending} className="w-full">
          {pending ? "Création en cours…" : "Créer mon compte"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-text/70">
        Déjà inscrit ?{" "}
        <Link href="/connexion" className="font-medium text-primary hover:underline">
          Se connecter
        </Link>
      </p>
    </main>
  );
}
