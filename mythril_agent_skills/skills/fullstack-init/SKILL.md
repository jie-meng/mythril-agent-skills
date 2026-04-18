---
name: fullstack-init
description: |
  Initialize or update a multi-repo fullstack workspace. Every run is a full
  refresh — AGENTS.md, .gitignore, README.md, and agent templates are
  regenerated. Only fullstack.json (config) and user directories (docs,
  scripts, .agents/skills) are preserved.
license: Apache-2.0
---

# Fullstack Workspace Initializer

Initialize or update a multi-repo fullstack workspace so AI coding assistants
have full cross-repo context. Designed for projects where web, api, ios,
android, and other repos live as sibling directories under one root.

## Design Philosophy

**Every run is a full refresh.** The script regenerates all scaffolding files
from scratch — no merge logic, no migration, no stale state. This makes it
safe to re-run at any time: after adding repos, after upgrading the skill,
or just to fix a broken workspace.

| Category | What happens on every run |
|----------|--------------------------|
| **Regenerated** | `AGENTS.md`, `README.md`, `.gitignore`, `.agents/agents/*.md` |
| **Preserved** | `fullstack.json`, `<docs-dir>/`, `scripts/`, `.agents/skills/` |
| **Create-only** | `<docs-dir>/` + git init, `scripts/`, `.agents/skills/` — created if missing, never touched if present |

## What It Does

1. **Discovers** all git repos in immediate subdirectories
2. **Analyzes** each repo's README.md, AGENTS.md, tech stack, and role
3. **Regenerates** workspace-level infrastructure from scratch
4. **Preserves** user content in docs dir, scripts/, and .agents/skills/

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
python3 SKILL_PATH/scripts/workspace_init.py                         # re-run: safe refresh
python3 SKILL_PATH/scripts/workspace_init.py --dry-run               # preview only
python3 SKILL_PATH/scripts/workspace_init.py --json                  # JSON output
```

## Workspace Agents

Four agents are generated in `.agents/agents/` on every run:

| Agent | File | Role |
|-------|------|------|
| Planner | `planner.md` | Analyzes requirements, writes `plan.md` |
| Developer | `developer.md` | Implements code — the only agent that writes production code |
| Reviewer | `reviewer.md` | Reviews with falsification mindset, writes `review.md` |
| Debugger | `debugger.md` | Root-cause analysis for fix work type |

These are regenerated on every run. Any customization will be overwritten.
For persistent custom agents, use `.agents/skills/` or repo-level agents.

### Agent delegation rules

- **Workspace-level agents** handle cross-repo coordination
- If a repo has its own `.agents/agents/`, workspace agents **defer to
  repo-level agents** for that repo's internal concerns
- Reviewer is **read-only on source code** — fixes are done by Developer
- Debugger is invoked for `fix/` type work items

## Typical Workspace Layout

```
project-workspace/
├── AGENTS.md                     # Regenerated each run
├── README.md                     # Regenerated each run
├── .gitignore                    # Regenerated each run
├── fullstack.json                # Only persistent state
├── .agents/
│   ├── agents/                   # Regenerated each run
│   │   ├── planner.md
│   │   ├── developer.md
│   │   ├── reviewer.md
│   │   └── debugger.md
│   └── skills/                   # Preserved (user content)
├── central-docs/                 # Independent git repo (preserved)
│   ├── .git/
│   ├── AGENTS.md
│   ├── feat/
│   ├── refactor/
│   └── fix/
├── scripts/                      # Preserved (user content)
├── web/                          # Independent repo
├── api/                          # Independent repo
└── ios/                          # Independent repo
```

## Requirements

- Python 3.10+
- `git` CLI
