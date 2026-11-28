"""Tests for fullstack-docs-migration skill scripts.

Covers pure/deterministic functions from migrate_scan.py:
- extract_status — parse **Status** field from plan.md
- extract_progress_status — detect completion markers in progress.md
- extract_verdict — parse spike verdict.md
- normalize_name — name normalization for spike↔impl matching
- find_impl_counterpart — match a spike to its impl work directory
- scan_work_items / scan_spikes / scan_non_convention_dirs — inventory
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


class TestExtractStatus:
    """Tests for migrate_scan.extract_status."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from migrate_scan import extract_status
        self.func = extract_status

    def test_english_status(self):
        text = "# X\n\n**Source**: foo\n**Status**: Done\n"
        assert self.func(text) == "Done"

    def test_chinese_status(self):
        text = "# X\n\n**状态**：已完成\n"
        assert self.func(text) == "已完成"

    def test_full_width_colon(self):
        text = "**Status**：Done v3 — final approach\n"
        assert self.func(text) == "Done v3 — final approach"

    def test_no_status_returns_empty(self):
        assert self.func("# X\n\nno status here\n") == ""

    def test_status_with_description_kept_verbatim(self):
        text = "**Status**: In Progress (Round 1 merged, iter-2 active)\n"
        assert self.func(text) == "In Progress (Round 1 merged, iter-2 active)"


class TestExtractProgressStatus:
    """Tests for migrate_scan.extract_progress_status."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from migrate_scan import extract_progress_status
        self.func = extract_progress_status

    def test_empty_text_returns_empty(self):
        assert self.func("") == ""

    def test_english_complete(self):
        assert self.func("**Overall status**: Complete") == "complete"

    def test_chinese_complete(self):
        assert self.func("**整体状态**：已完成") == "已完成"

    def test_done(self):
        assert self.func("## Status: Done") == "done"

    def test_in_progress_no_marker(self):
        assert self.func("**Overall status**: In Progress") == ""

    def test_merged_marker(self):
        assert self.func("已合并到主分支") == "已合并"

    def test_case_insensitive(self):
        assert self.func("COMPLETED on 2026-04-18") == "complete"

    def test_plain_progress_no_marker(self):
        assert self.func("## Change Log\n\nstarted\n") == ""

    # --- substring false positives the scanner used to report as done ---

    def test_incomplete_is_not_complete(self):
        assert self.func("Incomplete: blocked on API review") == ""

    def test_not_done_is_not_done(self):
        assert self.func("In progress, not done yet") == ""

    def test_not_yet_merged_is_not_merged(self):
        assert self.func("PR opened, not yet merged") == ""

    def test_almost_complete_is_not_complete(self):
        assert self.func("UI almost complete") == ""

    def test_completed_steps_heading_is_ignored(self):
        assert self.func("## Completed Steps\n\n- none yet\n") == ""

    def test_abandoned_does_not_contain_done(self):
        assert self.func("abandoned approach A, trying B") == ""

    def test_undone_is_not_done(self):
        assert self.func("rollback: change undone") == ""

    def test_unchecked_box_is_ignored(self):
        assert self.func("- [ ] merged to main\n- [ ] shipped\n") == ""

    def test_checked_box_counts(self):
        assert self.func("- [x] merged to main\n") == "merged"

    def test_chinese_not_completed(self):
        assert self.func("尚未完成，等待联调") == ""

    def test_status_line_decides_over_stray_marker(self):
        text = "**Status**: In Progress\n\n- 2026-05-01 — done with API\n"
        assert self.func(text) == ""

    def test_last_status_line_wins(self):
        text = "Status: In Progress\n...\nStatus: Done\n"
        assert self.func(text) == "done"


class TestExtractVerdict:
    """Tests for migrate_scan.extract_verdict."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from migrate_scan import extract_verdict
        self.func = extract_verdict

    def test_english_feasible(self):
        text = "**Verdict**: FEASIBLE\n"
        assert self.func(text) == "FEASIBLE"

    def test_english_not_feasible(self):
        text = "**Verdict**: NOT_FEASIBLE\n"
        assert self.func(text) == "NOT_FEASIBLE"

    def test_english_needs_more_research(self):
        text = "**Verdict**: NEEDS_MORE_RESEARCH\n"
        assert self.func(text) == "NEEDS_MORE_RESEARCH"

    def test_chinese_feasible(self):
        text = "**结论**：可行\n"
        assert self.func(text) == "FEASIBLE"

    def test_chinese_not_feasible(self):
        text = "**结论**：不可行\n"
        assert self.func(text) == "NOT_FEASIBLE"

    def test_chinese_needs_more_research(self):
        text = "**结论**：需要更多调研\n"
        assert self.func(text) == "NEEDS_MORE_RESEARCH"

    def test_missing_returns_empty(self):
        assert self.func("# Verdict\n\nno verdict\n") == ""

    def test_empty_text(self):
        assert self.func("") == ""


class TestNormalizeName:
    """Tests for migrate_scan.normalize_name."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from migrate_scan import normalize_name
        self.func = normalize_name

    def test_lowercase(self):
        assert self.func("Add-Dark-Mode") == "add_dark_mode"

    def test_hyphens_to_underscores(self):
        assert self.func("oauth-pkce") == "oauth_pkce"

    def test_underscores_kept(self):
        assert self.func("idle_button") == "idle_button"

    def test_trailing_separators_stripped(self):
        assert self.func("ble-token-encryption-") == "ble_token_encryption"

    def test_leading_separators_stripped(self):
        assert self.func("-random-audio") == "random_audio"


class TestFindImplCounterpart:
    """Tests for migrate_scan.find_impl_counterpart."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from migrate_scan import find_impl_counterpart
        self.func = find_impl_counterpart

    def _make_work_dirs(self, root: Path) -> dict:
        work_dirs = {"feat": [], "refactor": [], "fix": []}
        (root / "feat").mkdir()
        (root / "fix").mkdir()
        (root / "refactor").mkdir()
        (root / "feat" / "mood-emotion-update").mkdir()
        (root / "fix" / "idle-button-unresponsive").mkdir()
        work_dirs["feat"].append(root / "feat" / "mood-emotion-update")
        work_dirs["fix"].append(root / "fix" / "idle-button-unresponsive")
        return work_dirs

    def test_exact_match(self, tmp_path: Path):
        work_dirs = self._make_work_dirs(tmp_path)
        spike = tmp_path / "spike" / "idle-button-unresponsive"
        result = self.func(spike, tmp_path, work_dirs)
        assert result is not None
        assert result.name == "idle-button-unresponsive"
        assert result.parent.name == "fix"

    def test_hyphen_variation_match(self, tmp_path: Path):
        work_dirs = self._make_work_dirs(tmp_path)
        # Spike uses "mood_emotion_update", impl uses "mood-emotion-update".
        spike = tmp_path / "spike" / "mood_emotion_update"
        result = self.func(spike, tmp_path, work_dirs)
        assert result is not None
        assert result.name == "mood-emotion-update"

    def test_no_match_returns_none(self, tmp_path: Path):
        work_dirs = self._make_work_dirs(tmp_path)
        spike = tmp_path / "spike" / "harmonyos-support"
        assert self.func(spike, tmp_path, work_dirs) is None

    def test_different_impl_name_no_match(self, tmp_path: Path):
        work_dirs = self._make_work_dirs(tmp_path)
        # Spike es8311 vs impl remove-es8311-dead-code — NOT a name match.
        spike = tmp_path / "spike" / "es8311-detect-headphone"
        assert self.func(spike, tmp_path, work_dirs) is None


class TestScanFunctions:
    """Tests for the migrate_scan inventory functions (filesystem)."""

    def _build_legacy_docs(self, root: Path) -> None:
        """Build a representative legacy docs repo layout."""
        # feat work item — complete
        feat = root / "feat" / "import-export"
        feat.mkdir(parents=True)
        (feat / "analysis.md").write_text("# Analysis: Import-Export\n")
        (feat / "plan.md").write_text(
            "# Import-Export\n\n**Status**: In Progress\n"
        )
        (feat / "progress.md").write_text(
            "# Progress: Import-Export\n\n**Overall status**: Complete\n"
        )
        (feat / "review.md").write_text("# Review: Import-Export\n")
        # fix work item — active
        fix = root / "fix" / "timezone-default-zero"
        fix.mkdir(parents=True)
        (fix / "plan.md").write_text("# Fix\n\n**Status**: In Progress\n")
        (fix / "progress.md").write_text(
            "# Progress\n\n## Change Log\n\n### 2026-04-21 — Started\n"
        )
        # spike with matching impl
        (root / "spike" / "import-export").mkdir(parents=True)
        (root / "spike" / "import-export" / "verdict.md").write_text(
            "**Verdict**: FEASIBLE\n"
        )
        # orphan spike
        (root / "spike" / "harmonyos-support").mkdir(parents=True)
        (root / "spike" / "harmonyos-support" / "verdict.md").write_text(
            "**Verdict**: FEASIBLE\n"
        )
        # non-convention dirs
        (root / "docs").mkdir()
        (root / "robocontrol-changelog").mkdir()

    def test_scan_work_items(self, tmp_path: Path):
        self._build_legacy_docs(tmp_path)
        from migrate_scan import scan_work_items
        items, work_dirs = scan_work_items(tmp_path)
        by_name = {i["name"]: i for i in items}
        assert set(by_name) == {"import-export", "timezone-default-zero"}
        item = by_name["import-export"]
        assert item["type"] == "feat"
        assert item["four_files"] == {
            "analysis": True, "plan": True, "progress": True, "review": True,
        }
        assert item["plan_status"] == "In Progress"
        assert item["progress_status"] == "complete"
        active = by_name["timezone-default-zero"]
        assert active["plan_status"] == "In Progress"
        assert active["progress_status"] == ""

    def test_scan_spikes_matches_impl(self, tmp_path: Path):
        self._build_legacy_docs(tmp_path)
        from migrate_scan import scan_spikes, scan_work_items
        items, work_dirs = scan_work_items(tmp_path)
        spikes = scan_spikes(tmp_path, work_dirs, items)
        by_name = {s["name"]: s for s in spikes}
        assert by_name["import-export"]["verdict"] == "FEASIBLE"
        assert by_name["import-export"]["impl_counterpart"] == "feat/import-export"
        assert by_name["harmonyos-support"]["impl_counterpart"] is None

    def test_scan_non_convention_dirs(self, tmp_path: Path):
        self._build_legacy_docs(tmp_path)
        from migrate_scan import scan_non_convention_dirs
        dirs = scan_non_convention_dirs(tmp_path)
        assert "docs" in dirs
        assert "robocontrol-changelog" in dirs
        assert "feat" not in dirs
        assert "spike" not in dirs

    def test_main_outputs_json(self, tmp_path: Path, capsys, monkeypatch):
        self._build_legacy_docs(tmp_path)
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        from migrate_scan import main
        monkeypatch.setattr("sys.argv", ["migrate_scan.py", str(tmp_path)])
        rc = main()
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert "work_items" in data
        assert "spikes" in data
        assert "non_convention_dirs" in data

    def test_main_not_a_git_repo(self, tmp_path: Path, capsys, monkeypatch):
        self._build_legacy_docs(tmp_path)
        monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
        from migrate_scan import main
        monkeypatch.setattr("sys.argv", ["migrate_scan.py", str(tmp_path)])
        assert main() == 1
        assert "not a git repository" in capsys.readouterr().err

    def test_non_convention_dirs_skip_dot_dirs(self, tmp_path: Path):
        self._build_legacy_docs(tmp_path)
        (tmp_path / ".git").mkdir()
        from migrate_scan import scan_non_convention_dirs
        assert ".git" not in scan_non_convention_dirs(tmp_path)

    def test_main_bad_arg(self, tmp_path: Path, capsys, monkeypatch):
        from migrate_scan import main
        monkeypatch.setattr("sys.argv", ["migrate_scan.py"])
        rc = main()
        assert rc == 2

    def test_main_missing_dir(self, tmp_path: Path, capsys, monkeypatch):
        from migrate_scan import main
        monkeypatch.setattr("sys.argv", ["migrate_scan.py", str(tmp_path / "nope")])
        rc = main()
        assert rc == 2


class TestLatestDateInText:
    """Tests for migrate_scan.latest_date_in_text."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from migrate_scan import latest_date_in_text
        self.func = latest_date_in_text

    def test_picks_latest(self):
        from datetime import date

        text = "### 2026-03-01\n### 2026-05-03 — merged\n### 2026-04-10\n"
        assert self.func(text, date(2026, 11, 1)) == "2026-05-03"

    def test_ignores_future_and_invalid_dates(self):
        from datetime import date

        text = "2026-02-30 is invalid, 2027-01-01 is future, 2026-01-05 ok"
        assert self.func(text, date(2026, 11, 1)) == "2026-01-05"

    def test_no_date(self):
        assert self.func("no dates here") == ""


class TestLastActiveInfo:
    """last_active falls back from git to progress.md dates to mtime."""

    @pytest.fixture(autouse=True)
    def _import(self, monkeypatch, tmp_path: Path):
        from migrate_scan import last_active_info
        self.func = last_active_info
        # Keep git from finding a repository above tmp_path.
        monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    def test_progress_dates_without_git(self, tmp_path: Path):
        item = tmp_path / "feat" / "x"
        item.mkdir(parents=True)
        (item / "progress.md").write_text("### 2025-12-01 — started\n### 2026-01-09\n")
        assert self.func(tmp_path, item) == ("2026-01-09", "progress")

    def test_mtime_without_git_or_dates(self, tmp_path: Path):
        item = tmp_path / "feat" / "y"
        item.mkdir(parents=True)
        (item / "plan.md").write_text("# Plan\n")
        found, source = self.func(tmp_path, item)
        assert source == "mtime"
        assert len(found) == 10


class TestGitLastCommitDate:
    """Tests for migrate_scan.git_last_commit_date (subprocess, best-effort)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from migrate_scan import git_last_commit_date
        self.func = git_last_commit_date

    def test_non_git_dir_returns_empty(self, tmp_path: Path):
        # Not a git repo — subprocess fails or returns nothing.
        (tmp_path / "feat").mkdir()
        assert self.func(tmp_path, "feat") == ""

    def test_git_repo_returns_date(self, tmp_path: Path):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / "a.md").write_text("x")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-q", "-m", "init"],
            cwd=tmp_path, check=True,
        )
        date = self.func(tmp_path, "a.md")
        assert len(date) == 10  # YYYY-MM-DD


class TestSkillContract:
    """SKILL.md rules that the scanner cannot enforce."""

    SKILL = (
        Path(__file__).resolve().parents[2]
        / "mythril_agent_skills/skills/fullstack-docs-migration/SKILL.md"
    )

    def test_spike_merge_never_deletes_the_linked_record(self):
        text = self.SKILL.read_text(encoding="utf-8")
        assert "git rm" not in text
        assert "../../archive/YYYY-MM-DD-spike-<name>/" in text
        assert "the link must resolve" in text
