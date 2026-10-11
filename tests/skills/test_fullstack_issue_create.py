"""Tests for fullstack-issue-create: init scaffolding, generated templates, SKILL contract."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ISSUE_SKILL_DIR = (
    REPO_ROOT / "mythril_agent_skills" / "skills" / "fullstack-issue-create"
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_repo(tmp_path: Path, name: str, readme: str = "") -> Path:
    """Create a fake git repo directory with .git/ and optional README."""
    repo = tmp_path / name
    repo.mkdir()
    (repo / ".git").mkdir()
    if readme:
        (repo / "README.md").write_text(readme, encoding="utf-8")
    return repo


def _snapshot(root: Path) -> dict[str, bytes]:
    """Return path -> bytes for every file under root (sorted, stable)."""
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


# ---------------------------------------------------------------------------
# Scaffolding: bootstrap_workspace provisions issues/ create-only (REQ2)
# ---------------------------------------------------------------------------


class TestIssueScaffolding:
    """Integration tests: issues/ and issues/archive/ are create-only dirs."""

    @pytest.fixture(autouse=True)
    def _import(self):
        # workspace_init is the only module with this name across skills —
        # never bare-import the four same-named check_workspace modules.
        from workspace_init import bootstrap_workspace
        self.func = bootstrap_workspace

    def test_fresh_workspace_creates_issues_dirs(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")

        self.func(tmp_path)

        assert (tmp_path / "central-docs" / "issues").is_dir()
        assert (tmp_path / "central-docs" / "issues" / "archive").is_dir()

    def test_report_lists_issue_dirs_as_created(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")

        report = self.func(tmp_path)

        assert any(
            "central-docs/issues/ (issue tracking)" in e for e in report["created"]
        )
        assert any(
            "central-docs/issues/archive/ (archived issues)" in e
            for e in report["created"]
        )

    def test_rerun_does_not_touch_issue_dirs(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)
        first = _snapshot(tmp_path / "central-docs" / "issues")

        report = self.func(tmp_path)

        assert not any("issues" in e for e in report["created"])
        assert not any("issues" in e for e in report["updated"])
        assert _snapshot(tmp_path / "central-docs" / "issues") == first

    def test_manual_issue_dir_survives_rerun_byte_for_byte(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)

        issue = (
            tmp_path / "central-docs" / "issues" / "2026-10-11-brownout-4g-bursts"
        )
        log_dir = issue / "log"
        log_dir.mkdir(parents=True)
        (issue / "README.md").write_text(
            "# Brownout during 4G bursts\n", encoding="utf-8"
        )
        (log_dir / "2026-10-11-robo-az3-serial-capture.log").write_bytes(
            b"\x00\x01raw evidence bytes"
        )
        (log_dir / "2026-10-11-robo-az3-serial-capture.cleaned.log").write_text(
            "trimmed window", encoding="utf-8"
        )
        before = _snapshot(issue)

        report = self.func(tmp_path)

        assert _snapshot(issue) == before
        assert not any(
            "2026-10-11-brownout-4g-bursts" in e
            for e in report["created"] + report["updated"]
        )

    def test_custom_docs_dir_gets_issues_dirs(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")

        self.func(tmp_path, docs_dir="project_documents")

        assert (tmp_path / "project_documents" / "issues").is_dir()
        assert (tmp_path / "project_documents" / "issues" / "archive").is_dir()


# ---------------------------------------------------------------------------
# Templates: workspace AGENTS.md (generate_agents_md)
# ---------------------------------------------------------------------------


class TestWorkspaceAgentsMdIssues:
    """generate_agents_md must carry the issues convention in Work Tracking + tree."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_agents_md, parse_agents_md_sections
        self.func = generate_agents_md
        self.parse = parse_agents_md_sections

    def _work_tracking_section(self) -> str:
        result = self.func("proj", "| t |", "central-docs")
        _h1, sections = self.parse(result)
        return next(body for title, body in sections if title == "## Work Tracking")

    def test_work_tracking_section_documents_issues(self):
        section = self._work_tracking_section()
        assert "issues/" in section
        assert "sibling of `changes/`" in section
        assert "YYYY-MM-DD-<name>" in section
        assert "date = the record day" in section
        assert "log/" in section
        assert "issues/archive/" in section
        assert "fullstack-issue-create" in section

    def test_work_tracking_states_close_semantics(self):
        section = self._work_tracking_section()
        assert "name unchanged" in section
        assert "never deleted" in section

    def test_directory_structure_tree_lists_issues(self):
        result = self.func("proj", "| t |", "central-docs")
        # The workspace AGENTS.md tree carries no per-line comments, so
        # assert the two new lines adjacent — a bare "archive/" substring
        # would also match the changes/ archive line and prove nothing.
        assert "│   ├── issues/\n│   │   └── archive/" in result


# ---------------------------------------------------------------------------
# Templates: docs AGENTS.md (generate_docs_agents_md)
# ---------------------------------------------------------------------------


class TestDocsAgentsMdIssues:
    """generate_docs_agents_md must carry the issues convention."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_docs_agents_md
        self.func = generate_docs_agents_md

    def test_work_tracking_table_has_issues_row(self):
        result = self.func("central-docs")
        assert "| `issues/` |" in result

    def test_work_tracking_explains_issue_shape_and_close_move(self):
        result = self.func("central-docs")
        assert "fullstack-issue-create" in result
        assert "YYYY-MM-DD-<name>" in result
        assert "log/" in result
        assert "issues/archive/" in result
        assert "name unchanged" in result

    def test_structure_tree_lists_issues(self):
        result = self.func("central-docs")
        # Assert the new lines WITH their comment suffixes — a bare
        # "archive/" substring would also match the changes/ archive line.
        assert "├── issues/            # Issue records (pre-work-item)" in result
        assert "│   └── archive/       #   Closed issues (name unchanged)" in result


# ---------------------------------------------------------------------------
# Templates: README.md — English and Chinese halves asserted separately
# ---------------------------------------------------------------------------


class TestReadmeIssuesEnglish:
    """_generate_readme_en must carry the issues convention (EN half)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_readme
        self.func = generate_readme

    def test_structure_tree_lists_issues(self):
        result = self.func("proj", "central-docs", lang="en")
        assert "│   ├── issues/" in result
        assert "│   │   └── archive/" in result
        assert "Issue records (pre-work-item)" in result

    def test_work_tracking_paragraph(self):
        result = self.func("proj", "central-docs", lang="en")
        assert "issues/YYYY-MM-DD-<name>" in result
        assert "date = the record day" in result
        assert "log/" in result
        assert "issues/archive/" in result
        assert "name unchanged" in result
        assert "fullstack-issue-create" in result

    def test_no_chinese_half_bleed(self):
        result = self.func("proj", "central-docs", lang="en")
        assert "问题记录" not in result


class TestReadmeIssuesChinese:
    """_generate_readme_zh must carry the issues convention (ZH half)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_readme
        self.func = generate_readme

    def test_structure_tree_lists_issues(self):
        result = self.func("proj", "central-docs", lang="zh")
        # Assert the new line WITH its comment suffix — a bare
        # "archive/" substring would also match the changes/ archive line.
        assert "│   ├── issues/        #   问题记录（立项前）" in result
        assert "│   │   └── archive/   #   已关闭 issue" in result
        assert "问题记录" in result

    def test_work_tracking_paragraph(self):
        result = self.func("proj", "central-docs", lang="zh")
        assert "issues/YYYY-MM-DD-<name>" in result
        assert "记录日" in result
        assert "log/" in result
        assert "issues/archive/" in result
        assert "目录名保持不变" in result
        assert "fullstack-issue-create" in result

    def test_no_english_half_bleed(self):
        result = self.func("proj", "central-docs", lang="zh")
        assert "Issue records (pre-work-item)" not in result


# ---------------------------------------------------------------------------
# SKILL contract: fullstack-issue-create/SKILL.md (read by path, never imported)
# ---------------------------------------------------------------------------


class TestIssueCreateSkillContract:
    """The SKILL.md is the lifecycle authority — assert its text by path.

    Never import from this skill's scripts/: conftest puts all skills'
    scripts/ on sys.path and check_workspace.py exists in four skills.
    """

    @pytest.fixture(autouse=True)
    def _skill_md(self):
        path = ISSUE_SKILL_DIR / "SKILL.md"
        assert path.is_file(), f"missing SKILL.md at {path}"
        content = path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        self.frontmatter = parts[1]
        self.body = parts[2]

    def test_description_carries_trigger_markers(self):
        for marker in (
            "fullstack issue",
            "记录这个问题",
            "log this problem",
            "track this problem",
            "gh-operations",
        ):
            assert marker in self.frontmatter, f"description missing: {marker}"

    def test_three_operations_are_titled(self):
        assert "## Step 1 — Create" in self.body
        assert "## Step 2 — Update" in self.body
        assert "## Step 3 — Close" in self.body

    def test_boundary_section_with_github(self):
        assert "Boundary with GitHub" in self.body

    def test_directory_naming_rules(self):
        assert "YYYY-MM-DD-" in self.body
        assert "-HHMM" in self.body

    def test_log_evidence_rules(self):
        assert "log/" in self.body
        assert ".cleaned.log" in self.body

    def test_archive_location(self):
        assert "issues/archive" in self.body

    def test_four_close_modes(self):
        for mode in ("proposed", "resolved", "wontfix", "merged"):
            assert mode in self.body, f"missing close mode: {mode}"
