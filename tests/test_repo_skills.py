"""Tests for the repo-private skill index (repo_skills.py).

Covers frontmatter parsing (plain and block scalars), skill discovery
under both roots with symlink dedupe, repo-name resolution across the
current and sibling workspaces (including the ambiguous case), the
machine-readable index output, and the CLI contract the fullstack skills
rely on.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from mythril_agent_skills.shared.workspace.repo_skills import (
    discover_repo_skills,
    find_workspace_root,
    format_repo_index,
    parse_frontmatter,
    resolve_repo,
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
        lines, ok = format_repo_index(tmp_path, cwd=tmp_path)
        assert ok is True
        assert "SKILLS=1" in lines
        skill_line = next(line for line in lines if line.startswith("SKILL="))
        assert skill_line.startswith("SKILL=alpha | ")
        assert skill_line.endswith(" | A")

    def test_empty_index_is_identified_not_an_error(self, tmp_path: Path):
        lines, ok = format_repo_index(tmp_path, cwd=tmp_path)
        assert ok is True
        assert f"NO_REPO_SKILLS={tmp_path.name}" in lines

    def test_missing_repo(self, tmp_path: Path):
        lines, ok = format_repo_index(tmp_path / "ghost", cwd=tmp_path)
        assert ok is False
        assert lines[0].startswith("ERROR_NO_SUCH_REPO=")


class TestResolveRepo:
    """A repo may be named by path or by directory name, nearest scope first."""

    def _workspace(self, tmp_path: Path, name: str) -> Path:
        root = tmp_path / name
        root.mkdir(parents=True, exist_ok=True)
        (root / "fullstack.json").write_text(
            '{"docs_dir": "docs"}', encoding="utf-8"
        )
        return root

    def test_existing_path_wins(self, tmp_path: Path):
        repo = tmp_path / "somewhere"
        repo.mkdir()
        assert resolve_repo(str(repo), cwd=tmp_path).path == repo.resolve()

    def test_name_resolves_inside_the_current_workspace(
        self, tmp_path: Path
    ):
        ws = self._workspace(tmp_path, "ai")
        repo = ws / "stock-analysis"
        repo.mkdir()
        found = resolve_repo("stock-analysis", cwd=ws)
        assert found.path == repo.resolve()
        assert found.note == ""

    def test_name_resolves_from_a_repo_directory_inside_the_workspace(
        self, tmp_path: Path
    ):
        ws = self._workspace(tmp_path, "ai")
        repo = ws / "stock-analysis"
        inside = repo / "src"
        inside.mkdir(parents=True)
        found = resolve_repo("stock-analysis", cwd=inside)
        assert found.path == repo.resolve()
        assert "workspace root" in found.note

    def test_name_reaches_a_sibling_workspace(self, tmp_path: Path):
        ws = self._workspace(tmp_path, "ai")
        (ws / "art-studio").mkdir()
        neighbor = self._workspace(tmp_path, "hkmw")
        target = neighbor / "robo-server"
        target.mkdir()
        found = resolve_repo("robo-server", cwd=ws)
        assert found.path == target.resolve()
        assert "sibling" in found.note or "neighboring" in found.note

    def test_local_hit_beats_a_sibling_of_the_same_name(self, tmp_path: Path):
        ws = self._workspace(tmp_path, "ai")
        local = ws / "robo-server"
        local.mkdir()
        other = self._workspace(tmp_path, "hkmw") / "robo-server"
        other.mkdir()
        assert resolve_repo("robo-server", cwd=ws).path == local.resolve()

    def test_two_sibling_hits_are_ambiguous(self, tmp_path: Path):
        ws = self._workspace(tmp_path, "ai")
        (ws / "art-studio").mkdir()
        for name in ("hkmw", "other"):
            hit = self._workspace(tmp_path, name) / "shared-repo"
            hit.mkdir()
        found = resolve_repo("shared-repo", cwd=ws)
        assert found.path is None
        assert len(found.candidates) == 2

    def test_miss_reports_the_scopes_it_tried(self, tmp_path: Path):
        ws = self._workspace(tmp_path, "ai")
        found = resolve_repo("nope", cwd=ws)
        assert found.path is None
        assert str(ws / "nope") in found.searched

    def test_dot_named_siblings_are_skipped(self, tmp_path: Path):
        ws = self._workspace(tmp_path, "ai")
        (ws / "art-studio").mkdir()
        hidden = tmp_path / ".cache" / "robo-server"
        hidden.mkdir(parents=True)
        assert resolve_repo("robo-server", cwd=ws).path is None

    def test_find_workspace_root_walks_up(self, tmp_path: Path):
        ws = self._workspace(tmp_path, "ai")
        deep = ws / "repo" / "src" / "pkg"
        deep.mkdir(parents=True)
        assert find_workspace_root(deep) == ws.resolve()

    def test_format_reports_ambiguity_as_lines(self, tmp_path: Path):
        ws = self._workspace(tmp_path, "ai")
        (ws / "art-studio").mkdir()
        for name in ("hkmw", "other"):
            self._workspace(tmp_path, name)
            (tmp_path / name / "shared-repo").mkdir()
        lines, ok = format_repo_index("shared-repo", cwd=ws)
        assert ok is False
        assert lines[0] == "AMBIGUOUS_REPO=shared-repo"
        assert any(line.startswith("CANDIDATE=") for line in lines)
        assert any(line.startswith("SEARCHED=") for line in lines)


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
            cwd=tmp_path,
        )
        assert result.returncode == 1
        assert "ERROR_NO_SUCH_REPO=" in result.stdout

    def test_cli_accepts_a_bare_repo_name(self, tmp_path: Path):
        ws = tmp_path / "ai"
        ws.mkdir()
        (ws / "fullstack.json").write_text(
            '{"docs_dir": "docs"}', encoding="utf-8"
        )
        _skill(ws / "stock-analysis", "technical-indicator", "---\n---\n")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "stock-analysis"],
            capture_output=True,
            text=True,
            check=False,
            cwd=ws,
        )
        assert result.returncode == 0
        assert "REPO=stock-analysis" in result.stdout
        assert "SKILL=technical-indicator" in result.stdout
