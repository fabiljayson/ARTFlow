"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ApiError, me, type MeUser } from "@/lib/api";

type State = "loading" | "anonymous" | "forbidden" | "ok";

/**
 * Garde d'authentification pour les pages privées (client components).
 *
 * - 401 / 403 de `/auth/me` → redirection vers `/connexion?next=<chemin>`.
 * - `role="artist"` exige le rôle ARTIST ; `role="admin"` exige MODERATOR ou ADMIN.
 * - `onUser` expose le profil aux pages filles (tableau, formulaires).
 */
export function RequireAuth({
  children,
  role,
  onUser,
}: {
  children: ReactNode;
  role?: "artist" | "admin";
  onUser?: (user: MeUser | null) => void;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [state, setState] = useState<State>("loading");
  // Ref : évite de relancer l'effet quand le parent passe une fonction inline.
  const onUserRef = useRef(onUser);
  onUserRef.current = onUser;

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const profile = await me();
        if (cancelled) return;

        if (role === "artist" && !profile.is_artist && !profile.roles.includes("ARTIST")) {
          setState("forbidden");
          return;
        }
        if (role === "admin" && !profile.roles.some((r) => r === "MODERATOR" || r === "ADMIN")) {
          setState("forbidden");
          return;
        }
        onUserRef.current?.(profile);
        setState("ok");
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          router.replace(`/connexion?next=${encodeURIComponent(pathname)}`);
          return;
        }
        setState("forbidden");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [role, pathname, router]);

  if (state === "loading") {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16">
        <div className="h-24 animate-pulse rounded-lg bg-surface-muted" />
      </div>
    );
  }

  if (state === "anonymous") return null;

  if (state === "forbidden") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-primary-strong">Accès refusé</h1>
        <p className="mt-3 text-text/70">
          Votre compte ne dispose pas des permissions nécessaires pour cette page.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
