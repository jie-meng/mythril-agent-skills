---
name: figma
description: >
  Fetches Figma design specs (layout, colors, typography, components) and
  exports nodes as images through the Figma REST API. Use when a message contains
  a figma.com link, or the user asks to implement, inspect, or code a design, or
  asks about colors, spacing, or fonts in a design — e.g. "implement this
  design", "according to Figma", "照着设计稿实现", "看下 figma".
license: Apache-2.0
---

# When to Use This Skill

- A message contains a `figma.com` URL (design, file, proto)
- User asks about colors, spacing, fonts, or dimensions from a design
- User wants to implement, match, or code a component from a design
- User says "according to Figma", "from the design", "in the mockup"

# Prerequisites

Requires `FIGMA_ACCESS_TOKEN` environment variable. See `README.md` in this skill directory for setup instructions.

## Security — MANDATORY rules for AI agents

1. **NEVER echo, print, or log** the value of `FIGMA_ACCESS_TOKEN` or any other environment variable. Do NOT run commands like `echo $FIGMA_ACCESS_TOKEN` or `printenv FIGMA_ACCESS_TOKEN` — even for debugging.
2. **NEVER pass token values as inline CLI arguments or env-var overrides** (e.g. `FIGMA_ACCESS_TOKEN=xxx python3 ...`). The scripts read the token from the environment automatically — just run the script directly.
3. **When debugging auth errors**, rely solely on the script's error output (401, 403, 429 messages). Do NOT attempt to verify tokens by reading or printing them.
4. **Do NOT read environment variable values** using shell commands or programmatic access. The scripts handle all credential access internally.
5. **NEVER extract credentials from OS credential stores or config files.** Strictly forbidden commands include:
   - `security find-internet-password`, `security find-generic-password` (macOS Keychain)
   - `git credential fill`, `cat ~/.git-credentials`, `cat ~/.netrc`
   - Any command that outputs a password, token, or secret value from any credential store
6. **NEVER use extracted credential values in commands.** Do NOT manually construct authenticated requests using raw credential values. The bundled script handles all authentication internally.
7. **Use only the documented CLI subcommands.** Do NOT `import` the bundled script or call its internal functions (`get_token()`, `*_request()`, etc.) via `python3 -c` or ad-hoc code — that bypasses the CLI's argument handling, and a misordered argument can put the credential into a URL or error message. If a needed subcommand or output field is missing, tell the user instead of scripting around it — and **never edit the installed skill files** (`SKILL_PATH/scripts/*`) to add it; a local patch silently diverges from the published skill and is overwritten on the next install. Script output redacts credentials as `[REDACTED]`; if a credential value ever appears in any output anyway, do NOT repeat it — tell the user to rotate it.

# Workflow

1. Extract the Figma URL(s) from the user's message
2. Run `figma_fetch.py` to get structured design specs
3. If fetch succeeds → read the markdown output, use the specs to generate accurate code
4. If fetch fails with 429 → **fall back to image export** (see "Fallback" below)

## Quota rules — read before calling

Node specs (`/files/:key/nodes`) and image export (`/images/:key`) are **Tier 1** endpoints. View/Collab seats get **6 Tier 1 calls per month**; Dev/Full seats get 10–20 per minute. Every call counts, no matter how many nodes it covers. So:

- **Several nodes from the same file → ONE command.** Pass all URLs (or `--ids`) to a single `figma_fetch.py` / `figma_export.py` run. **Never loop over nodes in the shell** — a loop of 6 exports spends 6 calls, a single batched export spends 1.
- **Nodes from different files → one command per file.** The scripts refuse mixed files.
- A URL **without** node-id costs nothing from Tier 1: the overview comes from the Tier 3 metadata endpoint. Add `--pages` only when you need the page/component list (one Tier 1 call).

## Passing URLs and node ids

- Quote every URL and pass **nothing but the URL** in that argument. Never glue a label or filename onto it (`"...node-id=1-2 shelf"`) — the scripts reject it with exit code 2. Use `--names` to name output files.
- Supported links: `figma.com/{design,file,proto,board,slides,make}/<key>/...`. Branch links (`/design/<main>/branch/<branch>/...`) are resolved to the branch key automatically.
- `--ids` takes comma-separated ids in either form: `1-2,3:4,I5:6;7:8`.

## Running the Scripts

Both scripts live in this skill's `scripts/` directory and use only the Python standard library (3.10+); `SKILL_PATH` below is this skill's installed directory. Exit codes: 0 = success, 1 = API error (or some nodes missing), 2 = bad arguments. On error, surface the printed message to the user.

### Fetch design specs (figma_fetch.py) — primary

```bash
# One node (most common — URL contains node-id)
python3 SKILL_PATH/scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2"

# Several nodes from the same file — ONE API call
python3 SKILL_PATH/scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2" \
  "https://www.figma.com/design/ABC123/Name?node-id=3-4" --ids 5-6

# File overview (no node-id): metadata only, Tier 3
python3 SKILL_PATH/scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name"

# File overview with pages and components (one Tier 1 call)
python3 SKILL_PATH/scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name" --pages

# Big page/section: just the layer tree (type, name, id, size) — one Tier 1 call
python3 SKILL_PATH/scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2" --outline --depth 2

# Also resolve design-token names (+1 Tier 2 call; Enterprise plan only)
python3 SKILL_PATH/scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2" --variables
```

| Flag | Default | Description |
|---|---|---|
| `--ids` | — | Extra comma-separated node ids from the same file |
| `--depth N` | `5` | Max recursion depth into child nodes. Use `2`–`3` for large frames to avoid truncation. |
| `--version V` | latest | Read a specific file version id |
| `--outline` | off | Print only the layer tree (type, name, id, size). Use it first on pages, sections, or frames too big for a full spec, then fetch the children you need by id |
| `--variables` | off | Resolve bound design tokens to names via `/variables/local` (one extra **Tier 2** call). Needs an Enterprise plan + `file_variables:read` scope; otherwise prints a NOTE and falls back to listing the bound fields |
| `--pages` | off | Overview mode: also list pages and components (Tier 1) |

Multiple nodes are printed as separate spec sections divided by `---`.

### Export nodes as images (figma_export.py) — secondary / fallback

Downloads rendered images of one or more nodes (same file, one API call) and prints each saved path, one per line. Use as a **fallback** when `figma_fetch.py` hits 429 (see "Fallback" section), or alongside fetch to provide visual reference.

**Bash (macOS / Linux):**
```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
  CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
fi
CACHE_DIR="$CACHE_ROOT/figma"
mkdir -p "$CACHE_DIR"

# One node
python3 SKILL_PATH/scripts/figma_export.py "https://www.figma.com/design/ABC123/Name?node-id=1-2" \
  --format png --scale 2 --output "$CACHE_DIR/node_1-2.png"

# Several nodes — ONE API call, named files
python3 SKILL_PATH/scripts/figma_export.py "https://www.figma.com/design/ABC123/Name?node-id=1-2" \
  --ids 3-4,5-6 --out-dir "$CACHE_DIR" --names shelf,list,detail
```

**PowerShell (Windows):**
```powershell
$CACHE_ROOT = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "mythril-skills-cache"
$CACHE_DIR = Join-Path $CACHE_ROOT "figma"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
python3 SKILL_PATH/scripts/figma_export.py "https://www.figma.com/design/ABC123/Name?node-id=1-2" `
  --ids 3-4 --out-dir $CACHE_DIR --names shelf,list
```

**Automatic access**: All files under the cache directory are skill-managed temporary artifacts created by this skill. Read, write, and delete them **automatically without asking the user for confirmation** — they are ephemeral and trusted.

| Flag | Default | Description |
|---|---|---|
| `--ids` | — | Extra comma-separated node ids from the same file |
| `--format` | `png` | `png`, `jpg`, `svg`, or `pdf` |
| `--scale` | `2.0` | Export scale factor 0.01–4 (e.g. `2` for @2x retina) |
| `--output PATH` | — | Destination file — **single node only** |
| `--out-dir DIR` | current dir | Destination directory for one or more nodes. **Always use the cache dir above for temp exports.** |
| `--names a,b,c` | `figma_<node-id>` | File names (no extension), one per node, in the order the nodes were given (URLs first, then `--ids`) |
| `--version V` | latest | Render a specific file version id |
| `--contents-only false` | API default `true` | Also render content overlapping the node |
| `--absolute-bounds` | off | Use the node's full dimensions even if it is cropped |
| `--svg-outline-text false` | API default `true` | SVG only: keep text as `<text>` elements |

If a node fails to render, the other images are still saved; the failure is reported on stderr and the exit code is 1.

#### Original images behind image fills (`--image-fills`)

A photo, avatar, or illustration placed as an image fill shows up in the fetch output as `Fill: image fill (ref: <hex>, scale: FILL)`. Rendering the node gives you a cropped screenshot; to get the **original uploaded file** for the real asset, pass those refs:

```bash
python3 SKILL_PATH/scripts/figma_export.py "https://www.figma.com/design/ABC123/Name" \
  --image-fills 3f2a...c1,9b7e...04 --out-dir "$CACHE_DIR" --names hero,avatar
```

This uses `GET /v1/files/:key/images` (**Tier 2**, so it does not spend Tier 1 quota). The URL only needs to identify the file. The extension (`png`/`jpg`/`gif`/`webp`/`svg`) comes from the downloaded bytes. Cannot be combined with `--ids` or `--output`.

## Handling 429 Rate Limit errors

Both scripts fail immediately on 429 — **no automatic retry**. Do NOT attempt alternative approaches (no browser/playwright, no screenshots, no web-fetching the Figma URL).

### Fallback: fetch 429 → try image export

When `figma_fetch.py` returns 429, attempt `figma_export.py` as a visual fallback (both use Tier 1 endpoints but may have separate quota remaining):

1. Run `figma_export.py` with `--output` pointing to the cache dir (see example above)
2. If export succeeds → load the image for visual analysis and **tell the user explicitly**:
   - "I could not get the structured design data (API quota exceeded), so I exported an image instead."
   - "The image shows the visual appearance, but I do NOT have exact property values (spacing in px, font sizes, colors as hex, border-radius, etc.). These values may be approximate if I infer them from the image."
3. If export also fails with 429 → stop. Report the error to the user:
   - **`limit_type: low`**: Monthly quota exhausted (View/Collab seat = 6 calls/month on Tier 1). Suggest upgrading to a **Dev or Full seat**.
   - **`limit_type: high`**: Per-minute burst limit (Dev/Full seat). Suggest waiting the seconds shown in the error.

### Clean up exported images

Delete each exported file once you have finished analyzing it, even if errors occurred — exports are large and the cache otherwise grows across sessions.

```bash
rm -f "$CACHE_DIR/node_1-2.png"  # delete each specific file you exported
```

If leftovers accumulate from interrupted sessions, the user can run `skills-clean-cache`.

## Using the Output

**figma_fetch.py** outputs structured markdown (one section per node) covering all visual and layout properties present on each node. The exact fields vary by node type — a FRAME with auto-layout produces different output than a TEXT node. Read what's there; don't expect every section to appear on every node.

Every child heading carries its node id — `### [FRAME] Login (id: 3:4)` — and `--pages` lists page ids the same way. To drill into or export children of a page/section/frame (e.g. all screens in a section), collect those ids and pass them in **one** `--ids` call; never guess ids or build URLs by hand.

Typical sections include layout dimensions, fills/strokes, effects, typography (TEXT nodes), component metadata, and design token bindings. Use these values to generate accurate CSS or UI code matching the design. When a section is absent, the node doesn't have that property set.

Names that map the design onto the codebase's design system — **use them instead of hard-coding raw values** when the project has matching tokens or components:

- `- Styles: fill=Brand/Primary, text=Heading/H1` — shared Figma styles (always resolved; no extra call). Look for a same-named color, text style, or CSS variable in the project.
- `- Component: Button/Primary (id: …)` — the main component an instance comes from. Look for the matching component in the codebase before writing a new one.
- `- Variables: fills=Colors/primary/500, itemSpacing=Spacing/4` — design tokens, only with `--variables` on an Enterprise plan. Without it you get `Bound variables (token fields): fills, itemSpacing`: the value is a token, but its name is unknown, so search the project for a token with that value instead of hard-coding it. A `?` means the variable comes from a library file and cannot be resolved from this file.

**figma_export.py** outputs image files. You can analyze the image visually, but you will NOT have structured property data (exact dimensions, colors, font specs, padding, etc.). Always caveat to the user that values inferred from the image are approximate.

## Limits compared with the Figma MCP server

The REST API has no equivalent for these Figma MCP features. If the user needs one of them, say so and suggest the official Figma MCP server; do not try to work around it:

- **Code Connect** mappings (design component → the real component file in the repo)
- Generated reference code (React + Tailwind) for a selection
- Reading the **current selection** in the Figma desktop app without a link
- Variable names on non-Enterprise plans
