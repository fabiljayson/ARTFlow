# Itération « preuve sociale » (inspirée Kwossimboa) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre le catalogue ARTFlow vivant et rassurant : badge artiste vérifié ✓, compteurs de vues/favoris/ventes, page artiste enrichie, section Tendances (fenêtre 7 jours) et seed de démonstration.

**Architecture:** Une table d'événements `ArtworkView` (clé visiteur anonyme issue d'un cookie) + champ dénormalisé `view_count` pour l'affichage ; statistiques agrégées côté serveur via sous-requêtes (`catalogue/queries.py`) pour éviter le produit cartésien des Jointures multiples ; le tri `sort=trending` calcule un score 7 jours (vues + 3×favoris) dans le queryset.

**Tech Stack:** Django 6.1 + DRF (backend, port 8003), Next.js 16 app router (frontend, port 5175), PostgreSQL (Docker `artflow-postgres` :5435), pytest + Vitest/RTL.

**Spec:** `docs/superpowers/specs/2026-11-09-kwossimboa-social-proof-design.md` (design approuvé le 2026-11-09 — le plan argue de ce document, lire les deux).

## Global Constraints

- UI en **français**, tokens DESIGN.md (clay/Liquid Glass/Geist), montants en **XAF**
- **TDD** : échec d'abord à chaque étape fonctionnelle ; **1 commit par étape** de fin de tâche
- Messages de commit : `Social proof: <description>` (fonctionnel) ou `docs: <description>` (docs)
- Gates backend (depuis `backend/`) : `timeout 360000 uv run pytest -q -p no:cacheprovider` (exit 0),
  `uv run ruff check .`, `uv run python manage.py makemigrations --check --dry-run`
- Gates frontend (depuis `frontend/`) : `npx oxlint src` (0 erreur), `npx tsc --noEmit` (0),
  `npx vitest run`, `npm run build` (20 routes, inchangé)
- Toute nouvelle app/champ exige `uv run python manage.py migrate` sur la BDD dev avant smoke
- **Règle maison** : aucune donnée personnelle dans les docs système
- Chemins API : toujours écrire les paths avec slash final dans `api.ts`
  (`apiFetch` le retire, le proxy Next le rétablit — sinon boucle 308/301)
- Constantes nommées partagées : `PAID_ORDER_STATUSES` (commerce), cookie `af_visitor`

## Review Focus

1. **Dé-duplication 24 h** : le même visiteur qui recharge la fiche ne doit PAS incrémenter ; un visiteur neuf doit incrémenter — test dans Task 3.
2. **Œuvre non publiée** : POST vue sur un brouillon → 404 et zéro événement créé — test dans Task 3.
3. **Fenêtre 7 jours du Trending** : une vue de 8 jours ne doit plus compter ; 1 favori récent (poids 3) doit battre 2 vues récentes — tests dans Task 5.
4. **Compte « vendues »** : commandes `PENDING_PAYMENT`, `CANCELLED`, `REFUNDED` exclues ; `PAID` et `DELIVERED` inclus — test dans Task 5.
5. **Faveur anonyme** : bouton ♡ non connecté → redirection `/connexion?next=` sans
   erreur ; artiste `PENDING`/`SUSPENDED` → `is_verified=false` — tests dans Tasks 7 et 1.

---

### Task 0: Prélude — clore la Phase D3

**Files:**
- Read : `docs/plans/2026-10-28-d3-paiement.md` (Task 6, non cochée)
- Create : `/tmp/opencode/smoke_d3.py`
- Modify : `docs/payments.md`, `MEMORY.md`

Les étapes exactes (scénarios smoke ~40 checks, gates complets, docs) sont détaillées
dans le plan D3, Task 6 — exécuter tel quel :

- [ ] Gates complets backend (pytest exit 0 + ruff + makemigrations --check) et frontend (vitest/oxlint/tsc/build)
- [ ] Écrire et exécuter `smoke_d3.py` → 100 % OK ; corriger le code si échec réel
- [ ] `docs/payments.md` §5/§2 cochés, `docs/api.md` relue si besoin
- [ ] `MEMORY.md` : entrée D3 livrée + pièges ; rapport §27 D3 présenté dans le chat
- [ ] Commit : `docs: D3 payment phase status + smoke`

> Rien de ce prélude ne touche aux fichiers des tâches suivantes (hors `MEMORY.md`
> et `docs/api.md`, relus en Task 11).

---

### Task 1: Badge artiste vérifié — backend

**Files:**
- Modify : `backend/apps/catalogue/serializers.py` (`ArtworkSummarySerializer`, `ArtistPublicSerializer`)
- Test : `backend/apps/catalogue/tests/test_api_public.py`

**Interfaces:**
- Produces : `ArtworkSummarySerializer.artist_verified : bool` (`artist.status == APPROVED`) ;
  `ArtistPublicSerializer.is_verified : bool` (même logique sur `obj.status`) ;
  `ArtistPublicDetailSerializer` hérite de `is_verified` sans modification

- [ ] **Step 1: Écrire les tests échouants** (dans `test_api_public.py`, nouvelle classe `TestVerifiedBadge`)

```python
def test_artist_is_verified_when_approved(self, client, artwork_factory):
    art = artwork_factory(status=ArtworkStatus.PUBLISHED)
    data = client.get(ARTISTS).json()
    assert data["results"][0]["is_verified"] is True

def test_artist_not_verified_when_pending(self, client, user_factory, category, db):
    from apps.artists.models import ApplicationStatus, ArtistProfile
    ArtistProfile.objects.create(user=user_factory(), display_name="Sous", city="Yaoundé",
                                 status=ApplicationStatus.PENDING_REVIEW)
    data = client.get(ARTISTS).json()
    pending = next(r for r in data["results"] if r["display_name"] == "Sous")
    assert pending["is_verified"] is False

def test_artist_not_verified_when_suspended(self, client, user_factory, db):
    from apps.artists.models import ApplicationStatus, ArtistProfile
    ArtistProfile.objects.create(user=user_factory(), display_name="Suspendu", city="Douala",
                                 status=ApplicationStatus.SUSPENDED)
    data = client.get(ARTISTS).json()
    row = next(r for r in data["results"] if r["display_name"] == "Suspendu")
    assert row["is_verified"] is False

def test_artwork_summary_exposes_artist_verified(self, client, artwork_factory):
    art = artwork_factory(status=ArtworkStatus.PUBLISHED)
    assert client.get(detail(art.slug)).json()["artist_verified"] is True
```

- [ ] **Step 2: Vérifier l'échec** — Run: `uv run pytest apps/catalogue/tests/test_api_public.py -k VerifiedBadge -v` (depuis `backend/`) → FAIL (KeyError/AssertionError, champ absent)

- [ ] **Step 3: Implémenter** — dans `ArtworkSummarySerializer` : champ
  `artist_verified = serializers.SerializerMethodField()` + `get_artist_artist_verified`
  renvoyant `obj.artist.status == ApplicationStatus.APPROVED` (importer
  `ApplicationStatus` depuis `apps.artists.models`) ; dans `ArtistPublicSerializer` :
  `is_verified` de même nature sur `obj.status`. Ajouter les champs à `Meta.fields`.

- [ ] **Step 4: Vérifier le passage** — Run: idem Step 2 → PASS ; puis toute la file publique :
  `uv run pytest apps/catalogue/tests/ -q` → exit 0

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Social proof: expose artist verified flag"`

---

### Task 2: Badge artiste vérifié — frontend

**Files:**
- Create : `frontend/src/components/verified-badge.tsx`
- Modify : `frontend/src/lib/api.ts` (types `ArtworkSummary`, `ArtistPublic`), `frontend/src/components/artwork-card.tsx`, `frontend/src/app/oeuvre/[slug]/page.tsx`, `frontend/src/app/artistes/page.tsx`, `frontend/src/app/artistes/[slug]/page.tsx`
- Test : `frontend/src/components/verified-badge.test.tsx`

**Interfaces:**
- Consumes : `artist_verified` (ArtworkSummary), `is_verified` (ArtistPublic) — Task 1
- Produits : `<VerifiedBadge />` — composant présentatif sans props, SVG ✓ + `aria-label="Artiste vérifié"` ; types TS `artist_verified: boolean`, `is_verified: boolean`

- [ ] **Step 1: Test échouant** — `verified-badge.test.tsx` :

```tsx
it("affiche le badge avec un libellé accessible", () => {
  render(<VerifiedBadge />);
  expect(screen.getByLabelText("Artiste vérifié")).toBeInTheDocument();
});
```

- [ ] **Step 2: Vérifier l'échec** — Run: `npx vitest run src/components/verified-badge.test.tsx` → FAIL (module absent)

- [ ] **Step 3: Implémenter le composant** — fichier unique ne proposant que le composant
  (règle oxlint `only-export-components`), style : petit cercle `text-primary`/check,
  `inline-flex`, aucune dépendance externe. Ajouter les deux champs aux interfaces TS.

- [ ] **Step 4: Tests d'intégration** — **d'abord** ajouter `artist_verified: false` au helper
  `makeArtwork` de `artwork-card.test.tsx` (sinon `tsc` casse sur le type requis), puis :

```tsx
it("affiche le badge vérifié à côté de l'artiste", () => {
  render(<ArtworkCard artwork={makeArtwork({ artist_verified: true })} />);
  expect(screen.getByLabelText("Artiste vérifié")).toBeInTheDocument();
});
it("n'affiche pas le badge si l'artiste n'est pas vérifié", () => {
  render(<ArtworkCard artwork={makeArtwork({ artist_verified: false })} />);
  expect(screen.queryByLabelText("Artiste vérifié")).not.toBeInTheDocument();
});
```

- [ ] **Step 5: Vérifier le passage** — Run: `npx vitest run` → tous verts ; intégration
  visuelle : badge sur la ligne artiste de `ArtworkCard`, à côté du lien artiste de la fiche
  œuvre (après `{artwork.artist_display_name}`), dans l'en-tête `<h1>` de
  `/artistes/[slug]`, et dans la liste `/artistes` (après `display_name`).

- [ ] **Step 6: Gates** — `npx oxlint src && npx tsc --noEmit && npx vitest run && npm run build` → 0/0/verts/20 routes

- [ ] **Step 7: Commit** — `Social proof: verified badge on cards and artist pages`

---

### Task 3: Compteur de vues — backend (modèles + endpoint)

**Files:**
- Modify : `backend/apps/catalogue/models.py` (champ `view_count` + modèle `ArtworkView`), `backend/apps/catalogue/views.py`, `backend/apps/catalogue/urls.py`, `backend/config/settings.py` (rate throttle)
- Create : `backend/apps/catalogue/migrations/000X_artworkview_and_view_count.py` (via `makemigrations`)
- Test : `backend/apps/catalogue/tests/test_api_views.py` (nouveau)

**Interfaces:**
- Produces : `Artwork.view_count : PositiveIntegerField(default=0)` ;
  `ArtworkView(artwork FK CASCADE, viewer_key Char(32), created_at default=timezone.now)`
  avec index `(artwork, viewer_key, created_at)` + index `(created_at)` —
  **`default=timezone.now` et non `auto_now_add`** : le seed (Task 10) et les tests
  (Task 5) doivent dater les événements dans le passé ;
  `POST /api/v1/catalog/artworks/<slug>/view/` → `{"view_count": int, "counted": bool}` ;
  cookie `af_visitor` (HttpOnly, SameSite=Lax, max_age 31 536 000, secure si
  `request.is_secure()`) ; scope throttle `artwork-view` (rate `120/min`)
- Note : le champ `view_count` vit **sur `Artwork`**, la table sert aux fenêtres
  glissantes et à la dé-duplication — ne pas compter depuis la table dans les serializers

- [ ] **Step 1: Tests échouants** — `test_api_views.py` (imports :
  `hashlib`, `pytest`, `APIClient`, `ArtworkStatus`, `ArtworkView`, `Artwork` ;
  fixture locale `client = APIClient()` comme dans `test_api_public.py`) :

```python
VIEW = lambda slug: f"/api/v1/catalog/artworks/{slug}/view/"  # helper def view_url(slug)

def test_first_view_sets_visitor_cookie_and_counts(client, artwork_factory):
    art = artwork_factory(status=ArtworkStatus.PUBLISHED)
    resp = client.post(view_url(art.slug))
    assert resp.status_code == 200
    assert resp.json() == {"view_count": 1, "counted": True}
    token = client.cookies["af_visitor"]
    assert token  # présent
    # HttpOnly : accessible pour le navigateur mais pas via JS — vérifié par le code de la vue
    art.refresh_from_db()
    assert art.view_count == 1
    ev = ArtworkView.objects.get(artwork=art)
    assert ev.viewer_key == hashlib.sha256(token.encode()).hexdigest()[:32]

def test_same_visitor_within_24h_not_counted(client, artwork_factory):
    art = artwork_factory(status=ArtworkStatus.PUBLISHED)
    client.post(view_url(art.slug))
    resp = client.post(view_url(art.slug))
    assert resp.json() == {"view_count": 1, "counted": False}
    assert ArtworkView.objects.count() == 1

def test_new_visitor_counts_separately(client, artwork_factory):
    art = artwork_factory(status=ArtworkStatus.PUBLISHED)
    client.post(view_url(art.slug))
    from rest_framework.test import APIClient
    resp = APIClient().post(view_url(art.slug))
    assert resp.json() == {"view_count": 2, "counted": True}

def test_unpublished_returns_404_and_creates_nothing(client, artwork_factory):
    art = artwork_factory(status=ArtworkStatus.DRAFT)
    assert client.post(view_url(art.slug)).status_code == 404
    assert not ArtworkView.objects.exists()

def test_throttle_scope_declared():
    from apps.catalogue.views import ArtworkViewTrack
    from rest_framework.settings import api_settings
    assert ArtworkViewTrack.throttle_scope == "artwork-view"
    assert api_settings.DEFAULT_THROTTLE_RATES["artwork-view"] == "120/min"
```

- [ ] **Step 2: Vérifier l'échec** — Run: `uv run pytest apps/catalogue/tests/test_api_views.py -v` → FAIL (ImportError `ArtworkView`)

- [ ] **Step 3: Modèles** — dans `models.py` : champ sur `Artwork` (après `stock_quantity`) ;
  classe `ArtworkView` avec `Meta.indexes` cités + `__str__` bref. Puis
  `uv run python manage.py makemigrations catalogue` → migration créée ; `migrate` OK.

- [ ] **Step 4: Vue + URL + throttle** — `ArtworkViewTrack(APIView)` :
  `permission_classes = [AllowAny]`, `throttle_classes = [ScopedRateThrottle]`,
  `throttle_scope = "artwork-view"` ; `post(request, slug)` :
  1. artwork PUBLISHED sinon `Http404`
  2. token = `request.COOKIES.get("af_visitor")` ; si absent →
     `secrets.token_hex(16)` + `response.set_cookie("af_visitor", token, max_age=31536000, httponly=True, samesite="Lax", secure=request.is_secure())`
  3. `viewer_key = hashlib.sha256(token.encode()).hexdigest()[:32]`
  4. dé-dup : `ArtworkView.objects.filter(artwork=..., viewer_key=..., created_at__gte=timezone.now()-timedelta(hours=24)).exists()`
     → si vrai : réponse `counted=False` sans incrémenter
  5. sinon créer l'événement + `artwork.view_count = F("view_count") + 1` + `refresh_from_db`/réponse `counted=True` avec la valeur lue
  Dans `settings.py` : `"artwork-view": "120/min"` dans `DEFAULT_THROTTLE_RATES`.
  Dans `urls.py` : `path("catalog/artworks/<slug:slug>/view/", ...)` **avant** la route
  `media/` pour éviter toute collision de capture.

- [ ] **Step 5: Vérifier le passage** — Run: idem Step 2 → PASS ; file complète
  `uv run pytest apps/catalogue/tests/ -q` → exit 0 ; ruff OK

- [ ] **Step 6: Commit** — `Social proof: artwork view tracking with visitor cookie dedup`

---

### Task 4: Compteur de vues — frontend (ViewTracker)

**Files:**
- Create : `frontend/src/components/view-tracker.tsx`
- Modify : `frontend/src/lib/api.ts`, `frontend/src/app/oeuvre/[slug]/page.tsx`
- Test : `frontend/src/components/view-tracker.test.tsx`

**Interfaces:**
- Consumes : endpoint Task 3
- Produits : `recordView(slug: string): Promise<{ view_count: number; counted: boolean }>`
  → `apiFetch("/catalog/artworks/" + slug + "/view/", { method: "POST" })` (chemin **avec**
  slash final) ; `<ViewTracker slug={string} />` — composant client, rend `null`

- [ ] **Step 1: Test échouant** :

```tsx
it("envoie une vue au montage une seule fois", async () => {
  const spy = vi.spyOn(api, "recordView").mockResolvedValue({ view_count: 1, counted: true });
  render(<ViewTracker slug="masque-wouri" />);
  await waitFor(() => expect(spy).toHaveBeenCalledWith("masque-wouri"));
  expect(spy).toHaveBeenCalledTimes(1);
});
it("reste silencieux si l'enregistrement échoue", async () => {
  vi.spyOn(api, "recordView").mockRejectedValue(new Error("boom"));
  render(<ViewTracker slug="masque-wouri" />);
  await waitFor(() => expect(api.recordView).toHaveBeenCalled());
  expect(screen.queryByText(/erreur/i)).not.toBeInTheDocument();
});
```

(mock `vi.mock("@/lib/api", ...)` avec `importOriginal` pour ne pas casser les autres
exports, ou spyOn du module importé — même motif que `artwork-card.test.tsx`.)

- [ ] **Step 2: Vérifier l'échec** — Run: `npx vitest run src/components/view-tracker.test.tsx` → FAIL

- [ ] **Step 3: Implémenter** — `recordView` dans `api.ts` (près de `getSimilarArtworks`) ;
  `ViewTracker` : `useEffect(() => { recordView(slug).catch(() => {}) }, [slug])`,
  aucun état, aucun rendu.

- [ ] **Step 4: Monter sur la fiche** — dans `oeuvre/[slug]/page.tsx`, à côté du `<Suspense>`
  bas de page : `<ViewTracker slug={slug} />` (client component importé — pas de `"use client"`
  sur la page serveur, l'import suffit).

- [ ] **Step 5: Vérifier le passage** — Run: `npx vitest run` → verts ; `npx oxlint src && npx tsc --noEmit && npm run build`

- [ ] **Step 6: Commit** — `Social proof: fire view tracking on artwork detail page`

---

### Task 5: Statistiques agrégées — backend (with_stats, trending, stats artiste)

**Files:**
- Modify : `backend/apps/commerce/models.py` (constante `PAID_ORDER_STATUSES`),
  `backend/apps/catalogue/serializers.py`, `backend/apps/catalogue/views.py`
- Create : `backend/apps/catalogue/queries.py`
- Test : `backend/apps/catalogue/tests/test_api_stats.py` (nouveau)

**Interfaces:**
- Consumes : `Artwork.view_count`, `ArtworkView` (Task 3), `make_order` de `backend/apps/conftest.py`
- Produits :
  - `apps.commerce.models.PAID_ORDER_STATUSES : frozenset[str]` =
    `{PAID, PROCESSING, SHIPPED, DELIVERED, PARTIALLY_REFUNDED}` (défini à côté de `Order.Status`)
  - `catalogue.queries.with_stats(qs) -> qs` — annoté `favorite_count`
    (`Count("favorited_by", distinct=True)`) et `sold_count`
    (**Subquery** `OrderItem…annotate(s=Sum("quantity")).values("s")[:1]` filtrée
    `artwork=OuterRef("pk")` + `order__status__in=PAID_ORDER_STATUSES`, `Coalesce(..., 0)`)
    → **pas de jointure directe** : Count + Sum sur deux relations multi-valeurs
    produisent un produit cartésien qui fausse la somme
  - `catalogue.queries.trending_rank(qs) -> qs` — ajoute `views_7d` et `favs_7d`
    (Subquery `ArtworkView`/`Favorite` avec `created_at__gte=now-7d`) + `score =
    views_7d + 3 * favs_7d` (constante `TRENDING_FAV_WEIGHT = 3` dans le même fichier)
  - `ArtworkSummarySerializer` + champs `favorite_count : int`, `sold_count : int`,
    `views_7d : int` (default 0 côté FE)
  - `ArtistPublicDetailSerializer.stats : {"works": int, "sold": int, "views": int, "favorites": int}`
    — calculé dans `get_stats(obj)` par **agrégations séparées** (jamais combinées en une
    seule annotation, voir note cartésienne) : `obj.artworks.filter(status=PUBLISHED).aggregate(Count("pk"), Sum("view_count"))`
    pour works+views ; `Favorite.objects.filter(artwork__artist=obj, artwork__status=PUBLISHED).count()`
    pour favorites ; `OrderItem.objects.filter(artist=obj, order__status__in=PAID_ORDER_STATUSES).aggregate(Sum("quantity"))`
    pour sold → 3 requêtes propres sur le détail d'un seul artiste
  - `sort=trending` accepté dans `CatalogArtworkList` : `trending_rank(qs).order_by("-score", "-published_at")`
  - `with_stats` appliqué à : liste catalogue, similaires, favoris, œuvres du détail artiste

- [ ] **Step 1: Tests échouants** — `test_api_stats.py` (imports : `timedelta`,
  `django.utils.timezone`, `pytest`, `APIClient` + fixture locale `client`,
  `ArtworkStatus`/`ArtworkView`/`Favorite` depuis `apps.catalogue.models`,
  `Order` depuis `apps.commerce.models`, `make_order` depuis `apps.conftest`) :

```python
def test_summary_exposes_counts(client, artwork_factory, user_factory, user):
    art = artwork_factory(status=ArtworkStatus.PUBLISHED)
    Favorite.objects.create(user=user, artwork=art)
    make_order(user_factory(), art, status=Order.Status.PAID, quantity=2)
    row = client.get(LIST).json()["results"][0]
    assert row["favorite_count"] == 1
    assert row["sold_count"] == 2

def test_sold_excludes_pending_cancelled_refunded(client, artwork_factory, user_factory):
    art = artwork_factory(status=ArtworkStatus.PUBLISHED)
    for st in (Order.Status.PENDING_PAYMENT, Order.Status.CANCELLED, Order.Status.REFUNDED):
        make_order(user_factory(), art, status=st, quantity=1)
    assert client.get(LIST).json()["results"][0]["sold_count"] == 0

def test_trending_prefers_recent_views(client, artwork_factory, db):
    old, new = (artwork_factory(status=ArtworkStatus.PUBLISHED, title=t)
                for t in ("Ancien", "Recent"))
    now = timezone.now()
    for i in range(5):
        ArtworkView.objects.create(artwork=old, viewer_key=f"o{i}", created_at=now - timedelta(days=6))
    ArtworkView.objects.create(artwork=new, viewer_key="n1", created_at=now - timedelta(hours=1))
    ArtworkView.objects.create(artwork=new, viewer_key="n2", created_at=now - timedelta(hours=2))
    titles = [r["title"] for r in client.get(f"{LIST}?sort=trending").json()["results"]]
    assert titles.index("Ancien") > titles.index("Recent")  # 2 vues récentes > 5 vues de j6

def test_trending_window_is_7_days(client, artwork_factory, db):
    stale = artwork_factory(status=ArtworkStatus.PUBLISHED, title="Vieux")
    fresh = artwork_factory(status=ArtworkStatus.PUBLISHED, title="Frais")
    ArtworkView.objects.create(artwork=stale, viewer_key="s", created_at=timezone.now() - timedelta(days=7, hours=1))
    ArtworkView.objects.create(artwork=fresh, viewer_key="f", created_at=timezone.now() - timedelta(days=1))
    rows = client.get(f"{LIST}?sort=trending").json()["results"]
    assert rows[0]["title"] == "Frais"

def test_trending_fav_weights_3(client, artwork_factory, user_factory, user):
    two_views = artwork_factory(status=ArtworkStatus.PUBLISHED, title="2v")
    one_fav = artwork_factory(status=ArtworkStatus.PUBLISHED, title="1f")
    now = timezone.now()
    ArtworkView.objects.create(artwork=two_views, viewer_key="a", created_at=now)
    ArtworkView.objects.create(artwork=two_views, viewer_key="b", created_at=now)
    Favorite.objects.create(user=user_factory(), artwork=one_fav, created_at=now)
    rows = client.get(f"{LIST}?sort=trending").json()["results"]
    assert rows[0]["title"] == "1f"

def test_artist_detail_stats(client, artwork_factory, user, user_factory):
    art = artwork_factory(status=ArtworkStatus.PUBLISHED, stock=3)
    make_order(user_factory(), art, status=Order.Status.PAID, quantity=1)
    Favorite.objects.create(user=user, artwork=art)
    stats = client.get(f"/api/v1/catalog/artists/{art.artist.slug}/").json()["stats"]
    assert stats == {"works": 1, "sold": 1, "views": 0, "favorites": 1}
```

- [ ] **Step 2: Vérifier l'échec** — Run: `uv run pytest apps/catalogue/tests/test_api_stats.py -v` → FAIL (champ absent)

- [ ] **Step 3: `PAID_ORDER_STATUSES`** — dans `commerce/models.py` juste après `Order`,
  `PAID_ORDER_STATUSES = frozenset({...})` (valeurs exactes de `Order.Status`). File commerce : `uv run pytest apps/commerce/ -q` → exit 0. Commit intermédiaire :
  `Social proof: shared paid order statuses constant`

- [ ] **Step 4: `queries.py`** — implémenter `with_stats` et `trending_rank` comme spécifié
  (Subquery + Coalesce ; `outerref`/`output_field=IntegerField()`). Aucune jointure directe
  vers `order_items` dans une annotation combinée.

- [ ] **Step 5: serializers + vues** — champs du summary ; `stats` dans le détail artiste via
  `get_stats(obj)` avec les **3 agrégations séparées** décrites en Interfaces (jamais combinées) ;
  `sort=trending` dans `sort_map` via branche spéciale (avant `qs.order_by` final) ;
  `with_stats` appelé dans les queryset des 4 vues listées.

- [ ] **Step 6: Vérifier le passage** — Run: idem Step 2 → PASS ;
  `uv run pytest apps/catalogue/tests/ apps/commerce/tests/ -q` → exit 0 ; ruff

- [ ] **Step 7: Commit** — `Social proof: social stats annotations and 7-day trending sort`

---

### Task 6: Compteurs visibles — frontend

**Files:**
- Modify : `frontend/src/lib/api.ts` (types), `frontend/src/components/artwork-card.tsx`
- Create : `frontend/src/components/social-counts.tsx`
- Modify : `frontend/src/app/oeuvre/[slug]/page.tsx`
- Test : `frontend/src/components/social-counts.test.tsx`, `frontend/src/components/artwork-card.test.tsx`

**Interfaces:**
- Consumes : `favorite_count`, `sold_count`, `views_7d`, `view_count` — Task 5 (+ 3 pour `view_count`)
- Produits : `<SocialCounts viewCount={number} favoriteCount={number} />` —
  ligne « 👁 N · ♡ M », rend `null` si les deux sont à 0 (masqué) — **utilisé sur les cartes
  uniquement** ; sur la **fiche œuvre**, la ligne se compose de : `👁 N vues` (span inline à
  côté du prix), le badge « N vendues » (si `sold_count > 0`), et le `♡` du `FavoriteButton`
  (Task 7, qui porte son propre compteur) → **pas de `SocialCounts` sur la fiche**, évite
  tout doublon d'état entre le compteur et le bouton ;
  `ArtworkCard` gère aussi le badge « N vendues » (`sold_count > 0`) ;
  types : `favorite_count: number`, `sold_count: number`, `views_7d: number`

- [ ] **Step 1: Tests échouants** :

```tsx
it("affiche les vues et favoris", () => {
  render(<SocialCounts viewCount={42} favoriteCount={12} />);
  expect(screen.getByText(/42/)).toBeInTheDocument();
  expect(screen.getByText(/12/)).toBeInTheDocument();
});
it("reste vide quand tout est à zéro", () => {
  const { container } = render(<SocialCounts viewCount={0} favoriteCount={0} />);
  expect(container).toBeEmptyDOMElement();
});
// artwork-card.test.tsx :
it("affiche le badge vendues si sold_count > 0", () => {
  render(<ArtworkCard artwork={makeArtwork({ sold_count: 3 })} />);
  expect(screen.getByText(/3 vendues/)).toBeInTheDocument();
});
it("masque le badge vendues si sold_count est 0", () => {
  render(<ArtworkCard artwork={makeArtwork({ sold_count: 0 })} />);
  expect(screen.queryByText(/vendues/)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Vérifier l'échec** — Run: `npx vitest run src/components/social-counts.test.tsx src/components/artwork-card.test.tsx` → FAIL

- [ ] **Step 3: Implémenter** — `social-counts.tsx` (icônes SVG inline, `text-text/60`,
  seuil d'affichage `viewCount + favoriteCount > 0`) ; `makeArtwork` de test : initialiser
  `favorite_count: 0, sold_count: 0, views_7d: 0, artist_verified: false` (les fixtures TS
  doivent rester complètes pour `tsc`) ; intégrer `SocialCounts` **dans la carte** (après
  `PriceTag`) + badge « N vendues » dans la carte ; sur la **fiche œuvre** : span inline
  `👁 {view_count} vues` (masqué si 0) à côté du prix, badge « N vendues » et mention
  « Pièce unique — déjà vendue » (`is_unique_piece && sold_count >= 1`, `ink-danger`) —
  le ♡ arrive en Task 7 via `FavoriteButton`.

- [ ] **Step 4: Vérifier le passage** — Run: idem Step 2 → PASS ; `npx vitest run` → verts

- [ ] **Step 5: Gates** — `npx oxlint src && npx tsc --noEmit && npm run build`

- [ ] **Step 6: Commit** — `Social proof: view favorite and sold counters on cards and detail`

---

### Task 7: Bouton favori ♡ (backend `is_favorited` + frontend)

**Files:**
- Modify : `backend/apps/catalogue/serializers.py` (`ArtworkDetailSerializer.is_favorited`),
  `frontend/src/lib/api.ts` (`toggleFavorite` corrigé + type), Create :
  `frontend/src/components/favorite-button.tsx`, Modify : `frontend/src/app/oeuvre/[slug]/page.tsx`
- Test : `backend/apps/catalogue/tests/test_api_public.py`, `frontend/src/components/favorite-button.test.tsx`

**Interfaces:**
- Produits : `ArtworkDetailSerializer.is_favorited : bool` (false si anonyme ;
  `obj.favorited_by.filter(user=request.user).exists()` via le `request` du context) ;
  `toggleFavorite(artworkId: number)` → `apiFetch(\`/catalog/artworks/${artworkId}/favorite/\`, { method: "POST" })`
  (**URL corrigée** : l'actuelle `/catalog/artworks/favorite/` est fausse — il manque l'id) ;
  `<FavoriteButton artworkId initialFavorited initialCount />` — cœur + compteur, état
  optimiste ; `aria-label` **exact** : `"Ajouter aux favoris"` ou `"Retirer des favoris"`
  (selon l'état) — les tests s'appuient sur ces libellés

- [ ] **Step 1: Test backend échouant** — dans `test_api_public.py` classe `TestIsFavorited` :

```python
def test_detail_is_favorited_false_anonymous(self, client, artwork_factory):
    art = artwork_factory(status=ArtworkStatus.PUBLISHED)
    assert client.get(detail(art.slug)).json()["is_favorited"] is False

def test_detail_is_favorited_true_after_toggle(self, client, user, artwork_factory):
    art = artwork_factory(status=ArtworkStatus.PUBLISHED)
    client.force_authenticate(user=user)
    client.post(f"/api/v1/catalog/artworks/{art.pk}/favorite/")
    assert client.get(detail(art.slug)).json()["is_favorited"] is True
```

- [ ] **Step 2: Vérifier l'échec** — Run: `uv run pytest apps/catalogue/tests/test_api_public.py -k IsFavorited -v` → FAIL

- [ ] **Step 3: Implémenter backend** — `is_favorited = serializers.SerializerMethodField()`
  sur `ArtworkDetailSerializer` ; méthode : `request = self.context.get("request")`,
  anonyme → False ; ajouter `"is_favorited"` aux `fields` du détail. → PASS + file catalogue verte.

- [ ] **Step 4: Tests frontend échouants** — `favorite-button.test.tsx`
  (**piège connu : le mock `useRouter` doit renvoyer un objet stable**,
  `const router = { push, replace }` hors du mock) :

```tsx
it("bascule le cœur en optimiste quand connecté", async () => {
  // spy toggleFavorite → mockResolvedValue({ favorited: true })
  render(<FavoriteButton artworkId={1} initialFavorited={false} initialCount={0} />);
  await user.click(screen.getByRole("button", { name: "Ajouter aux favoris" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Retirer des favoris" })).toBeInTheDocument(),
  );
  expect(screen.getByText("1")).toBeInTheDocument();
});
it("retire des favoris quand c'était déjà favori", async () => {
  // spy toggleFavorite → mockResolvedValue({ favorited: false })
  render(<FavoriteButton artworkId={1} initialFavorited initialCount={3} />);
  await user.click(screen.getByRole("button", { name: "Retirer des favoris" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Ajouter aux favoris" })).toBeInTheDocument(),
  );
  expect(screen.getByText("2")).toBeInTheDocument();
});
it("redirige vers la connexion si anonyme (401)", async () => {
  // spy toggleFavorite → mockRejectedValue(new ApiError(...)) avec status 401
  render(<FavoriteButton artworkId={1} initialFavorited={false} initialCount={0} />);
  await user.click(screen.getByRole("button", { name: "Ajouter aux favoris" }));
  await waitFor(() =>
    expect(router.replace).toHaveBeenCalledWith(expect.stringContaining("/connexion?next=")),
  );
});
```

(même motif que `add-to-cart-button.tsx` pour le 401 : `err instanceof ApiError && err.status === 401`
→ `router.replace(\`/connexion?next=${encodeURIComponent(pathname)}\`)` avec `usePathname`.)

- [ ] **Step 5: Implémenter le frontend** — corriger `toggleFavorite` (URL avec `{id}`) ;
  composant `favorite-button.tsx` (état local `favorited`/`count`, clic → si 401 rediriger,
  sinon appeler et basculer, erreur réseau → retour à l'état initial) ; monter sur la fiche
  œuvre **à côté du span `👁 N vues`** de la Task 6 (le bouton porte le compteur ♡ —
  `SocialCounts` ne sert que sur les cartes, aucun doublon d'état).

- [ ] **Step 6: Vérifier le passage + gates** — `npx vitest run && npx oxlint src && npx tsc --noEmit && npm run build` ; `uv run pytest apps/catalogue/tests/ -q`

- [ ] **Step 7: Commit** — deux commits : `Social proof: expose is_favorited on artwork detail` (backend), `Social proof: favorite heart button on artwork page` (frontend)

---

### Task 8: Tendances — frontend (tri catalogue + section accueil)

**Files:**
- Create : `frontend/src/components/trending-section.tsx`
- Modify : `frontend/src/app/catalogue/page.tsx` (option de tri), `frontend/src/app/page.tsx` (fetch + section)
- Test : `frontend/src/components/trending-section.test.tsx`

**Interfaces:**
- Consumes : `listCatalogue({ sort: "trending", ... })` (le paramètre `sort` existe déjà
  dans `CatalogFilters` et `buildCatalogQuery`), champs `views_7d`/compteurs — Task 5/6
- Produits : `<TrendingSection artworks={ArtworkSummary[]} />` — composant présentatif
  (titre « Tendances », grille de 8 cartes avec badge « 🔥 N vues / 7 j » via `views_7d`,
  lien « Voir tout → /catalogue?sort=trending »)

- [ ] **Step 1: Test échouant** — `trending-section.test.tsx` (helper local `makeArtwork`
  copié de `artwork-card.test.tsx`, avec les nouveaux champs à 0) :

```tsx
it("affiche le titre, les cartes et le lien vers le tri", () => {
  render(<TrendingSection artworks={[makeArtwork({ views_7d: 9 }), makeArtwork({ id: 2, slug: "b", title: "Œuvre 2", views_7d: 4 })]} />);
  expect(screen.getByRole("heading", { name: "Tendances" })).toBeInTheDocument();
  expect(screen.getByText(/9 vues/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /voir tout/i })).toHaveAttribute("href", "/catalogue?sort=trending");
});
```

- [ ] **Step 2: Vérifier l'échec** — Run: `npx vitest run src/components/trending-section.test.tsx` → FAIL

- [ ] **Step 3: Implémenter le composant** — réutilise `ArtworkCard` ; le badge « N vues / 7 j »
  est rendu dans la section (au-dessus de la grille ou en overlay sur la carte via une prop
  optionnelle `views7d` de `ArtworkCard` — **choix du builder**, le plus simple sans
  casser les tests existants de la carte).

- [ ] **Step 4: câbler les pages** — `catalogue/page.tsx` : ajouter
  `<option value="trending">Tendances (7 jours)</option>` dans le select ; `app/page.tsx` :
  `listCatalogue({ sort: "trending", page: "1" }).then(p => p.results.slice(0, 8)).catch(() => [])`
  et rendre `<TrendingSection>` entre le hero et les catégories (masquer si vide).

- [ ] **Step 5: Vérifier le passage + gates** — `npx vitest run && npx oxlint src && npx tsc --noEmit && npm run build`

- [ ] **Step 6: Commit** — `Social proof: trending section on homepage and catalogue sort`

---

### Task 9: Page artiste enrichie — frontend

**Files:**
- Modify : `frontend/src/lib/api.ts` (type `ArtistPublicDetail` + `stats`),
  `frontend/src/app/artistes/[slug]/page.tsx`
- Create : `frontend/src/components/artist-stats.tsx`
- Test : `frontend/src/components/artist-stats.test.tsx`

**Interfaces:**
- Consumes : `stats {works, sold, views, favorites}` — Task 5 ; `is_verified` — Task 1
- Produits : `<ArtistStats stats={...} />` — ligne « 14 œuvres · 3 vendues · 1 200 vues · 45 ♡ »
  (formatage : `Intl.NumberFormat("fr-FR")` pour les grands nombres)

- [ ] **Step 1: Test échouant** :

```tsx
it("affiche les quatre statistiques au format français", () => {
  render(<ArtistStats stats={{ works: 14, sold: 3, views: 1200, favorites: 45 }} />);
  expect(screen.getByText(/14 œuvres/)).toBeInTheDocument();
  expect(screen.getByText(/3 vendues/)).toBeInTheDocument();
  expect(screen.getByText(/1[\u202f\u00a0]200 vues/)).toBeInTheDocument(); // espace fine insécable
  expect(screen.getByText(/45/)).toBeInTheDocument();
});
it("pluriel correct à 0 et 1", () => { /* œuvre/œuvre, vue/vue, vente/vente */ });
```

(même piège RTL que `formatXAF` : normaliser les espaces insécables des deux côtés.)

- [ ] **Step 2: Vérifier l'échec** — Run: `npx vitest run src/components/artist-stats.test.tsx` → FAIL

- [ ] **Step 3: Implémenter + intégrer** — remplacer la ligne
  `{artist.artwork_count} œuvre(s) publiée(s)` de l'en-tête par `<ArtistStats>` ;
  le badge ✓ Task 2 est déjà dans l'en-tête.

- [ ] **Step 4: Vérifier le passage + gates** — `npx vitest run && npx oxlint src && npx tsc --noEmit && npm run build`

- [ ] **Step 5: Commit** — `Social proof: enriched artist profile stats line`

---

### Task 10: Seed de démonstration `seed_social`

**Files:**
- Create : `backend/apps/catalogue/management/commands/seed_social.py`
- Test : `backend/apps/catalogue/tests/test_seed_social.py`

**Interfaces:**
- Consumes : `ArtworkView`, `Favorite`, `make_order`-like construction, `apps.commerce.services.mark_paid`
- Produits : `uv run python manage.py seed_social` — idempotent, **skip silencieux (exit 0) si
  `ArtworkView.objects.exists()`** ; crée ses **comptes démo** si absents (upsert :
  `viewer.demo1..5@example.test`, acheteur `d1buyer@artflow.test` — mot de passe
  `D1Smoke!Pass2026`, jamais affiché) ; ~50 vues réparties sur les 7 derniers jours
  (`created_at` daté explicitement — d'où le `default=timezone.now` du modèle) sur **toutes**
  les œuvres `PUBLISHED` disponibles (2 suffisent), synchronise `view_count` ;
  ~15 favoris récents (5 users × 3 œuvres) + 3 anciens ; et **1 commande `PAID`** :
  construit Order `PENDING_PAYMENT` + OrderItem + StockReservation + Payment
  (miroir exact de `make_order` dans `backend/apps/conftest.py`) sur `d1buyer`, puis
  `mark_paid(order)` (les services font la conversion → stock sold, ledger)

- [ ] **Step 1: Test échouant** — `test_seed_social.py` (imports : `pytest`,
  `django.core.management.call_command`, `ArtworkView`/`Favorite`/`Artwork`/`ArtworkStatus`
  depuis `apps.catalogue.models`, `Order` depuis `apps.commerce.models`) :

```python
@pytest.mark.django_db
def test_seed_social_creates_and_is_idempotent(artwork_factory):
    artwork_factory(status=ArtworkStatus.PUBLISHED, stock=5)
    artwork_factory(status=ArtworkStatus.PUBLISHED, stock=5)
    call_command("seed_social")
    v1 = ArtworkView.objects.count()
    f1 = Favorite.objects.count()
    assert v1 >= 40 and f1 >= 10 and Order.objects.filter(status=Order.Status.PAID).count() == 1
    art = Artwork.objects.filter(view_count__gt=0).first()
    assert art.view_count == ArtworkView.objects.filter(artwork=art).count()
    call_command("seed_social")  # re-run : skip silencieux
    assert ArtworkView.objects.count() == v1 and Favorite.objects.count() == f1
    assert Order.objects.count() == 1
```

- [ ] **Step 2: Vérifier l'échec** — Run: `uv run pytest apps/catalogue/tests/test_seed_social.py -v` → FAIL (CommandError : unknown command)

- [ ] **Step 3: Implémenter** — dates via `timezone.now() - timedelta(days=i % 7, hours=…)`
  passées à `ArtworkView(created_at=…)` (modèle en `default=timezone.now`), `viewer_key =
  f"seed-{i:03d}"` ; upsert des comptes démo (User + `set_password`) puis vues/favoris
  distribués parmi eux ; œuvres = `Artwork.objects.filter(status=PUBLISHED)` (si 0 →
  message « aucune œuvre publiée » + sortie 0) ; `artwork.view_count` recalculé à la fin ;
  commande `PAID` sur `d1buyer@artflow.test` via la construction miroir de `make_order` +
  `mark_paid`.

- [ ] **Step 4: Vérifier le passage** — Run: idem Step 2 → PASS ; ruff ;
  smoke manuel : `uv run python manage.py seed_social` deux fois sur la BDD dev.

- [ ] **Step 5: Commit** — `Social proof: seed_social demo data (views favorites paid order)`

---

### Task 11: Gates complets + smoke E2E + docs + mémoire

**Files:**
- Create : `/tmp/opencode/smoke_social.py` (modèle : `/tmp/opencode/smoke_d3.py` du prélude)
- Modify : `docs/api.md` (endpoint `view/`, champs `favorite_count`/`sold_count`/`views_7d`/`artist_verified`/`is_verified`/`is_favorited`/`stats`, `sort=trending`), `docs/database.md` (`ArtworkView`, `view_count`), `docs/screens.md` (compteurs/badges/section Tendances), `MEMORY.md`
- Modify : `docs/superpowers/specs/2026-11-09-kwossimboa-social-proof-design.md` (cocher l'état « livré »)

**Scénarios smoke (~30 checks, via proxy :5175)** : `seed_social` → GET catalogue :
`favorite_count`/`sold_count`/`artist_verified` présents ; POST `view/` 200 `counted:true`
puis re-POST `counted:false` (cookie) ; `?sort=trending` 200 ; login `d1buyer@artflow.test` →
fiche œuvre `is_favorited:false` → toggle favori 201 → re-GET `is_favorited:true` →
re-toggle 200 false ; page artiste 200 avec `stats` cohérents ; pages HTML `/`,
`/catalogue?sort=trending`, `/oeuvre/{slug}`, `/artistes/{slug}` 200 ; badge vérifié présent
dans le HTML du catalogue.

- [ ] **Step 1: Gates complets** — backend (pytest exit 0 + ruff + makemigrations --check) ;
  frontend (oxlint 0 + tsc 0 + vitest verts + build 20 routes) ; `migrate` à jour
- [ ] **Step 2: Smoke** — écrire et exécuter `smoke_social.py` → 100 % ; corriger le code si échec réel
- [ ] **Step 3: Docs** — api.md, database.md, screens.md ; design doc mis à jour (statut livré)
- [ ] **Step 4: Mémoire + rapport** — `MEMORY.md` (section ARTFlow : itération livrée + pièges,
  entrée historique du jour) ; rapport §27 présenté dans le chat (lignes du cahier des charges
  concernées + backlog : bouton Soutenir, purge vues, page « Mes favoris »)
- [ ] **Step 5: Commit** — `docs: social proof iteration status + smoke`
