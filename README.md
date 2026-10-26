# ArtFlow

Marketplace multi-artistes camerounaise : découverte et vente d'œuvres d'art (peintures, sculptures, artisanat, contemporain) en **XAF**, commission **10 %**, approbation manuelle des artistes, expéditions par vendeur, paiement **Mobile Money** (MTN MoMo / Orange Money via CamPay — étude Phase A).

> **Statut : Phase A (conception) — aucun code applicatif pour l'instant.**
> Aucune fonctionnalité n'est « disponible » tant qu'elle n'est pas implémentée et testée.

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

## Prochaines étapes (après validation Phase A)

1. **Phase B** — Fondation : `frontend/` (Next.js 16), `backend/` (Django 6.1 + DRF), Postgres Docker, CI, tests de base.
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

## Licences des données de démo

Tout média de démo sera tracé dans un manifeste (`docs/media-manifest.csv`) avec source, auteur, licence et date de vérification — aucune image d'artiste réel sans droits.

---

Les mentions de conformité juridique sont absentes volontairement : les politiques sont des brouillons à valider par un juriste compétent avant tout lancement (voir Phase F).
