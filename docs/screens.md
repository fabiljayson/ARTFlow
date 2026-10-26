# ArtFlow — Écrans (maquettes textuelles)

> Phase A. Description fonctionnelle des écrans (pas de mockup graphique). Design tokens : `DESIGN.md` (ambre + glass), arbitrage dans `docs/design.md`.

## Global
- **Shell** : header (logo ArtFlow, recherche, nav Œuvres/Artistes/Vidéos, compte/panier), footer (légal, contact, devenir artiste).
- États systématiques : chargement (squelette), vide, erreur + retry, succès.
- Mobile : navigation bottom ou drawer ; grilles 1 colonne.

## 1. Accueil `/`
Hero glass sur image d'œuvre (headline FR + CTA « Explorer le catalogue » / « Vendre mes œuvres ») → sélection « Œuvres du moment » (grille 4×) → artistes en vedette (avatars + ville) → catégories (chips/visuels) → bande « Découverte vidéo » (3 miniatures play) → CTA final devenir artiste → footer.

## 2. Catalogue `/catalogue`
Barre de filtres (catégorie, prix min/max XAF, disponibilité, tri) + grille cartes (image, titre, artiste, prix XAF, badge « Épuisé »). Pagination. Empty state « Aucune œuvre ne correspond ».

## 3. Fiche œuvre `/oeuvre/{slug}`
Galerie images (principale + vignettes) + lecteur vidéo si présente ; colonne infos : titre, prix, artiste (lien), catégorie, statut stock, bouton ajouter panier ; bloc caractéristiques (dimensions, matériaux, technique, année) ; expédition (frais vendeur) ; conditions ; avis ; similaires.

## 4. Fil vidéo `/videos`
Feed vertical (mobile) / grille (desktop) : vidéo muette au survol, play au clic, titre+artiste en overlay glass, bouton « Voir l'œuvre ». Fallback poster si échec.

## 5. Auth
`/connexion`, `/inscription` (CGU case obligatoire + lien version), `/mot-de-passe/oublié`. Messages d'erreur précis.

## 6. Compte
`/compte/profil` (infos, téléphone), `/compte/adresses` (CRUD), `/compte/notifications` (préférences), `/compte/cgu` (historique acceptations).

## 7. Candidature `/devenir-artiste`
Formulaire multi-étapes : infos perso → bio/ville → upload pièce d'identité + preuve création (privé) → récap → soumettre. Page statut : PENDING_REVIEW (message d'attente), NEEDED_INFO (champs à compléter), REJECTED (motif), APPROVED (CTA œuvres).

## 8. Espace artiste `/artiste`
- Dashboard : cartes stats (ventes du mois, commissions dues, commandes à expédier).
- `/artiste/oeuvres` : table CRUD + statut modération + actions publier/dépublier.
- `/artiste/oeuvres/nouvelle` : formulaire + upload médias (drag-drop, barres de progression).
- `/artiste/commandes` : lignes vendeur ; action « Créer expédition » (tracking).
- `/artiste/gains` : ledger + payouts.

## 9. Panier & checkout
`/panier` : lignes (relecture serveur), alerte « prix/stock modifié », sous-total, livraison par vendeur, total.
`/commande/confirmation` : récap avant paiement.
`/paiement/{ref}` : choix opérateur (MTN/Orange), saisie téléphone +237, bouton payer → état « Validez sur votre téléphone… » (polling statut) → succès/échec.
`/commandes` + `/commandes/{ref}` : statut, lignes, expéditions suivies, boutons litige/remboursement.

## 10. Litige `/commandes/{ref}/litige`
Formulaire motif + description + upload preuves ; fil messages ; statut.

## 11. Admin `/admin`
Sections : Tableau de bord (santé), Utilisateurs, Candidatures (file d'attente + détail docs), Œuvres (modération), Commandes, Paiements, Remboursements (file d'approbation), Litiges, Commissions/Ledger, Payouts, Catégories, Signalements, Audit (filtres), Paramètres (commission bps, TTL réservation, seuil ré-moderation).
Actions sensibles : modale de confirmation + **motif obligatoire**.

## 12. Légal `/legal/{slug}?lang=fr|en`
Pages politiques versionnées ; bandeau cookies au premier visit (essentiels seuls par défaut).

## 13. Accessibilité transverse
- focus-visible sur glass ; navigation clavier complète ; `alt` sur toutes images d'œuvre ; contrastes AA (texte ambre foncé sur crème ; inverse sur hero sombre) ; `prefers-reduced-motion` respecté.
