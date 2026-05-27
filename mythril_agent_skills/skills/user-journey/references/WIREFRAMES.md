# Wireframes — Layouts, Elements, Interactions (v2)

A `screen.layout` block tells the renderer what to draw inside the device frame. In v2, layouts use **nested containers** (`stack` / `grid` / `row`) instead of flat element arrays — this lets you build real UI structure (keypads, button rows, side-by-side cards).

Layouts model **lo-fi visual structure with real interactive semantics**. The renderer draws:

- Buttons that look like buttons (variant, state, icon)
- Inputs that look like inputs (label, placeholder, validation)
- Keypads laid out in a 3×4 grid (not a stack of "1 2 3" cards)
- List items with leading icon + trailing chevron (look clickable)
- Interactive elements **outlined in blue + numbered hotspot bubble** so reviewers see where the user can tap

Interactive elements with `transitions` pointing at them get hover tooltips (`→ to-screen · trigger: tap`) and click-to-jump in Flow view.

## Layout containers

Every screen has a root `layout`. Containers nest freely.

### `stack` — vertical column (default)

```json
{
  "type": "stack",
  "gap": "md",
  "elements": [ ... ]
}
```

Children stack top-to-bottom. `gap`: `none` | `xs` | `sm` | `md` | `lg` (default `md`).

### `grid` — N-column grid

```json
{
  "type": "grid",
  "cols": 3,
  "gap": "sm",
  "elements": [
    { "type": "keypad-button", "id": "k1", "label": "1" },
    { "type": "keypad-button", "id": "k2", "label": "2" },
    { "type": "keypad-button", "id": "k3", "label": "3" }
  ]
}
```

| Field | Notes |
|---|---|
| `cols` | Number of columns (1–6) |
| `gap` | Same vocabulary as stack |
| Children may set `span: N` to span multiple columns |

### `row` — horizontal row

```json
{
  "type": "row",
  "gap": "sm",
  "justify": "between",
  "elements": [
    { "type": "button", "label": "Cancel", "variant": "secondary" },
    { "type": "button", "id": "confirm", "label": "Confirm", "variant": "primary", "interactive": true }
  ]
}
```

`justify`: `start` | `end` | `between` | `around` | `center` (default `start`).

## Common element fields

All non-container elements support these fields:

| Field | Type | Notes |
|---|---|---|
| `type` | string | Element kind (see catalog below) |
| `id` | string | **Required** when `interactive: true` — used by `transitions.from_element`. Otherwise optional but recommended. |
| `interactive` | boolean | Default `false`. When `true`, the element gets a blue outline + numbered hotspot bubble + hover tooltip showing its outgoing transition. |
| `disabled` | boolean | Default `false`. Renders grayed out, no hotspot. |
| `state` | enum | `default` \| `hover` \| `pressed` \| `error`. Lets you freeze the element in a particular visual state. |
| `hotspot_number` | int | Manual hotspot label. If absent, the renderer auto-numbers interactive elements in document order. |
| `span` | int | When parent is a `grid`, span this many columns. Default `1`. |

## Element catalog

### `header`

```json
{"type": "header", "label": "ATM 主菜单", "back": false, "actions": ["settings"]}
```

Top title bar. `back: true` adds a `‹` chevron. `actions`: optional icon array (rendered right-aligned).

### `text`

```json
{"type": "text", "label": "请选择交易类型", "size": "lg", "weight": "bold", "color": "primary"}
```

Plain text. `size`: `sm` | `md` | `lg` | `xl`. `weight`: `regular` | `bold`. `color`: `primary` | `secondary` | `error` | `success` (optional, defaults to body color).

### `button`

```json
{
  "type": "button",
  "id": "confirm",
  "label": "确认",
  "variant": "primary",
  "icon": "✓",
  "interactive": true
}
```

Real-looking button. `variant`:

| Variant | Visual |
|---|---|
| `primary` | Filled accent color |
| `secondary` | Outlined |
| `ghost` | Text-only, accent color |
| `destructive` | Filled red |

`icon` (optional) renders before the label (use single glyph or named icon — see "Icon glyphs" below).

### `keypad-button`

```json
{"type": "keypad-button", "id": "k7", "label": "7"}
```

Square monospace button. Designed for numeric keypads inside a `grid` with `cols: 3` or `cols: 4`. Has pressed-state inner shadow.

### `icon-button`

```json
{"type": "icon-button", "id": "back", "icon": "←", "interactive": true, "badge": "3"}
```

Square button with only an icon. Optional `badge` shows a small number bubble (notifications, cart count).

### `form-field`

```json
{
  "type": "form-field",
  "id": "email",
  "label": "Email",
  "placeholder": "you@example.com",
  "prefilled": "alice@example.com",
  "validation": {"required": true, "error_message": "Email is required"},
  "state": "error"
}
```

Labeled input. `label` renders above; `placeholder` inside; `prefilled` shows pre-entered value. Setting `state: "error"` plus `validation.error_message` renders the field with a red border and error text below — useful for demoing error states.

### `list-item`

```json
{
  "type": "list-item",
  "id": "row-ippudo",
  "icon": "🍜",
  "title": "Ippudo",
  "subtitle": "Tonkotsu · 25 min · ⭐ 4.5",
  "trailing": "chevron",
  "interactive": true
}
```

Three-segment row: leading icon + title/subtitle stack + trailing element. `trailing`: `chevron` (default for interactive rows) | `badge:5` | `text:¥58` | `none`.

### `list` — wraps multiple `list-item`s

```json
{
  "type": "list",
  "elements": [
    {"type": "list-item", "title": "Ippudo", "subtitle": "⭐ 4.5"},
    {"type": "list-item", "title": "Ichiran", "subtitle": "⭐ 4.6"}
  ]
}
```

Convenience container. Equivalent to a `stack` with `gap: none` and dividers between items.

### `card`

```json
{
  "type": "card",
  "id": "card-akamaru",
  "image": {"ratio": "16:9", "label": "Akamaru photo"},
  "title": "Akamaru Modern",
  "body": "Signature pork bone broth · ¥58",
  "footer_actions": [
    {"label": "Add to cart", "variant": "primary", "id": "add-akamaru", "interactive": true}
  ]
}
```

Bordered card. All sub-fields optional. `footer_actions` is a row of buttons.

### `image-placeholder`

```json
{"type": "image-placeholder", "ratio": "16:9", "label": "Hero photo"}
```

Gray rectangle. `ratio`: `1:1` | `4:3` | `16:9` | `3:4`.

### `search-bar`

```json
{"type": "search-bar", "id": "search", "label": "Search restaurants", "interactive": true}
```

Search input with leading magnifier icon.

### `tab-bar`

```json
{
  "type": "tab-bar",
  "items": [
    {"id": "tab-home", "label": "Home", "icon": "🏠"},
    {"id": "tab-orders", "label": "Orders", "icon": "📦", "badge": "2"},
    {"id": "tab-me", "label": "Me", "icon": "👤"}
  ],
  "active": "tab-home"
}
```

Bottom navigation bar (mobile). Each item can have an `id` so transitions can attach to individual tabs.

### `chip`

```json
{"type": "chip", "id": "chip-500", "label": "¥500", "variant": "outlined", "interactive": true}
```

Pill / capsule. Useful for quick-amount selectors, filter chips. `variant`: `filled` | `outlined`.

### `toast`

```json
{"type": "toast", "label": "Saved!", "variant": "success"}
```

Floating notification. `variant`: `info` | `success` | `warning` | `error`.

### `progress`

```json
{"type": "progress", "kind": "linear", "value": 60, "label": "Processing..."}
```

Progress indicator. `kind`: `linear` (default) | `circular` | `indeterminate`. `value`: 0–100 (omit for `indeterminate`).

### `divider`

```json
{"type": "divider", "label": "or"}
```

Horizontal line. Optional `label` renders inline.

### `badge`

```json
{"type": "badge", "label": "NEW", "variant": "accent"}
```

Small inline label. `variant`: `accent` | `neutral` | `success` | `warning` | `error`.

### `spacer`

```json
{"type": "spacer", "size": "lg"}
```

Vertical whitespace inside a `stack`. `size`: `xs` | `sm` | `md` | `lg` | `xl`.

### `side-key-rail` — ATM/kiosk physical function keys

```json
{
  "type": "side-key-rail",
  "side": "right",
  "keys": [
    {"id": "k-r1", "label": "取款", "interactive": true},
    {"id": "k-r2", "label": "存款", "interactive": true},
    {"id": "k-r3", "label": "查询", "interactive": true},
    {"id": "k-r4", "label": "退卡", "interactive": true, "variant": "destructive"}
  ]
}
```

Vertical column of physical function keys docked to the **left or right edge** of the screen, with text labels pointing inward — exactly how real ATM and kiosk menus are structured. The label belongs to the on-screen menu item; the physical button is drawn as a colored notch on the bezel.

| Field | Notes |
|---|---|
| `side` | `left` \| `right` — which side of the screen the rail docks to |
| `keys` | Array of 1–6 keys (typical ATM is 4 per side) |
| Each key | `id`, `label`, optional `interactive`, `variant` (`primary` \| `secondary` \| `destructive`), `disabled` |

Use this on `atm-screen`, `kiosk-screen` (when the kiosk has physical buttons), or any device with hardware function keys. **Do NOT** use a `grid` of `button`s to fake this — the visual is genuinely different, and reviewers can immediately tell ATM vs. mobile.

### `hardware-slot` — physical port indicator on the device bezel

```json
{
  "type": "hardware-slot",
  "id": "slot-cash-out",
  "slot": "cash-out",
  "position": "bottom",
  "label": "请取钞",
  "interactive": true
}
```

Marks a physical port on the device chassis (cash dispenser, card reader, receipt printer, deposit slot, biometric scanner, etc.). Only meaningful when the screen has `chrome: "panel"` enabled — otherwise it renders as a small annotated rectangle inside the screen body as a fallback.

| Field | Notes |
|---|---|
| `slot` | `card-reader` \| `cash-out` \| `cash-in` \| `deposit` \| `receipt` \| `biometric` \| `scanner` \| `nfc` \| `pin-pad` \| `custom` |
| `position` | `top` \| `bottom` \| `left` \| `right` — which edge of the device chassis it sits on. Ignored when `chrome` is off. |
| `label` | Short caption shown next to the slot (e.g. "请取钞", "Insert card here") |
| `interactive` | Optional. If true, gets a hotspot bubble — useful for triggering the next screen when the user "inserts a card" or "takes the cash". |

The slot kind drives a small glyph: `▭` for card-reader, `‖‖‖` for cash, `▤` for receipt, `◉` for biometric, etc.

## Device chrome (machine bezel)

For devices where **the physical chassis around the screen matters** — ATMs, kiosks, payment terminals — set the top-level `screen.chrome` field:

```json
{
  "id": "main-menu",
  "kind": "atm-screen",
  "chrome": "panel",
  "hardware": [
    {"slot": "card-reader", "position": "top",    "label": "插卡口"},
    {"slot": "cash-out",    "position": "bottom", "label": "出钞口"},
    {"slot": "receipt",     "position": "bottom", "label": "凭条口"}
  ],
  "layout": { "...": "normal layout, plus any side-key-rail inside" }
}
```

| Field | Notes |
|---|---|
| `chrome` | `"none"` (default) \| `"panel"` — wraps the screen frame inside a beige/dark device panel with thick bezels |
| `hardware` | Array of `hardware-slot`-shaped entries rendered on the bezel (not inside the screen body). Each entry is interpreted the same as inline `hardware-slot` elements. |

When `chrome: "panel"` is set:
- The screen frame gets a thick outer bezel (4:3 ratio preserved inside).
- `hardware[]` entries are positioned on the matching bezel edge.
- `side-key-rail` elements found inside `layout` are pulled out and stuck to the bezel edge, matching their `side` field — this is exactly how real ATM menus work.

Use `chrome: "panel"` on key decision-point screens (main menu, transaction selection) and screens where hardware interaction is the point (insert card, take cash, scan QR). Skip it on transient processing/loading screens — the bezel just adds noise there.

## Icon glyphs

Wherever `icon` is supported, you can pass:

- A single unicode character: `"←"`, `"⌕"`, `"🍜"`, `"✓"`
- A named icon (renderer maps to a glyph): `"back"` | `"more"` | `"search"` | `"share"` | `"favorite"` | `"menu"` | `"close"` | `"settings"` | `"filter"` | `"add"` | `"check"` | `"info"` | `"warning"` | `"error"`

Stick to one style per screen for consistency.

## Interactivity model

The renderer treats `interactive: true` elements as **hotspots**. For each hotspot:

1. **Visual indicator** — element gets a 2px dashed accent-color outline + small numbered bubble in its corner (`1`, `2`, ...) so reviewers know "you can tap this".
2. **Hover tooltip** — when the cursor enters a hotspot, a small card appears next to it: `→ Main menu · trigger: tap`. Sourced from the screen's `transitions` whose `from_element` matches the element's `id`.
3. **Click to jump** — clicking a hotspot navigates Flow view to the target screen (animated slide). Back-button restores the previous screen.
4. **Hotspot list** — Flow view's right panel lists all transitions (`1. 点击确认 → 主菜单 · tap` etc.), each clickable.

A `transitions` entry with `from_element: "any"` makes the **entire screen** a single tap target — useful for splash screens or "tap to continue" prompts. In that case no hotspot bubble is drawn; the screen body has a subtle dashed outline instead.

## Authoring tips

- **Define each screen once.** If "main menu" appears in two stages, define it once and reference it twice (`step.screen_refs`).
- **Pick the right device kind, and stay true to its form.** An ATM is not a phone in landscape; a TV remote is not a mouse pointer. See "Device-aware modeling" below.
- **Make interactive elements obvious.** A screen where every other element is `interactive: true` is a screen where nothing stands out. Reserve `interactive` for the actual tap targets a user must hit to advance.
- **Always set `is_default: true` on the happy-path transition** for each screen. The Presenter Space-to-advance and the auto-numbered flow rely on it.
- **Use real strings.** A wireframe is most useful when the copy is real (`"取款 ¥500"`, not `"Button label"`). Lo-fi is a layout-and-language exercise, not lorem-ipsum filler.
- **Use `grid` for keypads, button bars, dashboard cards.** A `stack` of `card`s that look like keys does not communicate "this is a keypad".
- **Reserve modals for actual modals.** Don't use `modal` kind for a normal screen — Flow view's nav groups by kind and overlays modals on the preceding screen.

## Device-aware modeling

The same `button` and `stack` primitives can model a phone or a 1980s ATM — but the result only looks **right** if you reach for the device-specific vocabulary when the device demands it. A screen that should feel like an ATM but is built with `grid` + `button` will look like a phone in landscape mode.

| Device `kind`        | Looks-right checklist |
|---|---|
| `mobile-screen`      | Touch buttons in `stack`/`grid`; optional `tab-bar` at the bottom; never side-key-rail. |
| `tablet-screen`      | Same as mobile but wider; multi-column lists OK. |
| `desktop-window`     | `header` + content; multi-column dashboards; hover states matter. |
| `atm-screen`         | **Almost always uses `side-key-rail` for menus**, not a center grid of buttons. Key transactional screens (main menu, cash-out, deposit) should set `chrome: "panel"` with `hardware[]` for card-reader / cash-out / receipt slots. Numeric input uses a `grid cols=3` keypad. |
| `kiosk-screen`       | Often touch-only (no side-key-rail). Big chunky buttons, large fonts; hardware like `barcode-scanner` or `nfc` go in `hardware[]` with `chrome: "panel"` if a chassis is visible. |
| `tv-screen`          | Limited input (remote): focused-state element + numeric-grid navigation. Avoid scrolling lists; use horizontal carousels. Big text. |
| `email`              | Subject + body + CTA; ignore touch affordances. |
| `notification`       | One-line title + body + 1–2 action buttons; aspect is wide & short. |

If your screen is `kind: atm-screen` and your `layout` contains zero `side-key-rail` and zero `hardware-slot` elements, you almost certainly modeled it as a phone. Add either a side-key-rail or set `chrome: "panel"` with appropriate `hardware[]` slots. The `validate_screens.py` validator flags this.

## End-to-end example A: an ATM PIN screen (no chrome, numeric keypad)

```json
{
  "id": "pin-entry",
  "kind": "atm-screen",
  "title": "密码输入",
  "stage_id": "authenticate",
  "layout": {
    "type": "stack",
    "gap": "md",
    "elements": [
      {"type": "header", "label": "XX 银行 ATM"},
      {"type": "text", "label": "请输入密码", "size": "xl", "weight": "bold"},
      {"type": "text", "label": "Enter your PIN", "size": "sm", "color": "secondary"},
      {"type": "form-field", "id": "pin", "label": "", "placeholder": "● ● ● ● ● ●"},
      {
        "type": "grid",
        "cols": 3,
        "gap": "sm",
        "elements": [
          {"type": "keypad-button", "id": "k1", "label": "1"},
          {"type": "keypad-button", "id": "k2", "label": "2"},
          {"type": "keypad-button", "id": "k3", "label": "3"},
          {"type": "keypad-button", "id": "k4", "label": "4"},
          {"type": "keypad-button", "id": "k5", "label": "5"},
          {"type": "keypad-button", "id": "k6", "label": "6"},
          {"type": "keypad-button", "id": "k7", "label": "7"},
          {"type": "keypad-button", "id": "k8", "label": "8"},
          {"type": "keypad-button", "id": "k9", "label": "9"},
          {"type": "keypad-button", "id": "cancel", "label": "取消", "variant": "secondary", "interactive": true},
          {"type": "keypad-button", "id": "k0", "label": "0"},
          {"type": "keypad-button", "id": "confirm", "label": "确认", "variant": "primary", "interactive": true}
        ]
      },
      {"type": "text", "label": "剩余尝试次数: 3 次", "size": "sm", "color": "secondary"}
    ]
  },
  "transitions": [
    {"from_element": "confirm", "trigger": "tap", "to_screen": "main-menu",  "label": "确认 → 主菜单",  "is_default": true},
    {"from_element": "cancel",  "trigger": "tap", "to_screen": "welcome",    "label": "取消 → 返回欢迎"}
  ]
}
```

## End-to-end example B: an ATM main menu (chrome + side-key-rail + hardware)

This is what an ATM main menu actually looks like — and the example you should model your own ATM main-menu / cash-out / deposit screens after:

```json
{
  "id": "main-menu",
  "kind": "atm-screen",
  "title": "主菜单",
  "stage_id": "select-transaction",
  "chrome": "panel",
  "hardware": [
    {"slot": "card-reader", "position": "top",    "label": "插卡口"},
    {"slot": "receipt",     "position": "bottom", "label": "凭条口"},
    {"slot": "cash-out",    "position": "bottom", "label": "出钞口"}
  ],
  "layout": {
    "type": "stack",
    "gap": "lg",
    "elements": [
      {"type": "header", "label": "XX 银行 — 请选择服务"},
      {"type": "text", "label": "欢迎, 张明", "size": "sm", "color": "secondary"},
      {
        "type": "row",
        "justify": "between",
        "gap": "lg",
        "elements": [
          {
            "type": "side-key-rail",
            "side": "left",
            "keys": [
              {"id": "k-withdrawal", "label": "取款", "interactive": true, "variant": "primary"},
              {"id": "k-deposit",    "label": "存款", "interactive": true, "variant": "primary"},
              {"id": "k-balance",    "label": "余额查询", "interactive": true},
              {"id": "k-other",      "label": "其他业务", "interactive": true}
            ]
          },
          {
            "type": "stack",
            "gap": "sm",
            "elements": [
              {"type": "text", "label": "请按左右两侧物理键选择业务", "size": "md", "color": "secondary"}
            ]
          },
          {
            "type": "side-key-rail",
            "side": "right",
            "keys": [
              {"id": "k-transfer", "label": "转账汇款", "interactive": true},
              {"id": "k-payment",  "label": "缴费充值", "interactive": true},
              {"id": "k-language", "label": "Language", "interactive": true},
              {"id": "k-exit",     "label": "退卡", "interactive": true, "variant": "destructive"}
            ]
          }
        ]
      }
    ]
  },
  "transitions": [
    {"from_element": "k-withdrawal", "trigger": "tap", "to_screen": "withdrawal-amount", "label": "取款 → 选金额", "is_default": true},
    {"from_element": "k-deposit",    "trigger": "tap", "to_screen": "deposit-select",    "label": "存款 → 选类型"},
    {"from_element": "k-exit",       "trigger": "tap", "to_screen": "welcome",           "label": "退卡 → 返回欢迎"}
  ]
}
```
