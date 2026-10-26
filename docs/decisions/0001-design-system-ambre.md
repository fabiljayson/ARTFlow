# ADR-0001 : Palette et design system

- **Statut** : accepté (Phase A, validation commanditaire 2026-10-26)
- **Contexte** : le prompt §14 propose marine `#1E2B58` + bronze `#C68B29` ; le fichier `DESIGN.md` racine définit un système ambre `#a16207` + crème + Roboto Condensed + Glassmorphism.
- **Décision** : retenir **`DESIGN.md`** comme source de vérité. Interprétation : surfaces solides crème pour les pages denses, glass sur images pour hero/bandes média (voir `docs/design.md`).
- **Conséquences** : tokens codés en CSS variables dès la Phase B ; revue de contraste systématique ; prompt §14 abandonné (le reste de l'exigence accessibilité reste d'application).
