---
name: fullstack-brief
description: |
  Export the complete context of a multi-repo fullstack workspace, a single
  repo, or any user-specified directory into ONE self-contained, AI-optimized
  Markdown brief. Purpose: paste it into a web AI (ChatGPT, Claude.ai, Gemini)
  and continue architecture/design discussions without the local CLI agent,
  saving local tokens. Pure text: no local file or image references (paths
  appear as inline code text), mermaid diagrams and internet links allowed.
  Modes: workspace (writes into the docs repo docs directory), single-repo
  (writes into the repo docs directory), or explicit — when the user names
  a directory or subject, the user's instruction wins over auto-detection.
  Destination path and filename MUST be confirmed with the user before
  writing. Includes mandatory secret-redaction rules.
  Trigger: "fullstack brief", "context brief", "context handoff",
  "export context", "generate context doc", "brief me on this codebase",
  "导出上下文", "上下文简报", "生成简报", "上下文交接", "项目简报",
  "喂给网页AI", "网页AI上下文".
license: Apache-2.0
---

# Fullstack Brief

Export the knowledge of a multi-repo fullstack workspace, a single repo, or a
user-specified directory into **one self-contained Markdown brief** whose
reader is another AI, not a
human. The user pastes this file into a web AI session (ChatGPT, Claude.ai,
Gemini, ...) and continues solution discussions there — instead of paying
local CLI agent tokens for every message.

This skill is read-only on all code repos. It writes exactly one file: the
output brief.

## Core Principles

1. **Written for an AI reader** — dense, factual, well-structured prose.
   Completeness beats brevity within the size budget. No marketing tone,
   no filler. Every sentence must transfer information the external AI
   cannot guess.
2. **Self-contained** — the file must survive being pasted into a web chat:
   - NO relative markdown links to local files, NO images, NO embeds.
   - File paths appear as inline code (`path/to/file.py`) — quoted text,
     not links. This is expected and encouraged.
   - Mermaid diagrams are allowed and encouraged (if the target does not
     render them, they still read as plain structured text).
   - Internet URLs (public docs, spec pages) are allowed.
3. **Snapshot semantics** — record generation date and per-repo commit SHA.
   State inside the document that it is a snapshot, so the external AI
   treats it accordingly.
4. **Verified claims** — same rule as `fullstack-explore`: documents and
   graphify tell you WHERE to look; source code tells you WHAT is true.
   Read actual files before asserting architecture facts in the brief.

## Security — MANDATORY rules for AI agents

The output file will be pasted into THIRD-PARTY web services. Therefore:

1. **NEVER open credential files** to copy their contents into the brief:
   `.env`, `.env.*`, `*.pem`, `*.key`, `credentials.json`,
   `service-account*.json`, `.netrc`, IDE auth caches. You MAY note that
   such files EXIST and list variable NAMES only (e.g. "`.env` defines
   `DATABASE_URL`, `REDIS_URL`") — never values.
2. **NEVER include token/key/password values** in any form: API keys, JWTs,
   connection strings with credentials, private keys, cookies,
   `Authorization` headers. Refer to them by variable name only.
3. **Self-scan before writing**: search the composed markdown for
   secret-looking strings (`sk-`, `ghp_`, `github_pat_`, `AKIA`, `xoxb`,
   `BEGIN ... PRIVATE KEY`, `password=`, long base64/hex blobs). Remove or
   redact every hit before showing the preview to the user.
4. **Internal-only URLs** (intranet wikis, VPN-only Jira/Confluence,
   staging hosts) are unreachable from a web AI session. Include only with
   an "(internal)" marker, or drop when they add nothing.
5. **Warn once at confirmation**: when presenting the destination
   (Step 3), remind the user the file is meant to be pasted into
   third-party web AI services.

## Step 0 — Determine Scope: User Override Wins, Then Auto-Detect

### User override wins (honor the user first)

If the prompt names an explicit scope, the user decides — never let
auto-detection override the user's instruction:

- **User names a specific directory** (absolute or workspace-relative path):
  that directory IS the scope root. Run `detect_scope.py <dir>` to classify it:
  - `SCOPE=workspace` → workspace mode rooted at the user's directory.
  - `SCOPE=repo` → single-repo mode rooted there.
  - `SCOPE=none` → explicit-directory mode: brief that folder as-is (a git
    repo is NOT required). The user's directory becomes the scope.
- **User names specific subjects/modules** ("只总结支付模块", "只讲订单
  服务", "summarize only the auth service") → those subjects are the mandatory
  Topic Focus AND the set of repos/modules to read; do not widen to the whole
  default workspace.
- **Default — no explicit scope** → run the auto-detection below.

### Auto-detection (MANDATORY SCRIPT CALL)

Run `detect_scope.py` the same way other fullstack skills run their gate
scripts:

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/fullstack-brief/scripts/detect_scope.py",
    pathlib.Path.home() / ".claude/skills/fullstack-brief/scripts/detect_scope.py",
    pathlib.Path.home() / ".copilot/skills/fullstack-brief/scripts/detect_scope.py",
    pathlib.Path.home() / ".cursor/skills/fullstack-brief/scripts/detect_scope.py",
    pathlib.Path.home() / ".gemini/skills/fullstack-brief/scripts/detect_scope.py",
    pathlib.Path.home() / ".codex/skills/fullstack-brief/scripts/detect_scope.py",
    pathlib.Path.home() / ".qwen/skills/fullstack-brief/scripts/detect_scope.py",
    pathlib.Path.home() / ".grok/skills/fullstack-brief/scripts/detect_scope.py",
]
script = next((p for p in candidates if p.exists()), None)
if not script:
    print("ERROR: detect_scope.py not found", file=sys.stderr)
    sys.exit(1)
result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
print(result.stdout)
```

Output keys:

| Key | Meaning |
|-----|---------|
| `SCOPE=workspace\|repo\|none` | Detected mode |
| `ROOT=<path>` | Root used for detection |
| `DOCS_DIR=<name>` | Docs repo dir name (workspace mode, from `fullstack.json`) |
| `GITHUB_REPOS=true\|false` | Workspace flag (informational here) |
| `IS_GIT=true\|false` | Whether ROOT itself is a git repo |

Decision logic:

- `SCOPE=workspace` → workspace mode. If `DOCS_DIR` is empty (corrupt
  config), ask the user for the docs directory name before Step 3.
- `SCOPE=repo` → single-repo mode.
- `SCOPE=none` → if the user explicitly requested this scope, proceed in
  explicit-directory mode (see "User override wins"). Otherwise STOP and tell
  the user: run this skill on a git repo, or at a workspace root initialized
  by `fullstack-init`.

### Announce the Scope contract (MANDATORY OUTPUT)

After detection, output EXACTLY this line before continuing:

```
Scope: <workspace|repo|dir> | root=<ROOT> | docs_dir=<DOCS_DIR|->
```

Use English regardless of conversation language — machine-readable marker.

## Language Selection

The brief's language MUST match the language of the user's prompt:

1. If the user **explicitly requests a language** → use that language.
2. If the user's prompt contains **any Chinese characters** → Chinese.
3. Otherwise → English (default).

Filenames stay lowercase-hyphenated English regardless of document language.

## Depth & Focus Selection

Infer silently from the prompt; ask nothing when defaults fit.

| Depth | When | Target size |
|-------|------|-------------|
| quick | "快速简报", "quick brief" | ~20 KB (~5k tokens) |
| standard (default) | otherwise | ~80 KB (~20k tokens) |
| deep | "深入", "详细", "deep", "all details" | up to ~200 KB |

**Topic focus**: if the prompt names a topic ("针对支付重构的简报"),
allocate extra depth to related repos/modules and compress unrelated ones.

**Trimming order** (cut from the bottom first): open questions → glossary →
current state → conventions → code map → key flows → repo map → mission &
architecture. Never trim the security self-scan or snapshot header.

## Step 1 — Gather Context

Follow the token-efficient chain (workspace docs → graphify → source files).

### Workspace mode

1. **Workspace docs**: `fullstack.json`, workspace `AGENTS.md` (repo table,
   conventions), `<docs-dir>/AGENTS.md`.
2. **Active work items**: list `<docs-dir>/changes/{feat,refactor,fix}/`
   directories; for each, skim `plan.md` / `analysis.md` headers only —
   extract name, objective, status, affected repos. Do NOT paste whole
   work documents into the brief.
3. **Per repo** (from the AGENTS.md repo table):
   - `README.md`, package manifests (`package.json`, `pyproject.toml`,
     `go.mod`, `build.gradle*`, `Podfile`, ...) → stack + versions
   - graphify: run `python3 SKILL_PATH/scripts/graphify_check.py <repo>`.
     When `graphify-out/` exists, `cd <repo> && graphify query "<question>"`
     for module/relationship structure before grepping.
   - key entry points: main/app bootstrap files, route definitions,
     public API surfaces.
4. **Cross-repo relationships**: who calls whom (HTTP routes, clients,
   shared schemas/events). Verify by reading both sides of each boundary.

### Single-repo mode

Same as above minus cross-repo parts; the repo IS the scope. Detect
monorepo layouts naturally (workspaces/packages dirs) and describe them as
internal modules.

### Explicit-directory mode

The user-named directory IS the scope, repo or not. Apply the single-repo
chain to it: enumerate its top-level entries (subdirs, key files) into the
Module Map, read each submodule's entry points, and describe structure
honestly — no framework jargon if none is present. If the folder sits inside
a workspace, skip workspace-only sections (docs-dir changes, work items,
cross-repo map) unless the user asked for them.

### Verification budget

Read enough source to back every architecture claim with at least one real
file you opened. Mark anything you could not verify as "⚠️ unverified" in
the brief instead of guessing.

## Step 2 — Compose the Document

Use this template. Section sizes adapt to depth; keep heading numbering.

```markdown
# <Workspace, Repo, or Directory Name> — Context Brief

> Snapshot generated YYYY-MM-DD by fullstack-brief for use in an external
> AI session. Scope: N repos @ <sha short> | single repo @ <sha> | explicit
> dir <path>.
> Self-contained: paths are quoted text, not live links. Code has evolved
> since this snapshot — verify critical details against the repo when it matters.

## Reader Notes (for the AI consuming this brief)
- This is a point-in-time export; treat it as ground truth for the listed
  commits only.
- Claims marked ⚠️ were not fully verified against source.
- Ask for missing details rather than inventing them.

## 1. Mission & Overview
What the product/system does, users, and the problem space. 2-4 paragraphs.

## 2. Architecture Overview
Prose + ONE mermaid `graph TD/LR` of major components and boundaries
(frontend/api/db/queue/external services). Annotate tech per node.

## 3. Repositories & Responsibilities
| Repo | Role | Stack & versions | Key entry points |
(For single-repo or explicit-directory mode: "Module Map" with top-level
entries instead.)

## 4. Key Flows
2-4 mermaid `sequenceDiagram`/`flowchart` for the most important flows,
e.g. auth, core business transaction, deploy pipeline. One paragraph each.

## 5. Code Map — Key Modules
Per repo/module: path (inline code) → purpose → notable symbols
(classes/functions) → gotchas. This is the largest section at deep depth;
at quick depth keep only the most load-bearing modules.

## 6. Conventions & Constraints
Languages/frameworks with versions; coding standards actually observed in
the codebase; branch naming; commit style; PR process; test/build/run
commands; environment/config strategy (names only); known constraints
(perf budgets, compliance, supported platforms).

## 7. Current State
Active work items (name, type, status, repos touched, one-line objective);
recently completed items if relevant; known issues / TODO clusters;
in-flight migrations.

## 8. Domain Glossary
Table: term → meaning. Include internal jargon the external AI cannot know.

## 9. Open Questions for the Session
What the user plans to discuss (if stated). Empty if none.
```

### Mermaid authoring rules

- Read bundled `references/MERMAID-RULES.md` before authoring diagrams.
- Lint EVERY diagram before writing the file:
  `python3 SKILL_PATH/scripts/mermaid_lint.py <draft.md>` — fix all errors.
- Keep diagrams under ~30 nodes; prefer several small diagrams over one giant.

## Step 3 — Confirm Destination & Write (MANDATORY USER CONFIRMATION)

Propose the destination BEFORE writing anything:

- Workspace mode default:
  `<workspace-root>/<DOCS_DIR>/docs/<filename>.md`
- Single-repo mode default: `<repo-root>/docs/<filename>.md`
  (create `docs/` if missing)
- Explicit-directory mode default:
  `<explicit-dir>/docs/<filename>.md` (create `docs/` if missing; when
  unsure, ask the user for a destination)
- Filename default: `context-brief-YYYY-MM-DD.md`, or
  `brief-<topic>-YYYY-MM-DD.md` when a topic was given
  (lowercase-hyphenated English).

Present to the user, then WAIT for confirmation:

```
Destination: <absolute path>
Depth: <quick|standard|deep> | Focus: <topic|->
Estimated size: <N KB ≈ N tokens>
Note: this file is intended to be pasted into third-party web AI services.
Confirm? (Enter = write here, or provide another path/filename)
```

After confirmation:

1. Run the secret self-scan (Security rules) on the final markdown.
2. `mkdir -p` the destination directory and write the file.
3. Report: final path, size in KB, estimated tokens (~chars/4 for mixed
   CJK content count CJK chars individually), and usage hint:
   "Paste the entire file as your first message in the web AI session."

## Requirements

- Python 3.10+ (stdlib only)
- Optional: `graphify` CLI for knowledge-graph queries (checked via
  bundled `graphify_check.py`; skipped gracefully when absent)
