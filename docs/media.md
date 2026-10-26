# ArtFlow — Médias (images & vidéos)

> Phase A. Règles du prompt §12–13 appliquées intégralement.

## 1. Principes

1. Les fichiers **utilisateurs** (artistes) et les fichiers **démo** sont traités différemment.
2. Tout fichier : validation type **réel** (magic bytes), taille max, nom généré sûr (`uuid.ext`), stockage hors webroot.
3. Documents de vérification : **privés définitivement**.
4. Jamais d'image de stock présentée comme œuvre réelle ; jamais d'attribution d'œuvre fictive à un artiste réel (démo = comptes fictifs `*@example.test`, badges « démo »).
5. **Manifeste** obligatoire pour chaque média démo (`docs/media-manifest.csv` créé en Phase B/C au premier seed).

## 2. Sources de médias de démo (licences)

| Source | Usage prévu | API | Licence | Notes |
|---|---|---|---|---|
| Unsplash | images œuvres démo | API + clé env | Unsplash License (usage démo gratuit, pas de revente « comme photo de quelqu'un ») | clé serveur, rate-limit respectée |
| Pexels | images **et vidéos** démo | API + clé env | Pexels License | idem |
| Pixabay | images/vidéos | API | Pixabay Content License | idem |
| Wikimedia Commons | images domaine public / CC | API | varie (CC0/BY/…) | **attribution** si CC BY — ligne manifeste obligatoire |
| Openverse | agrégateur CC | API | varie | vérifier licence source |

**Règles API** : quotas respectés ; pas de scrape ; clés dans `.env` serveur ; le seed télécharge **au maximum N fichiers** (borné, une fois) puis commit **uniquement si la licence le permet** — sinon chargement à la volée via URL API du fournisseur (pas de copie dans le dépôt). Chaque média démo ⇒ ligne manifeste : `filename, source, source_url, author, license, license_url, attribution, verified_at, intended_use`.

## 3. Hébergement vidéo des artistes

| Option | Modèle | Pour ArtFlow | Coût indicatif (à confirmer) | Décision |
|---|---|---|---|---|
| **Stockage dev local** (MVP dev) | fichiers serveur, player HTML5, transcoding ffmpeg local pour démo | démo uniquement | 0 | **Oui Phase B–D (dev)** |
| **Cloudflare Stream** | $/min stockage + diffusion, upload direct, webhooks, URLs signées, player | production | ~5 $/1000 min stock + 1 $/1000 min diffusion | Candidat n°1 |
| **Mux** | idem, excellent player | production | payant, essai limité | Candidat n°2 |
| **Cloudinary** | free tier puis usage ; images+vidéo | polyvalent | free tier généreux | Candidat n°3 (si images aussi) |

**Recommandation** : MVP dev = local ; décision fournisseur managé **avant Phase E** (compte payant = validation commanditaire). L'interface `VideoProvider` (upload status, playback url signée, poster) est prévue dès la Phase C pour brancher sans refonte.

### 3.1 Flux vidéo artiste (cible)
1. Artiste upload vidéo (mp4/mov, taille max configurable).
2. Backend : validation → mise en file (outbox) → transfert vers provider → statut `PROCESSING` → webhook provider → `READY` (+ poster auto).
3. Fil vidéo public : lecture **différée** (IntersectionObserver), muet par défaut, sous-titres/titre artiste, lien œuvre si FK existe.
4. Échec provider → statut `FAILED` + fallback image poster + re-tentative bornée.

## 4. Politique fichiers utilisateurs

| Règle | Valeur défaut (config) |
|---|---|
| Images acceptées | jpeg, png, webp (magic bytes) |
| Taille image max | 10 Mo |
| Images/œuvre | 10 |
| Vidéos acceptées | mp4, webm, mov |
| Taille vidéo max | 200 Mo (dev local) / selon provider |
| Vidéos/œuvre | 1 |
| Documents vérification | pdf, jpeg, png — 10 Mo — **privé** |
| Noms | stockés sous `uuid.<ext>` ; `original_filename` affiché seulement aux admins |
| Suppression | soft-delete + cleanup cron des blobs orphelins |

## 5. Miniatures et performance

- Images : Pillow → thumbnails (400 px, 1200 px) WebP (+ fallback JPEG), `srcset` côté front.
- Vidéo : poster obligatoire avant lecture ; `preload="none"` ; `playsinline` ; pas d'autoplay sonore.
- CDN en prod (optionnel) pour images publiques uniquement ; documents privés **jamais** via CDN public.

## 6. Modération média

- Œuvre en `IN_MODERATION` : médias visibles seulement par l'artiste + modérateur.
- Signalement (`content_reports`) peut masquer un média (`HIDDEN`) avec audit.
- Remplacement d'image principale après publication ⇒ ré-moderation (politique architecture).

## 7. Interdits

- Stocker vidéos volumineuses en BLOB PostgreSQL.
- Servir documents d'identité depuis le domaine public.
- Scraper des galeries/artistes réels.
- Prétendre qu'une vidéo de démo appartient à un artiste réel.
