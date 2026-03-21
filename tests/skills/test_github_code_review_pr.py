"""Tests for github-code-review-pr skill scripts.

Covers pure/deterministic functions that require no network, git, or API calls:
- review_runner: URL parsing, key-value output parsing, manifest dataclass
- review_output_gate: speculation detection, verdict parsing, gate logic
- review_template_builder: template rendering (English + Chinese)
- path_select: URL parsing, normalized identity
- repo_cache_lookup: URL parsing, normalize_key
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest


# ── review_runner ──────────────────────────────────────────────────────────────


class TestReviewRunnerParsePrRepoUrl:
    """Tests for review_runner.parse_pr_repo_url."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from review_runner import parse_pr_repo_url
        self.parse = parse_pr_repo_url

    def test_github_com_url(self):
        url = "https://github.com/owner/repo/pull/42"
        repo_url, host, owner, repo = self.parse(url)
        assert repo_url == "https://github.com/owner/repo"
        assert host == "github.com"
        assert owner == "owner"
        assert repo == "repo"

    def test_github_enterprise_url(self):
        url = "https://git.company.com/org/project/pull/123"
        repo_url, host, owner, repo = self.parse(url)
        assert repo_url == "https://git.company.com/org/project"
        assert host == "git.company.com"
        assert owner == "org"
        assert repo == "project"

    def test_nested_owner_path(self):
        url = "https://gitlab.example.com/group/subgroup/repo/pull/99"
        repo_url, host, owner, repo = self.parse(url)
        assert owner == "group/subgroup"
        assert repo == "repo"

    def test_trailing_path_segments(self):
        url = "https://github.com/owner/repo/pull/7/files"
        repo_url, host, owner, repo = self.parse(url)
        assert host == "github.com"
        assert owner == "owner"
        assert repo == "repo"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            self.parse("not-a-url")

    def test_missing_pull_segment_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            self.parse("https://github.com/owner/repo/issues/42")


class TestReviewRunnerParseKeyValueOutput:
    """Tests for review_runner.parse_key_value_output."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from review_runner import parse_key_value_output
        self.parse = parse_key_value_output

    def test_basic_parsing(self):
        text = "SELECTED_PATH=A\nREPO_PATH=/tmp/foo\n"
        result = self.parse(text)
        assert result["SELECTED_PATH"] == "A"
        assert result["REPO_PATH"] == "/tmp/foo"

    def test_ignores_non_kv_lines(self):
        text = "[PATH-CHECK] A: HIT\nSELECTED_PATH=B\nsome random text\n"
        result = self.parse(text)
        assert result == {"SELECTED_PATH": "B"}

    def test_empty_value(self):
        text = "REPO_PATH=\n"
        result = self.parse(text)
        assert result["REPO_PATH"] == ""

    def test_empty_input(self):
        assert self.parse("") == {}

    def test_value_with_equals_sign(self):
        text = "CONTEXT_LIMITATION=error=timeout at step 3\n"
        result = self.parse(text)
        assert result["CONTEXT_LIMITATION"] == "error=timeout at step 3"


# ── review_output_gate ─────────────────────────────────────────────────────────


class TestGateNoSpeculation:
    """Tests for review_output_gate.gate_no_speculation."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from review_output_gate import gate_no_speculation
        self.gate = gate_no_speculation

    def test_clean_text_passes(self):
        r = self.gate("This PR modifies the login flow. Approve.")
        assert r.passed is True

    def test_forbidden_phrase_fails(self):
        r = self.gate("This looks like GitLab based on the domain.")
        assert r.passed is False
        assert "looks like gitlab" in r.detail

    def test_not_a_github_url_fails(self):
        r = self.gate("This is not a GitHub URL, so we can't proceed.")
        assert r.passed is False

    def test_case_insensitive(self):
        r = self.gate("Possibly GITLAB instance detected.")
        assert r.passed is False


class TestGateSingleFetch:
    """Tests for review_output_gate.gate_single_fetch."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from review_output_gate import gate_single_fetch
        self.gate = gate_single_fetch

    def _entry(self, cmd: list[str]) -> dict:
        return {"cmd": cmd, "cwd": "", "ts_utc": "2025-01-01T00:00:00Z"}

    def test_exactly_once_passes(self):
        entries = [
            self._entry(["gh", "pr", "view", "https://x/pull/1", "--json", "url"]),
            self._entry(["gh", "pr", "diff", "https://x/pull/1"]),
            self._entry(["git", "fetch", "origin", "main"]),
        ]
        r = self.gate(entries)
        assert r.passed is True

    def test_duplicate_view_fails(self):
        entries = [
            self._entry(["gh", "pr", "view", "url1", "--json", "x"]),
            self._entry(["gh", "pr", "view", "url1", "--json", "x"]),
            self._entry(["gh", "pr", "diff", "url1"]),
        ]
        r = self.gate(entries)
        assert r.passed is False
        assert "view count=2" in r.detail

    def test_missing_diff_fails(self):
        entries = [
            self._entry(["gh", "pr", "view", "url1", "--json", "x"]),
        ]
        r = self.gate(entries)
        assert r.passed is False
        assert "diff count=0" in r.detail

    def test_empty_log_fails(self):
        r = self.gate([])
        assert r.passed is False


class TestGateCleanupEvidence:
    """Tests for review_output_gate.gate_cleanup_evidence."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from review_output_gate import gate_cleanup_evidence
        self.gate = gate_cleanup_evidence

    def test_marker_present_passes(self):
        r = self.gate("[PATH-CLEANUP] Path B - reset cached repo to main")
        assert r.passed is True

    def test_marker_missing_fails(self):
        r = self.gate("Cleanup completed successfully.")
        assert r.passed is False


class TestDetectVerdict:
    """Tests for review_output_gate.detect_verdict."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from review_output_gate import detect_verdict
        self.detect = detect_verdict

    def test_approve(self):
        text = "## 6. Summary Verdict\n- Verdict: Approve\n- Rationale: looks good"
        assert self.detect(text) == "APPROVE"

    def test_request_changes(self):
        text = "## Summary\n- Verdict: Request Changes\n- Major issues found"
        assert self.detect(text) == "REQUEST_CHANGES"

    def test_comment_verdict(self):
        text = "## Summary Verdict\n- Overall assessment: Comment\n- Minor suggestions"
        assert self.detect(text) == "COMMENT"

    def test_no_verdict_returns_unknown(self):
        text = "This is a plain review with no verdict keyword at all."
        assert self.detect(text) == "UNKNOWN"


class TestGateVerdictState:
    """Tests for review_output_gate.gate_verdict_state."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from review_output_gate import gate_verdict_state
        self.gate = gate_verdict_state

    def test_open_pr_approve_passes(self):
        r = self.gate("OPEN", "APPROVE", False)
        assert r.passed is True

    def test_merged_pr_request_changes_fails(self):
        r = self.gate("MERGED", "REQUEST_CHANGES", False)
        assert r.passed is False

    def test_merged_pr_request_changes_allowed(self):
        r = self.gate("MERGED", "REQUEST_CHANGES", True)
        assert r.passed is True

    def test_merged_pr_comment_passes(self):
        r = self.gate("MERGED", "COMMENT", False)
        assert r.passed is True

    def test_unknown_verdict_fails(self):
        r = self.gate("OPEN", "UNKNOWN", False)
        assert r.passed is False

    def test_ambiguous_verdict_fails(self):
        r = self.gate("OPEN", "AMBIGUOUS", False)
        assert r.passed is False


# ── review_template_builder ────────────────────────────────────────────────────


class TestReviewTemplateBuilder:
    """Tests for review_template_builder render functions."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from review_template_builder import render_english, render_chinese
        self.render_en = render_english
        self.render_zh = render_chinese

    def _manifest(self, **overrides) -> dict:
        base = {
            "pr_number": 42,
            "pr_url": "https://github.com/owner/repo/pull/42",
            "pr_state": "OPEN",
            "context_mode": "full_repo",
            "context_limitation": "",
        }
        base.update(overrides)
        return base

    def test_english_contains_all_sections(self):
        text = self.render_en(self._manifest())
        assert "1. PR Overview" in text
        assert "2. Repository Context Analysis" in text
        assert "3. Code Quality" in text
        assert "4. Major Issues" in text
        assert "5. Incremental Suggestions" in text
        assert "6. Summary Verdict" in text

    def test_english_default_verdict_approve_for_open(self):
        text = self.render_en(self._manifest(pr_state="OPEN"))
        assert "Verdict: Approve" in text

    def test_english_default_verdict_comment_for_merged(self):
        text = self.render_en(self._manifest(pr_state="MERGED"))
        assert "Verdict: Comment" in text

    def test_english_diff_only_shows_limitation(self):
        text = self.render_en(self._manifest(
            context_mode="diff_only",
            context_limitation="User chose diff-only",
        ))
        assert "diff-only" in text
        assert "User chose diff-only" in text

    def test_chinese_contains_all_sections(self):
        text = self.render_zh(self._manifest())
        assert "1. PR 概览" in text
        assert "2. 仓库上下文分析" in text
        assert "3. 代码质量" in text
        assert "4. 潜在的重大问题和风险" in text
        assert "5. 增量建议" in text
        assert "6. 总结评价" in text

    def test_chinese_includes_pr_number(self):
        text = self.render_zh(self._manifest(pr_number=99))
        assert "#99" in text


# ── path_select helpers ────────────────────────────────────────────────────────


class TestPathSelectParseRepoUrl:
    """Tests for path_select.parse_repo_url."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from path_select import parse_repo_url, normalized_identity
        self.parse = parse_repo_url
        self.normalize = normalized_identity

    def test_https_url(self):
        host, owner, repo = self.parse("https://github.com/owner/repo")
        assert (host, owner, repo) == ("github.com", "owner", "repo")

    def test_https_with_git_suffix(self):
        host, owner, repo = self.parse("https://github.com/owner/repo.git")
        assert repo == "repo"

    def test_ssh_url(self):
        host, owner, repo = self.parse("git@github.com:owner/repo.git")
        assert (host, owner, repo) == ("github.com", "owner", "repo")

    def test_ssh_url_protocol(self):
        host, owner, repo = self.parse("ssh://git@github.com/owner/repo.git")
        assert (host, owner, repo) == ("github.com", "owner", "repo")

    def test_enterprise_url(self):
        host, owner, repo = self.parse("https://git.corp.com/team/project")
        assert host == "git.corp.com"
        assert owner == "team"
        assert repo == "project"

    def test_nested_groups(self):
        host, owner, repo = self.parse("https://gitlab.com/group/sub/repo")
        assert owner == "group/sub"
        assert repo == "repo"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            self.parse("not-a-url")

    def test_normalized_identity_case_insensitive(self):
        a = self.normalize("GitHub.COM", "Owner", "Repo")
        b = self.normalize("github.com", "owner", "repo")
        assert a == b


# ── repo_cache_lookup ──────────────────────────────────────────────────────────


class TestRepoCacheLookup:
    """Tests for repo_cache_lookup URL parsing."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from repo_cache_lookup import parse_repo_url, normalize_key
        self.parse = parse_repo_url
        self.normalize = normalize_key

    def test_https_parse(self):
        host, owner, repo = self.parse("https://github.com/owner/repo")
        assert (host, owner, repo) == ("github.com", "owner", "repo")

    def test_ssh_parse(self):
        host, owner, repo = self.parse("git@github.com:org/project.git")
        assert (host, owner, repo) == ("github.com", "org", "project")

    def test_normalize_key(self):
        key = self.normalize("https://github.com/owner/repo.git")
        assert key == "github.com/owner/repo"

    def test_normalize_key_ssh(self):
        key = self.normalize("git@github.com:owner/repo.git")
        assert key == "github.com/owner/repo"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            self.parse("ftp://example.com/foo")
