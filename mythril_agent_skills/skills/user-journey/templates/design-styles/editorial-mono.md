---
version: alpha
name: Editorial Mono
description: High-contrast monochrome with editorial typography. For content products, media, and reading-first apps.
colors:
  primary: "#0A0A0A"
  secondary: "#525252"
  tertiary: "#B8422E"
  neutral: "#F5F2EB"
  surface: "#FFFFFF"
  on-surface: "#0A0A0A"
  border: "#0A0A0A"
  emotion-delighted: "#1F6B43"
  emotion-happy: "#3F8E5F"
  emotion-neutral: "#737373"
  emotion-frustrated: "#C77B2C"
  emotion-blocked: "#B8422E"
typography:
  headline-lg:
    fontFamily: "Fraunces, Source Serif Pro, Georgia, serif"
    fontSize: 38px
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.02em
  headline-md:
    fontFamily: "Fraunces, Source Serif Pro, Georgia, serif"
    fontSize: 22px
    fontWeight: 500
    lineHeight: 1.3
  body-md:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  label-sm:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: 11px
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0.12em
  mono-sm:
    fontFamily: "JetBrains Mono, Menlo, Consolas, monospace"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: 0px
  md: 0px
  lg: 2px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 32px
  xl: 56px
  xxl: 88px
# Semantic state palette — meanings LOCKED (red=error, green=success,
# amber=warning, blue=loading). Editorial tone favors muted, earthy
# variants of the canonical palette so they sit naturally on a warm
# paper background.
state:
  default:
    bg: "#F0EDE5"
    bd: "#C9C2B3"
    hd: "#0A0A0A"
  loading:
    bg: "#E1ECF2"
    bd: "#6FA0BD"
    hd: "#1F4E63"
  success:
    bg: "#E1EEDF"
    bd: "#6FA075"
    hd: "#1F6B43"
  error:
    bg: "#F2DCD5"
    bd: "#C77B6E"
    hd: "#8A2A1F"
  warning:
    bg: "#F5E8CC"
    bd: "#C9A45A"
    hd: "#7A5215"
arrows:
  default: "#525252"
  success: "#1F6B43"
  error:   "#B8422E"
  cancel:  "#A1A1A1"
canvas:
  bg:         "#F5F2EB"
  grid-major: "rgba(10, 10, 10, 0.06)"
  grid-minor: "rgba(10, 10, 10, 0.03)"
components:
  stage-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: 28px
  stage-card-active:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.tertiary}"
    rounded: "{rounded.md}"
  edge-arrow:
    backgroundColor: "{colors.primary}"
---

# Editorial Mono

## Overview

Print-magazine aesthetic. Serif headlines, generous whitespace, single warm accent. For content-focused products (publications, knowledge bases, reading apps) and decks aimed at design-literate audiences. Quiet, confident, slow.

## Colors

- **Primary (#0A0A0A):** Near-black ink.
- **Secondary (#525252):** Mid-gray for captions and metadata.
- **Tertiary (#B8422E):** "Boston Clay" — terracotta accent; only for the active stage.
- **Neutral (#F5F2EB):** Warm off-white — the page background.
- **Surface (#FFFFFF):** Pure white for cards, contrasting against the neutral page.

## Typography

- **Fraunces** for headlines — a contemporary serif with editorial gravity.
- **Inter** for body and labels — neutral counterpoint to the serif.
- ALL CAPS labels with generous letter-spacing for section headers (e.g. `ACTIONS`, `THOUGHTS`).

## Layout

8 px base scale, but spacing leans larger: `lg = 32 px`, `xl = 56 px`. Stage cards 320 px wide, 32 px gap. The journey breathes.

## Elevation & Depth

Flat — no shadows. A 1 px hairline `border` in the primary color on cards. Hierarchy comes from the contrast between white cards and the warm neutral page.

## Shapes

0 px corner radius (sharp) — reinforces the editorial / architectural tone. Pills allowed only on emotion chips.

## Components

- `stage-card` — white card, 1 px primary border, 28 px padding
- `stage-card-active` — neutral background instead of white, terracotta heading, primary border thickens to 2 px
- `edge-arrow` — primary color, 1 px stroke, simple straight line (no curves)

## Do's and Don'ts

- Do let the page breathe — never tighten spacing
- Do treat ALL-CAPS labels as design elements, not just labels
- Don't add rounded corners
- Don't use the terracotta on more than one element per view
