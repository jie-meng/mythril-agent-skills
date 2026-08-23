#!/usr/bin/env python3
"""Detect whether a directory is a fullstack workspace, a single repo, or neither.

fullstack-brief works in two modes: workspace mode exports the context of
every repo in an initialized fullstack workspace; single-repo mode exports
the context of one repository. This script is the deterministic front door
that decides which mode applies, replacing ad-hoc LLM checks of "does
fullstack.json exist" / "is there a .git here".

A directory with ALL workspace markers is a workspace. Anything else that
contains .git falls back to single-repo mode; only a directory with neither
yields SCOPE=none.

Usage:
    python3 detect_scope.py [root]

Output (machine-readable key=value lines):
    SCOPE=workspace|repo|none
    ROOT=<path used for detection>
    DOCS_DIR=<name or empty>       (workspace mode, from fullstack.json)
    GITHUB_REPOS=true|false        (workspace mode, from fullstack.json)
    IS_GIT=true|false              (whether ROOT itself is a git repo)

Exit codes:
    0 — scope detected (workspace or repo)
    1 — no usable scope found
    2 — invalid arguments
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE_MARKERS = ("fullstack.json", "AGENTS.md", ".agents")


def _missing_markers(root: Path) -> list[str]:
    """Return workspace markers absent from root."""
    missing: list[str] = []
    for marker in WORKSPACE_MARKERS:
        path = root / marker
        if marker == ".agents":
            ok = path.is_dir()
        else:
            ok = path.is_file()
        if not ok:
            missing.append(marker)
    return missing


def read_workspace_config(root: Path) -> tuple[str, str]:
    """Read fullstack.json, returning (docs_dir, github_repos) as strings.

    Returns empty/false values when the file is missing or corrupt.
    """
    config_path = root / "fullstack.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "", "false"
    docs_dir = str(config.get("docs_dir", ""))
    github_repos = "true" if config.get("github_repos", False) else "false"
    return docs_dir, github_repos


def detect_scope(root: Path) -> dict[str, str]:
    """Run all scope checks and return a result dict."""
    result: dict[str, str] = {
        "SCOPE": "none",
        "ROOT": str(root),
        "DOCS_DIR": "",
        "GITHUB_REPOS": "false",
        "IS_GIT": "true" if (root / ".git").exists() else "false",
    }
    if _missing_markers(root):
        if result["IS_GIT"] == "true":
            result["SCOPE"] = "repo"
        return result

    result["SCOPE"] = "workspace"
    docs_dir, github_repos = read_workspace_config(root)
    result["DOCS_DIR"] = docs_dir
    result["GITHUB_REPOS"] = github_repos
    return result


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print(
            "Usage: detect_scope.py [root]",
            file=sys.stderr,
        )
        return 2

    root = Path(args[0]).resolve() if len(args) == 1 else Path.cwd()
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2

    result = detect_scope(root)
    for key, value in result.items():
        print(f"{key}={value}")

    return 0 if result["SCOPE"] != "none" else 1


if __name__ == "__main__":
    sys.exit(main())
