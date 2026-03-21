#!/usr/bin/env python3
"""Validate SKILL.md description length limits across all skills."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_LIMIT = 1024
DESCRIPTION_KEY = "description"
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def _load_frontmatter(text: str, path: Path) -> str:
    """Extract YAML frontmatter content from a SKILL.md file."""
    if not text.startswith("---"):
        raise ValueError(f"Missing frontmatter in {path}")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Incomplete frontmatter in {path}")
    return parts[1].lstrip("\n")


def _fold_block(style: str, lines: list[str]) -> str:
    """Fold YAML block scalars for description value."""
    if style == "|":
        return "\n".join(lines).rstrip("\n")
    if style == ">":
        output: list[str] = []
        paragraph: list[str] = []
        for line in lines:
            if line.strip() == "":
                if paragraph:
                    output.append(" ".join(paragraph).strip())
                    paragraph = []
                output.append("")
            else:
                paragraph.append(line.strip())
        if paragraph:
            output.append(" ".join(paragraph).strip())
        return "\n".join(output).rstrip("\n")
    return "\n".join(lines).rstrip("\n")


def _parse_description(frontmatter: str) -> str | None:
    """Parse the description field from YAML frontmatter."""
    lines = frontmatter.splitlines()
    i = 0
    key_re = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
    while i < len(lines):
        line = lines[i]
        match = key_re.match(line)
        if match:
            key = match.group(1)
            value = match.group(2)
            if key == DESCRIPTION_KEY:
                if value in ("|", ">", ""):
                    style = value
                    i += 1
                    block_lines: list[str] = []
                    while i < len(lines):
                        next_line = lines[i]
                        if key_re.match(next_line) and not next_line.startswith(" "):
                            break
                        if next_line.startswith(" "):
                            block_lines.append(next_line[1:])
                        elif next_line.startswith("\t"):
                            block_lines.append(next_line.lstrip("\t"))
                        else:
                            block_lines.append(next_line)
                        i += 1
                    return _fold_block(style, block_lines)
                return value.strip()
        i += 1
    return None


def _collect_skill_dirs(skills_dir: Path) -> list[Path]:
    """Collect skill directories that contain SKILL.md files."""
    if not skills_dir.exists():
        raise FileNotFoundError(f"Skills directory not found: {skills_dir}")
    skill_dirs = [p for p in skills_dir.iterdir() if p.is_dir()]
    return sorted(skill_dirs, key=lambda p: p.name)


def _validate_skill(skill_dir: Path, limit: int) -> tuple[str, int | None, str | None]:
    """Return (skill_name, length, error) for a single skill."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return skill_dir.name, None, "SKILL.md not found"

    text = skill_md.read_text()
    try:
        frontmatter = _load_frontmatter(text, skill_md)
    except ValueError as exc:
        return skill_dir.name, None, str(exc)

    description = _parse_description(frontmatter)
    if description is None:
        return skill_dir.name, None, "description field not found"

    return skill_dir.name, len(description), None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate SKILL.md description length limits.",
    )
    parser.add_argument(
        "--skills-dir",
        default="mythril_agent_skills/skills",
        help="Path to skills directory (default: mythril_agent_skills/skills)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum allowed description length (default: {DEFAULT_LIMIT})",
    )
    args = parser.parse_args()

    skills_dir = Path(args.skills_dir)
    limit = args.limit

    over_limit = False
    missing = False

    skill_dirs = _collect_skill_dirs(skills_dir)
    print(f"Validating {len(skill_dirs)} skills (limit: {limit} chars)\n")

    for skill_dir in skill_dirs:
        name, length, error = _validate_skill(skill_dir, limit)
        if error:
            missing = True
            print(f"{YELLOW}!! {name}: {error}{NC}")
            continue
        if length is not None and length > limit:
            over_limit = True
            print(f"{RED}!! {name}: {length} chars (exceeds {limit}){NC}")
        else:
            print(f"{GREEN}   {name}: {length} chars{NC}")

    if over_limit or missing:
        print(f"\n{RED}FAIL: description validation failed.{NC}")
        sys.exit(1)

    print(f"\n{GREEN}OK: all descriptions are within the limit.{NC}")


if __name__ == "__main__":
    main()
