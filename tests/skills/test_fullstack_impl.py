"""Tests for fullstack-impl skill scripts.

Covers pure/deterministic functions from:
- check_github_repos.py — fullstack.json config reading
- iteration_log_check.py — post-finalization iteration log consistency
"""

from __future__ import annotations

import json
import textwrap
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


def _write_work_dir(
    work_dir: Path,
    *,
    progress_text: str | None = None,
    review_text: str | None = None,
) -> None:
    """Helper: create a work directory with given progress/review files."""
    if progress_text is not None:
        (work_dir / "progress.md").write_text(progress_text, encoding="utf-8")
    if review_text is not None:
        (work_dir / "review.md").write_text(review_text, encoding="utf-8")


PROGRESS_HEADER_EN = textwrap.dedent(
    """\
    # Progress: Test

    ## Iteration Log

    | # | Date | Trigger | Repos | Files | Review | analysis.md | plan.md | Commit |
    |---|------|---------|-------|-------|--------|-------------|---------|--------|
    """
)

PROGRESS_HEADER_ZH = textwrap.dedent(
    """\
    # 进度：测试

    ## 迭代记录

    | # | 日期 | 触发 | 仓库 | 文件 | 审查 | analysis.md | plan.md | 提交 |
    |---|------|------|------|------|------|-------------|---------|------|
    """
)

REVIEW_TWO_ROUNDS = textwrap.dedent(
    """\
    # Review: Test

    ## api — Review Round 1 — 2026-04-29
    PASS

    ## web — Review Round 1 — 2026-04-29
    PASS
    """
)

REVIEW_ONE_ROUND = textwrap.dedent(
    """\
    # Review: Test

    ## api — Review Round 1 — 2026-04-29
    PASS
    """
)


class TestFindIterationLogSection:
    """Tests for iteration_log_check.find_iteration_log_section."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from iteration_log_check import find_iteration_log_section
        self.func = find_iteration_log_section

    def test_english_header(self):
        text = "# X\n\n## Iteration Log\n\nbody line\n"
        assert self.func(text) is not None
        assert "body line" in self.func(text)

    def test_chinese_header(self):
        text = "# X\n\n## 迭代记录\n\n中文内容\n"
        assert self.func(text) is not None
        assert "中文内容" in self.func(text)

    def test_no_section_returns_none(self):
        assert self.func("# X\n\n## Other Section\n\nbody\n") is None

    def test_section_stops_at_next_h2(self):
        text = (
            "## Iteration Log\n\nrow content\n\n"
            "## Next Section\n\nshould not include this\n"
        )
        section = self.func(text)
        assert section is not None
        assert "row content" in section
        assert "should not include this" not in section

    def test_section_extends_to_eof_when_no_next_h2(self):
        text = "## Iteration Log\n\nlast line\n"
        section = self.func(text)
        assert section is not None
        assert "last line" in section


class TestParseMarkdownTable:
    """Tests for iteration_log_check.parse_markdown_table."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from iteration_log_check import parse_markdown_table
        self.func = parse_markdown_table

    def test_well_formed_table(self):
        section = textwrap.dedent(
            """\
            | a | b | c |
            |---|---|---|
            | 1 | 2 | 3 |
            | 4 | 5 | 6 |
            """
        )
        header, rows = self.func(section)
        assert header == ["a", "b", "c"]
        assert rows == [["1", "2", "3"], ["4", "5", "6"]]

    def test_no_table_returns_empty(self):
        assert self.func("just some prose\nno table here\n") == ([], [])

    def test_header_only_no_data_rows(self):
        section = "| a | b |\n|---|---|\n"
        header, rows = self.func(section)
        assert header == ["a", "b"]
        assert rows == []

    def test_separator_with_alignment_colons(self):
        section = "| a | b |\n|:--|:-:|\n| 1 | 2 |\n"
        header, rows = self.func(section)
        assert header == ["a", "b"]
        assert rows == [["1", "2"]]

    def test_invalid_separator_returns_empty_rows(self):
        section = "| a | b |\n| not a separator |\n| 1 | 2 |\n"
        header, rows = self.func(section)
        assert header == ["a", "b"]
        assert rows == []

    def test_blank_row_skipped(self):
        section = textwrap.dedent(
            """\
            | a | b |
            |---|---|
            |   |   |
            | 1 | 2 |
            """
        )
        _, rows = self.func(section)
        assert rows == [["1", "2"]]


class TestDetectLanguage:
    """Tests for iteration_log_check.detect_language."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from iteration_log_check import detect_language
        self.func = detect_language

    def test_chinese_header(self):
        assert self.func(["#", "日期", "触发", "仓库", "文件"]) == "zh"

    def test_english_header(self):
        assert self.func(["#", "Date", "Trigger", "Repos", "Files"]) == "en"

    def test_mixed_with_chinese_token_wins(self):
        assert self.func(["#", "Date", "触发", "Repos"]) == "zh"


class TestCountReviewRounds:
    """Tests for iteration_log_check.count_review_rounds."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from iteration_log_check import count_review_rounds
        self.func = count_review_rounds

    def test_english_rounds(self):
        text = (
            "## api — Review Round 1 — 2026-04-29\n\n"
            "## api — Review Round 2 — 2026-04-29\n\n"
            "## web — Review Round 1 — 2026-04-29\n"
        )
        assert self.func(text) == 3

    def test_chinese_rounds(self):
        text = (
            "## api — 第 1 轮审查 — 2026-04-29\n\n"
            "## web — 第 1 轮审查 — 2026-04-29\n"
        )
        assert self.func(text) == 2

    def test_no_rounds(self):
        assert self.func("# Review\n\nNothing here yet.\n") == 0

    def test_ignores_non_round_h2(self):
        text = (
            "## Cross-Repo Consistency Review — 2026-04-29\n\n"
            "## api — Review Round 1 — 2026-04-29\n"
        )
        assert self.func(text) == 1


class TestCheckWorkDirectory:
    """Tests for iteration_log_check.check_work_directory."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from iteration_log_check import check_work_directory
        self.func = check_work_directory

    def test_passes_with_valid_english_log(self, tmp_path: Path):
        progress = PROGRESS_HEADER_EN + (
            "| 1 | 2026-04-29 | bug X | api | api/foo.py "
            "| PASS (round 1) | unchanged | unchanged | api@abc |\n"
            "| 2 | 2026-04-29 | bug Y | web | web/bar.ts "
            "| PASS (round 1) | updated: root cause | unchanged | web@def |\n"
        )
        _write_work_dir(
            tmp_path, progress_text=progress, review_text=REVIEW_TWO_ROUNDS
        )
        result = self.func(tmp_path)
        assert result.status == "PASS"
        assert result.errors == []
        assert len(result.iteration_rows) == 2
        assert result.review_round_count == 2

    def test_passes_with_valid_chinese_log(self, tmp_path: Path):
        progress = PROGRESS_HEADER_ZH + (
            "| 1 | 2026-04-29 | 修复 X | api | api/foo.py "
            "| PASS (round 1) | 未变 | 未变 | api@abc |\n"
        )
        review = "## api — 第 1 轮审查 — 2026-04-29\nPASS\n"
        _write_work_dir(tmp_path, progress_text=progress, review_text=review)
        result = self.func(tmp_path)
        assert result.status == "PASS"

    def test_missing_progress_md(self, tmp_path: Path):
        _write_work_dir(tmp_path, review_text=REVIEW_ONE_ROUND)
        result = self.func(tmp_path)
        assert result.status == "FAIL"
        assert any("progress.md not found" in e for e in result.errors)

    def test_missing_review_md(self, tmp_path: Path):
        _write_work_dir(tmp_path, progress_text=PROGRESS_HEADER_EN)
        result = self.func(tmp_path)
        assert result.status == "FAIL"
        assert any("review.md not found" in e for e in result.errors)

    def test_no_iteration_log_section_is_warning(self, tmp_path: Path):
        progress = "# Progress\n\n## Change Log\n\nstart\n"
        _write_work_dir(
            tmp_path, progress_text=progress, review_text=REVIEW_ONE_ROUND
        )
        result = self.func(tmp_path)
        assert result.status == "WARN"
        assert result.errors == []
        assert any("no '## Iteration Log'" in w for w in result.warnings)

    def test_empty_iteration_log_is_pass(self, tmp_path: Path):
        _write_work_dir(
            tmp_path,
            progress_text=PROGRESS_HEADER_EN,
            review_text=REVIEW_ONE_ROUND,
        )
        result = self.func(tmp_path)
        assert result.status == "PASS"
        assert result.iteration_rows == []

    def test_more_iterations_than_review_rounds_fails(self, tmp_path: Path):
        progress = PROGRESS_HEADER_EN + (
            "| 1 | 2026-04-29 | A | api | f.py "
            "| PASS (1) | unchanged | unchanged | api@a |\n"
            "| 2 | 2026-04-29 | B | api | g.py "
            "| PASS (1) | unchanged | unchanged | api@b |\n"
            "| 3 | 2026-04-29 | C | api | h.py "
            "| PASS (1) | unchanged | unchanged | api@c |\n"
        )
        _write_work_dir(
            tmp_path, progress_text=progress, review_text=REVIEW_TWO_ROUNDS
        )
        result = self.func(tmp_path)
        assert result.status == "FAIL"
        assert any(
            "every iteration MUST have at least one staged-review round"
            in e
            for e in result.errors
        )

    def test_non_sequential_numbers_fails(self, tmp_path: Path):
        progress = PROGRESS_HEADER_EN + (
            "| 1 | 2026-04-29 | A | api | f.py "
            "| PASS (1) | unchanged | unchanged | api@a |\n"
            "| 3 | 2026-04-29 | C | api | h.py "
            "| PASS (1) | unchanged | unchanged | api@c |\n"
        )
        _write_work_dir(
            tmp_path, progress_text=progress, review_text=REVIEW_TWO_ROUNDS
        )
        result = self.func(tmp_path)
        assert result.status == "FAIL"
        assert any(
            "iteration numbers must be sequential" in e
            for e in result.errors
        )

    def test_missing_required_column_fails(self, tmp_path: Path):
        progress = PROGRESS_HEADER_EN + (
            "| 1 | 2026-04-29 | A | api | f.py "
            "| PASS (1) |  | unchanged | api@a |\n"
        )
        _write_work_dir(
            tmp_path, progress_text=progress, review_text=REVIEW_ONE_ROUND
        )
        result = self.func(tmp_path)
        assert result.status == "FAIL"
        assert any(
            "missing required columns: analysis.md" in e
            for e in result.errors
        )

    def test_doc_status_freeform_text_is_warning(self, tmp_path: Path):
        progress = PROGRESS_HEADER_EN + (
            "| 1 | 2026-04-29 | A | api | f.py "
            "| PASS (1) | random text | unchanged | api@a |\n"
        )
        _write_work_dir(
            tmp_path, progress_text=progress, review_text=REVIEW_ONE_ROUND
        )
        result = self.func(tmp_path)
        assert any("random text" in w for w in result.warnings)

    def test_doc_status_updated_with_section_passes(self, tmp_path: Path):
        progress = PROGRESS_HEADER_EN + (
            "| 1 | 2026-04-29 | A | api | f.py "
            "| PASS (1) | updated: Root Cause | unchanged | api@a |\n"
        )
        _write_work_dir(
            tmp_path, progress_text=progress, review_text=REVIEW_ONE_ROUND
        )
        result = self.func(tmp_path)
        assert result.status == "PASS"


class TestFormatResult:
    """Tests for iteration_log_check.format_result output schema."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from iteration_log_check import CheckResult, format_result
        self.cls = CheckResult
        self.func = format_result

    def test_empty_pass(self):
        out = self.func(self.cls())
        assert "STATUS=PASS" in out
        assert "ITERATION_ROWS=0" in out
        assert "REVIEW_ROUNDS=0" in out

    def test_warn_only(self):
        result = self.cls(warnings=["something off"])
        out = self.func(result)
        assert "STATUS=WARN" in out
        assert "WARNING: something off" in out

    def test_fail_with_error(self):
        result = self.cls(errors=["broken"], warnings=["minor"])
        out = self.func(result)
        assert "STATUS=FAIL" in out
        assert "ERROR:   broken" in out
        assert "WARNING: minor" in out
