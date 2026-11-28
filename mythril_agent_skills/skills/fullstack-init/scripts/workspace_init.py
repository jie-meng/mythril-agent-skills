#!/usr/bin/env python3
"""Initialize or update a multi-repo fullstack workspace.

Scans a root directory for git repositories, analyzes their README.md and
AGENTS.md files, and generates workspace-level infrastructure: AGENTS.md,
agent templates, and shared docs directory.

Design: every re-run is a three-way refresh. Each managed unit (an
AGENTS.md section, a Workspace Conventions bullet, a repos-table row, an
agent file, README.md, the docs AGENTS.md) is compared across three
versions — what is on disk, what this script generated last time (the
baseline in `.agents/.fullstack-init-baseline.json`), and what it
generates now. A unit the user never touched takes the new template; a
unit the user edited is kept; a unit both sides changed is kept and the new
template is written to `.agents/init-pending/` for a by-hand merge. The
docs directory content and user directories (scripts/, .agents/skills/)
are created if missing but never overwritten.

The workspace root is NOT a git repo — no .gitignore, no .git. This is
intentional: all major AI agents (Cursor, Claude Code, Copilot, Codex,
Gemini CLI, etc.) respect .gitignore and hide ignored files from their
search/indexing tools. Since the workspace contains independent repos as
subdirectories, a .gitignore that hides them would make their files
invisible to AI agents. The docs directory is the only workspace-managed
git repo.

Uses only Python 3.10+ standard library (zero dependencies).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_FILENAME = "fullstack.json"
LEGACY_CONFIG_FILENAME = ".fullstack-init.json"

DEFAULT_DOCS_DIR = "central-docs"

INFRA_DIRS = {
    ".agents",
    "scripts",
    "node_modules",
    "__pycache__",
}

# Agent manifest lives beside the generated agents; subagent discovery
# globs `*.md`, so the dot-file stays invisible to it.
AGENT_MANIFEST_NAME = ".generated-agents.json"
BASELINE_FILENAME = ".fullstack-init-baseline.json"
PENDING_DIRNAME = "init-pending"

# Agent names this skill generated in releases that predate the manifest.
# Workspaces created then have the files on disk with no manifest to
# consult, so a rename (reviewer → code-reviewer) needs this list to know
# what it is allowed to prune.
LEGACY_GENERATED_AGENTS = ("planner", "developer", "reviewer", "debugger")


# ---------------------------------------------------------------------------
# Config persistence (fullstack.json is the ONLY persistent state)
# ---------------------------------------------------------------------------

class WorkspaceConfigError(Exception):
    """The workspace config cannot be trusted; the run must stop."""


def _read_config_file(path: Path) -> dict:
    """Parse one config file; raise WorkspaceConfigError when it is unusable.

    A broken `fullstack.json` must stop the run: falling back to defaults
    would silently switch the docs directory, re-classify the real docs
    repo as a code repo, and overwrite the user's config.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise WorkspaceConfigError(
            f"{path.name} is not valid JSON ({exc}). Fix or remove it, then "
            "re-run — refusing to fall back to defaults."
        ) from exc
    if not isinstance(data, dict):
        raise WorkspaceConfigError(
            f"{path.name} must hold a JSON object, got {type(data).__name__}."
        )
    return data


def load_config(root: Path) -> dict[str, str]:
    """Load workspace config from fullstack.json (with legacy fallback).

    Raises WorkspaceConfigError when the file exists but cannot be parsed.
    """
    config_path = root / CONFIG_FILENAME
    if config_path.exists():
        return _read_config_file(config_path)
    legacy_path = root / LEGACY_CONFIG_FILENAME
    if legacy_path.exists():
        return _read_config_file(legacy_path)
    return {}


def save_config(root: Path, config: dict[str, str]) -> None:
    """Save workspace config to fullstack.json (removes legacy file if present)."""
    config_path = root / CONFIG_FILENAME
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    legacy_path = root / LEGACY_CONFIG_FILENAME
    if legacy_path.exists():
        legacy_path.unlink()


def validate_docs_dir_name(name: str) -> str:
    """Return `name` if it is a plain directory name under the root.

    The docs dir is joined onto the workspace root and excluded from repo
    discovery by name, so a path (`a/b`, `../x`, `/abs`) or a dot-name
    would create directories outside the workspace or slip past discovery.
    """
    if (
        not name
        or name in (".", "..")
        or name.startswith(".")
        or "/" in name
        or "\\" in name
        or Path(name).is_absolute()
    ):
        raise WorkspaceConfigError(
            f"Invalid docs directory name {name!r}: use a single plain "
            "directory name such as 'central-docs' (no path separators, "
            "no leading dot)."
        )
    return name


def resolve_docs_dir(root: Path, cli_docs_dir: str | None) -> str:
    """Determine docs dir: CLI arg > saved config > default.

    A CLI name that differs from the saved one is refused while the saved
    directory still exists: re-pointing the config would leave the real
    docs repo behind as a "code repo" and start an empty one.
    """
    config = load_config(root)
    saved = config.get("docs_dir")
    if cli_docs_dir:
        name = validate_docs_dir_name(cli_docs_dir)
        if saved and saved != name and (root / str(saved)).exists():
            raise WorkspaceConfigError(
                f"--docs-dir {name!r} differs from the configured docs "
                f"directory {saved!r}, which still exists. To rename it, move "
                f"the directory and update 'docs_dir' in {CONFIG_FILENAME} by "
                "hand, then re-run without --docs-dir."
            )
        return name
    if saved:
        return validate_docs_dir_name(str(saved))
    return DEFAULT_DOCS_DIR


def resolve_github_repos(root: Path, cli_github: bool | None) -> bool:
    """Determine if repos use GitHub: CLI arg > saved config > False."""
    if cli_github is not None:
        return cli_github
    config = load_config(root)
    return bool(config.get("github_repos", False))


# ---------------------------------------------------------------------------
# Repo discovery and analysis
# ---------------------------------------------------------------------------

def is_git_repo(path: Path) -> bool:
    """Check if a directory is a git repository."""
    return (path / ".git").exists()


def discover_repos(root: Path, docs_dir: str) -> list[Path]:
    """Find all immediate subdirectory git repos under root."""
    exclude = INFRA_DIRS | {docs_dir}
    repos = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in exclude:
            continue
        if is_git_repo(entry):
            repos.append(entry)
    return repos


def detect_tech_stack(repo_path: Path) -> str:
    """Detect primary tech stack from common config files."""
    indicators: list[tuple[str, str]] = [
        ("package.json", "JavaScript/TypeScript"),
        ("tsconfig.json", "TypeScript"),
        ("Podfile", "iOS (Swift/ObjC)"),
        ("build.gradle", "Android (Kotlin/Java)"),
        ("build.gradle.kts", "Android (Kotlin)"),
        ("requirements.txt", "Python"),
        ("pyproject.toml", "Python"),
        ("Cargo.toml", "Rust"),
        ("go.mod", "Go"),
        ("pom.xml", "Java"),
        ("Gemfile", "Ruby"),
        ("composer.json", "PHP"),
        ("pubspec.yaml", "Flutter/Dart"),
        ("*.csproj", "C# / .NET"),
        ("CMakeLists.txt", "C/C++"),
    ]
    found = []
    for filename, tech in indicators:
        if "*" in filename:
            if list(repo_path.glob(filename)):
                found.append(tech)
        elif (repo_path / filename).exists():
            found.append(tech)
    return ", ".join(found[:3]) if found else "—"


def extract_repo_description(repo_path: Path) -> str:
    """Extract a one-line description from README.md or AGENTS.md."""
    for filename in ("README.md", "AGENTS.md"):
        filepath = repo_path / filename
        if not filepath.exists():
            continue
        text = filepath.read_text(encoding="utf-8", errors="replace")
        desc = _extract_first_description(text)
        if desc:
            return desc
    return "—"


def _extract_first_description(text: str) -> str:
    """Extract the first meaningful paragraph after the H1 heading."""
    lines = text.split("\n")
    past_h1 = False
    for line in lines:
        stripped = line.strip()
        if not past_h1:
            if stripped.startswith("# "):
                past_h1 = True
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            break
        if stripped.startswith(("![", "<", "```", "|", "---", "- ", "* ")):
            continue
        desc = stripped.rstrip(".")
        if len(desc) > 120:
            desc = desc[:117] + "..."
        return desc
    return ""


def detect_repo_role(repo_path: Path) -> str:
    """Infer the repo's role/platform from its name and contents."""
    name = repo_path.name.lower()
    role_keywords: list[tuple[list[str], str]] = [
        (["web", "frontend", "fe", "webapp", "dashboard", "portal"], "Web Frontend"),
        (["api", "backend", "server", "service", "gateway"], "Backend / API"),
        (["ios", "apple"], "iOS"),
        (["android"], "Android"),
        (["mobile", "app"], "Mobile"),
        (["infra", "devops", "deploy", "k8s", "terraform", "helm"], "Infrastructure"),
        (["shared", "common", "lib", "sdk", "core", "pkg", "packages"], "Shared Library"),
        (["docs", "doc", "documentation", "wiki"], "Documentation"),
        (["design", "figma", "sketch"], "Design"),
        (["data", "ml", "ai", "model", "pipeline"], "Data / ML"),
        (["test", "e2e", "qa", "integration-test"], "Testing"),
        (["config", "env", "setup"], "Configuration"),
    ]
    for keywords, role in role_keywords:
        for kw in keywords:
            if kw in name:
                return role
    return "—"


def analyze_repo(repo_path: Path) -> dict[str, str]:
    """Analyze a single repo and return its metadata."""
    return {
        "name": repo_path.name,
        "description": extract_repo_description(repo_path),
        "tech_stack": detect_tech_stack(repo_path),
        "role": detect_repo_role(repo_path),
    }


# ---------------------------------------------------------------------------
# Content generation (all pure functions — no side effects)
# ---------------------------------------------------------------------------

def build_repos_table(repos: list[dict[str, str]]) -> str:
    """Build a Markdown table from repo metadata."""
    lines = [
        "| # | Repository | Role | Tech Stack | Description |",
        "|---|-----------|------|-----------|-------------|",
    ]
    for i, repo in enumerate(repos, 1):
        lines.append(
            f"| {i} | [{repo['name']}](./{repo['name']}/) "
            f"| {repo['role']} "
            f"| {repo['tech_stack']} "
            f"| {repo['description']} |"
        )
    return "\n".join(lines)


def resolve_skill_script(
    skill: str, script: str, home: Path | None = None
) -> str:
    """Return a `~`-relative path to an installed skill script, or "".

    The generated AGENTS.md orders agents to run the gate themselves,
    without being asked — so a script path that does not exist on this
    machine makes the mandate decorative. Skills install per tool
    (`~/.claude/skills/…`), in the cross-tool shared directory
    (`~/.agents/skills/…`), and in nested config dirs
    (`~/.config/opencode/skills/…`), so the location is not knowable from
    the template and has to be probed where it is written.
    """
    root = home or Path.home()
    for pattern in (".agents/skills", ".claude/skills", "*/skills", "*/*/skills"):
        for candidate in sorted(root.glob(f"{pattern}/{skill}/scripts/{script}")):
            if candidate.is_file():
                return f"~/{candidate.relative_to(root)}"
    return ""


def skill_command(
    skill: str, script: str, args: str, home: Path | None = None
) -> tuple[str, str]:
    """Return (command, caveat) for a script the reader must be able to run."""
    resolved = resolve_skill_script(skill, script, home)
    if resolved:
        return f"python3 {resolved} {args}".strip(), ""
    placeholder = f"~/.<agent>/skills/{skill}/scripts/{script}"
    return (
        f"python3 {placeholder} {args}".strip(),
        "`<agent>` is unresolved — no skill install was found on this "
        "machine. Install the skills, then re-run fullstack-init to write "
        "the real path.",
    )


# The whole command is the placeholder, argument included: `graphify_check.py`
# takes exactly one path, so replacing only the script part would leave the
# old argument standing and produce a call the script rejects with exit 2.
LEGACY_GRAPHIFY_PLACEHOLDER = "python3 SKILL_PATH/scripts/graphify_check.py <repo-path>"
# Workspaces migrated by that first version carry the doubled argument; the
# repair is a pure typo fix, so it runs even where no install resolves.
DOUBLED_GRAPHIFY_ARGS = "graphify_check.py <repo-path> <repo-path>"
CLEAN_GRAPHIFY_ARGS = "graphify_check.py <repo-path>"


def upgrade_legacy_skill_commands(text: str, home: Path | None = None) -> str:
    """Replace the legacy `SKILL_PATH` placeholder with the installed path.

    Workspaces initialized before the command was resolved carry
    `python3 SKILL_PATH/scripts/graphify_check.py <repo-path>`, which cannot
    run from the workspace root: there is no skill directory there to
    substitute for `SKILL_PATH`. Re-init rewrites that literal to the path
    probed on this machine, and repairs the doubled argument an earlier
    version of this migration left behind. When no install is found the
    placeholder is left untouched rather than replaced with a second
    placeholder.
    """
    text = text.replace(DOUBLED_GRAPHIFY_ARGS, CLEAN_GRAPHIFY_ARGS)
    command, caveat = skill_command(
        "fullstack-init", "graphify_check.py", "<repo-path>", home
    )
    if caveat:
        return text
    return text.replace(LEGACY_GRAPHIFY_PLACEHOLDER, command)


DOCS_LOCKSTEP_BULLET = (
    "- **Docs-Code Lockstep**: these documents record why the code looks the\n"
    "  way it does, and they move with it. The rule — owner lookup\n"
    "  (`plan_lint.py --find <path-or-symbol>`), which documents a change must\n"
    "  update, and when a small change may skip the work item as a quick fix —\n"
    "  lives in one place: the workspace root `AGENTS.md` →\n"
    "  *Docs-Code Lockstep (MANDATORY)*."
)


def inject_docs_lockstep(text: str) -> str:
    """Add the Docs-Code Lockstep bullet to a docs AGENTS.md that lacks it.

    The docs directory's AGENTS.md is create-only because users customize
    it — which also means a workspace initialized before this rule has no
    pointer to it, and that pointer is the entrance for a reader who came
    from the documents rather than from the code. Only the missing bullet
    is inserted, so hand-written content survives the re-run.
    """
    if "Docs-Code Lockstep" in text:
        return text
    lines = text.splitlines()
    try:
        start = next(
            index
            for index, line in enumerate(lines)
            if line.strip() in ("## Conventions", "## 约定")
        )
    except StopIteration:
        return text.rstrip("\n") + "\n\n## Conventions\n\n" + DOCS_LOCKSTEP_BULLET + "\n"

    last_bullet = None
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            break
        if lines[index].startswith("- "):
            last_bullet = index
    if last_bullet is None:
        return text.rstrip("\n") + "\n\n" + DOCS_LOCKSTEP_BULLET + "\n"

    end = last_bullet
    for index in range(last_bullet + 1, len(lines)):
        if lines[index].startswith(("  ", "\t")) and lines[index].strip():
            end = index
        elif lines[index].strip() and not lines[index].startswith("## "):
            break
        else:
            break
    return "\n".join(lines[: end + 1] + [DOCS_LOCKSTEP_BULLET] + lines[end + 1 :]) + (
        "\n" if text.endswith("\n") else ""
    )


def generate_agents_md(
    project_name: str,
    repos_table: str,
    docs_dir: str,
    home: Path | None = None,
) -> str:
    """Generate the workspace-level AGENTS.md (always from scratch)."""
    plan_lint_cmd, plan_lint_caveat = skill_command(
        "fullstack-propose", "plan_lint.py", "--find <path-or-symbol>", home
    )
    gate_cmd, _ = skill_command(
        "fullstack-propose", "plan_lint.py", "<work-dir>", home
    )
    mermaid_cmd, _ = skill_command(
        "fullstack-propose", "mermaid_lint.py", "path/to/file.md", home
    )
    repo_skills_cmd, repo_skills_caveat = skill_command(
        "fullstack-init", "repo_skills.py", "<repo>", home
    )
    graphify_cmd, _ = skill_command(
        "fullstack-init", "graphify_check.py", "<repo-path>", home
    )
    # Built outside the template: Python < 3.12 rejects a backslash anywhere
    # inside an f-string's expression part, nested literals included.
    repo_skills_note = f"  {repo_skills_caveat}\n" if repo_skills_caveat else ""
    plan_lint_note = f"\n   {plan_lint_caveat}\n" if plan_lint_caveat else ""
    return f"""\
# {project_name}

## Project Overview

This is a multi-repo fullstack workspace. Every subdirectory — including
`{docs_dir}/` — is an independent git repository with its own version control.

## Repositories

{repos_table}

## Workspace Conventions

- **Cross-repo changes**: When making changes that span multiple repos,
  commit and test each repo independently.
- **Shared documentation**: Cross-cutting docs live in `{docs_dir}/`
  (its own git repo — NOT managed by the workspace git).
- **Scripts**: Workspace-level automation lives in `scripts/`.
- **Agent delegation**: Workspace-level agents live in `.agents/agents/`.
  When working inside a specific repo that has its own `.agents/agents/`,
  prefer using the repo-level agents for that repo's code.
- **Repo Skills**: a repo's private skills live in `<repo>/.agents/skills/`
  and are invisible to the agent's skill tool from the workspace root.
  Before starting work in a repo (editing code or answering a domain
  question), run the index command below and read the `SKILL.md` of each
  skill whose description matches the task:

  ```bash
  {repo_skills_cmd}
  ```

  Treat a matching skill as binding instructions and run its commands
  from the repo root. Do not bulk-load non-matching skills. Name the repo
  the way the user said it: the script resolves a bare directory name
  against this workspace first and a sibling workspace next, so ask for a
  path only when it answers `AMBIGUOUS_REPO`.
{repo_skills_note}
- **Knowledge Graph (graphify)**: Some repos may have a `graphify-out/`
  directory generated by the `graphify` skill — a knowledge graph of the
  codebase for fast, accurate information retrieval and cross-file
  relationship analysis.
  - **Check for graphify-out/**: Run
    `{graphify_cmd}` to check
    whether a repo has a knowledge graph. This script uses a direct
    filesystem check that is immune to `.gitignore` filtering — do NOT
    use Glob or other file-search tools that may silently skip ignored
    paths.
  - **Query first** — When `graphify-out/` exists, `cd` into the repo's
    root directory and use `graphify query "<question>"` to retrieve
    information from the knowledge graph BEFORE reading source files
    directly.
  - **Update after changes** — After modifying files in a repo that has
    `graphify-out/`, `cd` into that repo and run `graphify update` to
    keep the graph in sync.

## Work Tracking

When starting any cross-repo work, create a work directory under
`{docs_dir}/changes/` in the appropriate category:

| Category | Directory | Branch prefix | Use for |
|----------|-----------|--------------|---------|
| Feature | `{docs_dir}/changes/feat/<name>/` | `feat/` | New features, capabilities |
| Refactor | `{docs_dir}/changes/refactor/<name>/` | `refactor/` | Code restructuring, tech debt |
| Fix | `{docs_dir}/changes/fix/<name>/` | `fix/` | Bug fixes, issue resolution |

Completed work items are archived by moving them under
`{docs_dir}/changes/archive/YYYY-MM-DD-<type>-<name>/`.

Each work directory contains:

```
<category>/<work-name>/
├── analysis.md        # Technical analysis (architecture, root cause, design options)
├── plan.md            # Plan: repos, tasks, Success Criteria, Code Map
├── progress.md        # Dated change log (status, completed steps, blockers)
└── review.md          # Review findings, Evidence table, verdict
```

Work directories are **never deleted** — they serve as project history.
Archived work lives under `{docs_dir}/changes/archive/`. The
`{docs_dir}/` repo does NOT use feature branches — all work tracking
docs are committed directly to its main branch.

Problems observed but not yet ready to become work items are recorded
first under `{docs_dir}/issues/` (sibling of `changes/`) via the
`fullstack-issue-create` skill: each issue is a `YYYY-MM-DD-<name>/`
directory (date = the record day) holding a `README.md` plus raw
evidence in `log/`. Closing is a move into `{docs_dir}/issues/archive/`
with the name unchanged — directory location is the state, and nothing
under `issues/` is ever deleted. Issues are closed by the
`fullstack-issue-archive` skill — including a problem that was fixed
directly without a work item — and only after the fix is verified or
the user explicitly accepts an unresolved close.

## Docs-Code Lockstep (MANDATORY)

A work item's four documents under `{docs_dir}/changes/` record *why* its
code looks the way it does; an edit that leaves them behind makes the next
reader implement against a spec that is no longer true. Before editing code
in this workspace — whether or not the fullstack skills are invoked — decide
which path the change takes.

1. **Find the owner.** A file or symbol belongs to the work item whose
   `## Code Map` lists it:

   ```bash
   {plan_lint_cmd}
   ```
{plan_lint_note}
   Only `CODEMAP:` lines are ownership, and only under an active
   `changes/<type>/` directory; `SUBSTRING:` and `MENTION:` lines are
   candidates to confirm. `STATUS=OWNER` exits 0, `CANDIDATE` / `NONE`
   exit 1, and 2 means no docs directory (run it from the workspace root).
2. **Pick the path.**

   | Situation | Path |
   |---|---|
   | An active work item owns the code | Follow-up on that item (`fullstack-apply`): update the documents the change invalidates (table below) and record a code-review round with a one-line `**文档同步**` / `**Document Sync**` attestation |
   | No active owner (none, or only an archived one) and the change is a **quick fix** — a bug whose root cause is established with evidence, or a fully specified small tweak; one repo; no cross-repo contract, persisted data / schema, or external API change; small | Quick fix (`fullstack-apply` → quick fix): no work item; a regression test where the repo has tests, one independent code review, and a commit message carrying what changed, why, and how it was verified |
   | Anything else | Ask whether to open a work item (`fullstack-propose`); never edit silently because "no doc applies". An archived item is never reopened — new work on its scope is a new item |

3. **Keep an active item's documents in step**, in the same pass as the
   code:

   | What the change did | Must change |
   |---|---|
   | any code edit | `progress.md` — new dated entry |
   | moved a responsibility, changed a call order, added or removed a component, altered a frozen contract | `analysis.md` — rewrite the affected section and its diagram; never append a note that contradicts the body |
   | touched behavior a Success Criterion covers | `plan.md` criterion + its `review.md` Evidence row |
   | touched a file the Code Map does not list | `plan.md` Code Map row |
   | was reviewed or verified | `review.md` — a compact round: findings, verdict, Document Sync line |

4. **Gate an active item before committing** — it must report
   `STATUS=PASS`:

   ```bash
   {gate_cmd}
   ```

   Errors are broken chains (a criterion with no Evidence row, a missing
   Code Map, a dangling task id); warnings (a missing attestation, a stale
   summary) should be fixed but do not block.

## Branch Naming Convention

When implementing work items, create branches in each affected repo:

| Category | Without Jira | With Jira |
|----------|-------------|-----------|
| Feature | `feat/Import-Export` | `feat/XYZ-706/Import-Export` |
| Refactor | `refactor/Refine-Models` | `refactor/XYZ-707/Refine-Models` |
| Fix | `fix/iPad-Ble-Not-Working` | `fix/XYZ-708/iPad-Ble-Not-Working` |

Branch names use Title-Case-With-Hyphens for the descriptive part.

## Documentation Diagrams (Mermaid Compatibility)

When writing Mermaid diagrams in any Markdown file inside this workspace
(`AGENTS.md`, `README.md`, `plan.md`, `progress.md`, `analysis.md`,
`findings.md`, `verdict.md`, `review.md`, etc.), target **Mermaid 10.2.3**
compatibility. Many platforms used to render these docs (older GitHub
Enterprise, Confluence, Notion exports, internal wikis, IDE preview
plugins) ship Mermaid 10.2.3 or earlier. Newer syntax causes
`Syntax error in text` rendering failures that block readers.

### Allowed (safe in Mermaid 10.2.3)

- `flowchart` / `graph` (`TD`, `LR`, `BT`, `RL`) with the basic node
  shapes only: `[rect]`, `(round)`, `((circle))`, `{{diamond}}`,
  `[/parallel/]`, `[\\parallel\\]`, `[(database)]`, `[[subroutine]]`,
  `>flag]`, `{{{{hexagon}}}}`
- Standard arrows: `-->`, `---`, `-.->`, `==>`, `--text-->`,
  `-. text .->`, `== text ==>`
- `subgraph Name ... end` (no `direction` override inside)
- `sequenceDiagram` with `participant`, `->>`, `-->>`, `Note over`,
  `loop`, `alt`/`else`, `opt`, `par`/`and`, `rect`, `activate`/`deactivate`
- `classDiagram` with classes, members, `<|--`, `*--`, `o--`, `-->`, `..>`
- `stateDiagram-v2` with states, transitions, `[*]`, `note right of`
- `erDiagram` with basic entity-relationship syntax
- `gantt` with sections, tasks, `dateFormat`, `axisFormat`
- `pie`, `journey`, `gitGraph`
- `%%{{init: {{...}}}}%%` directive with stable themes
  (`default`, `dark`, `forest`, `neutral`)

### Avoid (introduced after 10.2.3 — will fail to render)

- Beta diagram types: `block-beta`, `quadrantChart`, `xychart-beta`,
  `sankey-beta`, `packet-beta`, `architecture-beta`, `treemap`,
  `radar`, `kanban`
- New node-shape syntax: `A@{{ shape: ... }}` (introduced in 11.x)
- Extended flowchart shapes: `tag`, `stadium`, `lean-r`, `trap-b`,
  `cyl`, `f-circ`, `framed`, `fork`, `notch-rect`
- Mermaid icon shapes: `fa:`, `mdi:`, `logos:`
- ELK renderer config (`flowchart-elk`)
- Sequence diagram `box ... end` grouping, `actor X as Y @{{...}}`
- `classDiagram` namespaces, `note for <class>`, generic `~T~` on members
- `gantt` `tickInterval`, `weekday`
- `mindmap` advanced features (it exists in 10.2 but with limited shape
  support — keep nodes plain text only)

### Safety rules

- If you are unsure whether a feature is supported, prefer a simpler
  diagram, a Markdown table, or ASCII art over an experimental Mermaid
  feature.
- **Quote labels with special characters — applies to ALL label
  positions, not just node labels.** The most common failure observed
  in the wild is an UNQUOTED edge label that contains `(`, `[`, or
  `{{`. Always wrap such labels in double quotes:

  | Position | Bad (FAILS to parse) | Good |
  |----------|---------------------|------|
  | Node label | `A[Step 1: parse (AST)]` | `A["Step 1: parse (AST)"]` |
  | Edge label | `A -->\\|hello (world)\\| B` | `A -->\\|"hello (world)"\\| B` |
  | Edge label | `A -->\\|key[0]\\| B` | `A -->\\|"key[0]"\\| B` |
  | Subgraph title | `subgraph My (Group)` | `subgraph "My (Group)"` |

- The characters that REQUIRE quoting in **edge labels** in 10.2.3 are:
  `(`, `)`, `[`, `]`, `{{`, `}}`. Other characters (`/`, `+`, `:`, `#`,
  `&`, `<br/>`, Chinese, commas) work unquoted.
- The characters that REQUIRE quoting in **node labels** are: `()`,
  `[]`, `{{}}`, `:`, `|`, `#`, `&`, `"`, `<` (other than `<br/>`).
- **Subgraph titles** that contain `(` or `)` MUST be quoted. Brackets
  in subgraph titles are interpreted as the shape syntax — avoid that
  combination unless intended.
- **Sequence diagram participant aliases, message text, and `Note`
  text** are LENIENT — parens, brackets, slashes, `<br/>`, Chinese
  all work unquoted. No quoting needed there.
- Multi-line labels — use `<br/>` (line breaks via `\\n` are NOT
  supported in 10.2.3). When a label has BOTH `<br/>` and `()`,
  wrapping in quotes covers both.
- Do NOT use HTML entities like `&amp;`, `&lt;` inside labels — escape
  by quoting the label instead.
- One diagram, one purpose. Splitting into multiple smaller diagrams is
  more compatible than a single complex one.

### Validate before declaring a doc done

Run the bundled `mermaid_lint.py` script (shipped with the
`fullstack-propose`, `fullstack-apply`, and `user-journey` skills — same
file in each) on any Markdown file containing Mermaid blocks BEFORE
declaring the document done. It is a static linter that catches the
common 10.2.3 incompatibilities (unquoted edge labels, unquoted
subgraph titles, `@{{ shape: ... }}` syntax, beta diagram types,
literal `\\n` in labels, bare `<br>`) without requiring a JS
toolchain. The `fullstack-propose` / `fullstack-apply` skills run it
automatically after writing `analysis.md` / `plan.md`; for any other
Markdown file you author by hand, invoke it manually:

```bash
{mermaid_cmd}
```

`STATUS=PASS` means safe to ship. `STATUS=FAIL` means the file will
render as `Syntax error in text` (or as visible garbage like
`xxx-api\\n(Domain API)`) on Mermaid 10.2.3 — fix every `ERROR:`
line and re-run before committing. Full rules live in
`MERMAID-RULES.md` bundled with each of the three skills above.

## Directory Structure

```
{project_name}/
├── AGENTS.md          # This file (regenerated by fullstack-init)
├── README.md          # Human-readable project overview (regenerated)
├── fullstack.json     # Workspace config — the only persistent state
├── .agents/
│   ├── agents/        # Workspace-level sub-agents (regenerated)
│   │   ├── planner.md
│   │   ├── plan-reviewer.md
│   │   ├── developer.md
│   │   ├── code-reviewer.md
│   │   └── debugger.md
│   └── skills/        # Custom skills for this workspace (preserved)
├── scripts/           # Workspace-level automation scripts (preserved)
├── {docs_dir + "/":<23s}# Shared docs (independent git repo, preserved)
│   ├── AGENTS.md
│   ├── changes/
│   │   ├── feat/
│   │   ├── refactor/
│   │   ├── fix/
│   │   └── archive/
│   ├── issues/
│   │   └── archive/
├── web/               # ← Independent git repo (example)
├── api/               # ← Independent git repo (example)
└── ios/               # ← Independent git repo (example)
```
"""


def parse_agents_md_sections(content: str) -> tuple[str, list[tuple[str, str]]]:
    """Parse AGENTS.md into (h1_line, [(section_title, section_body), ...]).

    section_title is the full "## Title" line.
    section_body includes the title line and all content until the next H2.
    """
    lines = content.split("\n")
    h1_line = ""
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_body: list[str] = []

    in_fence = False
    for line in lines:
        stripped = line.strip()
        # A heading inside a fenced block is example text (a document
        # template quoted in AGENTS.md), not a section of this file.
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
        if in_fence or stripped.startswith(("```", "~~~")):
            if current_title:
                current_body.append(line)
            continue
        if stripped.startswith("# ") and not current_title:
            h1_line = line
            continue
        if stripped.startswith("## "):
            if current_title:
                sections.append((current_title, "\n".join(current_body)))
            current_title = line
            current_body = [line]
        elif current_title:
            current_body.append(line)

    if current_title:
        sections.append((current_title, "\n".join(current_body)))

    return h1_line, sections


# Convention bullets whose text belongs to the skill, not the workspace.
# They carry machine-resolved commands and get revised as the skill
# evolves, so a merged copy would keep a stale rule alive across re-runs —
# the same failure `merge_agents_md` replaces whole shipped sections for.
# Every other bullet stays user territory: kept as written, refreshed only
# by hand, because a workspace owner may legitimately reword them.
SHIPPED_CONVENTION_BULLETS = frozenset({"Repo Skills", "Knowledge Graph (graphify)"})


def _bullet_title(line: str) -> str:
    """Return a top-level bullet's bold title without asterisks, or "".

    The title text runs from index 4 — past the opening `- **` — to the
    closing `**`. A one-character title (`- **A**:`) has its closing pair at
    index 5, so the open scan starts at 4 and never finds the opener.
    """
    stripped = line.strip()
    if not stripped.startswith("- **"):
        return ""
    end = stripped.find("**", 4)
    return stripped[4:end].strip() if end > 4 else ""


def _convention_blocks(section: str) -> list[tuple[str, int, int]]:
    """Return `(title, start_line, end_line)` per top-level bullet.

    A block runs from a `- ` line at column zero up to the next one, so
    indented sub-bullets and indented code fences belong to their parent —
    which is what makes a whole-bullet replacement possible. The old
    splitter tested the *stripped* line and therefore cut sub-bullets into
    separate blocks. A fenced block at column zero cannot start a bullet:
    lines inside it are ignored while tracking the fence.
    """
    lines = section.split("\n")
    starts: list[int] = []
    in_fence = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith("- "):
            starts.append(index)

    blocks: list[tuple[str, int, int]] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        blocks.append((_bullet_title(lines[start]), start, end))
    return blocks


def three_way(
    existing: str | None, baseline: str | None, generated: str
) -> tuple[str, str]:
    """Decide one managed unit's text from its three versions.

    `existing` is what is on disk (None when absent), `baseline` what this
    script generated last time (None when unknown), `generated` what it
    generates now. Returns `(text, outcome)`:

    - `created`   — nothing on disk; take the template
    - `unchanged` — disk already matches the template
    - `updated`   — the user never touched it; take the new template
    - `kept`      — the user edited it and the template did not move; keep it
    - `conflict`  — both moved, or there is no baseline to tell; keep the
      user's text and let the caller surface the new template

    Comparison ignores surrounding whitespace, because sections are
    re-joined with normalized blank lines.
    """
    if existing is None:
        return generated, "created"
    if existing.strip() == generated.strip():
        return existing, "unchanged"
    if baseline is not None and existing.strip() == baseline.strip():
        return generated, "updated"
    if baseline is not None and generated.strip() == baseline.strip():
        return existing, "kept"
    return existing, "conflict"


def _merge_conventions_report(
    existing_section: str, generated_section: str, baseline_section: str | None
) -> tuple[str, list[str], list[str]]:
    """Merge Workspace Conventions bullet by bullet.

    Returns `(section, conflicts, review)`: `conflicts` are bullets both the
    user and the template changed; `review` are bullets that differ from the
    template when there is no baseline to tell who changed them.

    - Shipped bullets (`SHIPPED_CONVENTION_BULLETS`) are replaced in place —
      their commands and rules move with the skill.
    - Other bullets present on both sides go through `three_way` against the
      baseline bullet of the same title: untouched ones take the new
      template, edited ones are kept, and both-changed ones are kept and
      reported as conflicts.
    - Generated bullets the workspace lacks are appended — unless the
      baseline shows the template already offered them, which means the
      user deleted them on purpose.
    - Bullets only the workspace has are user territory and stay as written.

    When nothing changes the section is returned byte-for-byte unchanged, so
    a no-op re-init leaves the file alone.
    """
    lines = existing_section.split("\n")
    blocks = _convention_blocks(existing_section)
    generated_lines = generated_section.split("\n")
    generated_blocks = [
        (title, generated_lines[start:end])
        for title, start, end in _convention_blocks(generated_section)
    ]
    baseline_blocks: dict[str, str] = {}
    if baseline_section is not None:
        baseline_lines = baseline_section.split("\n")
        baseline_blocks = {
            title: "\n".join(baseline_lines[start:end])
            for title, start, end in _convention_blocks(baseline_section)
            if title
        }

    existing_text = {
        title: "\n".join(lines[start:end]) for title, start, end in blocks if title
    }
    replacements: dict[str, list[str]] = {}
    appends: list[list[str]] = []
    conflicts: list[str] = []
    review: list[str] = []
    for title, body in generated_blocks:
        if not title:
            continue
        if title not in existing_text:
            if baseline_section is not None and title in baseline_blocks:
                continue
            appends.append(body)
            continue
        if title in SHIPPED_CONVENTION_BULLETS:
            replacements[title] = body
            continue
        _, outcome = three_way(
            existing_text[title], baseline_blocks.get(title), "\n".join(body)
        )
        if outcome == "updated":
            replacements[title] = body
        elif outcome == "conflict":
            target = conflicts if baseline_section is not None else review
            target.append(f"Workspace Conventions → {title}")

    if not replacements and not appends:
        return existing_section, conflicts, review

    out: list[str] = []
    cursor = 0
    for title, start, end in blocks:
        out.extend(lines[cursor:start])
        original = lines[start:end]
        if title in replacements:
            stripped_original = list(original)
            trailing_blanks = 0
            while stripped_original and not stripped_original[-1].strip():
                stripped_original.pop()
                trailing_blanks += 1
            replacement = list(replacements[title])
            while replacement and not replacement[-1].strip():
                replacement.pop()
            out.extend(replacement)
            out.extend([""] * trailing_blanks)
        else:
            out.extend(original)
        cursor = end
    out.extend(lines[cursor:])

    for body in appends:
        while out and not out[-1].strip():
            out.pop()
        stripped_body = list(body)
        while stripped_body and not stripped_body[-1].strip():
            stripped_body.pop()
        out.append("")
        out.extend(stripped_body)

    return "\n".join(out), conflicts, review


def _merge_conventions(
    existing_section: str,
    generated_section: str,
    baseline_section: str | None = None,
) -> str:
    """Merge Workspace Conventions; see `_merge_conventions_report`."""
    merged, _, _ = _merge_conventions_report(
        existing_section, generated_section, baseline_section
    )
    return merged


REPO_ROW_RE = re.compile(r"^\|\s*\d+\s*\|\s*\[([^\]]+)\]\(")
REPO_ROW_NUMBER_RE = re.compile(r"^\|\s*\d+\s*\|")


def _repo_rows(section: str | None) -> dict[str, str]:
    """Return `{repo name: row}` for the repos table in a section."""
    rows: dict[str, str] = {}
    for line in (section or "").split("\n"):
        match = REPO_ROW_RE.match(line.strip())
        if match:
            rows[match.group(1)] = line.strip()
    return rows


def _row_cells(row: str) -> str:
    """A row without its `#` cell, so renumbering is not an edit."""
    return REPO_ROW_NUMBER_RE.sub("", row, count=1).strip()


def _merge_repositories(
    existing_section: str, generated_section: str, baseline_section: str | None
) -> tuple[str, list[str]]:
    """Merge the Repositories section row by row; return (section, kept repos).

    Rows follow the generated set — a new repo gets a row, a removed repo
    loses it — and are renumbered in generated order. A row the user edited
    (it differs from the baseline row, or there is no baseline row to compare
    with) keeps the user's cells; an untouched row takes the freshly detected
    role, tech stack, and description. Text around the table — notes above or
    below it — is kept as written.
    """
    existing_rows = _repo_rows(existing_section)
    baseline_rows = _repo_rows(baseline_section)
    generated_lines = generated_section.split("\n")

    header: list[str] = []
    rows: list[str] = []
    kept: list[str] = []
    for line in generated_lines:
        stripped = line.strip()
        match = REPO_ROW_RE.match(stripped)
        if not match:
            if stripped.startswith("|"):
                header.append(stripped)
            continue
        name = match.group(1)
        row = stripped
        old = existing_rows.get(name)
        if old is not None and _row_cells(old) != _row_cells(row):
            base = baseline_rows.get(name)
            if base is None or _row_cells(old) != _row_cells(base):
                row = REPO_ROW_NUMBER_RE.sub(f"| {len(rows) + 1} |", old, count=1)
                kept.append(name)
        rows.append(row)

    existing_lines = existing_section.split("\n")
    table_start = next(
        (i for i, line in enumerate(existing_lines) if line.strip().startswith("|")),
        None,
    )
    if table_start is None:
        return generated_section, []
    table_end = table_start
    while table_end < len(existing_lines) and existing_lines[
        table_end
    ].strip().startswith("|"):
        table_end += 1
    merged = existing_lines[:table_start] + header + rows + existing_lines[table_end:]
    return "\n".join(merged), kept


# Sections whose text belongs to the skill, not the workspace: replaced
# wholesale on every run, because a merged copy keeps dead commands alive.
SKILL_OWNED_SECTIONS = frozenset(
    {
        "Directory Structure",
        "Docs-Code Lockstep (MANDATORY)",
        "Documentation Diagrams (Mermaid Compatibility)",
    }
)


def merge_agents_md_report(
    existing: str,
    generated: str,
    baseline: str | None = None,
    add_missing_without_baseline: bool = True,
) -> tuple[str, dict[str, list[str]]]:
    """Three-way merge of a Markdown file by H2 section.

    Used for the workspace `AGENTS.md` and the docs-directory `AGENTS.md`.
    Returns the merged text and a report with `updated`, `kept`,
    `conflicts`, and `review` lists naming the units involved. `review`
    holds units that differ from the template when no baseline exists yet —
    either the user's edit or a template update a pre-baseline workspace
    never received; only a person can tell, once.

    - Skill-owned sections (`SKILL_OWNED_SECTIONS`): always the template.
    - Repositories: row-by-row (`_merge_repositories`).
    - Workspace Conventions: bullet-by-bullet (`_merge_conventions_report`).
    - Any other section on both sides: `three_way` against the baseline
      section. With no baseline the user's text is kept and a difference is
      listed under `review` for a one-time look; the baseline recorded by
      that run settles it for every later run.
    - A template section the workspace lacks is added, unless the baseline
      shows it was offered before (the user deleted it on purpose). With no
      baseline, `add_missing_without_baseline=False` adds nothing — for a
      file that was create-only before and may be entirely hand-written.
    - A section only the workspace has stays — unless it is a template
      section the template dropped and the user never edited.
    """
    existing_h1, existing_sections = parse_agents_md_sections(existing)
    generated_h1, generated_sections = parse_agents_md_sections(generated)
    baseline_map: dict[str, str] = {}
    if baseline is not None:
        baseline_map = {
            title[3:]: body for title, body in parse_agents_md_sections(baseline)[1]
        }
    existing_map = {title[3:]: body for title, body in existing_sections}

    report: dict[str, list[str]] = {
        "updated": [],
        "kept": [],
        "conflicts": [],
        "review": [],
    }
    bodies: dict[str, str] = {}
    additions: list[tuple[str, str, str | None]] = []
    previous_key: str | None = None

    for gen_title, gen_body in generated_sections:
        key = gen_title[3:]
        if key in SKILL_OWNED_SECTIONS and key in existing_map:
            bodies[key] = gen_body
        elif key == "Repositories" and key in existing_map:
            body, kept_rows = _merge_repositories(
                existing_map[key], gen_body, baseline_map.get(key)
            )
            report["kept"].extend(f"Repositories → {name}" for name in kept_rows)
            bodies[key] = body
        elif key == "Workspace Conventions" and key in existing_map:
            body, conflicts, review = _merge_conventions_report(
                existing_map[key], gen_body, baseline_map.get(key)
            )
            report["conflicts"].extend(conflicts)
            report["review"].extend(review)
            bodies[key] = body
        elif key in existing_map:
            text, outcome = three_way(
                existing_map[key], baseline_map.get(key), gen_body
            )
            if outcome == "updated":
                report["updated"].append(key)
            elif outcome == "kept":
                report["kept"].append(key)
            elif outcome == "conflict":
                report["conflicts" if baseline is not None else "review"].append(key)
            bodies[key] = text
        elif key in SKILL_OWNED_SECTIONS:
            additions.append((key, gen_body, previous_key))
        elif baseline is not None and key in baseline_map:
            pass
        elif baseline is None and not add_missing_without_baseline:
            pass
        else:
            additions.append((key, gen_body, previous_key))
        previous_key = key

    generated_keys = {title[3:] for title, _ in generated_sections}
    order: list[tuple[str, str]] = []
    for title, body in existing_sections:
        key = title[3:]
        if (
            key not in generated_keys
            and key in baseline_map
            and body.strip() == baseline_map[key].strip()
        ):
            report["updated"].append(f"removed {key}")
            continue
        order.append((key, bodies.get(key, body)))

    for key, body, after in additions:
        keys = [k for k, _ in order]
        index = keys.index(after) + 1 if after in keys else 0
        order.insert(index, (key, body))

    result_lines = [existing_h1 or generated_h1, ""]
    preamble = _preamble(existing).strip()
    if preamble:
        result_lines.extend([preamble, ""])
    for _, body in order:
        result_lines.append(body.strip())
        result_lines.append("")
    return "\n".join(result_lines), report


def _preamble(content: str) -> str:
    """Return the text between the H1 line and the first H2 heading."""
    lines = content.split("\n")
    out: list[str] = []
    seen_h1 = False
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
        if stripped.startswith("## ") and not in_fence:
            break
        if stripped.startswith("# ") and not seen_h1:
            seen_h1 = True
            continue
        if seen_h1:
            out.append(line)
    return "\n".join(out)


def merge_agents_md(
    existing: str, generated: str, baseline: str | None = None
) -> str:
    """Merge an existing AGENTS.md with a fresh template; see the report form."""
    merged, _ = merge_agents_md_report(existing, generated, baseline)
    return merged


def detect_language(text: str) -> str:
    """Detect language from text. Returns 'zh' if Chinese characters found, else 'en'."""
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            return "zh"
    return "en"


def generate_readme(project_name: str, docs_dir: str, lang: str = "en") -> str:
    """Generate the workspace README.md with usage guide."""
    if lang == "zh":
        return _generate_readme_zh(project_name, docs_dir)
    return _generate_readme_en(project_name, docs_dir)


def _generate_readme_en(project_name: str, docs_dir: str) -> str:
    """Generate English README."""
    return f"""\
# {project_name}

Multi-repo fullstack workspace managed by
[mythril-agent-skills](https://github.com/jie-meng/mythril-agent-skills)
fullstack skills.

## Quick Start

> **Important**: Always launch your AI agent from the workspace root
> directory (where `fullstack.json` lives). The fullstack skills will not
> work if started from a subdirectory or outside the workspace.

### Initialize the workspace

Run `fullstack-init` when setting up for the first time or after adding /
removing repositories:

```
> Initialize this fullstack workspace
```

This discovers all git repos, generates `AGENTS.md`, agent templates, and
sets up the shared documentation directory (`{docs_dir}/`).

Re-running is safe — it refreshes generated files while preserving your
docs, scripts, and custom skills.

### Explore before implementing

Use `fullstack-explore` to understand the codebase read-only:

```
> How does authentication work across repos?
> Which repo handles payments?
```

Use `fullstack-propose` to plan work — and validate unknowns first if
needed:

```
> Plan OAuth2 PKCE support (Jira: PROJ-123)
> Investigate whether WebSocket can replace polling, then plan it
> Can we migrate from REST to GraphQL?
```

The propose skill creates a work plan under `{docs_dir}/changes/`. If
there are unknowns, its deep mode makes temporary code changes (no
branches, no commits) and records the verdict in the same work directory.

### Implement a feature / refactor / fix

Use `fullstack-apply` to implement a planned work item across repos:

```
> Implement the dark mode feature (Jira: PROJ-123)
> Refactor the authentication module across all services
> Fix the login crash on empty password
> Implement oauth2-pkce based on the plan
```

You can include links to Jira tickets, Confluence pages, GitHub issues, or
Figma designs — the skill will gather context from all of them before
implementing.

The skill will:

1. Read the plan from `{docs_dir}/changes/<type>/<name>/`
2. Identify affected repos and propose branches
3. Ask for your confirmation
4. Implement changes repo by repo (in dependency order)
5. Run tests and linting in each repo
6. Review changes against the plan's Success Criteria
7. Create Pull Requests for each repo (if repos are on GitHub)

### Quick fix — no work item

A bug whose root cause is already known — one repo, small, no contract or
schema change — does not need a plan. Ask `fullstack-apply` to fix it
directly:

```
> The root cause is clear, just fix it
```

It branches, adds a regression test, runs one independent code review,
and commits. No work directory is created; the commit message is the
record.

### Archive completed work

When a work item is done, use `fullstack-archive`:

```
> Archive the dark mode feature
> 归档登录崩溃修复
```

The skill moves the work directory into
`{docs_dir}/changes/archive/YYYY-MM-DD-<type>-<name>/`.

### Close a recorded issue

An issue that was fixed directly — no work item needed — is closed with
`fullstack-issue-archive`:

```
> Close the issue: brownout during 4G bursts
> 归档 issue：4G 突发时电压跌落
```

The skill moves the issue directory into `{docs_dir}/issues/archive/`
with the name unchanged, and records the close mode (`resolved` here),
a pointer to the commit that fixed it, and how the fix was verified.

### Resume previous work

If a session was interrupted, start a new session and tell the agent to
continue:

```
> Continue the dark mode feature
> Resume work on PROJ-123
> Check the docs and keep going
```

The skill reads `{docs_dir}/changes/` for existing plans and progress,
detects which branches are already checked out, and picks up where it
left off.

## Workspace Structure

```
{project_name}/
├── fullstack.json     # Workspace config (do not delete)
├── AGENTS.md          # AI agent context (regenerated by fullstack-init)
├── README.md          # This file (regenerated by fullstack-init)
├── .agents/
│   ├── agents/        # Workspace-level AI agents (regenerated)
│   └── skills/        # Custom skills (preserved across runs)
├── {docs_dir + "/":<23s}# Shared docs — independent git repo
│   ├── changes/
│   │   ├── feat/      #   Feature work tracking
│   │   ├── refactor/  #   Refactor work tracking
│   │   ├── fix/       #   Fix work tracking
│   │   └── archive/   #   Completed work
│   ├── issues/        #   Issue records (pre-work-item)
│   │   └── archive/   #   Closed issues
├── scripts/           # Workspace-level scripts (preserved)
└── <repos...>/        # Your git repositories
```

## Work Tracking

Every cross-repo work item gets its own directory under
`{docs_dir}/changes/<type>/`:

```
{docs_dir}/changes/<type>/<work-name>/
├── analysis.md        # Technical analysis (why and how)
├── plan.md            # What to do, which repos, Success Criteria
├── progress.md        # Dated change log (done, in progress, blockers)
└── review.md          # Review findings, Evidence table, verdict
```

Completed work is archived under
`{docs_dir}/changes/archive/YYYY-MM-DD-<type>-<name>/`.

These are never deleted — they serve as project history.

Problems that are not ready to become work items are recorded first
under `{docs_dir}/issues/YYYY-MM-DD-<name>/` (date = the record day)
with raw evidence in `log/`. Closing an issue moves it into
`{docs_dir}/issues/archive/` with the name unchanged. See the
`fullstack-issue-create` skill (record / update) and
`fullstack-issue-archive` (close).

## Documentation

- **Workspace AGENTS.md** — Cross-repo context and conventions for AI agents
- **`{docs_dir}/AGENTS.md`** — Documentation conventions
- **Repo-level AGENTS.md** — Each repo's own coding standards and build instructions
"""


def _generate_readme_zh(project_name: str, docs_dir: str) -> str:
    """Generate Chinese README."""
    return f"""\
# {project_name}

由 [mythril-agent-skills](https://github.com/jie-meng/mythril-agent-skills)
fullstack 技能管理的多仓库全栈工作区。

## 快速上手

> **重要**：请始终在工作区根目录（`fullstack.json` 所在目录）启动你的 AI
> 编程助手。如果在子目录或工作区外启动，fullstack 技能将无法正常工作。

### 初始化工作区

首次使用或增删了子仓库后，运行 `fullstack-init`：

```
> 初始化这个全栈工作区
```

脚本会自动发现所有 git 子仓库、生成 `AGENTS.md`、AI agent 模板，以及共享
文档目录（`{docs_dir}/`）。

重复运行是安全的——会刷新生成的文件，但保留你的文档、脚本和自定义技能。

### 先探索再规划

使用 `fullstack-explore` 只读探索代码库：

```
> 认证是怎么跨仓库工作的？
> 哪个仓库负责支付逻辑？
```

使用 `fullstack-propose` 规划工作——如有未知项可先验证：

```
> 规划 OAuth2 PKCE 支持（Jira: PROJ-123）
> 调研 WebSocket 能否替换轮询，然后做规划
> 先研究 REST 迁移 GraphQL 的可行性
```

propose 会在 `{docs_dir}/changes/` 下创建工作计划。如果有未知项，
其深度模式会做临时代码改动（不开分支、不提交），并把结论记录在
同一个工作目录中。

### 开发新功能 / 重构 / 修复 Bug

使用 `fullstack-apply` 实现已规划的工作项：

```
> 实现暗色模式功能（Jira: PROJ-123）
> 重构所有服务的鉴权模块
> 修复空密码登录崩溃问题
> 基于方案实现 oauth2-pkce
```

你可以在消息中附带 Jira 卡片、Confluence 页面、GitHub Issue 或 Figma 设计
链接——技能会在实现之前自动采集所有相关上下文。

技能会按以下步骤执行：

1. 读取 `{docs_dir}/changes/<type>/<name>/` 中的方案
2. 识别受影响的仓库并提议分支名
3. 等你确认
4. 按依赖顺序逐仓库实现变更
5. 在每个仓库中运行测试和代码检查
6. 对照方案的 Success Criteria 审查
7. 为每个仓库创建 Pull Request（仓库在 GitHub 上时）

### 快修——不建工作项

根因已经查清、只涉及一个仓库、改动小、不改契约和 schema 的 bug，不需要先出方案，
直接让 `fullstack-apply` 修：

```
> 根因已经清楚了，直接修
```

它会开分支、补回归测试、做一次独立代码审查并提交。不建工作目录，提交信息就是记录。

### 归档已完成的工作

工作项完成后，使用 `fullstack-archive`：

```
> 归档暗色模式功能
> Archive the login crash fix
```

技能会把工作目录移动到
`{docs_dir}/changes/archive/YYYY-MM-DD-<type>-<name>/`。

### 关闭已记录的 issue

如果问题已直接修好、不需要立项，用 `fullstack-issue-archive` 关闭：

```
> 关闭 issue：4G 突发时电压跌落
> Close the issue: brownout during 4G bursts
```

技能会把 issue 目录移入 `{docs_dir}/issues/archive/`，目录名保持不变，
并记录关闭方式（这里是 `resolved`）、修复它的提交指针，以及验证方式。

### 继续上一次的工作

如果上次会话中断了，新建会话后告诉 AI 继续：

```
> 继续暗色模式功能的开发
> 继续 PROJ-123
> 看看文档，接着之前的进度继续
```

技能会读取 `{docs_dir}/changes/` 中已有的计划和进度，检测各仓库当前分支，
从中断处继续。

## 工作区结构

```
{project_name}/
├── fullstack.json     # 工作区配置（请勿删除）
├── AGENTS.md          # AI agent 上下文（fullstack-init 自动生成）
├── README.md          # 本文件（fullstack-init 自动生成）
├── .agents/
│   ├── agents/        # 工作区级 AI agent（自动生成）
│   └── skills/        # 自定义技能（跨运行保留）
├── {docs_dir + "/":<23s}# 共享文档 — 独立 git 仓库
│   ├── changes/
│   │   ├── feat/      #   功能开发跟踪
│   │   ├── refactor/  #   重构跟踪
│   │   ├── fix/       #   Bug 修复跟踪
│   │   └── archive/   #   已完成归档
│   ├── issues/        #   问题记录（立项前）
│   │   └── archive/   #   已关闭 issue
├── scripts/           # 工作区级脚本（跨运行保留）
└── <repos...>/        # 你的各个 git 子仓库
```

## 工作跟踪

每个跨仓库工作项在 `{docs_dir}/changes/<type>/` 下都有自己的目录：

```
{docs_dir}/changes/<type>/<work-name>/
├── analysis.md        # 技术分析（为什么和怎么做）
├── plan.md            # 做什么、涉及哪些仓库、Success Criteria
├── progress.md        # 日期变更记录（已完成、进行中、阻塞项）
└── review.md          # 审查发现、证据核验表、结论
```

已完成的工作归档到 `{docs_dir}/changes/archive/YYYY-MM-DD-<type>-<name>/`。

这些目录不会被删除——它们是项目的实施历史记录。

尚不能立项的问题先用 `fullstack-issue-create` 技能记录到
`{docs_dir}/issues/YYYY-MM-DD-<name>/`（日期为记录日）下，
原始证据存放在 `log/`。关闭 issue 时用 `fullstack-issue-archive`
技能将其移入 `{docs_dir}/issues/archive/`，目录名保持不变——
包括问题已直接修好、没有走工作项的情况；只有修复经过验证，或用户
明确接受未解决的关闭时，才会真正关闭。

## 文档说明

- **工作区 AGENTS.md** — 跨仓库上下文和 AI agent 约定
- **`{docs_dir}/AGENTS.md`** — 文档编写约定
- **各仓库 AGENTS.md** — 每个仓库自己的编码规范和构建说明
"""


def generate_docs_agents_md(docs_dir: str) -> str:
    """Generate an AGENTS.md for the shared docs directory."""
    title = docs_dir.replace("-", " ").replace("_", " ").title()
    return f"""\
# {title}

This directory is an **independent git repository** that holds shared
documentation spanning all repositories in this workspace. It has its own
version control, separate from the workspace-level git repo.

## Conventions

- Use Markdown for all documents.
- Organize by topic or domain, not by repo.
- Link to repo-specific docs using relative paths: `../repo-name/docs/...`
- Keep documents concise; deep-dive details belong in the relevant repo.
- This repo does NOT use feature branches — commit work tracking docs
  directly to the main branch.
{DOCS_LOCKSTEP_BULLET}
- **Mermaid diagrams**: target Mermaid 10.2.3 compatibility. Many
  rendering platforms (older GitHub Enterprise, Confluence, Notion
  exports, internal wikis) still ship Mermaid 10.2.3 or earlier. Newer
  syntax (`block-beta`, `quadrantChart`, `xychart-beta`, `sankey-beta`,
  `architecture-beta`, `treemap`, `kanban`, `@{{ shape: ... }}` node
  syntax, ELK renderer, extended flowchart shapes, sequence `box`,
  `classDiagram` namespaces, etc.) causes `Syntax error in text` and
  must be avoided. The most frequent slip-up is an unquoted edge label
  containing parentheses (e.g. `A -->|step (x)| B`) — always quote it
  as `A -->|"step (x)"| B`. See the workspace root `AGENTS.md` →
  *Documentation Diagrams (Mermaid Compatibility)* section for the
  full allowed/avoid list and safety rules, and run the bundled
  `mermaid_lint.py` (shipped with `fullstack-propose`,
  `fullstack-apply`, and `user-journey`) against any Markdown file with
  Mermaid blocks before committing.

## Work Tracking

The `changes/feat/`, `changes/refactor/`, and `changes/fix/`
directories contain per-work-item documentation created by the fullstack
skills. Completed work is archived under `changes/archive/`:

| Directory | Branch prefix | Use for |
|-----------|--------------|---------|
| `changes/feat/` | `feat/` | New features and capabilities |
| `changes/refactor/` | `refactor/` | Code restructuring, tech debt |
| `changes/fix/` | `fix/` | Bug fixes, issue resolution |
| `changes/archive/` | _(none)_ | Completed work, `YYYY-MM-DD-<type>-<name>/` |
| `issues/` | _(none)_ | Pre-work-item issue records, `YYYY-MM-DD-<name>/` (closed → `issues/archive/`, name unchanged) |

The `issues/` directory holds problem records created by the
`fullstack-issue-create` skill before they become work items — each
issue is a `YYYY-MM-DD-<name>/` directory with a `README.md` and raw
evidence in `log/`; closing moves it into `issues/archive/` with the
name unchanged and is performed by `fullstack-issue-archive`.

Each work item gets its own subdirectory:

```
<category>/<work-name>/
├── analysis.md   # Technical analysis (why and how)
├── plan.md       # Requirements, Success Criteria, Code Map, plan
├── progress.md   # Dated change log
└── review.md     # Review findings, Evidence table, verdict (append-only)
```

These directories are **never deleted** — they form the project's
implementation history. Archived work stays in `changes/archive/`,
closed issues in `issues/archive/`. Do not modify docs created by
other work items.

## Structure

```
{docs_dir}/
├── AGENTS.md          # This file
├── changes/           # Work tracking
│   ├── feat/          #   Feature work tracking
│   ├── refactor/      #   Refactor work tracking
│   ├── fix/           #   Fix work tracking
│   └── archive/       #   Completed work (YYYY-MM-DD-<type>-<name>/)
├── issues/            # Issue records (pre-work-item)
│   └── archive/       #   Closed issues (name unchanged)
├── architecture.md    # System-wide architecture overview (example)
├── api-contracts/     # Shared API schemas, contracts (example)
└── onboarding/        # New-member onboarding guides (example)
```
"""


# ---------------------------------------------------------------------------
# Agent installation
# ---------------------------------------------------------------------------


def _resolve_skill_agents_dir() -> Path:
    """Return the path to this skill's agents/ directory.

    Resolves relative to this script's location:
      fullstack-init/scripts/workspace_init.py  →  fullstack-init/agents/
    """
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent / "agents"


def install_agents(
    target_root: Path,
    project_name: str,
    baseline: dict[str, str] | None = None,
    outcomes: dict[str, str] | None = None,
    force: bool = False,
) -> tuple[list[str], list[str]]:
    """Sync the workspace's `.agents/agents/` with the bundled agents.

    Each bundled `.md` gets `{project_name}` substituted and is refreshed
    three-way against `baseline` (the text written last time, keyed
    `agents/<name>.md`): an untouched file takes the new template, a file the
    user edited is kept, and a file both sides changed is kept while the new
    template goes to `.agents/init-pending/agents/`. With no baseline entry
    the file on disk is treated as the previous template — agent files were
    always regenerated before the baseline existed, so nobody could have kept
    edits in them. `force` overwrites unconditionally.

    Agents this skill generated in an earlier release but no longer
    generates are removed — a renamed role must not linger as a second,
    stale agent that delegation can still resolve to. The generated set is
    recorded in a manifest so the next release can do the same to it.

    `outcomes`, when given, receives `{name: three_way outcome}`; `baseline`,
    when given, is updated in place with the newly generated text.

    Returns (installed, pruned) agent-name lists.
    """
    source_dir = _resolve_skill_agents_dir()
    target_dir = target_root / ".agents" / "agents"
    ensure_directory(target_dir)

    agent_names: list[str] = []

    for src_file in sorted(source_dir.glob("*.md")):
        name = src_file.stem
        generated = src_file.read_text(encoding="utf-8").replace(
            "{project_name}", project_name
        )
        target = target_dir / f"{name}.md"
        existing = target.read_text(encoding="utf-8") if target.is_file() else None
        key = f"agents/{name}.md"
        previous = (baseline or {}).get(key, existing)
        if force:
            text, outcome = generated, "updated"
        else:
            text, outcome = three_way(existing, previous, generated)
        if text != existing:
            target.write_text(text, encoding="utf-8")
        if outcome == "conflict":
            write_pending(target_root, key, generated)
        if outcomes is not None:
            outcomes[name] = outcome
        if baseline is not None:
            baseline[key] = generated
        agent_names.append(name)

    pruned = prune_stale_agents(target_dir, set(agent_names))
    write_agent_manifest(target_dir, agent_names)

    return agent_names, pruned


def load_baseline(root: Path) -> dict[str, str] | None:
    """Return the per-unit text this script generated last time, or None."""
    path = root / ".agents" / BASELINE_FILENAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    units = data.get("units") if isinstance(data, dict) else None
    if not isinstance(units, dict):
        return None
    return {str(k): str(v) for k, v in units.items()}


def save_baseline(root: Path, units: dict[str, str]) -> None:
    """Record what this run generated, for the next run's three-way refresh."""
    path = root / ".agents" / BASELINE_FILENAME
    ensure_directory(path.parent)
    path.write_text(
        json.dumps({"version": 1, "units": units}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )


def write_pending(root: Path, unit: str, text: str) -> Path:
    """Write a template that could not be applied, for a by-hand merge."""
    path = root / ".agents" / PENDING_DIRNAME / unit
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def list_pending(root: Path) -> list[str]:
    """Return pending templates still waiting for a by-hand merge."""
    pending = root / ".agents" / PENDING_DIRNAME
    if not pending.is_dir():
        return []
    return sorted(
        str(path.relative_to(root)) for path in pending.rglob("*") if path.is_file()
    )


def resolve_readme_lang(root: Path, cli_lang: str | None) -> str:
    """Pick the README language: CLI flag, then saved config, then the file.

    The language is persisted so a re-run in another conversation language
    does not flip the README. A workspace that predates the setting keeps
    the language its current README is written in.
    """
    if cli_lang:
        return cli_lang
    saved = load_config(root).get("readme_lang")
    if saved in ("en", "zh"):
        return str(saved)
    readme = root / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        # The English README quotes Chinese trigger phrases, so a character
        # scan misreads it; the template's own headings do not.
        if "## 快速上手" in text:
            return "zh"
        if "## Quick Start" in text:
            return "en"
        return detect_language(text)
    return "en"


def prune_stale_agents(target_dir: Path, current_names: set[str]) -> list[str]:
    """Delete agent files this skill generated before but no longer generates.

    Only names recorded in the manifest — plus LEGACY_GENERATED_AGENTS, for
    workspaces created before the manifest existed — are candidates. Agent
    files written by the user under other names are never touched.
    """
    known = read_agent_manifest(target_dir) | set(LEGACY_GENERATED_AGENTS)
    pruned: list[str] = []

    for name in sorted(known - current_names):
        stale = target_dir / f"{name}.md"
        if stale.is_file():
            stale.unlink()
            pruned.append(name)

    return pruned


def read_agent_manifest(target_dir: Path) -> set[str]:
    """Return the agent names a previous run recorded as generated."""
    manifest = target_dir / AGENT_MANIFEST_NAME
    if not manifest.is_file():
        return set()
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    names = data.get("agents") if isinstance(data, dict) else None
    return set(names) if isinstance(names, list) else set()


def write_agent_manifest(target_dir: Path, agent_names: list[str]) -> None:
    """Record the generated agent set for the next run's pruning step."""
    manifest = target_dir / AGENT_MANIFEST_NAME
    manifest.write_text(
        json.dumps({"agents": sorted(agent_names)}, indent=2) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Infrastructure bootstrapping
# ---------------------------------------------------------------------------

def ensure_directory(path: Path) -> bool:
    """Create a directory if it doesn't exist. Return True if created."""
    if path.exists():
        return False
    path.mkdir(parents=True, exist_ok=True)
    return True


# ---------------------------------------------------------------------------
# Tool-specific agent symlinks
# ---------------------------------------------------------------------------

# Tools that support subagent discovery via <tool_dir>/agents/*.md
AGENT_SYMLINK_TOOLS: dict[str, str] = {
    "opencode": ".opencode/agents",
    "claude": ".claude/agents",
    "cursor": ".cursor/agents",
    "copilot": ".copilot/agents",
}


def create_agent_symlinks(root: Path) -> list[str]:
    """Create symlinks from tool-specific dirs to .agents/agents/.

    For each supported tool, ensures <tool_dir>/agents -> ../.agents/agents.
    Returns a list of status messages for the report.
    """
    agents_dir = root / ".agents" / "agents"
    if not agents_dir.is_dir():
        return []

    target = Path("..") / ".agents" / "agents"
    messages: list[str] = []

    expected = agents_dir.resolve()
    for tool_name, link_path in AGENT_SYMLINK_TOOLS.items():
        full_link = root / link_path

        # Already reaches .agents/agents — e.g. the whole tool directory is
        # itself a symlink to .agents. Nothing to do, nothing to report.
        if full_link.exists() and full_link.resolve() == expected:
            continue

        if full_link.is_symlink():
            resolved = full_link.resolve()
            expected = (root / ".agents" / "agents").resolve()
            if resolved == expected:
                continue
            full_link.unlink()
        elif full_link.is_dir():
            messages.append(
                f".{tool_name}/agents/ (skipped: directory already exists, "
                f"not a symlink)"
            )
            continue
        elif full_link.exists():
            full_link.unlink()

        parent = full_link.parent
        ensure_directory(parent)

        try:
            full_link.symlink_to(target, target_is_directory=True)
        except OSError as exc:
            messages.append(
                f".{tool_name}/agents/ (skipped: symlink failed — {exc})"
            )
            continue

        messages.append(f".{tool_name}/agents -> .agents/agents/")

    return messages


def _agent_baseline(
    previous: dict[str, str] | None, baseline: dict[str, str]
) -> dict[str, str]:
    """Seed the agent baseline: last run's agent texts, updated in place.

    `install_agents` reads the old text per file and overwrites the entry
    with the new one, so the dict it returns into is the next baseline.
    Without a previous baseline the entries are absent and each agent file on
    disk counts as the previous template.
    """
    if previous is not None:
        baseline.update(
            {key: text for key, text in previous.items() if key.startswith("agents/")}
        )
    return baseline


def _record_merge(
    report: dict[str, list[str]],
    root: Path,
    unit: str,
    generated: str,
    merge_report: dict[str, list[str]],
) -> None:
    """Fold a section merge report into the run report; park conflicts."""
    report["kept"].extend(f"{unit} → {item}" for item in merge_report["kept"])
    if merge_report["conflicts"] or merge_report["review"]:
        write_pending(root, unit, generated)
    for key in ("conflicts", "review"):
        for item in merge_report[key]:
            report[key].append(
                f"{unit} → {item} (template: .agents/{PENDING_DIRNAME}/{unit})"
            )


def bootstrap_workspace(
    root: Path,
    docs_dir: str | None = None,
    dry_run: bool = False,
    lang: str | None = None,
    github_repos: bool | None = None,
    force: bool = False,
) -> dict[str, list[str]]:
    """Bootstrap or update workspace infrastructure. Return a report.

    Design: every re-run is a three-way refresh (see the module docstring).
    Untouched generated units take the new template, user edits are kept,
    and units both sides changed are kept with the new template written to
    `.agents/init-pending/`. `--force` overwrites every generated unit.
    fullstack.json, docs dir content, scripts/, and .agents/skills/ are
    never overwritten.
    """
    report: dict[str, list[str]] = {
        "created": [],
        "updated": [],
        "skipped": [],
        "kept": [],
        "conflicts": [],
        "review": [],
    }

    project_name = root.name
    resolved_docs_dir = resolve_docs_dir(root, docs_dir)
    resolved_github = resolve_github_repos(root, github_repos)

    # --- Discover repos ---
    repos = discover_repos(root, resolved_docs_dir)
    if not repos:
        report["skipped"].append("No git repositories found in subdirectories")
        return report

    repo_infos = [analyze_repo(r) for r in repos]
    repos_table = build_repos_table(repo_infos)

    if dry_run:
        print(f"\n[dry-run] Found {len(repos)} repos:")
        for info in repo_infos:
            print(f"  - {info['name']} ({info['role']}, {info['tech_stack']})")
        print(f"\n[dry-run] Docs directory: {resolved_docs_dir}")
        print(f"[dry-run] GitHub repos: {resolved_github}")
        print(f"\n[dry-run] Would generate repos table:\n{repos_table}")
        return report

    # --- Save config ---
    readme_lang = resolve_readme_lang(root, lang)
    config = load_config(root)
    config["docs_dir"] = resolved_docs_dir
    config["github_repos"] = resolved_github
    config["readme_lang"] = readme_lang
    save_config(root, config)
    report["updated"].append(
        f"{CONFIG_FILENAME} (docs_dir: {resolved_docs_dir}, "
        f"github_repos: {resolved_github}, readme_lang: {readme_lang})"
    )
    previous = None if force else load_baseline(root)
    baseline: dict[str, str] = {}

    # --- Create-only directories (never overwrite contents) ---
    for dirname, desc in [
        (".agents/skills", "workspace-level skills"),
        (resolved_docs_dir, "shared documentation (independent repo)"),
        (f"{resolved_docs_dir}/changes", "work tracking container"),
        (f"{resolved_docs_dir}/changes/feat", "feature work tracking"),
        (f"{resolved_docs_dir}/changes/refactor", "refactor work tracking"),
        (f"{resolved_docs_dir}/changes/fix", "fix work tracking"),
        (f"{resolved_docs_dir}/changes/archive", "archived work"),
        (f"{resolved_docs_dir}/issues", "issue tracking"),
        (f"{resolved_docs_dir}/issues/archive", "archived issues"),
        ("scripts", "workspace-level scripts"),
    ]:
        if ensure_directory(root / dirname):
            report["created"].append(f"{dirname}/ ({desc})")

    # --- Init docs dir as git repo ---
    docs_path = root / resolved_docs_dir
    if not (docs_path / ".git").exists():
        subprocess.run(
            ["git", "init"], cwd=docs_path,
            capture_output=True, text=True, check=True,
        )
        report["created"].append(
            f"{resolved_docs_dir}/.git (initialized docs as independent repo)"
        )

    # --- Docs dir AGENTS.md (three-way by section; the lockstep pointer
    # is added when missing, so a workspace predating the rule still gets it)
    docs_agents = docs_path / "AGENTS.md"
    docs_unit = f"{resolved_docs_dir}/AGENTS.md"
    docs_generated = generate_docs_agents_md(resolved_docs_dir)
    baseline[docs_unit] = docs_generated
    if not docs_agents.exists():
        docs_agents.write_text(docs_generated, encoding="utf-8")
        report["created"].append(docs_unit)
    else:
        existing = docs_agents.read_text(encoding="utf-8")
        if force:
            patched = docs_generated
        else:
            merged, merge_report = merge_agents_md_report(
                existing,
                docs_generated,
                previous.get(docs_unit) if previous is not None else None,
                add_missing_without_baseline=False,
            )
            patched = inject_docs_lockstep(
                merged if merged.strip() != existing.strip() else existing
            )
            _record_merge(report, root, docs_unit, docs_generated, merge_report)
        if patched != existing:
            docs_agents.write_text(patched, encoding="utf-8")
            report["updated"].append(f"{docs_unit} (refreshed)")

    # --- .agents/agents/ (three-way per agent file) ---
    outcomes: dict[str, str] = {}
    agent_names, pruned_agents = install_agents(
        root,
        project_name,
        baseline=_agent_baseline(previous, baseline),
        outcomes=outcomes,
        force=force,
    )
    for name, outcome in outcomes.items():
        unit = f".agents/agents/{name}.md"
        if outcome in ("created", "updated"):
            report["updated"].append(unit)
        elif outcome == "kept":
            report["kept"].append(unit)
        elif outcome == "conflict":
            report["conflicts"].append(
                f"{unit} → .agents/{PENDING_DIRNAME}/agents/{name}.md"
            )
    if pruned_agents:
        report["updated"].append(
            ".agents/agents/ (removed stale agents: "
            f"{', '.join(n + '.md' for n in pruned_agents)})"
        )

    # --- Tool-specific agent symlinks ---
    symlink_messages = create_agent_symlinks(root)
    if symlink_messages:
        report["updated"].extend(symlink_messages)

    # --- AGENTS.md (three-way by section / bullet / repo row) ---
    agents_md_path = root / "AGENTS.md"
    new_agents_md = upgrade_legacy_skill_commands(
        generate_agents_md(project_name, repos_table, resolved_docs_dir)
    )
    baseline["AGENTS.md"] = new_agents_md
    if not force and agents_md_path.exists():
        existing = agents_md_path.read_text(encoding="utf-8")
        merged, merge_report = merge_agents_md_report(
            existing,
            new_agents_md,
            previous.get("AGENTS.md") if previous is not None else None,
        )
        merged = upgrade_legacy_skill_commands(merged)
        if merged.strip() != existing.strip():
            agents_md_path.write_text(merged, encoding="utf-8")
            report["updated"].append("AGENTS.md (merged three-way)")
        _record_merge(report, root, "AGENTS.md", new_agents_md, merge_report)
    else:
        agents_md_path.write_text(new_agents_md, encoding="utf-8")
        report["updated"].append("AGENTS.md")

    # --- README.md (three-way as a whole file) ---
    readme_path = root / "README.md"
    readme_generated = generate_readme(project_name, resolved_docs_dir, readme_lang)
    baseline["README.md"] = readme_generated
    existing_readme = (
        readme_path.read_text(encoding="utf-8") if readme_path.is_file() else None
    )
    if force:
        readme_text, readme_outcome = readme_generated, "updated"
    else:
        # No baseline means no record of what this script wrote: a README
        # on disk may be the user's own, so it is never treated as an old
        # template (that would overwrite it). It is kept and the template
        # parked, like every other unit without a baseline.
        readme_previous = (
            previous.get("README.md") if previous is not None else None
        )
        readme_text, readme_outcome = three_way(
            existing_readme, readme_previous, readme_generated
        )
    if readme_text != existing_readme:
        readme_path.write_text(readme_text, encoding="utf-8")
        report["updated"].append("README.md")
    elif readme_outcome == "kept":
        report["kept"].append("README.md")
    elif readme_outcome == "conflict":
        write_pending(root, "README.md", readme_generated)
        report["conflicts" if previous is not None else "review"].append(
            f"README.md (template: .agents/{PENDING_DIRNAME}/README.md)"
        )

    save_baseline(root, baseline)
    reported = " ".join(report["conflicts"] + report["review"])
    for pending in list_pending(root):
        if pending not in reported:
            report["conflicts"].append(
                f"{pending} (still waiting from an earlier run — merge it by "
                "hand, then delete the file)"
            )

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def format_report(report: dict[str, list[str]]) -> str:
    """Format the bootstrap report for display."""
    sections = [
        ("created", "Created:", "+"),
        ("updated", "Refreshed:", "~"),
        ("kept", "Kept your edits:", "="),
        ("conflicts", "Needs a by-hand merge (template changed AND you edited):", "!"),
        (
            "review",
            "Differs from the current template — first run with a baseline, "
            "review once (your edit, or an update this workspace missed?):",
            "?",
        ),
        ("skipped", "Unchanged:", "-"),
    ]
    lines = []
    for key, title, mark in sections:
        items = report.get(key) or []
        if items:
            lines.append(title)
            lines.extend(f"  {mark} {item}" for item in items)
    return "\n".join(lines)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize or update a multi-repo fullstack workspace.",
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Workspace root directory (default: current directory)",
    )
    parser.add_argument(
        "--docs-dir",
        default=None,
        help=(
            "Name of the shared documentation directory "
            "(default: value from fullstack.json, or 'central-docs')"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--lang",
        default=None,
        choices=["en", "zh"],
        help=(
            "Language for generated README.md ('en' or 'zh'). Saved to "
            "fullstack.json; omit it on re-runs to keep the saved language."
        ),
    )
    parser.add_argument(
        "--github",
        action="store_true",
        default=None,
        help="Mark repos as GitHub / GitHub Enterprise hosted (enables PR creation in fullstack-apply)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help=(
            "Overwrite every generated file with the template, discarding "
            "edits (default: three-way refresh)"
        ),
    )
    parser.add_argument(
        "--no-github",
        action="store_true",
        default=False,
        help="Mark repos as NOT GitHub hosted (disables PR creation in fullstack-apply)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output report as JSON",
    )

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    github_repos: bool | None = None
    if args.github:
        github_repos = True
    elif args.no_github:
        github_repos = False

    try:
        report = bootstrap_workspace(
            root,
            docs_dir=args.docs_dir,
            dry_run=args.dry_run,
            lang=args.lang,
            github_repos=github_repos,
            force=args.force,
        )
    except WorkspaceConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print(f"\nWorkspace: {root}")
        print(f"{'=' * 60}")
        print(format_report(report))
        print()


if __name__ == "__main__":
    main()
