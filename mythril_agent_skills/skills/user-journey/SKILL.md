---
name: user-journey
description: |
  Draft and iterate user journey maps and lo-fi wireframes for product managers
  and business analysts via natural language. Outputs a self-contained
  workspace with synchronized JOURNEY.md (business + mermaid), journey.json
  (structured data), DESIGN.md (visual style, Google open spec), and a vanilla
  HTML/CSS/JS preview with map / stage / presenter views — no build step,
  open by double-clicking index.html.
  Trigger: "user journey", "journey map", "用户旅程", "用户旅程地图",
  "wireframe", "线框图", "low-fidelity", "低保真", "product flow",
  "客户旅程", "user flow map", "draft a journey", "画用户旅程",
  "出一份用户旅程", "before UX hi-fi", "在 UX 出高保真之前",
  "PM wireframe", "BA flow", "demo flow", or providing an existing
  user-journey workspace path to continue work.
  Also trigger when the user pastes a path to a directory containing
  JOURNEY.md or journey.json and asks to extend, refine, or present it.
license: Apache-2.0
---

# User Journey Skill

Help product managers and business analysts draft user journey maps and lo-fi wireframes through natural-language conversation. The output is a self-contained workspace that is portable, version-controllable, presentable in a browser, and resumable across sessions.

## When to Use This Skill

- The user wants to draft a **user journey map** or **customer journey**
- The user wants **lo-fi wireframes / flow diagrams** before UX produces hi-fi
- The user asks to **present a product flow** to stakeholders
- The user gives a path to an existing journey workspace and asks to continue / refine / extend
- Triggered by the phrases listed in the description

## Core Principles

1. **Three files form one source of truth** — they MUST stay in sync after every edit:

   | File | Audience | Role |
   |---|---|---|
   | `JOURNEY.md` | Humans (PM/BA/stakeholders) | Business requirements, persona, goals, mermaid flow, written narrative |
   | `journey.json` | Machine (the renderer) | Structured stages → steps + top-level `screens[]` (with `transitions[]` between them) |
   | `DESIGN.md` | Visual style (Google open spec) | Colors, typography, components — the CSS reads its tokens |

   `index.html` + `assets/*` are **pure renderers** — never hand-edit them.

2. **Screens-first authoring (when there is UI)** — For any journey that has a digital UI, do NOT settle for a stage map alone. The user wants to see **actual screens with controls** and the **arrows between them**. Workflow:

   - Define each unique UI screen once in `journey.json` `screens[]` with `id`, `kind` (mobile/atm/desktop/...), `layout` (containers + interactive elements), and `transitions[]` (which control jumps to which screen, with `from_element`, `trigger`, `to_screen`, `label`, and `is_default: true` on the happy path).
   - On each step, set `screen_refs: ["screen-id"]` to declare which screens that step displays.
   - A screen can be referenced by multiple steps — define once, reuse.

   Even a 5-stage journey is worth ~6–10 screens. Treat screens as first-class deliverables, not as an afterthought.

3. **Conversational, low-friction** — Infer everything possible from the user's message (language, project, persona type). Ask only what is genuinely missing. The user is a PM/BA, not a developer — never talk about HTML/CSS, JSON schemas, or git unless asked.

4. **Resumable** — Any session can be resumed by passing the workspace path. The skill reads all three files to rebuild full context.

5. **Browser-first preview** — Double-clicking `index.html` works in 99% of cases (journey data is inlined). If the user reports a blank page, fall back to `python3 preview.py` for a local HTTP server.

## Phase 1 — Intake & Workspace Bootstrap

### 1a. Auto-Infer

| Parameter | How to infer |
|---|---|
| **Language** | Match the user's message language. Chinese message → Chinese JOURNEY.md. English → English. |
| **Product / domain** | Extract from the message ("a food-delivery app", "B2B SaaS onboarding"). |
| **Primary persona** | Extract if mentioned, else ask in Phase 1b. |
| **Workspace path** | If the user gave a path → use it. Else default to `./journeys/<slug>/` in CWD. |
| **Design style** | If the user mentions a style ("playful", "corporate", "dark"), pick the closest preset. Else ask in Phase 1b. |
| **Existing workspace** | If the path already contains `JOURNEY.md` → this is a **resumption**, skip to Phase 4. |

### 1b. Confirm in ONE Block

Present a single confirmation message with all inferred values + gaps marked `_(请补充)_` / `_(please specify)_`. Example (Chinese):

> 我准备开始这份用户旅程，请确认或修改：
>
> - **产品 / 场景**: 外卖小程序首单引导
> - **主角色**: _（请补充：新用户？复购用户？商家？）_
> - **覆盖范围**: 从下载 App 到完成首单
> - **语言**: 中文
> - **视觉风格**: corporate-clean （可选：corporate-clean / playful-pastel / dark-engineering / editorial-mono）
> - **工作区**: `./journeys/food-delivery-first-order/`
>
> 回复确认，或调整任意一项。

After confirmation, run the bootstrap script:

```bash
python3 SKILL_PATH/scripts/init_workspace.py \
  --path "<workspace-path>" \
  --title "<product / scenario>" \
  --persona "<primary persona>" \
  --language en|zh \
  --design-style corporate-clean
```

The script creates the workspace with template `JOURNEY.md`, empty `journey.json` (just the persona scaffold), the chosen `DESIGN.md`, `index.html`, `assets/`, `preview.py`, and `README.md`. The workspace is **not** turned into a git repo — assume the user keeps multiple journeys under a parent repo they manage themselves.

**Design-style presets** ship with the skill at `SKILL_PATH/templates/design-styles/`:

| Preset | Best for | Personality |
|---|---|---|
| `corporate-clean` | B2B SaaS, enterprise, fintech | Neutral, serif headlines, restrained accent |
| `playful-pastel` | Consumer apps, kids/lifestyle | Rounded, pastel palette, friendly typography |
| `dark-engineering` | DevTools, infra dashboards | Dark surface, monospace, neon accent |
| `editorial-mono` | Content products, media | High-contrast mono headlines, generous whitespace |

If the user wants a custom palette, edit `DESIGN.md` directly after init — the renderer picks up changes on refresh.

## Phase 2 — Draft the Journey

Work in passes, each pass touches **all three files together**. Never edit one without the other two.

### Pass A — Skeleton

Co-author with the user:

1. **Persona block** — name, role, goals, frustrations, tech savvy (1–5).
2. **Stage list** — 3–7 stages at most for one journey (e.g., `Discover → Sign up → First task → Habit → Advocacy`). More than 7 stages indicates two journeys; split them.
3. **Scope statement** — "From X to Y" — one sentence.

Write Pass A into `JOURNEY.md` (prose + a mermaid `flowchart LR` of the stages) AND `journey.json` (stages with empty steps). Save and tell the user: "Skeleton is ready. Open `index.html` to see the map view. Next we'll fill in each stage's steps."

### Pass B — Per-Stage Detail

For each stage, ask or propose:

| Field | Required? | Example |
|---|---|---|
| `actions` | Yes | "Search for restaurants", "Browse menu" |
| `touchpoints` | Yes | "Home screen", "Search results", "Restaurant detail" |
| `thoughts` | Yes | "Will this arrive on time?" |
| `emotion` | Yes | one of `delighted / happy / neutral / frustrated / blocked` |
| `pain_points` | Optional | "Filters reset on back navigation" |
| `opportunities` | Optional | "Show ETA badge on each card" |
| `metrics` | Optional | "Add-to-cart rate", "Drop-off %" |

Encourage the user to think aloud. The skill is the scribe. Update **all three files** after each stage is filled in.

### Pass C — Screens & Transitions (when there is UI)

For each stage with digital touchpoints, design the screens **before** declaring done:

1. **List the unique screens** for the whole journey (6–15 is typical). One screen = one rendered UI state, not one moment in time. Reuse "main menu" across stages — define once.
2. For each screen, decide:
   - `id` (immutable slug, e.g. `pin-entry`)
   - `kind` (`mobile-screen` / `atm-screen` / `desktop-window` / ... — see `references/WIREFRAMES.md`)
   - `title` (display name)
   - `stage_id` (primary stage)
   - `layout` — use `stack` / `grid` / `row` containers with real interactive elements (`button`, `keypad-button`, `form-field`, `list-item`, `chip`, ...). Set `interactive: true` and a stable `id` on every element a user must tap.
3. For each screen, design the **outgoing transitions**:
   - One `is_default: true` on the happy path
   - Additional transitions for back / cancel / error / alt paths (`is_error_path: true` if applicable)
   - Use `from_element: "any"` for "tap anywhere to continue" splash screens
4. **Wire steps to screens** — set each step's `screen_refs: ["screen-id", ...]` in document order.

The renderer's Flow view (`F`) will then show every screen at full size with hotspot bubbles on interactive elements. Click a hotspot or use `Enter` (default) / `1`–`9` (n-th transition) / `Space` (auto-play) to walk the flow.

### Pass D — Polish

- Read `JOURNEY.md` end-to-end with the user; tighten language; add a TL;DR at top.
- Ensure the mermaid diagram in `JOURNEY.md` matches the stages in `journey.json` (use `validate_sync.py`).
- Walk each screen in Flow view; check that every interactive element either has a transition or is intentionally inert.

## Phase 3 — Sync Discipline (MANDATORY)

Three gates run after every change. All three must pass before declaring an edit done.

### Gate 1 — Sync Validator

```bash
python3 SKILL_PATH/scripts/validate_sync.py "<workspace-path>"
```

Compares `JOURNEY.md` + `journey.json` and reports drift (missing stages, mismatched step counts, undefined personas). **Never** declare an edit complete with drift outstanding.

### Gate 2 — Screens Validator

```bash
python3 SKILL_PATH/scripts/validate_screens.py "<workspace-path>"
```

Validates screens and transitions: unique screen ids, every `transitions.to_screen` and `step.screen_refs` resolves, every `transitions.from_element` exists in the layout, at most one `is_default: true` per screen, plus orphan / dead-end warnings. See [`references/SCREENS-RULES.md`](references/SCREENS-RULES.md).

### Gate 3 — Mermaid Compatibility

```bash
python3 SKILL_PATH/scripts/mermaid_lint.py "<workspace-path>/JOURNEY.md"
```

Lints every ` ```mermaid ` block in `JOURNEY.md` against the rules in [`references/MERMAID-RULES.md`](references/MERMAID-RULES.md). The single most common authoring bug it catches is using `\n` (literal backslash-n) for line breaks inside a node label — on most renderers (GitHub, Mermaid 10.x, Confluence, Notion exports) `\n` does NOT become a newline. The fix is `<br/>`:

```
A[xxx-api\n(Domain API)]         ← BAD
A["xxx-api<br/>(Domain API)"]    ← GOOD (quotes needed because of `()`)
```

When writing mermaid programmatically from structured data, use the bundled escape helper:

```python
from mermaid_lint import escape_label_for_mermaid

label = escape_label_for_mermaid(stage["name"])  # handles \n, quotes, parens
```

`init_workspace.py` already does this — apply the same when you hand-edit the diagram or add new nodes.

### When the user requests an edit (add a stage, rename a step, add a screen, rewire a transition, change emotion):

1. Update `journey.json` (the structured source).
2. Regenerate the affected section of `JOURNEY.md` from the JSON (prose + mermaid). Use `<br/>` for any line break inside a mermaid label.
3. Run `validate_sync.py`, `validate_screens.py`, AND `mermaid_lint.py`. All must pass.
4. Tell the user what changed in plain language.

## Phase 4 — Resumption (User Returns Later)

When the user provides a workspace path and asks to continue:

1. Read `JOURNEY.md` (business context, persona, narrative).
2. Read `journey.json` (current structured state).
3. Read `DESIGN.md` (visual style).
4. Optionally `git log --oneline -20` for recent change history.
5. Confirm understanding in one short message:
   > 已加载工作区。当前覆盖 4 个阶段（Discover → Sign up → First task → Habit），共 11 个步骤。最近一次修改：调整了 "Sign up" 的痛点。要继续做什么？

Never start editing without the user's go-ahead.

## Phase 5 — Present / Demo Mode

When the user says "I'll present this to stakeholders" / "演示一下" / "give a walkthrough":

1. Tell them to open `index.html` and press `P` for presenter mode (or click the "Present" button top-right).
2. In presenter mode: arrow keys advance / go back; one stage per slide; large type; speaker notes (from `journey.json`'s `notes` field) appear at the bottom.
3. **For UI walkthroughs**, press `Space` inside a stage that has `screen_refs` to enter screen-playback mode — every screen of that stage plays back in order, with hotspots and transitions visible. `Space` again advances along the `is_default` transition; `←` rewinds; `Esc` returns to the stage slide.
4. For free-form screen exploration outside the presenter, the Flow view (`F`) lets the reviewer click any screen and walk it interactively.
5. Press `Esc` (in stage mode) to exit presenter.
6. If they want to share via screen-share, `python3 preview.py` opens a local server — link only works on their machine but avoids any `file://` quirks during screen capture.

## How to View / Run the Output (Tell the User This)

Standard answer for every workspace:

> **打开方式**：双击工作区里的 `index.html` 即可在浏览器中打开。
>
> 四种视图（右上角切换或键盘快捷键）：
>
> - **Map** — 全景旅程地图（M）
> - **Stage** — 单阶段细节（S，左右键切换阶段）
> - **Flow** — 屏与跳转（F，左侧选屏，热区悬停看跳转，点击跳屏）
> - **Presenter** — 全屏演示（P，左右键翻页，Space 进入屏播放，Esc 退出）
>
> 如果双击打开后页面空白（极少数浏览器禁用 `file://` 读 JSON），在工作区运行 `python3 preview.py`，自动打开 `http://localhost:8765`。

## Security

This skill does NOT require API tokens or credentials. It writes only to the user-provided workspace path. No network calls. No environment variables.

## File Locations Reference

| Item | Path |
|---|---|
| Bootstrap script | `SKILL_PATH/scripts/init_workspace.py` |
| Sync validator | `SKILL_PATH/scripts/validate_sync.py` |
| Screens validator | `SKILL_PATH/scripts/validate_screens.py` |
| Mermaid lint (compat gate) | `SKILL_PATH/scripts/mermaid_lint.py` |
| HTML/CSS/JS templates | `SKILL_PATH/templates/workspace/` |
| Design-style presets | `SKILL_PATH/templates/design-styles/*.md` |
| Wireframe primitives reference | `SKILL_PATH/references/WIREFRAMES.md` |
| journey.json schema reference | `SKILL_PATH/references/SCHEMA.md` |
| Sync rules reference | `SKILL_PATH/references/SYNC-RULES.md` |
| Screens rules reference | `SKILL_PATH/references/SCREENS-RULES.md` |
| Mermaid rules reference | `SKILL_PATH/references/MERMAID-RULES.md` |
| Presenting & views reference | `SKILL_PATH/references/PRESENTING.md` |

## Anti-Patterns to Avoid

- ❌ Editing `index.html` or `assets/*` by hand — they are generated renderers
- ❌ Updating `JOURNEY.md` without also updating `journey.json` (or vice versa)
- ❌ Talking to the PM about HTML/CSS/JSON internals
- ❌ Treating screens as optional. For any journey with UI, the screens-first principle (Pass C) is mandatory — a stakeholder asks "show me the screen" and that needs to work.
- ❌ Defining the same screen twice with different ids — define once in `screens[]`, reference by id from multiple steps.
- ❌ Forgetting to mark a happy-path transition with `is_default: true` — Presenter auto-play and `Enter` to advance both depend on it.
- ❌ Cramming more than 7 stages into one journey — split it
- ❌ Asking 10 questions upfront — infer and confirm in ONE block
- ❌ Declaring done without running ALL THREE: `validate_sync.py`, `validate_screens.py`, AND `mermaid_lint.py`
- ❌ Using `\n` for line breaks inside a mermaid label — use `<br/>` instead (see `references/MERMAID-RULES.md`)
