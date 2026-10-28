# ArtFlow — Modèle de données

> Phase A. PostgreSQL 18. Convention : clés `BigAutoKey` internes ; références publiques codées (ex. `ORD-2026-000123`) ; montants **XAF en entiers** (`BigIntegerField`, jamais de décimale) ; horodatages `timestamptz` ; UUID pour webhooks/paiements externes.
> Suppression : **jamais de DELETE** sur données financières, audit, politiques, acceptations → `is_active` ou archivage. Les suppressions d'œuvres/devantures sont logiques (`ARCHIVED`/`deleted_at`).

## 1. Identité et profils

### users
| Champ | Type | Notes |
|---|---|---|
| id | BigAutoKey | PK |
| email | varchar(254) | **unique**, CI, index |
| password | varchar | Argon2id (django-argon2-password-formatter ou argon2-cffi via AUTH_PASSWORD_HASHERS) |
| first_name, last_name | varchar(100) | |
| phone | varchar(15) | unique partiel non nul ; format +237… (validation regex CM) |
| is_active | bool | désactivation = accès coupé, données conservées |
| is_staff, is_superuser | bool | admin Django (usage interne limité) |
| email_verified_at | timestamptz null | |
| last_login | timestamptz | |
| created_at, updated_at | timestamptz | |

### user_roles
| Champ | Type | Notes |
|---|---|---|
| id | BigAutoKey | |
| user | FK users, PROTECT | |
| role | varchar(20) | `BUYER`, `ARTIST`, `MODERATOR`, `ADMIN`, `FINANCE` (choix) |
| granted_by | FK users null | |
| created_at | timestamptz | |
| | **unique (user, role)** | rôles multiples possibles |

> Le rôle « candidat artiste » n'est pas un rôle : c'est l'état d'une `artist_profiles` (un BUYER peut déposer une candidature ; le rôle `ARTIST` est **granté à l'approbation**).

### artist_profiles
| Champ | Type | Notes |
|---|---|---|
| id | BigAutoKey | |
| user | OneToOne users, CASCADE | 1 profil par utilisateur |
| display_name | varchar(120) | nom public (peut différer du nom légal) |
| bio | text null | |
| city | varchar(80) | ex. Yaoundé |
| region | varchar(80) | |
| status | varchar(20) | `DRAFT`, `PENDING_REVIEW`, `NEEDS_INFO`, `APPROVED`, `REJECTED`, `SUSPENDED` |
| submitted_at, reviewed_at | timestamptz null | |
| reviewed_by | FK users null | admin/modérateur |
| rejection_reason / info_request | text null | |
| suspension_reason | text null | |
| shipping_base_fee_xaf | int ≥ 0 | frais d'expédition par défaut du vendeur |
| payout_method | varchar(20) | `MANUAL` (MVP) — réservé futur |
| created_at, updated_at | timestamptz | |

**Index** : `(status)`, `(user)`.

### artist_verification_documents
| Champ | Type | Notes |
|---|---|---|
| id | BigAutoKey | |
| artist_profile | FK, CASCADE | |
| kind | varchar(30) | `ID_CARD`, `PASSPORT`, `ART_PROOF`, `OTHER` |
| file | chemin stockage privé | **jamais d'URL publique** (`PrivateMediaStorage`) |
| original_filename | varchar(255) | affichage admin uniquement |
| content_type | varchar(100) | validé (magic bytes) |
| size_bytes | bigint | |
| uploaded_at | timestamptz | |
| uploaded_by | FK users | |

**Règles** : lecture = admin/modérateur autorisé (test 403/404) ; audit `verification_document.viewed` ; pas de listing dans les exports front.

### seller_payout_details
| Champ | Type | Notes |
|---|---|---|
| id | BigAutoKey | |
| artist_profile | OneToOne, CASCADE | |
| momo_phone | varchar(15) null | destination MoMo (MTN/Orange) |
| momo_operator | varchar(10) null | `MTN`/`ORANGE` |
| bank_name, bank_account_encrypted | varchar null | chiffré (Fernet) si renseigné — MVP : MoMo seul |
| verified_at | timestamptz null | revérification admin |
| created_at, updated_at | timestamptz | |

### addresses
| Champ | Type | Notes |
|---|---|---|
| id | BigAutoKey | |
| user | FK, CASCADE | |
| label | varchar(40) | ex. « Domicile » |
| recipient_name | varchar(120) | |
| line1, line2 | varchar(255) | |
| city | varchar(80) | |
| region | varchar(80) | |
| phone | varchar(15) | contact livraison |
| is_default | bool | |
| created_at, updated_at | | |
| | index `(user, is_default)` | |

## 2. Catalogue et médias

### categories
| Champ | Type | Notes |
|---|---|---|
| id | BigAutoKey | |
| slug | varchar(80) unique | URL stable |
| name_fr, name_en | varchar(120) | |
| description_fr, description_en | text null | |
| parent | FK self null | arborescence 2 niveaux max (validation) |
| is_active | bool | |
| position | int | ordre affichage |

### artworks
| Champ | Type | Notes |
|---|---|---|
| id | BigAutoKey | |
| reference | varchar(20) unique | ex. `ART-2026-00045` (généré) |
| artist | FK artist_profiles, PROTECT | propriétaire |
| title | varchar(200) | |
| slug | varchar(220) unique | auto depuis titre + PK |
| description | text | |
| category | FK categories, PROTECT | |
| price_xaf | bigint CHECK (price_xaf > 0) | |
| stock_quantity | int CHECK (>= 0) | défaut 1 (pièce unique) |
| status | varchar(20) | `DRAFT`, `IN_MODERATION`, `PUBLISHED`, `REFUSED`, `HIDDEN`, `ARCHIVED` |
| refusal_reason | text null | |
| moderation_note | text null | note interne |
| dimensions | varchar(120) null | ex. « 80 × 60 cm » |
| materials | varchar(255) null | |
| technique | varchar(120) null | |
| year_created | int null | |
| weight_kg | numeric(6,2) null | aide livraison |
| is_unique_piece | bool | défaut true si stock max 1 |
| published_at | timestamptz null | |
| created_at, updated_at | | |

**Index** : `(status, published_at DESC)`, `(artist, status)`, `(category, status)`, GIN trigram sur `title` + `description` (recherche PG `pg_trgm`), `(price_xaf)`.

### artwork_media
| Champ | Type | Notes |
|---|---|---|
| id | BigAutoKey | |
| artwork | FK, CASCADE | |
| kind | varchar(10) | `IMAGE`, `VIDEO` |
| source | varchar(20) | `UPLOAD`, `EXTERNAL_PROVIDER` |
| file | chemin privé (uploads) null | pour UPLOAD |
| provider | varchar(30) null | `CLOUDFLARE_STREAM`/`MUX`/… si managé |
| external_id | varchar(120) null | id chez le provider |
| playback_url | varchar(500) null | URL signée/générée par provider |
| poster_file | chemin null | miniature vidéo |
| thumbnail_file | chemin null | miniature image (générée Pillow) |
| position | int | ordre galerie |
| alt_text_fr, alt_text_en | varchar(255) | **obligatoire pour images** (validation) |
| width_px, height_px, size_bytes | int/bigint null | |
| content_type | varchar(100) | validé (magic bytes) |
| checksum_sha256 | char(64) | anti-doublon |
| is_primary | bool | couverture |
| created_at | | |
| | **unique (artwork, position)** | |

**Règles** : quotas (max 10 images + 1 vidéo/œuvre, tailles configurables) ; supprimer un média notifie le stockage (cleanup cron) ; vidéo ≠ œuvre sans FK vérifiée.

### artwork_reviews
| Champ | Type | Notes |
|---|---|---|
| id | | |
| artwork | FK, CASCADE | |
| author | FK users, CASCADE | acheteur ayant commandé (validation serveur) |
| rating | smallint 1–5 | |
| comment | text null | |
| is_visible | bool | modération |
| created_at | | |
| | **unique (artwork, author)** | 1 avis par acheteur/œuvre |

### favorites
`(user, artwork)` **unique**, `created_at`. Index `(user)`.

### content_reports
| Champ | Type | Notes |
|---|---|---|
| id | | |
| reporter | FK users | |
| target_type | varchar(20) | `ARTWORK`, `REVIEW`, `ARTIST` |
| target_id | bigint | (polymorphe léger, validé en service) |
| reason | varchar(30) | `COPYRIGHT`, `INAPPROPRIATE`, `FAKE`, `OTHER` |
| details | text | |
| status | varchar(20) | `OPEN`, `IN_REVIEW`, `RESOLVED`, `DISMISSED` |
| handled_by | FK users null | modérateur |
| resolution_note | text null | |
| created_at, resolved_at | | |

## 3. Commerce

### carts
| Champ | Type | Notes |
|---|---|---|
| id | | |
| user | OneToOne, CASCADE | **1 panier actif par user** |
| updated_at | | |

### cart_items
| Champ | Type | Notes |
|---|---|---|
| id | | |
| cart | FK, CASCADE | |
| artwork | FK, CASCADE | |
| quantity | int CHECK (> 0) | bornée au stock au moment de l'ajout (revalidé checkout) |
| created_at | | |
| | **unique (cart, artwork)** | |

> Pas de prix stocké dans le panier : toujours relu au quote/checkout.

### orders
| Champ | Type | Notes |
|---|---|---|
| id | | |
| reference | varchar(20) unique | `ORD-YYYY-NNNNNN` |
| buyer | FK users, PROTECT | |
| status | varchar(25) | `PENDING_PAYMENT`, `PAID`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`, `PARTIALLY_REFUNDED`, `REFUNDED` |
| subtotal_items_xaf | bigint | somme lignes |
| shipping_total_xaf | bigint | somme expéditions |
| fees_total_xaf | bigint | frais distincts éventuels (0 au MVP) |
| grand_total_xaf | bigint | |
| currency | char(3) | `XAF` |
| shipping_address_snapshot | JSON | copie complète au checkout |
| buyer_note | text null | |
| idempotency_key | varchar(64) unique | reçu du client ou généré |
| request_fingerprint | varchar(64) index | sha256 du corps checkout canonique (détection « clé réutilisée + corps différent » → 409 `idempotency_conflict`) |
| placed_at | timestamptz | |
| paid_at | timestamptz null | |
| cancelled_at | timestamptz null | |
| created_at, updated_at | | |

**Index** : `(buyer, placed_at DESC)`, `(status)`.

### order_items
| Champ | Type | Notes |
|---|---|---|
| id | | |
| order | FK, CASCADE | |
| artwork | FK, PROTECT | |
| artist | FK artist_profiles, PROTECT | snapshot du vendeur |
| title_snapshot | varchar(200) | |
| unit_price_xaf | bigint | **figé** |
| quantity | int | |
| line_total_xaf | bigint | unit × qty (vérifié serveur) |
| commission_rate_bps | int | **figé = 1000** (10 %) |
| commission_xaf | bigint | `floor(unit_price × qty × rate / 10000)` |
| artist_net_xaf | bigint | line_total − commission |
| created_at | | |

> Le taux courant de la plateforme vit dans `core.PlatformSettings.commission_rate_bps` ; il n'est **jamais** relu sur les anciennes lignes.

### stock_reservations
| Champ | Type | Notes |
|---|---|---|
| id | | |
| artwork | FK, PROTECT | |
| order | FK, CASCADE | |
| quantity | int | |
| status | varchar(12) | `ACTIVE`, `CONVERTED`, `RELEASED`, `EXPIRED` |
| expires_at | timestamptz | placed + TTL (30 min) |
| created_at, released_at | | |
| | index `(status, expires_at)` pour le cron | |

**Invariants** : `stock_quantity ≥ 0` (CHECK) + verrou ligne au checkout ; conversion = décrément stock + libération réservation dans la même transaction que le passage `PAID`.

### payments
| Champ | Type | Notes |
|---|---|---|
| id | | |
| order | FK, PROTECT | |
| provider | varchar(20) | `CAMPAY`, `MOCK` |
| provider_reference | varchar(120) null | uuid/refs CamPay |
| external_reference | varchar(64) | notre référence envoyée (idempotence côté provider) |
| amount_xaf | bigint | doit égaler `order.grand_total_xaf` (vérifié) |
| status | varchar(12) | `CREATED`, `PENDING`, `SUCCEEDED`, `FAILED`, `EXPIRED`, `CANCELLED` |
| operator | varchar(10) null | `MTN`/`ORANGE` |
| phone | varchar(15) null | |
| failure_reason | varchar(255) null | |
| initiated_at, confirmed_at | timestamptz | |
| raw_last_status | JSON null | derniers poll/webhook (redacté) |
| poll_count | int | tentatives du cron `poll_pending_payments` (max 20) |
| created_at, updated_at | | |

**Index** : `(order)`, `(provider, provider_reference) unique partiel non nul`.

> Le statut de remboursement **n'est pas** un statut de `payments` contradictoire : il vit dans `refunds` (1 paiement peut être remboursé partiellement plusieurs fois, somme bornée au montant encaissé).

### payment_events (append-only)
| Champ | Type | Notes |
|---|---|---|
| id | | |
| payment | FK, PROTECT | |
| event_id | varchar(120) **unique** | idempotence (webhook rejeué → ignoré) |
| kind | varchar(30) | `WEBHOOK_RECEIVED`, `STATUS_POLL`, `STATE_CHANGE` |
| status_after | varchar(12) | |
| signature_valid | bool | |
| payload | JSON | **redigé** (pas de secrets, pas de données carte — MoMo) |
| received_at | timestamptz | |

### refunds
| Champ | Type | Notes |
|---|---|---|
| id | | |
| order | FK, PROTECT | |
| payment | FK, PROTECT | |
| requested_by | FK users | acheteur (ou admin) |
| reason | varchar(30) | `DISPUTE`, `DAMAGED`, `NOT_RECEIVED`, `OTHER` |
| amount_xaf | bigint CHECK (> 0) | borné : Σ refunds ≤ montant encaissé |
| status | varchar(15) | `REQUESTED`, `APPROVED`, `REJECTED`, `PROCESSING`, `CONFIRMED`, `FAILED` |
| provider_refund_id | varchar(120) null | id CamPay si API ; sinon référence manuelle |
| execution_mode | varchar(15) | `API`, `MANUAL_DASHBOARD` (MVP : manuel avec preuve) |
| decided_by | FK users null | admin/finance |
| decision_note | text null | |
| confirmed_at | timestamptz null | **uniquement** après preuve exécution |
| created_at | | |

### commission_ledger (append-only)
| Champ | Type | Notes |
|---|---|---|
| id | | |
| order_item | FK, PROTECT | |
| order | FK, PROTECT | |
| artist | FK, PROTECT | |
| kind | varchar(20) | `CHARGE`, `REFUND_ADJUSTMENT` |
| gross_xaf, commission_xaf, artist_net_xaf | bigint | signés (négatif pour ajustement) |
| commission_rate_bps | int | figé copié |
| created_at | | |
| | **unique (order_item, kind)** pour CHARGE | anti double-écriture |

### payouts
| Champ | Type | Notes |
|---|---|---|
| id | | |
| artist | FK, PROTECT | |
| amount_xaf | bigint | |
| status | varchar(15) | `PENDING`, `PROCESSING`, `PAID`, `FAILED` |
| method | varchar(20) | `CAMPAY_MASS_PAYOUT`, `MANUAL` |
| provider_batch_ref | varchar(120) null | |
| executed_by | FK users | finance/admin |
| proof_note | text null | référence transaction CamPay |
| created_at, paid_at | | |

## 4. Livraison et litiges

### shipments
| Champ | Type | Notes |
|---|---|---|
| id | | |
| order | FK, PROTECT | |
| artist | FK, PROTECT | **1 shipment par (order, artist)** — unique |
| status | varchar(12) | `PENDING`, `SHIPPED`, `DELIVERED` |
| shipping_fee_xaf | bigint | figé au checkout (profil vendeur) |
| carrier | varchar(80) null | |
| tracking_number | varchar(120) null | |
| tracking_url | varchar(500) null | |
| shipped_at, delivered_at | null | |
| buyer_note / artist_note | text null | |
| created_at, updated_at | | |

### shipment_events (append-only)
`(shipment, status_from, status_to, actor, note, created_at)` — historique des transitions.

### disputes
| Champ | Type | Notes |
|---|---|---|
| id | | |
| order | FK, PROTECT | |
| opened_by | FK users | acheteur (ou artiste en réponse ? non : ouverture acheteur ou admin) |
| against | varchar(10) | `ARTIST`, `PLATFORM` |
| shipment | FK null | si litige lié à une expédition précise |
| reason | varchar(30) | `NOT_RECEIVED`, `DAMAGED`, `NOT_AS_DESCRIBED`, `COUNTERFEIT`, `OTHER` |
| description | text | |
| status | varchar(20) | `OPEN`, `ARTIST_RESPONDED`, `UNDER_REVIEW`, `RESOLVED_BUYER`, `RESOLVED_SELLER`, `CLOSED` |
| assigned_to | FK users null | modérateur/admin |
| resolution_note | text obligatoire à la clôture | |
| refund | FK refunds null | si accordé |
| created_at, resolved_at | | |
| | **unique active par order** | 1 litige ouvert à la fois (service) |

### dispute_evidence
`(dispute, uploaded_by, file privé, kind ∈ {PHOTO, DOCUMENT, TEXT_NOTE}, description, created_at)` — stockage privé + audit d'accès.

## 5. Gouvernance

### policy_documents + policy_versions
| policy_documents | |
|---|---|
| id, slug unique (`privacy-policy`, `terms-of-service`, `seller-policy`, `payment-refund-policy`, `confidentiality-policy`, `cookies-retention-policy`), category, created_at | |

| policy_versions | |
|---|---|
| id, policy FK, version varchar(20) (ex. `1.0`), language (`fr`/`en`), title, body_md/text, content_sha256, status (`DRAFT`,`PUBLISHED`,`SUPERSEDED`,`ARCHIVED`), published_at, effective_at, created_by, created_at | |
| **unique (policy, version, language)** ; 1 seule PUBLISHED par (policy, language) (UniqueConstraint conditionnelle) | |

### policy_acceptances (append-only)
`(user FK, policy_version FK PROTECT, accepted_at, mechanism ∈ {REGISTER_CHECKBOX, TOC_CLICK, ADMIN_TOS}, ip, user_agent)` — jamais de delete ; une nouvelle version = nouvelle ligne.

### cookie_preferences
`(user FK null (anonyme = session), essential_always_true, analytics bool default false, marketing bool default false, updated_at, version_banner int)` — cookies non essentiels **off par défaut**.

### audit_logs (append-only)
`(id, actor FK null, actor_role, action varchar(60) (ex. `artwork.published`, `refund.approved`), object_type, object_id, metadata JSON, ip inet, created_at)` — index `(actor, created_at)`, `(object_type, object_id)`, `(action, created_at)`. **Aucun UPDATE/DELETE.**

### notification_outbox
`(id, event varchar(60), user FK, channel ∈ {IN_APP, EMAIL}, subject, body_preview, payload JSON, status ∈ {PENDING, SENT, FAILED}, attempts int, last_error, dedupe_key unique null, scheduled_at, sent_at, created_at)` — index `(status, scheduled_at)`.

### platform_settings (singleton)
`(id=1, commission_rate_bps default 1000, reservation_ttl_minutes default 30, moderation_reprice_threshold_pct default 20, updated_by, updated_at)` — modifiable admin uniquement, changement audité.

## 6. Relations synthétiques

```
users 1─1 artist_profiles 1─N artworks 1─N artwork_media
users 1─N orders 1─N order_items N─1 artworks
orders 1─N payments 1─N payment_events
orders 1─N shipments 1─N shipment_events
orders 1─N refunds ; orders 1─0..1 disputes 1─N dispute_evidence
order_items 1─N commission_ledger ; artist_profiles 1─N payouts
carts 1─N cart_items N─1 artworks
users 1─N policy_acceptances N─1 policy_versions N─1 policy_documents
```

## 7. Intégrités clés (résumé)

1. `price_xaf`, montants commande/paiement : entiers, CHECK ≥ 0 (≥ 1 pour prix).
2. `Σ refunds ≤ payments encaissés` (vérifié en service + test).
3. `Σ ledger CHARGE − REFUND_ADJUSTMENT` = commissions dues par artiste (vue SQL de contrôle).
4. Stock : `stock_quantity ≥ 0` + verrou `FOR UPDATE` au checkout ; concurrence testée.
5. 1 seul `PENDING`-type actif : panier unique, réservation active par ligne, litige ouvert unique.
6. `payment_events.event_id` unique → rejeu webhook sans effet.
7. `order_items.commission_rate_bps` jamais muté après création (trigger ou service + test).
8. Politiques : 1 `PUBLISHED` max par (policy, language).
9. Médias : `alt_text` obligatoire images ; magic bytes validés ; fichiers hors webroot.
10. Audit/ledger/payments/payment_events/policy_acceptances/shipment_events : tables append-only (pas de model.save update sauf champs autorisés, pas de delete).
