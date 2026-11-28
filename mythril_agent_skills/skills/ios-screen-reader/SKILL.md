---
name: ios-screen-reader
description: >
  Reads the current screen of a connected iPhone/iPad (USB or Wi-Fi paired) or a
  booted iOS Simulator on macOS, using Xcode's devicectl/simctl to take a
  screenshot and, for simulators, the AXe accessibility tree for exact text and
  controls when installed. Use when the user wants to know what is on an iOS
  device or simulator screen, extract UI text, or debug iOS app state, or
  mentions iPhone, iPad, iOS simulator, devicectl, simctl, or "看一下我 iPhone 屏幕".
license: Apache-2.0
---

# iOS Screen Reader

Read the current screen of a connected iOS device or a booted iOS Simulator and
report what is visible accurately and concisely.

| Target | Screenshot | Exact text / controls |
|---|---|---|
| Physical device | `xcrun devicectl` (bundled script) | Not available — read the screenshot |
| Simulator | `xcrun simctl` (bundled script) | `axe describe-ui` if AXe is installed |

macOS only — Xcode is required. If the host is Linux or Windows, stop and say so.

## Step 1 — Pre-flight

```bash
xcrun devicectl --version && xcrun simctl help >/dev/null && echo OK
```

If `xcrun` or `devicectl` is missing, tell the user to install Xcode 15 or later
(and run `xcode-select --install`). Do NOT try libimobiledevice
(`idevicescreenshot`): it cannot screenshot iOS 17+ devices and does not see
devices paired only over Wi-Fi.

Optional, simulators only — check for AXe:

```bash
command -v axe
```

If missing, continue with screenshots only. Mention once, in the final report,
that `brew install cameroncooke/axe/axe` enables exact text extraction on
simulators. Never install it without the user's consent.

## Step 2 — Device discovery and selection

```bash
python3 SKILL_PATH/scripts/ios_devices.py list
```

The script lists paired physical devices (probing them in parallel, ~1–20 s in
total) followed by booted simulators:

```
1. [physical] My iPhone — iPhone 11 (27.2.1) state=ready udid=00008030-...
2. [physical] My iPad — iPad (9th generation) (26.6.2) state=unreachable udid=...
3. [simulator] iPhone 17 — iPhone 17 (iOS 26.5) state=ready udid=4FA3...
```

| State | Meaning |
|---|---|
| `ready` | Reachable, unlocked — usable |
| `locked` | Reachable but locked — usable, but the screenshot shows the lock screen; ask the user to unlock first |
| `unreachable` | Paired before but not reachable now (off, asleep, different network, unplugged) |

Usable = `ready` or `locked`.

**0 usable** → Stop. Tell the user to either connect and unlock an iPhone/iPad
that is paired with this Mac (Xcode → Window → Devices and Simulators; Developer
Mode must be on), or boot a simulator (`open -a Simulator`, or
`xcrun simctl boot "<name>"`).

**1 usable** → Proceed automatically.

**Multiple usable** → Present the numbered list and use the `ask_user` tool (or
ask inline if unavailable) to let the user pick. If the user's request already
names one ("the simulator", "my iPhone 11"), pick it without asking.

Record `UDID` and `KIND` (`physical` or `simulator`) from the chosen row.

## Step 3 — Create a temporary run directory

```bash
CACHE_DIR="$HOME/Library/Caches/mythril-skills-cache/ios-screen-reader"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
```

## Step 4 — Read the screen

### Simulator with AXe: accessibility tree first

```bash
axe describe-ui --udid "$UDID" > "$RUN_DIR/ui.json"
```

The JSON is a tree of elements. Use each element's label (`AXLabel`), value
(`AXValue`), type/role, and frame. This gives exact strings — prefer it over
reading text off the image.

**The tree alone is enough** for standard UIKit/SwiftUI screens (text, buttons,
lists, alerts). **Take a screenshot too** when the tree is empty or nearly
empty, the screen is a game, camera, map, canvas, video or WebView, or text you
expect is missing from the tree.

### Physical device, or simulator without AXe: screenshot

```bash
python3 SKILL_PATH/scripts/ios_devices.py screenshot \
  --udid "$UDID" --kind "$KIND" --out "$RUN_DIR/screen.png"
```

On success it prints the PNG path. Load that PNG as an image and read it
visually. Images are full device resolution (e.g. 828x1792); that is fine to
read directly.

If the screenshot fails on a physical device: ask the user to unlock and wake
the device, keep it on the same network (or plug in USB), then retry once. Do
not try other tools.

Combine both sources when both were captured — tree for exact strings,
screenshot for visual context.

## Step 5 — Cleanup

Delete temporary files as soon as the analysis is done. They are skill-managed
ephemeral artifacts — delete them automatically without asking.

```bash
rm -f "$RUN_DIR/screen.png" "$RUN_DIR/ui.json"
rmdir "$RUN_DIR" 2>/dev/null || true
```

Do not shut down a simulator you did not boot.

## Output format

1. **Device** — which device was read (name, physical/simulator, iOS version) when more than one was available
2. **Active app / screen** — which app and which screen (home screen, settings page, etc.)
3. **Visible text** — quote exact strings where they matter
4. **Controls and interactive elements** — buttons, inputs, tabs, alerts, sheets
5. **Unusual state** — errors, permission alerts, loading spinners, lock screen
6. **Most likely next action** — what the user probably intends to do next

When the text came only from the screenshot (physical device, or no AXe), treat
small or low-contrast strings as best-effort and say so if one matters. Keep the
report concise.
