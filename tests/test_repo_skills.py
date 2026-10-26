"""Tests for the repo-private skill index (repo_skills.py).

Covers frontmatter parsing (plain and block scalars), skill discovery
under both roots with symlink dedupe, the machine-readable index output,
and the CLI contract the fullstack skills rely on.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from mythril_agent_skills.shared.workspace.repo_skills import (
    discover_repo_skills,
    format_repo_index,
    parse_frontmatter,
)

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "mythril_agent_skills"
    / "skills"
    / "fullstack-init"
    / "scripts"
    / "repo_skills.py"
)


def _skill(repo: Path, name: str, frontmatter: str) -> Path:
    path = repo / ".agents" / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(frontmatter, encoding="utf-8")
    return path


class TestParseFrontmatter:
    def test_folded_block_scalar(self):
        name, description = parse_frontmatter(
            "---\n"
            "name: deploy-helper\n"
            "description: >\n"
            "  Deploy the service.\n"
            "  Use for releases.\n"
            "---\n"
        )
        assert name == "deploy-helper"
        assert description == "Deploy the service. Use for releases."

    def test_plain_scalar_and_quotes(self):
        name, description = parse_frontmatter(
            '---\nname: "release-helper"\ndescription: Cut a release\n---\n'
        )
        assert name == "release-helper"
        assert description == "Cut a release"

    def test_missing_frontmatter(self):
        assert parse_frontmatter("# just a heading\n") == ("", "")

    def test_description_pipes_are_normalized(self):
        _, description = parse_frontmatter(
            "---\ndescription: a | b\n---\n"
        )
        assert description == "a / b"


class TestDiscoverRepoSkills:
    def test_lists_every_skill_sorted(self, tmp_path: Path):
        _skill(tmp_path, "beta", "---\nname: beta\n---\n")
        _skill(tmp_path, "alpha", "---\nname: alpha\ndescription: A\n---\n")
        found = discover_repo_skills(tmp_path)
        assert [name for name, _, _ in found] == ["alpha", "beta"]
        assert found[0][2] == "A"

    def test_claude_symlink_is_deduped(self, tmp_path: Path):
        _skill(tmp_path, "alpha", "---\nname: alpha\n---\n")
        (tmp_path / ".claude").symlink_to(
            tmp_path / ".agents", target_is_directory=True
        )
        found = discover_repo_skills(tmp_path)
        assert [name for name, _, _ in found] == ["alpha"]

    def test_repo_without_skills(self, tmp_path: Path):
        assert discover_repo_skills(tmp_path) == []


class TestFormatRepoIndex:
    def test_emits_every_skill_with_absolute_path(self, tmp_path: Path):
        _skill(tmp_path, "alpha", "---\nname: alpha\ndescription: A\n---\n")
        lines, ok = format_repo_index(tmp_path)
        assert ok is True
        assert "SKILLS=1" in lines
        skill_line = next(line for line in lines if line.startswith("SKILL="))
        assert skill_line.startswith("SKILL=alpha | ")
        assert skill_line.endswith(" | A")

    def test_empty_index_is_identified_not_an_error(self, tmp_path: Path):
        lines, ok = format_repo_index(tmp_path)
        assert ok is True
        assert f"NO_REPO_SKILLS={tmp_path.name}" in lines

    def test_missing_repo(self, tmp_path: Path):
        lines, ok = format_repo_index(tmp_path / "ghost")
        assert ok is False
        assert lines[0].startswith("ERROR_NO_SUCH_REPO=")


class TestCli:
    def test_indexes_multiple_repos(self, tmp_path: Path):
        first = tmp_path / "api"
        second = tmp_path / "web"
        _skill(first, "deploy-helper", "---\nname: deploy-helper\n---\n")
        second.mkdir()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(first), str(second)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout.count("REPO=") == 2
        assert "SKILL=deploy-helper" in result.stdout
        assert "NO_REPO_SKILLS=web" in result.stdout

    def test_missing_repo_exits_nonzero(self, tmp_path: Path):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(tmp_path / "ghost")],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert "ERROR_NO_SUCH_REPO=" in result.stdout
