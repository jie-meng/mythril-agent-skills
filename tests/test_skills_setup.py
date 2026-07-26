"""Tests for mythril_agent_skills.cli.skills_setup."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mythril_agent_skills.cli.skills_setup import (
    SkillEntry,
    annotate_skill_entries_status,
    run_skills_check,
)


@pytest.fixture
def mock_skill_dir(tmp_path: Path) -> Path:
    """Create a mock source skill directory."""
    skill_dir = tmp_path / "src_skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("name: test-skill\n")
    return skill_dir


class TestAnnotateSkillEntriesStatus:
    def test_not_installed(self, mock_skill_dir: Path, tmp_path: Path) -> None:
        target_dir = tmp_path / "target_skills"
        target_dir.mkdir()

        entry = SkillEntry(
            path=mock_skill_dir,
            name="test-skill",
            is_local=False,
            has_conflict=False,
        )

        annotate_skill_entries_status([entry], [target_dir])

        assert entry.is_installed is False
        assert entry.needs_update is False

    def test_installed_and_up_to_date(self, mock_skill_dir: Path, tmp_path: Path) -> None:
        target_dir = tmp_path / "target_skills"
        installed_skill = target_dir / "test-skill"
        installed_skill.mkdir(parents=True)
        (installed_skill / "SKILL.md").write_text("name: test-skill\n")

        entry = SkillEntry(
            path=mock_skill_dir,
            name="test-skill",
            is_local=False,
            has_conflict=False,
        )

        annotate_skill_entries_status([entry], [target_dir])

        assert entry.is_installed is True
        assert entry.needs_update is False

    def test_needs_update(self, mock_skill_dir: Path, tmp_path: Path) -> None:
        target_dir = tmp_path / "target_skills"
        installed_skill = target_dir / "test-skill"
        installed_skill.mkdir(parents=True)
        (installed_skill / "SKILL.md").write_text("name: test-skill\n# Old version\n")

        entry = SkillEntry(
            path=mock_skill_dir,
            name="test-skill",
            is_local=False,
            has_conflict=False,
        )

        annotate_skill_entries_status([entry], [target_dir])

        assert entry.is_installed is True
        assert entry.needs_update is True

    def test_multiple_target_dirs_mixed(self, mock_skill_dir: Path, tmp_path: Path) -> None:
        target_dir1 = tmp_path / "target1"
        target_dir2 = tmp_path / "target2"
        target_dir1.mkdir()
        target_dir2.mkdir()

        # Installed in target1, missing in target2
        installed1 = target_dir1 / "test-skill"
        installed1.mkdir()
        (installed1 / "SKILL.md").write_text("name: test-skill\n")

        entry = SkillEntry(
            path=mock_skill_dir,
            name="test-skill",
            is_local=False,
            has_conflict=False,
        )

        annotate_skill_entries_status([entry], [target_dir1, target_dir2])

        # Missing in target2 -> not fully installed across all target dirs
        assert entry.is_installed is False
        assert entry.needs_update is False


class TestRunSkillsCheck:
    def test_runs_only_for_selected_builtin_skills(self, tmp_path: Path) -> None:
        builtin_entry = SkillEntry(
            path=tmp_path / "jira",
            name="jira",
            is_local=False,
            has_conflict=False,
        )
        local_entry = SkillEntry(
            path=tmp_path / "custom-skill",
            name="custom-skill",
            is_local=True,
            has_conflict=False,
        )

        mock_check_main = MagicMock()

        captured_argv = []

        def side_effect():
            captured_argv.extend(sys.argv)

        mock_check_main.side_effect = side_effect

        with patch.dict(
            "sys.modules",
            {"mythril_agent_skills.cli.skills_check": MagicMock(main=mock_check_main)},
        ):
            run_skills_check([builtin_entry, local_entry])

            mock_check_main.assert_called_once()
            assert captured_argv == ["skills-check", "jira"]


    def test_skips_when_no_builtin_skills_selected(self, tmp_path: Path) -> None:
        local_entry = SkillEntry(
            path=tmp_path / "custom-skill",
            name="custom-skill",
            is_local=True,
            has_conflict=False,
        )

        mock_check_main = MagicMock()

        with patch.dict(
            "sys.modules",
            {"mythril_agent_skills.cli.skills_check": MagicMock(main=mock_check_main)},
        ):
            run_skills_check([local_entry])
            mock_check_main.assert_not_called()
