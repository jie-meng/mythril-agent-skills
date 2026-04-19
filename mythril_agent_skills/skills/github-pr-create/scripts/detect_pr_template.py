#!/usr/bin/env python3
"""Detect PR templates in a git repository.

Searches standard locations for pull request templates and outputs
machine-readable results. Runs from the repository root.

Usage:
    python3 detect_pr_template.py [--repo-root <path>]

Output (machine-readable key=value lines):
    TEMPLATE_FOUND=true|false
    TEMPLATE_PATH=<relative-path>       (only when found)
    TEMPLATE_CONTENT=<base64>           (only when found, single template)
    MULTIPLE_TEMPLATES=true|false
    TEMPLATE_NAMES=<comma-separated>    (only when multiple)
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

SINGLE_TEMPLATE_PATHS = [
    ".github/pull_request_template.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "pull_request_template.md",
    "PULL_REQUEST_TEMPLATE.md",
    "docs/pull_request_template.md",
    "docs/PULL_REQUEST_TEMPLATE.md",
]

TEMPLATE_DIRS = [
    ".github/PULL_REQUEST_TEMPLATE",
    ".github/pull_request_template",
]


def find_repo_root(start: Path) -> Path:
    """Walk up from *start* to find the nearest .git directory."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return start.resolve()


def detect_single_template(repo_root: Path) -> Path | None:
    """Return the first matching single-file template, or None."""
    for rel in SINGLE_TEMPLATE_PATHS:
        candidate = repo_root / rel
        if candidate.is_file():
            return candidate
    return None


def detect_multiple_templates(repo_root: Path) -> list[Path]:
    """Return all template files inside a template directory."""
    for rel in TEMPLATE_DIRS:
        template_dir = repo_root / rel
        if template_dir.is_dir():
            templates = sorted(
                p
                for p in template_dir.iterdir()
                if p.is_file() and p.suffix.lower() == ".md"
            )
            if templates:
                return templates
    return []


def run(repo_root: Path | None = None) -> dict[str, str]:
    """Detect PR templates and return result dict."""
    if repo_root is None:
        repo_root = find_repo_root(Path.cwd())

    result: dict[str, str] = {}

    multi = detect_multiple_templates(repo_root)
    if multi:
        result["TEMPLATE_FOUND"] = "true"
        result["MULTIPLE_TEMPLATES"] = "true"
        names = ",".join(p.stem for p in multi)
        result["TEMPLATE_NAMES"] = names
        first = multi[0]
        result["TEMPLATE_PATH"] = str(first.relative_to(repo_root))
        content = first.read_text(encoding="utf-8")
        result["TEMPLATE_CONTENT"] = base64.b64encode(
            content.encode("utf-8")
        ).decode("ascii")
        return result

    single = detect_single_template(repo_root)
    if single:
        result["TEMPLATE_FOUND"] = "true"
        result["MULTIPLE_TEMPLATES"] = "false"
        result["TEMPLATE_PATH"] = str(single.relative_to(repo_root))
        content = single.read_text(encoding="utf-8")
        result["TEMPLATE_CONTENT"] = base64.b64encode(
            content.encode("utf-8")
        ).decode("ascii")
        return result

    result["TEMPLATE_FOUND"] = "false"
    result["MULTIPLE_TEMPLATES"] = "false"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect PR templates")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: auto-detect from cwd)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root
    if repo_root is not None:
        repo_root = repo_root.resolve()

    result = run(repo_root)
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
