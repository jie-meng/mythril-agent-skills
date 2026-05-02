#!/usr/bin/env python3
"""Validate a fullstack workspace and report key configuration in one call.

This script is the single source of truth for the Workspace Validation Gate
defined in fullstack-impl/SKILL.md. It replaces ad-hoc LLM checks of
"does fullstack.json exist", "does AGENTS.md exist", etc. with a
deterministic answer.

It also reports the github_repos flag (used in Step 8) and the docs_dir
name (used to locate work directories), so a single invocation gives the
agent everything it needs to start routing.

Usage:
    python3 check_workspace.py [workspace-root]

Output (machine-readable key=value lines):
    WORKSPACE_VALID=true|false
    MISSING=<comma-separated list of missing markers, empty if valid>
    CONFIG_FOUND=true|false
    CONFIG_PATH=<path>
    DOCS_DIR=<name or empty>
    GITHUB_REPOS=true|false

Exit codes:
    0 — workspace is valid
    1 — workspace is invalid (one or more markers missing OR config corrupt)
    2 — invalid arguments
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE_MARKERS = ("fullstack.json", "AGENTS.md", ".agents")


def check_workspace(root: Path) -> dict[str, str]:
    """Run all workspace gate checks and return a result dict."""
    missing: list[str] = []
    for marker in WORKSPACE_MARKERS:
        path = root / marker
        if marker == ".agents":
            if not path.is_dir():
                missing.append(marker)
        else:
            if not path.is_file():
                missing.append(marker)

    config_path = root / "fullstack.json"
    config_found = config_path.is_file()
    docs_dir = ""
    github_repos = "false"

    if config_found:
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            docs_dir = str(config.get("docs_dir", ""))
            github_repos = "true" if config.get("github_repos", False) else "false"
        except (json.JSONDecodeError, OSError):
            if "fullstack.json" not in missing:
                missing.append("fullstack.json (corrupt)")

    return {
        "WORKSPACE_VALID": "true" if not missing else "false",
        "MISSING": ",".join(missing),
        "CONFIG_FOUND": "true" if config_found else "false",
        "CONFIG_PATH": str(config_path),
        "DOCS_DIR": docs_dir,
        "GITHUB_REPOS": github_repos,
    }


def main() -> int:
    if len(sys.argv) > 2:
        print(
            "Usage: check_workspace.py [workspace-root]",
            file=sys.stderr,
        )
        return 2

    root = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path.cwd()
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2

    result = check_workspace(root)
    for key, value in result.items():
        print(f"{key}={value}")

    return 0 if result["WORKSPACE_VALID"] == "true" else 1


if __name__ == "__main__":
    sys.exit(main())
