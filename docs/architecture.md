# ArtFlow — Architecture

> Phase A. Décisions tracées dans `docs/decisions/`.

## 1. Vue d'ensemble

```
┌────────────────────────────────────────────────────────────┐
│  Navigateur (acheteur / artiste / admin)                   │
│  Next.js 16 (App Router) — SSR catalogue, SPA espace      │
│  membre ; Tailwind 4 + tokens DESIGN.md (ambre)            │
└──────────────┬─────────────────────────────▲───────────────┘
               │ HTTPS (mêmes origines via  │ cookies de session
               │ reverse proxy en prod)     │ httpOnly + CSRF
┌──────────────▼─────────────────────────────┴───────────────┐
│  API Django 6.1 + DRF 3.18 (Python 3.14, uv)               │
│  - auth sessions · permissions par vue · validation serveur│
│  - OpenAPI (drf-spectacular) · audit append-only           │
│  - adaptateur Paiement (CamPay | Mock signé)               │
│  - outbox notifications + commandes cron (pas Celery MVP)  │
└──────┬──────────────┬──────────────┬───────────────────────┘
       │              │              │
┌──────▼─────┐ ┌──────▼──────┐ ┌─────▼──────────────────────┐
│ PostgreSQL │ │ Stockage    │ │ Services externes          │
│ 18 (Docker │ │ privé       │ │ - CamPay (paiement MoMo)   │
│ artflow-   │ │ médias +    │ │ - SMTP (e-mails txn)       │
│ postgres)  │ │ documents   │ │ - Vidéo managée (Phase D+) │
└────────────┘ │ (S3 ou disq)│ │ - CDN images (optionnel)   │
               └─────────────┘ └────────────────────────────┘
```

## 2. Stack retenue (validée Phase A)

| Couche | Choix | Version cible | Justification |
|---|---|---|---|
| Frontend | Next.js (App Router) + React + TypeScript | 16.4.x / 19.3.x | SSR catalogue (SEO fiches), cible Vercel/Node |
| UI | Tailwind CSS + composants accessibles typés (Radix-style) + tokens `DESIGN.md` | 4.x | Cohérence ambre/glass + WCAG |
| Formulaires | Validation client + **serveur** (serializer DRF) | — | Double barrière |
| Data client | TanStack Query (ou équivalent léger) | — | Cache, états loading/erreur |
| Backend | Django + DRF + drf-spectacular | 6.1 / 3.18 | Éprouvé (référentiel STAR), OpenAPI auto |
| Auth | **Sessions cookie `httpOnly` + CSRF** (ADR-0002) | — | Site marchand même-origine ; CSRF par token |
| DB | PostgreSQL | 18 (conteneur `artflow-postgres`, ADR-0003) | Transactions, contraintes, `SELECT FOR UPDATE` |
| Async | **Outbox DB + cron** (management commands) — pas de Celery au MVP (ADR-0005) | — | Expiration réservations, e-mails différés, rappels |
| Médias | Upload contrôlé → stockage privé → miniatures ; vidéos via service managé (docs/media.md) | — | Jamais de fichier utilisateur en public brut |
| CI | GitHub Actions | — | Tests, lint, types, migrations, build |
| Prod (cible) | Front Vercel-compatible ; API sur hébergeur Python (Railway/Render/VPS) ; Postgres managé ; SMTP transactionnel | — | Choix hébergeur = décision ultérieure (budget) |

## 3. Monorepo

```
artflow/
├── frontend/            # Next.js (app/)
│   ├── app/             # routes (RSC + client components)
│   ├── components/      # UI générique + features
│   ├── lib/             # api client typé, utils, i18n
│   └── e2e/             # Playwright
├── backend/
│   ├── config/          # settings, urls, wsgi/asgi
│   ├── apps/
│   │   ├── core/        # utils, permissions de base, audit
│   │   ├── accounts/    # users, sessions, adresses, CGU
│   │   ├── artists/     # candidatures, profils, vérification
│   │   ├── catalog/     # catégories, œuvres, médias, favoris, avis
│   │   ├── commerce/    # panier, commandes, stock, expéditions
│   │   ├── payments/    # tentatives, webhooks, refunds, ledger, payouts
│   │   ├── disputes/    # litiges + preuves
│   │   ├── legal/       # politiques versionnées + acceptations
│   │   └── notifications/ # outbox + préférences
│   ├── media/           # (gitignoré) stockage privé dev
│   └── pyproject.toml   # uv
├── docs/                # cette documentation
├── infrastructure/      # docker-compose, configs reverse-proxy
└── .github/workflows/   # CI
```

Règles : front et back **responsabilités séparées** ; zéro logique métier dupliquée côté navigateur ; pas d'abstraction prématurée (1 adaptateur paiement = 2 implémentations max : mock + CamPay).

## 4. Modèles de responsabilités (backend)

### 4.1 Authentification et sessions
- `django.contrib.auth` + sessions serveur ; cookie `sessionid` `HttpOnly` + `SameSite=Lax` (+ `Secure` en prod) ; CSRF via cookie `csrftoken` + header (standard Django, front le relaie).
- Front : `credentials: 'include'` + en-tête CSRF sur mutations.
- Réinitialisation mot de passe : e-mail à jeton à usage unique (outbox → SMTP).
- E-mail vérification : option activable (`ACCOUNT_EMAIL_VERIFICATION = optional|required`, défaut développement = optionnel pour la démo).

### 4.2 Autorisations
- DRF : permissions custom par vue (ex. `IsArtistOwnerOrReadOnly`, `IsAdminOrFinanceReadOnly`).
- QuerySets **scoppés par rôle** (artistes ne voient que leurs œuvres ; acheteurs leurs commandes).
- Tout accès refusé sensible = **404** si l'objet n'est pas dans le périmètre du rôle (pas de fuite d'existence), **403** si périmètre OK mais action interdite.
- Chaque action sensible écrit dans `audit_logs`.

### 4.3 Paiement (adaptateur)
```python
class PaymentGateway(Protocol):
    def initiate(self, amount_xaf: int, phone: str, operator: str,
                 external_reference: str, description: str) -> InitiateResult: ...
    def get_status(self, reference: str) -> StatusResult: ...
    def verify_webhook(self, headers, body: bytes) -> WebhookEvent: ...  # lève si invalide
```
- Implémentations : `MockPaymentGateway` (sandbox signée, dev/tests) puis `CamPayGateway` (Phase D, après création de compte validée).
- **Aucune confirmation de commande sans** statut `SUCCESSFUL` vérifié (webhook signé **ou** interrogation serveur du statut).

### 4.4 Stock et concurrence
- `artworks.stock_quantity` (≥ 0, CHECK) ; ventes uniques = quantité 1 par défaut.
- Checkout : transaction + `SELECT ... FOR UPDATE` sur lignes d'œuvre → création `stock_reservations` (TTL 30 min, configurable) → décrément effectif à la conversion paiement réussi.
- Cron `expire_stock_reservations` toutes les 5 min : libère les réservations expirées.
- Idempotence : `orders.idempotency_key` (acheteur fournit ou serveur génère) + unicité contrainte.

### 4.5 Commission et ledger
- `commission_rate_bps = 1000` (10 %) **figé dans `order_items.commission_rate_bps`** à l'achat.
- `commission_xaf = floor(price_xaf * rate / 10000)` (arrondi **inférieur**, documenté, testé — favorise l'artiste d'un centime max).
- `commission_ledger` : écritures append-only (`order_item`, `order`, `type` ∈ {charge, refund_adjustment}, montants).
- `payouts` : accumulés par artiste ; exécution via **Mass Payout CamPay** (manuel/semi-auto au MVP, ADR-0004) — jamais de promesse d'auto-liquidation.

### 4.6 Notifications
- `notification_outbox` (table) : events métier → lignes ; cron d'envoi e-mail + affichage in-app ; statuts `pending|sent|failed` + retry borné.
- In-app : centre de notifications par utilisateur.

### 4.7 Audit
- `audit_logs` append-only : `actor`, `action`, `object_type`, `object_id`, `metadata` JSON, `ip`, `created_at`. Aucune modification/suppression.

## 5. Flux essentiels

### 5.1 Achat (resume)
1. Panier → `POST /checkout/quote/` → backend recalcule (prix serveur, dispo, livraison par vendeur, total).
2. `POST /checkout/` (Idempotency-Key) → commande `PENDING_PAYMENT` + réservations stock (transaction) + `payment_attempt` via adaptateur.
3. Acheteur redirigé/confirmé sur CamPay ( USSD push MoMo ).
4. Webhook CamPay (ou polling serveur de secours) → vérif signature/référence → `payment_events` (append) → si `SUCCESSFUL` : commande `PAID`, réservations converties, ledger écrit ; si `FAILED/EXPIRED` : libération stock, commande `CANCELLED` ou nouvelle tentative selon politique.
5. Rejeu webhook = même résultat, **zéro double écriture** (contrainte `event_id` unique).

### 5.2 Multi-vendeurs
- 1 commande gère N lignes avec N artistes → N `shipments` (1 par vendeur), chacun avec ses étapes et son statut indépendant.
- Commande livrée = tous les shipments `DELIVERED`.

### 5.3 Litige
- Acheteur ouvre dispute sur commande payée → preuves (privées) → notification artiste → réponse → examen modérateur/admin → décision → si faveur acheteur : création `refund` **à exécuter côté CamPay** (dashboard/mode disponible) + enregistrement preuve + ledger `refund_adjustment`. Aucun remboursement auto-piloté par le front.

## 6.-i18n
- Backend : `LANGUAGES = [('fr', 'Français'), ('en', 'English')]`, défaut `fr` ; traductions dans les modèles (champs `*_fr/_en` ou table de traduction pour contenus politiques).
- Front : dictionnaires de traduction, switch langue futur ; toute string UI dans le système de traduction dès le départ.

## 7. Environnements

| Env | But |
|---|---|
| dev local | Docker Postgres, MockPaymentGateway, e-mails console, données démo `seed_demo` |
| CI | Postgres service GitHub Actions, migrations + tests, pas de secrets |
| staging | CamPay sandbox, SMTP réel test, stockage objet (type S3) |
| prod | CamPay live, backups, monitoring, HTTPS strict |

Variables d'environnement : listées dans `docs/deployment.md` + `.env.example` (Phase B). **Aucun secret en dur.**

## 8. Points ouverts documentés
- Hébergeur prod exact (budget) — décision avant Phase G.
- Fournisseur vidéo managé (comparatif docs/media.md) — décision avant Phase D/E, compte payant = validation.
- Vérification e-mail obligatoire ou non en prod — validation avant lancement.
- Seuil de ré-moderation sur modification d'œuvre — paramètre admin, défaut : prix +20 % ou changement titre → re-modération.
