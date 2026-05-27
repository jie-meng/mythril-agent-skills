---
version: alpha
name: Playful Pastel
description: Warm, friendly palette for consumer apps, lifestyle, and education products.
colors:
  primary: "#3D2C5C"
  secondary: "#7C6F9A"
  tertiary: "#FF8FA3"
  neutral: "#FFF8F0"
  surface: "#FFFFFF"
  on-surface: "#2D1F4A"
  border: "#F0E6F5"
  accent-sun: "#FFD166"
  accent-mint: "#A8E6CF"
  accent-sky: "#A8D8FF"
  emotion-delighted: "#06D6A0"
  emotion-happy: "#83E8B0"
  emotion-neutral: "#C8B6E2"
  emotion-frustrated: "#FFB347"
  emotion-blocked: "#EF6F6C"
typography:
  headline-lg:
    fontFamily: "Quicksand, Nunito, -apple-system, system-ui, sans-serif"
    fontSize: 34px
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: -0.01em
  headline-md:
    fontFamily: "Quicksand, Nunito, -apple-system, system-ui, sans-serif"
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.35
  body-md:
    fontFamily: "Nunito, -apple-system, system-ui, sans-serif"
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.6
  label-sm:
    fontFamily: "Nunito, -apple-system, system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.4
  mono-sm:
    fontFamily: "JetBrains Mono, Menlo, Consolas, monospace"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: 10px
  md: 16px
  lg: 24px
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
    rounded: "{rounded.lg}"
    padding: 24px
  stage-card-active:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.tertiary}"
    rounded: "{rounded.lg}"
  edge-arrow:
    backgroundColor: "{colors.tertiary}"
---

# Playful Pastel

## Overview

Warm, soft, and welcoming. For consumer-facing flows where the journey should feel approachable: onboarding wizards, kids/education apps, lifestyle products, social apps. Rounded everything, gentle drop-shadow on cards, more whitespace than corporate.

## Colors

- **Primary (#3D2C5C):** Deep aubergine for body text — softer than pure black.
- **Secondary (#7C6F9A):** Mauve for metadata.
- **Tertiary (#FF8FA3):** Coral pink — the playful accent, used for the active stage.
- **Neutral (#FFF8F0):** Cream background — never pure white.
- **Accent triad** (sun / mint / sky): rotates across stages to give each one its own color identity in the map view.

## Typography

- **Quicksand** for headlines — rounded, friendly geometric sans.
- **Nunito** for body — pairs with Quicksand and has excellent screen rendering.

## Layout

8 px base scale. Stage cards 300 px wide, 24 px gap (more breathing room than corporate). Generous padding inside cards.

## Elevation & Depth

Soft elevation via `box-shadow: 0 4px 16px rgba(61, 44, 92, 0.08)` on cards. Active stage gets a slightly stronger shadow.

## Shapes

16 px corner radius on cards (lg = 24 px on chips and CTAs). Pill emotion chips.

## Components

- `stage-card` — cream-tinted surface with soft shadow, 24 px padding
- `stage-card-active` — coral border (2 px) plus stronger shadow
- `edge-arrow` — coral curved arrow with rounded line caps

## Do's and Don'ts

- Do rotate the accent triad (sun/mint/sky) across stages for visual rhythm
- Do let cards breathe — never reduce padding below 16 px
- Don't use the coral for anything other than the primary path
- Don't use sharp corners anywhere
