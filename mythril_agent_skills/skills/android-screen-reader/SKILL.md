---
name: android-screen-reader
description: |
  Read the current screen of a connected Android device via adb. Use when the
  user asks to inspect or summarize what is visible on a phone/tablet screen,
  extract UI text or controls, debug Android app state, or mentions adb,
  screencap, uiautomator, current screen, or connected Android devices. When
  multiple devices are connected, list them with model info and let the user
  choose. Prefer the UI hierarchy for exact text and element metadata; fall
  back to a screenshot when the hierarchy is empty or the screen is visual-only.
  Delete all temporary screenshots and XML dumps immediately after analysis.
license: Apache-2.0
---

# Android Screen Reader

Read the current screen of a connected Android device and report what is visible
accurately and concisely.

## Step 1 — Pre-flight

Verify `adb` is available:

```bash
adb version
```

If missing, tell the user to install Android Platform Tools:
- macOS: `brew install android-platform-tools`
- Linux: package manager or https://developer.android.com/studio/releases/platform-tools
- Windows: download from the link above and add to `PATH`

## Step 2 — Device discovery and selection

List all connected devices with full details:

```bash
adb devices -l
```

Parse the output — only lines where the second field is `device` are usable.
Other status values:

| Status | Meaning |
|---|---|
| `device` | Ready |
| `unauthorized` | USB debugging prompt not confirmed on the phone |
| `offline` | Device not responding |

**0 usable devices** → Stop. Tell the user to connect a device with USB debugging
enabled (Settings → Developer options → USB debugging).

**1 usable device** → Proceed automatically. Record its serial number.

**Multiple usable devices** → Present a numbered list using the `serial` and
`model:` fields from the `-l` output, then use the `ask_user` tool (or ask inline
if that tool is unavailable) to let the user pick one. For example:

```
Connected devices — which one should I read?
  1. R3CT704XXXX  — SM-S911B
  2. emulator-5554 — sdk_gphone_x86_arm
```

Store the chosen serial as `SERIAL`. Every subsequent `adb` call must include
`-s "$SERIAL"` so the command targets the right device.

## Step 3 — Create a temporary run directory

All captured files go here. Nothing is written outside this directory.

### Bash (macOS / Linux)

```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
  CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
fi
CACHE_DIR="$CACHE_ROOT/android-screen-reader"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
```

### PowerShell (Windows)

```powershell
$CACHE_ROOT = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "mythril-skills-cache"
$CACHE_DIR = Join-Path $CACHE_ROOT "android-screen-reader"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
$RUN_DIR = Join-Path $CACHE_DIR ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $RUN_DIR | Out-Null
```

## Step 4 — Read the screen

### Primary path: UI hierarchy

The hierarchy gives exact text, content descriptions, resource IDs, and element
roles — all without rendering an image. Try this first.

```bash
# Write to /sdcard/ on the device, pull, then delete from device
adb -s "$SERIAL" shell uiautomator dump /sdcard/window_dump.xml
adb -s "$SERIAL" pull /sdcard/window_dump.xml "$RUN_DIR/window_dump.xml"
adb -s "$SERIAL" shell rm -f /sdcard/window_dump.xml
```

Parse `window_dump.xml` for:
- `text` — the visible label or value
- `content-desc` — accessibility description (often richer than `text`)
- `class` — element type (e.g. `android.widget.Button`)
- `resource-id` — stable identifier for the element

**The hierarchy alone is enough** when the screen is standard Android UI (text,
buttons, lists, dialogs, menus).

**Take a screenshot too** when:
- The dump is empty (`<hierarchy rotation="0" />` with no children)
- The screen is a game, camera, map, drawing canvas, or media player
- Key visible text is absent from the hierarchy (custom views, WebView, etc.)

### Fallback / supplement: Screenshot

**Bash:**
```bash
adb -s "$SERIAL" exec-out screencap -p > "$RUN_DIR/screen.png"
```

**PowerShell** (the Bash redirect does not work for binary output on Windows):
```powershell
$bytes = adb -s $SERIAL exec-out screencap -p
[System.IO.File]::WriteAllBytes("$RUN_DIR\screen.png", $bytes)
```

Load `screen.png` as an image and read it visually. Combine with hierarchy data
when both were captured — hierarchy for exact strings, screenshot for visual
context the XML misses.

## Step 5 — Cleanup

Delete all temporary files as soon as you have finished the analysis. These are
skill-managed ephemeral artifacts — delete them automatically without asking.

**Bash:**
```bash
rm -f "$RUN_DIR/screen.png" "$RUN_DIR/window_dump.xml"
rmdir "$RUN_DIR" 2>/dev/null || true
```

**PowerShell:**
```powershell
Remove-Item -Force "$RUN_DIR\screen.png" -ErrorAction SilentlyContinue
Remove-Item -Force "$RUN_DIR\window_dump.xml" -ErrorAction SilentlyContinue
Remove-Item -Force "$RUN_DIR" -ErrorAction SilentlyContinue
```

## Output format

Report what is visible with this structure:

1. **Active app / screen** — which app and which screen or activity
2. **Visible text** — quote exact strings where they matter
3. **Controls and interactive elements** — buttons, inputs, menus, dialogs
4. **Unusual state** — errors, warnings, loading spinners, permission dialogs
5. **Most likely next action** — what the user probably intends to do next

When multiple devices were connected, open with which device was read (serial and
model). Keep the report concise — the user wants to understand the screen at a
glance, not read a transcript of the XML.
