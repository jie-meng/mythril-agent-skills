#!/usr/bin/env python3
"""List the private skills a repository ships, so callers can load lazily.

A workspace agent's skill registry is rooted at the session root
(`~/.agents/skills/`, `<workspace>/.agents/skills/`); skill directories
nested inside a repository are never scanned. Those skills are still
plain `SKILL.md` instruction files, so the way to use them is to read the
matching file on demand — but only after knowing which ones exist.

This script prints that index and nothing else: one block per repo, one
line per skill, with the absolute `SKILL.md` path so the caller can read
it without guessing where the skill lives. It parses frontmatter without
PyYAML because skill scripts must run on a bare Python install.

Usage:
    python3 repo_skills.py <repo> [<repo> ...]

Output (one field per line, machine-readable):
    REPO=<name>  REPO_PATH=<abs path>  SKILLS=<n>
    SKILL=<skill-dir-name> | <abs SKILL.md path> | <description>
    NO_REPO_SKILLS=<name>
    ERROR_NO_SUCH_REPO=<path>

Exit codes: 0 = every repo was read, 1 = at least one repo path is not a
directory, 2 = usage error. A repo with zero skills is not an error: the
`NO_REPO_SKILLS` line distinguishes "nothing to load" from "script
failed".
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# `.claude` is often a symlink to `.agents`; the realpath dedupe below
# keeps those from listing every skill twice.
SKILL_ROOTS = (".agents/skills", ".claude/skills")
# Descriptions carry the trigger phrases the loader matches against, and
# they sit at the end of the block as often as at the start — truncating
# at 200 cut them off on most real skills. 500 bounds a pathological
# frontmatter without dropping the matching signal.
MAX_DESCRIPTION_CHARS = 500


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def _normalize_description(value: str) -> str:
    """Collapse a YAML description to one line the index can carry."""
    text = re.sub(r"\s+", " ", value).strip()
    text = text.replace("|", "/")
    if len(text) > MAX_DESCRIPTION_CHARS:
        text = text[: MAX_DESCRIPTION_CHARS - 1].rstrip() + "…"
    return text


def parse_frontmatter(text: str) -> tuple[str, str]:
    """Return `(name, description)` from a SKILL.md frontmatter block.

    Supports the two shapes skill authors actually use: a plain scalar on
    the key line, and a `>` / `|` block scalar whose body is indented
    underneath. A missing or malformed block yields empty strings; the
    caller falls back to the directory name.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", ""
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            end = index
            break
    if end is None:
        return "", ""

    name = ""
    description: list[str] = []
    collecting = False
    last_key = ""
    for raw in lines[1:end]:
        if collecting:
            if raw.strip() == "" or raw.startswith((" ", "\t")):
                description.append(raw.strip())
                continue
            collecting = False
        if raw[:1] in (" ", "\t"):
            # A wrapped plain scalar continues on an indented line.
            if raw.strip() and last_key == "description":
                description.append(raw.strip())
            continue
        key, separator, value = raw.partition(":")
        if not separator:
            continue
        key = key.strip().lower()
        value = value.strip()
        last_key = key
        if key == "name":
            name = _unquote(value)
        elif key == "description":
            if value in ("|", ">", "|-", ">-", "|+", ">+"):
                collecting = True
                description = []
            else:
                description = [value]
    return name, _normalize_description(" ".join(description))


def discover_repo_skills(repo: Path) -> list[tuple[str, Path, str]]:
    """Return `(skill_name, skill_md_path, description)` for one repo."""
    seen: set[Path] = set()
    found: list[tuple[str, Path, str]] = []
    for relative in SKILL_ROOTS:
        base = repo / relative
        if not base.is_dir():
            continue
        for skill_md in sorted(base.glob("*/SKILL.md")):
            if not skill_md.is_file():
                continue
            real = skill_md.resolve()
            if real in seen:
                continue
            seen.add(real)
            try:
                text = skill_md.read_text(encoding="utf-8")
            except OSError:
                continue
            _, description = parse_frontmatter(text)
            found.append((skill_md.parent.name, skill_md.resolve(), description))
    return sorted(found, key=lambda item: item[0].lower())


def format_repo_index(repo: Path) -> tuple[list[str], bool]:
    """Return `(output_lines, repo_exists)` for one repo path."""
    repo = repo.expanduser()
    if not repo.is_dir():
        return [f"ERROR_NO_SUCH_REPO={repo}"], False
    resolved = repo.resolve()
    skills = discover_repo_skills(resolved)
    lines = [
        f"REPO={resolved.name}",
        f"REPO_PATH={resolved}",
        f"SKILLS={len(skills)}",
    ]
    for name, skill_md, description in skills:
        lines.append(f"SKILL={name} | {skill_md} | {description or '—'}")
    if not skills:
        lines.append(f"NO_REPO_SKILLS={resolved.name}")
    return lines, True


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="List the skills a repository ships under "
        ".agents/skills/ (falling back to .claude/skills/).",
    )
    parser.add_argument(
        "repos",
        nargs="+",
        metavar="repo",
        help="Repository path (one or more)",
    )
    args = parser.parse_args(argv)

    all_ok = True
    for item in args.repos:
        lines, ok = format_repo_index(Path(item))
        all_ok = all_ok and ok
        print("\n".join(lines))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
