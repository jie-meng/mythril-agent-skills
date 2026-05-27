# `journey.json` Schema (v2)

The structured source of truth for the journey. `JOURNEY.md` is the human-readable view; `journey.json` is what the renderer (`assets/render.js`) consumes.

Three files must stay in sync. Run BOTH validators after every change:

```bash
python3 SKILL_PATH/scripts/validate_sync.py    <workspace>
python3 SKILL_PATH/scripts/validate_screens.py <workspace>
```

## What's new in v2

- Top-level `screens[]` — screens are **first-class entities**, not appendages of a step.
- `stages[].steps[].screen_refs: string[]` — a step references screens by id, instead of embedding them.
- `screens[].transitions[]` — screen-to-screen jumps with trigger, source element, target screen, and an optional `is_default` flag for the main path.
- `screens[].layout` — nested layout containers (`stack` / `grid` / `row`) replace flat element arrays.
- New interactive element fields: `id`, `interactive`, `state`, `validation`, `icon`, `badge`, `hotspot_number`.
- New element types: `button`, `keypad-button`, `icon-button`, `divider`, `badge`, `chip`, `progress`.

v1 workspaces (no `screens[]`, `wireframe` embedded in step) are still read by `validate_sync.py` (schema_version `"1"` is accepted), but the renderer's Flow view, the screens validator, and Presenter screen-playback all require v2. To upgrade an old workspace, hand-edit `journey.json` to add a top-level `screens[]` array and `screen_refs` on the affected steps — there is no automated migration.

## Top-level object

```json
{
  "schema_version": "2",
  "title": "ATM withdrawal journey",
  "subtitle": "From approach to leaving with cash",
  "language": "en",
  "personas": [ { ... } ],
  "stages":   [ { ... } ],
  "screens":  [ { ... } ],
  "metadata": {
    "author": "PM Jane",
    "created": "2026-05-27",
    "last_updated": "2026-05-27",
    "version": "0.3.0"
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | string | yes | `"2"` for new workspaces. `"1"` is still accepted by `validate_sync.py` for legacy read-only access — upgrade by hand-editing the file. |
| `title` | string | yes | Browser tab + map header. |
| `subtitle` | string | no | One-line scope statement. |
| `language` | `"en"` \| `"zh"` | yes | Drives UI labels. |
| `personas` | Persona[] | yes | At least one. First is primary. |
| `stages` | Stage[] | yes | 3–7 entries. |
| `screens` | Screen[] | no | Empty array allowed (e.g. a pure-research journey with no UI). |
| `metadata` | object | no | Free-form provenance. |

## Persona — unchanged from v1

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

| Field | Type | Required |
|---|---|---|
| `id` | slug | yes — unique within `stages` |
| `label` | string | yes — ≤ 20 chars |
| `summary` | string | yes — one sentence |
| `persona_id` | string | no — defaults to first persona |
| `steps` | Step[] | yes — 1–8 entries |
| `notes` | string | no — speaker notes |

## Step

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

| Field | Type | Required |
|---|---|---|
| `id` | slug | yes — unique within stage |
| `actions` | string[] | yes |
| `touchpoints` | string[] | yes |
| `thoughts` | string[] | yes |
| `emotion` | enum | yes — `delighted` \| `happy` \| `neutral` \| `frustrated` \| `blocked` |
| `pain_points` | string[] | no |
| `opportunities` | string[] | no |
| `metrics` | Metric[] | no |
| `screen_refs` | string[] | no — screen ids this step displays; may be empty for non-UI steps (thoughts, offline actions) |

**Note**: v2 step does NOT support an inline `wireframe` field. Define the screen once in `screens[]` and reference it by id. A screen can be referenced by multiple steps (e.g. the "main menu" screen appears in both `browse-menu` and `select-withdrawal`).

## Screen — new in v2

```json
{
  "id": "pin-entry",
  "kind": "atm-screen",
  "title": "密码输入",
  "stage_id": "approach-insert",
  "notes": "防窥设计在此屏最关键",
  "layout": { ... },
  "transitions": [ { ... } ]
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | slug | yes | Unique within `screens`. Used in `step.screen_refs` and `transitions.to_screen`. **Immutable** once created. |
| `kind` | enum | yes | Device frame — see below |
| `title` | string | yes | Human-readable screen name (shown in Flow nav, hover labels) |
| `stage_id` | string | no | Which stage this screen primarily belongs to. Used to group screens in the Flow nav and Map view. If absent, the renderer groups by first referencing stage. |
| `notes` | string | no | Author notes shown in Flow view |
| `layout` | Layout | yes | Root layout container — see WIREFRAMES.md |
| `transitions` | Transition[] | no | Outgoing jumps — see below. Empty means "dead end" (final/error screen). |

### `screen.kind` values

| Kind | Aspect | Use for |
|---|---|---|
| `mobile-screen` | 9:19.5 | Phone app |
| `tablet-screen` | 3:4 | Tablet app |
| `desktop-window` | 16:10 | Web app, dashboard |
| `atm-screen` | 4:3 | ATM, kiosk (landscape with side function keys) |
| `kiosk-screen` | 9:16 | Vertical kiosk |
| `tv-screen` | 16:9 | TV / smart display |
| `email` | 3:4 | Transactional email |
| `modal` | 4:3 | Modal dialog over another screen |
| `notification` | 8:1 | Push notification, banner |

## Transition — new in v2

```json
{
  "from_element": "confirm",
  "trigger": "tap",
  "to_screen": "main-menu",
  "label": "点击确认 → 主菜单",
  "is_default": true,
  "is_error_path": false,
  "delay_ms": 0
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `from_element` | string | yes | Element `id` within this screen's layout that triggers the jump. Special value `"any"` means "any tap anywhere on the screen". |
| `trigger` | enum | yes | `tap` \| `long-press` \| `swipe` \| `input` \| `insert-card` \| `timeout` \| `auto` |
| `to_screen` | string | yes | Target `screen.id`. Must exist in `screens[]`. |
| `label` | string | yes | Human-readable description (shown in Flow view's right panel and hover tooltip). |
| `is_default` | boolean | no | Default `false`. Marks the main happy-path edge. Used by Presenter auto-play (`Space`). At most ONE default per screen. |
| `is_error_path` | boolean | no | Default `false`. Renders the edge red and excludes it from auto-play. |
| `delay_ms` | integer | no | Default `0`. For `trigger: "timeout"` or `trigger: "auto"`, how long auto-play waits before advancing. Useful for processing/loading screens. |

**Triggers**:

- `tap` — user taps/clicks the element
- `long-press` — user long-presses
- `swipe` — user swipes
- `input` — user enters data and submits (forms)
- `insert-card` — domain-specific: card inserted into reader (ATM/kiosk)
- `timeout` — automatic after `delay_ms`
- `auto` — automatic immediately on screen entry (rare; for splash → next)

## Validation rules

Enforced by `validate_sync.py` (structural) and `validate_screens.py` (screens + transitions):

### `validate_sync.py`

1. Every `stage.id`, `step.id`, `persona.id`, `screen.id` is unique within its scope.
2. Every `step.persona_id` (if present) references a defined persona.
3. `emotion` is one of the five allowed values.
4. `stages` array length is in `[1, 7]` — more than 7 is an error.
5. Each stage has at least one step.
6. The mermaid `flowchart` in `JOURNEY.md` has the same node ids as `stages[].id`.
7. The stage count and stage ids in `JOURNEY.md`'s `## Stages` section match `journey.json`.

### `validate_screens.py` — see SCREENS-RULES.md

1. Screen `id` unique
2. `transitions.to_screen` resolves
3. `transitions.from_element` resolves within the screen's layout
4. `step.screen_refs[]` all resolve
5. Orphan screens (no incoming reference) → warning
6. Dead-end non-terminal screens → info
7. At most one `is_default: true` transition per screen → error

Any violation prints a structured `STATUS=FAIL` report; AI must fix before continuing.
