"""Tests for fullstack-brief skill scripts."""

import json

import pytest


class TestDetectScope:
    """Tests for detect_scope.detect_scope."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from detect_scope import detect_scope
        self.func = detect_scope

    def _make_workspace(self, root, docs_dir="central-docs", github_repos=False):
        (root / "AGENTS.md").write_text("# workspace")
        (root / ".agents").mkdir()
        config = {"docs_dir": docs_dir, "github_repos": github_repos}
        (root / "fullstack.json").write_text(json.dumps(config))

    def test_workspace_valid(self, tmp_path):
        self._make_workspace(tmp_path, docs_dir="my-docs", github_repos=True)
        result = self.func(tmp_path)
        assert result["SCOPE"] == "workspace"
        assert result["DOCS_DIR"] == "my-docs"
        assert result["GITHUB_REPOS"] == "true"

    def test_workspace_defaults_when_config_keys_missing(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# workspace")
        (tmp_path / ".agents").mkdir()
        (tmp_path / "fullstack.json").write_text("{}")
        result = self.func(tmp_path)
        assert result["SCOPE"] == "workspace"
        assert result["DOCS_DIR"] == ""
        assert result["GITHUB_REPOS"] == "false"

    def test_workspace_corrupt_config_still_detected(self, tmp_path):
        self._make_workspace(tmp_path)
        (tmp_path / "fullstack.json").write_text("{not json")
        result = self.func(tmp_path)
        assert result["SCOPE"] == "workspace"
        assert result["DOCS_DIR"] == ""
        assert result["GITHUB_REPOS"] == "false"

    def test_agents_marker_must_be_directory(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# workspace")
        (tmp_path / "fullstack.json").write_text("{}")
        (tmp_path / ".agents").write_text("not a dir")
        result = self.func(tmp_path)
        assert result["SCOPE"] != "workspace"

    def test_single_repo_git_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        result = self.func(tmp_path)
        assert result["SCOPE"] == "repo"
        assert result["IS_GIT"] == "true"
        assert result["DOCS_DIR"] == ""

    def test_single_repo_git_file_worktree(self, tmp_path):
        (tmp_path / ".git").write_text("gitdir: ../elsewhere\n")
        result = self.func(tmp_path)
        assert result["SCOPE"] == "repo"
        assert result["IS_GIT"] == "true"

    def test_partial_markers_fall_back_to_repo(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# repo-level agents file")
        (tmp_path / ".git").mkdir()
        result = self.func(tmp_path)
        assert result["SCOPE"] == "repo"

    def test_no_scope(self, tmp_path):
        result = self.func(tmp_path)
        assert result["SCOPE"] == "none"
        assert result["IS_GIT"] == "false"


class TestReadWorkspaceConfig:
    """Tests for detect_scope.read_workspace_config."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from detect_scope import read_workspace_config
        self.func = read_workspace_config

    def test_reads_values(self, tmp_path):
        (tmp_path / "fullstack.json").write_text(
            '{"docs_dir": "docs", "github_repos": true}'
        )
        docs_dir, github_repos = self.func(tmp_path)
        assert docs_dir == "docs"
        assert github_repos == "true"

    def test_missing_file_returns_defaults(self, tmp_path):
        docs_dir, github_repos = self.func(tmp_path)
        assert docs_dir == ""
        assert github_repos == "false"

    def test_corrupt_file_returns_defaults(self, tmp_path):
        (tmp_path / "fullstack.json").write_text("]]]")
        docs_dir, github_repos = self.func(tmp_path)
        assert docs_dir == ""
        assert github_repos == "false"


class TestMissingMarkers:
    """Tests for detect_scope._missing_markers."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from detect_scope import _missing_markers
        self.func = _missing_markers

    def test_all_present(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("")
        (tmp_path / ".agents").mkdir()
        (tmp_path / "fullstack.json").write_text("{}")
        assert self.func(tmp_path) == []

    def test_reports_each_missing(self, tmp_path):
        missing = self.func(tmp_path)
        assert set(missing) == {"AGENTS.md", ".agents", "fullstack.json"}


class TestMain:
    """Tests for detect_scope.main exit codes and output."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from detect_scope import main
        self.func = main

    def _run(self, capsys, *argv):
        code = self.func(list(argv))
        return code, capsys.readouterr().out

    def test_exit_zero_for_repo(self, tmp_path, capsys):
        (tmp_path / ".git").mkdir()
        code, out = self._run(capsys, str(tmp_path))
        assert code == 0
        assert f"ROOT={tmp_path}" in out
        assert "SCOPE=repo" in out

    def test_exit_one_for_none(self, tmp_path, capsys):
        code, out = self._run(capsys, str(tmp_path))
        assert code == 1
        assert "SCOPE=none" in out

    def test_too_many_args(self, capsys):
        code = self.func(["a", "b", "c"])
        assert code == 2

    def test_nonexistent_root(self, capsys):
        code = self.func(["/nonexistent/path/xyz"])
        assert code == 2
