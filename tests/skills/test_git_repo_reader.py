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


class TestRepoManagerUrlSafety:
    """Regression tests: crafted URLs must never map outside the repo cache."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from repo_manager import parse_repo_url

        self.parse = parse_repo_url

    @pytest.mark.parametrize(
        "url",
        [
            "https://h/../../../../../../Users/someone/project",
            "https://github.com/owner/..",
            "https://github.com/./repo",
            "git@h:../../x/y",
            "git@github.com:owner/../../etc",
            "https://github.com/owner//repo",
            "https://github.com/own\\er/repo",
        ],
    )
    def test_unsafe_segments_rejected(self, url):
        with pytest.raises(ValueError):
            self.parse(url)

    def test_invalid_host_rejected(self):
        with pytest.raises(ValueError, match="Invalid host"):
            self.parse("https://bad_host!/owner/repo")

    def test_credentials_stripped(self):
        host, owner, repo, clone_url = self.parse(
            "https://user:secret@github.com/owner/repo.git"
        )
        assert host == "github.com"
        assert "secret" not in clone_url
        assert clone_url == "https://github.com/owner/repo.git"

    def test_port_kept_in_host_and_clone_url(self):
        host, _, _, clone_url = self.parse("https://git.corp.io:8443/team/svc")
        assert host == "git.corp.io:8443"
        assert clone_url == "https://git.corp.io:8443/team/svc.git"

    def test_github_tree_url_trimmed(self):
        host, owner, repo, clone_url = self.parse(
            "https://github.com/owner/repo/tree/main/src"
        )
        assert (owner, repo) == ("owner", "repo")
        assert clone_url == "https://github.com/owner/repo.git"

    def test_gitlab_blob_url_keeps_subgroups(self):
        _, owner, repo, _ = self.parse(
            "https://gitlab.com/g1/g2/repo/-/blob/main/README.md"
        )
        assert (owner, repo) == ("g1/g2", "repo")

    def test_query_string_dropped(self):
        _, _, repo, _ = self.parse("https://github.com/owner/repo?tab=readme")
        assert repo == "repo"


class TestRepoManagerCachePathGuard:
    """Tests for get_local_path / ensure_within_repos_root / lookup_entry."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        import repo_manager

        self.rm = repo_manager
        self.repos = tmp_path / "cache" / "repos"
        self.map_path = tmp_path / "cache" / "repo_map.json"
        monkeypatch.setattr("repo_manager.get_repos_dir", lambda: self.repos)
        monkeypatch.setattr("repo_manager.get_map_path", lambda: self.map_path)

    def test_local_path_inside_root(self):
        path = self.rm.get_local_path("https://github.com/a/b")
        assert path == (self.repos / "github.com" / "a" / "b").resolve()

    def test_port_colon_replaced_in_path(self):
        path = self.rm.get_local_path("https://git.corp.io:8443/a/b")
        assert "git.corp.io_8443" in path.parts
        assert all(":" not in part for part in path.parts[1:])

    def test_outside_path_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="outside repo cache"):
            self.rm.ensure_within_repos_root(tmp_path / "elsewhere", self.repos)

    def test_root_itself_rejected(self):
        with pytest.raises(ValueError):
            self.rm.ensure_within_repos_root(self.repos, self.repos)

    def test_remove_tree_refuses_outside_path(self, tmp_path):
        victim = tmp_path / "victim"
        victim.mkdir()
        with pytest.raises(ValueError):
            self.rm.remove_tree(victim)
        assert victim.exists()

    def test_lookup_ignores_tampered_entry(self, tmp_path):
        self.rm.save_map({"github.com/a/b": str(tmp_path / "victim")})
        assert self.rm.lookup_entry("https://github.com/a/b") is None

    def test_lookup_returns_entry_inside_cache(self):
        inside = self.repos / "github.com" / "a" / "b"
        self.rm.save_map({"github.com/a/b": str(inside)})
        assert self.rm.lookup_entry("https://github.com/a/b") == inside.resolve()

    def test_save_map_leaves_no_tmp_file(self):
        self.rm.save_map({"k": "v"})
        leftovers = [p.name for p in self.map_path.parent.iterdir()]
        assert leftovers == ["repo_map.json"]


class TestRepoManagerNetworkFailureKeepsCache:
    """Regression: a failed refresh/fetch must not delete the cached clone."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        import repo_manager

        self.rm = repo_manager
        self.repos = tmp_path / "cache" / "repos"
        self.map_path = tmp_path / "cache" / "repo_map.json"
        self.local = self.repos / "github.com" / "a" / "b"
        (self.local / ".git").mkdir(parents=True)
        monkeypatch.setattr("repo_manager.get_repos_dir", lambda: self.repos)
        monkeypatch.setattr("repo_manager.get_map_path", lambda: self.map_path)
        monkeypatch.setattr("repo_manager.is_valid_checkout", lambda _p: True)
        self.rm.save_map({"github.com/a/b": str(self.local)})

        def offline(_path):
            raise RuntimeError("Could not resolve host: github.com")

        def no_clone(*_args, **_kwargs):
            raise AssertionError("must not re-clone on a network failure")

        monkeypatch.setattr("repo_manager.git_refresh", offline)
        monkeypatch.setattr("repo_manager.git_fetch", offline)
        monkeypatch.setattr("repo_manager.git_clone", no_clone)

    def test_clone_uses_stale_copy(self, capsys):
        self.rm.cmd_clone("https://github.com/a/b")
        assert capsys.readouterr().out.strip() == str(self.local.resolve())
        assert self.local.exists()
        assert self.rm.lookup_entry("https://github.com/a/b") is not None

    def test_sync_uses_stale_copy(self, capsys, monkeypatch):
        calls: list[list[str]] = []

        def fake_git(args, cwd=None):
            import subprocess

            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")

        monkeypatch.setattr("repo_manager.run_git", fake_git)
        monkeypatch.setattr("repo_manager.git_get_default_branch", lambda _p: "main")
        self.rm.cmd_sync("https://github.com/a/b")
        assert capsys.readouterr().out.strip() == str(self.local.resolve())
        assert self.local.exists()
        assert ["reset", "--hard", "origin/main"] in calls

    def test_sync_reports_failed_reset(self, monkeypatch):
        import subprocess

        def failing_git(args, cwd=None):
            return subprocess.CompletedProcess(args, 1, "", "boom")

        monkeypatch.setattr("repo_manager.run_git", failing_git)
        monkeypatch.setattr("repo_manager.git_get_default_branch", lambda _p: "main")
        with pytest.raises(RuntimeError, match="boom"):
            self.rm.cmd_sync("https://github.com/a/b")
