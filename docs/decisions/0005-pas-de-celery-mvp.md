# ADR-0005 : Pas de Celery/Redis au MVP

- **Statut** : accepté (Phase A)
- **Contexte** : le prompt autorise l'async « si réellement nécessaire ».
- **Décision** : **outbox en base** (`notification_outbox`) + **management commands cron** (expiration réservations toutes les 5 min, envois e-mails bornés, rappels). Redis/Celery reportés à une charge réelle.
- **Conséquences** : moins d'infra (disque/RAM) ; latence d'envoi = fréquence cron (acceptable MVP) ; pattern outbox conservé pour migrer vers Celery sans refonte métier.
