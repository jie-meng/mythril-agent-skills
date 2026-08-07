#!/usr/bin/env python3
"""Initialize or update a multi-repo fullstack workspace.

Scans a root directory for git repositories, analyzes their README.md and
AGENTS.md files, and generates workspace-level infrastructure: AGENTS.md,
agent templates, and shared docs directory.

Design: every run is a full refresh. AGENTS.md, README.md, and agent
templates are regenerated from scratch. The only persistent state is
fullstack.json (stores docs_dir). The docs directory and user directories
(scripts/, .agents/skills/) are created if missing but never overwritten.

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


# ---------------------------------------------------------------------------
# Config persistence (fullstack.json is the ONLY persistent state)
# ---------------------------------------------------------------------------

def load_config(root: Path) -> dict[str, str]:
    """Load workspace config from fullstack.json (with legacy fallback)."""
    config_path = root / CONFIG_FILENAME
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    legacy_path = root / LEGACY_CONFIG_FILENAME
    if legacy_path.exists():
        try:
            return json.loads(legacy_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
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


def resolve_docs_dir(root: Path, cli_docs_dir: str | None) -> str:
    """Determine docs dir: CLI arg > saved config > default."""
    if cli_docs_dir:
        return cli_docs_dir
    config = load_config(root)
    saved = config.get("docs_dir")
    if saved:
        return saved
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


def generate_agents_md(
    project_name: str,
    repos_table: str,
    docs_dir: str,
) -> str:
    """Generate the workspace-level AGENTS.md (always from scratch)."""
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
- **Knowledge Graph (graphify)**: Some repos may have a `graphify-out/`
  directory generated by the `graphify` skill — a knowledge graph of the
  codebase for fast, accurate information retrieval and cross-file
  relationship analysis.
  - **Check for graphify-out/**: Run
    `python3 SKILL_PATH/scripts/graphify_check.py <repo-path>` to check
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
├── plan.md            # Implementation plan (repos, tasks, Success Criteria)
├── progress.md        # Dated change log (status, completed steps, blockers)
└── review.md          # Review findings, Evidence table, verdict
```

Work directories are **never deleted** — they serve as project history.
Archived work lives under `{docs_dir}/changes/archive/`. The
`{docs_dir}/` repo does NOT use feature branches — all work tracking
docs are committed directly to its main branch.

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
python3 ~/.<agent>/skills/fullstack-propose/scripts/mermaid_lint.py \\
    path/to/file.md
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
│   │   ├── developer.md
│   │   ├── reviewer.md
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

    for line in lines:
        stripped = line.strip()
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


def _merge_conventions(existing_section: str, generated_section: str) -> str:
    """Merge Workspace Conventions sections.

    Keeps all existing bullets, appends any new ones from generated that have
    a bold title (e.g., "- **Knowledge Graph (graphify)**:") not present in
    the existing section.
    """

    def _extract_bullet_titles(text: str) -> set[str]:
        """Extract the first bold title from each bullet."""
        titles: set[str] = set()
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- **"):
                end = stripped.find("**", 4)
                if end > 0:
                    titles.add(stripped[3 : end + 2])
        return titles

    def _extract_bullet_blocks(text: str) -> list[str]:
        """Split a section body into individual bullet blocks."""
        blocks: list[str] = []
        current: list[str] = []
        heading_found = False

        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## ") and not heading_found:
                heading_found = True
                continue
            if not heading_found:
                continue
            if stripped.startswith("- "):
                if current:
                    blocks.append("\n".join(current))
                current = [line]
            elif current:
                current.append(line)

        if current:
            blocks.append("\n".join(current))
        return blocks

    existing_titles = _extract_bullet_titles(existing_section)
    generated_blocks = _extract_bullet_blocks(generated_section)

    new_blocks: list[str] = []
    for block in generated_blocks:
        block_lines = block.strip().split("\n")
        if block_lines:
            first = block_lines[0].strip()
            if first.startswith("- **"):
                end = first.find("**", 4)
                if end > 0:
                    title = first[3 : end + 2]
                    if title not in existing_titles:
                        new_blocks.append(block)

    if not new_blocks:
        return existing_section

    existing_lines = existing_section.rstrip().split("\n")
    existing_lines.append("")
    for block in new_blocks:
        existing_lines.append(block.rstrip())

    return "\n".join(existing_lines)


def merge_agents_md(existing: str, generated: str) -> str:
    """Incrementally merge an existing AGENTS.md with a freshly generated template.

    Merge rules:
    - Repositories section: always replace with generated (new repos may appear)
    - Directory Structure section: always replace with generated
    - Workspace Conventions: merge bullet points (keep existing, add new ones)
    - New H2 sections (only in generated): insert at the expected position
    - User-only H2 sections (only in existing): preserve (append after generated)
    - Everything else: keep existing content (may be user-customized)
    """
    existing_h1, existing_sections = parse_agents_md_sections(existing)
    generated_h1, generated_sections = parse_agents_md_sections(generated)

    existing_map: dict[str, str] = {}
    for title, body in existing_sections:
        existing_map[title[3:]] = body

    REPLACE_SECTIONS = {"Repositories", "Directory Structure"}
    MERGE_SECTIONS = {"Workspace Conventions"}

    merged: list[tuple[str, str]] = []
    seen_keys: set[str] = set()

    for gen_title, gen_body in generated_sections:
        key = gen_title[3:]
        seen_keys.add(key)

        if key in REPLACE_SECTIONS:
            merged.append((gen_title, gen_body))
        elif key in MERGE_SECTIONS and key in existing_map:
            merged.append(
                (gen_title, _merge_conventions(existing_map[key], gen_body))
            )
        elif key in existing_map:
            merged.append((gen_title, existing_map[key]))
        else:
            merged.append((gen_title, gen_body))

    for title, body in existing_sections:
        key = title[3:]
        if key not in seen_keys:
            merged.append((title, body))

    result_lines = [existing_h1 or generated_h1, ""]
    for title, body in merged:
        result_lines.append(body.strip())
        result_lines.append("")

    return "\n".join(result_lines)


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

### Archive completed work

When a work item is done, use `fullstack-archive`:

```
> Archive the dark mode feature
> 归档登录崩溃修复
```

The skill moves the work directory into
`{docs_dir}/changes/archive/YYYY-MM-DD-<type>-<name>/`.

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

### 归档已完成的工作

工作项完成后，使用 `fullstack-archive`：

```
> 归档暗色模式功能
> Archive the login crash fix
```

技能会把工作目录移动到
`{docs_dir}/changes/archive/YYYY-MM-DD-<type>-<name>/`。

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

Each work item gets its own subdirectory:

```
<category>/<work-name>/
├── analysis.md   # Technical analysis (why and how)
├── plan.md       # Requirements, Success Criteria, implementation plan
├── progress.md   # Dated change log
└── review.md     # Review findings, Evidence table, verdict (append-only)
```

These directories are **never deleted** — they form the project's
implementation history. Archived work stays in `changes/archive/`. Do
not modify docs created by other work items.

## Structure

```
{docs_dir}/
├── AGENTS.md          # This file
├── changes/           # Work tracking
│   ├── feat/          #   Feature work tracking
│   ├── refactor/      #   Refactor work tracking
│   ├── fix/           #   Fix work tracking
│   └── archive/       #   Completed work (YYYY-MM-DD-<type>-<name>/)
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


def install_agents(target_root: Path, project_name: str) -> list[str]:
    """Copy agent .md files from the skill's agents/ dir to the workspace.

    Reads each .md file from the bundled agents directory, replaces
    {project_name}, and writes to <workspace>/.agents/agents/<name>.md.
    Returns a sorted list of installed agent names.
    """
    source_dir = _resolve_skill_agents_dir()
    target_dir = target_root / ".agents" / "agents"
    ensure_directory(target_dir)

    agent_names: list[str] = []

    for src_file in sorted(source_dir.glob("*.md")):
        name = src_file.stem
        content = src_file.read_text(encoding="utf-8")
        content = content.replace("{project_name}", project_name)
        (target_dir / f"{name}.md").write_text(content, encoding="utf-8")
        agent_names.append(name)

    return agent_names


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

    for tool_name, link_path in AGENT_SYMLINK_TOOLS.items():
        full_link = root / link_path

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


def bootstrap_workspace(
    root: Path,
    docs_dir: str | None = None,
    dry_run: bool = False,
    lang: str = "en",
    github_repos: bool | None = None,
    force: bool = False,
) -> dict[str, list[str]]:
    """Bootstrap or update workspace infrastructure. Return a report.

    Design: every run is a full refresh. Generated files are overwritten
    except AGENTS.md, which is merged incrementally when it already exists
    (--force bypasses the merge and does a full overwrite).
    Only fullstack.json, docs dir content, scripts/, and .agents/skills/
    are preserved across runs.
    """
    report: dict[str, list[str]] = {
        "created": [],
        "updated": [],
        "skipped": [],
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
    config = load_config(root)
    config["docs_dir"] = resolved_docs_dir
    config["github_repos"] = resolved_github
    save_config(root, config)
    report["updated"].append(
        f"{CONFIG_FILENAME} (docs_dir: {resolved_docs_dir}, github_repos: {resolved_github})"
    )

    # --- Create-only directories (never overwrite contents) ---
    for dirname, desc in [
        (".agents/skills", "workspace-level skills"),
        (resolved_docs_dir, "shared documentation (independent repo)"),
        (f"{resolved_docs_dir}/changes", "work tracking container"),
        (f"{resolved_docs_dir}/changes/feat", "feature work tracking"),
        (f"{resolved_docs_dir}/changes/refactor", "refactor work tracking"),
        (f"{resolved_docs_dir}/changes/fix", "fix work tracking"),
        (f"{resolved_docs_dir}/changes/archive", "archived work"),
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

    # --- Docs dir AGENTS.md (create-only — user may customize) ---
    docs_agents = docs_path / "AGENTS.md"
    if not docs_agents.exists():
        docs_agents.write_text(
            generate_docs_agents_md(resolved_docs_dir), encoding="utf-8"
        )
        report["created"].append(f"{resolved_docs_dir}/AGENTS.md")

    # === REGENERATED FILES (always overwrite) ===

    # --- .agents/agents/ (copy from bundled agents/) ---
    agent_names = install_agents(root, project_name)
    report["updated"].append(
        f".agents/agents/ ({', '.join(agent_names)})"
    )

    # --- Tool-specific agent symlinks ---
    symlink_messages = create_agent_symlinks(root)
    if symlink_messages:
        report["updated"].extend(symlink_messages)
    # --- AGENTS.md ---
    agents_md_path = root / "AGENTS.md"
    new_agents_md = generate_agents_md(project_name, repos_table, resolved_docs_dir)
    if not force and agents_md_path.exists():
        existing = agents_md_path.read_text(encoding="utf-8")
        merged = merge_agents_md(existing, new_agents_md)
        agents_md_path.write_text(merged, encoding="utf-8")
        report["updated"].append("AGENTS.md (merged incrementally)")
    else:
        agents_md_path.write_text(new_agents_md, encoding="utf-8")
        report["updated"].append("AGENTS.md")

    # --- README.md (full refresh) ---
    (root / "README.md").write_text(
        generate_readme(project_name, resolved_docs_dir, lang), encoding="utf-8"
    )
    report["updated"].append("README.md")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def format_report(report: dict[str, list[str]]) -> str:
    """Format the bootstrap report for display."""
    lines = []
    if report["created"]:
        lines.append("Created:")
        for item in report["created"]:
            lines.append(f"  + {item}")
    if report["updated"]:
        lines.append("Regenerated:")
        for item in report["updated"]:
            lines.append(f"  ~ {item}")
    if report["skipped"]:
        lines.append("Unchanged:")
        for item in report["skipped"]:
            lines.append(f"  - {item}")
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
        help="Language for generated README.md ('en' or 'zh'). Default: en.",
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
        help="Full overwrite of AGENTS.md instead of incremental merge",
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

    lang = args.lang or "en"
    report = bootstrap_workspace(
        root,
        docs_dir=args.docs_dir,
        dry_run=args.dry_run,
        lang=lang,
        github_repos=github_repos,
        force=args.force,
    )

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print(f"\nWorkspace: {root}")
        print(f"{'=' * 60}")
        print(format_report(report))
        print()


if __name__ == "__main__":
    main()
