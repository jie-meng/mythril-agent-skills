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
        cfg = tmp_path / "fullstack.json"
        cfg.write_text('{"docs_dir": "my-docs"}')
        assert self.func(tmp_path) == {"docs_dir": "my-docs"}

    def test_corrupt_json(self, tmp_path: Path):
        cfg = tmp_path / "fullstack.json"
        cfg.write_text("not json at all")
        assert self.func(tmp_path) == {}

    def test_legacy_fallback(self, tmp_path: Path):
        legacy = tmp_path / ".fullstack-init.json"
        legacy.write_text('{"docs_dir": "old-docs"}')
        assert self.func(tmp_path) == {"docs_dir": "old-docs"}

    def test_new_config_takes_priority_over_legacy(self, tmp_path: Path):
        (tmp_path / "fullstack.json").write_text('{"docs_dir": "new"}')
        (tmp_path / ".fullstack-init.json").write_text('{"docs_dir": "old"}')
        assert self.func(tmp_path) == {"docs_dir": "new"}


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

    def test_removes_legacy_file(self, tmp_path: Path):
        legacy = tmp_path / ".fullstack-init.json"
        legacy.write_text('{"docs_dir": "old"}')
        self.save(tmp_path, {"docs_dir": "new"})
        assert not legacy.exists()
        assert (tmp_path / "fullstack.json").exists()


# ---------------------------------------------------------------------------
# resolve_github_repos
# ---------------------------------------------------------------------------


class TestResolveGithubRepos:
    """Tests for workspace_init.resolve_github_repos."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import resolve_github_repos, save_config
        self.func = resolve_github_repos
        self.save = save_config

    def test_cli_true_wins(self, tmp_path: Path):
        self.save(tmp_path, {"docs_dir": "docs", "github_repos": False})
        assert self.func(tmp_path, True) is True

    def test_cli_false_wins(self, tmp_path: Path):
        self.save(tmp_path, {"docs_dir": "docs", "github_repos": True})
        assert self.func(tmp_path, False) is False

    def test_saved_config_used(self, tmp_path: Path):
        self.save(tmp_path, {"docs_dir": "docs", "github_repos": True})
        assert self.func(tmp_path, None) is True

    def test_default_false_when_nothing(self, tmp_path: Path):
        assert self.func(tmp_path, None) is False

    def test_none_cli_reads_saved_false(self, tmp_path: Path):
        self.save(tmp_path, {"docs_dir": "docs", "github_repos": False})
        assert self.func(tmp_path, None) is False


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

    def test_ignores_infrastructure_and_docs_dirs(self, tmp_path: Path):
        _make_repo(tmp_path, "central-docs")
        _make_repo(tmp_path, "scripts")
        _make_repo(tmp_path, "real-repo")
        result = self.func(tmp_path, "central-docs")
        assert [r.name for r in result] == ["real-repo"]

    def test_empty_directory(self, tmp_path: Path):
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

    def test_python_project(self, tmp_path: Path):
        (tmp_path / "requirements.txt").write_text("flask")
        assert "Python" in self.func(tmp_path)

    def test_ios_project(self, tmp_path: Path):
        (tmp_path / "Podfile").write_text("platform :ios")
        assert "iOS" in self.func(tmp_path)

    def test_unknown_project(self, tmp_path: Path):
        assert self.func(tmp_path) == "—"


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
        assert self.func(tmp_path / "web") == "Web Frontend"

    def test_api_backend(self, tmp_path: Path):
        assert self.func(tmp_path / "api") == "Backend / API"

    def test_ios(self, tmp_path: Path):
        assert self.func(tmp_path / "ios-app") == "iOS"

    def test_unknown_role(self, tmp_path: Path):
        assert self.func(tmp_path / "foobar") == "—"


# ---------------------------------------------------------------------------
# build_repos_table
# ---------------------------------------------------------------------------


class TestBuildReposTable:
    """Tests for workspace_init.build_repos_table."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import build_repos_table
        self.func = build_repos_table

    def test_basic_table(self):
        repos = [
            {"name": "web", "role": "Web Frontend", "tech_stack": "TS", "description": "Dashboard"},
            {"name": "api", "role": "Backend", "tech_stack": "Python", "description": "REST API"},
        ]
        result = self.func(repos)
        assert "| 1 |" in result
        assert "| 2 |" in result
        assert "[web](./web/)" in result

    def test_empty_repos(self):
        result = self.func([])
        assert "Repository" in result
        assert "| 1 |" not in result


# ---------------------------------------------------------------------------
# generate_agents_md
# ---------------------------------------------------------------------------


class TestGenerateAgentsMd:
    """Tests for workspace_init.generate_agents_md."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_agents_md
        self.func = generate_agents_md

    def test_contains_project_name(self):
        result = self.func("my-project", "| table |", "central-docs")
        assert "# my-project" in result

    def test_contains_repos_table(self):
        result = self.func("proj", "| repos |", "central-docs")
        assert "| repos |" in result

    def test_uses_custom_docs_dir(self):
        result = self.func("proj", "| t |", "project_documents")
        assert "project_documents/" in result
        assert "central-docs" not in result

    def test_work_tracking_sections(self):
        result = self.func("proj", "| t |", "central-docs")
        assert "feat/" in result
        assert "refactor/" in result
        assert "fix/" in result

    def test_branch_convention(self):
        result = self.func("proj", "| t |", "central-docs")
        assert "feat/XYZ-706" in result

    def test_four_agents_in_structure(self):
        result = self.func("proj", "| t |", "central-docs")
        assert "planner.md" in result
        assert "developer.md" in result
        assert "reviewer.md" in result
        assert "debugger.md" in result

    def test_docs_is_independent_repo(self):
        result = self.func("proj", "| t |", "central-docs")
        assert "independent git repo" in result.lower()

    def test_mermaid_compatibility_section_present(self):
        result = self.func("proj", "| t |", "central-docs")
        assert "Mermaid Compatibility" in result
        assert "10.2.3" in result

    def test_mermaid_section_lists_unsupported_features(self):
        result = self.func("proj", "| t |", "central-docs")
        for keyword in (
            "block-beta",
            "quadrantChart",
            "xychart-beta",
            "sankey-beta",
            "architecture-beta",
            "@{ shape:",
        ):
            assert keyword in result, f"missing avoid-list keyword: {keyword}"

    def test_mermaid_section_lists_safe_features(self):
        result = self.func("proj", "| t |", "central-docs")
        for keyword in (
            "flowchart",
            "sequenceDiagram",
            "classDiagram",
            "stateDiagram-v2",
            "erDiagram",
            "gantt",
        ):
            assert keyword in result, f"missing allowed-list keyword: {keyword}"

    def test_mermaid_section_explains_failure_mode(self):
        result = self.func("proj", "| t |", "central-docs")
        assert "Syntax error in text" in result


# ---------------------------------------------------------------------------
# generate_docs_agents_md
# ---------------------------------------------------------------------------


class TestGenerateDocsAgentsMd:
    """Tests for workspace_init.generate_docs_agents_md."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_docs_agents_md
        self.func = generate_docs_agents_md

    def test_contains_docs_dir_name(self):
        result = self.func("project_documents")
        assert "project_documents" in result

    def test_title_is_humanized(self):
        result = self.func("central-docs")
        assert "# Central Docs" in result

    def test_independent_repo_note(self):
        result = self.func("central-docs")
        assert "independent git repository" in result.lower()

    def test_work_tracking_table(self):
        result = self.func("central-docs")
        for keyword in ("feat/", "refactor/", "fix/", "spike/"):
            assert keyword in result

    def test_mermaid_compatibility_note_present(self):
        result = self.func("central-docs")
        assert "Mermaid" in result
        assert "10.2.3" in result
        assert "Syntax error in text" in result

    def test_mermaid_note_points_to_workspace_agents_md(self):
        result = self.func("central-docs")
        assert "workspace root `AGENTS.md`" in result


# ---------------------------------------------------------------------------
# generate_agent_template
# ---------------------------------------------------------------------------


class TestGenerateAgentTemplate:
    """Tests for workspace_init.generate_agent_template."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_agent_template, AGENT_TEMPLATES
        self.func = generate_agent_template
        self.templates = AGENT_TEMPLATES

    def test_all_four_agents_exist(self):
        assert set(self.templates.keys()) == {"planner", "developer", "reviewer", "debugger"}

    def test_project_name_substitution(self):
        for name in self.templates:
            result = self.func(name, "my-project")
            assert "my-project" in result

    def test_planner_is_read_only(self):
        result = self.func("planner", "proj")
        assert "MUST NOT" in result

    def test_developer_implements(self):
        result = self.func("developer", "proj")
        assert "implementation" in result.lower()

    def test_reviewer_does_not_fix(self):
        result = self.func("reviewer", "proj")
        assert "Do not fix issues you find" in result

    def test_debugger_root_cause(self):
        result = self.func("debugger", "proj")
        assert "root cause" in result.lower()


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
        report = {"created": ["docs/"], "updated": [], "skipped": []}
        assert "+ docs/" in self.func(report)

    def test_updated_items(self):
        report = {"created": [], "updated": ["AGENTS.md"], "skipped": []}
        result = self.func(report)
        assert "Regenerated:" in result
        assert "~ AGENTS.md" in result

    def test_all_empty(self):
        report = {"created": [], "updated": [], "skipped": []}
        assert self.func(report) == ""


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    """Tests for workspace_init.detect_language."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import detect_language
        self.func = detect_language

    def test_english_text(self):
        assert self.func("Initialize this workspace") == "en"

    def test_chinese_text(self):
        assert self.func("初始化这个工作区") == "zh"

    def test_mixed_text(self):
        assert self.func("Initialize 初始化") == "zh"

    def test_empty_string(self):
        assert self.func("") == "en"

    def test_numbers_and_symbols(self):
        assert self.func("123 !@# >>>") == "en"

    def test_single_chinese_char(self):
        assert self.func("run 一下") == "zh"


# ---------------------------------------------------------------------------
# generate_readme
# ---------------------------------------------------------------------------


class TestGenerateReadme:
    """Tests for workspace_init.generate_readme."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import generate_readme
        self.func = generate_readme

    def test_english_default(self):
        result = self.func("my-project", "central-docs")
        assert "# my-project" in result
        assert "Quick Start" in result
        assert "central-docs" in result

    def test_english_explicit(self):
        result = self.func("proj", "docs", lang="en")
        assert "Quick Start" in result
        assert "快速上手" not in result

    def test_chinese(self):
        result = self.func("proj", "docs", lang="zh")
        assert "快速上手" in result
        assert "Quick Start" not in result

    def test_custom_docs_dir_in_english(self):
        result = self.func("proj", "my-docs", lang="en")
        assert "my-docs" in result
        assert "central-docs" not in result

    def test_custom_docs_dir_in_chinese(self):
        result = self.func("proj", "my-docs", lang="zh")
        assert "my-docs" in result

    def test_contains_init_instructions_en(self):
        result = self.func("proj", "docs", lang="en")
        assert "fullstack-init" in result
        assert "fullstack-impl" in result

    def test_contains_init_instructions_zh(self):
        result = self.func("proj", "docs", lang="zh")
        assert "fullstack-init" in result
        assert "fullstack-impl" in result

    def test_contains_resume_section_en(self):
        result = self.func("proj", "docs", lang="en")
        assert "resume" in result.lower() or "Resume" in result or "continue" in result.lower()

    def test_contains_resume_section_zh(self):
        result = self.func("proj", "docs", lang="zh")
        assert "继续" in result

    def test_contains_workspace_structure(self):
        result = self.func("proj", "docs", lang="en")
        assert "fullstack.json" in result
        assert "AGENTS.md" in result
        assert ".agents/" in result


# ---------------------------------------------------------------------------
# Integration: bootstrap_workspace
# ---------------------------------------------------------------------------


class TestBootstrapWorkspace:
    """Integration tests for bootstrap_workspace."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from workspace_init import bootstrap_workspace, load_config
        self.func = bootstrap_workspace
        self.load_config = load_config

    def test_fresh_init(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nFrontend app.\n")
        _make_repo(tmp_path, "api", "# API\n\nBackend service.\n")

        self.func(tmp_path)

        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / "README.md").exists()
        assert not (tmp_path / ".gitignore").exists()
        assert (tmp_path / "fullstack.json").exists()
        assert (tmp_path / "central-docs" / ".git").exists()
        assert (tmp_path / "central-docs" / "AGENTS.md").exists()
        assert (tmp_path / "central-docs" / "feat").is_dir()
        assert (tmp_path / "central-docs" / "refactor").is_dir()
        assert (tmp_path / "central-docs" / "fix").is_dir()
        assert (tmp_path / ".agents" / "skills").is_dir()
        assert (tmp_path / "scripts").is_dir()

        for name in ("planner", "developer", "reviewer", "debugger"):
            assert (tmp_path / ".agents" / "agents" / f"{name}.md").exists()

        agents_md = (tmp_path / "AGENTS.md").read_text()
        assert "[web](./web/)" in agents_md
        assert "[api](./api/)" in agents_md

    def test_rerun_regenerates_agents_md(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)

        (tmp_path / "AGENTS.md").write_text("# User garbage\n")

        _make_repo(tmp_path, "api", "# API\n\nService.\n")
        self.func(tmp_path)

        agents_md = (tmp_path / "AGENTS.md").read_text()
        assert "User garbage" not in agents_md
        assert "[web](./web/)" in agents_md
        assert "[api](./api/)" in agents_md

    def test_rerun_regenerates_agent_templates(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)

        dev_agent = tmp_path / ".agents" / "agents" / "developer.md"
        dev_agent.write_text("# Outdated content\n")

        self.func(tmp_path)
        content = dev_agent.read_text()
        assert "Outdated content" not in content
        assert "Developer" in content

    def test_no_workspace_git_init(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)
        assert not (tmp_path / ".git").exists()

    def test_docs_dir_preserved(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)

        custom_doc = tmp_path / "central-docs" / "feat" / "my-feature" / "plan.md"
        custom_doc.parent.mkdir(parents=True)
        custom_doc.write_text("# My plan\n")

        self.func(tmp_path)
        assert custom_doc.read_text() == "# My plan\n"

    def test_docs_agents_md_not_overwritten(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)

        docs_agents = tmp_path / "central-docs" / "AGENTS.md"
        docs_agents.write_text("# Custom docs rules\n")

        self.func(tmp_path)
        assert docs_agents.read_text() == "# Custom docs rules\n"

    def test_scripts_dir_preserved(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)

        script = tmp_path / "scripts" / "deploy.sh"
        script.write_text("#!/bin/bash\necho deploy\n")

        self.func(tmp_path)
        assert script.read_text() == "#!/bin/bash\necho deploy\n"

    def test_skills_dir_preserved(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)

        skill = tmp_path / ".agents" / "skills" / "my-skill" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# My skill\n")

        self.func(tmp_path)
        assert skill.read_text() == "# My skill\n"

    def test_custom_docs_dir(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path, docs_dir="project_documents")

        assert (tmp_path / "project_documents" / ".git").exists()
        assert not (tmp_path / "central-docs").exists()
        config = self.load_config(tmp_path)
        assert config["docs_dir"] == "project_documents"

    def test_rerun_reads_saved_docs_dir(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path, docs_dir="my-docs")

        self.func(tmp_path)
        config = self.load_config(tmp_path)
        assert config["docs_dir"] == "my-docs"

    def test_no_repos_found(self, tmp_path: Path):
        report = self.func(tmp_path)
        assert any("no git" in s.lower() for s in report["skipped"])

    def test_legacy_config_migration(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        legacy = tmp_path / ".fullstack-init.json"
        legacy.write_text('{"docs_dir": "my-docs"}')

        self.func(tmp_path)

        assert not legacy.exists()
        assert (tmp_path / "fullstack.json").exists()
        config = self.load_config(tmp_path)
        assert config["docs_dir"] == "my-docs"
        assert (tmp_path / "my-docs").exists()

    def test_readme_english_by_default(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)
        readme = (tmp_path / "README.md").read_text()
        assert "Quick Start" in readme

    def test_readme_chinese(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path, lang="zh")
        readme = (tmp_path / "README.md").read_text()
        assert "快速上手" in readme

    def test_readme_uses_docs_dir(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path, docs_dir="my-docs")
        readme = (tmp_path / "README.md").read_text()
        assert "my-docs" in readme

    def test_github_repos_saved_true(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path, github_repos=True)
        config = self.load_config(tmp_path)
        assert config["github_repos"] is True

    def test_github_repos_saved_false(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path, github_repos=False)
        config = self.load_config(tmp_path)
        assert config["github_repos"] is False

    def test_github_repos_defaults_false(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path)
        config = self.load_config(tmp_path)
        assert config["github_repos"] is False

    def test_github_repos_preserved_on_rerun(self, tmp_path: Path):
        _make_repo(tmp_path, "web", "# Web\n\nApp.\n")
        self.func(tmp_path, github_repos=True)
        self.func(tmp_path)
        config = self.load_config(tmp_path)
        assert config["github_repos"] is True
