#!/usr/bin/env python3
"""Check whether the fullstack workspace repos are GitHub-hosted.

Backward-compatible thin wrapper around `check_workspace.py`. Step 8 of
SKILL.md historically calls this script with a fixed candidate-path lookup;
keeping it ensures older agent transcripts and external scripts continue
to work. New callers should prefer `check_workspace.py`, which returns
the same `GITHUB_REPOS` plus full workspace status in one call.

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

import sys
from pathlib import Path

from check_workspace import check_workspace


def check_github_repos(root: Path) -> dict[str, str]:
    """Read fullstack.json and return github_repos status.

    Returns the legacy three-key shape for backward compatibility, derived
    from the unified workspace check.
    """
    workspace = check_workspace(root)
    return {
        "GITHUB_REPOS": workspace["GITHUB_REPOS"],
        "CONFIG_PATH": workspace["CONFIG_PATH"],
        "CONFIG_FOUND": workspace["CONFIG_FOUND"],
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
