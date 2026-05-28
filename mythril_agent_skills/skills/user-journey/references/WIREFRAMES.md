# Wireframes — Layouts, Elements, Interactions (v3)

A `screen.layout` block tells the renderer what to draw inside the device frame. The element vocabulary is split into three tiers:

1. **Layout containers** — `stack`, `grid`, `row`, `section` (composition).
2. **Composition primitives** — `app-bar`, `section`, `key-value`, `stat-tile`, `alert`, `step-indicator`, `empty-state`, `footer-bar`, `avatar`. These encode common **design patterns** so screens compose well by default instead of devolving into flat element soup.
3. **Atoms** — `button`, `text`, `form-field`, `list-item`, `chip`, `divider`, `keypad-button`, `side-key-rail`, `hardware-slot`, etc.

The renderer draws:

- Buttons that look like buttons (variant, state, icon)
- Inputs that look like inputs (label, placeholder, validation)
- Keypads in a 3×4 grid (not a stack of "1 2 3" cards)
- List items with leading icon + trailing chevron
- Sections with proper title + body + optional surface
- Stat tiles for dashboards, alerts for inline banners
- Interactive elements **outlined in blue** so reviewers see where the user can tap

The screen is wrapped in an **outer colored card** whose color comes from `screen.state` (`default` / `loading` / `success` / `error` / `warning`). The card sits on the canvas and is the unit the user pans / zooms / drags arrows to.

## The zone model — every screen has 3 zones

Real screens almost always decompose into:

| Zone | Pattern | Typical elements |
|---|---|---|
| **Top** (always visible) | `app-bar` (preferred) or `header` | title, back chevron, action icons, search |
| **Body** (scrollable / main content) | one or more `section`s | text, forms, lists, cards, stat tiles, alerts, step indicators, empty states |
| **Bottom** (always visible) | `tab-bar` (navigation) or `footer-bar` (action) | tabs, primary CTA, summary |

Default `screen.layout` skeleton:

```json
{
  "type": "stack",
  "gap": "md",
  "elements": [
    {"type": "app-bar", "title": "...", "back": true},
    {"type": "section", "elements": [ ... ]},
    {"type": "section", "title": "...", "elements": [ ... ]},
    {"type": "footer-bar", "actions": [ ... ]}
  ]
}
```

The zone model is what makes a screen **read as a screen**, not as a vertical pile of widgets.

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

Children stack top-to-bottom. `gap`: `none` | `xs` | `sm` | `md` | `lg` | `xl` | `2xl` (default `md`). The same vocabulary works on `row`, `grid`, and `side-key-rail`.

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

## Composition primitives

These encode the **design patterns** every modern UI uses. Reach for them BEFORE dropping atoms into a raw `stack`.

### `app-bar` — top-of-screen title bar

```json
{
  "type": "app-bar",
  "title": "Account",
  "subtitle": "Tier: Premium",
  "back": true,
  "icon": "👤",
  "variant": "default",
  "actions": [
    {"icon": "search", "id": "search"},
    {"icon": "settings", "id": "settings", "badge": "2"}
  ]
}
```

| Field | Notes |
|---|---|
| `title` | Main label (required) |
| `subtitle` | Optional second line (e.g. status, breadcrumb) |
| `back` | `true` adds a `‹` chevron |
| `icon` | Optional leading icon (named or unicode) |
| `variant` | `default` (slim) \| `prominent` (taller, larger title) |
| `actions` | Right-aligned icon list; each `{icon, id, badge?}` |

Prefer `app-bar` over the older `header` for any screen where the top zone matters (90% of mobile + tablet + desktop). Keep `header` only for inline mini-titles inside the body.

### `section` — grouped block of content

```json
{
  "type": "section",
  "title": "Recent activity",
  "subtitle": "Last 7 days",
  "action": {"label": "See all", "id": "see-all-activity"},
  "variant": "surface",
  "gap": "sm",
  "elements": [
    {"type": "list-item", "title": "...", "subtitle": "..."},
    {"type": "list-item", "title": "...", "subtitle": "..."}
  ]
}
```

| Field | Notes |
|---|---|
| `title` | Optional group label |
| `subtitle` | Optional secondary label |
| `action` | Optional inline action on the right (string or `{label, id}`) |
| `variant` | `flat` (default, transparent) \| `surface` (white card with border + padding) |
| `gap` | Spacing between children. Same vocabulary as stack. Default `md`. |
| `elements` | Children rendered inside the body |

Group related rows into a `section` rather than dropping 8 list-items into a bare stack. A screen with **2–4 named sections** reads vastly better than a stack of 30 raw items.

### `section-header` — inline group label between blocks

```json
{"type": "section-header", "eyebrow": "PAYMENT", "label": "Choose method", "trailing": "Step 2 of 4"}
```

A lighter alternative to `section` when you just need a label between two groups (no surface, no nested elements).

### `key-value` and `key-value-list` — summaries and definition lists

```json
{
  "type": "key-value-list",
  "density": "comfortable",
  "items": [
    {"key": "金额", "value": "¥500", "emphasis": true},
    {"key": "到账卡", "value": "*** 4521"},
    {"key": "手续费", "value": "¥0.00", "color": "success"},
    {"key": "预计到账", "value": "立即"}
  ]
}
```

| Field | Notes |
|---|---|
| `items` | Array of `{key, value, emphasis?, color?}` |
| `density` | `compact` \| `comfortable` (default) \| `spacious` |
| `key` | Label on the left |
| `value` | Value on the right (right-aligned) |
| `emphasis` | Bolds the value |
| `color` | `primary` \| `secondary` \| `success` \| `warning` \| `error` |

Use this for **order summaries, receipt confirmations, settings, account details, transaction details, summary bottom-sheets**. Anything where the user is reading "label → value" pairs.

### `stat-tile` — single metric for dashboards

```json
{
  "type": "stat-tile",
  "label": "Daily revenue",
  "value": "¥12,480",
  "unit": "",
  "delta": "+8.2%",
  "delta_direction": "up",
  "caption": "vs. last week"
}
```

| Field | Notes |
|---|---|
| `label` | Metric name (uppercase, small) |
| `value` | Main number |
| `unit` | Optional unit (e.g. `"%"`, `"ms"`, `"req/s"`) |
| `delta` | Change indicator (e.g. `"+8.2%"`, `"-3"`); rendered as pill |
| `delta_direction` | `up` (green) \| `down` (red) \| `flat` (neutral); inferred from sign if omitted |
| `caption` | Small caption below |

Compose a dashboard by putting 3–4 `stat-tile`s inside a `grid` with `cols: 3` or `cols: 4`. Also aliased as `metric` for convenience.

### `alert` — inline banner with severity

```json
{
  "type": "alert",
  "severity": "warning",
  "icon": "warning",
  "title": "余额不足",
  "message": "您的账户余额低于最低取款金额。",
  "action": {"label": "充值", "id": "topup"}
}
```

| Field | Notes |
|---|---|
| `severity` | `info` (default) \| `success` \| `warning` \| `error` |
| `icon` | Named icon or unicode (auto-pick if omitted) |
| `title` | Optional bold first line |
| `message` | Optional body line |
| `action` | Optional inline action (string or `{label, id}`) |

Use over `toast` when the banner is part of the screen body (not a transient notification).

### `step-indicator` — multi-step progress

```json
{
  "type": "step-indicator",
  "orientation": "horizontal",
  "active": 1,
  "steps": ["选择金额", "确认", "处理中", "完成"]
}
```

| Field | Notes |
|---|---|
| `steps` | Array of step labels (strings) or `{label}` objects |
| `active` | 0-based index of the **current** step (steps before it render as "done") |
| `orientation` | `horizontal` (default) \| `vertical` |

Use this whenever the user is N steps into an M-step flow. Communicates "where you are" at a glance.

### `empty-state` — no-content placeholder

```json
{
  "type": "empty-state",
  "icon": "📭",
  "title": "暂无订单",
  "message": "您还没有任何订单。开始下您的第一单。",
  "action": {"label": "开始下单", "id": "start-order", "interactive": true}
}
```

| Field | Notes |
|---|---|
| `icon` | Big illustration glyph |
| `title` | Headline |
| `message` | One-line description |
| `action` | Primary CTA (string or `{label, id, interactive}`) |

Every list / dashboard / search-results screen has an empty state. Define it as a separate `screen` with `state: "default"` and an `empty-state` element. Reviewers love seeing the empty path explicitly.

### `footer-bar` — bottom-pinned action bar

```json
{
  "type": "footer-bar",
  "summary": {"label": "Total", "value": "¥520.00"},
  "actions": [
    {"label": "Cancel", "variant": "secondary", "id": "cancel"},
    {"label": "Confirm", "variant": "primary", "id": "confirm", "interactive": true}
  ]
}
```

Different from `tab-bar` — `tab-bar` is for navigation, `footer-bar` is for the **primary action on the current screen** (with optional total / context on the left).

### `avatar` — person identity badge

```json
{"type": "avatar", "initials": "ZM", "label": "张明", "subtitle": "Premium · 持卡 8 年", "size": "lg"}
```

| Field | Notes |
|---|---|
| `initials` | 1–2 character monogram |
| `image` | If true, renders a colored circle placeholder instead of initials |
| `color` | Background color override |
| `label` | Optional name to the right of the avatar |
| `subtitle` | Optional secondary line |
| `size` | `sm` \| `md` (default) \| `lg` \| `xl` |

## Common element fields

All non-container elements support these fields:

| Field | Type | Notes |
|---|---|---|
| `type` | string | Element kind (see catalog below) |
| `id` | string | **Required** when an arrow's `from` references this element via `<screen-id>#<element-id>`. Required when `interactive: true`. |
| `interactive` | boolean | Default `false`. When `true`, the element gets a blue dashed outline so it reads as tappable. |
| `disabled` | boolean | Default `false`. Renders grayed out. |
| `state` | enum | `default` \| `hover` \| `pressed` \| `error`. Visual hover/pressed/error state for the element itself (independent of the outer screen.state). |
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

Square monospace button. Designed for numeric keypads inside a `grid` with `cols: 3` or `cols: 4`.

### `icon-button`

```json
{"type": "icon-button", "id": "back", "icon": "←", "interactive": true, "badge": "3"}
```

Square button with only an icon. Optional `badge` shows a small number bubble.

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

Labeled input. `label` renders above; `placeholder` inside; `prefilled` shows pre-entered value. Setting `state: "error"` plus `validation.error_message` renders the field with a red border and error text below.

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

Bottom navigation bar (mobile). Each item can have an `id` so arrows can attach to individual tabs.

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
  "gap": "lg",
  "keys": [
    {"id": "k-r1", "label": "取款", "interactive": true},
    {"id": "k-r2", "label": "存款", "interactive": true},
    {"id": "k-r3", "label": "查询", "interactive": true},
    {"id": "k-r4", "label": "退卡", "interactive": true, "variant": "destructive"}
  ]
}
```

Vertical column of physical function keys docked to the **left or right edge** of the screen, with text labels pointing inward. The label belongs to the on-screen menu item; the physical button is drawn as a colored notch on the bezel.

| Field | Notes |
|---|---|
| `side` | `left` \| `right` — which side of the screen the rail docks to |
| `gap` | `xs` \| `sm` \| `md` \| `lg` \| `xl` \| `2xl` — vertical spacing between keys. Default `md`. Bump to `lg`/`xl` when keys feel crammed. |
| `keys` | Array of 1–6 keys (typical ATM is 4 per side) |
| Each key | `id`, `label`, optional `interactive`, `variant` (`primary` \| `secondary` \| `destructive`), `disabled` |

Use this on `atm-screen`, `kiosk-screen` (when the kiosk has physical buttons), or any device with hardware function keys. **Do NOT** use a `grid` of `button`s to fake this — reviewers can immediately tell ATM vs. mobile.

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

Marks a physical port on the device chassis (cash dispenser, card reader, receipt printer, deposit slot, biometric scanner, etc.). Only meaningful when the screen has `chrome: "panel"` enabled.

| Field | Notes |
|---|---|
| `slot` | `card-reader` \| `cash-out` \| `cash-in` \| `deposit` \| `receipt` \| `biometric` \| `scanner` \| `nfc` \| `pin-pad` \| `custom` |
| `position` | `top` \| `bottom` \| `left` \| `right` — which edge of the device chassis it sits on |
| `label` | Short caption (e.g. "请取钞", "Insert card here") |
| `interactive` | If true, an arrow can originate from this slot. |

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
| `chrome` | `"none"` (default for mobile/desktop) \| `"panel"` (default for ATM/kiosk) |
| `hardware` | Array of `hardware-slot`-shaped entries rendered on the bezel |

When `chrome: "panel"` is set:
- The screen frame gets a thick outer bezel.
- `hardware[]` entries are positioned on the matching bezel edge.
- `side-key-rail` elements inside `layout` render flush with the bezel edge.

## Icon glyphs

Wherever `icon` is supported, you can pass:

- A single unicode character: `"←"`, `"⌕"`, `"🍜"`, `"✓"`
- A named icon (renderer maps to a glyph): `"back"` | `"more"` | `"search"` | `"share"` | `"favorite"` | `"menu"` | `"close"` | `"settings"` | `"filter"` | `"add"` | `"check"` | `"info"` | `"warning"` | `"error"`

Stick to one style per screen for consistency.

## Anchor model for arrows

When an arrow's `from` includes an `#<element-id>` suffix (e.g.
`"main-menu#k-withdraw"`), the renderer locates the element inside the
card and anchors the arrow to its edge. The element's
`data-anchor-side` (set automatically for side-key-rail keys and
hardware slots based on their `side` / `position`) biases the arrow
curvature so it exits the right edge of the card.

If no `#<element-id>` is provided, the arrow anchors to the card's
right edge by default. Use that form for whole-screen transitions
(timeout, auto-advance).

## Authoring tips

- **Define each screen once.** If "main menu" appears in two stages, define it once and reference it twice (`step.screen_refs`).
- **Pick the right device kind, and stay true to its form.** An ATM is not a phone in landscape; a TV remote is not a mouse pointer.
- **Make interactive elements obvious.** A screen where every other element is `interactive: true` is a screen where nothing stands out. Reserve `interactive` for the actual tap targets.
- **Set screen.state intentionally.** The colored outer card is the fastest way for a reviewer to skim the canvas. Use `success` for actual success acknowledgements, `error` for failure screens, `warning` for confirmations / risk screens, `loading` for processing — not for everything.
- **Always set `is_default: true` on the happy-path arrow** out of each screen. At most one per source screen.
- **Use real strings.** A wireframe is most useful when the copy is real (`"取款 ¥500"`, not `"Button label"`). Lo-fi is a layout-and-language exercise, not lorem-ipsum filler.
- **Use `grid` for keypads, button bars, dashboard cards.** A `stack` of `card`s that look like keys does not communicate "this is a keypad".

## Device-aware modeling

The same `button` and `stack` primitives can model a phone or a 1980s ATM — but the result only looks **right** if you reach for the device-specific vocabulary when the device demands it.

| Device `kind`        | Looks-right checklist |
|---|---|
| `mobile-screen`      | Touch buttons in `stack`/`grid`; optional `tab-bar` at the bottom; never side-key-rail. |
| `tablet-screen`      | Same as mobile but wider; multi-column lists OK. |
| `desktop-window`     | `header` + content; multi-column dashboards; hover states matter. |
| `atm-screen`         | **Almost always uses `side-key-rail` for menus**, not a center grid of buttons. Key transactional screens (main menu, cash-out, deposit) should set `chrome: "panel"` with `hardware[]`. Numeric input uses a `grid cols=3` keypad. |
| `kiosk-screen`       | Often touch-only. Big chunky buttons, large fonts; hardware like `barcode-scanner` or `nfc` go in `hardware[]` with `chrome: "panel"`. |
| `tv-screen`          | Limited input (remote): focused-state element + numeric-grid navigation. Avoid scrolling lists; use horizontal carousels. Big text. |
| `email`              | Subject + body + CTA; ignore touch affordances. |
| `notification`       | One-line title + body + 1–2 action buttons; aspect is wide & short. |

If your screen is `kind: atm-screen` and your `layout` contains zero `side-key-rail` and zero `hardware-slot` elements, you almost certainly modeled it as a phone. `validate_screens.py` flags this.

## End-to-end example A: an ATM PIN screen (numeric keypad)

```json
{
  "id": "pin-entry",
  "kind": "atm-screen",
  "title": "密码输入",
  "stage_id": "authenticate",
  "state": "default",
  "chrome": "panel",
  "hardware": [
    {"slot": "pin-pad", "position": "right", "label": "PIN-PAD"}
  ],
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
      }
    ]
  }
}
```

Then in the top-level `arrows[]`:

```json
{ "from": "pin-entry#confirm", "to": "main-menu", "label": "确认", "trigger": "tap", "kind": "success", "is_default": true },
{ "from": "pin-entry#cancel",  "to": "welcome",   "label": "取消", "trigger": "tap", "kind": "cancel" }
```

## End-to-end example B: an ATM main menu (chrome + side-key-rail + hardware)

```json
{
  "id": "main-menu",
  "kind": "atm-screen",
  "title": "主菜单",
  "stage_id": "select-transaction",
  "state": "default",
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
  }
}
```

Then in `arrows[]`:

```json
{ "from": "main-menu#k-withdrawal", "to": "withdrawal-amount", "label": "取款", "trigger": "tap", "kind": "default", "is_default": true },
{ "from": "main-menu#k-deposit",    "to": "deposit-select",    "label": "存款", "trigger": "tap", "kind": "default" },
{ "from": "main-menu#k-exit",       "to": "welcome",           "label": "退卡", "trigger": "tap", "kind": "cancel" }
```

## End-to-end example C: a mobile dashboard (zone model + sections + stat tiles)

A real mobile screen uses **app-bar + sections** instead of a flat stack. This is the pattern reviewers expect:

```json
{
  "id": "home-dashboard",
  "kind": "mobile-screen",
  "title": "Home",
  "stage_id": "habit",
  "state": "default",
  "layout": {
    "type": "stack",
    "gap": "md",
    "elements": [
      {
        "type": "app-bar",
        "variant": "prominent",
        "title": "你好,张明",
        "subtitle": "周三 · 11月13日",
        "actions": [
          {"icon": "search", "id": "search"},
          {"icon": "settings", "id": "settings", "badge": "2"}
        ]
      },
      {
        "type": "section",
        "title": "本周概览",
        "action": {"label": "查看详情", "id": "see-week"},
        "elements": [
          {
            "type": "grid",
            "cols": 2,
            "gap": "sm",
            "elements": [
              {"type": "stat-tile", "label": "收入", "value": "¥12,480", "delta": "+8.2%", "delta_direction": "up"},
              {"type": "stat-tile", "label": "订单",  "value": "37",      "delta": "+5",     "delta_direction": "up"}
            ]
          }
        ]
      },
      {
        "type": "section",
        "title": "待办",
        "subtitle": "3 项需要您处理",
        "variant": "surface",
        "elements": [
          {"type": "list-item", "icon": "📦", "title": "确认订单 #1241", "subtitle": "今日 14:00 截止", "trailing": "chevron", "id": "todo-1241", "interactive": true},
          {"type": "list-item", "icon": "💳", "title": "更新支付方式", "subtitle": "本月到期",         "trailing": "chevron", "id": "todo-payment", "interactive": true},
          {"type": "list-item", "icon": "📑", "title": "查看月度报告", "subtitle": "10 月已出",        "trailing": "chevron", "id": "todo-report",  "interactive": true}
        ]
      },
      {
        "type": "alert",
        "severity": "info",
        "title": "新功能上线",
        "message": "扫码立即体验快捷收款。",
        "action": {"label": "了解", "id": "feature-pay"}
      },
      {
        "type": "tab-bar",
        "items": [
          {"id": "tab-home",   "label": "首页",   "icon": "🏠"},
          {"id": "tab-orders", "label": "订单",   "icon": "📦", "badge": "3"},
          {"id": "tab-me",     "label": "我的",   "icon": "👤"}
        ],
        "active": "tab-home"
      }
    ]
  }
}
```

Notice the **rhythm**: app-bar → stat-tile grid in a labeled section → todo list in a surface section → alert → bottom tab-bar. No two adjacent blocks are the same primitive, and every block has a clear job.

## End-to-end example D: an order confirmation (zone + key-value + footer-bar)

```json
{
  "id": "order-confirm",
  "kind": "mobile-screen",
  "title": "确认订单",
  "stage_id": "checkout",
  "state": "default",
  "layout": {
    "type": "stack",
    "gap": "md",
    "elements": [
      {"type": "app-bar", "title": "确认订单", "back": true},
      {"type": "step-indicator", "active": 2, "steps": ["选择", "填写", "确认", "完成"]},
      {
        "type": "section",
        "title": "收货地址",
        "action": {"label": "更换", "id": "change-address"},
        "elements": [
          {"type": "key-value", "key": "收件人", "value": "张明"},
          {"type": "key-value", "key": "电话",   "value": "138 **** 5678"},
          {"type": "key-value", "key": "地址",   "value": "北京市朝阳区...", "color": "secondary"}
        ]
      },
      {
        "type": "section",
        "title": "订单详情",
        "variant": "surface",
        "elements": [
          {"type": "key-value-list", "density": "comfortable", "items": [
            {"key": "商品 × 2", "value": "¥480.00"},
            {"key": "运费",      "value": "¥0.00",  "color": "success"},
            {"key": "优惠券",    "value": "-¥40.00", "color": "primary"},
            {"key": "应付",      "value": "¥440.00", "emphasis": true}
          ]}
        ]
      },
      {
        "type": "footer-bar",
        "summary": {"label": "应付", "value": "¥440.00"},
        "actions": [
          {"label": "提交订单", "variant": "primary", "id": "submit-order", "interactive": true}
        ]
      }
    ]
  }
}
```

This screen reads instantly: progress indicator → grouped address → grouped order detail → fixed bottom action. The user knows exactly **where they are** and **what to do next**.

## Composition recipes (use these before falling back to raw stacks)

| Pattern | Recipe |
|---|---|
| **Dashboard** | `app-bar prominent` → `section` with `grid` of `stat-tile`s → `section` with key list → optional `alert` → `tab-bar` |
| **Settings** | `app-bar` → 2-4 `section`s of `list-item` rows grouped by topic → optional `footer-bar` with "Sign out" |
| **Form** | `app-bar` → `step-indicator` (if multi-step) → `section`s with `form-field`s grouped logically → `footer-bar` with primary CTA |
| **List + detail** | `app-bar` with search action → `search-bar` → `section`-wrapped list of `list-item`s → empty state if list is empty |
| **Confirmation/summary** | `app-bar` → `step-indicator` → 2 `section`s of `key-value-list` (address, items) → `footer-bar` with total + primary CTA |
| **Empty result** | `app-bar` → `empty-state` with icon + title + message + primary CTA |
| **Status (loading/success/error)** | Set `screen.state` accordingly. Body is a single big `empty-state`-style block (icon + message). Set the right state so the outer card colors itself. |
| **ATM transactional** | `chrome: "panel"` + `hardware[]` + `side-key-rail` on either side of a centered text/value block (NOT a flat stack of buttons) |

## Density and rhythm guidelines

- A screen with **more than 8 children in a single `stack`** is a smell — group them into 2–4 sections.
- A `section` with **more than 6 immediate children** is a smell — split into two sections.
- Mix at least **two different primitives** per screen body. A screen made entirely of buttons or entirely of text lines reads as a wireframe sketch, not a designed UI.
- Use `divider` and `section-header` sparingly — `section` already provides visual grouping.
- Use the `state` knob on the OUTER screen card to telegraph success/error/loading — don't try to communicate state with screen body color alone.
