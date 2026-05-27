# Presenting and Viewing the Journey

Tell the user this every time you finish a journey or workspace bootstrap:

## How to open

**Default — double-click `index.html`** in the workspace. Opens in the default browser. Works offline, no server, no install.

**If the page is blank** (some browsers block local `fetch()` for `file://`):

```bash
cd <workspace>
python3 preview.py
```

This launches a local web server on `http://localhost:8765` and opens the browser automatically. Press `Ctrl+C` to stop. Requires only Python 3.10+ standard library.

## The three views

A toolbar in the top-right of every view switches between them. Each has a keyboard shortcut.

### Map view (`M`)

Default. Shows the entire journey as a horizontal flow of stage cards with connecting arrows. Each card displays:

- Stage label and summary
- Emotion strip (a row of colored dots, one per step, colored by the step's emotion)
- Step count

Pan: click-drag empty space. Zoom: mouse-wheel, pinch, or `+` / `-` keys. `0` resets zoom.

Click a stage card → switches to Stage view for that stage.

### Stage view (`S`)

Drill-down for one stage. Shows all of its steps side-by-side as columns:

- Actions
- Touchpoints
- Thoughts
- Emotion (chip)
- Pain points (red)
- Opportunities (green)
- Metrics (cards)
- Inline wireframe (if present)

Navigate stages: `←` / `→` arrow keys, or click the stage chips in the breadcrumb.

### Presenter view (`P`)

Full-screen, one stage per slide. Designed for screen-share demos to stakeholders.

- Big stage title and summary on top
- 3-column layout: actions + touchpoints + thoughts
- Speaker notes (`stage.notes`) docked at the bottom — visible only on the presenter's screen if they're using a second monitor, otherwise on the main slide
- Progress dots top-right show position in the journey

Controls: `←` / `→` advance; `Esc` exits to map; `B` blanks the screen (useful when discussion goes off the slide).

## Tips for presenting to stakeholders

1. **Open in presenter mode from the start** — `index.html#present`. Or set the URL hash to `#present/<stage-id>` to start on a specific stage.
2. **Test screen-share zoom** — presenter mode uses 24 px body text by default; if your screen-share scales down, increase via `Cmd/Ctrl + +` in the browser.
3. **Have JOURNEY.md open on a second tab** — for stakeholder questions that go deeper than the slide can show.
4. **Don't open Stage view during a live demo** — it's information-dense; better for design review sessions than for stakeholder demos.

## Sharing the journey with others

The workspace is fully portable. Zip the entire workspace directory (`<workspace>.zip`) and send it. The recipient just unzips and double-clicks `index.html`. No installation needed on the recipient's side.

For online sharing (e.g. a Confluence page or wiki):

- Take screenshots of the map view and key stages
- Or commit the workspace to a git repo with GitHub Pages enabled — `index.html` works as-is on Pages

## URL hash routes (for deep linking)

The renderer treats the URL hash as a router so you can link to specific views:

| Hash | View |
|---|---|
| (empty) or `#map` | Map view, all stages |
| `#stage/<stage-id>` | Stage view focused on that stage |
| `#present` | Presenter view, first stage |
| `#present/<stage-id>` | Presenter view starting on that stage |

This makes it easy to drop a deep link into a Slack message or Jira ticket.
