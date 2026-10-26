---
name: "ARTFlow Design System"
description: "Framework-agnostic design rules for web and mobile app implementation."

# ─── Colors ───────────────────────────────────────────────
colors:
  # Brand
  primary:       "#a16207"
  primaryStrong: "#451a03"
  primarySoft:   "#fde68a"
  accent:        "#a16207"

  # Surfaces
  surface:       "#fef3c7"
  surfaceMuted:  "#fde68a"

  # Text & Border
  text:          "#1c0d02"
  border:        "#78350f"

  # Feedback
  success:       "#16A34A"
  warning:       "#D97706"
  danger:        "#DC2626"

# ─── Typography ───────────────────────────────────────────
typography:
  family:        "Roboto Condensed, Arial Narrow, sans-serif"
  displayFamily: "Roboto Condensed, Arial Narrow, sans-serif"
  monoFamily:    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
  source:        "Optional Google Font: https://fonts.google.com/specimen/Roboto+Condensed"
  weights:       "300, 400, 500, 700"
  defaultWeight: 500
  tone:          "condensed"

# Spacing
spacing:
  xs:      4px
  sm:      8px
  md:      12px
  lg:      16px
  xl:      24px
  xxl:     32px
  section: 48px

# Radius
radius:
  sm: 4px
  md: 8px
  lg: 12px

# Motion
motion:
  fast:   120ms
  normal: 180ms
  slow:   260ms
---

# Design System Rules

## Purpose
ARTFlow Design System defines portable, framework-agnostic design rules for web and mobile product interfaces. Use it as the source of truth before changing layouts, components, color, typography, motion, or interaction states.

This file is a portable design skill. Any AI or engineer should be able to read it and improve a web or mobile interface without needing React, Vue, Svelte, Tailwind, native mobile, or any other specific technology.

## Operating Modes

### New Project Mode
- Use these rules to create a coherent first implementation when no existing UI exists.
- Build the information architecture, component system, and responsive behavior from the tokens and rules below.

### Existing Project Refactor Mode
- Treat the existing product as the source of truth for content, routes, behavior, data, and information architecture.
- Improve the visual system by patching styles, tokens, spacing, typography, hierarchy, responsive behavior, and component states.
- Do not regenerate whole pages from scratch when a targeted patch can preserve the current experience.
- Do not replace real content with placeholder, demo, lorem ipsum, or simplified content.
- If a section looks inconsistent with this design system, restyle it first. Do not remove it.
- If removing content, routes, features, media, or data logic seems necessary, stop and ask for approval.

## Preservation Rules For Existing Products
- Preserve all existing headings, paragraphs, labels, buttons, links, images, icons, forms, navigation items, sections, routes, and data-fetching logic unless the user explicitly requests removal.
- Preserve semantic meaning and section order unless the user asks for an information-architecture change.
- Preserve working interactions: forms, menus, language toggles, theme toggles, dialogs, tabs, carousels, and scroll behavior.
- Preserve real brand/product names and domain-specific copy. Design changes must not make the page generic.
- Keep every original section represented after the refactor. A redesigned section is acceptable; a missing section is not.
- Never leave the first viewport empty unless the existing product intentionally has an empty state.

## Safe Refactor Workflow
1. Read the existing UI code before editing. Identify sections, routes, state, data dependencies, and user actions.
2. Inventory current colors, typography, spacing, radius, shadows, and component states.
3. Map old visual values to the tokens in this file one-to-one where possible.
4. Patch section by section. Avoid full-file rewrites when the current structure works.
5. After each section, verify the original content is still present, visible, and reachable.
6. After changing colors, check every affected text/background pair for contrast.
7. Verify desktop and mobile before finishing.

## Visual Direction
- Color direction: Warm - Soft amber depth.
- Typography direction: Condensed UI - Dense sidebars.
- Style direction: Glassmorphism - Frosted panels over gradients, glow, imagery, and layered UI surfaces
- References: Frosted glass interfaces, Dark luminous SaaS heroes, gradient finance cards, Windows acrylic menus, blurred UI panels over imagery, minimal glass effect demos.
- Visual style: Warm color direction, Condensed UI typography, Glassmorphism style.

## Style System: Glassmorphism
Use Glassmorphism to create a frosted interface where translucent panels, blurred backgrounds, soft gradients, luminous color fields, and thin borders make the UI feel layered and premium. Unlike Liquid Glass, this style is not about refractive blobs or adaptive material physics; it is about clean acrylic panels, glass cards, glass navigation, floating finance cards, app menus, and dark or colorful hero sections with readable frosted surfaces.

### Layout Rules
- start with a controlled depth background: dark neutral canvas, purple or blue gradient, soft radial glow, product image, landscape photo, or abstract orb field.
- use frosted panels as stable UI containers: nav bars, hero cards, app menus, payment cards, pricing slabs, feature panels, floating toolbars, dialogs, and sidebars.
- compose the first viewport around a readable headline and one or two translucent surfaces; the background can glow, but content must remain sharp.
- glass panels should usually be rectangular or rounded rectangles with consistent alignment, not irregular liquid shapes.
- place vivid gradients, blurred circles, product artwork, or photography behind glass so the blur effect has visible depth.
- use translucent cards to reveal context behind them, such as a card over a gradient, a menu over a desktop wallpaper, or CTA controls over a dark hero.
- reserve solid or near-solid sections for long-form text, dense tables, docs, forms, and anything that needs reading comfort.
- on mobile, reduce the number of overlapping translucent layers and stack glass panels in a simple vertical order.

### Component Patterns
- each frosted component needs a repeatable recipe: semi-transparent fill, backdrop blur, thin border, soft shadow, and optional inner highlight.
- glass navigation should use enough tint and separation that links, active states, menus, and profile controls remain readable over dark or image backgrounds.
- hero glass panels should support the headline and CTA; use a dark or light scrim when text crosses bright gradients or busy imagery.
- payment cards, account cards, or product cards can use glass with visible numbers, logos, labels, and subtle diagonal shine.
- Windows-style acrylic menus should feel calm and functional: dark translucent panel, clear app/icon grid, readable labels, and subtle blue or system-color depth.
- primary buttons inside glass surfaces need stronger fill, brighter border, or glow than secondary buttons.
- forms need stable field backgrounds, visible labels, helper text, error text, and focus rings; avoid fully transparent inputs.
- dialogs, popovers, menus, and sheets should use stronger opacity than decorative glass cards because they contain decisions.
- provide solid-color fallback surfaces when backdrop-filter or blur is unsupported.

### Existing Project Refactor Rules
- inventory the existing product before styling: hero, navigation, CTAs, forms, cards, pricing, testimonials, media, routes, and footer.
- preserve every existing section and decide whether it becomes a glass overlay, a solid content band, a media-backed hero, or a plain readable section.
- do not convert dense text, tables, docs, or long forms into weak translucent panels when a stable surface is clearer.
- patch backgrounds, overlays, borders, blur, and state styles section by section instead of rewriting the whole page.
- if the existing page is plain, add depth behind glass first through gradient fields, blurred color circles, product artwork, or photography; do not add transparent panels over a flat empty background.
- when restyling a page with strong imagery, add scrims or tinted overlays before placing text on top of the image.
- when restyling a dark SaaS page, use glow and glass to frame the product surface, but keep the UI screenshot or main workflow visible.
- when restyling a finance or product landing page, let glass cards carry concrete content such as card numbers, plan names, metrics, or feature labels rather than generic decoration.
- after each glass change, verify that original copy, CTAs, icons, media, form fields, and navigation remain visible and reachable.
- if content starts disappearing, inspect contrast, opacity, z-index, filter, and inherited text color before deleting or rebuilding sections.

### Spacing Rules
- use 12px to 16px padding for compact nav/menu glass, 18px to 28px for cards and panels, and 32px to 56px for large hero glass surfaces.
- leave visible negative space around frosted panels so shadow, blur, and glow can separate them from the background.
- keep glass navigation compact and aligned; frosted chrome should feel light, not oversized.
- use consistent gutters and alignment even when panels overlap gradients, photos, or abstract glow fields.
- avoid stacking glass card inside glass card; use internal spacing, separators, or subtle tint shifts instead.
- large glass cards need enough internal padding for labels, metadata, CTA groups, and icons to remain readable.
- reserve full-width solid or near-solid bands for content-heavy sections that need reading comfort.
- keep panel dimensions stable so loading states, hover states, and blur effects do not shift layout.

### Visual Hierarchy Rules
- use background brightness, blur strength, tint, border, and glow to separate background, glass, and foreground text.
- keep the hero message and primary CTA on the clearest part of the composition.
- use accent glow for primary actions, active nav items, selected cards, payment cards, or the main product focal point, not every panel.
- let gradients, photography, and product art create atmosphere while typography and spacing carry hierarchy.
- avoid placing body copy over high-frequency imagery, bright highlights, or complex gradients without a readable scrim.
- use stronger frosted surfaces for important information such as prices, dates, card numbers, form values, errors, and confirmations.
- keep glass panels lighter than the content they contain: text, icons, CTAs, and data must be sharper than the frosted layer.
- maintain focus rings that are visible on glass, dark backgrounds, and image-backed areas.

### Style Anti-patterns
- turn the page into a grid of identical glass cards just because Bento uses modules.
- place text directly on busy translucent backgrounds without a scrim or stable panel.
- use blur as a substitute for layout, hierarchy, or content grouping.
- make every section translucent until depth loses meaning.
- depend on backdrop-filter without a readable fallback.
- hide real media, CTA paths, forms, or navigation behind decorative glow.
- use low-opacity white text on light glass or low-opacity dark text on dark glass.
- imitate Liquid Glass with irregular refractive blobs, specular lens distortion, or physics-like material when this style should be frosted acrylic.

### Style Checklist
- the first viewport has a clear product or place signal, headline, supporting copy, and primary CTA.
- the background provides visible depth through gradient, glow, imagery, product art, or wallpaper-like context.
- all text on glass surfaces meets contrast against the final rendered background.
- each translucent panel has a visible edge through tint, border, highlight, or shadow.
- existing content, forms, media, CTAs, navigation, and routes remain present.
- the UI still works when blur support is unavailable.
- mobile views simplify glass effects when space or readability suffers.
- the result reads as atmospheric frosted acrylic glass, not a generic card grid or Liquid Glass blob system.
- focus, error, selected, hover, disabled, and loading states remain visible above the glass effect.

## Design Tokens
Use semantic tokens first. Raw values from frontmatter are source values, not permission to scatter hex codes or one-off sizes through implementation.

### Color
- Primary action color: #a16207.
- Strong primary: #451a03. Use for high-emphasis text, selected state, or strong borders.
- Soft primary: #fde68a. Use for subtle surfaces, selected backgrounds, or calm highlights.
- Surface: #fef3c7.
- Muted surface: #fde68a.
- Text: #1c0d02.
- Border: #78350f.
- Success, warning, and danger are semantic states. Pair them with labels, icons, or position; never rely on color alone.
- When moving from a dark theme to a light or warm theme, update inherited light text classes such as white, muted-white, or low-opacity foregrounds.
- Do not apply one warm/cream/brown palette across the entire page without contrast, hierarchy, and content anchors.

### Text Selection
- Use this style-specific `::selection` treatment for Glassmorphism. It should follow the selected color tokens and stay readable.
```css
/* Glassmorphism selection: frosted tint. */
::selection {
  background-color: #fde68a;
  color: #1c0d02;
  text-shadow: 0 1px 14px #fef3c7;
}
```
- If the selected color changes, keep the same style behavior but re-check text/background contrast.

### Contrast And Visibility Gate
- Every visible text node must remain readable after color changes.
- Check hero text, navigation, buttons, card titles, form labels, helper text, icons, borders, and disabled states against their actual backgrounds.
- If legacy classes or CSS keep text white on a light surface, replace them with semantic foreground tokens.
- If content appears missing after a restyle, inspect contrast and visibility before deleting or rebuilding the section.
- Do not finish with invisible text, hidden CTAs, empty hero areas, or decorative backgrounds replacing product content.

### Typography
- Primary family: Roboto Condensed, Arial Narrow, sans-serif.
- Display family: Roboto Condensed, Arial Narrow, sans-serif.
- Monospace family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace.
- Allowed weights: 300, 400, 500, 700.
- Default UI weight: 500.
- Keep heading levels semantic. Visual size must follow layout importance, not HTML heading number.
- Keep letter spacing at 0 by default. Use uppercase labels sparingly and only for short metadata.

### Spacing And Radius
- Spacing scale: 4/8/12/16/24/32/48.
- Prefer spacing and grouping over extra borders.
- Use 4px radius for compact controls, 8px for standard cards/inputs, and 12px only for larger feature surfaces.
- Do not invent new spacing values unless the layout cannot be solved with the scale.

## Layout Rules
- Start mobile-first. The smallest useful viewport defines the base layout.
- Use content-driven breakpoints. Do not scale type directly with viewport width.
- Keep navigation, primary actions, and form completion paths easy to reach on touch devices.
- Prefer a clear grid, predictable alignment, and stable dimensions for controls, cards, tabs, and repeated items.
- Empty, loading, and error states must preserve layout stability and explain the next action.

## Component Rules
- Every interactive component must define default, hover, active, focus-visible, disabled, loading, success, and error behavior when those states apply.
- Buttons must communicate hierarchy through role: primary, secondary, tertiary, destructive, or icon-only.
- Forms must keep labels visible, helper text close to the field, and errors specific enough to fix.
- Cards must represent repeated items or contained tools. Do not nest cards inside other cards.
- Modals and popovers must include focus management, escape behavior, and clear dismissal affordances.

## Interaction And Motion
- Motion must clarify state change, not decorate the screen.
- Transitions should usually stay between 120ms and 260ms.
- Provide reduced-motion behavior for animations, parallax, shimmer, and auto-moving content.
- Pointer hover cannot be the only way to reveal important controls because touch devices do not have hover.

## Accessibility Requirements
WCAG 2.2 AA, keyboard-first interactions, visible focus states, semantic HTML before ARIA, reduced-motion support, accessible target sizes.

- Text and meaningful non-text UI must meet WCAG 2.2 AA contrast.
- Keyboard users must be able to reach, understand, and operate every interactive control.
- Focus indicators must be visible, high-contrast, and not hidden by overflow or animation.
- Semantic HTML or native platform semantics come before ARIA patches.
- Touch targets should be at least 24px by WCAG 2.2 AA and should reach 44px when layout allows.

## Content Tone
Clear, concise, implementation-focused, low-jargon, and helpful without being decorative.

- Use direct labels for actions.
- Avoid vague UI copy like "Submit" when the action can be named.
- Keep empty states useful: state what happened, why it matters, and what the user can do next.

## Rules: Do
- use semantic tokens before raw values in components.
- preserve existing content, copy, media, routes, and behavior when applying this system to an existing project.
- preserve hierarchy with spacing, contrast, typography, and component state.
- define default, hover, active, focus-visible, disabled, loading, success, and error states.
- design mobile-first, then enhance for tablet and desktop density.
- keep implementation guidance portable across React, Vue, Svelte, plain HTML/CSS, and mobile UI stacks.
- use glass where layering adds context: media-backed heroes, frosted nav, app menus, finance cards, pricing overlays, product previews, dialogs, and featured cards.
- protect text with scrims, tint, stable panels, or stronger foreground tokens.
- include borders, tint, shadow, inner highlight, and fallback surfaces for glass panels.
- preserve product content while improving atmosphere, depth, and scan speed.
- verify contrast after every blur, opacity, blend-mode, background, or glow change.
- use real images, screenshots, maps, products, payment cards, app icons, or meaningful visual anchors when the existing project provides them.
- prefer consistent acrylic rectangles and frosted cards over liquid blobs or refractive lens shapes.

## Rules: Don't
- use low-contrast text, hidden focus indicators, or color-only state communication.
- delete or replace existing product content unless the user explicitly asks for content removal.
- introduce one-off spacing, typography, or radius values outside the token system.
- mix unrelated visual metaphors in the same screen.
- depend on framework-specific component names in design rules.
- add decorative motion without reduced-motion fallbacks.
- turn the page into a grid of identical glass cards just because Bento uses modules.
- place text directly on busy translucent backgrounds without a scrim or stable panel.
- use blur as a substitute for layout, hierarchy, or content grouping.
- make every section translucent until depth loses meaning.
- depend on backdrop-filter without a readable fallback.
- hide real media, CTA paths, forms, or navigation behind decorative glow.
- use low-opacity white text on light glass or low-opacity dark text on dark glass.
- imitate Liquid Glass with irregular refractive blobs, specular lens distortion, or physics-like material when this style should be frosted acrylic.

## AI Implementation Checklist
- Read this file before changing UI, layout, component styling, or interaction behavior.
- Identify the target surface: mobile app, mobile web, desktop web, dashboard, landing page, form flow, or content-heavy view.
- Map the design tokens to the project technology without changing the design intent.
- Reuse existing project components when they can satisfy these rules.
- If the current UI conflicts with this file, explain the conflict and choose the more accessible, consistent option.
- Confirm all original navigation items, hero content, CTAs, media, sections, and forms still exist unless removal was requested.
- Confirm no text became invisible from background, opacity, blend-mode, or inherited color changes.
- Confirm the first viewport contains meaningful product content, not just a background treatment.
- Verify keyboard navigation, focus-visible styling, responsive behavior, text overflow, loading state, and error state before finishing.
