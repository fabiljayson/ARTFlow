# ArtFlow — Contrats d'API (pré-OpenAPI)

> Phase A. Le spec OpenAPI formel sera **généré depuis le code** (drf-spectacular) en Phase B+ ; ce document fige les routes, verbes, permissions et enveloppes d'erreur attendues. Préfixe : `/api/v1/`. Auth : cookie de session + header `X-CSRFToken` sur mutations.

## 1. Conventions

- JSON camelCase côté API ? **Non** — snake_case (aligné Django/DRF), le front convertit si besoin (défaut : snake_case partout).
- Pagination : `?page=` cursor ou offset ? **Offset simple** au MVP (`count`, `next`, `previous`, `results`) ; keyset si perf exigée.
- Erreurs : enveloppe stable `{"error": {"code": "...", "message": "...", "details": {...}}}` ; codes machine stables.
- Dates : ISO-8601 UTC. Montants : entiers XAF, champ suffixé `_xaf`.
- Idempotence checkout : header `Idempotency-Key` (uuid) obligatoire.
- Rate limits : login 10/min/IP ; register 5/h/IP ; checkout 20/h/user ; webhooks : hors session (signature only).

## 2. Auth / compte (`/auth/`)

| Méthode | Route | Accès | Description |
|---|---|---|---|
| POST | `/auth/register/` | public | création compte + acceptation CGU (`accepted_terms_version` requis) |
| POST | `/auth/login/` | public | email+password → session cookie |
| POST | `/auth/logout/` | connecté | |
| GET | `/auth/me/` | connecté | profil + rôles + flags artiste |
| POST | `/auth/password/reset/` | public | email jeton |
| POST | `/auth/password/reset/confirm/` | public | |
| POST | `/auth/password/change/` | connecté | |
| GET/PATCH | `/auth/profile/` | connecté | |
| GET/POST | `/auth/addresses/` | connecté | |
| PATCH/DELETE | `/auth/addresses/{id}/` | connecté owner | |
| GET | `/auth/csrf/` | public | renvoie token initial (double submit) |

## 3. Catalogue public

| Méthode | Route | Accès | Description |
|---|---|---|---|
| GET | `/catalog/artworks/` | public | filtres `q, category, price_min, price_max, available, artist, sort, page` — **uniquement PUBLISHED** |
| GET | `/catalog/artworks/{slug}/` | public | fiche (404 si non publiée) |
| GET | `/catalog/artworks/{slug}/similar/` | public | même catégorie, hors self, max 6 |
| GET | `/catalog/artworks/{slug}/media/{mid}/{variant}/` | public* | `stream` (original), `thumb` (PNG 480px), `poster` (PNG); *si l'œuvre est PUBLISHED, sinon owner/MOD/ADMIN — 404 sinon |
| GET | `/catalog/categories/` | public | arborescence |
| GET | `/catalog/artists/` | public | artistes APPROVED (page publique) |
| GET | `/catalog/artists/{slug}/` | public | profil + œuvres publiées |
| GET | `/videos/feed/` | public | fil vidéo (médias VIDEO d'œuvres PUBLISHED) |
| POST | `/catalog/artworks/{id}/favorite/` | connecté | toggle |
| GET | `/catalog/favorites/` | connecté | |
| POST | `/catalog/reviews/` | connecté | seulement si a commandé ; 1/œuvre |
| GET | `/catalog/reviews?artwork=` | public | visibles |

## 4. Candidature artiste

| Méthode | Route | Accès | Description |
|---|---|---|---|
| GET | `/artists/application/me/` | connecté | ma candidature (404 si aucune) |
| POST | `/artists/application/` | connecté | création DRAFT |
| PATCH | `/artists/application/` | owner DRAFT/NEEDS_INFO | mise à jour champs |
| POST | `/artists/application/submit/` | owner | DRAFT/NEEDS_INFO → PENDING_REVIEW |
| POST | `/artists/application/documents/` | owner | upload doc (multipart) |
| DELETE | `/artists/application/documents/{id}/` | owner | |
| GET | `/admin/applications/` | MODERATOR/ADMIN | filtres statut |
| POST | `/admin/applications/{id}/approve/` | ADMIN | → APPROVED + rôle ARTIST + audit |
| POST | `/admin/applications/{id}/reject/` | ADMIN | motif requis |
| POST | `/admin/applications/{id}/request-info/` | MODERATOR+ | message |
| GET | `/admin/applications/{id}/documents/{doc}/` | ADMIN/MOD | **flux privé** (Content-Disposition, no-store) |

## 5. Espace artiste (`/artist/`)

| Méthode | Route | Accès | Description |
|---|---|---|---|
| GET | `/artist/dashboard/` | ARTIST | stats (ventes, dues, commandes ouvertes) |
| GET/POST | `/artist/artworks/` | ARTIST | liste les siennes / créer (brouillon) |
| GET/PATCH/DELETE | `/artist/artworks/{id}/` | owner | delete = ARCHIVED |
| POST | `/artist/artworks/{id}/media/` | owner | upload image/vidéo |
| DELETE | `/artist/artworks/{id}/media/{mid}/` | owner | |
| POST | `/artist/artworks/{id}/publish/` | owner | DRAFT → IN_MODERATION (garde APPROVED requis) |
| POST | `/artist/artworks/{id}/unpublish/` | owner | PUBLISHED → HIDDEN |
| GET | `/artist/orders/` | ARTIST | commandes contenant ses lignes |
| GET | `/artist/orders/{id}/` | ARTIST | scope lignes vendeur |
| POST | `/artist/shipments/` | ARTIST | création depuis lignes payées |
| PATCH | `/artist/shipments/{id}/` | owner | tracking, status → SHIPPED |
| POST | `/artist/shipments/{id}/deliver/` | owner | → DELIVERED (preuve note) |
| GET | `/artist/earnings/` | ARTIST | ledger somme + payouts |
| GET | `/artist/payouts/` | ARTIST | historique |

## 6. Commerce acheteur

| Méthode | Route | Accès | Description |
|---|---|---|---|
| GET | `/cart/` | connecté | panier courant (prix recalculés affichés) |
| POST | `/cart/items/` | connecté | `{artwork_id, quantity}` |
| PATCH/DELETE | `/cart/items/{id}/` | owner | |
| POST | `/checkout/quote/` | connecté | simulation totaux (server-side) |
| POST | `/checkout/` | connecté | `Idempotency-Key` ; crée order+payment+reservation; renvoie `{order_reference, payment: {provider, redirect_info}}` |
| GET | `/orders/` | connecté | mes commandes |
| GET | `/orders/{ref}/` | buyer owner | instantané + shipments + litiges |
| POST | `/orders/{ref}/cancel/` | buyer | si PENDING_PAYMENT |
| GET | `/orders/{ref}/shipments/` | buyer | suivi |
| POST | `/orders/{ref}/disputes/` | buyer | ouvrir litige |
| POST | `/disputes/{id}/evidence/` | partie | upload preuve |
| POST | `/disputes/{id}/response/` | artiste/admin | |
| GET | `/disputes/` | selon rôle | scoppé |
| POST | `/orders/{ref}/refunds/` | buyer | demande remboursement |

## 7. Paiements (webhooks + consultation)

| Méthode | Route | Accès | Description |
|---|---|---|---|
| POST | `/payments/webhooks/campay/` | **signature only** | corps brut ; HMAC vérifié ; 200 rapide ; idempotent |
| GET | `/payments/{uuid}/status/` | buyer owner | statut pour polling UI |
| POST | `/admin/payments/{id}/simulate/` | ADMIN (env démo uniquement) | sandbox hooks |

## 8. Administration

| Méthode | Route | Accès | Description |
|---|---|---|---|
| GET | `/admin/users/` | ADMIN | recherche, rôles |
| POST | `/admin/users/{id}/roles/` | ADMIN | grant/revoke + audit |
| GET | `/admin/artworks/` | MOD/ADMIN | tous statuts |
| POST | `/admin/artworks/{id}/moderate/` | MOD/ADMIN | approve/refuse/hide + motif |
| GET | `/admin/orders/` | ADMIN/FINANCE | |
| GET | `/admin/payments/` | ADMIN/FINANCE | |
| GET | `/admin/refunds/` | ADMIN/FINANCE | |
| POST | `/admin/refunds/{id}/decide/` | ADMIN/FINANCE | approve/reject |
| POST | `/admin/refunds/{id}/confirm-execution/` | FINANCE | preuve manuelle CamPay |
| GET | `/admin/ledger/` | FINANCE/ADMIN | filtres artist/order |
| POST | `/admin/payouts/` | FINANCE | batch création |
| GET | `/admin/disputes/` | MOD/ADMIN/FINANCE | |
| POST | `/admin/disputes/{id}/resolve/` | MOD/ADMIN | décision + motif |
| GET | `/admin/reports/` | MOD+ | signalements |
| GET | `/admin/audit/` | ADMIN | filtres |
| GET/PATCH | `/admin/settings/` | ADMIN | plateforme (commission, TTL…) |
| GET/POST | `/admin/categories/` | ADMIN | CRUD |

## 9. Légal

| Méthode | Route | Accès | Description |
|---|---|---|---|
| GET | `/legal/policies/` | public | liste |
| GET | `/legal/policies/{slug}/?lang=` | public | version publiée courante |
| POST | `/legal/acceptances/` | connecté | enregistre acceptation version |
| GET | `/legal/acceptances/mine/` | connecté | |
| GET/PATCH | `/legal/cookie-preferences/` | connecté/anon | |

## 10. Notifications

| Méthode | Route | Accès |
|---|---|---|
| GET | `/notifications/` | connecté (page + unread) |
| POST | `/notifications/{id}/read/` | owner |

## 11. Codes d'erreur standard

| code | HTTP | usage |
|---|---|---|
| `validation_error` | 400 | champs DRF (`details` = map) |
| `unauthenticated` | 401 | session absente |
| `permission_denied` | 403 | périmètre OK, action non |
| `not_found` | 404 | hors périmètre ou inexistant |
| `conflict` | 409 | transition illégale, stock, doublon |
| `idempotency_conflict` | 409 | même clé, corps différent |
| `rate_limited` | 429 | throttle |
| `provider_error` | 502/503 | CamPay KO |
| `moderation_required` | 403 | publication bloquée |
