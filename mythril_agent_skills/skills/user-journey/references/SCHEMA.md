# `journey.json` Schema (v3 — canvas)

The structured source of truth for the journey. `JOURNEY.md` is the human-readable
view. `journey.json` is what the renderer (`assets/render.js` + `canvas.js` +
`wireframe.js` + `arrows.js`) consumes.

Two files must stay in sync. Run BOTH validators after every change:

```bash
python3 SKILL_PATH/scripts/validate_sync.py    <workspace>
python3 SKILL_PATH/scripts/validate_screens.py <workspace>
```

## What v3 is

v3 reshapes the renderer into a **single Miro-style canvas** — all screens are
laid out on one infinite, pannable, zoomable surface, and connections between
screens are drawn as **arrows** (curved SVG paths) from one screen (or one
element inside a screen) to another. There are no more view tabs, no left nav,
no right inspector panel. One canvas, one truth.

Concretely, compared to v2:

| What changed | v2 (deprecated) | v3 (current) |
|---|---|---|
| Top-level views | `map` / `stage` / `flow` / `present` | **`canvas` only** |
| Per-screen edges | `screens[].transitions[]` (nested) | **Top-level `arrows[]`** |
| Screen position | implicit (auto-grouped by stage) | **Explicit `screen.position: {x, y}`** (auto-assigned if missing) |
| Status / state | none | **`screen.state: default \| loading \| success \| error \| warning`** drives outer card color |
| Annotations | `screen.notes` only | **`screen.annotations[]`** (numbered markers on the screen) + **top-level `stickies[]`** (canvas notes) |
| Schema version | `"2"` | **`"3"`** |

v1 / v2 workspaces are NOT read by the renderer anymore. `validate_sync.py`
accepts `"1"`, `"2"`, and `"3"` to allow tooling to inspect older files, but
the renderer requires `"3"`. To upgrade an old workspace, hand-edit
`journey.json`:

1. Move every `screens[].transitions[]` entry into a top-level `arrows[]` array
   (renaming fields per the table below).
2. Add `schema_version: "3"`.
3. Optionally set `screen.state` and `screen.position` on each screen.
4. Drop `screen.transitions[]`.

## Top-level object

```jsonc
{
  "schema_version": "3",
  "title": "ATM withdrawal journey",
  "subtitle": "From approach to leaving with cash",
  "language": "en",
  "personas": [ { ... } ],
  "stages":   [ { ... } ],
  "screens":  [ { ... } ],
  "arrows":   [ { ... } ],
  "stickies": [ { ... } ],
  "metadata": {
    "author": "PM Jane",
    "created": "2026-05-27",
    "last_updated": "2026-05-27",
    "version": "0.3.0",
    "seed_device_kind": "atm"
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | string | yes | `"3"`. |
| `title` | string | yes | Browser tab + canvas header. |
| `subtitle` | string | no | One-line scope statement. |
| `language` | `"en"` \| `"zh"` | yes | Drives UI labels. |
| `personas` | Persona[] | yes | At least one. First is primary. |
| `stages` | Stage[] | yes | 3–7 entries. Used for canvas auto-layout (one column per stage) and for `JOURNEY.md` narrative. |
| `screens` | Screen[] | no | Empty allowed (a journey can be a research stage-map only). |
| `arrows` | Arrow[] | no | Top-level screen-to-screen connections — replaces v2's nested `transitions`. |
| `stickies` | Sticky[] | no | Free-floating canvas notes (sticky-note style). |
| `metadata` | object | no | Free-form provenance. |

## Persona — unchanged

```json
{
  "id": "zhang-ming",
  "name": "张明",
  "role": "上班族",
  "goals": ["快速完成取款"],
  "frustrations": ["排队等待"],
  "tech_savvy": 3,
  "context": "工作日午休"
}
```

| Field | Type | Required |
|---|---|---|
| `id` | slug | yes |
| `name` | string | yes |
| `role` | string | yes |
| `goals` | string[] | yes |
| `frustrations` | string[] | no |
| `tech_savvy` | int 1–5 | no |
| `context` | string | no |

## Stage

```json
{
  "id": "approach-insert",
  "label": "到达 & 插卡",
  "summary": "用户找到 ATM,插入银行卡,输入密码",
  "persona_id": "zhang-ming",
  "steps": [ { ... } ],
  "notes": "Speaker notes (1–3 sentences)."
}
```

Stages keep their full v2 shape — they still drive `JOURNEY.md`, the mermaid
flow, validators, and the **canvas auto-layout** (one stage → one vertical
column on the canvas; screens with that `stage_id` stack inside the column,
auto-positioned if no explicit `position` is set).

| Field | Type | Required |
|---|---|---|
| `id` | slug | yes — unique within `stages` |
| `label` | string | yes — ≤ 20 chars |
| `summary` | string | yes — one sentence |
| `persona_id` | string | no — defaults to first persona |
| `steps` | Step[] | yes — 1–8 entries |
| `notes` | string | no |

## Step — unchanged

```json
{
  "id": "insert-card",
  "actions": ["从钱包取出银行卡", "按方向插入卡槽"],
  "touchpoints": ["银行卡", "ATM 卡槽"],
  "thoughts": ["哪面朝上?"],
  "emotion": "neutral",
  "pain_points": ["插卡方向不明确"],
  "opportunities": ["卡槽 LED 引导"],
  "metrics": [{"name": "插卡成功率", "target": "> 98%"}],
  "screen_refs": ["welcome", "card-insert-anim"]
}
```

`screen_refs[]` still exists — it lets a step say "this step happens on these
screens", which `JOURNEY.md` uses as a textual index. The canvas does not use
it for rendering (the canvas uses `arrows[]`).

## Screen — v3 shape

```jsonc
{
  "id": "pin-entry",
  "kind": "atm-screen",
  "title": "密码输入",
  "stage_id": "approach-insert",
  "state": "default",
  "position": { "x": 800, "y": 0 },
  "chrome": "panel",
  "hardware": [
    {"slot": "card-reader", "position": "top",    "label": "插卡口"},
    {"slot": "cash-out",    "position": "bottom", "label": "出钞口"}
  ],
  "layout": { ... },
  "annotations": [
    { "n": 1, "note": "防窥设计在这一屏最关键" }
  ],
  "notes": "AI / authoring notes; not shown on the canvas."
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | slug | yes | Unique within `screens`. **Immutable** once created — used by `arrows[]` and `step.screen_refs`. |
| `kind` | enum | yes | Device frame — see "screen.kind" below |
| `title` | string | yes | Rendered on the colored card header above the screen frame |
| `stage_id` | string | no | Drives canvas auto-layout column |
| `state` | enum | no | `default` (gray, default) \| `loading` (blue) \| `success` (green) \| `error` (red) \| `warning` (amber). Drives the colored outer card. |
| `position` | `{x, y}` | no | Explicit pixel coordinates on the canvas (top-left of the outer state card). When absent, the renderer auto-assigns a position based on `stage_id`. |
| `chrome` | `"none"` \| `"panel"` | no | `"panel"` wraps the screen in a device chassis. Default depends on `kind`: ATM/kiosk default to `"panel"`. |
| `hardware` | HardwareSlot[] | no | Physical chassis ports when `chrome: "panel"`. Ignored otherwise. See WIREFRAMES.md. |
| `layout` | Layout | yes | Root layout — see WIREFRAMES.md |
| `annotations` | Annotation[] | no | Numbered triangle markers placed on the screen card (top-right) with explanatory notes. Like Miro's `1` / `2` / `3` callouts. |
| `notes` | string | no | Authoring / speaker notes — kept in JSON for human reference, not rendered on the canvas. |

### `screen.kind` values

| Kind | Aspect | Use for |
|---|---|---|
| `mobile-screen` | 9:19.5 | Phone app |
| `tablet-screen` | 3:4 | Tablet app |
| `desktop-window` | 16:10 | Web app, dashboard |
| `atm-screen` | 4:3 | ATM (landscape with side function keys) |
| `kiosk-screen` | 9:16 | Vertical kiosk |
| `tv-screen` | 16:9 | TV / smart display |
| `email` | 3:4 | Transactional email |
| `modal` | 4:3 | Modal dialog over another screen |
| `notification` | 8:1 | Push notification, banner |

### `screen.state` values

The state drives the **colored card** that wraps the screen on the canvas
(mimicking the Miro convention from the reference image):

| Value | Card color | Use for |
|---|---|---|
| `default` | gray | normal screens, browse / select / read flows |
| `loading` | blue | "Loading…", "Processing…", spinner screens |
| `success` | green | success acknowledgements, "transaction complete" |
| `error` | red | error / failure / blocked screens |
| `warning` | amber | confirmation / "are you sure?" / risk screens |

## Arrow — top-level connection between screens

```json
{
  "id": "tx-1",
  "from": "welcome#h-card",
  "to": "pin-entry",
  "kind": "success",
  "trigger": "insert-card",
  "label": "插卡 → 输入密码",
  "is_default": true,
  "delay_ms": 0
}
```

Arrows are **top-level**, not nested inside screens. This makes the canvas
straightforward (one flat list to iterate) and lets a single arrow originate
from a specific element on the source screen.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | no | Optional stable id (autogenerated if omitted). |
| `from` | string | yes | Source. Either `"<screen-id>"` (whole-screen anchor) or `"<screen-id>#<element-id>"` (anchored at a specific button / hardware slot / side-key). |
| `via_elements` | string[] | no | List of element ids on the source screen that all funnel to the same target. Use when N buttons on one screen express ONE decision — see "Bundle arrows with via_elements" below. When set, `from` MUST be the whole-screen form `"<screen-id>"` (no `#`). |
| `to` | string | yes | Target `screen.id`. Whole-screen anchor only — arrows always land on a screen, not on an element. |
| `kind` | enum | no | `default` (blue) \| `success` (green) \| `error` (red) \| `cancel` (gray, dashed). Drives the arrow stroke. Default `default`. |
| `trigger` | enum | no | `tap` \| `long-press` \| `swipe` \| `input` \| `insert-card` \| `timeout` \| `auto`. Default `tap`. Renders as small text near the arrow. |
| `label` | string | no | Short human-readable description. Rendered mid-arrow. |
| `is_default` | boolean | no | Marks the main happy-path arrow out of a screen. At most one per source screen. |
| `delay_ms` | integer | no | For `trigger: "timeout"` / `"auto"`. |
| `do_not_consolidate` | boolean | no | Opt out of the renderer's auto-consolidation pass. Use sparingly — almost always the right answer is to bundle with `via_elements[]` instead. |

**Element addressing in `from`**: the `<element-id>` after `#` is resolved
against the same three address spaces as v2 transitions:

1. Layout-tree element ids (anything with `id` under `screen.layout`)
2. Side-key-rail key ids
3. Top-level `screen.hardware[]` slot ids

Use `<screen-id>` (no `#`) when the arrow conceptually originates from the
whole screen — e.g. "after this loading screen finishes, go to the next
screen" with `trigger: "timeout"`.

### Bundle arrows with `via_elements[]`

When **N buttons / keys / chips on one screen all lead to the SAME target
with the SAME intent**, model them as ONE arrow with `via_elements[]`
instead of N separate arrows. The canonical example is an amount-preset
screen where ¥100 / ¥200 / ¥500 / ... all just mean "pick any amount → go
to processing":

```jsonc
{
  "from": "withdraw-amount",
  "via_elements": [
    "k-100", "k-200", "k-500", "k-1000",
    "k-2000", "k-3000", "k-5000", "k-custom"
  ],
  "to": "withdraw-processing",
  "kind": "default",
  "is_default": true,
  "label": "任一金额",
  "trigger": "tap"
}
```

Renderer behavior:

- **Canvas**: draws ONE curved arrow from the source's right edge to the
  target's left edge. No fan-out, no 8 parallel lines. The label is
  rendered once.
- **Prototype**: every element id in `via_elements[]` becomes a clickable
  hotspot. Clicking ANY of them navigates to `to`. The arrows-hint panel
  shows a single bundled entry like `via 8 elements → <target>`.
- **Validator**: skips Rule 12 `[bundle-spam]` for this arrow (it's
  already bundled). All `via_elements[]` ids must resolve against the
  source screen's address spaces (same rules as `from#<element>`).

Constraints:

- `from` MUST be the whole-screen form `"<screen-id>"` (no `#`) — the
  bundled elements are listed in `via_elements[]`, not in `from`.
- Every id in `via_elements[]` must resolve on the source screen.
- Use ONE `via_elements[]` arrow per (source, target, kind) bundle —
  don't mix `via_elements[]` with separate `from: "<screen>#<el>"`
  arrows pointing to the same target with the same kind.

When NOT to use `via_elements[]`:

- The N buttons lead to **different** targets → keep separate arrows.
- The N buttons have **different `kind`** (one is `success`, one is
  `cancel`) → keep separate arrows; the colors carry information.
- There's only 1-2 element-anchored arrows in the group → not worth
  bundling, just keep them.

## Sticky — free-floating canvas note

```json
{
  "id": "sticky-1",
  "x": 1200,
  "y": 480,
  "text": "Do not submit lead until KYC complete",
  "color": "orange"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | no | Optional stable id |
| `x`, `y` | number | yes | Pixel coordinates of the sticky's top-left |
| `text` | string | yes | Sticky content |
| `color` | enum | no | `yellow` (default) \| `orange` \| `pink` \| `blue` \| `green` |

## Annotation — numbered marker on a screen card

```json
{
  "n": 3,
  "note": "Confirm dialog must surface card type"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `n` | int | yes | The number rendered inside the triangle marker |
| `note` | string | yes | Hover/click reveals this text |

Markers render as small triangles in the screen card's top-right corner, like
the `1` / `2` / `3` markers in the Miro reference image.

## Validation rules

Enforced by `validate_sync.py` (structural) and `validate_screens.py` (screens
+ arrows). See `SCREENS-RULES.md` for the full screens / arrows rules:

1. Every `stage.id`, `step.id`, `persona.id`, `screen.id`, `arrow.id` is unique.
2. Every `step.persona_id` resolves to a defined persona.
3. `emotion` is one of the five allowed values.
4. `stages` length ∈ [1, 7].
5. Each stage has at least one step.
6. The mermaid `flowchart` in `JOURNEY.md` matches `stages[].id`.
7. Every arrow `from`/`to` resolves to an existing screen (and element, when
   `from` includes `#`).
8. At most one `arrow.is_default = true` per source screen.
9. Orphan screens (no arrow points at them, no step references them) → warning.
10. Dead-end screens in non-terminal positions → info.

Any violation prints a `STATUS=FAIL` report; the AI must fix before declaring
done.
