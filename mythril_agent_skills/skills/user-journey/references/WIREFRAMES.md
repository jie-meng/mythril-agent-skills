# Inline Wireframes

A `step.wireframe` block tells the renderer to draw a lo-fi mock for that step. Use sparingly — only for "hero" steps the user wants to demo visually. A journey with a wireframe on every step becomes noisy.

## Schema

```json
{
  "kind": "mobile-screen",
  "title": "Search results",
  "elements": [ ... ]
}
```

`kind` is one of:

| Kind | Aspect | Use for |
|---|---|---|
| `mobile-screen` | 9:19.5 | Phone app screens |
| `tablet-screen` | 3:4 | iPad / tablet apps |
| `desktop-window` | 16:10 | Web apps, dashboards |
| `email` | 3:4 | Transactional emails |
| `modal` | 4:3 | Modal dialogs, popups |
| `notification` | 8:1 | Push notifications, banners |

## Element types

Each element is one row in the wireframe. The renderer draws them top-to-bottom inside the device frame. Keep wireframes simple — they are NOT meant to replicate the final UI; they show structure and content priority.

### `header`
```json
{"type": "header", "label": "Home", "back": true, "actions": ["search", "more"]}
```
Title bar. `back: true` shows a back chevron. `actions` are icon names (renderer uses generic icons).

### `search-bar`
```json
{"type": "search-bar", "label": "Filters: ramen, < 30 min"}
```
A search input row. `label` is the placeholder or current query.

### `text`
```json
{"type": "text", "label": "Order confirmed", "size": "lg", "weight": "bold"}
```
A line of text. `size`: `sm` | `md` | `lg`. `weight`: `regular` | `bold`.

### `list`
```json
{"type": "list", "items": ["Ippudo · ⭐ 4.5", "Ichiran · ⭐ 4.6"]}
```
Vertical list, one item per row.

### `card`
```json
{"type": "card", "title": "Today's special", "body": "Ramen set for 2 — ¥98"}
```
A bordered card row.

### `image-placeholder`
```json
{"type": "image-placeholder", "ratio": "16:9", "label": "Hero photo"}
```
Gray rectangle with optional label. `ratio`: `1:1` | `4:3` | `16:9` | `3:4`.

### `form-field`
```json
{"type": "form-field", "label": "Phone number", "placeholder": "+86 ..."}
```
A labeled input row.

### `cta`
```json
{"type": "cta", "label": "Place order", "variant": "primary"}
```
A call-to-action button. `variant`: `primary` | `secondary` | `ghost`.

### `tab-bar`
```json
{"type": "tab-bar", "items": ["Home", "Orders", "Me"], "active": "Home"}
```
Bottom navigation bar (typical for mobile).

### `toast`
```json
{"type": "toast", "label": "Saved!", "variant": "success"}
```
A floating toast notification. `variant`: `info` | `success` | `warning` | `error`.

### `spacer`
```json
{"type": "spacer", "size": "md"}
```
Vertical whitespace. `size`: `sm` | `md` | `lg`.

## Example: complete wireframe

```json
{
  "kind": "mobile-screen",
  "title": "Restaurant detail",
  "elements": [
    {"type": "header", "label": "Ippudo", "back": true, "actions": ["share", "favorite"]},
    {"type": "image-placeholder", "ratio": "16:9", "label": "Storefront photo"},
    {"type": "text", "label": "Ippudo · 4.5 ⭐ (1,243)", "size": "lg", "weight": "bold"},
    {"type": "text", "label": "Tonkotsu · 25–35 min · ¥45 min order", "size": "sm"},
    {"type": "spacer", "size": "md"},
    {"type": "card", "title": "Akamaru Modern", "body": "Signature pork bone broth · ¥58"},
    {"type": "card", "title": "Karaka-men", "body": "Spicy miso · ¥62"},
    {"type": "spacer", "size": "lg"},
    {"type": "cta", "label": "View cart (¥120)", "variant": "primary"},
    {"type": "tab-bar", "items": ["Home", "Orders", "Me"], "active": "Home"}
  ]
}
```

## Authoring tips

- **One wireframe per "key moment"** — usually entry, conversion, and confirmation.
- **Content over chrome** — write the actual copy (real restaurant names, real prices), not lorem ipsum. The point of lo-fi is to test the language as much as the layout.
- **Don't over-spec colors** — wireframes inherit the workspace's `DESIGN.md` palette and stay intentionally muted.
- **Use spacers** — vertical rhythm matters more than pixel positioning in lo-fi.
