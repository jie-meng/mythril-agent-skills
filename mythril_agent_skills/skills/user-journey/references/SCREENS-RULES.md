# Screens Validation Rules

`validate_screens.py` enforces structural integrity of `screens[]` and `transitions[]` in `journey.json`. Run after every edit:

```bash
# Iteration mode — warnings stay as warnings:
python3 SKILL_PATH/scripts/validate_screens.py <workspace>

# Before declaring the journey "done" — strict mode promotes the screen-count
# floor warning to an error:
python3 SKILL_PATH/scripts/validate_screens.py <workspace> --strict
```

Exit codes:
- `0` — all rules pass
- `1` — at least one error (or warning promoted under `--strict`)
- `2` — workspace structure invalid (missing `journey.json`)

Output format:

```
STATUS=PASS|FAIL
SCREENS_CHECKED=<N>
TRANSITIONS_CHECKED=<N>
ERROR:   <message>
WARNING: <message>
INFO:    <message>
```

## The 10 rules

### Rule 1 — Screen `id` must be unique

```
ERROR: duplicate screen id 'pin-entry'
```

`screens[].id` is referenced by `step.screen_refs` and `transitions.to_screen`. Duplicates make references ambiguous.

### Rule 2 — `transitions.to_screen` must resolve

```
ERROR: screen 'pin-entry' transition #1 to_screen='main-menu' does not exist in screens[]
```

A transition pointing at a non-existent screen is dead — Flow view's click-to-jump and Presenter's auto-play will break.

### Rule 3 — `transitions.from_element` must resolve

```
ERROR: screen 'pin-entry' transition #1 from_element='confirm' has no element with that id in this screen's layout
```

The validator resolves `from_element` against three address spaces:

1. **Layout-tree element ids** (anything with an `id` under `screen.layout`)
2. **Side-key-rail key ids** — every `keys[].id` inside a `side-key-rail` element
3. **Top-level `screen.hardware[]` slot ids** — `id` on any chrome-bezel hardware slot

Special value `from_element: "any"` is always allowed (treats the entire screen as the tap target).

The element does NOT need to have `interactive: true` for the rule to pass — the validator only checks element existence. But the renderer will silently skip transitions whose source element is not interactive, so the AI should set `interactive: true` on referenced elements (rule 8 below catches the most common case).

### Rule 4 — `step.screen_refs[]` must resolve

```
ERROR: stage 'select-service' step 'browse-menu' screen_refs[0]='menu' does not exist in screens[]
```

A step referencing a non-existent screen will render an empty placeholder in Stage view.

### Rule 5 — Orphan screen (warning)

```
WARNING: screen 'help-overlay' has no incoming references — no step references it AND no transition points at it
```

Possible causes:
1. The screen is genuinely unused (drafted but not yet wired up) — wire it up or delete it
2. A `step.screen_refs` typo — fix the typo
3. The screen is intentionally a deep-link only (rare) — silence with `"orphan_ok": true` in the screen (not common)

### Rule 6 — Dead-end non-terminal screen (info)

```
INFO: screen 'pin-entry' has no outgoing transitions but appears in step 1.2 of 3 — likely needs at least one transition out
```

A dead-end screen is fine for genuine terminal screens (e.g. "Transaction complete"). It's worth flagging when it sits in the middle of a flow.

### Rule 7 — At most one `is_default: true` per screen (error)

```
ERROR: screen 'main-menu' has 2 transitions with is_default=true — only one main path is allowed per screen
```

Presenter auto-play picks the default outgoing edge to advance. Ambiguous defaults break this. To have multiple paths, leave them all `is_default: false`; Presenter then stops at this screen and waits for manual navigation.

### Rule 8 — Interactive elements should have `id` (warning)

```
WARNING: screen 'main-menu' has interactive element of type 'button' without id — no transition can reference it
```

Caught at validation time so you don't end up with a "tappable" button that has no edge connected.

This also applies to `side-key-rail` keys: a key with `interactive: true` but no `id` cannot be referenced by any transition.

### Rule 9 — Device-aware modeling (warning)

```
WARNING: 3 screen(s) of kind='atm-screen' ('welcome', 'menu', 'cash-out')
         but NONE use side-key-rail / hardware-slot / chrome='panel' — these
         are most likely modeled as mobile screens.
```

Triggers when a journey contains any `atm-screen` or `kiosk-screen` screens but **none** of them use `side-key-rail`, `hardware-slot`, or `chrome: "panel"`. This is the harness-level guard against the "ATM looks like a phone" failure mode — when AI defaults to mobile thinking and models an ATM main menu as a vertical stack of phone-style buttons.

The check is **journey-wide per kind**, not per-screen, so a legitimate touch-only kiosk screen (e.g. a product picker between two hardware-interaction screens) does not falsely trigger as long as at least one screen of the same kind uses the right vocabulary.

Fix: re-model at least the transactional screens (main menu, hardware-interaction) per the `references/WIREFRAMES.md` "Device-aware modeling" table and "End-to-end example B".

### Rule 10 — Screen-count floor (warning / strict error)

```
WARNING: only 3 screens defined for 4 stages — Flow view will be sparse.
         Recommended floor is max(stages*2, 8) = 8.
```

Recommends at least `max(stages * 2, 8)` screens per journey. A journey with too few screens has an empty/sparse Flow view, which defeats the purpose of opening into Flow by default.

| Mode | Behavior |
|---|---|
| Default (no `--strict`) | Warning only — useful for iteration |
| `--strict` | Promoted to error — use before declaring a journey "done" |

## Common workflows

### Wiring up a new screen

1. Add the screen to `screens[]` with `layout` and `transitions: []` (empty, fill later).
2. Add `screen_refs: ["new-screen"]` to whichever step displays it.
3. Define outgoing transitions on the new screen.
4. Define incoming transition on whichever screen jumps to it.
5. Run validators.

### Renaming a screen

**Don't.** `screen.id` is immutable (same rule as `stage.id` and `step.id`). To rename, change `screen.title` (display name) — `id` stays the same.

If you really need to rename `id`: delete + re-create, then update all references. Validator will catch missed references.

### Reusing a screen across stages

Define the screen once, set `stage_id` to its primary stage (where it visually "belongs" in the Flow nav), reference it from `step.screen_refs[]` in as many steps as needed across stages. The renderer counts incoming references and shows them all in the Flow right panel.

### Modeling error paths

Set `is_error_path: true` on a transition. The Flow view edge renders red. Presenter auto-play skips it. Hover tooltip prefixes with "(error)".

### Modeling timeouts

```json
{
  "from_element": "any",
  "trigger": "timeout",
  "to_screen": "idle",
  "delay_ms": 30000,
  "label": "30s 无操作 → 回到待机"
}
```

`trigger: "timeout"` + `delay_ms` lets Presenter auto-play wait. Flow view shows a clock icon on the edge.

## What this validator does NOT check

- Whether the screen's `layout` is visually good (use the browser preview for that)
- Whether `step.screen_refs` order matches the actual UX flow (use Flow view's left nav order to sanity-check)
- Whether `is_default` paths form a connected DAG from start to end (future enhancement)

Pass these all by running the validator after every edit. Treat any ERROR as blocking; treat WARNING and INFO as "check this before declaring done".
