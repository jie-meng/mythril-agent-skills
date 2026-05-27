# `journey.json` Schema

The structured source of truth for the journey. `JOURNEY.md` is the human-readable view; `journey.json` is what the renderer (`assets/render.js`) consumes.

Both files MUST stay in sync. Run `scripts/validate_sync.py <workspace>` after every change.

## Top-level object

```json
{
  "schema_version": "1",
  "title": "Food-delivery first-order journey",
  "subtitle": "From app download to repeat order",
  "language": "en",
  "personas": [ { ... } ],
  "stages": [ { ... } ],
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
| `schema_version` | string | yes | Always `"1"` for now. |
| `title` | string | yes | Short title — shows in browser tab and map header. |
| `subtitle` | string | no | One-line scope statement. |
| `language` | `"en"` \| `"zh"` | yes | Drives the UI labels in `render.js`. |
| `personas` | Persona[] | yes | At least one. The first is the primary. |
| `stages` | Stage[] | yes | 3–7 entries. |
| `metadata` | object | no | Free-form provenance fields. |

## Persona

```json
{
  "id": "new-user",
  "name": "Lily, new user",
  "role": "First-time food-delivery customer",
  "goals": ["Order dinner in under 5 minutes", "Find restaurants nearby"],
  "frustrations": ["Too many forms during signup", "Hidden fees at checkout"],
  "tech_savvy": 3,
  "context": "On the subway, 5G spotty, holding the phone with one hand"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | slug | yes | `[a-z0-9-]+`, unique within `personas`. |
| `name` | string | yes | Display name. |
| `role` | string | yes | One-line role description. |
| `goals` | string[] | yes | 1–5 goals. |
| `frustrations` | string[] | no | 0–5 known frustrations. |
| `tech_savvy` | int 1–5 | no | 1 = novice, 5 = power user. |
| `context` | string | no | Situational context (location, device, time pressure). |

## Stage

```json
{
  "id": "discover",
  "label": "Discover",
  "summary": "User learns the app exists and decides to download",
  "persona_id": "new-user",
  "steps": [ { ... } ],
  "notes": "Speaker notes for presenter mode (1–3 sentences)."
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | slug | yes | `[a-z0-9-]+`, unique within `stages`. |
| `label` | string | yes | Short label shown on the map (≤ 20 chars). |
| `summary` | string | yes | One-sentence stage summary. |
| `persona_id` | string | no | Defaults to the first persona. |
| `steps` | Step[] | yes | 1–8 entries. More than 8 → split into two stages. |
| `notes` | string | no | Speaker notes shown in presenter mode. |

## Step

```json
{
  "id": "browse-restaurants",
  "actions": ["Search by cuisine", "Filter by delivery time"],
  "touchpoints": ["Home screen", "Search results"],
  "thoughts": ["Will this arrive on time?", "Is the rating real?"],
  "emotion": "neutral",
  "pain_points": ["Filters reset on back navigation"],
  "opportunities": ["Show ETA badge on each restaurant card"],
  "metrics": [
    {"name": "Add-to-cart rate", "target": "> 30%"},
    {"name": "Search-to-detail clickthrough"}
  ],
  "wireframe": {
    "kind": "mobile-screen",
    "title": "Search results",
    "elements": [
      {"type": "search-bar", "label": "Filters: ramen, < 30 min"},
      {"type": "list", "items": ["Ippudo · ⭐ 4.5 · 25 min", "Ichiran · ⭐ 4.6 · 35 min"]},
      {"type": "cta", "label": "Order"}
    ]
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | slug | yes | `[a-z0-9-]+`, unique within the stage. |
| `actions` | string[] | yes | What the user does — verb-led. |
| `touchpoints` | string[] | yes | What they interact with (screen / channel). |
| `thoughts` | string[] | yes | What they're thinking. |
| `emotion` | enum | yes | `delighted` \| `happy` \| `neutral` \| `frustrated` \| `blocked` |
| `pain_points` | string[] | no | Known issues at this step. |
| `opportunities` | string[] | no | Design / product opportunities. |
| `metrics` | Metric[] | no | Quantitative KPIs tracked at this step. |
| `wireframe` | Wireframe \| null | no | Optional inline lo-fi mock — see `WIREFRAMES.md`. |

## Validation rules (enforced by `validate_sync.py`)

1. Every `stage.id` and `step.id` is unique within its scope.
2. Every `step.persona_id` (if present) references a defined persona.
3. `emotion` is one of the five allowed values.
4. `stages` array length is in `[1, 7]` — more than 7 raises a warning.
5. Each stage has at least one step.
6. The mermaid `flowchart` in `JOURNEY.md` has the same node IDs as `stages[].id`.
7. The stage count and stage IDs in `JOURNEY.md`'s "Stages" section match `journey.json`.

Any violation prints a structured error; the AI must fix before continuing.
