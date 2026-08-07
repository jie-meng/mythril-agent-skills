---
name: fullstack-init
description: |
  Initialize or update a multi-repo fullstack workspace — discover repos,
  generate AGENTS.md, create docs directory and workspace agents.
  Trigger: "fullstack init", "fullstack initialize", "fullstack setup",
  "全栈初始化", "初始化全栈工作区", "全栈 init".
license: Apache-2.0
---

# Fullstack Workspace Initializer

Initialize or update a multi-repo fullstack workspace so AI coding assistants
have full cross-repo context. Designed for projects where web, api, ios,
android, and other repos live as sibling directories under one root.

## Design Philosophy

**First run is a full refresh; subsequent runs do incremental updates.**
On first run (or if `--force` is passed), the script regenerates all
scaffolding files from scratch. On subsequent runs, it detects that the
workspace has already been initialized and performs an **incremental
update** on `AGENTS.md` — preserving existing content while adding new
sections, updating the repos table, and merging Workspace Conventions
bullet points introduced by template updates.

| Category | First run / `--force` | Subsequent run |
|----------|----------------------|----------------|
| **Generated from scratch** | `AGENTS.md`, `README.md`, `.agents/agents/*.md` | `README.md`, `.agents/agents/*.md` |
| **Merged incrementally** | — | `AGENTS.md` (add new sections, update repos table, merge conventions, preserve user content) |
| **Preserved** | `fullstack.json`, `<docs-dir>/`, `scripts/`, `.agents/skills/` | same |
| **Create-only** | `<docs-dir>/` + git init, `scripts/`, `.agents/skills/` — created if missing, never touched if present | same |

This allows the workspace's AGENTS.md to evolve organically — users can add
project-specific sections, conventions, or documentation — while still
receiving template updates (like the Knowledge Graph section) on re-runs.

## What It Does

1. **Discovers** all git repos in immediate subdirectories
2. **Analyzes** each repo's README.md, AGENTS.md, tech stack, and role
3. **Regenerates** workspace-level infrastructure from scratch
4. **Preserves** user content in docs dir, scripts/, and .agents/skills/

## How the AI Agent MUST Handle Already-Initialized Workspaces

When `fullstack.json` **and** `AGENTS.md` both exist in the workspace root,
the workspace has already been initialized. The script automatically
performs an **incremental merge** on AGENTS.md:

- **Repos table**: Updated to match current repos (new repos may have been added)
- **Workspace Conventions bullet points**: New ones from template updates are appended
- **Directory Structure**: Updated to match current scaffolding layout
- **New H2 sections**: Inserted if they appear in the generated template but not in the existing file
- **User-customized content**: Preserved — sections that exist in both versions keep the user's version

The AI agent simply runs the script — no post-hoc merge steps needed.
To bypass merging and do a full overwrite, pass `--force`.

## Docs Directory — Independent Git Repo

The shared docs directory is an **independent git repository**, NOT managed
by the workspace git. It does NOT use feature branches — work tracking docs
are committed directly to its main branch.

The name is configurable (defaults to `central-docs`) and stored in
`fullstack.json`.

### How the AI agent MUST handle the docs dir name

1. **Check if `fullstack.json` exists** — if YES, docs dir is already
   configured. No need to ask. Run the script.
2. **Check if user specified a name** in their prompt — if YES, pass
   `--docs-dir <name>`.
3. **Otherwise, ask the user** (MANDATORY — do NOT silently use the default):
   > What should I name the shared docs directory? (default: `central-docs`)

## Usage

```bash
python3 SKILL_PATH/scripts/workspace_init.py                         # first run
python3 SKILL_PATH/scripts/workspace_init.py --docs-dir my-docs      # custom docs dir
python3 SKILL_PATH/scripts/workspace_init.py --lang zh               # Chinese README
python3 SKILL_PATH/scripts/workspace_init.py --github                # repos are on GitHub
python3 SKILL_PATH/scripts/workspace_init.py --no-github             # repos are NOT on GitHub
python3 SKILL_PATH/scripts/workspace_init.py                         # re-run: incremental merge
python3 SKILL_PATH/scripts/workspace_init.py --force                 # re-run: full overwrite
python3 SKILL_PATH/scripts/workspace_init.py --dry-run               # preview only
python3 SKILL_PATH/scripts/workspace_init.py --json                  # JSON output
```

### How the AI agent MUST handle the GitHub repos setting

1. **Check if `fullstack.json` exists and has `github_repos` set** — if YES,
   the setting is already configured. No need to ask. Run the script.
2. **Check if user specified it** in their prompt (e.g., "repos are on GitHub",
   "仓库在GitHub上") — if YES, pass `--github`.
3. **Otherwise, ask the user** (MANDATORY — do NOT silently use the default):
   > Are these repositories hosted on GitHub or GitHub Enterprise? (yes/no)
   >
   > If yes, `fullstack-apply` will be able to create Pull Requests
   > automatically after implementation and review are done.

   This includes GitHub Enterprise with custom domains (e.g., `git.company.com`).
   If the user answers yes, pass `--github`. If no, pass `--no-github`.

The setting is saved to `fullstack.json` as `"github_repos": true|false` and
persists across re-runs. Changing it requires passing `--github` or
`--no-github` explicitly on a future run.

### README language selection

The generated `README.md` includes a usage guide for the fullstack skills.
Its language is controlled by the `--lang` flag:

- `--lang zh` — Chinese
- `--lang en` — English (default)

**How the AI agent MUST choose the language**:

1. Examine the user's prompt that triggered this skill.
2. If the prompt contains **any Chinese characters** → pass `--lang zh`.
3. Otherwise → pass `--lang en` (or omit `--lang`).

This applies to every invocation, including re-runs. The README is
regenerated each time, so the language always reflects the latest run.

## Workspace Agents

Four subagents are generated in `.agents/agents/` on every run. Each file
contains YAML frontmatter (`name`, `description`, `mode: subagent`,
`permission`) compatible with OpenCode and Claude Code, followed by role-
specific instructions. Tools that support native subagent discovery
(OpenCode, Claude Code, Cursor, Copilot) receive symlinks so their
subagent systems automatically discover these agents:

| Agent | File | Role | Permissions |
|-------|------|------|-------------|
| Planner | `planner.md` | Analyzes requirements, writes `plan.md` | read-only on code |
| Developer | `developer.md` | Implements code — the only agent that writes production code | full access |
| Reviewer | `reviewer.md` | Reviews with falsification mindset, writes `review.md` | read-only on code |
| Debugger | `debugger.md` | Root-cause analysis for fix work type | full access |

These are regenerated on every run. Any customization will be overwritten.
For persistent custom agents, use `.agents/skills/` or repo-level agents.

### How AI tools discover these agents

On every run, the script creates relative symlinks from tool-specific
agent directories to `.agents/agents/`:

```
.opencode/agents -> ../.agents/agents   (OpenCode subagents)
.claude/agents   -> ../.agents/agents   (Claude Code subagents)
.cursor/agents   -> ../.agents/agents   (Cursor subagents)
.copilot/agents  -> ../.agents/agents   (Copilot subagents)
```

When you launch OpenCode (or Claude Code, Cursor, Copilot) from the
workspace root, these tools automatically discover and register the
four agents as available subagents. The main AI agent can then use
the `task` tool (or equivalent) to delegate work:

```
task("review the staged changes", subagent_type="reviewer")
```

If a tool's agents directory already exists as a regular directory
(user-created), the symlink is skipped to avoid overwriting user content.

### Agent delegation rules

- **Workspace-level agents** handle cross-repo coordination
- If a repo has its own `.agents/agents/`, workspace agents **defer to
  repo-level agents** for that repo's internal concerns
- Reviewer is **read-only on source code** — fixes are done by Developer
- Debugger is invoked for `fix/` type work items

## Typical Workspace Layout

```
project-workspace/
├── AGENTS.md                     # Merged incrementally on re-runs
├── README.md                     # Regenerated each run
├── fullstack.json                # Only persistent state
├── .opencode/
│   └── agents -> ../.agents/agents/   # OpenCode subagent symlink
├── .claude/
│   └── agents -> ../.agents/agents/   # Claude Code subagent symlink
├── .cursor/
│   └── agents -> ../.agents/agents/   # Cursor subagent symlink
├── .copilot/
│   └── agents -> ../.agents/agents/   # Copilot subagent symlink
├── .agents/
│   ├── agents/                   # Regenerated each run
│   │   ├── planner.md            # + YAML frontmatter for subagent tools
│   │   ├── developer.md
│   │   ├── reviewer.md
│   │   └── debugger.md
│   └── skills/                   # Preserved (user content)
├── central-docs/                 # Independent git repo (preserved)
│   ├── .git/
│   ├── AGENTS.md
│   ├── changes/
│   │   ├── feat/                 # Active feature work
│   │   ├── refactor/             # Active refactor work
│   │   ├── fix/                  # Active fix work
│   │   └── archive/              # Completed work (YYYY-MM-DD-<type>-<name>/)
├── scripts/                      # Preserved (user content)
├── web/                          # Independent repo
├── api/                          # Independent repo
└── ios/                          # Independent repo
```

## Requirements

- Python 3.10+
- `git` CLI
