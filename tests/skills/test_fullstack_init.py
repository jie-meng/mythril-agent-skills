"""Tests for fullstack-init skill scripts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


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


# ---------------------------------------------------------------------------
# load_config / save_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    """Tests for workspace_init.load_config."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import load_config
        self.func = load_config

    def test_no_config_file(self, tmp_path: Path):
        assert self.func(tmp_path) == {}

    def test_valid_config(self, tmp_path: Path):
        cfg = tmp_path / ".fullstack-init.json"
        cfg.write_text('{"docs_dir": "my-docs"}')
        assert self.func(tmp_path) == {"docs_dir": "my-docs"}

    def test_corrupt_json(self, tmp_path: Path):
        cfg = tmp_path / ".fullstack-init.json"
        cfg.write_text("not json at all")
        assert self.func(tmp_path) == {}


class TestSaveConfig:
    """Tests for workspace_init.save_config."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import save_config, load_config
        self.save = save_config
        self.load = load_config

    def test_roundtrip(self, tmp_path: Path):
        self.save(tmp_path, {"docs_dir": "shared-docs", "extra": "val"})
        loaded = self.load(tmp_path)
        assert loaded == {"docs_dir": "shared-docs", "extra": "val"}

    def test_overwrites_existing(self, tmp_path: Path):
        self.save(tmp_path, {"docs_dir": "old"})
        self.save(tmp_path, {"docs_dir": "new"})
        assert self.load(tmp_path)["docs_dir"] == "new"


# ---------------------------------------------------------------------------
# resolve_docs_dir
# ---------------------------------------------------------------------------


class TestResolveDocsDir:
    """Tests for workspace_init.resolve_docs_dir."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import resolve_docs_dir, save_config
        self.func = resolve_docs_dir
        self.save = save_config

    def test_cli_arg_wins(self, tmp_path: Path):
        self.save(tmp_path, {"docs_dir": "saved-name"})
        assert self.func(tmp_path, "from-cli") == "from-cli"

    def test_saved_config_used(self, tmp_path: Path):
        self.save(tmp_path, {"docs_dir": "project_documents"})
        assert self.func(tmp_path, None) == "project_documents"

    def test_default_when_nothing(self, tmp_path: Path):
        assert self.func(tmp_path, None) == "central-docs"

    def test_empty_string_cli_uses_saved(self, tmp_path: Path):
        self.save(tmp_path, {"docs_dir": "saved"})
        assert self.func(tmp_path, "") == "saved"


# ---------------------------------------------------------------------------
# get_infrastructure_dirs
# ---------------------------------------------------------------------------


class TestGetInfrastructureDirs:
    """Tests for workspace_init.get_infrastructure_dirs."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import get_infrastructure_dirs
        self.func = get_infrastructure_dirs

    def test_includes_docs_dir(self):
        result = self.func("my-special-docs")
        assert "my-special-docs" in result
        assert ".agents" in result
        assert "scripts" in result

    def test_different_names(self):
        r1 = self.func("docs-a")
        r2 = self.func("docs-b")
        assert "docs-a" in r1
        assert "docs-a" not in r2
        assert "docs-b" in r2


# ---------------------------------------------------------------------------
# discover_repos
# ---------------------------------------------------------------------------


class TestDiscoverRepos:
    """Tests for workspace_init.discover_repos."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import discover_repos
        self.func = discover_repos

    def test_finds_git_repos(self, tmp_path: Path):
        _make_repo(tmp_path, "web")
        _make_repo(tmp_path, "api")
        (tmp_path / "not-a-repo").mkdir()
        result = self.func(tmp_path, "central-docs")
        names = [r.name for r in result]
        assert names == ["api", "web"]

    def test_ignores_dotdirs(self, tmp_path: Path):
        _make_repo(tmp_path, ".hidden")
        _make_repo(tmp_path, "visible")
        result = self.func(tmp_path, "central-docs")
        assert [r.name for r in result] == ["visible"]

    def test_ignores_default_infrastructure_dirs(self, tmp_path: Path):
        _make_repo(tmp_path, "central-docs")
        _make_repo(tmp_path, "scripts")
        _make_repo(tmp_path, "real-repo")
        result = self.func(tmp_path, "central-docs")
        assert [r.name for r in result] == ["real-repo"]

    def test_ignores_custom_docs_dir(self, tmp_path: Path):
        _make_repo(tmp_path, "project_documents")
        _make_repo(tmp_path, "web")
        result = self.func(tmp_path, "project_documents")
        assert [r.name for r in result] == ["web"]

    def test_does_not_ignore_wrong_docs_dir(self, tmp_path: Path):
        _make_repo(tmp_path, "project_documents")
        _make_repo(tmp_path, "web")
        result = self.func(tmp_path, "central-docs")
        names = [r.name for r in result]
        assert "project_documents" in names

    def test_empty_directory(self, tmp_path: Path):
        assert self.func(tmp_path, "central-docs") == []

    def test_only_files(self, tmp_path: Path):
        (tmp_path / "somefile.txt").write_text("hello")
        assert self.func(tmp_path, "central-docs") == []


# ---------------------------------------------------------------------------
# _extract_first_description
# ---------------------------------------------------------------------------


class TestExtractFirstDescription:
    """Tests for workspace_init._extract_first_description."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import _extract_first_description
        self.func = _extract_first_description

    def test_basic_readme(self):
        text = "# My Project\n\nA simple web application for managing tasks.\n"
        assert self.func(text) == "A simple web application for managing tasks"

    def test_skips_badges_and_images(self):
        text = (
            "# Project\n\n"
            "![badge](https://img.shields.io/badge)\n"
            "<p align='center'>logo</p>\n"
            "The actual description line.\n"
        )
        assert self.func(text) == "The actual description line"

    def test_stops_at_next_heading(self):
        text = "# Title\n\nFirst para.\n\n## Details\n\nSecond para.\n"
        assert self.func(text) == "First para"

    def test_truncates_long_descriptions(self):
        long_line = "A" * 200
        text = f"# Title\n\n{long_line}\n"
        result = self.func(text)
        assert len(result) == 120
        assert result.endswith("...")

    def test_empty_text(self):
        assert self.func("") == ""

    def test_no_h1(self):
        assert self.func("Just some text without headings.") == ""

    def test_strips_trailing_period(self):
        text = "# Title\n\nEnds with period.\n"
        assert self.func(text) == "Ends with period"


# ---------------------------------------------------------------------------
# detect_tech_stack
# ---------------------------------------------------------------------------


class TestDetectTechStack:
    """Tests for workspace_init.detect_tech_stack."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import detect_tech_stack
        self.func = detect_tech_stack

    def test_javascript_project(self, tmp_path: Path):
        (tmp_path / "package.json").write_text("{}")
        assert "JavaScript" in self.func(tmp_path)

    def test_typescript_project(self, tmp_path: Path):
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "tsconfig.json").write_text("{}")
        result = self.func(tmp_path)
        assert "TypeScript" in result

    def test_python_project(self, tmp_path: Path):
        (tmp_path / "requirements.txt").write_text("flask")
        assert "Python" in self.func(tmp_path)

    def test_ios_project(self, tmp_path: Path):
        (tmp_path / "Podfile").write_text("platform :ios")
        assert "iOS" in self.func(tmp_path)

    def test_android_project(self, tmp_path: Path):
        (tmp_path / "build.gradle").write_text("apply plugin: 'com.android'")
        assert "Android" in self.func(tmp_path)

    def test_unknown_project(self, tmp_path: Path):
        assert self.func(tmp_path) == "—"

    def test_multi_stack(self, tmp_path: Path):
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "requirements.txt").write_text("django")
        result = self.func(tmp_path)
        assert "," in result


# ---------------------------------------------------------------------------
# detect_repo_role
# ---------------------------------------------------------------------------


class TestDetectRepoRole:
    """Tests for workspace_init.detect_repo_role."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import detect_repo_role
        self.func = detect_repo_role

    def test_web_frontend(self, tmp_path: Path):
        repo = tmp_path / "web"
        repo.mkdir()
        assert self.func(repo) == "Web Frontend"

    def test_api_backend(self, tmp_path: Path):
        repo = tmp_path / "api"
        repo.mkdir()
        assert self.func(repo) == "Backend / API"

    def test_ios(self, tmp_path: Path):
        repo = tmp_path / "ios-app"
        repo.mkdir()
        assert self.func(repo) == "iOS"

    def test_android(self, tmp_path: Path):
        repo = tmp_path / "android"
        repo.mkdir()
        assert self.func(repo) == "Android"

    def test_shared_lib(self, tmp_path: Path):
        repo = tmp_path / "shared-lib"
        repo.mkdir()
        assert self.func(repo) == "Shared Library"

    def test_unknown_role(self, tmp_path: Path):
        repo = tmp_path / "foobar"
        repo.mkdir()
        assert self.func(repo) == "—"


# ---------------------------------------------------------------------------
# build_repos_table
# ---------------------------------------------------------------------------


class TestBuildReposTable:
    """Tests for workspace_init.build_repos_table."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import build_repos_table, MARKER_START, MARKER_END
        self.func = build_repos_table
        self.marker_start = MARKER_START
        self.marker_end = MARKER_END

    def test_basic_table(self):
        repos = [
            {"name": "web", "role": "Web Frontend", "tech_stack": "TypeScript", "description": "Dashboard"},
            {"name": "api", "role": "Backend / API", "tech_stack": "Python", "description": "REST API"},
        ]
        result = self.func(repos)
        assert self.marker_start in result
        assert self.marker_end in result
        assert "| 1 |" in result
        assert "| 2 |" in result
        assert "[web](./web/)" in result
        assert "[api](./api/)" in result

    def test_empty_repos(self):
        result = self.func([])
        assert self.marker_start in result
        assert self.marker_end in result
        assert "| 1 |" not in result


# ---------------------------------------------------------------------------
# merge_repos_table
# ---------------------------------------------------------------------------


class TestMergeReposTable:
    """Tests for workspace_init.merge_repos_table."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import merge_repos_table, MARKER_START, MARKER_END
        self.func = merge_repos_table
        self.marker_start = MARKER_START
        self.marker_end = MARKER_END

    def test_replaces_between_markers(self):
        existing = (
            "# My Project\n\n"
            "Some intro.\n\n"
            "## Repositories\n\n"
            f"{self.marker_start}\n"
            "| old table |\n"
            f"{self.marker_end}\n\n"
            "## Custom Section\n\nMy custom notes.\n"
        )
        new_table = f"{self.marker_start}\n| new table |\n{self.marker_end}"
        result = self.func(existing, new_table)
        assert "| new table |" in result
        assert "| old table |" not in result
        assert "## Custom Section" in result
        assert "My custom notes." in result

    def test_preserves_content_before_and_after(self):
        existing = (
            "# Title\n\nIntro paragraph.\n\n"
            "## Repositories\n\n"
            f"{self.marker_start}\n| old |\n{self.marker_end}\n\n"
            "## Team Notes\n\nDon't delete me.\n"
        )
        new_table = f"{self.marker_start}\n| fresh |\n{self.marker_end}"
        result = self.func(existing, new_table)
        assert "Intro paragraph." in result
        assert "Don't delete me." in result
        assert "| fresh |" in result

    def test_appends_section_if_no_repos_section(self):
        existing = "# Title\n\nJust some content.\n"
        new_table = f"{self.marker_start}\n| added |\n{self.marker_end}"
        result = self.func(existing, new_table)
        assert "## Repositories" in result
        assert "| added |" in result
        assert "Just some content." in result

    def test_replaces_unmarked_table_in_repos_section(self):
        existing = (
            "# Title\n\n"
            "## Repositories\n\n"
            "| # | Name |\n"
            "|---|------|\n"
            "| 1 | old  |\n"
            "\n## Other\n\nKeep this.\n"
        )
        new_table = f"{self.marker_start}\n| new |\n{self.marker_end}"
        result = self.func(existing, new_table)
        assert "| new |" in result
        assert "Keep this." in result
        assert "| 1 | old  |" not in result


# ---------------------------------------------------------------------------
# generate_gitignore
# ---------------------------------------------------------------------------


class TestGenerateGitignore:
    """Tests for workspace_init.generate_gitignore."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_gitignore
        self.func = generate_gitignore

    def test_contains_docs_dir_name(self):
        result = self.func("project_documents")
        assert "!project_documents/" in result
        assert "!project_documents/**" in result

    def test_default_name(self):
        result = self.func("central-docs")
        assert "!central-docs/" in result

    def test_contains_standard_patterns(self):
        result = self.func("docs")
        assert "!AGENTS.md" in result
        assert "!.agents/" in result
        assert "!scripts/" in result
        assert "!.fullstack-init.json" in result


# ---------------------------------------------------------------------------
# needs_gitignore_update
# ---------------------------------------------------------------------------


class TestNeedsGitignoreUpdate:
    """Tests for workspace_init.needs_gitignore_update."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import needs_gitignore_update
        self.func = needs_gitignore_update

    def test_missing_file(self, tmp_path: Path):
        assert self.func(tmp_path / ".gitignore", "central-docs") is True

    def test_complete_file(self, tmp_path: Path):
        gi = tmp_path / ".gitignore"
        gi.write_text("!AGENTS.md\n!central-docs/\n!.agents/\n*\n")
        assert self.func(gi, "central-docs") is False

    def test_incomplete_file(self, tmp_path: Path):
        gi = tmp_path / ".gitignore"
        gi.write_text("!AGENTS.md\n*\n")
        assert self.func(gi, "central-docs") is True

    def test_wrong_docs_dir_name(self, tmp_path: Path):
        gi = tmp_path / ".gitignore"
        gi.write_text("!AGENTS.md\n!central-docs/\n!.agents/\n*\n")
        assert self.func(gi, "project_documents") is True

    def test_custom_docs_dir_present(self, tmp_path: Path):
        gi = tmp_path / ".gitignore"
        gi.write_text("!AGENTS.md\n!my-docs/\n!.agents/\n*\n")
        assert self.func(gi, "my-docs") is False


# ---------------------------------------------------------------------------
# generate_docs_agents_md
# ---------------------------------------------------------------------------


class TestGenerateDocsAgentsMd:
    """Tests for workspace_init.generate_docs_agents_md."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_docs_agents_md
        self.func = generate_docs_agents_md

    def test_uses_dir_name_in_heading(self):
        result = self.func("project-documents")
        assert "# Project Documents" in result

    def test_uses_dir_name_in_structure(self):
        result = self.func("my_docs")
        assert "my_docs/" in result

    def test_default_name(self):
        result = self.func("central-docs")
        assert "# Central Docs" in result


# ---------------------------------------------------------------------------
# generate_fresh_agents_md
# ---------------------------------------------------------------------------


class TestGenerateFreshAgentsMd:
    """Tests for workspace_init.generate_fresh_agents_md."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_fresh_agents_md
        self.func = generate_fresh_agents_md

    def test_contains_project_name(self):
        result = self.func("my-project", "| table |", "central-docs")
        assert "# my-project" in result

    def test_contains_repos_table(self):
        result = self.func("proj", "| repos table content |", "central-docs")
        assert "| repos table content |" in result

    def test_contains_structure_section(self):
        result = self.func("proj", "| t |", "central-docs")
        assert "central-docs/" in result
        assert ".agents/" in result

    def test_uses_custom_docs_dir(self):
        result = self.func("proj", "| t |", "project_documents")
        assert "project_documents/" in result
        assert "central-docs" not in result


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------


class TestFormatReport:
    """Tests for workspace_init.format_report."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import format_report
        self.func = format_report

    def test_created_items(self):
        report = {"created": ["AGENTS.md", ".gitignore"], "updated": [], "skipped": []}
        result = self.func(report)
        assert "+ AGENTS.md" in result
        assert "+ .gitignore" in result

    def test_updated_items(self):
        report = {"created": [], "updated": ["AGENTS.md (refreshed)"], "skipped": []}
        result = self.func(report)
        assert "~ AGENTS.md (refreshed)" in result

    def test_all_empty(self):
        report = {"created": [], "updated": [], "skipped": []}
        assert self.func(report) == ""


# ---------------------------------------------------------------------------
# Integration: bootstrap_workspace
# ---------------------------------------------------------------------------


class TestBootstrapWorkspace:
    """Integration tests for bootstrap_workspace using tmp_path."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import bootstrap_workspace, load_config
        self.func = bootstrap_workspace
        self.load_config = load_config

    def test_fresh_init_default_docs(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nFrontend React app.\n")
        _make_repo(tmp_path, "api", "# API\n\nBackend Python service.\n")

        report = self.func(tmp_path)

        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / ".gitignore").exists()
        assert (tmp_path / "central-docs" / "AGENTS.md").exists()
        assert (tmp_path / ".agents" / "skills").exists()
        assert (tmp_path / "scripts").exists()
        assert (tmp_path / "README.md").exists()
        assert (tmp_path / ".fullstack-init.json").exists()

        config = self.load_config(tmp_path)
        assert config["docs_dir"] == "central-docs"

        agents_content = (tmp_path / "AGENTS.md").read_text()
        assert "[web](./web/)" in agents_content
        assert "[api](./api/)" in agents_content

    def test_fresh_init_custom_docs(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")

        report = self.func(tmp_path, docs_dir="project_documents")

        assert (tmp_path / "project_documents" / "AGENTS.md").exists()
        assert not (tmp_path / "central-docs").exists()

        config = self.load_config(tmp_path)
        assert config["docs_dir"] == "project_documents"

        gitignore = (tmp_path / ".gitignore").read_text()
        assert "!project_documents/" in gitignore

        agents = (tmp_path / "AGENTS.md").read_text()
        assert "project_documents/" in agents

    def test_rerun_reads_saved_docs_dir(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path, docs_dir="my-docs")

        _make_repo(tmp_path, "api", "# API\n\nService.\n")
        report = self.func(tmp_path)

        config = self.load_config(tmp_path)
        assert config["docs_dir"] == "my-docs"
        assert (tmp_path / "my-docs" / "AGENTS.md").exists()

    def test_custom_docs_dir_excluded_from_repos(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        _make_repo(tmp_path, "project_documents", "# Docs\n\nShared docs.\n")

        self.func(tmp_path, docs_dir="project_documents")

        agents_content = (tmp_path / "AGENTS.md").read_text()
        assert "[web](./web/)" in agents_content
        assert "[project_documents]" not in agents_content

    def test_idempotent_rerun(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")

        self.func(tmp_path)
        agents_v1 = (tmp_path / "AGENTS.md").read_text()

        report2 = self.func(tmp_path)
        agents_v2 = (tmp_path / "AGENTS.md").read_text()

        assert agents_v1 == agents_v2
        assert any("unchanged" in s.lower() or "up to date" in s.lower()
                    for s in report2["skipped"])

    def test_preserves_user_content_on_rerun(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)

        agents_path = tmp_path / "AGENTS.md"
        original = agents_path.read_text()
        custom_section = "\n## My Custom Notes\n\nDon't delete this!\n"
        agents_path.write_text(original + custom_section)

        _make_repo(tmp_path, "api", "# API\n\nNew service.\n")
        self.func(tmp_path)

        updated = agents_path.read_text()
        assert "My Custom Notes" in updated
        assert "Don't delete this!" in updated
        assert "[api](./api/)" in updated

    def test_no_repos_found(self, tmp_path: Path):
        report = self.func(tmp_path)
        assert any("no git" in s.lower() for s in report["skipped"])

    def test_change_docs_dir_on_rerun(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path, docs_dir="old-docs")
        assert (tmp_path / "old-docs").exists()

        self.func(tmp_path, docs_dir="new-docs")
        assert (tmp_path / "new-docs").exists()
        config = self.load_config(tmp_path)
        assert config["docs_dir"] == "new-docs"

        gitignore = (tmp_path / ".gitignore").read_text()
        assert "!new-docs/" in gitignore

    def test_existing_docs_dir_not_overwritten(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        docs = tmp_path / "project_documents"
        docs.mkdir()
        custom_file = docs / "my-custom-doc.md"
        custom_file.write_text("# My important doc\n")

        self.func(tmp_path, docs_dir="project_documents")

        assert custom_file.exists()
        assert custom_file.read_text() == "# My important doc\n"
