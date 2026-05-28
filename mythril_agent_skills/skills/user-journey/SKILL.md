---
name: user-journey
description: |
  Draft and iterate user journey maps and lo-fi wireframes for product managers
  and business analysts via natural language. Outputs a self-contained
  workspace with synchronized JOURNEY.md (business + mermaid), journey.json
  (structured data + screens + arrows), DESIGN.md (visual style), and a
  dual-view HTML: Canvas (Miro-style overview, all screens on one zoom/pan
  surface with arrows + minimap) AND Prototype (single-screen click-through
  with hotspots, breadcrumb, sidebar nav). No build step, double-click index.html.
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

Help product managers and business analysts draft user journey maps and lo-fi wireframes through natural-language conversation. The output is a **single Miro-style canvas** — every screen of the journey laid out on one infinite, pan-and-zoomable surface, connected by arrows. Self-contained, version-controllable, presentable in a browser, resumable across sessions.

## When to Use This Skill

- The user wants to draft a **user journey map** or **customer journey**
- The user wants **lo-fi wireframes / flow diagrams** before UX produces hi-fi
- The user asks to **walk a stakeholder through a product flow**
- The user gives a path to an existing journey workspace and asks to continue / refine / extend
- Triggered by the phrases listed in the description

## Core Principles

1. **Three files form one source of truth** — they MUST stay in sync after every edit:

   | File | Audience | Role |
   |---|---|---|
   | `JOURNEY.md` | Humans (PM/BA/stakeholders) | Business requirements, persona, goals, mermaid flow, written narrative |
   | `journey.json` | Machine (the renderer) | Structured stages, steps, top-level `screens[]`, top-level `arrows[]`, optional `stickies[]` |
   | `DESIGN.md` | Visual style (Google open spec) | Colors, typography, components — the CSS reads its tokens |

   `index.html` + `assets/*` are **pure renderers** — never hand-edit them.

2. **Dual view: Canvas + Prototype.** v3 renders TWO complementary views of the same `journey.json`:

   - **Canvas** (default): a **Miro-style overview** — all screens laid out in columns by stage, connected by arrows, with optional stickies. Pan, zoom, fit, click the minimap. Use this for narrative walk-throughs and stakeholder presentations.
   - **Prototype**: a **single-screen click-through** — one screen at actual size with hotspots (any element with an outgoing arrow becomes a clickable element with a dashed blue ring). Breadcrumb tracks history, sidebar lists every screen. Use this for demo flows, dead-end checks, and design review.

   Both views are driven by the same data; switching is `V` / `P` or the topbar tabs. Sidebar selection, current-screen highlight, and history are shared. Never tell the user to choose one or the other — both are always available.

3. **Screens-first authoring (when there is UI).** For any journey with a digital UI, do NOT settle for a stage map alone. Define each unique UI screen once in `journey.json` `screens[]` with `id`, `kind`, `state`, `layout`, and (optionally) `position`. Then wire the screens together with top-level `arrows[]`.

   Even a 5-stage journey is worth ~10 screens. Aim for at least `max(stages × 2, 8)` screens — fewer and the canvas feels empty.

4. **State on each screen drives the colored card.** Every screen renders inside an outer colored card whose color comes from `screen.state`:
   - `default` (gray) — normal browse/select/read
   - `loading` (blue) — "Processing…", spinner screens
   - `success` (green) — success acknowledgements
   - `error` (red) — failure / blocked screens
   - `warning` (amber) — "are you sure?" / risk screens

   Use the state intentionally — it's how stakeholders skim the canvas and immediately see "this is the happy path, this is the failure mode".

5. **Design-pattern sense beats element soup.** Lo-fi does NOT mean "stack of atoms". Reach for **composition primitives** (`app-bar`, `section`, `key-value-list`, `stat-tile`, `alert`, `step-indicator`, `empty-state`, `footer-bar`) BEFORE dropping `button`/`text`/`form-field` directly into a `stack`. Every screen should follow the **zone model**:
   - Top zone: `app-bar` (or `header`) with title + actions
   - Body zone: 2–4 named `section`s — never a flat stack of 10+ atoms
   - Bottom zone: `tab-bar` (navigation) OR `footer-bar` (primary action)

   A wireframe that reads "title bar, two clearly-labeled sections, fixed bottom action" looks designed. A wireframe that reads "header + 8 buttons in a column" looks unfinished. The validator (`validate_screens.py`) flags `[flat-stack]`, `[no-hierarchy]`, `[monotonous]`, and `[overstuffed]` smells — listen to them.

6. **Conversational, low-friction.** Infer everything possible from the user's message (language, project, persona type). Ask only what is genuinely missing. The user is a PM/BA, not a developer — never talk about HTML/CSS, JSON schemas, or git unless asked.

7. **Resumable.** Any session can be resumed by passing the workspace path. The skill reads all three files to rebuild full context.

8. **Browser-first preview.** Double-clicking `index.html` works in 99% of cases (journey data is inlined). If the user reports a blank page, fall back to `python3 preview.py`.

## Phase 1 — Intake & Workspace Bootstrap

### 1a. Auto-Infer

| Parameter | How to infer |
|---|---|
| **Language** | Match the user's message language. Chinese message → Chinese JOURNEY.md. English → English. |
| **Product / domain** | Extract from the message ("a food-delivery app", "B2B SaaS onboarding"). |
| **Primary persona** | Extract if mentioned, else ask in Phase 1b. |
| **Workspace path** | If the user gave a path → use it. Else default to `./journeys/<slug>/` in CWD. |
| **Design style** | If the user mentions a style ("playful", "corporate", "dark"), pick the closest preset. Else ask in Phase 1b. |
| **Device kind** | Infer from the message: "ATM" → `atm`; "app / 小程序 / 手机" → `mobile`; "kiosk / 自助机" → `kiosk`; "web / SaaS / 后台" → `desktop`; "TV / 电视 / 大屏" → `tv`. **If you can't tell, ask in 1b** — getting this wrong (e.g. modeling an ATM as a phone) is the #1 cause of "this doesn't look right" complaints. |
| **Existing workspace** | If the path already contains `JOURNEY.md` → this is a **resumption**, skip to Phase 4. |

### 1b. Confirm in ONE Block

Present a single confirmation message with all inferred values + gaps marked `_(请补充)_` / `_(please specify)_`. Example (Chinese):

> 我准备开始这份用户旅程，请确认或修改：
>
> - **产品 / 场景**: 外卖小程序首单引导
> - **主角色**: _（请补充：新用户？复购用户？商家？）_
> - **覆盖范围**: 从下载 App 到完成首单
> - **语言**: 中文
> - **主要设备形态**: mobile（手机 App）_（可选：mobile / atm / kiosk / desktop / tv）_
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
  --design-style corporate-clean \
  --device-kind mobile|atm|kiosk|desktop|tv
```

The script creates the workspace with template `JOURNEY.md`, seed `journey.json` (3 screens demoing the device kind + 3 arrows + 1 sticky), the chosen `DESIGN.md`, `index.html`, `assets/`, `preview.py`, and `README.md`. The seed screens are tailored for the device kind so the user opens straight into a representative canvas (ATM → chrome + side-key-rail; mobile → tab bar; kiosk → scanner + NFC; etc. — see `references/WIREFRAMES.md`). The workspace is **not** turned into a git repo.

**Design-style presets** ship with the skill at `SKILL_PATH/templates/design-styles/`:

| Preset | Best for | Personality |
|---|---|---|
| `corporate-clean` | B2B SaaS, enterprise, fintech | Neutral, serif headlines, restrained accent |
| `playful-pastel` | Consumer apps, kids/lifestyle | Rounded, pastel palette, friendly typography |
| `dark-engineering` | DevTools, infra dashboards | Dark surface, monospace, neon accent |
| `editorial-mono` | Content products, media | High-contrast mono headlines, generous whitespace |

If the user wants a custom palette, edit `DESIGN.md` directly after init.

## Phase 2 — Draft the Journey

Work in passes, each pass touches **all three files together**. Never edit one without the other two.

### Pass A — Skeleton

Co-author with the user:

1. **Persona block** — name, role, goals, frustrations, tech savvy (1–5).
2. **Stage list** — 3–7 stages at most for one journey. More than 7 stages indicates two journeys; split them.
3. **Scope statement** — "From X to Y" — one sentence.

Write Pass A into `JOURNEY.md` (prose + mermaid `flowchart LR` of stages) AND `journey.json` (stages with empty steps). Tell the user: "Skeleton is ready. Open `index.html` — you'll see the seed screens on the canvas. Let's design the real screens next."

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

The skill is the scribe. Update **all three files** after each stage is filled in.

### Pass C — Screens & Arrows (when there is UI)

For each stage with digital touchpoints, design the screens **before** declaring done:

1. **List the unique screens** for the whole journey. Aim for at least `max(stages × 2, 8)`.
2. For each screen, decide:
   - `id` (immutable slug, e.g. `pin-entry`)
   - `kind` (`mobile-screen` / `atm-screen` / `desktop-window` / ... — see `references/WIREFRAMES.md`)
   - `title` (display name; shown in the colored card header)
   - `stage_id` (drives canvas column placement)
   - `state` (`default` / `loading` / `success` / `error` / `warning` — drives outer card color)
   - `layout` — **compose with patterns, not atoms**. See "Composition checklist" below.
3. **Stay true to the device form** (see "Device-aware modeling" below). Modeling an ATM as a vertical stack of phone-style buttons is the #1 quality bug — use `side-key-rail`, `hardware-slot`, and `chrome: "panel"` for ATM/kiosk screens.
4. **Wire screens with arrows.** For each meaningful transition, add an entry to the top-level `arrows[]`:
   - `from: "<screen-id>#<element-id>"` (e.g. `"pin-entry#confirm"`) for a transition triggered by a specific button / key / hardware slot, or `from: "<screen-id>"` for a whole-screen transition (e.g. timeout, auto)
   - `to: "<screen-id>"` — the target
   - `kind: "default" | "success" | "error" | "cancel"` — drives arrow color
   - `trigger: "tap" | "insert-card" | "input" | "timeout" | "auto" | ...`
   - `label` — short description rendered on the arrow
   - `is_default: true` on the happy-path arrow out of each screen (at most one per source)
5. **Wire steps to screens** — set each step's `screen_refs: ["screen-id"]` in document order. This is the textual index that lives in `JOURNEY.md`.

#### Composition checklist (MANDATORY before declaring Pass C done)

Every screen with non-trivial content (>4 atomic elements) must satisfy ALL of these. The validator catches the smells but the AI should self-check first.

- [ ] **Zone model**: top zone has `app-bar` (or `header`), bottom zone has `tab-bar` / `footer-bar` when appropriate.
- [ ] **At least one structural primitive** in the body: `section`, `app-bar`, `tab-bar`, `step-indicator`, `alert`, or `empty-state`. NEVER let a root `stack` contain >8 raw atoms with no grouping.
- [ ] **2–4 named sections** with `title` (and optional `subtitle` / `action`). Not 1 giant section, not 8 atoms-in-a-row.
- [ ] **Pattern picked from the recipe table** (`WIREFRAMES.md` → "Composition recipes"). Examples:
  - Dashboard → `app-bar prominent` + `stat-tile` grid + list section + `tab-bar`
  - Settings → `app-bar` + 2-4 `section`s of `list-item`s + optional `footer-bar`
  - Form → `app-bar` + optional `step-indicator` + grouped `form-field`s + `footer-bar`
  - Confirmation/summary → `app-bar` + `step-indicator` + `key-value-list` + `footer-bar` with total
  - Empty result → `app-bar` + `empty-state`
  - Status (loading/success/error) → matching `screen.state` + body `empty-state`-style block
- [ ] **Mix at least two atomic primitives** in the body. A screen made entirely of buttons reads as a sketch, not a wireframe.
- [ ] **Each section has ≤ 6 immediate children**. If a section grows past 6, split it.
- [ ] **Interactive elements have a stable `id`** so arrows can attach.
- [ ] **`is_default: true`** is set on the happy-path arrow out of each screen (at most one per source).

Run `python3 SKILL_PATH/scripts/validate_screens.py "<workspace-path>"` after Pass C — it flags `[flat-stack]`, `[no-hierarchy]`, `[monotonous]`, and `[overstuffed]` smells. Fix them before declaring done.

The canvas auto-lays out screens in columns (one column per stage), so you usually don't need to set explicit `position`. Use `position: {x, y}` only when you want to override the default placement (e.g. "this error screen sits below the happy path screen").

#### Device-aware modeling (MANDATORY when the journey has UI)

The same `button` and `stack` primitives can model a phone or a 1980s ATM — but the result only looks right if you reach for the device-specific vocabulary when the device demands it.

| Device `kind`     | What it MUST use | What it MUST NOT do |
|---|---|---|
| `mobile-screen`   | Touch buttons in `stack`/`grid`; optional `tab-bar` | Never use `side-key-rail` |
| `tablet-screen`   | Same as mobile, wider | Same |
| `desktop-window`  | `header` + content; multi-column dashboards | Never use `keypad-button` for primary CTAs |
| `atm-screen`      | **`side-key-rail`** for menus (left/right); `keypad-button` `grid cols=3` for numeric input; **`chrome: "panel"` with `hardware[]`** (card-reader / cash-out / receipt) on transactional screens | Never model the main menu as a vertical stack of fat buttons |
| `kiosk-screen`    | Big chunky touch buttons; `chrome: "panel"` if a chassis is visible; `hardware-slot` for `barcode-scanner` / `nfc` | Don't add a `tab-bar` |
| `tv-screen`       | Horizontal carousels, large fonts, focused-state via `state: "hover"` | No scroll-only lists, no `form-field` typing flows |

**Self-check**: for every `atm-screen` or `kiosk-screen` in `screens[]`, verify the layout contains at least one of: `side-key-rail`, `hardware-slot`, or top-level `chrome: "panel"`. If not, you almost certainly modeled it as a phone — `validate_screens.py` will warn you.

See `references/WIREFRAMES.md` "Device-aware modeling" + "End-to-end example B" for a worked ATM main-menu screen.

### Pass D — Polish

- Read `JOURNEY.md` end-to-end with the user; tighten language; add a TL;DR at top.
- Ensure the mermaid diagram in `JOURNEY.md` matches the stages in `journey.json` (use `validate_sync.py`).
- Walk every screen on the canvas; check that every interactive element either has an outgoing arrow or is intentionally inert.
- Add stickies for non-UI annotations: blockers, decisions, callouts.

## Phase 3 — Sync Discipline (MANDATORY)

Three gates run after every change. All three must pass before declaring an edit done.

### Gate 1 — Sync Validator

```bash
python3 SKILL_PATH/scripts/validate_sync.py "<workspace-path>"
```

Compares `JOURNEY.md` + `journey.json` and reports drift (missing stages, mismatched step counts, undefined personas). **Never** declare an edit complete with drift outstanding.

### Gate 2 — Screens + Arrows Validator

```bash
# During iteration — warnings are informational:
python3 SKILL_PATH/scripts/validate_screens.py "<workspace-path>"

# Before declaring the journey "done" or before handing it to the user — strict mode:
python3 SKILL_PATH/scripts/validate_screens.py "<workspace-path>" --strict
```

Validates screens and arrows: unique screen ids, every `arrow.to` and `step.screen_refs` resolves, every `arrow.from` resolves (screen + element), at most one `is_default: true` arrow per source screen, plus orphan / dead-end warnings.

It also enforces two **harness-level** rules:

- **Device-aware modeling**: any `atm-screen` / `kiosk-screen` with no `side-key-rail`, no `hardware-slot`, and no `chrome: "panel"` raises a warning.
- **Screen-count floor**: a journey with N stages should have at least `max(N×2, 8)` screens. Warning by default; promoted to **error** under `--strict`. Always run `--strict` before declaring the journey final.

See [`references/SCREENS-RULES.md`](references/SCREENS-RULES.md) for the full rule list.

### Gate 3 — Mermaid Compatibility

```bash
python3 SKILL_PATH/scripts/mermaid_lint.py "<workspace-path>/JOURNEY.md"
```

Lints every ` ```mermaid ` block in `JOURNEY.md` against the rules in [`references/MERMAID-RULES.md`](references/MERMAID-RULES.md).

### When the user requests an edit (add a stage, rename a step, add a screen, rewire an arrow, change state):

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
   > 已加载工作区。当前覆盖 4 个阶段（Discover → Sign up → First task → Habit），共 12 个屏，18 条箭头。最近一次修改：调整了 "Sign up" 的痛点。要继续做什么？

Never start editing without the user's go-ahead.

## Phase 5 — Present / Demo

When the user says "I'll present this to stakeholders" / "演示一下" / "give a walkthrough":

1. Tell them to open `index.html`. They'll see the **sidebar** (every screen listed) + a **Canvas / Prototype** view switcher at the top.
2. For an overview / narrative: use **Canvas**. Press `F` to fit-all, pan / zoom to walk through the journey. The colored cards make the narrative obvious — green = success path, red = error path, amber = warning/confirmation, blue = loading, gray = neutral.
3. For a demo: switch to **Prototype** (press `P`). The current screen renders at actual size; clickable hotspots have dashed blue rings. Click them to walk the user flow, press `Enter` to follow the default arrow, `Backspace` to step back. Far easier to follow than zooming around the canvas.
4. Use stickies for "here's where we need to validate", "here's the open question" — they only appear in Canvas mode.
5. If they want to share via screen-share, `python3 preview.py` opens a local server.

See [`references/PRESENTING.md`](references/PRESENTING.md) for full canvas + prototype tips.

## How to View / Run the Output (Tell the User This)

Standard answer for every workspace:

> **打开方式**：双击工作区里的 `index.html`，浏览器会打开一个双视图工作台:
>
> - **左侧 Sidebar**: 列出所有屏(按阶段分组)，点击切换，双击进入 Prototype。
> - **Canvas 模式 (默认)**: Miro 风格的整体画布，所有屏铺开、用箭头连接。
>   - 拖动空白处平移; 按住 `Space` 拖动也可以(Miro 风格)
>   - `Cmd/Ctrl` + 滚轮 或 触控板捏合 缩放
>   - `+` / `−` / `0` / `F` 缩放和自适应
>   - 双击某个屏 → 缩放并居中到那个屏
>   - 右下角的小地图(minimap)点击可快速跳转
> - **Prototype 模式 (`P` 切换)**: 一次显示一个屏，元素上虚线蓝框 = 可点击;点击会按箭头跳到目标屏。`Enter` 跟随默认箭头，`Backspace` 回退。适合走查/演示。
> - `V` / `P` 在 Canvas / Prototype 之间切换;`H` 看完整快捷键。
>
> 如果双击打开后页面空白，在工作区运行 `python3 preview.py`，自动打开 `http://localhost:8765`。

## Security

This skill does NOT require API tokens or credentials. It writes only to the user-provided workspace path. No network calls. No environment variables.

## File Locations Reference

| Item | Path |
|---|---|
| Bootstrap script | `SKILL_PATH/scripts/init_workspace.py` |
| Sync validator | `SKILL_PATH/scripts/validate_sync.py` |
| Screens + arrows validator | `SKILL_PATH/scripts/validate_screens.py` |
| Mermaid lint (compat gate) | `SKILL_PATH/scripts/mermaid_lint.py` |
| HTML/CSS/JS templates | `SKILL_PATH/templates/workspace/` |
| Design-style presets | `SKILL_PATH/templates/design-styles/*.md` |
| Wireframe primitives reference | `SKILL_PATH/references/WIREFRAMES.md` |
| journey.json schema reference | `SKILL_PATH/references/SCHEMA.md` |
| Sync rules reference | `SKILL_PATH/references/SYNC-RULES.md` |
| Screens + arrows rules reference | `SKILL_PATH/references/SCREENS-RULES.md` |
| Mermaid rules reference | `SKILL_PATH/references/MERMAID-RULES.md` |
| Canvas + presenting reference | `SKILL_PATH/references/PRESENTING.md` |

## Anti-Patterns to Avoid

- ❌ Editing `index.html` or `assets/*` by hand — they are generated renderers
- ❌ Updating `JOURNEY.md` without also updating `journey.json` (or vice versa)
- ❌ Talking to the PM about HTML/CSS/JSON internals
- ❌ Treating screens as optional. For any journey with UI, the screens-first principle (Pass C) is mandatory.
- ❌ **Flat element soup** — dropping 10 raw atoms (button, text, form-field) into a single `stack` instead of composing with `app-bar` + `section` + `footer-bar`. The validator will warn with `[flat-stack]` and `[no-hierarchy]`.
- ❌ **Monotonous screens** — a screen that's 100% buttons or 100% text lines. Mix at least 2 different atomic primitives plus a structural one.
- ❌ **Overstuffed sections** — more than 6 immediate children in one `section`. Split into two named sections.
- ❌ **Skipping the zone model** — no `app-bar` on a mobile/desktop screen, or no `footer-bar`/`tab-bar` on a screen that clearly needs a fixed bottom action.
- ❌ Defining the same screen twice with different ids — define once in `screens[]`, reference by id from multiple steps and arrows.
- ❌ Forgetting to mark a happy-path arrow with `is_default: true`.
- ❌ Cramming more than 7 stages into one journey — split it.
- ❌ Asking 10 questions upfront — infer and confirm in ONE block.
- ❌ Declaring done without running ALL THREE: `validate_sync.py`, `validate_screens.py`, AND `mermaid_lint.py`.
- ❌ Using `\n` for line breaks inside a mermaid label — use `<br/>` instead.
- ❌ Setting `screen.state` to `success` on every screen — state should mean something. Use it intentionally.
