# User Journey

Draft and iterate **user journey maps** and **lo-fi wireframes** for product managers and business analysts via natural-language conversation. Outputs a self-contained workspace that is portable, version-controllable, presentable in a browser, and resumable across sessions.

## When to use

- You need a journey map for a kickoff or stakeholder review
- You want lo-fi wireframes before UX produces hi-fi designs
- You want to present a product flow to stakeholders in the browser
- You're returning to a journey you started in a previous session

## What the skill produces

For every journey, the skill creates a single directory like this:

```
food-delivery-first-order/
├── JOURNEY.md            ← business requirements + mermaid + narrative (for humans)
├── journey.json          ← structured stages and steps (for the renderer)
├── DESIGN.md             ← visual style (Google open spec — pick from 4 presets)
├── index.html            ← double-click to preview
├── README.md             ← how-to-view instructions
├── preview.py            ← local HTTP fallback (python3 preview.py)
└── assets/
    ├── styles.css        ← reads DESIGN.md tokens
    ├── render.js         ← renders map / stage / presenter views
    └── wireframe.js      ← renders inline lo-fi mocks
```

All three knowledge files (`JOURNEY.md`, `journey.json`, `DESIGN.md`) stay synchronized by skill rules. If a session is interrupted, just give the AI the workspace path — it reads all three to rebuild full context.

## How to view

**Double-click `index.html`** in the workspace. Works offline, no install needed. Three views, switched by toolbar buttons or keyboard:

| View | Key | Use for |
|---|---|---|
| Map | `M` | Overview of all stages — pan/zoom with mouse |
| Stage | `S` | One stage in detail — `←` `→` to navigate |
| Presenter | `P` | Full-screen demo — `←` `→` advance, `B` blank, `Esc` exit |

If the page is blank (some browsers block `file://` fetches), run `python3 preview.py` in the workspace — opens `http://localhost:8765` automatically.

## Design styles

The skill ships with 4 presets (Google [DESIGN.md](https://github.com/google-labs-code/design.md) format):

| Preset | For | Vibe |
|---|---|---|
| `corporate-clean` | B2B SaaS, fintech | Neutral, trust blue, restrained |
| `playful-pastel` | Consumer apps | Coral pink, rounded, friendly |
| `dark-engineering` | DevTools, dashboards | Dark surface, mono type, neon cyan |
| `editorial-mono` | Content products | Serif headlines, generous whitespace |

You pick one at workspace creation. To swap later, copy a different preset over `DESIGN.md` and refresh the browser.

## How to use

Just tell your AI assistant:

```
Draft a user journey for our food-delivery first-order flow
画一份外卖小程序首单引导的用户旅程
Continue this user journey: /path/to/my-workspace
基于这个工作区继续：/path/to/my-workspace
```

The skill will ask you 1–2 questions (persona, design style) in one block, then create the workspace and start iterating. Follow up in plain language — "add a stage between Sign up and First task", "change the emotion at checkout to delighted", "fill in the wireframe for the search results screen", etc.

## Prerequisites

- Python 3.10+ (for the bootstrap script and the optional local preview server)
- `git` CLI (optional — used to track changes in the workspace)
- A modern browser (Chrome 110+, Firefox 110+, Safari 16+)

No external API keys. No npm. No build step. No internet required after creation.
