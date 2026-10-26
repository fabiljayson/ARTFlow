# ADR-0004 : Prestataire de paiement CamPay (étude approfondie)

- **Statut** : accepté pour l'étude et le développement (Phase A) ; **intégration live conditionnée** à la création d'un compte (validation + KYC) en Phase D
- **Contexte** : marché Cameroun = MTN MoMo (~60 %) + Orange Money (~35 %) ; le MVP n'exige pas les cartes bancaires dès le départ.
- **Décision** : **CamPay** comme prestataire principal (MTN+Orange, XAF, sandbox dédiée, mass payouts pour les artistes, tarif 2 % encaissement / 1 % retrait). L'architecture utilise un **adaptateur** (`PaymentGateway`) avec `MockPaymentGateway` en dev/CI.
- **Points durs documentés** (`docs/payments.md`) : signature webhook à vérifier en sandbox ; **pas d'API remboursement visible** → exécution manuelle tracée (`MANUAL_DASHBOARD`) le temps d'une éventuelle API.
- **Alternatives** : Flutterwave/CinetPay (cartes) — réévaluées si le commanditaire exige les cartes bancaires au MVP ; intégration directe opérateurs (délais longs) — rejetée.
- **Conséquences** : frais opérateur à la charge d'ArtFlow dans la commission 10 % ; aucun compte créé sans accord ; `PAYMENTS_ACCEPT_LIVE=false` par défaut.
