"""Tests for github-pr-create skill scripts.

Covers pure/deterministic functions from detect_pr_template.py:
- find_repo_root
- detect_single_template
- detect_multiple_templates
- run (end-to-end detection)
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ── detect_pr_template ─────────────────────────────────────────────────────────


class TestDetectSingleTemplate:
    """Tests for detect_pr_template.detect_single_template."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from detect_pr_template import detect_single_template

        self.func = detect_single_template

    def test_github_lowercase(self, tmp_path: Path):
        template = tmp_path / ".github" / "pull_request_template.md"
        template.parent.mkdir(parents=True)
        template.write_text("## PR\n")
        assert self.func(tmp_path) == template

    def test_github_uppercase(self, tmp_path: Path):
        template = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE.md"
        template.parent.mkdir(parents=True)
        template.write_text("## PR\n")
        result = self.func(tmp_path)
        assert result is not None
        assert result.exists()
        assert result.parent == template.parent

    def test_root_lowercase(self, tmp_path: Path):
        template = tmp_path / "pull_request_template.md"
        template.write_text("## PR\n")
        assert self.func(tmp_path) == template

    def test_root_uppercase(self, tmp_path: Path):
        template = tmp_path / "PULL_REQUEST_TEMPLATE.md"
        template.write_text("## PR\n")
        result = self.func(tmp_path)
        assert result is not None
        assert result.exists()
        assert result.parent == template.parent

    def test_docs_directory(self, tmp_path: Path):
        template = tmp_path / "docs" / "pull_request_template.md"
        template.parent.mkdir(parents=True)
        template.write_text("## PR\n")
        assert self.func(tmp_path) == template

    def test_priority_github_over_root(self, tmp_path: Path):
        gh_template = tmp_path / ".github" / "pull_request_template.md"
        gh_template.parent.mkdir(parents=True)
        gh_template.write_text("## GitHub PR\n")
        root_template = tmp_path / "pull_request_template.md"
        root_template.write_text("## Root PR\n")
        assert self.func(tmp_path) == gh_template

    def test_no_template(self, tmp_path: Path):
        assert self.func(tmp_path) is None


class TestDetectMultipleTemplates:
    """Tests for detect_pr_template.detect_multiple_templates."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from detect_pr_template import detect_multiple_templates

        self.func = detect_multiple_templates

    def test_template_directory(self, tmp_path: Path):
        tpl_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "feature.md").write_text("## Feature\n")
        (tpl_dir / "bugfix.md").write_text("## Bugfix\n")
        result = self.func(tmp_path)
        assert len(result) == 2
        names = [p.stem for p in result]
        assert "bugfix" in names
        assert "feature" in names

    def test_ignores_non_md_files(self, tmp_path: Path):
        tpl_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "feature.md").write_text("## Feature\n")
        (tpl_dir / "notes.txt").write_text("not a template\n")
        result = self.func(tmp_path)
        assert len(result) == 1
        assert result[0].stem == "feature"

    def test_empty_directory(self, tmp_path: Path):
        tpl_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        tpl_dir.mkdir(parents=True)
        assert self.func(tmp_path) == []

    def test_no_directory(self, tmp_path: Path):
        assert self.func(tmp_path) == []


class TestFindRepoRoot:
    """Tests for detect_pr_template.find_repo_root."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from detect_pr_template import find_repo_root

        self.func = find_repo_root

    def test_finds_git_dir(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        subdir = tmp_path / "src" / "components"
        subdir.mkdir(parents=True)
        assert self.func(subdir) == tmp_path

    def test_returns_start_when_no_git(self, tmp_path: Path):
        subdir = tmp_path / "some" / "deep" / "path"
        subdir.mkdir(parents=True)
        result = self.func(subdir)
        assert result == subdir.resolve()


class TestRun:
    """Tests for detect_pr_template.run (end-to-end)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from detect_pr_template import run

        self.func = run

    def test_single_template_found(self, tmp_path: Path):
        template = tmp_path / ".github" / "pull_request_template.md"
        template.parent.mkdir(parents=True)
        template.write_text("## Summary\n\nDescribe changes.\n")

        result = self.func(tmp_path)
        assert result["TEMPLATE_FOUND"] == "true"
        assert result["MULTIPLE_TEMPLATES"] == "false"
        assert result["TEMPLATE_PATH"] == ".github/pull_request_template.md"
        assert "TEMPLATE_CONTENT" in result

        import base64

        decoded = base64.b64decode(result["TEMPLATE_CONTENT"]).decode("utf-8")
        assert "## Summary" in decoded

    def test_multiple_templates_found(self, tmp_path: Path):
        tpl_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "feature.md").write_text("## Feature PR\n")
        (tpl_dir / "bugfix.md").write_text("## Bugfix PR\n")

        result = self.func(tmp_path)
        assert result["TEMPLATE_FOUND"] == "true"
        assert result["MULTIPLE_TEMPLATES"] == "true"
        assert "TEMPLATE_NAMES" in result
        names = result["TEMPLATE_NAMES"].split(",")
        assert "feature" in names
        assert "bugfix" in names

    def test_no_template(self, tmp_path: Path):
        result = self.func(tmp_path)
        assert result["TEMPLATE_FOUND"] == "false"
        assert result["MULTIPLE_TEMPLATES"] == "false"
        assert "TEMPLATE_PATH" not in result

    def test_multiple_templates_take_precedence(self, tmp_path: Path):
        """Multiple templates in directory should take precedence over single file."""
        tpl_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "feature.md").write_text("## Feature PR\n")

        single = tmp_path / ".github" / "pull_request_template.md"
        single.write_text("## Single PR\n")

        result = self.func(tmp_path)
        assert result["MULTIPLE_TEMPLATES"] == "true"
