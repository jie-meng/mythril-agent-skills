// web-tester example — canvas profile: coordinate swipe on a canvas game,
// before/after screenshots, optional read-only debug-hook state, video.
//
// Usage (run from the project under test's root, after setup.sh):
//   node "$SKILL_DIR/examples/example-canvas-swipe.mjs" <url> [device]
//
// Adapt me: per SKILL.md, write your own one-shot script per test point —
// this file shows the shape, not a universal test.

import { createSession, swipe, saveShot, closeSession } from "../scripts/lib.mjs";

const url = process.argv[2] ?? "http://localhost:5173";
const device = process.argv[3] ?? "iphone-14";

const session = await createSession(url, { device, video: true });
const { width, height } = session.device.viewport;

await saveShot(session, "01-before-swipe");

// Horizontal drag across the middle of the screen — adjust to the game's
// gesture area.
await swipe(session, {
  fromX: Math.round(width * 0.7),
  fromY: Math.round(height * 0.5),
  toX: Math.round(width * 0.3),
  toY: Math.round(height * 0.5),
});

await saveShot(session, "02-after-swipe");

// Read-only debug hook (canvas profile) — allowed by SKILL.md rules because
// it only reads state the dev build exposes; never mutate it here.
const hookState = await session.page.evaluate(() => {
  if (typeof window.__game === "undefined") return null;
  return JSON.parse(
    JSON.stringify(window.__game, (k, v) => (typeof v === "function" ? undefined : v)),
  );
});

const { consoleLog, pageErrors, videos } = await closeSession(session);

console.log(`hook state:   ${hookState ? JSON.stringify(hookState) : "(not exposed)"}`);
console.log(`videos:       ${videos.join(", ") || "(none)"}`);
console.log(`console log:  ${JSON.stringify(consoleLog, null, 2)}`);
console.log(`page errors:  ${JSON.stringify(pageErrors, null, 2)}`);
console.log("Next: view 01/02 PNGs (frames must differ if the swipe moved something).");
