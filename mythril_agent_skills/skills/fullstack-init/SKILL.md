---
name: fullstack-init
description: >
  Initializes or updates a multi-repo fullstack workspace: discovers repos,
  generates AGENTS.md, and creates the docs directory and workspace agents.
  Run it first in a new workspace, or again after repos are added or removed.
  Triggers: "fullstack init", "fullstack setup", "全栈初始化", "初始化全栈工作区", "全栈
  init".
license: Apache-2.0
---

# Fullstack Workspace Initializer

Initialize or update a multi-repo fullstack workspace so AI coding assistants
have full cross-repo context. Designed for projects where web, api, ios,
android, and other repos live as sibling directories under one root.

## Design Philosophy

**Re-run it whenever repos, the skills, or the docs change — it never
loses your edits and still brings template updates in.** Every generated
unit is refreshed three-way: what is on disk, what this script generated
last time (the baseline, `.agents/.fullstack-init-baseline.json`), and what
it generates now.

| Unit | How it is refreshed |
|------|---------------------|
| `AGENTS.md` H2 sections | Three-way per section. Skill-owned sections (*Directory Structure*, *Docs-Code Lockstep*, *Documentation Diagrams*) always take the template |
| *Workspace Conventions* bullets | Three-way per bullet; shipped bullets (*Repo Skills*, *Knowledge Graph*) always take the template; your own bullets are never touched |
| *Repositories* table | Row by row: rows follow the current repo set, an untouched row refreshes its detected role / stack / description, an edited row keeps your cells, notes around the table stay |
| `.agents/agents/*.md` | Three-way per file |
| `README.md` | Three-way as a whole file; language saved in `fullstack.json`. With no baseline an existing README is kept and the template parked (`Review once`) |
| `<docs-dir>/AGENTS.md` | Three-way per section; with no baseline it is treated as hand-written (nothing is added) |
| `fullstack.json`, `<docs-dir>/` content, `scripts/`, `.agents/skills/` | Never overwritten; directories created if missing |

Three-way outcomes, as the report prints them:

| Disk vs baseline | Template vs baseline | Result | Report |
|---|---|---|---|
| untouched | changed | takes the new template | `Refreshed` |
| edited | unchanged | your text stays | `Kept your edits` |
| edited | changed | your text stays; new template written to `.agents/init-pending/<unit>` | `Needs a by-hand merge` |
| no baseline yet, differs | — | your text stays; template parked in `init-pending/` | `Review once` |
| untouched | section dropped by the template | removed | `Refreshed` |
| you deleted it | still in template | stays deleted | — |

User-only sections and bullets always stay, in your order; new template
sections are inserted next to their template neighbour. `--force`
overwrites every generated unit with the template (your edits are lost).

## Handling Already-Initialized Workspaces

When `fullstack.json` **and** `AGENTS.md` both exist, just run the script
— no flags needed (do not pass `--force` unless the user asks to discard
their edits). Then read the report:

1. **`Needs a by-hand merge` / `Review once`** — for each listed unit, diff
   the file on disk against its template in `.agents/init-pending/`.
   Explain the template change in plain words, propose a merged text that
   keeps the user's intent, and apply it **only after the user confirms**.
   Then delete that pending file. Never resolve one silently.

   **Keeping old content is not the same as keeping old rules.** These
   files instruct every agent in the workspace, so a merged section must
   not tell an agent to do what the current skills forbid. When you keep
   something the template dropped because the workspace still has data in
   that shape, rewrite it as **history**, not as an instruction. Example:
   legacy `changes/archive/*-spike-*/` directories are kept as a
   "read-only legacy records" note, never as a *Spike* row in the category
   table, because today a spike runs as `fullstack-propose` deep mode inside
   the work item's `analysis.md`, and a category row would make an agent
   create new spike directories.
2. **`Review once`** appears on the first run after the baseline was
   introduced: the script cannot tell whether a difference is the user's
   edit or a template update the workspace never received. Ask; old
   template text (e.g. a *Work Tracking* section describing a layout that
   no longer exists) is usually the second case.
3. Pending files left from an earlier run are listed on every run until
   they are merged and deleted.

## Docs Directory — Independent Git Repo

The shared docs directory is an **independent git repository**, NOT managed
by the workspace git. It does NOT use feature branches — work tracking docs
are committed directly to its main branch.

The name is configurable (defaults to `central-docs`) and stored in
`fullstack.json`.

### Choosing the docs dir name

1. **Check if `fullstack.json` exists** — if YES, docs dir is already
   configured. No need to ask. Run the script.
2. **Check if user specified a name** in their prompt — if YES, pass
   `--docs-dir <name>`.
3. **Otherwise, ask the user** — the name is hard to change later, so do not silently use the default:
   > What should I name the shared docs directory? (default: `central-docs`)

The name must be a single plain directory name (no `/`, `\`, `..`, or
leading dot). The script refuses — exit 1, nothing written — when:

- `--docs-dir` differs from the `docs_dir` saved in `fullstack.json` while
  that directory still exists. Renaming is manual: move the directory,
  edit `docs_dir`, re-run without `--docs-dir`.
- `fullstack.json` is not valid JSON. Show the error to the user and fix
  the file with them; never delete it to make the run pass.

## Usage

`SKILL_PATH` is this skill's installed directory (the folder holding this SKILL.md); run scripts from the user's working directory, not from inside it.

```bash
python3 SKILL_PATH/scripts/workspace_init.py                         # first run
python3 SKILL_PATH/scripts/workspace_init.py --docs-dir my-docs      # custom docs dir
python3 SKILL_PATH/scripts/workspace_init.py --lang zh               # Chinese README
python3 SKILL_PATH/scripts/workspace_init.py --github                # repos are on GitHub
python3 SKILL_PATH/scripts/workspace_init.py --no-github             # repos are NOT on GitHub
python3 SKILL_PATH/scripts/workspace_init.py                         # re-run: three-way refresh
python3 SKILL_PATH/scripts/workspace_init.py --force                 # re-run: overwrite, discard edits
python3 SKILL_PATH/scripts/workspace_init.py --dry-run               # preview only
python3 SKILL_PATH/scripts/workspace_init.py --json                  # JSON output
```

### Choosing the GitHub repos setting

1. **Check if `fullstack.json` exists and has `github_repos` set** — if YES,
   the setting is already configured. No need to ask. Run the script.
2. **Check if user specified it** in their prompt (e.g., "repos are on GitHub",
   "仓库在GitHub上") — if YES, pass `--github`.
3. **Otherwise, ask the user** — it decides whether later skills create PRs, so do not silently use the default:
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

**Choosing the language**: the language is saved to
`fullstack.json` (`readme_lang`), so a re-run in another conversation
language does not flip the README.

1. **First run** (no `fullstack.json`): any Chinese character in the
   user's prompt → `--lang zh`; otherwise `--lang en`.
2. **Re-run**: omit `--lang` — the saved language is used (a workspace
   that predates the setting keeps its current README's language). Pass
   it only when the user asks to switch.

## Workspace Agents

Five subagents are generated in `.agents/agents/` on every run. Each file
contains YAML frontmatter (`name`, `description`, `mode: subagent`,
`permission` with the `edit` policy only) compatible with OpenCode and
Claude Code, followed by role-specific instructions. Tools that support
native subagent discovery (OpenCode, Claude Code, Cursor, Copilot, pi) receive symlinks so their
subagent systems automatically discover these agents:

| Agent | File | Role | Permissions |
|-------|------|------|-------------|
| Planner | `planner.md` | Analyzes requirements and architecture, writes `analysis.md`/`plan.md` directly into the work directory (full-tier items), returns a short summary | writes the work directory only; read-only on code |
| Plan Reviewer | `plan-reviewer.md` | Audits the written plan against the original requirements before implementation (coverage, contracts, referenced-code existence, testability), returns findings for `review.md` | read-only on code |
| Developer | `developer.md` | Implements code — the only agent that writes production code; stages changes, orchestrator commits | full access |
| Code Reviewer | `code-reviewer.md` | Reviews with falsification mindset, returns findings for `review.md` | read-only on code |
| Debugger | `debugger.md` | Root-cause analysis for fix work type; temporary debug edits allowed, never commits | scoped debug edits |

These are refreshed three-way on every run: an untouched file takes the
new template, a file you edited is kept, and when both changed the new
template waits in `.agents/init-pending/agents/` for a by-hand merge.
Agent files written before the baseline existed count as untouched,
because earlier releases always regenerated them.

### How AI tools discover these agents

On every run, the script creates relative symlinks from tool-specific
agent directories to `.agents/agents/`:

```
.opencode/agents -> ../.agents/agents   (OpenCode subagents)
.claude/agents   -> ../.agents/agents   (Claude Code subagents)
.cursor/agents   -> ../.agents/agents   (Cursor subagents)
.copilot/agents  -> ../.agents/agents   (Copilot subagents)
```

pi (pi-subagents) reads `.agents/agents/` directly — no symlink needed, and
its call shape is `subagent({ agent: "code-reviewer", task: "..." })`.

When you launch OpenCode (or Claude Code, Cursor, Copilot, pi) from the
workspace root, these tools automatically discover and register the
five agents as available subagents. The main AI agent can then use
the `task` tool (or equivalent) to delegate work:

```
task("review the staged changes", subagent_type="code-reviewer")
```

**One portability rule for these files**: declare only the `edit`
permission. A `bash` key is OpenCode-only and pi-subagents *rejects* the
whole agent file when it appears (`permissions.bash is unsupported; ...
leaves bash policy to pi-guard`) — the agent then silently does not exist,
while the skills keep instructing delegation to it. Shell policy is
owned by the host tool.

If a tool's agents directory already exists as a regular directory
(user-created), the symlink is skipped to avoid overwriting user content.

### Agent delegation rules

- **Workspace-level agents** handle cross-repo coordination
- If a repo has its own `.agents/agents/`, workspace agents **defer to
  repo-level agents** for that repo's internal concerns
- Code Reviewer is **read-only on source code** — fixes are done by Developer
- Plan Reviewer is **read-only too**, and audits plans instead of diffs:
  it runs during propose (before code exists), never during apply, and
  never rewrites the plan — the plan's author (Planner, or the orchestrator
  on a lean item) revises
- Debugger debugs hands-on with **temporary, uncommitted**
  instrumentation and returns root-cause analysis + a fix spec; it
  never commits — Developer implements and ships the fix
- Debugger is invoked for `fix/` type work items (propose) and as
  escalation for non-obvious failures during apply

## Typical Workspace Layout

```
project-workspace/
├── AGENTS.md                     # Refreshed three-way on re-runs
├── README.md                     # Refreshed three-way (language saved)
├── fullstack.json                # docs_dir, github_repos, readme_lang
├── .opencode/
│   └── agents -> ../.agents/agents/   # OpenCode subagent symlink
├── .claude/
│   └── agents -> ../.agents/agents/   # Claude Code subagent symlink
├── .cursor/
│   └── agents -> ../.agents/agents/   # Cursor subagent symlink
├── .copilot/
│   └── agents -> ../.agents/agents/   # Copilot subagent symlink
├── .agents/
│   ├── .fullstack-init-baseline.json  # What the last run generated (three-way base)
│   ├── init-pending/             # Templates awaiting a by-hand merge (if any)
│   ├── agents/                   # Refreshed three-way
│   │   ├── planner.md            # + YAML frontmatter for subagent tools
│   │   ├── plan-reviewer.md
│   │   ├── developer.md
│   │   ├── code-reviewer.md
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
│   ├── issues/                   # Issue records (pre-work-item)
│   │   └── archive/              # Closed issues (name unchanged)
├── scripts/                      # Preserved (user content)
├── web/                          # Independent repo
├── api/                          # Independent repo
└── ios/                          # Independent repo
```

## Requirements

- Python 3.10+
- `git` CLI
