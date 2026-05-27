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
- **Pick the right device kind.** ATM screens are not mobile screens — use `atm-screen` for landscape kiosks.
- **Make interactive elements obvious.** A screen where every other element is `interactive: true` is a screen where nothing stands out. Reserve `interactive` for the actual tap targets a user must hit to advance.
- **Always set `is_default: true` on the happy-path transition** for each screen. The Presenter Space-to-advance and the auto-numbered flow rely on it.
- **Use real strings.** A wireframe is most useful when the copy is real (`"取款 ¥500"`, not `"Button label"`). Lo-fi is a layout-and-language exercise, not lorem-ipsum filler.
- **Use `grid` for keypads, button bars, dashboard cards.** A `stack` of `card`s that look like keys does not communicate "this is a keypad".
- **Reserve modals for actual modals.** Don't use `modal` kind for a normal screen — Flow view's nav groups by kind and overlays modals on the preceding screen.

## End-to-end example: an ATM PIN screen

```json
{
  "id": "pin-entry",
  "kind": "atm-screen",
  "title": "密码输入",
  "stage_id": "approach-insert",
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
    {
      "from_element": "confirm",
      "trigger": "tap",
      "to_screen": "main-menu",
      "label": "点击确认 → 主菜单",
      "is_default": true
    },
    {
      "from_element": "cancel",
      "trigger": "tap",
      "to_screen": "welcome",
      "label": "取消 → 返回欢迎",
      "is_error_path": false
    }
  ]
}
```
