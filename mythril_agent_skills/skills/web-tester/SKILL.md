---
name: web-tester
description: >
  Black-box GUI testing of web apps in a real browser: click/tap/type/scroll/
  swipe through the page under test, capture screenshots, collect console and
  page errors, and produce an evidence-backed test report. Cross-agent (works
  in ZCode, Claude Code, opencode, Cursor, any shell-capable agent) via a
  capability ladder: session-native browser tooling, then @playwright/mcp,
  then the bundled Playwright toolbox. Profiles: desktop, mobile web (device
  emulation, tap/swipe/long-press, portrait/landscape), canvas games
  (coordinate interaction, screenshot verification, read-only debug hook).
  Trigger on: testing a webpage/web app/frontend after a code change,
  reproducing a frontend bug, checking interaction feedback or layout,
  mobile/touch/canvas game testing, "test this page", "mobile web test",
  "帮我测试这个页面", "点一下看看效果", "测试一下交互", "移动端页面测试",
  "游戏交互测试", "canvas 游戏测试", "UI 黑盒测试".
license: Apache-2.0
---

# web-tester — Cross-Agent Web GUI Testing

Black-box GUI testing for web apps: desktop sites, mobile web pages, and
canvas-heavy HTML5 games. Works in any agent that has shell access — no
harness-specific dependency is required.

## When to Use This Skill

- "Test this page / web app / frontend feature" — click through and verify.
- Verify UI behavior after a code change (interaction feedback, states, layout).
- Reproduce a frontend bug from a user description.
- Test a mobile web page: device emulation, touch gestures, portrait/landscape.
- Test an HTML5/canvas game: coordinate interaction, visual state verification.
- Collect console/page errors as evidence for a bug report.

Not for: CI regression suites (the project under test should own its own
Playwright e2e tests for that), API-only testing, or native mobile apps.

## Step 0 — Capability Detection (do this first, every session)

Detect what browser tooling the current session provides, in this order:

| # | Check | If available |
|---|-------|--------------|
| 1 | Session-native browser automation (e.g. a bundled browser-use /
    `control-browser` / `web-gui-tester` skill or tool in this session) | Use it and follow **its own usage skill/docs first**. Its rules for actions, waiting, and screenshots win over this file. Then jump to [Universal Test Loop](#universal-test-loop). |
| 2 | The harness supports MCP server configuration | Propose installing the official [`@playwright/mcp`](https://github.com/microsoft/playwright-mcp) server (follow its README for the harness's config format; do not hand-roll an MCP server). After it is configured, use its tools and jump to the Test Loop. |
| 3 | Neither (only Bash + Node ≥ 18) | Use the [Bundled Toolbox](#bundled-toolbox-fallback-path) below. |

Rules:

- Never skip detection. If level 1 exists, prefer it even if levels 2–3 are set up.
- Whichever tooling wins, the **Test Loop**, **Profiles**, and **Report** sections
  below apply unchanged — only the mechanics of "click" and "screenshot" differ.
- If the user explicitly picked a browser tool, use their choice.

## Universal Test Loop

1. **Plan.** Clarify the objective and acceptance criteria. If only a URL or
   "test it" was given, explore the page first, then organize test points by
   priority: P0 main flows → P1 interaction feedback (loading, success/failure,
   disabled states) → P2 input boundaries → P3 layout/styling. Show the plan,
   then start on P0 without waiting for confirmation.
2. **Environment prep.** Start/restart the dev server, seed test data, log in
   with a test account — anything needed to make the feature reachable. Prep is
   exempt from black-box rules, but: never pre-trigger the behavior under test;
   when prep is done, announce it and stop touching the environment; record
   every prep action for the report.
3. **Act → Observe.** One state-changing action per observation cycle. After
   each action, cross-validate: a read-only DOM/state check **and** a
   screenshot you actually look at. Neither replaces the other. Never
   conclude pass/fail without a viewed screenshot.
   - Locate targets from observed facts (DOM snapshot, visible text, screenshot
     coordinates for canvas) — never guess selectors.
   - No JavaScript injection with side effects on the page under test
     (no dispatching events, no mutating DOM/storage). Read-only evaluation is
     allowed as a last resort; in the canvas profile a read-only debug hook
     (see [canvas](#profile-canvas)) is explicitly allowed.
   - A failed action is a finding, not something to bypass. Record it and move on.
4. **Report.** See [Report Format](#report-format).

## Profiles

### Profile: desktop

Default browser viewport (no emulation). Mouse + keyboard interactions.
Use this profile for any web page; the other two profiles extend it.

### Profile: mobile

Simulate a phone/tablet before interacting. With the bundled toolbox, use a
device preset from `lib.mjs` (`iphone-14`, `iphone-se`, `pixel-7`, `ipad`) —
each sets viewport, deviceScaleFactor, `isMobile`, `hasTouch`, and a matching
user agent. Test portrait **and** landscape (`landscape: true` in
`createSession`). Desktop browsers cannot verify touch behavior — do not
report mobile results from a desktop viewport.

Gestures (bundled toolbox): `tap(x, y)`, `swipe({fromX, fromY, toX, toY})`,
`longPress(x, y, ms)`.

**Touch vs pointer events — verify before trusting clicks.** If taps appear to
do nothing, check what the page listens for:

- Pointer events (`pointerdown`/`pointerup`) respond to mouse emulation —
  everything just works.
- Native touch handlers (`touchstart`/`touchmove`) need `hasTouch` contexts.
  The toolbox's `tap()` uses `page.touchscreen.tap()` in touch contexts;
  `swipe()` dispatches real touch sequences via CDP (Chromium).
- Verification recipe: read-only evaluate
  `getEventListeners` is unavailable in page context — instead, temporarily
  test one known touch-driven control: tap it, screenshot, compare. If an
  element reacts to mouse but not the toolbox tap, note it as a finding
  (the app likely breaks on real devices in the same way) and tell the user.

### Profile: canvas

Canvas/WebGL apps (games, visualizations) are invisible to DOM snapshots —
there is nothing to locate. Adapt as follows:

- **Interact by coordinates** on the canvas element's bounding box (read-only
  geometry read), or by visible DOM HUD controls around the canvas.
- **Verify by screenshots.** Compare before/after pairs per action; for
  animation, capture two frames and confirm they differ.
- **Read-only debug hook**: if the app exposes one in dev mode (e.g.
  `window.__game`), read it for state assertions (score, phase, entity
  counts). Reads must be side-effect free — e.g.
  `page.evaluate(() => JSON.parse(JSON.stringify(window.__game)))`. If it is
  not exposed, rely on screenshots and *recommend* adding a hook (next
  section); do not inject one.
- **Transient states** (toasts, hit effects, countdowns): capture
  before-action and after-action screenshots **in the same script run**, as
  close together as possible. Do not rely on re-running to reproduce.

## Bundled Toolbox (fallback path)

Self-contained Playwright helpers shipped with this skill. Requires Node ≥ 18
and Chromium (installed by `setup.sh`).

**Setup — run once, from the project under test's root:**

```bash
bash "$SKILL_DIR/scripts/setup.sh" .
```

`$SKILL_DIR` is the directory containing this SKILL.md. `setup.sh` installs
`playwright` as a devDependency of the project under test and downloads
Chromium. It is idempotent. (Windows agents: run the two commands it contains
instead — `npm i -D playwright` and `npx playwright install chromium`.)

**API (`$SKILL_DIR/scripts/lib.mjs`):**

| Export | Purpose |
|--------|---------|
| `DEVICES` | Device preset table (`desktop`, `iphone-14`, `iphone-se`, `pixel-7`, `ipad`) |
| `lookupDevice(name)` | Preset lookup; throws with valid names on unknown input |
| `createSession(url, opts)` | Launch headless Chromium + context with preset; opts: `device`, `landscape`, `video`, `evidenceDir`, `headless`, `gotoTimeoutMs`. Auto-collects console + page errors. **Loads `playwright` from the current working directory** — always run node from the project under test's root |
| `tap(session, x, y)` | Touchscreen tap in touch contexts, mouse click otherwise |
| `swipe(session, {fromX, fromY, toX, toY, steps?, durationMs?})` | Real touch-sequence drag (CDP) in touch contexts, interpolated mouse drag otherwise |
| `longPress(session, x, y, ms?)` | Touch press-and-hold, mouse fallback |
| `saveShot(session, name)` | PNG screenshot into the session's evidence dir; returns the path |
| `closeSession(session)` | Closes cleanly; returns `{ consoleLog, pageErrors, videos }` |

**One-shot script pattern** — write a small script per test point into the
project under test (e.g. `web-tester-scratch/`, gitignored), run it with node,
then read the screenshots it produced. See `$SKILL_DIR/examples/`:
`example-mobile-tap.mjs`, `example-canvas-swipe.mjs`.

```js
import { createSession, tap, saveShot, closeSession } from "$SKILL_DIR/scripts/lib.mjs";

const session = await createSession("http://localhost:5173", { device: "iphone-14" });
await saveShot(session, "01-initial");
await tap(session, 195, 420);
await session.page.waitForTimeout(500);
await saveShot(session, "02-after-tap");
const { consoleLog, pageErrors } = await closeSession(session);
console.log(JSON.stringify({ consoleLog, pageErrors }, null, 2));
```

**Evidence convention.** All artifacts (screenshots, videos, captured logs)
land under `web-tester-evidence/<run-name>/` in the project under test. Name
screenshots by test point: `t1-initial.png`, `t1-after-tap.png`. Reference
these paths in the report.

**Video.** Pass `video: true` to `createSession` when a sequence of
interactions must be reviewed as a whole (gameplay, gesture trails). The
`.webm` path is returned by `closeSession`.

## Recommendations for the Project Under Test

Give the user these when the project makes testing harder than it should be:

1. **Prefer pointer events** (`pointerdown`/`pointermove`/`pointerup`) over
   native touch events — one code path works for mouse, touch, and pen.
2. **Expose a dev-only debug hook** (e.g. `window.__game` in development
   builds) with read-only state: score, phase, key entities. A few lines of
   code, and it turns canvas assertions from screenshot-guessing into checks.
3. Make randomness seedable so a failing interaction can be replayed.

## Report Format

Interleaved Markdown: per test point — action taken, expected vs observed,
verdict (pass/fail/blocked), and the screenshot path(s) that prove it. End
with: console/page errors collected (with the step each occurred at), any
environment prep performed, and any test point skipped as unsupported by the
tooling. Every verdict needs a viewed screenshot behind it — a test point
without evidence is reported as unverified, never as passed.

## Rules & Boundaries

- **Black-box**: test what a user can reach through the GUI. Side-effect-free
  reads (DOM, geometry, dev debug hook) are the only code-level observations.
- **Separate testing from fixing**: finish the test pass first, report, then
  fix if asked.
- **Faithful reporting**: never fake a success, never skip collecting evidence
  for a failure, never report an unviewed screenshot as verified.
- **Do not commit** the `web-tester-scratch/` or `web-tester-evidence/`
  directories; suggest gitignoring them.
