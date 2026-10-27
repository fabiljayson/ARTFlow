---
name: "ARTFlow Design System"
description: "Framework-agnostic design rules for web and mobile app implementation."

# ─── Colors ───────────────────────────────────────────────
colors:
  # Brand
  primary:       "#9b6f58"
  primaryStrong: "#5f4639"
  primarySoft:   "#e8ccb8"
  accent:        "#9b6f58"

  # Surfaces
  surface:       "#fff5e8"
  surfaceMuted:  "#f3dfcc"

  # Text & Border
  text:          "#3f2f2a"
  border:        "#7c5d4c"

  # Feedback
  success:       "#16A34A"
  warning:       "#D97706"
  danger:        "#DC2626"

# ─── Typography ───────────────────────────────────────────
typography:
  family:        "Geist, system-ui, sans-serif"
  displayFamily: "Geist, system-ui, sans-serif"
  monoFamily:    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
  source:        "Optional Google Font: https://fonts.google.com/specimen/Geist"
  weights:       "400, 500, 600, 700"
  defaultWeight: 600
  tone:          "sans"

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
- Color direction: Clay - Earthy editorial warmth.
- Typography direction: Geist UI - Modern SaaS screens.
- Style direction: Liquid Glass - Floating translucent material with lens-like refraction, soft glow, and adaptive chrome
- References: Apple Liquid Glass, visionOS controls, iOS widget glass, immersive travel hero overlays, smart home floating panels, dark glossy liquid hero surfaces, layered glass filter/overlay/specular construction.
- Visual style: Clay color direction, Geist UI typography, Liquid Glass style.

## Style System: Liquid Glass
Use Liquid Glass to make the interface feel like translucent adaptive material suspended over an immersive background. The style is defined by lens refraction, frosted depth, pill geometry, soft edge highlights, subtle glow, floating controls, and glass widgets that bend light without hiding the content. It works best for premium product pages, travel and media experiences, smart-home dashboards, command surfaces, app chrome, and interfaces where the background can carry atmosphere. It must feel tactile and alive, but never become an empty glass demo.

### Layout Rules
- start from an atmospheric base: a photo, dark depth field, soft gradient, product scene, or calm textured surface that gives glass something to refract.
- place glass as floating chrome and overlays, not as the entire layout: nav bars, profile pills, control clusters, media cards, destination cards, smart-home widgets, command palettes, and focused CTA capsules.
- compose the first viewport with a real content anchor first, then layer one to three glass surfaces around it; the glass should frame the story rather than replace it.
- use capsule and liquid-rounded silhouettes for controls, floating widgets, and status panels; use larger soft rounded rectangles for cards and content modules.
- use one oversized irregular glossy lens or blob only when the hero needs a dramatic focal material; keep surrounding navigation and CTAs clean so the hero does not become chaotic.
- let important glass elements overlap the background or sit partially over media, but keep text on controlled tints with enough contrast.
- create depth with an explicit layer model: background scene, glass filter/refraction layer, translucent overlay tint, specular highlight layer, rim shadow, and foreground content.
- use dotted light fields, faint grid lines, glow trails, or specular streaks only as secondary atmosphere behind content.
- on mobile and narrow panels, simplify floating layers into fewer stacked glass surfaces so controls do not cover headings, CTAs, forms, or navigation.

### Component Patterns
- each glass component needs a clear material recipe: backdrop blur, translucent fill, rim border, inner white highlight, soft dark shadow, and optional colored glow.
- large liquid hero objects can use an irregular blob silhouette with bright rim lighting, smoky internal gradients, and subtle distortion behind the main headline.
- use refractive pills for primary controls: rounded capsule, thin bright border, soft inner shine, centered label, and a small icon or arrow when it clarifies action.
- use glass widgets for compact controls: toggles, media controls, profile chips, status badges, lock controls, camera controls, volume pills, and floating quick actions.
- travel, gallery, and media cards can sit over imagery with a darker glass tint near the bottom so titles, metadata, and prices remain readable.
- primary CTAs should be the cleanest and brightest glass object in the view, not just another translucent card.
- interactive states should feel material: hover brightens the rim and tint, active compresses or darkens slightly, focus-visible adds an unmistakable ring above the glass.
- use specular streaks, edge glow, and liquid highlights only on selected, hovered, or hero-level surfaces; too many highlights make the UI noisy.
- separate implementation hooks for glass effects when possible: filter for blur/refraction, overlay for tint, specular for highlight, and content for readable text and controls.
- forms, tables, and long reading areas need solid or lightly tinted surfaces; do not put dense content on highly refractive glass.
- dialogs, command palettes, menus, and sheets need stronger tint and contrast than decorative widgets because they interrupt the workflow.
- provide non-blur fallbacks with solid translucent colors for browsers, devices, or reduced-transparency contexts where backdrop-filter is unavailable.

### Existing Project Refactor Rules
- inventory the current interface first: background media, hero, navigation, CTAs, cards, widgets, dialogs, forms, routes, and stateful controls.
- preserve all existing content, routes, media, CTAs, forms, data logic, and section order unless the user explicitly asks for structural changes.
- convert only the surfaces that naturally benefit from glass first: navigation, floating toolbars, hero CTAs, bottom bars, profile chips, selected cards, media overlays, and modal chrome.
- if the current page has no atmospheric background, create a restrained gradient, product media area, or depth field before adding translucent overlays.
- if the current hero already has a strong brand mark or headline, place the liquid object behind it as an optical material layer rather than covering or replacing the brand.
- when applying to image-heavy pages, add dark or light scrims behind text instead of relying on blur alone.
- when applying to existing dark UI, replace low-opacity gray text with clearer foreground tokens before adding glass layers.
- when applying to existing light UI, strengthen the glass rim, shadow, and tint so white surfaces do not disappear.
- if a screen is dense with data, docs, or forms, keep most content solid and reserve liquid glass for chrome, filters, toolbar actions, and selected states.
- after each material change, verify that every original heading, CTA, icon, form field, image, and section is still visible and reachable.

### Spacing Rules
- use 10px to 14px padding for tiny floating widgets, 12px to 18px for pill controls, 18px to 28px for cards, and 32px or more for hero glass modules.
- keep at least 10px to 16px between adjacent translucent layers so rims, shadows, and refraction edges can be read.
- use large radius for liquid objects: full pills for controls, 18px to 32px for widgets, and softer organic corners for hero overlays.
- oversized liquid blobs need generous breathing room around their rim; do not crop the glow tightly unless the crop is an intentional full-bleed hero effect.
- avoid edge-to-edge glass unless it is navigation chrome; glass needs surrounding negative space to feel suspended.
- keep alignment precise even when shapes feel fluid; drifting glass objects still need a consistent optical grid.
- use stable dimensions for nav bars, pills, toggles, widgets, cards, and badges so hover, loading, or selected states do not shift layout.
- do not stack glass inside glass repeatedly; use one strong shell plus inner dividers, icons, labels, or tint shifts.

### Visual Hierarchy Rules
- make the background cinematic but subordinate: it should create depth while the content and controls remain the readable foreground.
- use the strongest rim light, glow, and refraction on the primary CTA, selected control, active widget, or hero glass object.
- keep primary text, prices, form values, errors, and navigation labels on the most stable and highest-contrast glass layer.
- use floating secondary widgets to imply spatial depth, but keep them smaller and lower contrast than the main task path.
- let typography, placement, and control role define hierarchy before liquid material effects.
- keep one dominant material moment per view, such as a hero CTA capsule, floating dock, smart-home control cluster, command palette, or featured media card.
- when using a dark glossy hero lens, keep the headline, primary CTA, and core value proposition brighter and sharper than the material distortion.
- make focus rings, error states, destructive actions, and loading states visually sit above blur, glow, and refraction.

### Style Anti-patterns
- replace page content with empty shiny backgrounds, decorative blobs, or glass panels with no product role.
- place important copy directly over uncontrolled imagery, high blur, bright glow, or moving highlights.
- animate glass effects constantly without reduced-motion support.
- use liquid glass everywhere until all surfaces have the same importance.
- rely on opacity alone to create glass without borders, tint, fallback, shadow, or contrast checks.
- turn the design into a generic card grid; Liquid Glass should feel like floating material and adaptive chrome, not Bento.
- put a glossy blob in front of important text, controls, or product media unless it is acting as a readable backing layer.
- use glass for dense data tables, long forms, or documentation blocks when a solid surface would be clearer.
- let floating glass controls cover content on mobile or small desktop sidebars.

### Style Checklist
- the page still contains all original content, CTAs, media, navigation, forms, and stateful controls.
- the design has an atmospheric background or depth field that gives glass material something to refract.
- complex liquid effects are separated into filter, overlay, specular, and content layers or an equivalent maintainable structure.
- liquid glass appears on meaningful chrome, controls, widgets, media overlays, or product surfaces, not as empty decoration.
- every glass surface has a readable boundary through tint, rim border, inner highlight, shadow, or glow.
- text remains readable against the final rendered material on desktop and mobile.
- primary actions, focus-visible rings, selected states, and errors are stronger than decorative highlights.
- reduced-motion, non-blur, and solid-color fallbacks keep the design usable.
- floating controls do not cover important content or block touch targets.
- the result feels premium, fluid, refractive, and adaptive without sacrificing scannability or task flow.

## Design Tokens
Use semantic tokens first. Raw values from frontmatter are source values, not permission to scatter hex codes or one-off sizes through implementation.

### Color
- Primary action color: #9b6f58.
- Strong primary: #5f4639. Use for high-emphasis text, selected state, or strong borders.
- Soft primary: #e8ccb8. Use for subtle surfaces, selected backgrounds, or calm highlights.
- Surface: #fff5e8.
- Muted surface: #f3dfcc.
- Text: #3f2f2a.
- Border: #7c5d4c.
- Success, warning, and danger are semantic states. Pair them with labels, icons, or position; never rely on color alone.
- When moving from a dark theme to a light or warm theme, update inherited light text classes such as white, muted-white, or low-opacity foregrounds.
- Do not apply one warm/cream/brown palette across the entire page without contrast, hierarchy, and content anchors.

### Text Selection
- Use this style-specific `::selection` treatment for Liquid Glass. It should follow the selected color tokens and stay readable.
```css
/* Liquid Glass selection: soft lens glow. */
::selection {
  background-color: #e8ccb8;
  color: #3f2f2a;
  text-shadow: 0 0 12px #9b6f58;
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
- Primary family: Geist, system-ui, sans-serif.
- Display family: Geist, system-ui, sans-serif.
- Monospace family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace.
- Allowed weights: 400, 500, 600, 700.
- Default UI weight: 600.
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
- use liquid glass for purposeful floating chrome, premium controls, media overlays, smart widgets, and high-value interaction surfaces.
- preserve original content and improve the visual layer around it instead of replacing sections with empty material panels.
- combine tint, blur, rim border, inner highlight, shadow, and subtle glow so every surface has a readable boundary.
- use immersive backgrounds intentionally: product imagery, travel photos, soft depth gradients, or controlled dark fields.
- use explicit filter, overlay, specular, and content layers when building complex liquid glass so the effect can be tuned without harming readability.
- provide solid readable fallbacks for blur, transparency, reduced motion, and reduced transparency.
- verify rendered contrast after every opacity, blur, background, or highlight change.
- use subtle responsive motion between 160ms and 260ms when it clarifies interaction state.
- prefer fewer stronger glass objects over many weak translucent fragments.

## Rules: Don't
- use low-contrast text, hidden focus indicators, or color-only state communication.
- delete or replace existing product content unless the user explicitly asks for content removal.
- introduce one-off spacing, typography, or radius values outside the token system.
- mix unrelated visual metaphors in the same screen.
- depend on framework-specific component names in design rules.
- add decorative motion without reduced-motion fallbacks.
- replace page content with empty shiny backgrounds, decorative blobs, or glass panels with no product role.
- place important copy directly over uncontrolled imagery, high blur, bright glow, or moving highlights.
- animate glass effects constantly without reduced-motion support.
- use liquid glass everywhere until all surfaces have the same importance.
- rely on opacity alone to create glass without borders, tint, fallback, shadow, or contrast checks.
- turn the design into a generic card grid; Liquid Glass should feel like floating material and adaptive chrome, not Bento.
- put a glossy blob in front of important text, controls, or product media unless it is acting as a readable backing layer.
- use glass for dense data tables, long forms, or documentation blocks when a solid surface would be clearer.
- let floating glass controls cover content on mobile or small desktop sidebars.

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
