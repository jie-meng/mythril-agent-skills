"""Tests for fullstack-issue-archive: SKILL contract and routing rules."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = (
    REPO_ROOT / "mythril_agent_skills" / "skills" / "fullstack-issue-archive"
)


class TestIssueArchiveSkillContract:
    """The SKILL.md is the lifecycle authority — assert its text by path.

    Never import from this skill's scripts/: conftest puts all skills'
    scripts/ on sys.path and check_workspace.py exists in five skills.
    """

    @pytest.fixture(autouse=True)
    def _skill_md(self):
        path = SKILL_DIR / "SKILL.md"
        assert path.is_file(), f"missing SKILL.md at {path}"
        content = path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        self.frontmatter = parts[1]
        self.body = parts[2]

    def test_description_carries_trigger_markers(self):
        for marker in (
            "archive issue",
            "close issue",
            "归档 issue",
            "resolved",
            "fullstack-archive",
            "gh-operations",
        ):
            assert marker in self.frontmatter, f"description missing: {marker}"

    def test_lifecycle_steps_are_titled(self):
        assert "## Step 1 — Route by Target Type" in self.body
        assert "## Step 2 — Identify the Issue" in self.body
        assert "## Step 3 — Determine the Close Mode" in self.body
        assert "## Step 4 — Verify Closure and Integrity" in self.body
        assert "## Step 5 — Close" in self.body

    def test_closure_verification_is_blocking(self):
        assert "Closure verification gate" in self.body
        assert "Hard stops" in self.body
        assert "NOT CLOSED" in self.body
        assert "Never relabel an unresolved issue as `resolved`" in self.body

    def test_archive_it_is_not_proof(self):
        assert '"Archive it" is not proof that the problem is solved' in self.body

    def test_resolved_requires_fix_and_verification(self):
        assert "A concrete fix pointer" in self.body
        assert "verification that the symptom is gone" in self.body
        assert "with no fix pointer, or with a pointer but no verification" in self.body

    def test_verification_field_in_close_record(self):
        assert "- 验证:" in self.body
        assert "- Verification:" in self.body

    def test_unresolved_issue_is_kept_active_or_marked_wontfix(self):
        assert "keep the issue active" in self.body
        assert "closed without a verified fix by user decision" in self.body

    def test_route_rules_distinguish_target_trees(self):
        assert "issues/" in self.body
        assert "changes/{feat,refactor,fix}/" in self.body
        assert "Path beats prose" in self.body
        assert "hand off to `fullstack-archive`" in self.body

    def test_bare_archive_it_lists_both_tree(self):
        assert "List active issues AND active work items" in self.body

    def test_four_close_modes(self):
        for mode in ("proposed", "resolved", "wontfix", "merged"):
            assert mode in self.body, f"missing close mode: {mode}"

    def test_resolved_is_the_direct_fix_path(self):
        assert "Fixed directly, no work item needed" in self.body
        assert "No work item is created for a directly-fixed issue" in self.body

    def test_move_first_then_write(self):
        assert "move first, then write" in self.body
        assert "git add issues/" in self.body
        assert "POST-MOVE archive path" in self.body

    def test_name_unchanged_on_close(self):
        assert "directory name does not change" in self.body
        assert "YYYY-MM-DD-" not in self.body.split("## Step 5")[1]

    def test_close_record_follows_readme_language(self):
        assert "existing language" in self.body
        assert "## Closure" in self.body

    def test_archived_issue_is_read_only(self):
        assert "read-only forever" in self.body
        assert "There is no reopen" in self.body

    def test_bundled_workspace_gate_exists(self):
        assert (SKILL_DIR / "scripts" / "check_workspace.py").is_file()


class TestWorkItemArchiveRoutesIssuesAway:
    """fullstack-archive must not swallow issue close requests."""

    @pytest.fixture(autouse=True)
    def _skill_md(self):
        path = (
            REPO_ROOT
            / "mythril_agent_skills"
            / "skills"
            / "fullstack-archive"
            / "SKILL.md"
        )
        content = path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        self.frontmatter = parts[1]
        self.body = parts[2]

    def test_description_names_the_issue_handoff(self):
        assert "fullstack-issue-archive" in self.frontmatter
        assert "NOT for" in self.frontmatter
        assert "workspace issues" in self.frontmatter

    def test_step_one_routes_issue_paths(self):
        assert "Path under `<docs-dir>/issues/`" in self.body
        assert "hand off to `fullstack-issue-archive`" in self.body
        assert "List active work items AND active issues" in self.body

    def test_done_gate_is_blocking(self):
        assert "## Step 2 — Verify Done State and Check Integrity" in self.body
        assert "Done gate (BLOCKING)" in self.body
        assert "❌ Fail" in self.body
        assert "NEEDS_FIXES" in self.body
        assert "report `NOT DONE`" in self.body

    def test_early_archive_override_is_recorded(self):
        assert "Informed override" in self.body
        assert "progress.md` BEFORE" in self.body
        assert "Archived with SC-3" in self.body

