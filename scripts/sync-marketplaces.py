#!/usr/bin/env python3
"""Regenerate the WorkBuddy/CodeBuddy plugin catalogs from the canonical one.

The repository is published as a Claude Code plugin marketplace via
``.claude-plugin/marketplace.json`` (the canonical catalog, hand-edited when
a skill is added). WorkBuddy AI and CodeBuddy Code read the very same
catalog format from a ``.workbuddy-plugin/`` (or ``.codebuddy-plugin/``)
directory instead of ``.claude-plugin/``.

To avoid a second hand-maintained catalog drifting out of sync, the
WorkBuddy catalog is **generated** from the canonical Claude catalog:

  - every field is copied verbatim
  - the Claude-specific ``$schema`` key is dropped

Usage:
    python3 scripts/sync-marketplaces.py            # regenerate
    python3 scripts/sync-marketplaces.py --check     # verify (exit 1 on drift)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = PROJECT_ROOT / ".claude-plugin" / "marketplace.json"

#: Derived catalogs, in the manifest directory each tool scans.
DERIVED: list[tuple[str, Path]] = [
    (
        "WorkBuddy AI / CodeBuddy Code",
        PROJECT_ROOT / ".workbuddy-plugin" / "marketplace.json",
    ),
]

#: Keys that belong to the canonical (Claude) catalog only.
CLAUDE_ONLY_KEYS = ("$schema",)

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def render() -> str:
    """Render the derived marketplace catalog as JSON text.

    Raises:
        FileNotFoundError: If the canonical catalog is missing.
        json.JSONDecodeError: If the canonical catalog is not valid JSON.
    """
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))
    for key in CLAUDE_ONLY_KEYS:
        data.pop(key, None)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def targets() -> list[tuple[str, Path]]:
    """Return the derived catalog locations."""
    return list(DERIVED)


def main() -> None:
    check_only = "--check" in sys.argv[1:]

    if not CANONICAL.is_file():
        print(f"{RED}Error: canonical catalog not found: {CANONICAL}{NC}")
        sys.exit(1)

    try:
        expected = render()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"{RED}Error: cannot read {CANONICAL}: {exc}{NC}")
        sys.exit(1)

    drifted: list[str] = []

    for label, target in targets():
        current = target.read_text(encoding="utf-8") if target.is_file() else None

        if current == expected:
            if not check_only:
                print(f"  {GREEN}up to date{NC}  {target.relative_to(PROJECT_ROOT)}")
            continue

        if check_only:
            state = "missing" if current is None else "drifted"
            drifted.append(f"  - {state}: {target.relative_to(PROJECT_ROOT)}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(expected, encoding="utf-8")
        action = "created" if current is None else "updated"
        print(
            f"  {GREEN}{action}{NC}     {target.relative_to(PROJECT_ROOT)}"
            f"  ({label})"
        )

    if check_only and drifted:
        print(
            f"{RED}Derived marketplace catalogs are out of sync with "
            f"{CANONICAL.relative_to(PROJECT_ROOT)}.{NC}\n"
            "Run `python3 scripts/sync-marketplaces.py` to fix:\n" + "\n".join(drifted)
        )
        sys.exit(1)

    if check_only:
        print(f"{GREEN}All derived marketplace catalogs are in sync.{NC}")


if __name__ == "__main__":
    main()
