# Phase D2 — Commandes multi-vendeur — Plan d'implémentation

> **Pour les travailleurs agences :** exécuter task par task, syntaxe checkbox. TDD : test d'abord, le voir échouer, implémenter au minimum, revoir vert, commiter.

**Goal :** devis serveur (`/checkout/quote/`), checkout idempotent multi-vendeur (`POST /checkout/` + header `Idempotency-Key`) qui réserve le stock (TTL), fige les instantanés de commande (prix, commission, adresse) ; historique/détail/annulation de commandes ; commission ledger (modèle + `mark_paid` idempotent prêt pour le webhook D3) ; commandes expire réservations (cron) ; UI `/checkout` + `/commandes`.

**Découpage validé (2026-10-28) :** **D2 strict** — le checkout crée la commande `PENDING_PAYMENT` + réservations + `Payment(provider=MOCK, status=CREATED)` **sans initier de paiement** ; le `MockPaymentGateway` signé (→ `PAID`, ledger réel) arrive en **D3**. Adresse de livraison : **adresses existantes + mini-formulaire intégré au checkout** (API `/auth/addresses/` déjà en place).

**Architecture :** étend l'app `apps/commerce` (D1 = panier). Nouveaux modèles `Order`, `OrderItem`, `StockReservation`, `Payment`, `CommissionLedger` (champs exacts `docs/database.md` §3). `OrderService` dans `services.py` : transaction + `select_for_update` sur les artworks (triés par pk anti-deadlock), révalidation stock **libre = `stock_quantity` − Σ réservations `ACTIVE`**, réservations `expires_at = now + PlatformSettings.reservation_ttl_minutes`. Livraison : frais par **vendeur distinct** (`ArtistProfile.shipping_base_fee_xaf`), figés dans le total. Commission : `floor(unit × qty × bps / 10000)`, taux **figé** à la création depuis `PlatformSettings` (ADR-0006).

**Tech Stack :** Django 6.1 + DRF (cookies session + CSRF), Next 16 / React 19 / Tailwind 4 (design Clay), `formatXAF`/`apiFetch` existants.

**Spec :** `docs/api.md` §6 (routes), §1 (Idempotency-Key, throttle checkout 20/h), §11 (codes `conflict` / `idempotency_conflict`) ; `docs/database.md` §3 (orders, order_items, stock_reservations, payments, commission_ledger) ; `docs/payments.md` §2–3 ; `docs/requirements.md` EF-8/EF-9.1, critère **E** ligne §5.

## Contraintes globales (reprises de D1)

- XAF **entiers** (BigInteger) ; prix panier jamais stocké — **relu au quote et au checkout**.
- Cookies HttpOnly + CSRF double submit ; appels frontend **sans slash final**.
- Réponses succès plates ; erreurs enveloppe `{"error": {"code","message","details"}}` ; codes : `validation_error` 400, `conflict` 409, `idempotency_conflict` 409, `rate_limited` 429.
- Anonyme sur toutes les routes → **401**.
- TDD ; gates : `uv run pytest`, `uv run ruff check .`, `uv run python manage.py makemigrations --check` ; `npx oxlint src`, `npx vitest run`, `npx tsc --noEmit`, `npm run build`.
- FR partout dans l'UI.

## Review Focus (les pièges qui mordent)

1. **Idempotence checkout** : clé absente → 400 (`details.idempotency_key`) ; replay même buyer + même corps → **200** avec la même commande (aucune 2ᵉ réservation) ; même clé + corps différent → **409 `idempotency_conflict`** ; clé appartenant à un autre buyer → 409 `idempotency_conflict` (clé unique globale). Comparaison de corps = `request_fingerprint` = sha256 du JSON canonique (clés triées) — **colonne ajoutée à `orders`** (écart noté à `docs/database.md` §3, ligne mise à jour dans la Task 1).
2. **Concurrence stock** : 2 threads checkout, stock 2, qty 2 chacun → exactement **1×201 + 1×400**, `stock_quantity ≥ 0` toujours (verrou `FOR UPDATE` + réservations `ACTIVE` comptées, y compris expirées mais non encore purgées — conservateur, le cron tourne toutes les 5 min). Test `TransactionTestCase` + threads.
3. **Multi-vendeur** : 2 œuvres d'artistes différents → 2 lignes de frais de livraison distinctes ; 2 œuvres du **même** artiste → **1 seul** frais ; commission `floor()` par ligne (999 XAF → 99) ; le taux changé dans `PlatformSettings` **après** commande ne modifie rien (figé).
4. **Panier vieilli** : entre panier et checkout l'œuvre peut baisser de stock ou sortir du catalogue → 400 `validation_error` avec détail **par œuvre**, jamais un 500 ; panier vide au checkout → 400.
5. **Annulation** : seul le buyer owner (sinon 404) et seul statut `PENDING_PAYMENT` (sinon 409 `conflict`) ; réservations → `RELEASED`, `Payment` → `CANCELLED` ; le panier n'est **pas** restauré (choix documenté — l'acheteur ré-ajoute).
6. **`mark_paid` idempotent** (base de D3) : double appel → stock décrémenté **1 fois**, **1** ligne `CHARGE` par `order_item` (unique `(order_item, kind)`), réservations `CONVERTED`.

---

### Task 1 : modèles commande / réservation / paiement / ledger + migration

**Files :**
- Modify : `backend/apps/commerce/models.py`, `backend/config/settings.py` si besoin, `docs/database.md` (ligne `request_fingerprint`)
- Create : `backend/apps/commerce/migrations/0002_*.py`, `backend/apps/commerce/tests/test_models_order.py`

**Interfaces :**
- Produits : classes `Order`, `OrderItem`, `StockReservation`, `Payment`, `CommissionLedger` + `Order.Status`/`Payment.Status`/`StockReservation.Status` (choices) — consommées par les Tasks 2–6.

- [ ] **Step 1 : tests modèles (échouent : AttributeError)**

`tests/test_models_order.py` :
- `test_order_reference_unique` : 2 Order même `reference` → IntegrityError.
- `test_order_idempotency_key_unique` : 2 Order même `idempotency_key` → IntegrityError.
- `test_order_item_quantity_positive` : `OrderItem(quantity=0)` → IntegrityError (CheckConstraint).
- `test_order_item_commission_frozen_fields` : création avec `commission_xaf=1234`, `artist_net` cohérent, valeurs stockées telles quelles.
- `test_ledger_unique_charge_per_order_item` : 2 `CHARGE` même `order_item` → IntegrityError ; `CHARGE` + `REFUND_ADJUSTMENT` OK.
- `test_reservation_default_active` : statut par défaut `ACTIVE`.
- `test_payment_external_reference_unique`.

- [ ] **Step 2 : vérifier l'échec** → `uv run pytest apps/commerce/tests/test_models_order.py -v` → ImportError/AttributeError.

- [ ] **Step 3 : implémenter les modèles + migration**

Champs exacts `docs/database.md` §3 (ordre du fichier : Cart/CartItem existants puis) :
- `Order` : `reference` (varchar 20, unique), `buyer` FK settings.AUTH_USER_MODEL PROTECT, `status` (8 choices, défaut `PENDING_PAYMENT`), `subtotal_items_xaf`, `shipping_total_xaf`, `fees_total_xaf` (0), `grand_total_xaf`, `currency` (default `XAF`), `shipping_address_snapshot` JSONField, `buyer_note` (blank), `idempotency_key` (varchar 64, unique), **`request_fingerprint` (varchar 64, db_index)**, `placed_at` (default now), `paid_at`/`cancelled_at` nullables. Index `(buyer, -placed_at)`, `(status)`.
- `OrderItem` : `order` CASCADE related_name `items`, `artwork` PROTECT, `artist` FK `artists.ArtistProfile` PROTECT, `title_snapshot` (200), `unit_price_xaf`, `quantity` (Check ≥1), `line_total_xaf`, `commission_rate_bps`, `commission_xaf`, `artist_net_xaf` ; unique `(order, artwork)`.
- `StockReservation` : `artwork` PROTECT, `order` CASCADE related_name `reservations`, `quantity`, `status` (12 chars, défaut `ACTIVE`), `expires_at`, `created_at`, `released_at` null ; index `(status, expires_at)`.
- `Payment` : `order` PROTECT related_name `payments`, `provider` (10 chars choices `MOCK`/`CAMPAY`, défaut `MOCK`), `provider_reference` null + `UniqueConstraint` partiel non nul, `external_reference` unique, `amount_xaf`, `status` (12 chars, défaut `CREATED`), `operator`, `phone`, `failure_reason`, `initiated_at`, `confirmed_at`, `raw_last_status` JSON null.
- `CommissionLedger` : `order_item` PROTECT, `order` PROTECT, `artist` PROTECT, `kind` (20 chars `CHARGE`/`REFUND_ADJUSTMENT`), `gross_xaf`/`commission_xaf`/`artist_net_xaf` (BigInteger, signés), `commission_rate_bps`, `created_at` ; unique `(order_item, kind)`.

+ `makemigrations commerce` ; doc `docs/database.md` : ajouter la colonne `request_fingerprint | varchar(64) unique-index | sha256 corps checkout (idempotence)` à la table `orders`.

- [ ] **Step 4 : tests verts** → `uv run pytest apps/commerce/tests/test_models_order.py -v` ; suite complète.

- [ ] **Step 5 : Commit** `Phase D2: order models (Order, OrderItem, reservations, Payment, ledger) + migration`

---

### Task 2 : `POST /checkout/quote/` — simulation des totaux côté serveur

**Files :**
- Create : `backend/apps/commerce/services.py`, `backend/apps/commerce/tests/test_api_quote.py`
- Modify : `backend/apps/commerce/serializers.py`, `views.py`, `urls.py`

**Interfaces :**
- Produces (shape exact — consommé par Task 3 et le frontend Task 5) :
```json
{
  "items": [{
    "artwork_id": 3, "slug": "portrait-awa", "title": "Portrait d'Awa",
    "quantity": 2, "unit_price_xaf": 15000, "line_total_xaf": 30000,
    "artist": {"id": 7, "display_name": "Awa Ndiaye"},
    "commission_rate_bps": 1000, "commission_xaf": 3000, "artist_net_xaf": 27000,
    "primary_image_url": "/api/v1/catalog/artworks/…/thumb/"
  }],
  "shipping": [{"artist_id": 7, "display_name": "Awa Ndiaye", "shipping_fee_xaf": 2000}],
  "subtotal_items_xaf": 30000, "shipping_total_xaf": 2000, "fees_total_xaf": 0,
  "grand_total_xaf": 32000, "items_count": 2,
  "blocking_issues": []
}
```
`blocking_issues` : `{"artwork_id", "code": "stock_insufficient" | "artwork_unavailable", "message": FR, "quantity_demandee"}` — non vide ⇒ checkout refusé (400) ; affiché et bouton bloqué côté frontend.

- Consomme : panier D1 (`get_or_create_cart`), `PlatformSettings.get().commission_rate_bps`, `ArtistProfile.shipping_base_fee_xaf`.

- [ ] **Step 1 : tests API (échouent : 404 route)**

`tests/test_api_quote.py`, classe `TestCheckoutQuote` :
- `test_unauthenticated_401`.
- `test_empty_cart_returns_zeros` : 200, `items == []`, totaux à 0 (quote ne bloque pas sur vide).
- `test_multi_seller_totals` : 2 artistes (`seller_profile` + un second profil sur `other_user2`) → 2 entrées `shipping`, `grand_total = Σ lignes + Σ frais`.
- `test_one_shipping_fee_per_seller` : 2 œuvres du même artiste → **1** entrée `shipping`.
- `test_commission_floor` : prix 999 ×1 → `commission_xaf == 99`, `artist_net_xaf == 900`.
- `test_client_prices_ignored` : POST avec corps bidon `{"grand_total_xaf": 1, "items": [{"unit_price_xaf": 1}]}` → totaux identiques au quote sans corps (le corps est ignoré : prix toujours relus en base).
- `test_blocking_stock_issue` : ligne quantity 3, stock passé à 1 → `blocking_issues` contient `stock_insufficient`, `grand_total_xaf` reste calculé.
- `test_blocking_unavailable_issue` : œuvre passée HIDDEN → `artwork_unavailable`.

- [ ] **Step 2 : échec vérifié.**

- [ ] **Step 3 : implémenter**

- `services.py` :
  - `compute_quote(cart) -> dict` : charge lignes `select_related(artwork, artwork__artist)` + média primaire ; prix/stock/`PUBLISHED` **lus en base maintenant** ; commissions avec `bps = PlatformSettings.get().commission_rate_bps` ; frais livraison = 1× `shipping_base_fee_xaf` par artiste **distinct présent** (groupé, pas de doublon) ; `blocking_issues` par ligne.
  - `serialize_quote(...)` reste dans `serializers.py` (sérialiseur `CheckoutQuoteSerializer` ou dict propre — pas de boîte noire).
- `views.QuoteView(APIView)` `permission_classes=[IsAuthenticated]`, POST (body accepté puis **ignoré**), body vide OK.
- `urls.py` : `path("checkout/quote/", …)`.

- [ ] **Step 4 : verts** + suite complète.

- [ ] **Step 5 : Commit** `Phase D2: checkout quote with server-side totals and seller shipping groups`

---

### Task 3 : `POST /checkout/` — checkout idempotent + réservations stock

**Files :**
- Modify : `backend/apps/commerce/services.py`, `serializers.py`, `views.py`, `urls.py`, `backend/config/settings.py` (taux `checkout`)
- Create : `backend/apps/commerce/tests/test_api_checkout.py`, `backend/apps/commerce/tests/test_concurrency.py`

**Interfaces :**
- Produces : `POST /api/v1/checkout/` (headers `Idempotency-Key` requis) → **201** :
```json
{"order_reference": "ORD-2026-000123", "status": "PENDING_PAYMENT",
 "grand_total_xaf": 32000, "placed_at": "…",
 "payment": {"provider": "MOCK", "status": "CREATED", "redirect_info": null}}
```
Replay → **200** même payload. Body : `{"address_id": 5, "buyer_note": "…"}` (`buyer_note` optionnel).

- Consomme : `compute_quote` (Task 2), `Address` (account, `address_id` obligatoire, owner → sinon 404), throttle `checkout`.

- [ ] **Step 1 : tests (classe `TestCheckout`)**

- `test_unauthenticated_401`.
- `test_missing_idempotency_key_400` : sans header → 400 `validation_error`, `details.idempotency_key`.
- `test_checkout_creates_order` : 201, référence `^ORD-\d{4}-\d{6}$`, `Order` + `OrderItem` (commission figée) + `StockReservation(ACTIVE, expires_at ≈ now+30min)` + `Payment(MOCK, CREATED, amount == grand_total)`, **panier vidé**, `shipping_address_snapshot` = copie de l'adresse.
- `test_replay_returns_same_order` : 2e appel même clé + même corps → 200, `order_reference` identique, **1 seul Order** en base, 1 seule réservation.
- `test_same_key_different_body_409` : même clé, `buyer_note` différent → 409 code `idempotency_conflict`.
- `test_key_of_another_user_409` : clé d'un autre buyer → 409 `idempotency_conflict`.
- `test_foreign_address_404` / `test_missing_address_400` (details.address).
- `test_empty_cart_400`, `test_stale_stock_400` (stock chuté depuis le panier), `test_unpublished_artwork_400`.
- `test_commission_frozen_from_settings` : `PlatformSettings.commission_rate_bps` passé à 2000 **après** → `order_item.commission_rate_bps == 1000`.
- `test_throttle_checkout` : 21ᵉ appel → 429 `rate_limited` (autouse cache-clear isole le test).

- [ ] **Step 2 : échec vérifié.**

- [ ] **Step 3 : implémenter**

- `services.py` → `create_checkout(user, *, idempotency_key, address, buyer_note, fingerprint)` :
  1. Réponse de replay si `Order.objects.filter(idempotency_key=…)` : buyer + fingerprint OK → payload 200 ; sinon `IdempotencyConflict` (409) — sous-classer `APIException` avec attribut `artflow_code`, **étendre `apps/core/exceptions.py`** pour lire `getattr(exc, "artflow_code", …)` avant `_status_to_code` (sinon le code retombe sur `conflict`).
  2. `transaction.atomic()` : tri des artworks **par pk** puis `select_for_update()` ; par artwork : `libre = stock_quantity − Σ réservations ACTIVE` (toutes, même expirées) ; si `quantité > libre` → `ValidationError` 400 avec détail par `artwork_id` (messages FR comme D1).
  3. Créer `Order` (reference `ORD-YYYY-NNNNNN` : 6 chiffres aléatoires zéro-paddés, boucle ≤20 sur IntegrityError), `OrderItem`s (prix relu + commission figée), `StockReservation`s (`expires_at = now + ttl`), `Payment(provider="MOCK", status="CREATED", external_reference=uuid4, amount_xaf=grand_total)`, snapshot adresse complet, vider le panier, renvoyer le payload.
- `views.CheckoutView` : `permission_classes=[IsAuthenticated]`, `throttle_classes=[ScopedRateThrottle]`, `throttle_scope="checkout"` ; header `HTTP_IDEMPOTENCY_KEY` (strip, max 64) ; `fingerprint = sha256(json corps canonique)`.
- `settings.py` : `"checkout": "20/h"` dans `DEFAULT_THROTTLE_RATES`.

- [ ] **Step 4 : tests verts — concurrence** :
`test_concurrency.py` (pytest `@pytest.mark.django_db(transaction=True)` ou `TransactionTestCase`) : stock 2, deux threads/users, chacun qty 2 → 1×201 + 1×400, `Σ réservations ACTIVE ≤ 2`, `artwork.stock_quantity ≥ 0`.

- [ ] **Step 5 : gates backend** (pytest complet, ruff, `makemigrations --check`) ; Commit `Phase D2: idempotent checkout with stock reservations`

---

### Task 4 : `/orders/` (liste, détail, annulation) + `mark_paid` + cron d'expiration

**Files :**
- Modify : `backend/apps/commerce/services.py`, `views.py`, `urls.py`
- Create : `backend/apps/commerce/management/__init__.py`, `management/commands/__init__.py`, `management/commands/expire_stock_reservations.py`, `backend/apps/commerce/tests/test_api_orders.py`, `tests/test_services_order.py`, `tests/test_expire_reservations.py`

**Interfaces :**
- Produces :
  - `GET /orders/` (paginé DRF) → `{count, next, previous, results: [{reference, status, placed_at, paid_at, subtotal_items_xaf, shipping_total_xaf, grand_total_xaf, items_count}]}`
  - `GET /orders/{reference}/` → entête + `items` (instantanés `title_snapshot`, `unit_price_xaf`, `quantity`, `commission_*`, artiste, thumb) + `shipping` + `shipping_address_snapshot` + `payment: {provider, status}` + `shipments: []` + `disputes: []` (remplis en D4)
  - `POST /orders/{reference}/cancel/` → 200 détail (statut `CANCELLED`)
  - `OrderService.mark_paid(order)` → idempotent (stock décrémenté, réservations `CONVERTED`, ledger `CHARGE`, statut `PAID`) — **appelé en D3 par le webhook**, testé ici.
  - Commande `manage.py expire_stock_reservations` : ordres `PENDING_PAYMENT` ayant une réservation `ACTIVE` expirée → toutes ses réservations `EXPIRED`/`RELEASED` + order `CANCELLED` + payment `CREATED/PENDING` → `CANCELLED` (lignes `released_at = now`).

- [ ] **Step 1 : tests (échouent : 404)**

`test_api_orders.py` (classes `TestOrderList`, `TestOrderDetail`, `TestOrderCancel`) :
- `test_list_scoped_to_buyer` : commandes d'`other_user` absentes ; forme + `items_count`.
- `test_detail_owner_404` : référence d'un autre buyer → 404 ; inexistante → 404.
- `test_detail_shape` : instantanés figés (prix modifié en base après → détail affiche le prix **figé**), `payment`, `shipments == []`.
- `test_cancel_pending` : 200 `CANCELLED`, réservations `RELEASED`, payment `CANCELLED`.
- `test_cancel_paid_409` (après `mark_paid`) → code `conflict`.
- `test_cancel_other_order_404`.
- `test_unauthenticated_401` (chaque route).

`test_services_order.py` (`TestMarkPaid`) :
- `test_mark_paid_happy_path` : statut `PAID`, `paid_at`, stock décrémenté, réservations `CONVERTED`, 1 ledger `CHARGE` par item avec valeurs figées.
- `test_mark_paid_idempotent` : appel ×2 → **1** ledger par item, stock décrémenté une seule fois.
- `test_mark_paid_with_active_reservation_already_expired_in_db` : ne crée jamais de stock négatif (garde `F`/verification).

`test_expire_reservations.py` :
- `test_expire_cancels_unpaid_order` : réservation `expires_at` passé → commande `CANCELLED`, réservations libérées, payment `CANCELLED`.
- `test_expire_ignores_paid_order` : order `PAID` intouché.
- `test_expire_ignores_active_future` : rien ne change.

- [ ] **Step 2 : échec vérifié.**

- [ ] **Step 3 : implémenter** : `OrderListView(RetrieveAPIView…)` (pagination standard), `OrderDetailView` (lookup `reference` + `buyer=request.user` → 404), `OrderCancelView` (transition guard : seulement `PENDING_PAYMENT`, sinon 409 `Conflict` → utiliser `APIException` 409 ou `ValidationError`+`status` — via exception handler → code `conflict`), `mark_paid`, commande cron (tri par pk pour verrous).

- [ ] **Step 4 : verts** + suite complète.

- [ ] **Step 5 : Commit** `Phase D2: order history, detail, cancel + reservation expiry command`

---

### Task 5 : Frontend `/checkout` + `/commandes` + activation du panier

**Files :**
- Modify : `frontend/src/lib/api.ts` (types + fonctions), `frontend/src/app/panier/page.tsx` (bouton actif)
- Create : `frontend/src/app/checkout/page.tsx` (+ `page.test.tsx`), `frontend/src/app/commandes/page.tsx` (+ test), `frontend/src/app/commandes/[ref]/page.tsx` (+ test)

**Interfaces :**
- Consomme : shapes Tasks 2–4, `AddressSerializer` (`label, recipient_name, line1, line2, city, region, phone, is_default`), `apiFetch` (accepte déjà `headers` custom pour `Idempotency-Key`), `formatXAF`, composants Clay (`Button`, `EmptyState`, `.ink-*`).

- [ ] **Step 1 : tests composant (vitest, échouent)**

`checkout/page.test.tsx` :
- affiche le récap (lignes, frais livraison, total `formatXAF` — matcheur normalisé cf. piège D1).
- liste les adresses en radio ; **aucune adresse** → mini-form (7 champs dont `phone` format `+237…`) qui appelle `createAddress` puis se sélectionne.
- soumission → `checkout()` appelé avec **un** `Idempotency-Key` (uuid généré) et `address_id` ; redirection `/commandes/{reference}` (mock `useRouter.push`).
- 401 → `router.replace('/connexion?next=/checkout')` ; `blocking_issues` → liste d'alertes `.ink-warning` + bouton désactivé ; panier vide → lien `/panier`.

`commandes/page.test.tsx` : rend la liste (référence, statut FR, total, date), état vide.
`commandes/[ref]/page.test.tsx` : détail (instantanés, adresse, `payment`), bannière `PENDING_PAYMENT` « En attente de paiement — la simulation arrive à l'étape suivante », bouton « Annuler la commande » → `cancelOrder` appelé ; détail pagant → bouton masqué.

- [ ] **Step 2 : échec vérifié** → `npx vitest run`.

- [ ] **Step 3 : implémenter**

- `api.ts` : `interface Address` + `listAddresses()`, `createAddress(payload)` ; `Quote` (+ `quoteCheckout()` : POST `/checkout/quote` **sans slash**, corps `{}`) ; `CheckoutResult` + `checkout(payload, idempotencyKey)` (headers `{"Idempotency-Key": key}`) ; `OrderSummary`/`OrderDetail` + `listOrders()`, `getOrder(ref)`, `cancelOrder(ref)`.
- `checkout/page.tsx` (`"use client"`) : charge quote + adresses (401 → redirection connexion) ; radio adresses, mini-form repliable si vide ; `buyer_note` textarea ; bloc totaux ; bouton « **Confirmer la commande** » (pas « Payer » — paiement en D3) : `crypto.randomUUID()` → `checkout` → `router.push("/commandes/" + reference)` ; erreurs 400/409 en `.ink-danger` FR ; double-clic : état `submitting` (l'idempotence serveur est le filet de sécurité).
- `commandes/page.tsx` : liste paginée, badges statut (classes `.ink-*`), lien détail.
- `commandes/[ref]/page.tsx` : détail complet ; `PENDING_PAYMENT` → bannière + bouton Annuler (confirm local puis `cancelOrder`) ; `404` → `notFound()`.
- `panier/page.tsx` : bouton « Passer la commande » **activé** → `Link href="/checkout"` (supprimer le état désactivé « Bientôt disponible »).

- [ ] **Step 4 : gates frontend** → `npx oxlint src` 0, `npx vitest run` vert, `npx tsc --noEmit` 0, `npm run build` (routes `/checkout`, `/commandes`, `/commandes/[ref]`).

- [ ] **Step 5 : Commit** `Phase D2: checkout and order pages frontend`

---

### Task 6 : gates complets + smoke + rapport §27 + mémoire

- [ ] **Backend** : `uv run pytest` complet, `uv run ruff check .`, `uv run python manage.py makemigrations --check`.
- [ ] **Frontend** : `npx oxlint src`, `npx vitest run`, `npx tsc --noEmit`, `npm run build`.
- [ ] **Smoke HTTP** (`/tmp/opencode/smoke_d2.py`, même recette que D1, serveurs : API `8003`, web `5175`, Postgres `5435`, compte `d1buyer@artflow.test`) :
  1. ajouter 2 œuvres (1 multi-vendeur si possible) → `POST /checkout/quote/` → totaux + frais par vendeur ;
  2. `POST /checkout/` sans clé → 400 ; avec clé → 201 ; **replay même clé → 200 même référence** ; corps modifié → 409 `idempotency_conflict` ;
  3. `GET /orders/` + `GET /orders/{ref}/` → instantanés ; `POST …/cancel/` → 200 ; cancel ×2 → 409 ;
  4. `manage.py expire_stock_reservations` sur commande expirée → `CANCELLED` ;
  5. pages HTML : `/checkout`, `/commandes`, détail (200 + contenus clés) ; `/panier` → bouton « Passer la commande » actif.
- [ ] Rapport §27 Phase D2 présenté dans le chat.
- [ ] `MEMORY.md` mis à jour (D2 livrée, pièges, prochaine étape D3 MockPaymentGateway signé).
