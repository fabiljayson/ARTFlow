# ADR-0006 : Montants en XAF entiers + commission floor

- **Statut** : accepté (Phase A)
- **Contexte** : XAF a zéro décimale ; les erreurs d'arrondi financiers sont un risque prioritaire.
- **Décision** : tous les montants en `BigInteger` entiers ; commission = `floor(price × qty × bps / 10000)` (arrondi inférieur, favorise l'artiste d'au plus 1 XAF) ; taux **figé par ligne de commande** ; ledger append-only.
- **Conséquences** : table de vérité de 20 cas en tests ; interdiction des `FloatField` monétaires (revue de code) ; formatage `Intl.NumberFormat` zéro décimale côté front.
