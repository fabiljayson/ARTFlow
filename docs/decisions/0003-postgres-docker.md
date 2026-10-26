# ADR-0003 : PostgreSQL en conteneur Docker dédié

- **Statut** : accepté (Phase A, validation commanditaire)
- **Contexte** : serveur Postgres 18 local déjà partagé avec d'autres projets ; disque limité (8 Go libres).
- **Décision** : conteneur `artflow-postgres` (image `postgres:18-alpine`, déjà présente localement), port dédié (ex. `5435`), volume nommé `artflow-pgdata`.
- **Conséquences** : isolation totale ; `docker compose up` dans `infrastructure/` ; sauvegardes via `pg_dump` dans le conteneur ; attention disque — volume initialisé à la première migration (~50 Mo).
