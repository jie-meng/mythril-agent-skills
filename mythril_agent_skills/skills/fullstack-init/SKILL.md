---
name: fullstack-init
description: |
  Initialize or update a multi-repo fullstack workspace with unified AI context.
  Creates AGENTS.md (with auto-generated repo table), .gitignore, shared docs dir,
  .agents/skills/, and scripts/ — all version-controlled independently of sub-repos.
  Smart update: re-running refreshes the repo table without overwriting user-added
  content, custom agents, or skills. Trigger when user says 'init workspace',
  'initialize fullstack project', 'fullstack init', 'workspace init',
  'update workspace context', 'refresh workspace', 'init multi-repo',
  '初始化全栈项目', '初始化工作区', '更新工作区', '全栈初始化',
  '多仓库初始化', '刷新工作区上下文', 'set up monorepo workspace',
  'bootstrap multi-repo', 'create workspace AGENTS.md'.
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
| `.gitignore` | Tracks only workspace files, ignores sub-repos | Only updated if key patterns missing |
| `<docs-dir>/` | Shared cross-repo documentation (user-chosen name) | Created if missing, never overwritten |
| `<docs-dir>/AGENTS.md` | Doc management guidelines | Created if missing, never overwritten |
| `.agents/skills/` | Workspace-level custom skills | Created if missing, never overwritten |
| `scripts/` | Workspace-level automation | Created if missing, never overwritten |
| `README.md` | Human-readable overview | Created if missing, never overwritten |
| `.git` | Workspace-level git repo | Initialized if missing |
| `.fullstack-init.json` | Config persistence (docs dir name, etc.) | Updated when settings change |

## Shared Docs Directory — User-Configurable Name

The shared documentation directory name is **user-configurable**. It defaults to
`central-docs` but can be any name the user chooses.

### How the AI agent MUST handle this

**IMPORTANT**: Before running the script, follow this decision tree:

1. **Check if `.fullstack-init.json` exists** in the workspace root.
   - If YES → the docs dir is already configured. Read it and confirm with user.
     No need to ask again. Proceed to run the script (no `--docs-dir` needed).
   - If NO → this is a first-time init. Continue to step 2.

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

### How it works internally

- The chosen name is saved to `.fullstack-init.json` → `{"docs_dir": "xxx_documents"}`
- On re-run, the script reads `.fullstack-init.json` automatically
- `.gitignore` is generated with the actual directory name (not hardcoded)
- AGENTS.md references the actual directory name
- The docs directory is excluded from repo discovery

### Changing the docs dir name later

Pass `--docs-dir <new-name>` to update. The script will:
- Update `.fullstack-init.json`
- Update `.gitignore` with the new name
- Create the new directory if needed (old one is NOT deleted/renamed)

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
- **Reads** `.fullstack-init.json` for the saved docs dir name
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

### Specify a different root

```bash
python3 SKILL_PATH/scripts/workspace_init.py /path/to/workspace
```

## How the Repo Table Works

The auto-generated table is wrapped in HTML comment markers:

```markdown
<!-- fullstack-init:repos-table:start -->

| # | Repository | Role | Tech Stack | Description |
|---|-----------|------|-----------|-------------|
| 1 | [web](./web/) | Web Frontend | TypeScript | React dashboard app |
| 2 | [api](./api/) | Backend / API | Python | FastAPI service |
| 3 | [ios](./ios/) | iOS | iOS (Swift/ObjC) | Native iOS client |

<!-- fullstack-init:repos-table:end -->
```

On re-run, **only content between these markers is replaced**. Everything
above and below — including custom sections you've added — stays intact.

## Smart Merge Guarantees

- **AGENTS.md user content**: Any section you add (## Conventions, ## Team Notes,
  etc.) is preserved across re-runs. Only the marked repo table is refreshed.
- **`.agents/skills/`**: Your custom workspace skills are never touched.
- **Docs directory**: Your shared docs are never touched.
- **`scripts/`**: Your automation scripts are never touched.
- **`.gitignore`**: Only updated if missing critical workspace patterns.
- **`.fullstack-init.json`**: Preserves all saved settings; only changed fields
  are updated.

## Typical Workspace Layout After Init

```
my-project/                    # Workspace root (its own git repo)
├── AGENTS.md                  # AI context with repo table (auto-managed)
├── README.md                  # Project overview
├── .gitignore                 # Tracks workspace files only
├── .fullstack-init.json       # Config: {"docs_dir": "central-docs"}
├── .agents/
│   └── skills/                # Custom workspace-level skills
├── central-docs/              # Shared docs (name is user-configurable)
│   ├── AGENTS.md              # Doc management guidelines
│   ├── architecture.md        # Cross-repo architecture docs
│   └── api-contracts/         # Shared API schemas
├── scripts/
│   └── setup-all.sh           # Workspace automation
├── web/                       # ← Sub-repo (own .git, ignored by workspace)
├── api/                       # ← Sub-repo
├── ios/                       # ← Sub-repo
├── android/                   # ← Sub-repo
└── shared-lib/                # ← Sub-repo
```

## Requirements

- Python 3.10+
- `git` CLI (for `git init` on first run)
