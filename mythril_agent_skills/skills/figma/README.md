# Figma Design Fetcher

Fetch design specs (layout, colors, typography, components) from a Figma URL and output structured markdown for AI-assisted code generation.

**Official Figma REST API spec**: [github.com/figma/rest-api-spec](https://github.com/figma/rest-api-spec) — OpenAPI YAML + TypeScript types  
**Full API reference**: See [`references/API_REFERENCE.md`](./references/API_REFERENCE.md).

## Prerequisites

### 1. Get a Figma Personal Access Token

1. Go to [Figma Settings → Security](https://www.figma.com/settings) → **Personal access tokens**
2. Create a new token with read access (scopes: `file_content:read`, `file_metadata:read`; add `file_variables:read` on an Enterprise plan to use `--variables`)

### 2. Set the Environment Variable

```bash
# Add to your shell config (~/.zshrc, ~/.bashrc, etc.)
export FIGMA_ACCESS_TOKEN=your_token_here
```

Reload your shell or run `source ~/.zshrc`.

## Usage

Two scripts are available, sharing `scripts/figma_common.py` (auth, URL parsing, HTTP). Both require Python 3.10+ (standard library only, zero dependencies).

> **Quota**: node specs and image export are Figma **Tier 1** endpoints — View/Collab seats get 6 calls per *month*. Each command makes one call no matter how many nodes it covers, so pass every node from a file to a single command instead of looping.

### figma_fetch.py — Fetch design specs

```bash
# Inspect a specific node (URL with node-id)
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2"

# Several nodes from the same file, one API call
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2" --ids 3-4,5-6

# File overview (URL without node-id) — metadata endpoint, Tier 3
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name"

# Overview plus pages and components (one Tier 1 call)
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name" --pages

# Limit tree depth (default: 5); read an older version
python3 scripts/figma_fetch.py "https://..." --depth 3 --version 1234567890

# Layer tree only (type, name, id, size) — for big pages/sections
python3 scripts/figma_fetch.py "https://...?node-id=1-2" --outline --depth 2

# Resolve design-token names (+1 Tier 2 call, Enterprise plan only)
python3 scripts/figma_fetch.py "https://...?node-id=1-2" --variables
```

Outputs structured markdown to stdout with layout, colors, typography, effects, and component data — one section per node. Every layer shows its node id; shared styles and main components are shown by name (`Styles: fill=Brand/Primary`, `Component: Button/Primary`), resolved from the same API response at no extra cost.

### figma_export.py — Export nodes as images

Downloads rendered images of one or more nodes from the same file (one API call) and prints each saved path.

```bash
# Download one node as PNG @2x (default)
python3 scripts/figma_export.py "https://www.figma.com/design/ABC123/Name?node-id=1-2"

# SVG export, keeping text as <text>
python3 scripts/figma_export.py "https://..." --format svg --svg-outline-text false

# Several nodes into a directory with chosen names
# (use the unified cache dir for temp exports)
# macOS: ~/Library/Caches/mythril-skills-cache/figma/
# Linux: ${XDG_CACHE_HOME:-~/.cache}/mythril-skills-cache/figma/
python3 scripts/figma_export.py "https://www.figma.com/design/ABC123/Name?node-id=1-2" \
  --ids 3-4 --out-dir "$HOME/Library/Caches/mythril-skills-cache/figma" --names button,card
```

**Options**:

| Flag | Default | Description |
|---|---|---|
| `--ids` | — | Extra comma-separated node ids from the same file |
| `--format` | `png` | `png`, `jpg`, `svg`, or `pdf` |
| `--scale` | `2.0` | Export scale factor 0.01–4 (1.0 = @1x, 2.0 = @2x) |
| `--output` | `./figma_<node-id>.<format>` | Output file path (single node only) |
| `--out-dir` | new dir under `mythril-skills-cache/figma/` | Output directory (one or more nodes) |
| `--names` | `figma_<node-id>` | One file name per node, in order |
| `--version` | latest | Render a specific file version |
| `--image-fills` | — | Download the original images behind image fills (the `ref:` values from `figma_fetch.py`) instead of rendering nodes. Tier 2 — no Tier 1 quota |
| `--contents-only` | `true` | `false` also renders content overlapping the node |
| `--absolute-bounds` | off | Full node dimensions even if cropped |
| `--svg-outline-text` | `true` | SVG only: `false` keeps `<text>` elements |

On success, prints the **absolute path** of each saved file. Use these paths to open the images or pass them to the AI for visual analysis alongside the spec output from `figma_fetch.py`.

**Supported URL formats**:
- `https://www.figma.com/design/FILE_KEY/Name?node-id=1-2`
- `https://www.figma.com/file/FILE_KEY/Name?node-id=1%3A2`
- `https://www.figma.com/proto/FILE_KEY/Name`
- `https://www.figma.com/board/FILE_KEY/Name` (FigJam), `/slides/...`, `/make/...`
- `https://www.figma.com/design/MAIN_KEY/branch/BRANCH_KEY/Name?node-id=1-2` — the branch key is used, so you read the branch, not the main file

> `figma_export.py` requires a node id (in the URL or via `--ids`). Right-click any layer in Figma → "Copy link to selection" to get one. Pass each URL as its own quoted argument with nothing appended — the scripts reject URLs containing whitespace or malformed node ids.

## Output Format

The script outputs structured markdown. Fields are emitted only when present on the node — sections that don't apply to a given node type are omitted.

### Node-level metadata (always present)

| Field | Description |
|---|---|
| `id` | Figma node ID |
| `name` | Layer name |
| `type` | Node type (FRAME, TEXT, RECTANGLE, COMPONENT, INSTANCE, etc.) |
| `devStatus` | `READY_FOR_DEV` or `COMPLETED` if set in Dev Mode |

### Visual

| Field | Description |
|---|---|
| **Opacity** | Node-level opacity (omitted when 1.0) |
| **Blend mode** | CSS mix-blend-mode equivalent (omitted when NORMAL/PASS_THROUGH) |
| **Is mask** | Whether this layer is a clipping mask |

### Layout

| Field | Description |
|---|---|
| **Size** | `width × height` from `absoluteBoundingBox` (canvas-space layout dimensions) |
| **Position** | `x, y` from `absoluteBoundingBox` (shown for child nodes) |
| **Render bounds** | Actual visual extents including overflow effects (shadows, blur). Only shown when different from layout bounds. |
| **Rotation** | Layer rotation in degrees |
| **Layout positioning** | `ABSOLUTE` = taken out of auto-layout flow (CSS `position: absolute`) |
| **Layout (child)** | `layoutAlign` + `layoutGrow` — how this child behaves inside a parent auto-layout frame |
| **Constraints** | Horizontal + vertical resize constraints (`LEFT`, `RIGHT`, `CENTER`, `SCALE`, `STRETCH`) |
| **Size constraints** | `minWidth`, `maxWidth`, `minHeight`, `maxHeight` |

### Auto-layout (FRAME nodes with `layoutMode`)

| Field | Description |
|---|---|
| `layoutMode` | `HORIZONTAL`, `VERTICAL`, or `GRID` |
| `itemSpacing` | Gap between children |
| `layoutWrap` | `WRAP` for flex-wrap behavior (omitted when `NO_WRAP`) |
| `counterAxisSpacing` | Gap between wrapped rows/columns (when WRAP) |
| `paddingTop/Right/Bottom/Left` | Inner padding |
| `primaryAxisAlignItems` | Main axis alignment (`MIN`, `CENTER`, `MAX`, `SPACE_BETWEEN`) |
| `counterAxisAlignItems` | Cross axis alignment (`MIN`, `CENTER`, `MAX`, `BASELINE`) |
| `layoutSizingHorizontal/Vertical` | `FIXED`, `HUG`, or `FILL` |
| `itemReverseZIndex` | If `true`, first child is drawn on top (CSS z-order reversal) |

### Colors & Paints

| Paint type | Output format |
|---|---|
| `SOLID` | `#RRGGBB` or `#RRGGBB (opacity: 0.XX)` |
| `GRADIENT_*` | `GRADIENT_LINEAR: #HEX at 0%, #HEX at 100%, ...` |
| `IMAGE` | `image fill (ref: <imageRef>, scale: <scaleMode>)` |
| `PATTERN` | `pattern fill (source: <nodeId>)` |

### Borders & Strokes

| Field | Description |
|---|---|
| `cornerRadius` | Uniform border radius |
| `rectangleCornerRadii` | Per-corner radii `[TL, TR, BR, BL]` (shown only when non-uniform) |
| `cornerSmoothing` | 0–1 (0.6 = iOS squircle) |
| `strokes` | Stroke paint(s) with weight, alignment, cap, join |
| `strokesIncludedInLayout` | Present when `true` — equivalent to CSS `box-sizing: border-box` |
| `complexStroke` | Type of a complex stroke (`complexStrokeProperties`, e.g. variable width / brush) — approximate in CSS |

### Effects

| Effect type | Output format |
|---|---|
| `DROP_SHADOW` / `INNER_SHADOW` | `drop shadow: color=#HEX offset=(x,y) blur=N spread=N` |
| `LAYER_BLUR` / `BACKGROUND_BLUR` | `layer blur: radius=N` |

### Typography (TEXT nodes only)

| Field | Description |
|---|---|
| `fontFamily`, `fontSize`, `fontWeight` | Core font identity |
| `italic`, `textCase`, `textDecoration` | Font style modifiers |
| `lineHeightPx` | Line height in pixels |
| `letterSpacing` | Letter spacing |
| `textAlignHorizontal` | `LEFT`, `CENTER`, `RIGHT`, `JUSTIFIED` |
| `textAlignVertical` | `TOP`, `CENTER`, `BOTTOM` |
| `paragraphSpacing`, `paragraphIndent` | Paragraph layout |
| `textTruncation` + `maxLines` | Overflow truncation (ellipsis) |
| `characters` | Text content (truncated at 200 chars) |

### Component metadata (INSTANCE nodes)

| Field | Description |
|---|---|
| `componentId` | ID of the master component |
| `componentProperties` | Override values for component props |

### Export settings

Present when a node has configured export presets: `PNG@2x`, `SVG@1x/icon`, etc.

### Design tokens

| Field | Description |
|---|---|
| `boundVariables` | List of property names driven by Figma Variables (e.g. `fills`, `paddingLeft`). Use `/v1/files/:key/variables/local` to resolve variable values. |

### Children

Rendered recursively up to `--depth` levels. Invisible nodes (`visible: false`) are excluded. When the limit is reached, a truncation note shows the child count.

### Figma API Notes

- Sizes come from `absoluteBoundingBox.width/height` (always present), not `size` (only with `geometry=paths`)
- Colors are RGBA floats (0–1), converted to hex by the script
- `absoluteRenderBounds` is the actual visual extent (includes blur/shadow overflow); differs from `absoluteBoundingBox` when effects overflow the layout box
- Text styles are on `node.style` (TypeStyle object), not directly on the node
- `fills` and `strokes` are arrays of Paint objects; `type: SOLID` has a `color` sub-object
- `layoutPositioning: ABSOLUTE` means a child is pinned inside an auto-layout frame without participating in the layout flow — equivalent to CSS `position: absolute`
- `layoutGrow: 1` on a child = CSS `flex-grow: 1` (fills remaining space)
- `constraints` define how a node resizes when its parent resizes (non-auto-layout frames)

## Error Handling

| Exit Code | Error | Cause | Fix |
|---|---|---|---|
| 1 | `FIGMA_ACCESS_TOKEN not set` | Token missing from env | Set `export FIGMA_ACCESS_TOKEN=xxx` |
| 1 | `Figma API 403` | Token invalid or expired | Regenerate at figma.com/settings |
| — | `NOTE: metadata endpoint returned 403` | Token lacks `file_metadata:read` scope | Overview falls back to `GET /v1/files` automatically; add the scope to save Tier 1 quota |
| 1 | `Figma API 404` | File not found or no access | Check URL; ensure you have view access |
| — | `NOTE: could not resolve variable names` | `--variables` without an Enterprise plan or `file_variables:read` scope | Output still lists which fields are bound to tokens; use the Figma MCP server for token names |
| 2 | `Not an imageRef` | `--image-fills` given something other than the hex `ref:` value | Copy the `ref:` from `figma_fetch.py` output |
| 2 | `Could not find a file key` / `Not a figma.com URL` | Malformed URL | Use a URL copied directly from Figma |
| 2 | `URL contains whitespace` / `Invalid node id` | Extra text glued onto the URL or node id | Pass each URL alone, quoted; use `--names` for file names |
| 2 | `All URLs must belong to the same Figma file` | Batch spans files | Run once per file |
| 2 | `--output takes one file` | `--output` with several nodes | Use `--out-dir` (and `--names`) |
| 1 | `Node not found` | node-id refers to deleted/moved node | Re-copy the link from Figma |
| 2 | `No node id given` | figma_export.py needs a node URL or `--ids` | Right-click layer → "Copy link to selection" |
| 1 | `No image rendered for node` | Node is empty or render failed (other nodes are still saved) | Try a different node; check it has visible content |
| — | Script hangs | Network timeout | Check internet; try again |

If the response is empty or truncated on large files, use `--depth 2` to limit traversal.
