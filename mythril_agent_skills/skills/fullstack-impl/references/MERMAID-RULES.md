<!--
CANONICAL SOURCE: mythril_agent_skills/shared/mermaid/MERMAID-RULES.md
Bundled identical copies live under each consuming skill's references/
directory. To update, edit the canonical source and run:

    python3 scripts/sync-shared-assets.py

The drift test (tests/test_shared_assets_sync.py) fails CI if any
bundled copy diverges from the canonical source.
-->

# Mermaid 10.2.3 Compatibility Rules

This is the **single source of truth** for mermaid diagram rules across
all skills in `mythril-agent-skills`. The companion linter is
`mermaid_lint.py` in the same directory. Every rule below maps to a
machine-checkable rule in the linter.

## Why "10.2.3"?

Many platforms used to render Markdown ship Mermaid 10.2.3 or earlier:

- Older GitHub Enterprise instances
- Confluence (Atlassian's storage format and most renderer plugins)
- Notion exports (PDF / HTML)
- Internal wikis and documentation sites
- IDE preview plugins (older VS Code mermaid extensions)

Newer mermaid syntax causes silent "Syntax error in text" rendering
failures that block readers. The rules below are the minimum subset that
keeps a diagram readable on every common platform.

## The rules

### 1. Quote edge labels that contain `( ) [ ] { }`

Edge labels (the `|...|` between two nodes in `flowchart` / `graph`)
must be wrapped in double quotes when the label contains any of
`(`, `)`, `[`, `]`, `{`, `}`.

```
A -->|hello (world)| B          ← FAIL on 10.2.3
A -->|"hello (world)"| B        ← OK
```

Linter rule: `unquoted-edge-label`.

### 2. Quote subgraph titles that contain parentheses

```
subgraph My (Group)             ← FAIL
subgraph "My (Group)"           ← OK
```

Linter rule: `unquoted-subgraph-title`.

### 3. Do not use the post-10.2.3 `@{ ... }` shape syntax

The compact shape syntax was introduced in mermaid 11.x and is not
recognized by older renderers.

```
A@{ shape: rect, label: "x" }   ← FAIL on 10.2.3
A[x]                            ← OK
```

Use the classic shapes: `[rect]`, `(round)`, `{diamond}`, `((circle))`,
`>asymmetric]`, `{{hex}}`, `[/parallelogram/]`.

Linter rule: `new-shape-syntax`.

### 4. Do not use post-10.2.3 beta diagram types

The following diagram types do not exist in 10.2.3 and crash older
renderers:

- `block-beta`
- `quadrantChart`
- `xychart-beta`
- `sankey-beta`
- `packet-beta`
- `architecture-beta`
- `treemap`
- `radar`
- `kanban`

Linter rule: `beta-diagram-type`.

### 5. Use `<br/>` for line breaks, never `\n`

**This is the most common bug.** When writing a multi-line node label,
the natural impulse is to insert `\n`:

```
A[xxx-api\n(Domain API)]         ← FAIL — renders as the literal text
                                          `xxx-api\n(Domain API)`
A["xxx-api<br/>(Domain API)"]    ← OK
```

On Mermaid 10.2.3, GitHub's renderer, and every other renderer that
defaults to `htmlLabels: true`, the two characters `\` and `n` stay in
the rendered box. They do **not** become a newline.

**Always use `<br/>`**, the XHTML-style self-closing line break tag.
And note that you typically need to wrap the label in double quotes
because the surrounding text often contains parens or other special
characters.

Alternative (mermaid 9.4+): the markdown-string syntax with backticks
also supports real newlines:

```
A["`xxx-api
(Domain API)`"]
```

But `<br/>` is the safer default — it works on every mermaid version
and in every label position (nodes, edges, subgraph titles).

Linter rule: `literal-backslash-n`.

### 6. Use `<br/>`, not bare `<br>`

`<br>` (no closing slash) renders visually on GitHub but produces
**invalid XML/SVG**. It breaks Confluence storage format, Notion
exports, and any strict XML/SVG parser. Always use the XHTML
self-closing form `<br/>`.

```
A[line1<br>line2]               ← FAIL — invalid SVG
A[line1<br/>line2]              ← OK
```

Linter rule: `bare-br-tag`.

## Quick reference — when to quote

| Position | Quote when label contains |
|---|---|
| Node label `[label]` `(label)` `{label}` | `(`, `)`, `[`, `]`, `{`, `}`, `"`, `<`, `>`, `\|`, or `<br/>` |
| Edge label `\|label\|` | Same as above |
| Subgraph title `subgraph Title` | `(`, `)` (other chars usually fine) |

Inside a quoted label, escape an embedded `"` as `&quot;` (HTML entity).

## Programmatic label escape

When a skill builds mermaid from structured data, use the shared
`escape_label_for_mermaid(text)` helper in `mermaid_lint.py`. It:

- Converts real newlines (`\n`, `\r\n`, `\r`) → `<br/>`
- Converts literal backslash-n (`\\n` written by the model) → `<br/>`
- Escapes embedded `"` → `&quot;`
- Wraps in double quotes when the result needs quoting

```python
from mermaid_lint import escape_label_for_mermaid

# At write-time when building a node:
node_label = escape_label_for_mermaid(stage["name"])
md.append(f"    {stage['id']}[{node_label}]")
```

## Mermaid Compatibility Gate

After writing or editing any `.md` file that contains ` ```mermaid `
blocks, run the gate:

```bash
python3 path/to/mermaid_lint.py FILE [FILE ...]
```

Output:

```
STATUS=PASS|FAIL
BLOCKS_CHECKED=<N>
ERROR: <file>:<line>: [<rule>] <message>
...
```

Exit codes:
- `0` — all blocks pass
- `1` — at least one issue detected
- `2` — invocation error (no files, missing file)

The gate is mandatory after writing any mermaid-bearing doc. Skipping
the gate is the single most common cause of broken diagrams on GitHub
Enterprise, Confluence, Notion exports, and internal wikis.

## Locating the linter across AI tools

Skills are installed into different per-tool directories. Each
consuming skill bundles its own copy of `mermaid_lint.py` under
`<skill>/scripts/mermaid_lint.py`, so the in-skill path is always:

```
<this-skill-dir>/scripts/mermaid_lint.py
```

If the bundled copy is missing (rare — package install was broken),
fall back to checking these candidate paths in order, use the first
that exists:

```
~/.config/opencode/skills/<skill>/scripts/mermaid_lint.py
~/.claude/skills/<skill>/scripts/mermaid_lint.py
~/.copilot/skills/<skill>/scripts/mermaid_lint.py
~/.cursor/skills/<skill>/scripts/mermaid_lint.py
~/.gemini/skills/<skill>/scripts/mermaid_lint.py
~/.codex/skills/<skill>/scripts/mermaid_lint.py
~/.qwen/skills/<skill>/scripts/mermaid_lint.py
~/.grok/skills/<skill>/scripts/mermaid_lint.py
~/.openclaw/skills/<skill>/scripts/mermaid_lint.py
~/.hermes/skills/<skill>/scripts/mermaid_lint.py
```

(Replace `<skill>` with the active skill name — `fullstack-impl`,
`fullstack-spike`, or `user-journey`.)

If none exist, fall back to manual review of the diagram against the
rules above and document the gap.
