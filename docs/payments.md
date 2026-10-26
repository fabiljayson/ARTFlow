# ArtFlow — Paiements

> Phase A. Prestataire retenu à l'étude : **CamPay** (ADR-0004). Intégration réelle en Phase D après création de compte (délégation requise). Pendant le développement : `MockPaymentGateway`.

## 1. CamPay — fiche technique (sources : campay.net, SDK officiel campay/pypi, docs Postman)

| Élément | Constat | Source |
|---|---|---|
| Réseau | MTN MoMo + Orange Money Cameroun | campay.net FAQ |
| Devise | **XAF** | SDK officiel |
| Environnements | `demo.campay.net` (sandbox) + `www.campay.net` (live) | campay.net |
| Auth API | token d'accès via username/password **ou** token permanent (application) | docs Postman |
| Flux encaissement | Request Payment → référence → client reçoit USSD push → **statut** | SDK |
| Statuts | `PENDING` (défaut) → `SUCCESSFUL` / `FAILED` | SDK officiel |
| Vérification statut | `GET` Transaction Status par référence (polling serveur) | docs Postman |
| Webhook | endpoint « Webhook or Callback » configurable ; clé webhook présente dans l'écosystème | docs Postman, campay-js |
| Liens de paiement | API `get_payment_link` (alternative au push direct) | SDK |
| Payouts (vers vendeurs) | **Mass Payout Request + Status** disponibles | docs Postman |
| Solde | `Get Application Balance` | docs Postman |
| Frais | **2 % encaissement**, **1 % retrait MoMo**, 5 000 XAF virement bancaire | campay.net pricing |
| Versement fonds | « dès le jour ouvré suivant » (wallet → bank/MoMo) | campay.net |
| SDK | Python officiel `campay` (PyPI) — **réévaluation** : nous codons notre adaptateur HTTP direct (contrôle idempotence/signature) sans dépendre du SDK |
| Adresse | Yaoundé, Biyem-Assi ; support WhatsApp | campay.net |

### 1.1 Points non vérifiés (à trancher à la création du compte sandbox — Phase D)
1. **Signature exacte des webhooks** (schéma, en-tête, canonicalisation) — le code rejettera tout webhook non vérifié.
2. **API remboursement** : **aucun endpoint refund visible** dans la documentation publique → impact : remboursements exécutés en **mode manuel** (dashboard CamPay) avec enregistrement `execution_mode=MANUAL_DASHBOARD` + preuve ; si une API apparaît, bascule `API`.
3. Montants : certains SDK montrent `amount` numérique ; l'erreur `ER201` signale un contrôle décimal → notre code envoie **entiers XAF en texte sans décimale**.
4. Limits de transaction / KYC marchand / compte vérifié : conditions à lire dans les CGV (PDF campay.net) **avant** intégration live.
5. Fréquence/latence USSD push et codes opérateur (`MTN`/`ORANGE` exacts) : validés en sandbox.

## 2. Architecture d'intégration

```
checkout ──► OrderService.create()  [transaction]
                │  réservations stock
                │  Payment.objects.create(status=CREATED)
                ▼
        PaymentGateway.initiate()  ──► CamPay PENDING
                │
        acheteur : push USSD / lien
                │
   ┌────────────┴────────────┐
   ▼                         ▼
Webhook signé            Polling secours
(verif signature)        (cron toutes les 2 min,
   │                     max N polls/payment)
   └────────► PaymentEvent(event_id unique) ◄──────┘
                     │ idempotent
                     ▼
        si SUCCEEDED → Order PAID + ledger + convert. réservation
        si FAILED/EXPIRED → libération stock + politique retry
```

### 2.1 Règles d'or
1. **Jamais** de confirmation sur redirection navigateur (pas de `?success=` fiable).
2. Chaque notification externe devient une ligne `payment_events` avec `event_id` **unique** → rejeu = HTTP 200 + no-op.
3. Le montant CamPay doit être **strictement égal** au `order.grand_total_xaf` sinon rejet + alerte.
4. Une transition `payments.status` n'a lieu que dans `PaymentService.apply_status()` (machine à états + journal).
5. `external_reference` = notre `payment.uuid` → corrélé sans ambiguïté.
6. Secrets : `CAMPAY_USERNAME`, `CAMPAY_PASSWORD` (ou `CAMPAY_APP_TOKEN`), `CAMPAY_WEBHOOK_SECRET` en variables d'env, jamais en base ni en git.

### 2.2 Machine à états paiement
```
CREATED → PENDING → SUCCEEDED
                  → FAILED → (nouvelle tentative = nouveau Payment)
                  → EXPIRED
CREATED/PENDING → CANCELLED (annulation utilisateur avant push)
SUCCEEDED → terminal (remboursements via table refunds, pas de statut retro)
```
Transitions illégales = erreur 409 loggée + alerte.

### 2.3 Expiration et libération stock
- Réservation : TTL 30 min (`platform_settings`).
- Cron `expire_stock_reservations` : `ACTIVE` + `expires_at < now` → `EXPIRED` + libération + notification + commande `CANCELLED` si jamais payée.
- Payment `PENDING` > TTL : passage `EXPIRED` + webhook de confirmation perdu → si webhook tardif `SUCCESSFUL` **après** expiration : politique = accepter le paiement (l'argent est encaissé !) → commande `PAID` + stock vendu (peut créer stock négatif **jamais** : vente possible en négatif **interdite**, donc si stock insuffisant → litige manuel signalé finance). **Décision** : empêcher l'expiration payment tant que le webhook n'a pas tranché (TTL payment = TTL réservation + marge 15 min) pour réduire le cas.

## 3. Commission et calculs (rappel des règles testées)

| Concept | Règle |
|---|---|
| Assiette commission | `unit_price_xaf × quantity` (**pas** la livraison, **pas** les frais) |
| Taux | 1000 bps (10 %), figé par ligne |
| Arrondi | `floor()` — commission entière inférieure |
| Exemple | 100 000 XAF → commission 10 000 → artiste 90 000 |
| Exemple arrondi | 999 XAF → commission 99 (floor 99.9) → artiste 900 |
| Total commande | Σ lines + Σ shipping (par vendeur) + fees |
| Anciennes commandes | jamais recalculées avec le taux courant |

Tests obligatoires : table de vérité sur 20 cas (0, 1, 999, 1000, 3333, 999999, multi-qty, multi-vendeur, arrondi, refund partiel).

## 4. Remboursements (MVP)

1. Acheteur demande (ou admin) → `refunds REQUESTED`.
2. Admin/finance approuve/refuse (motif obligatoire).
3. Si approuvé : exécution **manuelle CamPay dashboard** (jusqu'à preuve d'API) → saisie référence transaction → `CONFIRMED` + `payment_events` + ledger `REFUND_ADJUSTMENT` + notification.
4. Contrainte : Σ refunds ≤ encaissé ; **zéro** double exécution (garde statut + audit).
5. Litige faveur acheteur : remboursement plein montant des lignes concernées (partiel possible) + shipment concerné suivi séparément.

## 5. MockPaymentGateway (dev/CI)

- Endpoints internes de test : simulateur avec scénarios paramétrables (`success`, `fail`, `timeout`, `webhook_lost_then_late`, `duplicate_webhook`).
- Signature factée mais **réelle** (HMAC) pour exercer le code de vérification.
- Aucune dépendance réseau → CI déterministe.
- En staging : bascure `PAYMENT_PROVIDER=campay` + sandbox keys.

## 6. Coûts et marge (indicatif, à revalider tarifs CamPay)

Pour 100 000 XAF d'œuvre : encaissement CamPay ≈ 2 % = 2 000 XAF. La commission ArtFlow 10 % (10 000) **ne couvre pas** les frais CamPay si elle était intégralement reversée… Modèle : la commission 10 % inclut la couverture des frais de paiement (règle produit : l'artiste reçoit 90 % net, les frais opérateur sont à la charge d'ArtFlow). **Hypothèse à valider avec le commanditaire** (écrit dans le cahier des charges : « part de l'artiste avant frais de paiement » = 90 % — conforme).

## 7. Checklists Phase D

- [ ] Compte sandbox CamPay créé (validation humaine)
- [ ] Documentation webhook réelle lue + tests de signature codés
- [ ] CGV CamPay lues (remboursements, limits, KYC)
- [ ] Parcours sandbox E2E : push → SUCCESSFUL → commande PAID
- [ ] Scénarios : échec, rejeu webhook ×3, webhook perdu + poll, expiration, montant erroné
- [ ] Mode prod désactivé sans double confirmation (`PAYMENTS_ACCEPT_LIVE=false` par défaut)
