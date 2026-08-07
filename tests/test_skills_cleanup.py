"""Tests for mythril_agent_skills.cli.skills_cleanup."""

from pathlib import Path

import pytest
from mythril_agent_skills.cli.skills_cleanup import (
    SkillEntry,
    ToolGroup,
    _build_rows,
    get_builtin_skill_names,
)


def _make_group(tmp_path: Path, label: str, config_dir: str) -> ToolGroup:
    """Create a ToolGroup whose skills_dir contains a mix of builtin/other."""
    skills_dir = tmp_path / config_dir / "skills"
    skills_dir.mkdir(parents=True)
    group = ToolGroup(label, config_dir, skills_dir)
    return group


class TestGetBuiltinSkillNames:
    @pytest.fixture(autouse=True)
    def _import(self):
        from mythril_agent_skills.cli import skills_cleanup as sc
        self.builtin_dir = sc.BUILTIN_SKILLS_DIR
        self.func = get_builtin_skill_names

    def test_returns_package_skill_names(self):
        names = self.func()
        # The package bundles real skills; assert a known subset.
        assert "jira" in names
        assert "figma" in names
        assert "fullstack-init" in names
        assert all(not n.startswith(".") for n in names)

    def test_missing_dir_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "mythril_agent_skills.cli.skills_cleanup.BUILTIN_SKILLS_DIR",
            tmp_path / "nonexistent",
        )
        assert self.func() == set()


class TestScanBuiltinMarking:
    """SkillEntry.is_builtin is set from the builtin-name set at scan time."""

    def test_marks_builtin_and_other(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "jira").mkdir()
        (skills_dir / "my-custom").mkdir()

        group = ToolGroup("Test", ".test", skills_dir)
        group.scan(builtin_names={"jira", "figma"})

        by_name = {s.name: s for s in group.skills}
        assert by_name["jira"].is_builtin is True
        assert by_name["my-custom"].is_builtin is False

    def test_skips_hidden_dirs(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "jira").mkdir()
        (skills_dir / ".hidden").mkdir()

        group = ToolGroup("Test", ".test", skills_dir)
        group.scan(builtin_names={"jira"})

        assert [s.name for s in group.skills] == ["jira"]


class TestBuildRows:
    """Row kinds and ordering for the cleanup tree view."""

    def _make_groups(self, tmp_path: Path) -> list[ToolGroup]:
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)
        for name in ("jira", "my-custom", "figma"):
            (skills_dir / name).mkdir()

        group = ToolGroup("Claude", ".claude", skills_dir)
        group.scan(builtin_names={"jira", "figma"})
        return [group]

    def test_sections_split_builtin_first(self, tmp_path: Path):
        rows = _build_rows(self._make_groups(tmp_path))
        kinds = [r[0] for r in rows]
        texts = [r[1] for r in rows]

        assert kinds == ["tool", "section", "skill", "skill", "section", "skill"]
        assert texts[0] == "Claude"
        assert texts[1] == "  Builtin Skills (2)"
        assert texts[4] == "  Other Skills (1)"

        # Builtin section lists jira + figma; other section lists my-custom.
        section_skills = [r[3].name for r in rows if r[0] == "skill"]
        assert section_skills == ["figma", "jira", "my-custom"]

    def test_only_builtin_no_other_section(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "jira").mkdir()
        group = ToolGroup("Claude", ".claude", skills_dir)
        group.scan(builtin_names={"jira"})

        rows = _build_rows([group])
        kinds = [r[0] for r in rows]
        texts = [r[1] for r in rows]
        assert kinds == ["tool", "section", "skill"]
        assert texts[1] == "  Builtin Skills (1)"
        assert "Other" not in texts

    def test_only_other_no_builtin_section(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "my-custom").mkdir()
        group = ToolGroup("Claude", ".claude", skills_dir)
        group.scan(builtin_names={"jira"})

        rows = _build_rows([group])
        kinds = [r[0] for r in rows]
        texts = [r[1] for r in rows]
        assert kinds == ["tool", "section", "skill"]
        assert texts[1] == "  Other Skills (1)"
        assert "Builtin" not in texts

    def test_multiple_groups_each_get_sections(self, tmp_path: Path):
        g1_dir = tmp_path / "skills_a"
        g1_dir.mkdir(parents=True)
        (g1_dir / "jira").mkdir()
        g1 = ToolGroup("Claude", ".claude", g1_dir)
        g1.scan(builtin_names={"jira"})

        g2_dir = tmp_path / "skills_b"
        g2_dir.mkdir(parents=True)
        (g2_dir / "my-custom").mkdir()
        g2 = ToolGroup("Cursor", ".cursor", g2_dir)
        g2.scan(builtin_names={"jira"})

        rows = _build_rows([g1, g2])
        kinds = [r[0] for r in rows]
        texts = [r[1] for r in rows]
        assert kinds == ["tool", "section", "skill", "tool", "section", "skill"]
        assert texts[0] == "Claude"
        assert texts[3] == "Cursor"
        assert texts[4] == "  Other Skills (1)"


class TestSkillEntry:
    def test_defaults(self, tmp_path: Path):
        entry = SkillEntry("x", tmp_path / "x")
        assert entry.is_builtin is False
        assert entry.selected is False
