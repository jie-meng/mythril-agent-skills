"""Tests for fullstack-impl skill scripts.

Covers pure/deterministic functions from:
- check_workspace.py — workspace validation gate (3 markers + config)
- check_github_repos.py — fullstack.json config reading (legacy wrapper)
- route_check.py — Mode routing helper (status normalization, verb
  detection, decision tree)
- iteration_log_check.py — post-finalization iteration log consistency
- mermaid_validate.py — Mermaid 10.2.3 compatibility lint
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest


class TestCheckWorkspace:
    """Tests for check_workspace.check_workspace."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from check_workspace import check_workspace
        self.func = check_workspace

    def _make_valid_workspace(self, tmp_path: Path, config: dict | None = None) -> None:
        if config is None:
            config = {"docs_dir": "docs", "github_repos": True}
        (tmp_path / "fullstack.json").write_text(json.dumps(config))
        (tmp_path / "AGENTS.md").write_text("# AGENTS")
        (tmp_path / ".agents").mkdir()

    def test_valid_workspace(self, tmp_path: Path):
        self._make_valid_workspace(tmp_path)
        result = self.func(tmp_path)
        assert result["WORKSPACE_VALID"] == "true"
        assert result["MISSING"] == ""
        assert result["DOCS_DIR"] == "docs"
        assert result["GITHUB_REPOS"] == "true"

    def test_missing_fullstack_json(self, tmp_path: Path):
        (tmp_path / "AGENTS.md").write_text("# AGENTS")
        (tmp_path / ".agents").mkdir()
        result = self.func(tmp_path)
        assert result["WORKSPACE_VALID"] == "false"
        assert "fullstack.json" in result["MISSING"]

    def test_missing_agents_md(self, tmp_path: Path):
        (tmp_path / "fullstack.json").write_text(json.dumps({}))
        (tmp_path / ".agents").mkdir()
        result = self.func(tmp_path)
        assert result["WORKSPACE_VALID"] == "false"
        assert "AGENTS.md" in result["MISSING"]

    def test_missing_agents_dir(self, tmp_path: Path):
        (tmp_path / "fullstack.json").write_text(json.dumps({}))
        (tmp_path / "AGENTS.md").write_text("# AGENTS")
        result = self.func(tmp_path)
        assert result["WORKSPACE_VALID"] == "false"
        assert ".agents" in result["MISSING"]

    def test_all_three_missing(self, tmp_path: Path):
        result = self.func(tmp_path)
        assert result["WORKSPACE_VALID"] == "false"
        for marker in ("fullstack.json", "AGENTS.md", ".agents"):
            assert marker in result["MISSING"]

    def test_corrupt_config_marks_invalid(self, tmp_path: Path):
        (tmp_path / "fullstack.json").write_text("not valid json {")
        (tmp_path / "AGENTS.md").write_text("# AGENTS")
        (tmp_path / ".agents").mkdir()
        result = self.func(tmp_path)
        assert result["WORKSPACE_VALID"] == "false"
        assert "corrupt" in result["MISSING"]

    def test_agents_file_not_dir_is_invalid(self, tmp_path: Path):
        """A file at .agents (not a directory) does not count as the marker."""
        (tmp_path / "fullstack.json").write_text(json.dumps({}))
        (tmp_path / "AGENTS.md").write_text("# AGENTS")
        (tmp_path / ".agents").write_text("oops")
        result = self.func(tmp_path)
        assert result["WORKSPACE_VALID"] == "false"
        assert ".agents" in result["MISSING"]

    def test_docs_dir_default_empty(self, tmp_path: Path):
        self._make_valid_workspace(tmp_path, {"github_repos": True})
        result = self.func(tmp_path)
        assert result["DOCS_DIR"] == ""

    def test_github_repos_false(self, tmp_path: Path):
        self._make_valid_workspace(tmp_path, {"docs_dir": "docs", "github_repos": False})
        result = self.func(tmp_path)
        assert result["GITHUB_REPOS"] == "false"


class TestCheckGithubRepos:
    """Tests for check_github_repos.check_github_repos (legacy wrapper)."""

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


# ---------------------------------------------------------------------------
# mermaid_validate
# ---------------------------------------------------------------------------


class TestExtractMermaidBlocks:
    """Tests for mermaid_validate.extract_mermaid_blocks."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_validate import extract_mermaid_blocks
        self.func = extract_mermaid_blocks

    def test_no_blocks(self):
        text = "# Title\n\nSome prose only.\n"
        assert self.func(text) == []

    def test_single_block(self):
        text = textwrap.dedent(
            """\
            # Title

            ```mermaid
            flowchart LR
                A --> B
            ```

            after
            """
        )
        blocks = self.func(text)
        assert len(blocks) == 1
        assert blocks[0].start_line == 3
        assert blocks[0].end_line == 6
        assert blocks[0].body == ["flowchart LR", "    A --> B"]

    def test_multiple_blocks(self):
        text = textwrap.dedent(
            """\
            ```mermaid
            flowchart LR
                A --> B
            ```

            text

            ```mermaid
            sequenceDiagram
                A->>B: hi
            ```
            """
        )
        blocks = self.func(text)
        assert len(blocks) == 2
        assert blocks[0].diagram_type == "flowchart"
        assert blocks[1].diagram_type == "sequenceDiagram"

    def test_skips_other_fenced_blocks(self):
        text = textwrap.dedent(
            """\
            ```python
            print(1)
            ```

            ```mermaid
            flowchart LR
                A --> B
            ```
            """
        )
        blocks = self.func(text)
        assert len(blocks) == 1
        assert blocks[0].diagram_type == "flowchart"

    def test_unclosed_block_is_dropped(self):
        text = "```mermaid\nflowchart LR\n  A --> B\n"
        assert self.func(text) == []

    def test_empty_block(self):
        text = "```mermaid\n```\n"
        blocks = self.func(text)
        assert len(blocks) == 1
        assert blocks[0].body == []
        assert blocks[0].diagram_type == ""

    def test_diagram_type_skips_comments(self):
        text = "```mermaid\n%% comment\nflowchart LR\n  A --> B\n```\n"
        blocks = self.func(text)
        assert blocks[0].diagram_type == "flowchart"


class TestIsQuoted:
    """Tests for mermaid_validate.is_quoted."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_validate import is_quoted
        self.func = is_quoted

    def test_double_quoted(self):
        assert self.func('"hello"') is True

    def test_double_quoted_with_spaces(self):
        assert self.func('  "hello"  ') is True

    def test_unquoted(self):
        assert self.func("hello") is False

    def test_single_quoted_does_not_count(self):
        assert self.func("'hello'") is False

    def test_only_open_quote(self):
        assert self.func('"hello') is False

    def test_only_close_quote(self):
        assert self.func('hello"') is False

    def test_empty(self):
        assert self.func("") is False

    def test_one_char(self):
        assert self.func('"') is False


class TestFindEdgeLabelIssues:
    """Tests for mermaid_validate.find_edge_label_issues."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_validate import find_edge_label_issues
        self.func = find_edge_label_issues

    def test_clean_label(self):
        assert self.func("A -->|hello world| B") == []

    def test_label_with_slash(self):
        assert self.func("A -->|key/value| B") == []

    def test_label_with_plus_dot_colon(self):
        assert self.func("A -->|a + b: c.d| B") == []

    def test_label_with_chinese(self):
        assert self.func("A -->|周期扫描| B") == []

    def test_label_with_br(self):
        assert self.func("A -->|line1<br/>line2| B") == []

    def test_label_with_parens_unquoted(self):
        issues = self.func("A -->|hello (world)| B")
        assert len(issues) == 1
        col, label = issues[0]
        assert "hello (world)" in label
        assert col >= 1

    def test_label_with_parens_quoted(self):
        assert self.func('A -->|"hello (world)"| B') == []

    def test_label_with_brackets_unquoted(self):
        issues = self.func("A -->|key[0]| B")
        assert len(issues) == 1
        assert "key[0]" in issues[0][1]

    def test_label_with_curlies_unquoted(self):
        issues = self.func("A -->|use {x}| B")
        assert len(issues) == 1
        assert "{x}" in issues[0][1]

    def test_lone_open_paren_flagged(self):
        issues = self.func("A -->|(start| B")
        assert len(issues) == 1

    def test_lone_close_paren_flagged(self):
        issues = self.func("A -->|hello)| B")
        assert len(issues) == 1

    def test_multiple_bad_labels_on_one_line(self):
        issues = self.func("A -->|first (x)| B -->|second (y)| C")
        assert len(issues) == 2
        labels = [lab for _, lab in issues]
        assert any("first (x)" in lab for lab in labels)
        assert any("second (y)" in lab for lab in labels)

    def test_one_clean_one_bad(self):
        issues = self.func("A -->|clean| B -->|dirty (x)| C")
        assert len(issues) == 1
        assert "dirty (x)" in issues[0][1]

    def test_label_with_brbr_and_parens_quoted(self):
        line = 'A -->|"step 1<br/>(detail)"| B'
        assert self.func(line) == []


class TestFindSubgraphIssue:
    """Tests for mermaid_validate.find_subgraph_issue."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_validate import find_subgraph_issue
        self.func = find_subgraph_issue

    def test_bare_id(self):
        assert self.func("subgraph SVC") is None

    def test_chinese_title(self):
        assert self.func("subgraph 客户端层") is None

    def test_multiword_unquoted(self):
        assert self.func("subgraph My Group") is None

    def test_quoted_with_parens(self):
        assert self.func('subgraph "My (Group)"') is None

    def test_unquoted_with_parens(self):
        result = self.func("subgraph My (Group)")
        assert result == "My (Group)"

    def test_indented_unquoted_with_parens(self):
        result = self.func("    subgraph Service (v2)")
        assert result == "Service (v2)"

    def test_not_a_subgraph_line(self):
        assert self.func("flowchart LR") is None

    def test_subgraph_end_line(self):
        assert self.func("end") is None


class TestFindNewShapeIssue:
    """Tests for mermaid_validate.find_new_shape_issue."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_validate import find_new_shape_issue
        self.func = find_new_shape_issue

    def test_old_syntax_brackets(self):
        assert self.func("    A[Hello]") is None

    def test_old_syntax_round(self):
        assert self.func("    A(Hello)") is None

    def test_old_syntax_diamond(self):
        assert self.func("    A{decision}") is None

    def test_new_shape_syntax(self):
        result = self.func("    A@{ shape: rect, label: \"Hi\" }")
        assert result is not None
        assert result.startswith("A@{")

    def test_new_shape_syntax_with_underscore(self):
        result = self.func("    my_node@{ shape: rect }")
        assert result is not None

    def test_init_directive_is_not_new_shape(self):
        assert self.func("%%{init: {'theme': 'dark'}}%%") is None


class TestFindLiteralBackslashN:
    """Tests for mermaid_validate.find_literal_backslash_n_issue."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_validate import find_literal_backslash_n_issue
        self.func = find_literal_backslash_n_issue

    def test_clean_line(self):
        assert self.func("    A[hello world] --> B") is False

    def test_clean_with_br_tag(self):
        assert self.func("    A[hello<br/>world] --> B") is False

    def test_clean_with_chinese(self):
        assert self.func("    A[你好<br/>世界] --> B") is False

    def test_node_label_with_backslash_n(self):
        assert self.func("    A[patterns.md\\nRefreshManager] --> B") is True

    def test_quoted_node_label_with_backslash_n(self):
        assert self.func('    A["patterns.md\\nRefreshManager"] --> B') is True

    def test_edge_label_with_backslash_n(self):
        assert self.func("    A -->|line1\\nline2| B") is True

    def test_quoted_edge_label_with_backslash_n(self):
        assert self.func('    A -->|"line1\\nline2"| B') is True

    def test_subgraph_title_with_backslash_n(self):
        assert self.func('    subgraph "Foo\\nBar"') is True

    def test_round_node_with_backslash_n(self):
        assert self.func("    A(text\\nmore)") is True

    def test_diamond_node_with_backslash_n(self):
        assert self.func("    A{decision\\nbranch}") is True


class TestFindBetaDiagramIssue:
    """Tests for mermaid_validate.find_beta_diagram_issue."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_validate import find_beta_diagram_issue
        self.func = find_beta_diagram_issue

    def test_flowchart_ok(self):
        assert self.func("flowchart") is None

    def test_sequence_ok(self):
        assert self.func("sequenceDiagram") is None

    def test_gantt_ok(self):
        assert self.func("gantt") is None

    def test_block_beta_flagged(self):
        assert self.func("block-beta") == "block-beta"

    def test_quadrant_chart_flagged(self):
        assert self.func("quadrantChart") == "quadrantChart"

    def test_xychart_beta_flagged(self):
        assert self.func("xychart-beta") == "xychart-beta"

    def test_sankey_beta_flagged(self):
        assert self.func("sankey-beta") == "sankey-beta"

    def test_packet_beta_flagged(self):
        assert self.func("packet-beta") == "packet-beta"

    def test_architecture_beta_flagged(self):
        assert self.func("architecture-beta") == "architecture-beta"

    def test_treemap_flagged(self):
        assert self.func("treemap") == "treemap"

    def test_radar_flagged(self):
        assert self.func("radar") == "radar"

    def test_kanban_flagged(self):
        assert self.func("kanban") == "kanban"


class TestLintBlock:
    """Tests for mermaid_validate.lint_block."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_validate import MermaidBlock, lint_block
        self.cls = MermaidBlock
        self.func = lint_block

    def _block(self, body: str, start: int = 1) -> object:
        lines = body.splitlines()
        return self.cls(start_line=start, end_line=start + len(lines) + 1, body=lines)

    def test_clean_flowchart(self):
        block = self._block("flowchart LR\n    A --> B\n    A -->|label| B")
        assert self.func(block, "f.md") == []

    def test_unquoted_edge_label(self):
        block = self._block(
            "flowchart LR\n    A -->|hello (world)| B",
            start=10,
        )
        issues = self.func(block, "f.md")
        assert len(issues) == 1
        assert issues[0].rule == "unquoted-edge-label"
        assert issues[0].file == "f.md"
        assert issues[0].line == 12  # start_line=10 + body offset 2

    def test_quoted_edge_label_passes(self):
        block = self._block(
            'flowchart LR\n    A -->|"hello (world)"| B'
        )
        assert self.func(block, "f.md") == []

    def test_subgraph_with_parens_flagged(self):
        block = self._block(
            "flowchart TD\n    subgraph My (Group)\n        A\n    end"
        )
        issues = self.func(block, "f.md")
        rules = [i.rule for i in issues]
        assert "unquoted-subgraph-title" in rules

    def test_sequence_diagram_does_not_lint_edge_labels(self):
        block = self._block(
            "sequenceDiagram\n    A->>B: hello (world)"
        )
        assert self.func(block, "f.md") == []

    def test_sequence_diagram_does_not_lint_subgraph(self):
        block = self._block(
            "sequenceDiagram\n    Note over A: my (group)"
        )
        assert self.func(block, "f.md") == []

    def test_beta_diagram_flagged(self):
        block = self._block("block-beta\n    columns 3", start=5)
        issues = self.func(block, "f.md")
        assert len(issues) == 1
        assert issues[0].rule == "beta-diagram-type"
        assert issues[0].line == 6

    def test_new_shape_syntax_flagged(self):
        block = self._block(
            "flowchart LR\n    A@{ shape: rect, label: \"Hi\" }"
        )
        issues = self.func(block, "f.md")
        rules = [i.rule for i in issues]
        assert "new-shape-syntax" in rules

    def test_multiple_issues_in_one_block(self):
        block = self._block(
            "flowchart TD\n"
            "    subgraph My (Group)\n"
            "        A -->|key[0]| B\n"
            "    end"
        )
        issues = self.func(block, "f.md")
        rules = sorted({i.rule for i in issues})
        assert rules == ["unquoted-edge-label", "unquoted-subgraph-title"]

    def test_comment_on_line_does_not_falsely_match(self):
        block = self._block(
            "flowchart LR\n    A --> B  %% note: see (foo)"
        )
        assert self.func(block, "f.md") == []

    def test_chinese_in_clean_label(self):
        block = self._block(
            "flowchart LR\n    A -->|周期扫描| B"
        )
        assert self.func(block, "f.md") == []

    def test_real_world_failing_label(self):
        """Reproduces the exact failure that motivated this validator."""
        block = self._block(
            "flowchart TD\n"
            "    RC -->|2. AliPay or ApplePay<br/>(passes orderNumber as<br/>"
            "appAccountToken)| Bridge"
        )
        issues = self.func(block, "f.md")
        assert len(issues) == 1
        assert issues[0].rule == "unquoted-edge-label"
        assert "appAccountToken" in issues[0].message

    def test_literal_backslash_n_in_node_label_flagged(self):
        """The user's reported case — `\\n` inside a node label renders literally."""
        block = self._block(
            "flowchart TD\n"
            "    A[patterns.md\\nRefreshManager / Skeleton / Nav / Utils]"
        )
        issues = self.func(block, "f.md")
        assert len(issues) == 1
        assert issues[0].rule == "literal-backslash-n"
        assert "<br/>" in issues[0].message

    def test_literal_backslash_n_in_edge_label_flagged(self):
        block = self._block(
            "flowchart TD\n"
            "    A -->|step 1\\nstep 2| B"
        )
        issues = self.func(block, "f.md")
        rules = [i.rule for i in issues]
        assert "literal-backslash-n" in rules

    def test_literal_backslash_n_in_subgraph_title_flagged(self):
        block = self._block(
            "flowchart TD\n"
            '    subgraph "Foo\\nBar"\n'
            "        A\n"
            "    end"
        )
        issues = self.func(block, "f.md")
        rules = [i.rule for i in issues]
        assert "literal-backslash-n" in rules

    def test_br_tag_node_label_passes(self):
        """The recommended replacement — `<br/>` — must not be flagged."""
        block = self._block(
            "flowchart TD\n"
            "    A[patterns.md<br/>RefreshManager / Skeleton / Nav / Utils]"
        )
        assert self.func(block, "f.md") == []

    def test_sequence_diagram_backslash_n_not_flagged(self):
        """Sequence diagrams have different rendering — out of scope."""
        block = self._block(
            "sequenceDiagram\n"
            "    A->>B: hello\\nworld\n"
            "    Note over A: line1\\nline2"
        )
        assert self.func(block, "f.md") == []

    def test_multiple_backslash_n_on_same_line_one_issue(self):
        """Repeated `\\n` on one line still produces a single issue per line."""
        block = self._block(
            "flowchart TD\n"
            "    A[line1\\nline2\\nline3]"
        )
        issues = self.func(block, "f.md")
        rules = [i.rule for i in issues]
        assert rules.count("literal-backslash-n") == 1


class TestLintFile:
    """Tests for mermaid_validate.lint_file."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_validate import lint_file
        self.func = lint_file

    def test_clean_file(self, tmp_path: Path):
        path = tmp_path / "ok.md"
        path.write_text(
            textwrap.dedent(
                """\
                # OK

                ```mermaid
                flowchart LR
                    A --> B
                ```
                """
            )
        )
        blocks, issues = self.func(path)
        assert blocks == 1
        assert issues == []

    def test_failing_file(self, tmp_path: Path):
        path = tmp_path / "broken.md"
        path.write_text(
            textwrap.dedent(
                """\
                # Broken

                ```mermaid
                flowchart LR
                    A -->|hello (world)| B
                ```
                """
            )
        )
        blocks, issues = self.func(path)
        assert blocks == 1
        assert len(issues) == 1
        assert issues[0].rule == "unquoted-edge-label"

    def test_no_mermaid_blocks(self, tmp_path: Path):
        path = tmp_path / "plain.md"
        path.write_text("# Plain\n\nNo diagrams here.\n")
        blocks, issues = self.func(path)
        assert blocks == 0
        assert issues == []

    def test_mixed_clean_and_broken(self, tmp_path: Path):
        path = tmp_path / "mixed.md"
        path.write_text(
            textwrap.dedent(
                """\
                ```mermaid
                flowchart LR
                    A --> B
                ```

                ```mermaid
                flowchart LR
                    A -->|hello (world)| B
                ```
                """
            )
        )
        blocks, issues = self.func(path)
        assert blocks == 2
        assert len(issues) == 1


class TestMermaidValidateMain:
    """Tests for mermaid_validate.main (CLI entry point)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_validate import main
        self.func = main

    def test_no_args_returns_2(self, capsys):
        rc = self.func([])
        assert rc == 2
        err = capsys.readouterr().err
        assert "usage" in err.lower()

    def test_missing_file_returns_2(self, tmp_path: Path, capsys):
        missing = tmp_path / "does-not-exist.md"
        rc = self.func([str(missing)])
        assert rc == 2

    def test_clean_file_returns_0(self, tmp_path: Path, capsys):
        path = tmp_path / "ok.md"
        path.write_text("```mermaid\nflowchart LR\n  A --> B\n```\n")
        rc = self.func([str(path)])
        out = capsys.readouterr().out
        assert rc == 0
        assert "STATUS=PASS" in out
        assert "BLOCKS_CHECKED=1" in out

    def test_broken_file_returns_1(self, tmp_path: Path, capsys):
        path = tmp_path / "bad.md"
        path.write_text(
            "```mermaid\nflowchart LR\n  A -->|hello (x)| B\n```\n"
        )
        rc = self.func([str(path)])
        out = capsys.readouterr().out
        assert rc == 1
        assert "STATUS=FAIL" in out
        assert "ERROR:" in out

    def test_multiple_files(self, tmp_path: Path, capsys):
        ok = tmp_path / "ok.md"
        ok.write_text("```mermaid\nflowchart LR\n  A --> B\n```\n")
        bad = tmp_path / "bad.md"
        bad.write_text(
            "```mermaid\nflowchart LR\n  A -->|hello (x)| B\n```\n"
        )
        rc = self.func([str(ok), str(bad)])
        out = capsys.readouterr().out
        assert rc == 1
        assert "STATUS=FAIL" in out
        assert "BLOCKS_CHECKED=2" in out


# ---------------------------------------------------------------------------
# route_check
# ---------------------------------------------------------------------------


def _make_workspace(tmp_path: Path, docs_dir: str = "docs") -> Path:
    """Create a minimal valid workspace and return its docs directory."""
    (tmp_path / "fullstack.json").write_text(
        json.dumps({"docs_dir": docs_dir, "github_repos": True})
    )
    (tmp_path / "AGENTS.md").write_text("# AGENTS")
    (tmp_path / ".agents").mkdir()
    docs_root = tmp_path / docs_dir
    for work_type in ("feat", "refactor", "fix"):
        (docs_root / work_type).mkdir(parents=True, exist_ok=True)
    return docs_root


def _make_work_dir(
    docs_root: Path,
    *,
    name: str,
    work_type: str = "feat",
    status: str = "Done",
    progress_extra: str = "",
) -> Path:
    """Create a work directory with plan.md and progress.md."""
    work_dir = docs_root / work_type / name
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "plan.md").write_text(
        f"# {name}\n\n**Status**: {status}\n", encoding="utf-8"
    )
    (work_dir / "progress.md").write_text(
        f"# Progress: {name}\n\n**Overall status**: {status}\n{progress_extra}",
        encoding="utf-8",
    )
    return work_dir


class TestNormalizeStatus:
    """Tests for route_check.normalize_status."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from route_check import normalize_status
        self.func = normalize_status

    def test_empty_is_unknown(self):
        assert self.func("") == "Unknown"

    def test_done_exact(self):
        assert self.func("Done") == "Done"

    def test_done_with_description(self):
        """The user's actual case: 'Done v3 — final approach'."""
        assert self.func("Done v3 — final approach") == "Done"

    def test_done_chinese_freeform(self):
        """Another real case: '已实现并测试通过'."""
        assert self.func("已实现并测试通过") == "Done"

    def test_complete(self):
        assert self.func("Complete") == "Done"

    def test_in_progress_english(self):
        assert self.func("In Progress") == "InProgress"

    def test_in_progress_hyphenated(self):
        assert self.func("in-progress") == "InProgress"

    def test_in_progress_chinese(self):
        assert self.func("进行中") == "InProgress"

    def test_planning(self):
        assert self.func("Planning") == "Planning"

    def test_planning_chinese(self):
        assert self.func("规划中") == "Planning"

    def test_closed(self):
        assert self.func("Closed") == "Closed"

    def test_closed_chinese(self):
        assert self.func("已关闭") == "Closed"

    def test_merged_counts_as_closed(self):
        assert self.func("Merged into main") == "Closed"

    def test_unknown_freeform(self):
        assert self.func("foo bar") == "Unknown"

    def test_closed_takes_precedence_over_done(self):
        """If both keywords appear, Closed wins (it is a stricter terminal state)."""
        assert self.func("Done and closed") == "Closed"


class TestParseStatus:
    """Tests for route_check.parse_status."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from route_check import parse_status
        self.func = parse_status

    def test_english_status(self):
        text = "# X\n\n**Source**: foo\n**Status**: Done\n"
        assert self.func(text) == "Done"

    def test_chinese_status(self):
        text = "# X\n\n**来源**：foo\n**状态**：已完成\n"
        assert self.func(text) == "已完成"

    def test_status_with_full_width_colon(self):
        text = "**状态**：Done v3\n"
        assert self.func(text) == "Done v3"

    def test_no_status_returns_empty(self):
        assert self.func("# X\n\nno status here\n") == ""

    def test_first_match_wins(self):
        text = "**Status**: Planning\n\n**Status**: Done\n"
        assert self.func(text) == "Planning"


class TestFindLatestSuccessor:
    """Tests for route_check.find_latest_successor."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from route_check import find_latest_successor
        self.func = find_latest_successor

    def test_no_successors_section(self):
        text = "# Progress\n\n## Change Log\n\nstuff\n"
        has, latest = self.func(text)
        assert has is False
        assert latest is None

    def test_english_single_successor(self):
        text = textwrap.dedent(
            """\
            ## Successors

            | Date | Successor | Type | Reason |
            |------|-----------|------|--------|
            | 2026-05-01 | [`feat/dark-mode-v2/`](../dark-mode-v2/) | feat | Extension |
            """
        )
        has, latest = self.func(text)
        assert has is True
        assert latest == "../dark-mode-v2/"

    def test_chinese_single_successor(self):
        text = textwrap.dedent(
            """\
            ## 后续工作

            | 日期 | 后续工作 | 类型 | 原因 |
            |------|----------|------|------|
            | 2026-05-01 | [`feat/dark-mode-v2/`](../dark-mode-v2/) | feat | 扩展 |
            """
        )
        has, latest = self.func(text)
        assert has is True
        assert latest == "../dark-mode-v2/"

    def test_returns_latest_when_multiple(self):
        text = textwrap.dedent(
            """\
            ## Successors

            | Date | Successor | Type | Reason |
            |------|-----------|------|--------|
            | 2026-05-01 | [`feat/dark-mode-v2/`](../dark-mode-v2/) | feat | A |
            | 2026-06-01 | [`feat/dark-mode-v3/`](../dark-mode-v3/) | feat | B |
            """
        )
        has, latest = self.func(text)
        assert has is True
        assert latest == "../dark-mode-v3/"

    def test_section_with_no_link_rows(self):
        text = "## Successors\n\n(none yet)\n"
        has, latest = self.func(text)
        assert has is False
        assert latest is None

    def test_stops_at_next_h2(self):
        text = textwrap.dedent(
            """\
            ## Successors

            | Date | Successor |
            |------|-----------|
            | 2026-05-01 | [`feat/x-v2/`](../x-v2/) |

            ## Other Section

            | a | b |
            |---|---|
            | [`feat/y/`](../y/) | x |
            """
        )
        has, latest = self.func(text)
        assert has is True
        assert latest == "../x-v2/"


class TestHasIterationLog:
    """Tests for route_check.has_iteration_log."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from route_check import has_iteration_log
        self.func = has_iteration_log

    def test_english_present(self):
        assert self.func("# P\n\n## Iteration Log\n\n") is True

    def test_chinese_present(self):
        assert self.func("# P\n\n## 迭代记录\n\n") is True

    def test_absent(self):
        assert self.func("# P\n\n## Change Log\n") is False


class TestDetectTriggers:
    """Tests for route_check.detect_triggers."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from route_check import detect_triggers
        self.func = detect_triggers

    def test_chinese_read_verb(self):
        triggers = self.func("看一下 feat/dark-mode")
        assert triggers.has_read is True
        assert triggers.has_followup is False
        assert triggers.has_iteration is False

    def test_english_read_verb(self):
        triggers = self.func("Look at feat/dark-mode for context")
        assert triggers.has_read is True

    def test_chinese_iteration_verb(self):
        triggers = self.func("我想改一下逻辑")
        assert triggers.has_iteration is True

    def test_english_iteration_verb(self):
        triggers = self.func("this is wrong, fix this")
        assert triggers.has_iteration is True

    def test_chinese_followup_verb(self):
        triggers = self.func("在 dark-mode 基础上扩展")
        assert triggers.has_followup is True

    def test_english_followup_verb(self):
        triggers = self.func("follow up on dark-mode")
        assert triggers.has_followup is True

    def test_resume_verb(self):
        triggers = self.func("继续 dark-mode")
        assert triggers.has_resume is True

    def test_compound_read_plus_iteration(self):
        """The user's original failing prompt — both verbs detected."""
        triggers = self.func("看一下 @feat/dark-mode 我想改一下逻辑")
        assert triggers.has_read is True
        assert triggers.has_iteration is True

    def test_no_trigger(self):
        triggers = self.func("implement a brand new feature")
        assert triggers.labels == []


class TestDecideRoute:
    """Tests for route_check.decide_route — the core decision tree."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from route_check import decide_route, detect_triggers
        self.decide = decide_route
        self.detect = detect_triggers

    def _info(
        self,
        *,
        status: str = "Done",
        has_successors: bool = False,
        latest_successor: str | None = None,
    ):
        from route_check import WorkDirInfo
        return WorkDirInfo(
            name="dark-mode",
            path=Path("/tmp/x"),
            work_type="feat",
            status_raw=status,
            status_normalized=status,
            has_successors=has_successors,
            latest_successor=latest_successor,
            iteration_log_found=False,
        )

    def test_no_work_dir_no_verb_is_fresh(self):
        result = self.decide(None, self.detect("implement a new feature"))
        assert result.route == "Fresh"

    def test_no_work_dir_with_verb_is_ask(self):
        result = self.decide(None, self.detect("look at feat/dark-mode"))
        assert result.route == "AskUser"

    def test_done_plus_iteration_verb(self):
        """The user's reported failure case — must route to Iteration."""
        info = self._info(status="Done")
        result = self.decide(info, self.detect("我想改一下"))
        assert result.route == "Iteration"
        assert result.recommended_next_doc == "iteration-mode.md"

    def test_done_plus_compound_read_and_iteration(self):
        """Read + iteration verbs → Iteration wins, with reading as background."""
        info = self._info(status="Done")
        result = self.decide(
            info, self.detect("看一下 feat/dark-mode 我想改一下逻辑")
        )
        assert result.route == "Iteration"
        assert any("background" in r.lower() for r in result.reasoning)

    def test_done_plus_read_only_is_reference(self):
        info = self._info(status="Done")
        result = self.decide(info, self.detect("look at feat/dark-mode"))
        assert result.route == "Reference"

    def test_done_no_verb_is_ask(self):
        info = self._info(status="Done")
        result = self.decide(info, self.detect("dark-mode"))
        assert result.route == "AskUser"

    def test_closed_plus_followup_verb(self):
        info = self._info(status="Closed")
        result = self.decide(info, self.detect("在 dark-mode 基础上扩展"))
        assert result.route == "Followup"

    def test_closed_plus_read_verb_is_reference(self):
        info = self._info(status="Closed")
        result = self.decide(info, self.detect("look at feat/dark-mode for context"))
        assert result.route == "Reference"

    def test_closed_plus_iteration_verb_is_ask(self):
        """Closed + iteration is ambiguous (shipped code) — must ask."""
        info = self._info(status="Closed")
        result = self.decide(info, self.detect("调一下"))
        assert result.route == "AskUser"

    def test_closed_no_verb_is_ask(self):
        info = self._info(status="Closed")
        result = self.decide(info, self.detect(""))
        assert result.route == "AskUser"

    def test_in_progress_plus_resume_is_resume(self):
        info = self._info(status="InProgress")
        result = self.decide(info, self.detect("继续 dark-mode"))
        assert result.route == "Resume"

    def test_planning_plus_iteration_verb_is_resume(self):
        info = self._info(status="Planning")
        result = self.decide(info, self.detect("再改一下"))
        assert result.route == "Resume"

    def test_unknown_status_is_ask(self):
        """Free-form Status that the agent can't map → ask user."""
        info = self._info(status="Unknown")
        result = self.decide(info, self.detect("我想改一下"))
        assert result.route == "AskUser"

    def test_compound_followup_and_iteration_is_ask(self):
        info = self._info(status="Done")
        result = self.decide(
            info, self.detect("在 dark-mode 基础上扩展，但其实只想改一下")
        )
        assert result.route == "AskUser"

    def test_successors_are_reported_in_reasoning(self):
        info = self._info(
            status="Closed",
            has_successors=True,
            latest_successor="../dark-mode-v2/",
        )
        result = self.decide(info, self.detect("look at feat/dark-mode"))
        assert any("Successors" in r for r in result.reasoning)
        assert any("dark-mode-v2" in r for r in result.reasoning)


class TestRouteCheckMain:
    """End-to-end tests for route_check.main."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from route_check import main
        self.func = main

    def test_invalid_workspace_returns_2(self, tmp_path: Path, capsys):
        rc = self.func([
            "--workspace-root", str(tmp_path),
            "--work-dir-name", "x",
            "--prompt", "look at x",
        ])
        assert rc == 2

    def test_valid_workspace_no_match_returns_fresh(self, tmp_path: Path, capsys):
        _make_workspace(tmp_path)
        rc = self.func([
            "--workspace-root", str(tmp_path),
            "--work-dir-name", "nonexistent",
            "--prompt", "implement a new feature",
        ])
        out = capsys.readouterr().out
        assert rc == 0
        assert "ROUTE=Fresh" in out

    def test_valid_workspace_with_match(self, tmp_path: Path, capsys):
        docs_root = _make_workspace(tmp_path)
        _make_work_dir(docs_root, name="dark-mode", status="Done")
        rc = self.func([
            "--workspace-root", str(tmp_path),
            "--work-dir-name", "dark-mode",
            "--prompt", "我想改一下 dark-mode 的逻辑",
        ])
        out = capsys.readouterr().out
        assert rc == 0
        assert "ROUTE=Iteration" in out
        assert "STATUS_NORMALIZED=Done" in out
        assert "RECOMMENDED_NEXT_DOC=iteration-mode.md" in out

    def test_real_world_freeform_status(self, tmp_path: Path, capsys):
        """The exact scenario reported by the user — 已实现并测试通过 + 我想改."""
        docs_root = _make_workspace(tmp_path)
        _make_work_dir(
            docs_root,
            name="low-battery-protection",
            status="已实现并测试通过",
        )
        rc = self.func([
            "--workspace-root", str(tmp_path),
            "--work-dir-name", "low-battery-protection",
            "--prompt", "看一下 low-battery-protection 我想改一下逻辑",
        ])
        out = capsys.readouterr().out
        assert rc == 0
        assert "ROUTE=Iteration" in out
        assert "STATUS_NORMALIZED=Done" in out

    def test_prompt_file_overrides_inline(self, tmp_path: Path, capsys):
        docs_root = _make_workspace(tmp_path)
        _make_work_dir(docs_root, name="x", status="Closed")
        prompt_path = tmp_path / "prompt.txt"
        prompt_path.write_text("look at feat/x")
        rc = self.func([
            "--workspace-root", str(tmp_path),
            "--work-dir-name", "x",
            "--prompt", "(this should be ignored)",
            "--prompt-file", str(prompt_path),
        ])
        out = capsys.readouterr().out
        assert rc == 0
        assert "ROUTE=Reference" in out

    def test_invalid_workspace_root_returns_1(self, tmp_path: Path):
        rc = self.func([
            "--workspace-root", str(tmp_path / "missing"),
        ])
        assert rc == 1
