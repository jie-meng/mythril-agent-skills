#!/usr/bin/env python3
"""Check whether a `graphify-out/` directory exists at a given path.

This uses `pathlib.Path.is_dir()`, which is immune to `.gitignore` filtering.
Some AI coding tools' Glob/file-search tools silently skip `.gitignore`-ignored
paths, so a direct filesystem check is the only reliable way to detect
`graphify-out/`.

Usage: python3 graphify_check.py <repo-path>
Exit codes:
  0 — graphify-out/ directory exists at the given path
  1 — graphify-out/ does NOT exist at the given path
  2 — usage error
"""

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: graphify_check.py <repo-path>", file=sys.stderr)
        sys.exit(2)

    repo = Path(sys.argv[1])
    graphify_dir = repo / "graphify-out"

    if graphify_dir.is_dir():
        print("EXISTS")
        sys.exit(0)
    else:
        print("NOT_FOUND")
        sys.exit(1)


if __name__ == "__main__":
    main()
