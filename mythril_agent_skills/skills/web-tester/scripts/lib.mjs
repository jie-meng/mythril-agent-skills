// web-tester skill — bundled Playwright toolbox (fallback capability level).
//
// Design notes:
// - `playwright` is loaded LAZILY via createRequire anchored at the current
//   working directory, so this module imports cleanly on machines without
//   playwright (pure functions stay unit-testable) and so one-shot test
//   scripts resolve the copy installed in the PROJECT UNDER TEST. Always run
//   node from the project under test's root.
// - Pure helpers (device presets, naming) never touch playwright or the
//   filesystem, and are tested by lib.test.mjs (node --test).
//
// Skill rules live in SKILL.md: black-box only, every verdict needs a viewed
// screenshot, one state-changing action per observation cycle.

import { mkdirSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";

/** Device presets. `hasTouch` + real UA matter: touch emulation without a
 * touch UA misreports mobile behavior. */
export const DEVICES = {
  desktop: {
    label: "Desktop 1280x800",
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 1,
    isMobile: false,
    hasTouch: false,
    userAgent: null,
  },
  "iphone-14": {
    label: "iPhone 14",
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    isMobile: true,
    hasTouch: true,
    userAgent:
      "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
  },
  "iphone-se": {
    label: "iPhone SE (3rd gen)",
    viewport: { width: 375, height: 667 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    userAgent:
      "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
  },
  "pixel-7": {
    label: "Pixel 7",
    viewport: { width: 412, height: 915 },
    deviceScaleFactor: 2.625,
    isMobile: true,
    hasTouch: true,
    userAgent:
      "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
  },
  ipad: {
    label: "iPad (9th gen)",
    viewport: { width: 810, height: 1080 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    userAgent:
      "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
  },
};

/** Resolve a device preset by name. Empty/undefined → desktop. Unknown names
 * throw (a silent desktop fallback would make touch tests lie). */
export function lookupDevice(name) {
  if (name === undefined || name === null || String(name).trim() === "") {
    return DEVICES.desktop;
  }
  const key = String(name).trim().toLowerCase();
  const device = DEVICES[key];
  if (!device) {
    throw new Error(
      `Unknown device '${name}'. Valid devices: ${Object.keys(DEVICES).join(", ")}`,
    );
  }
  return device;
}

/** Evidence/run directory name: `<prefix>-YYYYMMDD-HHMMSS` (local time).
 * `now` is injectable for tests. */
export function evidenceDirName(prefix = "web-tester", now = new Date()) {
  const p = String(prefix || "web-tester").trim() || "web-tester";
  const pad = (n, w = 2) => String(n).padStart(w, "0");
  const stamp =
    pad(now.getFullYear(), 4) +
    pad(now.getMonth() + 1) +
    pad(now.getDate()) +
    "-" +
    pad(now.getHours()) +
    pad(now.getMinutes()) +
    pad(now.getSeconds());
  return `${p}-${stamp}`;
}

/** Sanitize a screenshot base name to [A-Za-z0-9._-] so it is portable and
 * shell-safe. */
export function sanitizeShotName(name) {
  const cleaned = String(name ?? "shot")
    .trim()
    .replace(/[^A-Za-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return cleaned || "shot";
}

function loadPlaywright() {
  try {
    // Anchor at cwd so the playwright copy installed in the project under
    // test is the one that loads, regardless of where this skill lives.
    const require = createRequire(join(process.cwd(), "package.json"));
    return require("playwright");
  } catch (err) {
    throw new Error(
      "playwright is not resolvable from the current directory. Run `bash " +
        "$SKILL_DIR/scripts/setup.sh .` from the project under test's root " +
        "(see SKILL.md — Bundled Toolbox), then re-run node from that root.",
      { cause: err },
    );
  }
}

/** Launch headless Chromium with a device preset and open `url`.
 *
 * opts: device (preset name, default "desktop"), landscape (swap viewport
 * w/h), video (record .webm into the evidence dir), evidenceDir (default
 * `evidenceDirName()` in cwd), headless (default true), gotoTimeoutMs.
 *
 * Returns a session: { browser, context, page, deviceName, device,
 * evidenceDir, consoleLog, pageErrors }. consoleLog/pageErrors fill as the
 * page runs — read them via closeSession() or directly at any time.
 */
export async function createSession(url, opts = {}) {
  const { chromium } = loadPlaywright();
  const deviceName = opts.device ?? "desktop";
  const device = lookupDevice(deviceName);

  let viewport = { ...device.viewport };
  if (opts.landscape) {
    viewport = { width: viewport.height, height: viewport.width };
  }

  const evidenceDir = opts.evidenceDir ?? evidenceDirName();
  mkdirSync(evidenceDir, { recursive: true });

  const browser = await chromium.launch({ headless: opts.headless ?? true });
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: device.deviceScaleFactor,
    isMobile: device.isMobile,
    hasTouch: device.hasTouch,
    ...(device.userAgent ? { userAgent: device.userAgent } : {}),
    ...(opts.video
      ? { recordVideo: { dir: evidenceDir, size: viewport } }
      : {}),
  });
  const page = await context.newPage();

  const consoleLog = [];
  const pageErrors = [];
  page.on("console", (msg) => {
    consoleLog.push({ type: msg.type(), text: msg.text() });
  });
  page.on("pageerror", (err) => {
    pageErrors.push({
      text: String(err?.message ?? err),
      stack: err?.stack ?? null,
    });
  });

  await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: opts.gotoTimeoutMs ?? 15000,
  });

  return {
    browser,
    context,
    page,
    deviceName: String(deviceName).trim().toLowerCase(),
    device: { ...device, viewport },
    evidenceDir,
    consoleLog,
    pageErrors,
  };
}

/** Tap at viewport coordinates. Touch contexts use touchscreen.tap (real
 * touchstart/touchend); desktop falls back to a mouse click. */
export async function tap(session, x, y) {
  if (session.device.hasTouch) {
    await session.page.touchscreen.tap(x, y);
  } else {
    await session.page.mouse.click(x, y);
  }
}

/** Drag from (fromX, fromY) to (toX, toY). Touch contexts dispatch a real
 * touch sequence via CDP (Chromium) — pointer events and touch handlers both
 * fire. Elsewhere, an interpolated mouse drag. */
export async function swipe(
  session,
  { fromX, fromY, toX, toY, steps = 12, durationMs = 400 },
) {
  const n = Math.max(2, Math.floor(steps));
  const delay = Math.max(0, Math.floor(durationMs / n));

  if (session.device.hasTouch) {
    const cdp = await session.context.newCDPSession(session.page);
    const point = (x, y) => [{ x: Math.round(x), y: Math.round(y) }];
    await cdp.send("Input.dispatchTouchEvent", {
      type: "touchStart",
      touchPoints: point(fromX, fromY),
    });
    for (let i = 1; i <= n; i++) {
      const x = fromX + ((toX - fromX) * i) / n;
      const y = fromY + ((toY - fromY) * i) / n;
      await cdp.send("Input.dispatchTouchEvent", {
        type: "touchMove",
        touchPoints: point(x, y),
      });
      if (delay > 0) await sleep(delay);
    }
    await cdp.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    await cdp.detach();
    return;
  }

  await session.page.mouse.move(fromX, fromY);
  await session.page.mouse.down();
  for (let i = 1; i <= n; i++) {
    await session.page.mouse.move(
      fromX + ((toX - fromX) * i) / n,
      fromY + ((toY - fromY) * i) / n,
    );
    if (delay > 0) await sleep(delay);
  }
  await session.page.mouse.up();
}

/** Press and hold at (x, y) for `ms` (default 600). */
export async function longPress(session, x, y, ms = 600) {
  const { page } = session;
  if (session.device.hasTouch) {
    const cdp = await session.context.newCDPSession(page);
    await cdp.send("Input.dispatchTouchEvent", {
      type: "touchStart",
      touchPoints: [{ x: Math.round(x), y: Math.round(y) }],
    });
    await sleep(ms);
    await cdp.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    await cdp.detach();
    return;
  }
  await page.mouse.move(x, y);
  await page.mouse.down();
  await sleep(ms);
  await page.mouse.up();
}

/** Save a PNG screenshot into the session's evidence dir. `name` is
 * sanitized; returns the absolute path written. */
export async function saveShot(session, name) {
  const file = `${sanitizeShotName(name)}.png`;
  const path = join(session.evidenceDir, file);
  await session.page.screenshot({ path });
  return path;
}

/** Close cleanly. Video files are flushed on context close. Returns
 * { consoleLog, pageErrors, videos } for the final report. */
export async function closeSession(session) {
  await session.context.close();
  await session.browser.close();

  let videos = [];
  try {
    videos = readdirSync(session.evidenceDir)
      .filter((f) => f.endsWith(".webm"))
      .map((f) => join(session.evidenceDir, f));
  } catch {
    // evidence dir unreadable — report empty rather than crash the wrap-up
  }
  return {
    consoleLog: session.consoleLog,
    pageErrors: session.pageErrors,
    videos,
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
