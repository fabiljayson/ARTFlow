# ArtFlow — Sécurité

> Phase A. Plan de sécurité (prompt §15). Chaque risque : prévention / détection / réponse / test.

## 1. Fondations

| Domaine | Mesure |
|---|---|
| Transport | HTTPS strict en prod (HSTS), cookies `Secure` |
| Mots de passe | **Argon2id** (arghosh), politique longueur, jamais de log |
| Sessions | cookie `sessionid` HttpOnly, SameSite=Lax, rotation login/logout, expiration idle |
| CSRF | protection Django activée sur toutes les mutations ; front relaie token |
| CORS | **restrictif** : origine(s) front uniquement, credentials=true si besoin, méthodes limitées |
| Rate limiting | throttle DRF sur login, register, reset, checkout, webhook (scopes dédiés) |
| Validation | serializers DRF partout ; types/tailles fichiers ; regex téléphones CM |
| Injection | ORM Django uniquement (pas de SQL brut non paramétré) |
| XSS | React (échappement) + CSP `report-only` d'abord ; pas de `dangerouslySetInnerHTML` sans sanitizer (interdit au MVP sauf markdown assaini) |
| Secrets | `.env` gitignoré, `.env.example` documenté, rotation prochaine compromise |
| Dépendances | `pip-audit` + `npm audit` en CI (fail sur critical) ; Dependabot/Renovate |
| Erreurs | debug=False prod ; pages 404/500 génériques ; pas de stacktrace client |
| Logs | structurés ; redaction (phone, email partiel, zéro token/mot de passe) |
| Sauvegardes | pg_dump chiffré quotidiennement, rétention 30 j, **test de restauration trimestriel** (doc ops Phase G) |

## 2. Matrice de risques (prompt §15)

| # | Risque | Prévention | Détection | Réponse | Test |
|---|---|---|---|---|---|
| 1 | Modification prix côté navigateur | prix toujours recalculés serveur (quote + checkout) ; total server-side | alerte si montant provider ≠ order | annuler payment | test « client envoie price falsifié » |
| 2 | Lecture commande d'autre user | scoping queryset buyer=request.user | 404 logs anormaux | revoke session si pattern | test IDOR liste + détail |
| 3 | Modification œuvre d'autre artiste | permission owner-only + scoping | audit `artwork.update.denied` | — | test PATCH artiste B sur œuvre A → 404 |
| 4 | Faux webhook | signature HMAC (Mock réel / CamPay) + allowlist IP si provider le fournit | `signature_valid=false` count | 401 + alerte | test corps modifié, mauvaise clé |
| 5 | Double confirmation paiement | `payment_events.event_id` unique + machine à états | compteur duplicate | no-op 200 | test rejeu ×3 webhook identique |
| 6 | Double remboursement | contrainte statut + Σ refunds ≤ encaissé + audit | ledger incohérence check | rollback + alerte finance | test double approve refund |
| 7 | Vente multiple œuvre unique | transaction + `FOR UPDATE` + CHECK stock ≥ 0 + réservation TTL | métrique stock négatif (ne doit jamais arriver) | libération + priorité commandes | **test concurrence** (2 threads checkout) |
| 8 | Upload malveillant | magic bytes, antivirus ClamAV (prod, option Phase G), MIME allowlist, exécution impossible (hors webroot) | scan failures | quarantaine | test .php/.svg/exe rejetés ; polyglotte |
| 9 | Fuite documents privés | `PrivateMediaStorage` (url() → erreur), permissions admin, pas d'export front | audit vues documents | rotation accès + notification | test GET sans rôle → 404 |
| 10 | Compromission admin | MFA TOTP (Django-otp, Phase C si temps — sinon Phase F), moindre privilège, audit login, pas de mot de passe faible | logins échoués, IP nouvelles | disable compte + reset | test login rate-limit + lockout |
| 11 | Indisponibilité provider paiement | mode maintenance payments, statut error clair, pas de commande « payée » sans preuve | health check provider, alertes | communication + retry client | test provider down (mock 503) |
| 12 | Indisponibilité provider vidéo | poster fallback, statut FAILED média | webhook échec | re-upload proposer | test provider KO |
| 13 | Mauvais bucket storage | policies IaC/doc, pas de public-read par défaut, revue config | scan config | corriger + audit | check config staging |
| 14 | Fuite données perso | minimisation, écran RGPD (export/effacement Phase F), pas de PII dans logs | revue logs | procédure incident | test logs e2e sans email complet |

## 3. Permissions (matrice sommaire — spec dans `docs/api.md`)

| Ressource | Visiteur | Acheteur | Artiste | Modérateur | Admin | Finance |
|---|---|---|---|---|---|---|
| Catalogue publié | R | R | R | R | R | R |
| Panier/commandes | — | R (les siennes) | — | — | R all | R all (lecture) |
| Œuvres | R publiées | idem | CRUD les siennes | R tous + masquer | CRUD override | R |
| Candidatures | — | créer la sienne | lire la sienne | — | full | — |
| Documents vérif. | — | — | upload les siens | R (si perm modération artiste) | R | — |
| Litiges | — | ouvrir/répondre les siens | répondre les siens | review | full | R |
| Refunds | — | demander | — | — | approve | approve + execute |
| Ledger/payouts | — | — | résumé les ventes | — | R | full |
| Audit | — | — | — | R limité | R | R financiers |
| Settings plateforme | — | — | — | — | full | — |

## 4. Hardening Django (checklist implémentation)

- `DEBUG=False`, `ALLOWED_HOSTS` stricts, `SECURE_HSTS_SECONDS` prod.
- `SESSION_COOKIE_HTTPONLY`, `CSRF_COOKIE_SAMESITE=Lax`, `SECURE_SSL_REDIRECT` prod.
- `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.
- CSP (report-only d'abord) ; Permissions-Policy minimale.
- Upload handlers custom ; `DATA_UPLOAD_MAX_MEMORY_SIZE` borné.
- Admin Django : URL non devinée, MFA, 2FA, IP allowlist possible, pas de superuser quotidien.
- DRF : `EXCEPTION_HANDLER` maison (enveloppe d'erreur stable, pas de debug), pagination partout.
- Webhooks : route hors auth session, lecture body brut (bytes) pour HMAC, timeout client 10 s.

## 5. Conformité et limites

- **Aucune** certification (PCI-DSS côté serveur : on ne stocke jamais de données carte — MoMo uniquement ; le flux CamPay sort de notre périmètre de données sensibles carte).
- Données personnelles : conservation documentée dans la Privacy Policy (Phase F) ; hébergement possible hors Cameroun (hébergeur EU/US) ⇒ disclosure obligatoire.
- Les textes juridiques sont des **brouillons à faire valider par un juriste** — conformité jamais affirmée.

## 6. Tests de sécurité automatiques (CI)

1. Test permissions matrix (paramétré rôles × endpoints).
2. Test IDOR commandes/œuvres/litiges.
3. Test webhook signature (bonne/mauvaise/rejeu).
4. Test upload malveillant.
5. Test stock concurrent.
6. Test montant falsifié checkout.
7. Invariants config (settings de prod) style « security hardening tests » (rotation JWT N/A — sessions ; vérif cookies flags, HSTS staging, providers live off).
