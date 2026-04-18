# Fullstack Init — Design Document

Design document for the `fullstack-init` skill. Covers requirements, solution
architecture, key decisions, and current status.

**Last updated**: 2025-04-18

---

## Problem Statement

Developers working on fullstack projects often manage multiple repos (web, api,
ios, android, shared-lib, …) as sibling directories under a single root. They
open their AI coding assistant at this root so it can access all repos at once.

Pain points:

1. No unified AGENTS.md at the root — the AI has no cross-repo context.
2. No workspace-level `.gitignore` — workspace infrastructure files (AGENTS.md,
   scripts, shared docs) aren't version-controlled because the root isn't a git
   repo, or the sub-repos' git history conflicts.
3. No shared documentation directory — cross-cutting docs have no canonical home.
4. When new repos are added, the context must be manually updated.
5. If the AI initializes infrastructure, re-running it risks overwriting
   user-added content (custom agents, skills, notes, conventions).

## Requirements

### R1 — One-command init

Running a single script at the workspace root should bootstrap all
infrastructure:

- `AGENTS.md` with auto-generated repo table
- `.gitignore` that tracks only workspace-level files
- Shared docs directory with its own `AGENTS.md`
- `.agents/skills/` for workspace-level custom skills
- `scripts/` for workspace-level automation
- `README.md` for humans
- `.git` (init if needed)

### R2 — Idempotent re-run (smart update)

Re-running after adding new repos should:

- Refresh the repo table in AGENTS.md
- Preserve all user-added content in AGENTS.md (custom sections, notes)
- Preserve all files in `.agents/`, docs dir, `scripts/`
- Not overwrite `README.md`, docs dir `AGENTS.md`
- Not duplicate or corrupt existing infrastructure

### R3 — User-configurable docs directory name

The shared documentation directory should not be hardcoded to `central-docs`.
Users may already have a directory like `project_documents`, `shared-docs`, etc.

- First run: AI agent asks the user for the docs dir name (or accepts a default)
- The choice is persisted so re-runs don't need to ask again
- `.gitignore`, `AGENTS.md`, and all generated content adapt to the actual name

### R4 — Repo analysis

The script should automatically analyze each sub-repo by:

- Reading `README.md` and `AGENTS.md` for descriptions
- Detecting tech stack from config files (package.json, Podfile, build.gradle, …)
- Inferring role from directory name (web → Frontend, api → Backend, …)

### R5 — No external dependencies

Python 3.10+ stdlib only. No pip packages required.

## Solution

### Architecture: single idempotent script

A single Python script (`workspace_init.py`) handles both init and update. No
separate "update" command — running it again always does the right thing. This is
simpler to remember and teach to the AI agent.

### Config persistence: `.fullstack-init.json`

User choices (currently just `docs_dir`) are saved to `.fullstack-init.json` at
the workspace root. This solves the "how does re-run know the docs dir name"
problem without magic detection:

```json
{
  "docs_dir": "project_documents"
}
```

Priority for resolving docs dir:
1. CLI argument `--docs-dir` (explicit override)
2. Saved value in `.fullstack-init.json` (automatic on re-run)
3. Default `"central-docs"` (first run, nothing specified)

### Repo table markers

The auto-generated repo table in AGENTS.md is wrapped in HTML comment markers:

```markdown
<!-- fullstack-init:repos-table:start -->
| # | Repository | Role | Tech Stack | Description |
...
<!-- fullstack-init:repos-table:end -->
```

On re-run, only content between markers is replaced. All other sections
(user-written conventions, notes, team guidelines) are preserved.

### Dynamic `.gitignore`

The `.gitignore` is generated with the actual docs dir name, not hardcoded.
The pattern is "ignore everything, then explicitly un-ignore workspace
infrastructure":

```gitignore
*                          # ignore everything (sub-repos have own git)
!AGENTS.md                 # workspace AI context
!.fullstack-init.json      # config persistence
!.agents/                  # custom skills
!<docs-dir>/               # shared docs (actual name)
!scripts/                  # automation
...
```

### AI agent interaction flow (docs dir)

Defined in SKILL.md so the AI knows exactly how to handle the docs dir:

1. `.fullstack-init.json` exists? → already configured, skip asking
2. User specified in prompt? → use that
3. Neither? → **must ask the user** (don't silently default)

### Infrastructure dir exclusion

The docs dir name is added to the "infrastructure directories" set so it's
excluded from repo discovery. This prevents the docs dir from appearing in the
repo table even if it contains a `.git/`.

## File Inventory

```
mythril_agent_skills/skills/fullstack-init/
├── SKILL.md                     # Skill definition (frontmatter + instructions)
└── scripts/
    └── workspace_init.py        # Main script (stdlib-only, ~400 lines)

tests/skills/
└── test_fullstack_init.py       # 71 unit + integration tests

plugins/fullstack-init/
└── skills/
    └── fullstack-init -> ../../../mythril_agent_skills/skills/fullstack-init
```

Updated files:
- `pyproject.toml` — added extraPaths entry
- `.claude-plugin/marketplace.json` — added plugin entry

## Key Functions

| Function | Pure? | Purpose |
|----------|-------|---------|
| `load_config` / `save_config` | Yes/Side-effect | Read/write `.fullstack-init.json` |
| `resolve_docs_dir` | Yes | Priority resolution: CLI > config > default |
| `discover_repos` | Yes | Find git repos, exclude infrastructure dirs |
| `detect_tech_stack` | Yes | Infer tech from config files |
| `detect_repo_role` | Yes | Infer role from directory name |
| `_extract_first_description` | Yes | Parse first paragraph from README.md |
| `build_repos_table` | Yes | Generate Markdown table with markers |
| `merge_repos_table` | Yes | Replace table preserving surrounding content |
| `generate_gitignore` | Yes | Generate .gitignore with actual docs dir name |
| `needs_gitignore_update` | Yes | Check if .gitignore has required patterns |
| `generate_docs_agents_md` | Yes | Generate AGENTS.md for docs directory |
| `generate_fresh_agents_md` | Yes | Generate full AGENTS.md for new workspace |
| `bootstrap_workspace` | Side-effect | Orchestrator: calls all of the above |

## Current Status

### Done

- [x] R1 — One-command init: `workspace_init.py` creates all infrastructure
- [x] R2 — Idempotent re-run: marker-based merge preserves user content
- [x] R3 — User-configurable docs dir: `--docs-dir` + `.fullstack-init.json`
- [x] R4 — Repo analysis: tech stack detection, role inference, description extraction
- [x] R5 — Stdlib-only: zero external dependencies
- [x] Plugin wrapper + marketplace.json entry
- [x] 71 tests (unit + integration), all passing
- [x] Description validation (689 chars, under 1024 limit)

### Planned / Ideas

- [ ] Deep analysis mode: when README/AGENTS.md are insufficient, scan project
  structure (src/ layout, entry points, routes) for richer descriptions
- [ ] AGENTS.md template customization: let users provide a Jinja-like template
  for the generated AGENTS.md structure
- [ ] Workspace-level `skills-check`: verify cross-repo dependencies (e.g.,
  API contract compatibility, shared type definitions)
- [ ] Interactive TUI mode: curses-based multi-select for choosing which repos
  to include in the table (useful when some repos are archived/deprecated)
- [ ] Git hooks: auto-run `fullstack-init` on workspace-level commits to keep
  the repo table fresh

## Changelog

### 2025-04-18 — Initial implementation

- Created `fullstack-init` skill with `workspace_init.py`
- Repo discovery, tech stack detection, role inference
- AGENTS.md generation with marker-based smart merge
- .gitignore generation (ignore-all + explicit un-ignore pattern)
- central-docs/ bootstrapping with AGENTS.md template
- Config persistence via `.fullstack-init.json`
- User-configurable docs directory name (`--docs-dir`)
- `--dry-run` and `--json` output modes
- 71 unit + integration tests
- Plugin wrapper and marketplace.json entry
