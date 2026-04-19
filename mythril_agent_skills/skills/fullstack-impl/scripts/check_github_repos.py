#!/usr/bin/env python3
"""Check whether the fullstack workspace repos are GitHub-hosted.

Reads fullstack.json from the workspace root and outputs a deterministic
machine-readable result. This removes any LLM guessing — the answer comes
directly from the config file set during fullstack-init.

Usage:
    python3 check_github_repos.py [workspace-root]

Output (machine-readable key=value lines):
    GITHUB_REPOS=true|false
    CONFIG_PATH=<path>           (path to fullstack.json that was read)
    CONFIG_FOUND=true|false      (whether fullstack.json exists)

Exit codes:
    0 — config read successfully (check GITHUB_REPOS for the value)
    1 — fullstack.json not found (workspace not initialized)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def check_github_repos(root: Path) -> dict[str, str]:
    """Read fullstack.json and return github_repos status."""
    config_path = root / "fullstack.json"

    if not config_path.is_file():
        return {
            "GITHUB_REPOS": "false",
            "CONFIG_PATH": str(config_path),
            "CONFIG_FOUND": "false",
        }

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "GITHUB_REPOS": "false",
            "CONFIG_PATH": str(config_path),
            "CONFIG_FOUND": "true",
        }

    github_repos = config.get("github_repos", False)
    return {
        "GITHUB_REPOS": "true" if github_repos else "false",
        "CONFIG_PATH": str(config_path),
        "CONFIG_FOUND": "true",
    }


def main() -> None:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

    result = check_github_repos(root)
    for key, value in result.items():
        print(f"{key}={value}")

    if result["CONFIG_FOUND"] == "false":
        sys.exit(1)


if __name__ == "__main__":
    main()
