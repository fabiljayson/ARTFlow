# Design — Itération « preuve sociale » inspirée de Kwossimboa

Date : 2026-11-09 · Statut : **proposé, en attente d'approbation**
(relecture builder faite, 4 questions arbitrées par l'utilisateur)
Référent : http://kwossimboa.com/ (étude comparative du 2026-11-09)

## Intention (le pourquoi)

Kwossimboa donne envie d'acheter parce que **le contenu est vivant** : compteur
d'écoutes, badge ✓, classement Trending, bouton Soutenir. ARTFlow a un catalogue
fonctionnel mais silencieux : aucun compteur visible, aucun badge, aucun classement
de popularité. Cette itération rend le catalogue ARTFlow vivant et rassurant
(preuve sociale) **sans changer le métier** (marketplace d'œuvres physiques,
paiement CamPay, commission 10 %).

## Objectifs

1. Badge **artiste vérifié ✓** visible partout où un nom d'artiste apparaît
2. **Compteur de vues** par œuvre (dont le détail honnête : vues uniques par visiteur/24 h)
3. **Favoris visibles** (compteur ♡ sur les cartes et la fiche)
4. **Page artiste enrichie** : œuvres · vendues · vues · favoris
5. **Section Tendances** : classement des œuvres populaires sur **7 jours glissants**
6. Badge **« N vendues »** (preuve sociale d'achat)

## Non-objectifs (volontairement hors lot)

- Bouton **« Soutenir l'artiste »** (pourboire MoMo) → **backlog**, Phase E/F
- Aperçu vidéo 40 s avant paiement → reporté à la Phase E (vidéos)
- Purge/rétention des événements de vue → commandement plus tard (les données
  restent en base pour l'instant, volume jugé faible)
- Tableau de bord d'analytics pour l'artiste, checkout sans compte, abonnements
- Modification du processus de modération ou de paiement existant
- Page « Mes favoris » (liste dédiée) → reportée ; le bouton ♡ de la fiche suffit
  à cette itération

## Anti-objectifs

- Ne jamais stocker d'IP ni de donnée personnelle brute (voir `viewer_key`)
- Ne pas fausser les chiffres : aucune incrémentation côté client seul
- Ne pas casser le SSR ni le cache des pages serveur existantes
- Ne pas ajouter de dépendance externe

## Contraintes projet

- Backend Django 6.1/DRF, frontend Next 16 (app router, pages serveur)
- UI en français, montants XAF, tokens DESIGN.md (clay/Liquid Glass)
- TDD : un test d'abord par comportement, 1 commit par étape
- Gates : `uv run pytest -q` + `ruff check` + `makemigrations --check` ;
  `npx oxlint src` + `tsc --noEmit` + `vitest run` + `next build`
- Smoke E2E HTTP via proxy :5175 en fin d'itération (compte
  `d1buyer@artflow.test`)
- Règle maison : ne rien écrire de personnel dans les docs système

## Approches considérées

**A — Tout en champs simples** : `view_count`, favoris et ventes agrégés en
requête, Tendances = « les plus vues toutes époques ».
→ *Écartée* : le classement reste statique (les anciennes populaires écrasent
les nouveautés), contraire à l'esprit Trending de Kwossimboa.

**B — Compteur dénormalisé + table d'événements** *(retenue, validée par
l'utilisateur)* : `Artwork.view_count` pour l'affichage + table `ArtworkView`
(œuvres, clé visiteur anonyme, date) pour les fenêtres glissantes (Tendances 7 j,
dé-duplication 24 h). Les favoris ont déjà `created_at` → le score Tendances
combine les deux.

## Décisions

### 1. Badge artiste vérifié ✓

- `ArtistPublicSerializer` (+ détaillé) gagne `is_verified` :
  `status == APPROVED` (les statuts PENDING/REJECTED/SUSPENDED → false)
- Affichage : grille catalogue (ligne artiste de `ArtworkCard`), fiche œuvre,
  en-tête + liste de `/artistes`, page `/artistes/[slug]`
- Rendu : petit ✓ (SVG/icône) à côté du nom, même traitement sur desktop/mobile
- Aucun changement de modèle → pas de migration

### 2. Compteur de vues

**Modèles** (migration `catalogue`) :
- `Artwork.view_count` = `PositiveIntegerField(default=0)` (affichage)
- `ArtworkView` : `artwork` FK CASCADE, `viewer_key` Char(32),
  `created_at` = `default=timezone.now` (**pas** `auto_now_add` : le seed et les
  tests doivent pouvoir dater les événements dans le passé) ; index
  `(artwork, viewer_key, created_at)` + index `created_at`

**Règles** :
- `viewer_key` = **cookie visiteur opaque** *(décision utilisateur — le relecteur
  a montré que Django ne voit que 127.0.0.1 derrière le proxy Next, ce qui rendait
  la clé IP inutilisable)* :
  - à chaque POST vue, si le cookie `af_visitor` est absent → Django génère
    `secrets.token_hex(16)`, le pose en `HttpOnly` + `SameSite=Lax`
    (`max_age` 1 an, `Secure` en prod) et répond
    - `viewer_key = sha256(token)[:32]` (le jeton brut n'est jamais stocké en base)
  - aucune IP ni user-agent utilisés → conforme à l'anti-objectif vie privée
- **Dé-duplication 24 h** : si une vue du même `viewer_key` sur la même œuvre
  existe depuis < 24 h → réponse 200 mais `counted: false`, `view_count`
  inchangé (rafraîchir la page ne gonfle pas le compteur)
- `view_count` incrémenté uniquement quand `counted: true`
- Les vues de l'artiste lui-même comptent (MVP assumé)

**Endpoint** : `POST /api/v1/catalog/artworks/<slug>/view/` — `AllowAny`,
404 si l'œuvre n'est pas `PUBLISHED`, throttle scope `artwork-view: 120/min`
(déclaré dans la vue + `DEFAULT_THROTTLE_RATES`), réponse
`{"view_count": 42, "counted": true}`.
*Note throttle* : DRF identifie l'anon par l'IP (X-Forwarded-For d'abord s'il
existe) → en dev derrière le proxy Next, budget partagé pour tous (120/min
largement suffisant pour dev/smoke ; en prod, le reverse proxy transmet XFF).

**Frontend** : composant client `<ViewTracker slug>` monté **une fois** sur
`/oeuvre/[slug]` (effet au montage, silencieux en cas d'erreur, jamais pendant
le SSR). Compteur affiché : badge « 👁 42 vues » sur la fiche et les cartes.

### 3. Favoris visibles (♡) — **avec bouton** *(décision utilisateur)*

- `ArtworkSummarySerializer` gagne `favorite_count`
  (`Count("favorited_by", distinct=True)` via annotation)
- Carte : ligne de méta « 👁 42 · ♡ 12 » (masquée si les deux sont à 0)
- Fiche œuvre : même ligne à côté du prix
- **Bouton ♡ sur la fiche œuvre** (composant client) :
  - anonyme → clic → redirection `/connexion?next=` (comme le panier)
  - connecté → `POST /catalog/artworks/{id}/favorite/`, état optimiste
    (cœur plein/vidé, compteur ±1), re-bascule possible
  - **fix** : l'helper `toggleFavorite` du frontend appelle une URL fausse
    (`/catalog/artworks/favorite/`) → corrigée en `/catalog/artworks/{id}/favorite/`
- `ArtworkDetailSerializer` gagne `is_favorited` (bool, `false` si anonyme)
- Le backend toggle existe déjà, seul le frontend est à corriger/ajouter

### 4. Page artiste enrichie

- `ArtistPublicDetailSerializer.stats` :
  - `works` = œuvres publiées (existant)
  - `sold` = Σ `OrderItem.quantity` dont `Order.status` ∈
    `{PAID, PROCESSING, SHIPPED, DELIVERED, PARTIALLY_REFUNDED}`
    (exclut PENDING_PAYMENT, CANCELLED, REFUNDED)
  - `views` = Σ `view_count` des œuvres publiées
  - `favorites` = Σ `favorite_count` des œuvres publiées
- UI en-tête : badge ✓ + « 14 œuvres · 3 vendues · 1 200 vues · 45 ♡ »
  (remplace la ligne « N œuvres publiées » actuelle)
- Nécessite un import `commerce.OrderItem` depuis `catalogue` (même projet,
  accepté ; helper dédié `catalogue/queries.py::with_stats`)

### 5. Section Tendances (7 jours)

- `sort=trending` dans `CatalogArtworkList` : annotations
  `views_7d` (ArtworkView ≥ now−7 j) et `favs_7d` (Favorite ≥ now−7 j),
  **score = views_7d + 3 × favs_7d**, tri `-score, -published_at`
  (1 favori pèse 3 vues : intention d'achat plus forte — poids figé en constante
  nommée, ajustable)
- `ArtworkSummarySerializer` expose `views_7d` (utilisé par la carte Trending)
- **Catalogue** : option « Tendances » ajoutée au select de tri
  (`/catalogue?sort=trending`)
- **Accueil** : section « Tendances » (8 premières cartes, lien « Voir tout »
  → `/catalogue?sort=trending`)
- Helper `catalogue/queries.py::with_stats(qs)` réutilisé par : liste catalogue,
  similaires, favoris, œuvres de la page artiste, section accueil

### 6. Badge « N vendues »

- `ArtworkSummarySerializer` gagne `sold_count` (même définition que `stats.sold`,
  annotation `Count("order_items", filter=...)`)
- Carte : badge discret « 3 vendues » (> 0 uniquement), fiche œuvre : ligne
  dédiée près du prix (« Pièce unique — déjà vendue » si `sold_count ≥ 1` et
  `is_unique_piece`)
- Définition en constante partagée `PAID_ORDER_STATUSES` (source unique pour
  features 4 et 6)

### 7. Seed démo « preuve sociale » *(décision utilisateur)*

Sans ça, la base réelle montre 0 partout (0 commande payée, 0 vue, favori
hors fenêtre 7 j). Nouvelle commande de gestion `seed_social` (idempotente,
déterministe, réexécutable) :

- **vues** : ~40–60 `ArtworkView` réparties sur les 7 derniers jours sur
  ~10 œuvres publiées (dates fixes, `viewer_key` générés) + `view_count`
  recalculé pour rester cohérent
- **favoris** : ~15 favoris récents (< 7 j) + quelques anciens (hors fenêtre)
  sur comptes démo existants
- **commande payée** : 1 commande `PAID` créée via les **vrais services**
  (checkout → `mark_paid`) pour un compte démo → badge « vendues » visible
- respecte le garde `exists()` du style `seed_catalogue` (skip si déjà en place)

## Points ouverts réglés par le builder (appel de conception)

- Emplacement du helper `with_stats` et des constantes : `catalogue/queries.py`
- Ordre des migrations : une seule migration `catalogue` pour l'itération
- Le throttle `artwork-view` est déclaré dans `DEFAULT_THROTTLE_RATES` settings

## Ce qui reste au builder

- Écrire les tests d'abord (backend : vue/dé-dup/throttle/cookie/trending/sold/
  artist stats/seed idempotent ; frontend : cartes avec compteurs, bouton ♡,
  ViewTracker, section accueil)
- Choisir l'icône/le style exact des badges dans les tokens existants
- Le smoke E2E final + mise à jour `docs/api.md`, `docs/database.md`,
  `docs/screens.md`
- Backlog à documenter dans le rapport : bouton Soutenir, purge des vues,
  page « Mes favoris »

## Séquençage *(décision utilisateur)*

1. **Phase 0 — clore la D3** : gates complets backend/frontend,
   `smoke_d3.py` (~40 checks), `payments.md` §5/§2, `MEMORY.md`, rapport §27 D3
   (inchangé par ce design)
2. Puis cette itération, planifiée via le skill writing-plans
3. Ensuite : D4 (expéditions/litiges) reprend son cours
