#!/usr/bin/env python3
"""Initialize or update a multi-repo fullstack workspace.

Scans a root directory for git repositories, analyzes their README.md and
AGENTS.md files, and creates/updates a root-level AGENTS.md with a unified
project table. Also bootstraps .gitignore, shared docs dir, .agents/, and
scripts/ directories as needed.

The shared docs directory name is user-configurable (defaults to
"central-docs") and persisted in .fullstack-init.json so re-runs pick it
up automatically.

Designed for idempotent operation: running it multiple times preserves
user-added content while updating the auto-generated repo table and merging
new repos.

Uses only Python 3.10+ standard library (zero dependencies).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_FILENAME = ".fullstack-init.json"

MARKER_START = "<!-- fullstack-init:repos-table:start -->"
MARKER_END = "<!-- fullstack-init:repos-table:end -->"

FIXED_INFRA_DIRS = {
    ".agents",
    ".git",
    "scripts",
    "node_modules",
    "__pycache__",
}

DEFAULT_DOCS_DIR = "central-docs"


# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------

def load_config(root: Path) -> dict[str, str]:
    """Load workspace config from .fullstack-init.json."""
    config_path = root / CONFIG_FILENAME
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(root: Path, config: dict[str, str]) -> None:
    """Save workspace config to .fullstack-init.json."""
    config_path = root / CONFIG_FILENAME
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def resolve_docs_dir(
    root: Path,
    cli_docs_dir: str | None,
) -> str:
    """Determine the docs directory name from CLI arg, saved config, or default.

    Priority:
    1. Explicit CLI argument (--docs-dir)
    2. Previously saved value in .fullstack-init.json
    3. Default: "central-docs"
    """
    if cli_docs_dir:
        return cli_docs_dir

    config = load_config(root)
    saved = config.get("docs_dir")
    if saved:
        return saved

    return DEFAULT_DOCS_DIR


# ---------------------------------------------------------------------------
# Infrastructure dir set (dynamic based on docs dir)
# ---------------------------------------------------------------------------

def get_infrastructure_dirs(docs_dir: str) -> set[str]:
    """Return the full set of infrastructure directory names to exclude."""
    return FIXED_INFRA_DIRS | {docs_dir}


# ---------------------------------------------------------------------------
# Repo discovery and analysis
# ---------------------------------------------------------------------------

def is_git_repo(path: Path) -> bool:
    """Check if a directory is a git repository."""
    return (path / ".git").exists()


def discover_repos(root: Path, docs_dir: str) -> list[Path]:
    """Find all immediate subdirectory git repos under root."""
    infra_dirs = get_infrastructure_dirs(docs_dir)
    repos = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in infra_dirs:
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
# AGENTS.md generation and merging
# ---------------------------------------------------------------------------

def build_repos_table(repos: list[dict[str, str]]) -> str:
    """Build a Markdown table from repo metadata."""
    lines = [
        MARKER_START,
        "",
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
    lines.append("")
    lines.append(MARKER_END)
    return "\n".join(lines)


def generate_fresh_agents_md(
    project_name: str,
    repos_table: str,
    docs_dir: str,
) -> str:
    """Generate a full AGENTS.md for a new workspace."""
    return f"""\
# {project_name}

## Project Overview

This is a multi-repo fullstack workspace. Each subdirectory is an independent
git repository for a specific platform or service.

## Repositories

{repos_table}

## Workspace Conventions

- **Cross-repo changes**: When making changes that span multiple repos,
  commit and test each repo independently.
- **Shared documentation**: Cross-cutting docs live in `{docs_dir}/`.
- **Scripts**: Workspace-level automation lives in `scripts/`.

## Directory Structure

```
{project_name}/
├── AGENTS.md          # This file — workspace-level AI guidelines
├── README.md          # Human-readable project overview
├── .gitignore         # Tracks only workspace-level files
├── .agents/           # Workspace-level agents and skills
│   └── skills/        # Custom skills for this workspace
├── {docs_dir + "/":<23s}# Shared documentation across repos
│   └── AGENTS.md      # Documentation management guidelines
├── scripts/           # Workspace-level automation scripts
└── <repos...>/        # Individual git repositories
```
"""


def merge_repos_table(existing_content: str, new_table: str) -> str:
    """Replace the repo table between markers, preserving everything else."""
    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        re.DOTALL,
    )
    if pattern.search(existing_content):
        return pattern.sub(new_table, existing_content)
    sections = existing_content.split("\n## ")
    for i, section in enumerate(sections):
        if section.strip().lower().startswith("repositor"):
            heading_line = section.split("\n", 1)[0]
            rest = section.split("\n", 1)[1] if "\n" in section else ""
            old_table_match = re.search(
                r"\|.*?\n\|[-| ]+\n(?:\|.*?\n)*", rest
            )
            if old_table_match:
                new_rest = (
                    rest[: old_table_match.start()]
                    + new_table
                    + "\n"
                    + rest[old_table_match.end() :]
                )
                sections[i] = heading_line + "\n" + new_rest
                return "\n## ".join(sections)
            sections[i] = heading_line + "\n\n" + new_table + "\n" + rest
            return "\n## ".join(sections)
    return existing_content.rstrip("\n") + "\n\n## Repositories\n\n" + new_table + "\n"


# ---------------------------------------------------------------------------
# .gitignore management
# ---------------------------------------------------------------------------

def generate_gitignore(docs_dir: str) -> str:
    """Generate .gitignore content with the actual docs directory name."""
    return f"""\
# =============================================================================
# Fullstack workspace .gitignore
# Generated by fullstack-init — manages only workspace-level files.
# All subdirectory repos have their own version control.
# =============================================================================

# Include workspace infrastructure (these are NOT ignored)
!AGENTS.md
!README.md
!.gitignore
!.fullstack-init.json
!.agents/
!.agents/**
!scripts/
!scripts/**
!{docs_dir}/
!{docs_dir}/**

# Ignore everything else (sub-repos have their own git)
*

# OS / editor junk (even in tracked dirs)
.DS_Store
Thumbs.db
*.swp
*.swo
*~
"""


def needs_gitignore_update(gitignore_path: Path, docs_dir: str) -> bool:
    """Check if .gitignore needs updating (missing or lacks key patterns)."""
    if not gitignore_path.exists():
        return True
    content = gitignore_path.read_text(encoding="utf-8", errors="replace")
    key_patterns = ["!AGENTS.md", f"!{docs_dir}/", "!.agents/"]
    return not all(p in content for p in key_patterns)


# ---------------------------------------------------------------------------
# Docs directory AGENTS.md
# ---------------------------------------------------------------------------

def generate_docs_agents_md(docs_dir: str) -> str:
    """Generate an AGENTS.md for the shared docs directory."""
    title = docs_dir.replace("-", " ").replace("_", " ").title()
    return f"""\
# {title}

This directory holds shared documentation that spans multiple repositories
in this workspace. It is version-controlled by the workspace-level git repo.

## Conventions

- Use Markdown for all documents.
- Organize by topic or domain, not by repo.
- Link to repo-specific docs using relative paths: `../repo-name/docs/...`
- Keep documents concise; deep-dive details belong in the relevant repo.

## Structure

```
{docs_dir}/
├── AGENTS.md          # This file
├── architecture.md    # System-wide architecture overview (example)
├── api-contracts/     # Shared API schemas, contracts (example)
└── onboarding/        # New-member onboarding guides (example)
```
"""


# ---------------------------------------------------------------------------
# Infrastructure bootstrapping
# ---------------------------------------------------------------------------

def ensure_directory(path: Path, description: str) -> bool:
    """Create a directory if it doesn't exist. Return True if created."""
    if path.exists():
        return False
    path.mkdir(parents=True, exist_ok=True)
    return True


def bootstrap_workspace(
    root: Path,
    docs_dir: str | None = None,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    """Bootstrap or update workspace infrastructure. Return a report."""
    report: dict[str, list[str]] = {
        "created": [],
        "updated": [],
        "skipped": [],
    }

    project_name = root.name
    resolved_docs_dir = resolve_docs_dir(root, docs_dir)

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
        print(f"\n[dry-run] Would generate repos table:\n{repos_table}")
        return report

    # --- .git init ---
    if not (root / ".git").exists():
        subprocess.run(
            ["git", "init"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        report["created"].append(".git (initialized workspace git repo)")

    # --- Save config ---
    config = load_config(root)
    old_docs_dir = config.get("docs_dir")
    config["docs_dir"] = resolved_docs_dir
    save_config(root, config)
    if old_docs_dir != resolved_docs_dir:
        if old_docs_dir:
            report["updated"].append(
                f"{CONFIG_FILENAME} (docs_dir: {old_docs_dir} → {resolved_docs_dir})"
            )
        else:
            report["created"].append(
                f"{CONFIG_FILENAME} (docs_dir: {resolved_docs_dir})"
            )
    else:
        report["skipped"].append(f"{CONFIG_FILENAME} (unchanged)")

    # --- Directories ---
    for dirname, desc in [
        (".agents/skills", "workspace-level skills"),
        (resolved_docs_dir, "shared documentation"),
        ("scripts", "workspace-level scripts"),
    ]:
        path = root / dirname
        if ensure_directory(path, desc):
            report["created"].append(f"{dirname}/ ({desc})")
        else:
            report["skipped"].append(f"{dirname}/ (already exists)")

    # --- docs dir AGENTS.md ---
    docs_agents = root / resolved_docs_dir / "AGENTS.md"
    if not docs_agents.exists():
        docs_agents.write_text(
            generate_docs_agents_md(resolved_docs_dir), encoding="utf-8"
        )
        report["created"].append(f"{resolved_docs_dir}/AGENTS.md")
    else:
        report["skipped"].append(f"{resolved_docs_dir}/AGENTS.md (already exists)")

    # --- .gitignore ---
    gitignore_path = root / ".gitignore"
    if needs_gitignore_update(gitignore_path, resolved_docs_dir):
        already_exists = gitignore_path.exists()
        gitignore_path.write_text(
            generate_gitignore(resolved_docs_dir), encoding="utf-8"
        )
        action = "updated" if already_exists else "created"
        report[action].append(".gitignore")
    else:
        report["skipped"].append(".gitignore (up to date)")

    # --- AGENTS.md ---
    agents_path = root / "AGENTS.md"
    if agents_path.exists():
        existing = agents_path.read_text(encoding="utf-8", errors="replace")
        updated = merge_repos_table(existing, repos_table)
        if updated != existing:
            agents_path.write_text(updated, encoding="utf-8")
            report["updated"].append("AGENTS.md (repos table refreshed)")
        else:
            report["skipped"].append("AGENTS.md (repos table unchanged)")
    else:
        content = generate_fresh_agents_md(project_name, repos_table, resolved_docs_dir)
        agents_path.write_text(content, encoding="utf-8")
        report["created"].append("AGENTS.md")

    # --- README.md ---
    readme_path = root / "README.md"
    if not readme_path.exists():
        readme_content = f"# {project_name}\n\nMulti-repo fullstack workspace.\n"
        readme_path.write_text(readme_content, encoding="utf-8")
        report["created"].append("README.md")
    else:
        report["skipped"].append("README.md (already exists)")

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
        lines.append("Updated:")
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
            "(default: value from .fullstack-init.json, or 'central-docs')"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
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

    report = bootstrap_workspace(root, docs_dir=args.docs_dir, dry_run=args.dry_run)

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print(f"\nWorkspace: {root}")
        print(f"{'=' * 60}")
        print(format_report(report))
        print()


if __name__ == "__main__":
    main()
