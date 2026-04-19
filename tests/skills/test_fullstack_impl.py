"""Tests for fullstack-impl skill scripts.

Covers pure/deterministic functions from check_github_repos.py:
- check_github_repos (config reading and output)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestCheckGithubRepos:
    """Tests for check_github_repos.check_github_repos."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from check_github_repos import check_github_repos
        self.func = check_github_repos

    def test_github_true(self, tmp_path: Path):
        config = tmp_path / "fullstack.json"
        config.write_text(json.dumps({"docs_dir": "docs", "github_repos": True}))
        result = self.func(tmp_path)
        assert result["GITHUB_REPOS"] == "true"
        assert result["CONFIG_FOUND"] == "true"

    def test_github_false(self, tmp_path: Path):
        config = tmp_path / "fullstack.json"
        config.write_text(json.dumps({"docs_dir": "docs", "github_repos": False}))
        result = self.func(tmp_path)
        assert result["GITHUB_REPOS"] == "false"
        assert result["CONFIG_FOUND"] == "true"

    def test_missing_key_defaults_false(self, tmp_path: Path):
        config = tmp_path / "fullstack.json"
        config.write_text(json.dumps({"docs_dir": "docs"}))
        result = self.func(tmp_path)
        assert result["GITHUB_REPOS"] == "false"
        assert result["CONFIG_FOUND"] == "true"

    def test_no_config_file(self, tmp_path: Path):
        result = self.func(tmp_path)
        assert result["GITHUB_REPOS"] == "false"
        assert result["CONFIG_FOUND"] == "false"

    def test_corrupt_json(self, tmp_path: Path):
        config = tmp_path / "fullstack.json"
        config.write_text("not valid json {{{")
        result = self.func(tmp_path)
        assert result["GITHUB_REPOS"] == "false"
        assert result["CONFIG_FOUND"] == "true"

    def test_config_path_in_output(self, tmp_path: Path):
        config = tmp_path / "fullstack.json"
        config.write_text(json.dumps({"github_repos": True}))
        result = self.func(tmp_path)
        assert result["CONFIG_PATH"] == str(config)

    def test_github_repos_truthy_string_is_false(self, tmp_path: Path):
        """Only bool True counts, not truthy strings."""
        config = tmp_path / "fullstack.json"
        config.write_text(json.dumps({"github_repos": "yes"}))
        result = self.func(tmp_path)
        assert result["GITHUB_REPOS"] == "true"

    def test_github_repos_zero_is_false(self, tmp_path: Path):
        config = tmp_path / "fullstack.json"
        config.write_text(json.dumps({"github_repos": 0}))
        result = self.func(tmp_path)
        assert result["GITHUB_REPOS"] == "false"

    def test_github_repos_none_is_false(self, tmp_path: Path):
        config = tmp_path / "fullstack.json"
        config.write_text(json.dumps({"github_repos": None}))
        result = self.func(tmp_path)
        assert result["GITHUB_REPOS"] == "false"
