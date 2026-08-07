"""Tests for fullstack-apply skill scripts.

Covers pure/deterministic functions from:
- check_workspace.py — workspace validation gate (3 markers + config)
- check_github_repos.py — fullstack.json config reading (legacy wrapper)
- mermaid_lint.py — Mermaid 10.2.3 compatibility lint (canonical
  source at mythril_agent_skills/shared/mermaid/mermaid_lint.py;
  byte-identical bundled copy at fullstack-apply/scripts/mermaid_lint.py)
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



class TestExtractMermaidBlocks:
    """Tests for mermaid_lint.extract_mermaid_blocks."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import extract_mermaid_blocks
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
    """Tests for mermaid_lint.is_quoted."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import is_quoted
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
    """Tests for mermaid_lint.find_edge_label_issues."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import find_edge_label_issues
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
    """Tests for mermaid_lint.find_subgraph_issue."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import find_subgraph_issue
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
    """Tests for mermaid_lint.find_new_shape_issue."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import find_new_shape_issue
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
    """Tests for mermaid_lint.find_literal_backslash_n_issue."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import find_literal_backslash_n_issue
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
    """Tests for mermaid_lint.find_beta_diagram_issue."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import find_beta_diagram_issue
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



class TestFindBareBrIssue:
    """Tests for mermaid_lint.find_bare_br_issue."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import find_bare_br_issue
        self.func = find_bare_br_issue

    def test_clean_line(self):
        assert self.func("    A[hello world] --> B") is False

    def test_self_closing_br_ok(self):
        assert self.func("    A[line1<br/>line2]") is False

    def test_self_closing_br_with_space_ok(self):
        assert self.func("    A[line1<br />line2]") is False

    def test_bare_br_flagged(self):
        assert self.func("    A[line1<br>line2]") is True

    def test_bare_br_with_space_flagged(self):
        assert self.func("    A[line1<br >line2]") is True

    def test_bare_br_uppercase_flagged(self):
        assert self.func("    A[line1<BR>line2]") is True

    def test_bare_br_in_edge_label_flagged(self):
        assert self.func('    A -->|"line1<br>line2"| B') is True

    def test_text_containing_br_substring_not_flagged(self):
        # The word "brake" should not match.
        assert self.func("    A[brake system]") is False

    def test_br_with_attributes_not_flagged_as_bare(self):
        # If the author wrote <br class="x"> we treat it as "not bare"
        # — the regex only flags <br> or <br > with no other content.
        # A reviewer would flag attributed <br> as suspicious anyway.
        assert self.func("    A[x<br class='y'>y]") is False



class TestEscapeLabelForMermaid:
    """Tests for mermaid_lint.escape_label_for_mermaid."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import escape_label_for_mermaid
        self.func = escape_label_for_mermaid

    def test_none_returns_empty_quoted(self):
        assert self.func(None) == '""'

    def test_plain_word_unquoted(self):
        assert self.func("Discover") == "Discover"

    def test_plain_chinese_unquoted(self):
        assert self.func("发现") == "发现"

    def test_real_newline_becomes_br(self):
        assert self.func("xxx-api\n(Domain API)") == '"xxx-api<br/>(Domain API)"'

    def test_crlf_becomes_single_br(self):
        # CRLF collapses to one \n which becomes <br/>; the presence of
        # <br/> triggers quoting per the helper's contract.
        assert self.func("a\r\nb") == '"a<br/>b"'

    def test_cr_only_becomes_br(self):
        assert self.func("a\rb") == '"a<br/>b"'

    def test_chinese_with_newline(self):
        # Same quoting rule: any <br/> in the result implies quotes.
        assert self.func("发现\n试用") == '"发现<br/>试用"'

    def test_literal_backslash_n_becomes_br(self):
        # Two characters: backslash + n.
        assert self.func("xxx-api\\n(Domain API)") == '"xxx-api<br/>(Domain API)"'

    def test_parens_force_quoting(self):
        assert self.func("Domain (API)") == '"Domain (API)"'

    def test_brackets_force_quoting(self):
        assert self.func("step [1]") == '"step [1]"'

    def test_curlies_force_quoting(self):
        assert self.func("use {x}") == '"use {x}"'

    def test_pipe_forces_quoting(self):
        assert self.func("a | b") == '"a | b"'

    def test_angle_bracket_forces_quoting(self):
        assert self.func("a > b") == '"a > b"'

    def test_embedded_double_quote_escaped(self):
        assert self.func('He said "hi"') == '"He said &quot;hi&quot;"'

    def test_br_in_input_implies_quotes(self):
        # Plain "<br/>" alone (no other special chars) still needs quotes
        # because `<` and `>` are quoting-triggers.
        assert self.func("a<br/>b") == '"a<br/>b"'

    def test_only_alphanumerics_no_quotes(self):
        assert self.func("Stage1") == "Stage1"

    def test_hyphen_and_space_no_quotes(self):
        assert self.func("Sign up") == "Sign up"

    def test_chinese_with_paren_and_newline(self):
        assert self.func("发现\n（中文括号）") == '"发现<br/>（中文括号）"'

    def test_real_world_xxxapi_case(self):
        """The exact case from the user's bug report."""
        result = self.func("xxx-api\n(Domain API)")
        assert result == '"xxx-api<br/>(Domain API)"'
        # And it must NOT contain the literal "\n" sequence anywhere.
        assert "\\n" not in result
        assert "\n" not in result



class TestLintBlock:
    """Tests for mermaid_lint.lint_block."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import MermaidBlock, lint_block
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
    """Tests for mermaid_lint.lint_file."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import lint_file
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
    """Tests for mermaid_lint.main (CLI entry point)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from mermaid_lint import main
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


