// Pure-function tests for web-tester's lib.mjs. Run: node --test lib.test.mjs
// (from any directory — playwright is NOT needed; createSession etc. load it
// lazily and are integration-tested, not unit-tested).

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  DEVICES,
  lookupDevice,
  evidenceDirName,
  sanitizeShotName,
} from "./lib.mjs";

test("lookupDevice returns the requested preset", () => {
  assert.equal(lookupDevice("iphone-14").label, "iPhone 14");
  assert.equal(lookupDevice("pixel-7").hasTouch, true);
  assert.equal(lookupDevice("ipad").viewport.width, 810);
});

test("lookupDevice is case/whitespace tolerant", () => {
  assert.equal(lookupDevice("  IPhone-14 ").label, "iPhone 14");
  assert.equal(lookupDevice("DESKTOP").hasTouch, false);
});

test("lookupDevice defaults to desktop on empty input", () => {
  for (const empty of [undefined, null, "", "   "]) {
    assert.equal(lookupDevice(empty).label, "Desktop 1280x800");
  }
});

test("lookupDevice throws on unknown names, listing valid ones", () => {
  assert.throws(() => lookupDevice("ipone-14"), (err) => {
    assert.match(err.message, /ipone-14/);
    assert.match(err.message, /iphone-14/);
    return true;
  });
});

test("device presets are self-consistent", () => {
  for (const [name, d] of Object.entries(DEVICES)) {
    assert.ok(d.viewport.width > 0 && d.viewport.height > 0, name);
    assert.ok(d.deviceScaleFactor > 0, name);
    assert.equal(typeof d.hasTouch, "boolean", name);
    if (d.hasTouch) {
      assert.ok(d.userAgent, `${name} needs a mobile UA`);
      assert.equal(d.isMobile, true, name);
    }
  }
  assert.equal(DEVICES.desktop.hasTouch, false);
});

test("evidenceDirName stamps YYYYMMDD-HHMMSS with prefix", () => {
  const d = new Date(2026, 10, 7, 15, 3, 9); // 2026-11-07 15:03:09 local
  assert.equal(evidenceDirName("t1", d), "t1-20261107-150309");
  assert.equal(evidenceDirName("web-tester", d), "web-tester-20261107-150309");
});

test("evidenceDirName falls back to web-tester prefix", () => {
  const d = new Date(2026, 0, 2, 3, 4, 5);
  assert.equal(evidenceDirName(undefined, d), "web-tester-20260102-030405");
  assert.equal(evidenceDirName("  ", d), "web-tester-20260102-030405");
});

test("sanitizeShotName keeps safe characters, replaces the rest", () => {
  assert.equal(sanitizeShotName("t1-after-tap"), "t1-after-tap");
  assert.equal(sanitizeShotName("t1 (after) tap!"), "t1-after-tap");
  assert.equal(sanitizeShotName("../evil name"), "..-evil-name");
});

test("sanitizeShotName never returns empty", () => {
  assert.equal(sanitizeShotName(""), "shot");
  assert.equal(sanitizeShotName("///"), "shot");
  assert.equal(sanitizeShotName(undefined), "shot");
});
