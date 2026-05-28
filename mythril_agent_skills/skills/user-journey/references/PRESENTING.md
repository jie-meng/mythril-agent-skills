# Presenting and Viewing the Journey

The workspace gives you **two complementary views** of the same `journey.json`:

| View | When to use | What it shows |
|---|---|---|
| **Canvas** (default) | Overview, narrative walk-throughs, stakeholder presentations | All screens laid out in stage columns, connected by arrows. Pan + zoom like Miro. |
| **Prototype** | Walking the user flow, demoing click-through, design review | One screen at actual size + clickable hotspots that navigate via arrows. Like a paper prototype. |

You switch with the **Canvas / Prototype** tabs in the topbar, or with the `V` and `P` keyboard shortcuts.

Both views share a **left sidebar** showing the full stage→screen tree, a search box, and a state dot for each screen. Click a sidebar item to select; double-click to jump into Prototype mode on that screen.

---

## How to open

**Default — double-click `index.html`** in the workspace. Opens in the default browser. Works offline, no server, no install.

**If the page is blank** (some browsers block local `fetch()` for `file://`):

```bash
cd <workspace>
python3 preview.py
```

This launches a local web server on `http://localhost:8765` and opens the browser automatically. Press `Ctrl+C` to stop. Requires only Python 3.10+ standard library.

---

## Canvas view

The Miro-style overview. Every screen of the journey is laid out in columns (one per stage), connected by arrows, with optional sticky notes floating around. A small **minimap** in the bottom-right corner lets you click-to-pan and shows the current viewport rectangle.

### Canvas controls

| Action | How |
|---|---|
| Pan | Drag empty canvas, or hold `Space` and drag (Miro style) |
| Zoom in / out | `+` / `−` keys, `Cmd/Ctrl` + scroll wheel, or pinch on trackpad |
| Reset to 100% | `0` |
| Fit all to viewport | `F`, or the **Fit** button in the topbar |
| Focus a specific screen | Double-click it (auto-zoom + center, and selects it in the sidebar) |
| Pan to a region | Click the **minimap** in the bottom-right corner |
| Toggle help overlay | `H`, or the **?** button in the topbar |
| Nudge the view | `←` / `→` / `↑` / `↓` |
| Switch to Prototype | Click the **Prototype** tab, or press `P` |

The topbar always shows the current zoom percentage and a `Fit / + / − / ?` set of buttons.

### What you're looking at

Each screen renders inside a **colored outer card**. The card color comes from `screen.state`:

| Card color | State | Meaning |
|---|---|---|
| Gray | `default` | normal browse / select / read |
| Blue | `loading` | "Processing…", spinner screens |
| Green | `success` | success acknowledgement |
| Red | `error` | failure / blocked |
| Amber | `warning` | confirmation / risk |

The currently selected screen (selected in sidebar or via Prototype mode) is outlined in **blue** with a soft glow.

Arrows are colored by `arrow.kind`:

| Arrow color | Kind | Meaning |
|---|---|---|
| Blue-gray (solid) | `default` | normal forward arrow |
| Green | `success` | leads to a success outcome |
| Red | `error` | leads to an error / failure |
| Gray (dashed) | `cancel` | back / cancel / drop-out |

Arrows marked `is_default: true` render slightly thicker — that's the **happy path** the eye follows.

Sticky notes (yellow / orange / pink / blue / green) float freely on the canvas and are great for "open questions", "blocker", "decision point", "metric to instrument".

---

## Prototype view

Single-screen click-through. The screen renders at **actual size** (no zoom-out, no surrounding cards) inside a device frame. Any element that has an outgoing arrow becomes a **clickable hotspot** with a dashed blue ring.

### Prototype controls

| Action | How |
|---|---|
| Navigate via hotspot | Click any element with a dashed blue ring; the prototype follows that arrow's `to` screen |
| Follow the default arrow | Press `Enter` |
| Next / previous screen | Press `J` (next) / `K` (previous) in document order |
| Go back one step | Click the **← Back** button in the breadcrumb, or press `Backspace` |
| Jump to a prior step | Click any past entry in the breadcrumb path |
| Switch screen from sidebar | Click a sidebar item (resets history) |
| Continue (auto / timeout arrows) | Big blue **Continue** button below the screen frame |
| Switch back to Canvas | Click the **Canvas** tab, or press `V` |

The right-side **Transitions** panel lists every outgoing arrow from the current screen — `#element → target` with the trigger label. Click the target name to jump there. This is your "exits cheat-sheet" without scanning the screen for hotspots.

The breadcrumb at the top shows your trail: `Welcome ▸ Main ▸ Withdraw ▸ **Done**`. Click any earlier crumb to rewind to that point.

### When Prototype shines

1. **Walking the happy path with a stakeholder** — start on the first screen, hit `Enter` repeatedly, and the prototype follows `is_default` arrows like a slide deck.
2. **Reviewing error flows** — navigate normally, then on a screen with `kind: error` arrows, click the red-coded hotspot to see what users see when things break.
3. **Sanity-checking dead ends** — terminal screens show "No outgoing arrows. This is a terminal screen." in the Transitions panel. If you didn't expect that screen to be terminal, it's a hole in your model.
4. **Demoing on a small screen** — Prototype only shows one screen at a time, so it works on a phone or in a narrow window where the full Canvas would be unreadable.

---

## Tips for presenting to stakeholders

1. **Start with Canvas zoomed out.** Press `F` (Fit) so the whole journey is visible. Walk through the narrative top-to-bottom or stage-by-stage by panning.
2. **Switch to Prototype for the demo.** Press `P` to jump into the screen-by-screen view, then `Enter` to follow the happy path. Press `V` to pop back to Canvas at any time.
3. **Use the colored cards as your story beats.** "Here's where things go well (green), here's where users get stuck (amber confirmation), here's the failure mode we need to design out (red)."
4. **Stickies are your spoken-aloud notes.** Use them on the Canvas for "callout: this is where churn happens", "we need to instrument this transition", "open question: do we charge before or after confirmation?".
5. **Test screen-share zoom.** If your screen-share scales down, the in-canvas labels can become hard to read. Use `Cmd/Ctrl + +` in the browser to scale up, or zoom in with `+` on the canvas itself. Prototype mode is naturally larger and is often easier on screen-share.
6. **Have JOURNEY.md open on a second tab** — for stakeholder questions that go deeper than the canvas can show.

---

## Sharing the journey with others

The workspace is fully portable. Zip the entire workspace directory (`<workspace>.zip`) and send it. The recipient just unzips and double-clicks `index.html`. No installation needed on the recipient's side.

For online sharing (e.g. a Confluence page or wiki):

- Take screenshots of the fitted Canvas (`F`) and any Prototype screens
- Or commit the workspace to a git repo with GitHub Pages enabled — `index.html` works as-is on Pages

---

## Full keyboard reference

### Both views

| Key | Action |
|---|---|
| `V` | Switch to Canvas view |
| `P` | Switch to Prototype view |

### Canvas view

| Key | Action |
|---|---|
| Drag | Pan canvas (in empty space) |
| `Space` + drag | Pan canvas (anywhere) |
| `Cmd/Ctrl` + wheel | Zoom around cursor |
| Pinch (trackpad) | Zoom around cursor |
| `+` / `=` | Zoom in (around viewport center) |
| `−` / `_` | Zoom out (around viewport center) |
| `0` | Reset to 100% and recenter |
| `1` | Same as `0` |
| `F` | Fit all content to viewport |
| `H` | Toggle help overlay |
| `←` `→` `↑` `↓` | Nudge view by 60 px |
| Double-click a screen | Zoom + center on that screen + select it |
| Click on minimap | Pan to that world coordinate |

### Prototype view

| Key | Action |
|---|---|
| Click a hotspot | Follow that arrow's `to` screen |
| `Enter` | Follow the screen's default arrow |
| `J` | Next screen (document order) |
| `K` | Previous screen (document order) |
| `Backspace` | Back one step in history |
| Click a breadcrumb crumb | Rewind to that step |
| Click sidebar item | Jump to that screen (clears history) |
| Double-click sidebar item | Jump to that screen AND switch to Prototype |
