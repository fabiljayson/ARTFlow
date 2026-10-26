# ADR-0002 : Authentification par sessions cookie

- **Statut** : accepté (Phase A, validation commanditaire)
- **Contexte** : marketplace web SSR même-origine ; alternatives JWT.
- **Décision** : sessions **Django côté serveur**, cookie `sessionid` HttpOnly + SameSite=Lax (+Secure en prod) ; CSRF standard Django (token double-submit) ; front appelle l'API avec `credentials: 'include'`.
- **Alternatives rejetées** : JWT stateless (surface d'attaque plus large, gestion refresh/blacklist déjà vue ailleurs, inutile sans app mobile au MVP).
- **Conséquences** : logout immédiat possible (delete session) ; scaling horizontal nécessite store session partagé (DB/Redis) — acceptable (sessions en table PostgreSQL) ; si apps natives plus tard : réévaluer (ADR future).
