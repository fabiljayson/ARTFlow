# ArtFlow

Marketplace multi-artistes camerounaise : découverte et vente d'œuvres d'art (peintures, sculptures, artisanat, contemporain) en **XAF**, commission **10 %**, approbation manuelle des artistes, expéditions par vendeur, paiement **Mobile Money** (MTN MoMo / Orange Money via CamPay — étude Phase A).

> **Statut : Phase B (fondation) — socle livré : backend Django, frontend Next.js, Postgres Docker, CI.**
> Aucune fonctionnalité métier n'est « disponible » tant qu'elle n'est pas implémentée et testée (Phase C+).

## Documentation

| Document | Contenu |
|---|---|
| [docs/requirements.md](docs/requirements.md) | Exigences fonctionnelles et critères d'acceptation |
| [docs/architecture.md](docs/architecture.md) | Vue d'ensemble, stack, monorepo, flux |
| [docs/database.md](docs/database.md) | Modèle de données champ-par-champ |
| [docs/api.md](docs/api.md) | Contrats d'API (pré-OpenAPI) |
| [docs/payments.md](docs/payments.md) | CamPay, webhooks, idempotence, remboursements |
| [docs/media.md](docs/media.md) | Images/vidéos, licences, hébergement |
| [docs/security.md](docs/security.md) | Plan de sécurité et matrice de risques |
| [docs/testing.md](docs/testing.md) | Stratégie de tests |
| [docs/screens.md](docs/screens.md) | Description des écrans |
| [docs/design.md](docs/design.md) | Design system appliqué |
| [docs/decisions/](docs/decisions/) | Décisions d'architecture (ADR) |
| [DESIGN.md](DESIGN.md) | Tokens et règles visuelles (source de vérité design) |

## Prochaines étapes (après validation Phase B)

1. ~~**Phase B** — Fondation~~ : **livrée** (backend Django + frontend Next.js + Postgres Docker + CI).
2. **Phase C** — Identité, candidatures, catalogue, médias.
3. **Phase D** — Commerce, paiements (compte CamPay à créer avec validation).
4. **Phase E** — Expéditions, litiges, remboursements, notifications.
5. **Phase F** — Politiques juridiques (brouillons FR/EN à faire valider par un juriste).
6. **Phase G** — Validation, perf, déploiement.

## Prérequis (Phase B+)

- Python ≥ 3.12 + [uv](https://docs.astral.sh/uv/)
- Node.js ≥ 22 + npm
- Docker (PostgreSQL 18)
- ffmpeg (outillage média, optionnel dev)

## Démarrage (Phase B)

Ports : **Postgres 5435**, **API 8003**, **web 5175** (choisis libres).

```bash
# 1. Base de données (conteneur artflow-postgres)
docker compose -f infrastructure/docker-compose.yml up -d --wait

# 2. Backend (Django + DRF)
cd backend
uv sync
cp .env.example .env   # puis ajuster si besoin
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8003

# 3. Frontend (Next.js) — autre terminal
cd frontend
npm install
npm run dev            # http://127.0.0.1:5175 (proxy /api → 8003)
```

Vérifications :

```bash
cd backend && uv run python -m pytest && uv run ruff check .
cd frontend && npm test -- --run && npx tsc --noEmit && npm run build
```

## Licences des données de démo

Tout média de démo sera tracé dans un manifeste (`docs/media-manifest.csv`) avec source, auteur, licence et date de vérification — aucune image d'artiste réel sans droits.

---

Les mentions de conformité juridique sont absentes volontairement : les politiques sont des brouillons à valider par un juriste compétent avant tout lancement (voir Phase F).
