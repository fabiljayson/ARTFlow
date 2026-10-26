# ArtFlow — Stratégie de tests

> Phase A. Outils : **pytest** (+ pytest-django) backend, **Vitest** front composants, **Playwright** E2E. Règle : jamais déclarer un test vert sans exécution réelle ; rapport de phase distingue verts/échoués/bloqués/non exécutés.

## 1. Pyramide

```
E2E Playwright (12 scénarios prompt + critiques)     ~30
Intégration API (DRF APIClient + DB)                 ~250
Unitaires (services, calculs, machines à états)      ~150
```

## 2. Backend — organisation

```
backend/apps/<app>/tests/
  test_models.py
  test_services.py
  test_api_<resource>.py
  test_permissions.py
backend/apps/core/tests/test_scenarios.py   # E2E API scénarios A–L
backend/apps/core/tests/test_security.py    # invariants
```

- Fixtures : factories (factory_boy) ; DB transactionnelle ; **chaque test crée ses users** (pas de partage).
- `APIClient` sessions (cookies) pour coller au produit réel.
- MockPaymentGateway activé par défaut en tests ; quelques tests webhook « brut » signés HMAC.

## 3. Catalogue de tests unitaires obligatoires

| Domaine | Cas |
|---|---|
| Commission | table 20 cas, floor, multi-qty, multi-vendeur, taux figé historique |
| Totaux commande | livraison par vendeur, 0 items refusé, quantity bornée |
| Machines à états | artworks, applications, payments, orders, shipments, disputes — transitions légales/illégales |
| Réservation TTL | expiration, conversion, double release idempotent |
| Arrondis | property test léger (hypothesis optionnel) |
| Permissions | matrice rôles × actions |
| Politiques | 1 published max/language, hash content |
| Validation média | magic bytes, quota, alt obligatoire |

## 4. Intégration API (exemples d'authentification)

- Auth session login/logout/CSRF.
- Candidature DRAFT→PENDING→APPROVED (+ NEEDS_INFO).
- Upload œuvre par artiste non approuvé → 403 ; approuvé → 201.
- Catalogue : seul PUBLISHED visible ; recherche, filtres, tri, pagination.
- Checkout quote : prix manipulés côté client ignorés.
- Checkout : stock réservé ; concurrence (TransactionTestCase + threads ou simulation séquentielle du verrou).
- Webhook mock : succès, échec, rejeu, signature invalide, montant différent.
- Refund : bornes, double exécution refusée.
- Litige : flux complet + preuves privées 404 hors périmètre.
- Expéditions multi-artistes indépendantes.
- Admin : candidature, modération œuvre, settings.

## 5. E2E Playwright (scénarios du prompt §18)

| # | Scénario |
|---|---|
| 1 | Visiteur consulte catalogue + fiche + vidéo (poster, muet) |
| 2 | Acheteur crée compte (CGU versionnée cochée) |
| 3 | Artiste soumet candidature + document |
| 4 | Admin approuve l'artiste |
| 5 | Artiste publie une œuvre (modération) |
| 6 | Acheteur ajoute au panier |
| 7 | Backend calcule total exact (assert UI = API) |
| 8 | Paiement confirmé via simulateur |
| 9 | Commande créée + stock correct |
| 10 | Artiste marque expédié ; acheteur voit suivi |
| 11 | Litige ouvert + preuve + décision |
| 12 | Remboursement simulé tracé (admin) |

### Scénarios critiques (au moins)
- Deux acheteurs, même œuvre unique → 1 gagnant.
- Prix falsifié navigateur → ignoré.
- Webhook faux → rejet ; rejeu → no-op.
- Paiement échoué → stock libéré.
- Webhook perdu → poll confirme.
- IDOR commandes/œuvres/documents.
- Politique change de version → ancienne acceptation reste valable, nouvelle exigée au prochain achat (politique d'affichage).
- Vidéo indisponible → fallback poster.
- Image externe démo en erreur → placeholder.

## 6. Front (Vitest + RTL)

- Composants : boutons, champs, modales (focus/escape), cartes œuvre, états empty/error/loading.
- Pages : panier (affichage serveur), checkout erreurs, espace artiste.
- `renderPage` helpers avec providers (session, query).

## 7. CI (GitHub Actions)

| Job | Contenu |
|---|---|
| backend | uv sync, ruff, pytest, makemigrations --check, pip-audit |
| frontend | npm ci, oxlint/eslint, tsc, vitest, build |
| e2e | playwright install --with-deps, stack up (postgres service), run e2e (main only ou nightly si lent) |
| security | bandit, npm audit, gitleaks |

Échec = blocant. Pas de `continue-on-error` permanent ; toute exception = TODO daté + issue.

## 8. Performance (Phase G)

- Lighthouse/cwv sur pages publiques (LCP ≤ 2,5 s p75, INP ≤ 200 ms, CLS ≤ 0,1) — mesures locales indicatives + après déploiement réel.
- `EXPLAIN ANALYZE` sur requêtes catalogue (recherche trigram, filtres, pagination keyset si besoin).
- k6 (optionnel) : 50 users concurrents catalogue + 10 checkouts (verrou stock).

## 9. Commandes cibles (Phase B+)

```bash
# backend
cd backend && uv run pytest
uv run ruff check .
uv run python manage.py makemigrations --check --dry-run

# frontend
cd frontend && npm run lint && npm test && npm run build

# e2e
cd frontend && npx playwright test
```
