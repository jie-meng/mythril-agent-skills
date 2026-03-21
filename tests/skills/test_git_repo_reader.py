"""Tests for git-repo-reader skill scripts.

Covers pure functions in repo_manager.py:
- parse_repo_url: URL → (host, owner, repo, clone_url)
- normalize_key: URL → cache key string
- get_local_path: URL → deterministic local path
- load_map / save_map: JSON round-trip with tmp files
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestRepoManagerParseUrl:
    """Tests for repo_manager.parse_repo_url (git-repo-reader version)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from repo_manager import parse_repo_url
        self.parse = parse_repo_url

    def test_https_github(self):
        host, owner, repo, clone_url = self.parse("https://github.com/owner/repo")
        assert host == "github.com"
        assert owner == "owner"
        assert repo == "repo"
        assert clone_url == "https://github.com/owner/repo.git"

    def test_https_with_dot_git(self):
        host, owner, repo, clone_url = self.parse("https://github.com/a/b.git")
        assert repo == "b"
        assert clone_url == "https://github.com/a/b.git"

    def test_https_trailing_slash(self):
        host, owner, repo, _ = self.parse("https://github.com/a/b/")
        assert repo == "b"

    def test_ssh_url(self):
        host, owner, repo, clone_url = self.parse("git@github.com:owner/repo.git")
        assert host == "github.com"
        assert owner == "owner"
        assert repo == "repo"
        assert clone_url == "git@github.com:owner/repo.git"

    def test_enterprise_https(self):
        host, owner, repo, _ = self.parse("https://git.corp.io/team/service")
        assert host == "git.corp.io"
        assert owner == "team"
        assert repo == "service"

    def test_nested_groups(self):
        host, owner, repo, _ = self.parse("https://gitlab.com/g1/g2/repo")
        assert owner == "g1/g2"
        assert repo == "repo"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Unrecognized"):
            self.parse("not-a-url")

    def test_too_few_path_parts_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            self.parse("https://github.com/onlyowner")


class TestRepoManagerNormalizeKey:
    """Tests for repo_manager.normalize_key."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from repo_manager import normalize_key
        self.normalize = normalize_key

    def test_https(self):
        assert self.normalize("https://github.com/a/b") == "github.com/a/b"

    def test_ssh(self):
        assert self.normalize("git@github.com:a/b.git") == "github.com/a/b"

    def test_same_key_for_same_repo(self):
        k1 = self.normalize("https://github.com/owner/repo.git")
        k2 = self.normalize("git@github.com:owner/repo.git")
        assert k1 == k2


class TestRepoManagerMapRoundTrip:
    """Tests for load_map / save_map with temporary files."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from repo_manager import load_map, save_map, get_map_path
        self.load_map = load_map
        self.save_map = save_map
        self.get_map_path = get_map_path

    def test_load_missing_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "repo_manager.get_map_path",
            lambda: tmp_path / "nonexistent" / "repo_map.json",
        )
        assert self.load_map() == {}

    def test_save_and_load(self, tmp_path, monkeypatch):
        map_path = tmp_path / "repo_map.json"
        monkeypatch.setattr("repo_manager.get_map_path", lambda: map_path)

        data = {"github.com/a/b": "/cache/repos/github.com/a/b"}
        self.save_map(data)
        loaded = self.load_map()
        assert loaded == data

    def test_load_corrupt_json_returns_empty(self, tmp_path, monkeypatch):
        map_path = tmp_path / "repo_map.json"
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text("not valid json{{{", encoding="utf-8")
        monkeypatch.setattr("repo_manager.get_map_path", lambda: map_path)
        assert self.load_map() == {}
