# ArtFlow — Exigences et critères d'acceptation

> Phase A (conception). Source : PROMPT MAÎTRE ArtFlow. Toute évolution majeure exige une validation explicite du commanditaire.

## 1. Résumé produit

ArtFlow est une **marketplace multi-artistes** (Cameroun, devise XAF) permettant la découverte et la vente d'œuvres d'art (peintures, sculptures, artisanat, contemporain). Modèle : commission **10 %** sur le prix de l'œuvre (hors livraison/frais), **approbation manuelle des artistes** avant vente, **expéditions gérées par chaque artiste**, paiement **Mobile Money (MTN MoMo, Orange Money)** via **CamPay** (décision Phase A), MVP **web responsive FR**, applications natives hors périmètre.

## 2. Rôles

| Rôles | Capacités principales |
|---|---|
| Visiteur | Catalogue, recherche/filtres, vidéos publiques, pages artistes approuvés, inscription/connexion |
| Acheteur | Profil, adresses, panier, paiement, commandes, suivi, signalements, litiges, demandes de remboursement |
| Candidat artiste | Candidature, documents de vérification (privés), statut, corrections |
| Artiste approuvé | Œuvres (CRUD + médias + prix + stock), commandes/Expéditions, ventes/commissions dues, réponses litiges |
| Modérateur | Contenus signalés, approbation/masquage justifiés |
| Administrateur | Utilisateurs/rôles, candidatures, modération, catégories, commandes/paiements, litiges/remboursements, audit, paramètres |
| Opérations financières | Registres financiers, réconciliation, commissions, remboursements, payouts artistes — lecture + actions limitées, jamais d'altération d'historique |

Règle : le rôle affiché côté interface n'est **jamais** une preuve — toute autorisation est vérifiée côté serveur (principe du moindre privilège).

## 3. Exigences fonctionnelles (numérotées)

### EF-1 Accueil
- EF-1.1 Présentation, sélection d'œuvres, artistes en vedette, catégories, accès catalogue, fil vidéo, CTA acheter/devenir artiste, pied de page (légal + contact).
- EF-1.2 Performance : pas d'effets visuels ralentissant la navigation ; animations réduites si `prefers-reduced-motion`.

### EF-2 Catalogue
- EF-2.1 Affiche uniquement les œuvres `PUBLISHED` + approuvées ; jamais de données privées.
- EF-2.2 Recherche titre/artiste/mots-clés ; filtres catégorie, prix, disponibilité ; tri pertinence/date/prix ; pagination.
- EF-2.3 États : chargement, vide, erreur.

### EF-3 Fiche œuvre
- EF-3.1 Titre, images, vidéo, description, artiste + profil, catégorie, prix XAF, dimensions, matériaux, technique, date de création, disponibilité, infos livraison, conditions, similaires (si logique fiable).
- EF-3.2 Champs obligatoires définis de façon cohérente ; ne jamais fabriquer de valeurs.

### EF-4 Fil vidéo
- EF-4.1 Lecteur responsive, miniatures, lecture différée (hors écran = pas de vidéo), commandes accessibles, muet par défaut, titre + artiste, lien vers l'œuvre liée uniquement si relation vérifiée.
- EF-4.2 États chargement/échec/remplacement ; pas de téléchargement massif ; réduction des animations respectée.

### EF-5 Authentification
- EF-5.1 Inscription, connexion, déconnexion, réinitialisation mot de passe, vérification e-mail (si activée), profil, adresses, sessions, consentements contractuels (CGU versionnées).
- EF-5.2 Sessions cookie `httpOnly` + CSRF (décision Phase A, ADR-0002).

### EF-6 Candidature artiste
- EF-6.1 Statuts : `DRAFT`, `PENDING_REVIEW`, `NEEDS_INFO`, `APPROVED`, `REJECTED`, `SUSPENDED`.
- EF-6.2 Soumission, examen admin, acceptation/refus motivé, demande d'info complémentaire, suspension, traçabilité (audit).
- EF-6.3 Documents de vérification : stockage privé, accès admin uniquement.
- EF-6.4 Non approuvé ⇒ impossible de publier une œuvre à la vente.

### EF-7 Œuvres
- EF-7.1 Artiste approuvé : créer, modifier, médias, prix, stock, publier/dépublier selon règles.
- EF-7.2 Isolation stricte entre artistes (404/403 testé).
- EF-7.3 Modification majeure (prix > seuil, titre, médias principaux) ⇒ ré-moderation (politique documentée).

### EF-8 Panier et paiement
- EF-8.1 Panier : œuvres, sous-totaux **calculés serveur**, livraison/frais séparés, total avant confirmation, détection changement de prix/dispo.
- EF-8.2 Commandes multi-artistes : un panier → N groupes vendeurs.
- EF-8.3 Le navigateur n'est jamais source de vérité pour les montants.

### EF-9 Commandes et expéditions
- EF-9.1 Instantané à l'achat : prix, quantité, commission appliquée, frais, coordonnées, artiste, conditions.
- EF-9.2 Expéditions indépendantes par artiste ; suivi mis à jour par l'artiste, visible acheteur.
- EF-9.3 Jamais de statut « livré » sans mise à jour appropriée.

### EF-10 Litiges et remboursements
- EF-10.1 Ouverture, description, preuves autorisées (privées), réponse artiste, examen autorisé, décision motivée, remboursement éventuel enregistré, historique complet.
- EF-10.2 Remboursement **uniquement** après confirmation prestataire/mode vérifiable — jamais sur avis navigateur.

### EF-11 Administration
- EF-11.1 Tableau de bord : utilisateurs, candidatures, œuvres, signalements, commandes, paiements, remboursements, commissions, expéditions, litiges, audit, santé services.
- EF-11.2 Actions sensibles : autorisation explicite + journalisation.

## 4. Exigences transverses

| ID | Exigence |
|---|---|
| EX-1 | Montants XAF en **entiers** (zéro décimale), calculs serveur, arrondis documentés et testés |
| EX-2 | Commission 10 % prix œuvre, hors livraison/frais ; **taux figé par ligne de commande** |
| EX-3 | Réservation de stock transactionnelle + TTL ; libération sur échec/expiration ; test de concurrence |
| EX-4 | Webhooks : signature vérifiée + idempotence (rejeu = 1 exécution) ; réconciliation si notification perdue |
| EX-5 | Permissions testées pour les 7 rôles ; aucun IDOR (accès objet par autre utilisateur) |
| EX-6 | Médias : validation type/taille, miniatures, manifeste de licences, documents privés inaccessibles |
| EX-7 | 6 politiques juridiques FR/EN versionnées + acceptation tracée ; brouillons « à valider par juriste » |
| EX-8 | CI : tests, lint, types, migrations check, build ; pas d'exceptions permanentes |
| EX-9 | WCAG 2.2 AA « dans la mesure applicable » ; mobile-first |
| EX-10 | Aucune déclaration de conformité non vérifiée ; aucun service fictif |

## 5. Critères d'acceptation par phase

| Phase | Critères vérifiables |
|---|---|
| A (actuelle) | Docs complets et cohérents ; comparatif CamPay sourcé ; décisions tracées (ADR) ; validation commanditaire |
| B | `git init` + monorepo ; backend répond `/health` + OpenAPI ; frontend build ; Postgres Docker healthy ; CI verte sur PR ; 1 test backend + 1 test front |
| C | Inscription/connexion/CGU ; candidature DRAFT→APPROVED avec docs privés ; catalogue ne montre que PUBLISHED ; CRUD œuvre isolé par artiste ; upload médias validé |
| E | Checkout multi-vendeur avec montants serveur ; stock réservé/libéré (test concurrence) ; webhook signé idempotent ; ledger commissions ; expéditions N par commande ; litige + remboursement tracé |
| F | 6 politiques versionnées FR/EN ; acceptation CGU inscription ; cookies non essentiels bloqués sans consentement ; audit de permissions complet |
| G | 12 scénarios E2E §18 du prompt exécutés et rapportés ; sauvegarde+restauration testées ; perf cibles mesurées ; docs ops à jour |

## 6. Hors périmètre MVP (ne pas développer sans validation)

Apps natives Android/iOS ; enchères live ; XR/3D ; reco IA ; livraison internationale auto ; portefeuille interne ; split payment non validé ; abonnement vendeur ; vente de téléchargements numériques.

## 7. Devise, langue, marché

- Devise : **XAF**, stockée en entiers, affichée sans décimale.
- Marché : **Cameroun uniquement** (adresses CM, numéros +237).
- Langue UI : **français** ; architecture i18n prête (EN ultérieur).
- Données de démo : synthétiques, marquées comme démo.
