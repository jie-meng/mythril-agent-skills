// web-tester example — mobile profile: open a page, tap, capture evidence.
//
// Usage (run from the project under test's root, after setup.sh):
//   node "$SKILL_DIR/examples/example-mobile-tap.mjs" <url> [device] [tapX] [tapY]
//
// Adapt me: per SKILL.md, write your own one-shot script per test point —
// this file shows the shape, not a universal test.

import { createSession, tap, saveShot, closeSession } from "../scripts/lib.mjs";

const url = process.argv[2] ?? "http://localhost:5173";
const device = process.argv[3] ?? "iphone-14";
const tapX = Number(process.argv[4] ?? 195); // default: horizontal center of
const tapY = Number(process.argv[5] ?? 420); // an iPhone 14 portrait viewport

const session = await createSession(url, { device });

await saveShot(session, "01-initial");

await tap(session, tapX, tapY);
// Let UI settle / animation play before the evidence screenshot. Prefer
// waiting for a concrete element/state when one exists.
await session.page.waitForTimeout(500);

await saveShot(session, "02-after-tap");

const { consoleLog, pageErrors, videos } = await closeSession(session);

console.log(`device:        ${device}`);
console.log(`evidence dir:  ${session.evidenceDir}`);
if (videos.length) console.log(`videos:        ${videos.join(", ")}`);
console.log(`console log:   ${JSON.stringify(consoleLog, null, 2)}`);
console.log(`page errors:   ${JSON.stringify(pageErrors, null, 2)}`);
console.log("Next: view 01-initial.png and 02-after-tap.png, then verdict.");
