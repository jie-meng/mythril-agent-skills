# {{TITLE}}

> **Scope:** {{SUBTITLE}}
> **Primary persona:** {{PERSONA_NAME}}
> **Last updated:** {{DATE}}
> **Status:** skeleton — fill in step details next

## TL;DR

_Write a 2-3 sentence summary of what this journey is about and why it matters — the elevator pitch for a stakeholder who has 10 seconds._

## Personas

### {{PERSONA_SLUG}} — {{PERSONA_NAME}}

- **Role:** {{PERSONA_ROLE}}
- **Goals:** _list 1-3 things the persona wants to achieve_
- **Frustrations:** _list 0-3 known frustrations_
- **Context:** _where / when / on what device do they live in this journey_

## Stages

```mermaid
flowchart LR
{{MERMAID_BODY}}
```

### 1. {{FIRST_STAGE_LABEL}}

_One sentence summarizing this stage._

- **Steps** _(filled in pass B)_:
  - Step 1 — actions / touchpoints / thoughts go here

### _(add more stages as you map them)_

## Screens & Arrows

_Visual screens and the arrows connecting them live on the canvas in `index.html`.
Open it to see the full picture — Canvas view for the overview, Prototype view for click-through._

| Screen | Kind | Stage | State | Outgoing |
|---|---|---|---|---|
| _(empty — fill as you design screens)_ | | | | |

## Open Questions

- _Anything ambiguous, contested, or pending research goes here_
- _Use this section as the running log of "things to validate with the team"_

## Related Materials

- _Links to research notes, hi-fi designs, Jira tickets, Confluence pages_

---

> **How to view this journey visually:** double-click `index.html` in this directory.
> Opens a dual-view workspace:
> - **Canvas** (default, press `V`): Miro-style overview of every screen + arrows.
>   Pan (drag empty space or `Space`+drag) · zoom (`Cmd/Ctrl` + scroll, or pinch) ·
>   `F` fit · `0` reset · double-click a screen to focus · minimap (bottom-right).
> - **Prototype** (press `P`): one screen at a time + clickable hotspots.
>   `Enter` follow default arrow · `Backspace` back · `J`/`K` next/prev screen.
> - Both views share the **left sidebar** screen list + search.
> - `H` shows the full keyboard reference.
>
> **Authoring note (sync):** this file and `journey.json` must stay in sync. After any
> change to either, run BOTH validators:
> `python3 SKILL_PATH/scripts/validate_sync.py    .`
> `python3 SKILL_PATH/scripts/validate_screens.py .`
>
> **Authoring note (mermaid line breaks):** inside any ` ```mermaid ` block, use
> `<br/>` for line breaks — never `\n`. On most renderers (GitHub, Mermaid 10.x,
> Confluence) `\n` shows up as the two literal characters `\` and `n` inside the
> box. Labels with parens or `<br/>` must be wrapped in double quotes, e.g.
> `A["xxx-api<br/>(Domain API)"]`. After editing this file, run the gate:
> `python3 SKILL_PATH/scripts/mermaid_lint.py JOURNEY.md`. Full rules:
> `SKILL_PATH/references/MERMAID-RULES.md`.
