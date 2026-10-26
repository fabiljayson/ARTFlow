# ArtFlow — Design system appliqué (arbitrage Phase A)

> Décision : **conserver le `DESIGN.md` racine** (ambre, Roboto Condensed, Glassmorphism) — validation commanditaire Phase A. Le prompt §14 (marine/bronze) est abandonné ; le fond neutre + contraste AA reste exigé.

## 1. Tokens (source : `/DESIGN.md`)

| Token | Valeur | Usage ArtFlow |
|---|---|---|
| primary | `#a16207` | CTA, liens, accents |
| primaryStrong | `#451a03` | texte emphase, bordures fortes |
| primarySoft | `#fde68a` | fonds subtils, badges |
| surface | `#fef3c7` | fonds de page |
| surfaceMuted | `#fde68a` | bandes, table rows alt |
| text | `#1c0d02` | texte courant |
| border | `#78350f` | bordures |
| success/warning/danger | vert/orange/rouge standard | + icône/label (jamais couleur seule) |
| typo | Roboto Condensed 300–700, défaut 500 | tout le site |
| spacing | 4/8/12/16/24/32/48 | scale exclusive |
| radius | 4/8/12 | compacts / cartes / surfaces larges |
| motion | 120/180/260 ms | + reduced-motion off |

## 2. Interprétation Glassmorphism pour un site d'art (ambiguïté résolue)

Le DESIGN.md décrit un glass sur canvas **sombre** ; la palette tokens est **chaude claire**. Arbitrage :

1. **Pages catalogue/fiches/admin/tables/formulaires** : surfaces **solides crème** (`surface`) — confort de lecture, contraste maximal, images d'œuvres qui portent la couleur.
2. **Hero accueil, bandes vidéo, modales, cartes de prix panier** : panneaux **glass** posés sur image d'œuvre ou dégradé ambre profond (`primaryStrong` → brun) avec scrim — l'effet premium du DESIGN.md sans sacrifier la lisibilité.
3. Header : glass léger sur les pages média ; solide sur les pages denses.
4. Fallback : sans `backdrop-filter`, panneaux opaques `primarySoft`/blanc cassé.

## 3. Composants prioritaires (bibliothèque Phase B/C)

`Button` (primary/secondary/ghost/danger), `TextField` (label + helper + error), `Select`, `Badge` (statuts œuvre/commande), `Card` (artwork card), `Modal` (focus trap), `Toast`, `Tabs`, `Pagination`, `Stepper` (candidature), `Dropzone` (médias), `Table` (admin), `EmptyState`, `Skeleton`, `VideoPlayer` (muet, lazy), `CookieBanner`, `PriceTag` (format `100 000 XAF` sans décimale).

## 4. Format monnaie

`Intl.NumberFormat('fr-CM', { style:'currency', currency:'XAF', maximumFractionDigits: 0 })` → ex. `100 000 XAF`. Helper unique côté front ; jamais de flottants.

## 5. Images d'œuvres

- Ratio constant 4:5 dans les grilles catalogue ; `object-fit: cover` ; lazy loading ; dimensions déclarées (CLS).
- Fallback : plaque `surfaceMedium` + icône si échec image.

## 6. Contraste (à tester en Phase C)

| Pair | Cible |
|---|---|
| text on surface | ≥ 12:1 |
| primary on surface | ≥ 4.5:1 (liens) |
| texte blanc sur hero sombre (image + scrim 60 %) | ≥ 4.5:1 |
| danger/success texte + icône | ≥ 4.5:1 |

## 7. Ce qui n'est PAS dans le DESIGN.md (décisions produit)

- Police display secondaire : **aucune** (tout en Roboto Condensed).
- Mode sombre : hors MVP.
- Icônes : jeu outline 24 px (Lucide-style) monochrome `text`/`primary`.
