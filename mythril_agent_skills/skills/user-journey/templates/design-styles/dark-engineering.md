---
version: alpha
name: Dark Engineering
description: High-contrast dark surface with mono type and neon accent. For devtools, infra, and observability flows.
colors:
  primary: "#E5E7EB"
  secondary: "#9CA3AF"
  tertiary: "#22D3EE"
  neutral: "#0B0F17"
  surface: "#111827"
  surface-elevated: "#1F2937"
  on-surface: "#F3F4F6"
  border: "#1F2937"
  border-strong: "#374151"
  emotion-delighted: "#34D399"
  emotion-happy: "#A7F3D0"
  emotion-neutral: "#6B7280"
  emotion-frustrated: "#FBBF24"
  emotion-blocked: "#F87171"
typography:
  headline-lg:
    fontFamily: "JetBrains Mono, IBM Plex Mono, Menlo, Consolas, monospace"
    fontSize: 28px
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: -0.01em
  headline-md:
    fontFamily: "JetBrains Mono, IBM Plex Mono, Menlo, Consolas, monospace"
    fontSize: 18px
    fontWeight: 600
    lineHeight: 1.35
  body-md:
    fontFamily: "Inter, -apple-system, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.55
  label-sm:
    fontFamily: "JetBrains Mono, Menlo, Consolas, monospace"
    fontSize: 11px
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0.08em
  mono-sm:
    fontFamily: "JetBrains Mono, Menlo, Consolas, monospace"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: 2px
  md: 4px
  lg: 6px
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
    padding: 18px
  stage-card-active:
    backgroundColor: "{colors.surface-elevated}"
    textColor: "{colors.tertiary}"
    rounded: "{rounded.md}"
  edge-arrow:
    backgroundColor: "{colors.tertiary}"
---

# Dark Engineering

## Overview

Terminal aesthetic — dark surface, mono headlines, single neon accent. For developer-facing products (DX tools, infrastructure, observability dashboards) and internal engineering audiences. Information-dense; minimal decoration.

## Colors

- **Primary (#E5E7EB):** Off-white for body text.
- **Secondary (#9CA3AF):** Mid-gray for metadata.
- **Tertiary (#22D3EE):** Neon cyan — the active stage and primary CTAs.
- **Neutral (#0B0F17):** Near-black page background.
- **Surface (#111827):** Card background — one step lighter than the page.
- **Surface elevated (#1F2937):** Active card — two steps lighter.

## Typography

- **JetBrains Mono** for headlines, labels, and code-like content (step IDs, metric names).
- **Inter** for body prose — mono headlines are striking but mono body fatigues.

## Layout

8 px base scale. Stage cards 260 px wide, 12 px gap. Tighter than the other styles — dev tools assume the reader scans more than browses.

## Elevation & Depth

No shadows. Hierarchy comes from layered surfaces (`neutral` → `surface` → `surface-elevated`). 1 px border in `border-strong` on the active card.

## Shapes

4 px corner radius. Sharp enough to feel engineered, soft enough to avoid harshness.

## Components

- `stage-card` — surface card with 1 px `border` (same color as bg, so invisible until active)
- `stage-card-active` — elevated background + 1 px cyan border + cyan inner glow `box-shadow: inset 0 0 0 1px #22D3EE`
- `edge-arrow` — cyan with 2 px stroke; dashed for fallback / error edges

## Do's and Don'ts

- Do use mono for stage labels (they read like commands)
- Do keep emotion chips small and unobtrusive
- Don't introduce a light-mode surface
- Don't use the cyan for anything decorative — it's reserved for the active path
