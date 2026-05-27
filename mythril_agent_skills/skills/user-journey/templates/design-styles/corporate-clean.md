---
version: alpha
name: Corporate Clean
description: Neutral, restrained palette for B2B SaaS, enterprise, and fintech.
colors:
  primary: "#1F2937"
  secondary: "#475569"
  tertiary: "#2563EB"
  neutral: "#F8FAFC"
  surface: "#FFFFFF"
  on-surface: "#0F172A"
  border: "#E2E8F0"
  emotion-delighted: "#10B981"
  emotion-happy: "#22C55E"
  emotion-neutral: "#94A3B8"
  emotion-frustrated: "#F97316"
  emotion-blocked: "#EF4444"
typography:
  headline-lg:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.01em
  headline-md:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.3
  body-md:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.55
  label-sm:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0.04em
  mono-sm:
    fontFamily: "JetBrains Mono, Menlo, Consolas, monospace"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: 4px
  md: 8px
  lg: 12px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  xxl: 64px
components:
  stage-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: 20px
  stage-card-active:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.tertiary}"
    rounded: "{rounded.md}"
  edge-arrow:
    backgroundColor: "{colors.secondary}"
---

# Corporate Clean

## Overview

Restrained, trustworthy, and dense. Suits enterprise software, fintech, and B2B SaaS where stakeholders expect a serious tone. The palette leans on neutral grays with a single accent blue used only for the primary path through the journey.

## Colors

- **Primary (#1F2937):** Slate ink for headlines and primary text.
- **Secondary (#475569):** Mid-slate for metadata, secondary text, and edges.
- **Tertiary (#2563EB):** Trust blue — used only for the active stage and primary CTAs.
- **Neutral (#F8FAFC):** Page background — almost-white with a hint of cool.
- **Emotion scale** — uses traffic-light semantics (`emotion-delighted` through `emotion-blocked`).

## Typography

- **Inter** for all UI text. Modern, neutral, and screens well at small sizes.
- **JetBrains Mono** for metric values and IDs (e.g. step keys).

## Layout

8 px base scale. Stage cards 280 px wide, 16 px gap. Map canvas uses CSS Grid with `auto-fit, minmax(280px, 1fr)` so it reflows on different screen widths.

## Elevation & Depth

Flat — no shadows. Visual hierarchy comes from spacing, weight, and the single accent color. A 1 px `border` on cards.

## Shapes

4 px corner radius on cards; 9999 px (pill) on emotion chips.

## Components

- `stage-card` — white card with 1 px border, `padding: 20px`
- `stage-card-active` — accent-colored 2 px border, rest unchanged
- `edge-arrow` — secondary-color SVG arrow with 1.5 px stroke

## Do's and Don'ts

- Do reserve the tertiary blue for ONE thing: the active stage / current step
- Do use the emotion palette consistently — never reassign meanings
- Don't add gradients or shadows
- Don't introduce a third font
