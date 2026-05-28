# Screens & Arrows Validation Rules (v3)

`validate_screens.py` enforces structural integrity of `screens[]` and the
top-level `arrows[]` in `journey.json`. Run after every edit:

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
ARROWS_CHECKED=<N>
ERROR:   <message>
WARNING: <message>
INFO:    <message>
```

## The rules

### Rule 1 — Screen `id` must be unique

```
ERROR: duplicate screen id 'pin-entry'
```

`screens[].id` is referenced by `step.screen_refs` and by `arrows[].from` /
`arrows[].to`. Duplicates make references ambiguous.

### Rule 2 — Every `arrow.to` must resolve

```
ERROR: arrow #3 to='main-menu' does not exist in screens[]
```

An arrow that lands nowhere is dead — it would render as a red dotted stub
on the canvas.

### Rule 3 — Every `arrow.from` must resolve

The validator parses `from` into `<screen-id>` (always required) and
`<element-id>` (optional, after `#`). Both must resolve.

```
ERROR: arrow #1 from='ghost#confirm' — screen 'ghost' does not exist in screens[]
ERROR: arrow #1 from='pin-entry#confirm' — element 'confirm' not found in screen 'pin-entry'
```

Element resolution checks three address spaces:

1. **Layout-tree element ids** — anything with an `id` under `screen.layout`
2. **Side-key-rail key ids** — every `keys[].id` inside a `side-key-rail`
3. **Top-level `screen.hardware[]` slot ids**

The element does NOT need `interactive: true` to pass — the validator only
checks existence. But the renderer draws hotspot bubbles only on
`interactive: true` elements, so the AI should set `interactive: true` on
any element referenced from an arrow.

### Rule 4 — `step.screen_refs[]` must resolve

```
ERROR: stage 'select-service' step 'browse-menu' screen_refs[0]='menu' does not exist in screens[]
```

A step referencing a non-existent screen is broken in `JOURNEY.md`'s textual
index.

### Rule 5 — Orphan screen (warning)

```
WARNING: screen 'help-overlay' has no incoming references — no step references it AND no arrow points at it
```

Possible causes:
1. The screen is genuinely unused (drafted but not yet wired up) — wire it
   up or delete it
2. A `step.screen_refs` typo — fix the typo
3. An `arrows[].to` typo — fix the typo
4. The screen is intentionally a deep-link only — set `"orphan_ok": true`
   on the screen (rare)

### Rule 6 — Dead-end non-terminal screen (info)

```
INFO: screen 'pin-entry' has no outgoing arrows but appears in step 1.2 of 3 — likely needs at least one arrow out
```

A dead-end screen is fine for genuine terminals ("Transaction complete").
Flagged when it sits in the middle of a flow.

### Rule 7 — At most one `is_default: true` arrow per source screen (error)

```
ERROR: 2 arrows out of screen 'main-menu' have is_default=true — only one main path is allowed per source screen
```

The default arrow is the visual "happy path" — at most one per source.

### Rule 8 — Interactive elements should have `id` (warning)

```
WARNING: screen 'main-menu' has interactive element of type 'button' without id — no arrow can reference it
```

Caught at validation time so you don't end up with a "tappable" button no
arrow can attach to.

### Rule 9 — Device-aware modeling (warning)

```
WARNING: 3 screen(s) of kind='atm-screen' ('welcome', 'menu', 'cash-out')
         but NONE use side-key-rail / hardware-slot / chrome='panel' — these
         are most likely modeled as mobile screens.
```

Triggers when a journey contains `atm-screen` / `kiosk-screen` screens but
**none** of them use `side-key-rail`, `hardware-slot`, or `chrome: "panel"`.
This is the harness-level guard against the "ATM looks like a phone" failure
mode.

Fix: re-model at least the transactional screens (main menu, hardware-
interaction) per the `references/WIREFRAMES.md` "Device-aware modeling"
table.

### Rule 10 — Screen-count floor (warning / strict error)

```
WARNING: only 3 screens defined for 4 stages — canvas will be sparse.
         Recommended floor is max(stages*2, 8) = 8.
```

Recommends at least `max(stages * 2, 8)` screens per journey. The canvas is
designed for ~10+ screens — fewer and you should consider whether this needs
to be a journey workspace at all (vs a JOURNEY.md-only doc).

| Mode | Behavior |
|---|---|
| Default (no `--strict`) | Warning only — useful for iteration |
| `--strict` | Promoted to error — use before declaring final |

### Rule 11 — Design-pattern sense (warnings)

These advisory warnings catch the "flat element soup" anti-pattern — screens
that work but lack design-pattern composition. Each warning is tagged with a
`[smell-name]` prefix so the AI can address them systematically.

```
WARNING: [flat-stack]    screen 'profile' root stack has 12 direct children and
                         no app-bar/section/header — group into 2-4 sections
                         instead of one big stack.

WARNING: [no-hierarchy]  screen 'list' has 9 atomic elements but no app-bar,
                         header, section, or tab-bar — add at least one
                         structural primitive so the screen reads as a screen.

WARNING: [monotonous]    screen 'pad' is 92% 'button' elements (11/12) — mix
                         at least one other primitive (section, alert, stat-
                         tile, divider, ...) to break the rhythm.

WARNING: [overstuffed]   screen 'settings' section 'Account' has 9 immediate
                         children — split into 2 sections (max 6).
```

Trigger conditions:

| Smell | Fires when |
|---|---|
| `[flat-stack]`   | root is `stack`/`grid` with > 8 direct children AND none is structural |
| `[no-hierarchy]` | > 4 atomic elements AND no `app-bar`/`header`/`section`/`tab-bar`/`step-indicator`/`alert`/`empty-state`/`footer-bar` anywhere |
| `[monotonous]`   | ≥ 5 atomic elements AND ≥ 80% are the same primitive type (exemptions: `keypad-button`, `key-value`, `list-item` — these are legitimately repeated) |
| `[overstuffed]`  | any `section` with > 6 immediate children |

These are **advisory** — they don't fail the build, but the AI should fix them
before declaring Pass C done. See `WIREFRAMES.md` "Composition recipes" for
the patterns that satisfy these checks.

### Rule 12 — Arrow bundle-spam (warning)

```
WARNING: [bundle-spam] 8 arrows go from screen 'withdraw-amount' to screen
         'withdraw-processing' all with kind='default', anchored at distinct
         elements ('k-100', 'k-200', 'k-500', 'k-1000', ...) — collapse into
         ONE arrow with via_elements=['k-100', 'k-200', 'k-500', 'k-1000', ...]
         for canvas legibility.
```

Fires when **≥ 3 element-anchored arrows** from the same source screen lead
to the same target screen, all with `kind="default"`. Almost always means
the author wrote "one arrow per button" for a screen where N buttons are
parallel ways to express ONE decision (numeric amount presets, chip
pickers, "choose any of these → next").

The canvas renderer auto-collapses such groups at draw time
(`arrows.js` → `consolidateArrows`), so the visual result is already
clean — but the `journey.json` stays noisy and the Prototype view loses
the "this is a bundle" semantic. Fix it by merging into one arrow:

```jsonc
// Before — 8 arrows:
{ "from": "withdraw-amount#k-100",  "to": "withdraw-processing", "label": "¥100" },
{ "from": "withdraw-amount#k-200",  "to": "withdraw-processing", "label": "¥200" },
// ... 6 more ...

// After — 1 arrow:
{
  "from": "withdraw-amount",
  "via_elements": ["k-100","k-200","k-500","k-1000","k-2000","k-3000","k-5000","k-custom"],
  "to": "withdraw-processing",
  "kind": "default",
  "is_default": true,
  "label": "任一金额"
}
```

The warning does NOT fire when:

- The kind is NOT `default` (success/error/cancel arrows landing on the
  same target are usually distinct outcomes — keep them separate)
- `via_elements[]` is already used (you bundled them — well done)
- `do_not_consolidate: true` is set on the arrow (author override)
- The `from` is whole-screen (no `#element-id`)
- Fewer than 3 arrows share the bucket (two parallel arrows are still readable)

## Common workflows

### Wiring up a new screen

1. Add the screen to `screens[]` with `layout` and (optionally) a `position`.
2. Add `screen_refs: ["new-screen"]` on the step(s) it represents.
3. Add at least one `arrows[]` entry whose `to` is the new screen.
4. Add at least one `arrows[]` entry whose `from` is the new screen (or
   leave it as a terminal if it really is one).
5. Run validators.

### Renaming a screen

**Don't.** `screen.id` is immutable (same rule as `stage.id` and `step.id`).
Change `screen.title` (display name) — `id` stays. To truly rename: delete +
re-create, then update all `arrows[]` and `step.screen_refs` references.
Validator will catch missed references.

### Reusing a screen across stages

Define once, set `stage_id` to its primary stage, reference from
`step.screen_refs[]` in as many steps as needed. The canvas places it once;
multiple arrows can land on it from different parts of the canvas.

### Modeling error paths

Set `kind: "error"` on the arrow (renders red). Set `kind: "error"` on the
target screen if it's a dedicated error state (the screen card turns red).

### Modeling timeouts

```json
{
  "from": "loading",
  "to": "ready",
  "trigger": "timeout",
  "delay_ms": 2000,
  "label": "2s 后自动",
  "kind": "default"
}
```

## What this validator does NOT check

- Whether the screen's `layout` looks visually good (use the browser preview)
- Whether `arrows[]` form a connected DAG (future enhancement)
- Whether explicit `screen.position` values overlap (the canvas auto-resolves
  by stacking; this is fine for iteration)

Treat any ERROR as blocking; treat WARNING / INFO as "check before declaring
done".
