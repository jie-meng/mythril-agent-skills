---
name: fullstack-init
description: |
  Initialize or update a multi-repo fullstack workspace. Creates AGENTS.md
  with auto-generated repo table, docs dir (independent git repo), four
  workspace agents (planner/dev/reviewer/debugger), and work tracking dirs.
  Re-running refreshes the repo table without overwriting user content.
license: Apache-2.0
---

# Fullstack Workspace Initializer

Initialize or update a multi-repo fullstack workspace so AI coding assistants
have full cross-repo context. Designed for projects where web, api, ios,
android, and other repos live as sibling directories under one root.

## What It Does

1. **Discovers** all git repos in immediate subdirectories
2. **Analyzes** each repo's README.md, AGENTS.md, tech stack, and role
3. **Creates or updates** workspace-level infrastructure:

| File / Directory | Purpose | On re-run |
|-----------------|---------|-----------|
| `AGENTS.md` | AI guidelines with auto-generated repo table | Table refreshed, user content preserved |
| `.gitignore` | Ignores all subdirs except workspace infra | Regenerated each run to catch new/removed dirs |
| `<docs-dir>/` | Shared docs (**independent git repo**) | Created + git init if missing, never overwritten |
| `<docs-dir>/AGENTS.md` | Doc management guidelines | Created if missing, never overwritten |
| `<docs-dir>/feat/` | Feature work tracking | Created if missing |
| `<docs-dir>/refactor/` | Refactor work tracking | Created if missing |
| `<docs-dir>/fix/` | Fix work tracking | Created if missing |
| `.agents/agents/` | Planner, dev, reviewer, debugger agents | Created if missing, never overwritten |
| `.agents/skills/` | Workspace-level custom skills | Created if missing, never overwritten |
| `scripts/` | Workspace-level automation | Created if missing, never overwritten |
| `README.md` | Human-readable overview | Created if missing, never overwritten |
| `.git` | Workspace-level git repo | Initialized if missing |
| `fullstack.json` | Config persistence (docs dir name, etc.) | Updated when settings change |

## Shared Docs Directory — Independent Git Repo

The shared documentation directory is an **independent git repository**,
NOT managed by the workspace-level git. This means:

- It has its own `.git/` directory (created by the init script)
- The workspace `.gitignore` does NOT track it
- It does NOT use feature branches — work tracking docs are committed
  directly to its main branch
- Each code repo has its own feature branches, but docs are always on main

The directory name is **user-configurable** (defaults to `central-docs`).

### How the AI agent MUST handle this

**IMPORTANT**: Before running the script, follow this decision tree:

1. **Check if `fullstack.json` exists** in the workspace root.
   - If YES → the docs dir is already configured. Read it and confirm with user.
     No need to ask again. Proceed to run the script (no `--docs-dir` needed).
   - If NO → check for legacy `.fullstack-init.json` (auto-migrated). Continue to step 2.

2. **Check if user specified a docs directory** in their prompt
   (e.g. "use project_documents as the docs dir", "文档目录用 xxx_documents").
   - If YES → pass it via `--docs-dir <name>`. Done.
   - If NO → continue to step 3.

3. **Ask the user** (MANDATORY — do NOT skip this and silently use the default):
   > Do you have an existing directory for shared cross-repo documentation?
   > If so, tell me its name (e.g. `project_documents`, `shared-docs`).
   > If not, I'll create one called `central-docs`.
   - If user provides a name → verify the directory exists, then pass `--docs-dir <name>`.
   - If user says no / create one → run without `--docs-dir` (defaults to `central-docs`).

### Changing the docs dir name later

Pass `--docs-dir <new-name>` to update. The script will:
- Update `fullstack.json`
- Create the new directory + git init if needed
- Old directory is NOT deleted/renamed

## Usage

### First-time initialization

```bash
python3 SKILL_PATH/scripts/workspace_init.py
python3 SKILL_PATH/scripts/workspace_init.py --docs-dir project_documents
```

### Update after adding new repos

Simply re-run the same command (no need to re-specify `--docs-dir`):

```bash
python3 SKILL_PATH/scripts/workspace_init.py
```

The script:
- **Reads** `fullstack.json` for the saved docs dir name
- **Preserves** all user-added sections in AGENTS.md
- **Refreshes** only the auto-generated repo table between marker comments
- **Preserves** all files in `.agents/`, docs dir, and `scripts/`

### Preview changes

```bash
python3 SKILL_PATH/scripts/workspace_init.py --dry-run
```

### JSON output (for scripting)

```bash
python3 SKILL_PATH/scripts/workspace_init.py --json
```

## Workspace Agents

The init script creates four agent definitions in `.agents/agents/`:

| Agent | File | Role |
|-------|------|------|
| Planner | `planner.md` | Analyzes requirements, designs solutions, writes `plan.md` |
| Dev | `dev.md` | Implements code across repos — the only agent that writes production code |
| Reviewer | `reviewer.md` | Reviews changes with falsification mindset, records findings |
| Debugger | `debugger.md` | Root-cause analysis specialist for fix work type |

### Agent delegation rules

- **Workspace-level agents** handle cross-repo coordination
- If a specific repo has its own `.agents/agents/` directory, the
  workspace agents should **defer to repo-level agents** for that
  repo's internal concerns
- The reviewer is **read-only on source code** — findings go
  in `review.md`, fixes are done by the dev agent
- The debugger is invoked for `fix/` type work items

## Smart Merge Guarantees

- **AGENTS.md user content**: Any section you add is preserved across
  re-runs. Only the marked repo table is refreshed.
- **`.agents/`**: Your custom agents and skills are never touched.
- **Docs directory**: Your shared docs are never touched.
- **`scripts/`**: Your automation scripts are never touched.
- **`.gitignore`**: Only updated if missing critical workspace patterns.
- **`fullstack.json`**: Preserves all saved settings; only changed fields
  are updated.

## Typical Workspace Layout After Init

```
project-workspace/                # Workspace root (its own git repo)
├── AGENTS.md                     # AI context with repo table (auto-managed)
├── README.md                     # Project overview
├── .gitignore                    # Ignores all subdirs except .agents/ and scripts/
├── fullstack.json               # Config: {"docs_dir": "central-docs"}
├── .agents/
│   ├── agents/                   # Workspace-level sub-agents
│   │   ├── planner.md            # Requirements & solution design
│   │   ├── dev.md                # Implementation agent
│   │   ├── reviewer.md           # Independent validation agent
│   │   └── debugger.md           # Root-cause analysis agent
│   └── skills/                   # Custom workspace-level skills
├── central-docs/                 # Shared docs (INDEPENDENT git repo)
│   ├── .git/                     # Its own version control
│   ├── AGENTS.md                 # Doc management guidelines
│   ├── feat/                     # Feature work tracking
│   │   └── add-dark-mode/        # Example feature
│   │       ├── plan.md
│   │       ├── progress.md
│   │       └── review.md
│   ├── refactor/                 # Refactor work tracking
│   └── fix/                      # Fix work tracking
├── scripts/
│   └── setup-all.sh              # Workspace automation
├── web/                          # ← Independent repo (own .git)
├── api/                          # ← Independent repo
├── ios/                          # ← Independent repo
└── android/                      # ← Independent repo
```

## Requirements

- Python 3.10+
- `git` CLI (for `git init` on workspace and docs dir)
