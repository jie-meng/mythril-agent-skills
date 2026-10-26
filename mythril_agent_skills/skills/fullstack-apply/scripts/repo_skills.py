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

A repo is named either by path or by directory name. Names resolve
nearest scope first and the first scope with a hit wins, so
"push-data in robo-business-skills" works from any workspace root
without the user supplying a path:

1. the argument as a path, if it is one that exists
2. `<workspace>/<name>` — the workspace root the argument belongs to
   (`fullstack.json`'s directory, else the current directory)
3. `<workspace-parent>/*/<name>` — a repo that lives in a sibling
   workspace. More than one hit is reported as ambiguous, never guessed.

Usage:
    python3 repo_skills.py <repo> [<repo> ...]

Output (one field per line, machine-readable):
    REPO=<name>  REPO_PATH=<abs path>  SKILLS=<n>
    SKILL=<skill-dir-name> | <abs SKILL.md path> | <description>
    NO_REPO_SKILLS=<name>
    NOTE=<how the name was resolved>            (name resolved off cwd)
    AMBIGUOUS_REPO=<name> + CANDIDATE=<abs path>
    ERROR_NO_SUCH_REPO=<argument>  SEARCHED=<scope tried> ...

Exit codes: 0 = every repo was read, 1 = at least one argument resolved to
no single directory, 2 = usage error. A repo with zero skills is not an
error: the `NO_REPO_SKILLS` line distinguishes "nothing to load" from
"script failed".
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# `.claude` is often a symlink to `.agents`; the realpath dedupe below
# keeps those from listing every skill twice.
SKILL_ROOTS = (".agents/skills", ".claude/skills")
# Descriptions carry the trigger phrases the loader matches against, and
# they sit at the end of the block as often as at the start — truncating
# at 200 cut them off on most real skills. 500 bounds a pathological
# frontmatter without dropping the matching signal.
MAX_DESCRIPTION_CHARS = 500
WORKSPACE_CONFIG = "fullstack.json"
# An ambiguous name reports this many candidates; more than this means the
# caller needs a path, not a longer list.
MAX_CANDIDATES = 8


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


@dataclass(frozen=True)
class Resolution:
    """What a repo argument turned into. Exactly one outcome is set."""

    path: Path | None = None
    candidates: list[Path] = field(default_factory=list)
    searched: list[str] = field(default_factory=list)
    note: str = ""


def find_workspace_root(start: Path) -> Path | None:
    """Return the nearest directory holding `fullstack.json`, or None."""
    for candidate in (start, *start.parents):
        if (candidate / WORKSPACE_CONFIG).is_file():
            return candidate
    return None


def _visible_children(parent: Path, name: str) -> list[Path]:
    """Return `parent/*/<name>` hits, skipping dot-directories and non-dirs."""
    if name.startswith("."):
        return []
    try:
        matches = sorted(parent.glob(f"*/{name}"))
    except OSError:
        return []
    return [
        match
        for match in matches
        if not match.parent.name.startswith(".") and match.is_dir()
    ]


def resolve_repo(argument: str, cwd: Path | None = None) -> Resolution:
    """Resolve a repo path or bare directory name into one directory.

    Scopes are tried nearest first and the first scope holding a hit wins:
    the argument as a path, then `<base>/<name>`, then
    `<base-parent>/*/<name>` so a repo belonging to a sibling workspace
    resolves by name. `base` is the workspace root the session sits in
    (`fullstack.json`'s directory), falling back to the current directory.
    Two hits in the same scope are reported as candidates, never guessed:
    the same repo name in two workspaces is a question for the user.
    """
    start = (cwd or Path.cwd()).expanduser().resolve()
    given = Path(argument).expanduser()
    if given.is_dir():
        return Resolution(path=given.resolve())

    name = given.name
    if not name:
        return Resolution(path=None, searched=[str(given)])

    base = find_workspace_root(start) or start
    searched = [str(base / name)]
    direct = base / name
    if direct.is_dir():
        note = (
            f"NOTE: resolved from the workspace root {base}"
            if base != start
            else ""
        )
        return Resolution(path=direct.resolve(), searched=searched, note=note)

    parent = base.parent
    if parent != base and len(base.parents) > 1:
        searched.append(str(parent / "*" / name))
        hits = _visible_children(parent, name)
        if len(hits) == 1:
            return Resolution(
                path=hits[0].resolve(),
                searched=searched,
                note=f"NOTE: resolved outside this directory — the repo lives "
                f"in the neighboring workspace {hits[0].parent}",
            )
        if len(hits) > 1:
            return Resolution(
                candidates=[hit.resolve() for hit in hits[:MAX_CANDIDATES]],
                searched=searched,
            )

    return Resolution(searched=searched)


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


def format_repo_index(
    argument: str | Path, cwd: Path | None = None
) -> tuple[list[str], bool]:
    """Return `(output_lines, resolved)` for one repo path or name."""
    resolution = resolve_repo(str(argument), cwd)
    if resolution.path is None:
        if resolution.candidates:
            lines = [f"AMBIGUOUS_REPO={Path(str(argument)).name}"]
            lines += [f"CANDIDATE={hit}" for hit in resolution.candidates]
        else:
            lines = [f"ERROR_NO_SUCH_REPO={argument}"]
        lines += [f"SEARCHED={scope}" for scope in resolution.searched]
        lines.append(
            "NOTE: pass the repository path, or its directory name inside "
            "this workspace or a sibling workspace"
        )
        return lines, False

    repo = resolution.path
    skills = discover_repo_skills(repo)
    lines = [f"REPO={repo.name}", f"REPO_PATH={repo}"]
    if resolution.note:
        lines.append(resolution.note)
    lines.append(f"SKILLS={len(skills)}")
    for name, skill_md, description in skills:
        lines.append(f"SKILL={name} | {skill_md} | {description or '—'}")
    if not skills:
        lines.append(f"NO_REPO_SKILLS={repo.name}")
    return lines, True


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="List the skills a repository ships under "
        ".agents/skills/ (falling back to .claude/skills/). A repository "
        "is named by path or by directory name.",
    )
    parser.add_argument(
        "repos",
        nargs="+",
        metavar="repo",
        help="Repository path or directory name (one or more)",
    )
    args = parser.parse_args(argv)

    all_ok = True
    for item in args.repos:
        lines, ok = format_repo_index(item)
        all_ok = all_ok and ok
        print("\n".join(lines))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
