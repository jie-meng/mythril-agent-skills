"""Tests for the shared work-tracking document linter (plan_lint.py).

Covers Success-Criteria ↔ Evidence-row reconciliation, plan-review closure
and round numbering, task-id references, placeholder detection, the Code
Map reverse index, the per-round document-sync attestation, and the CLI
contract (lint mode and `--find` lookup mode) used by the fullstack
skills.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from mythril_agent_skills.shared.plan.plan_lint import (
    detect_verdict,
    discover_docs_dir,
    find_in_docs_dir,
    find_placeholders,
    format_findings,
    lint_work_dir,
    match_code_map_row,
    normalize_path,
    parse_code_map_rows,
    parse_coverage_rows,
    parse_evidence_rows,
    parse_plan_review_rounds,
    parse_req_ids,
    parse_sc_ids,
    parse_task_ids,
)


def _work_dir(tmp_path: Path, plan: str = "", review: str = "", analysis: str = ""):
    """Write a work directory with the given document contents."""
    if plan:
        (tmp_path / "plan.md").write_text(plan, encoding="utf-8")
    if review:
        (tmp_path / "review.md").write_text(review, encoding="utf-8")
    if analysis:
        (tmp_path / "analysis.md").write_text(analysis, encoding="utf-8")
    return tmp_path


SUMMARY_BLOCK = """## 摘要（给人读的——全工作项唯一允许原地更新的章节）

**一句话**：给 demo 工作项一个可以核验的最小骨架。
**状态**：规划中——方案待审查。
**需要你决策的事**：无
**没解决的事**：无
**读哪里**：问题细节→analysis.md；怎么实施→本文件正文；审查与证据→review.md

"""

CODE_MAP_BLOCK = """## 代码地图（Code Map）

| 仓库 | 路径 | 符号 | 改了什么 |
|------|------|------|---------|
| api | `src/preferences/dark_mode.py` | `ThemePreference` | 新增偏好接口 |

"""

PLAN_OK = f"""# Plan: demo

{SUMMARY_BLOCK}## 成功标准

- [ ] SC1 works
- [ ] SC2 also works

{CODE_MAP_BLOCK}## 实现计划

- [ ] T1 do the thing
"""

PLAN_NO_SUMMARY = PLAN_OK.replace(SUMMARY_BLOCK, "")

REVIEW_OK = """# 审查：demo

## 证据核验

| 成功标准 | 结果 | 证据 |
|---------|------|------|
| SC1 | 待核验 | |
| SC2 | 待核验 | |

## 方案审查 — 第 1 轮 — 2026-09-21

机械门禁：Mermaid **PASS**

### 判定

PASS — no blocking findings.
"""

ANALYSIS_REQS = """# 分析：demo

## 需求原文

- **REQ1**「跟周围的人聊聊天。」（用户原话，未指定话题）
- **REQ2**「你和周围的人聊聊这个问题呗」要先聊刚才那件事

## 根因

正文。
"""

REVIEW_COV = """# 审查：demo

## 证据核验

| 成功标准 | 结果 | 证据 |
|---------|------|------|
| SC1 | 待核验 | |
| SC2 | 待核验 | |

## 方案审查 — 第 1 轮 — 2026-09-21

### 需求覆盖

| 需求 | 标准 | 状态 |
|---|---|---|
| REQ1 | SC1 | 覆盖 |
| REQ2 | SC2 | 覆盖 |

### 判定

PASS — 无阻塞问题。
"""

# A coverage matrix that names requirements in prose instead of by id —
# the shape every work item wrote before requirements got an id namespace.
REVIEW_COV_NOREQ = REVIEW_COV.replace("| REQ1 |", "| 聊天指令 |").replace(
    "| REQ2 |", "| 回指场景 |"
)


def _review_with_findings(p0: int = 0, p1: int = 0, p2: int = 0) -> str:
    """REVIEW_OK's round 1 carrying the given number of severity bullets."""
    bullets = "\n".join(
        f"- [P{level}] finding {index}"
        for level, count in (("0", p0), ("1", p1), ("2", p2))
        for index in range(count)
    )
    return REVIEW_OK.replace(
        "机械门禁：Mermaid **PASS**",
        f"### 问题清单\n\n{bullets}\n\n机械门禁：Mermaid **PASS**"
        if bullets
        else "机械门禁：Mermaid **PASS**",
    )


def _errors(findings) -> list[str]:
    return [f.message for f in findings if f.level == "ERROR"]


def _warnings(findings) -> list[str]:
    return [f.message for f in findings if f.level == "WARN"]


class TestParseIds:
    def test_sc_ids(self):
        assert parse_sc_ids("SC1 SC10 and SC4a, but not SUPERSC2") == {
            "SC1",
            "SC10",
            "SC4a",
        }

    def test_task_ids(self):
        assert parse_task_ids("T0, T3b and T14 — not TODO") == {"T0", "T3b", "T14"}

    def test_req_ids(self):
        assert parse_req_ids("REQ1 REQ12 but not REQUEST2") == {"REQ1", "REQ12"}

    def test_severity_bullets(self):
        from mythril_agent_skills.shared.plan.plan_lint import count_severities

        body = (
            "- [P0] block\n- [P1] a\n- [P1] b\n* [P2] c\n"
            "- plain bullet, no severity\n"
        )
        assert count_severities(body) == {"0": 1, "1": 2, "2": 1}


class TestParseEvidenceRows:
    def test_reads_table_rows_only(self):
        text = (
            "## 证据核验\n\n"
            "| 成功标准 | 结果 | 证据 |\n"
            "|---------|------|------|\n"
            "| SC1 | 通过 | x |\n"
            "| SC2 | 待核验 | |\n"
        )
        assert parse_evidence_rows(text) == {"SC1", "SC2"}

    def test_prose_mention_does_not_count_as_row(self):
        text = "## 证据核验\n\nSC3 is discussed in prose but has no row.\n"
        assert parse_evidence_rows(text) == set()

    def test_english_heading(self):
        text = "## Evidence\n\n| Criterion | Result |\n|---|---|\n| SC7 | Pass |\n"
        assert parse_evidence_rows(text) == {"SC7"}

    def test_missing_section_returns_none(self):
        assert parse_evidence_rows("# 审查：demo\n\nno table here\n") is None


class TestParseCoverageRows:
    def test_reads_matrix_rows_across_rounds(self):
        text = (
            "## Plan Review - Round 1 - 2026-09-21\n"
            "### Requirements Coverage\n"
            "| Requirement | Criterion | Status |\n"
            "|---|---|---|\n"
            "| REQ1 | SC1 | OK |\n"
            "| REQ2 | SC2 | OK |\n"
            "### Verdict\n"
            "PASS\n"
            "## Plan Review - Round 2 - 2026-09-22\n"
            "### Requirements Coverage\n"
            "| Requirement | Criterion | Status |\n"
            "|---|---|---|\n"
            "| REQ3 | SC3 | OK |\n"
            "### Verdict\n"
            "PASS\n"
        )
        assert parse_coverage_rows(text) == {"REQ1", "REQ2", "REQ3"}

    def test_prose_mention_does_not_count_as_row(self):
        text = (
            "## Plan Review - Round 1 - 2026-09-21\n"
            "### Requirements Coverage\n"
            "REQ1 is discussed in prose but has no row.\n"
        )
        assert parse_coverage_rows(text) == set()

    def test_missing_matrix_returns_none(self):
        assert parse_coverage_rows("# 审查：demo\n\nno matrix here\n") is None


class TestDetectVerdict:
    def test_verdict_heading_wins_over_gate_results(self):
        # A real pattern: the section reports "Mermaid PASS" before its
        # verdict. Reading the last token would call this a PASS.
        body = (
            "机械门禁：Mermaid **PASS**、DAG PASS\n\n"
            "### 判定：NEEDS_FIXES\n\n| 级别 | 问题 |\n|---|---|\n"
        )
        assert detect_verdict(body) == "NEEDS_FIXES"

    def test_english_verdict_heading(self):
        body = "### Verdict\n\nPASS_WITH_RISKS — see risks below.\n"
        assert detect_verdict(body) == "PASS_WITH_RISKS"

    def test_falls_back_to_last_token(self):
        assert detect_verdict("Round 1: NEEDS_FIXES ... later PASS") == "PASS"

    def test_no_token(self):
        assert detect_verdict("nothing to see here") is None


class TestParsePlanReviewRounds:
    def test_english_and_chinese_headings(self):
        text = (
            "## Plan Review — Round 1 — 2026-01-01\n\n### Verdict\nNEEDS_FIXES\n\n"
            "## 方案审查 — 第 2 轮 — 2026-01-02\n\n### 结论\nPASS\n"
        )
        rounds = parse_plan_review_rounds(text)
        assert [r.number for r in rounds] == [1, 2]
        assert [r.verdict for r in rounds] == ["NEEDS_FIXES", "PASS"]

    def test_ignores_unrelated_sections(self):
        text = "## 证据核验\n\n| SC1 |\n\n## 设计复核\n\nNEEDS_FIXES-ish\n"
        assert parse_plan_review_rounds(text) == []


class TestFindPlaceholders:
    def test_finds_placeholder_lines(self):
        text = "| D7 | strategy | **待确认** |\n"
        assert len(find_placeholders(text)) == 1

    def test_skips_heading_naming_the_section(self):
        assert find_placeholders("## 风险 / 待确认问题\n") == []

    def test_skips_negated_mention(self):
        text = "- 设计与决策已全部拍板：**开工前无待确认问题。**\n"
        assert find_placeholders(text) == []


class TestLintWorkDir:
    def test_clean_item_passes(self, tmp_path: Path):
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, REVIEW_OK))
        assert _errors(findings) == []

    def test_missing_evidence_row_is_an_error(self, tmp_path: Path):
        review = REVIEW_OK.replace("| SC2 | 待核验 | |\n", "")
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, review))
        assert any("SC2" in message for message in _errors(findings))

    def test_stale_evidence_row_is_an_error(self, tmp_path: Path):
        review = REVIEW_OK.replace(
            "| SC2 | 待核验 | |", "| SC2 | 待核验 | |\n| SC9 | 待核验 | |"
        )
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, review))
        assert any("SC9" in message for message in _errors(findings))

    def test_unclosed_review_is_an_error(self, tmp_path: Path):
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, REVIEW_OK))
        assert _errors(findings) == []

        review = REVIEW_OK.replace("PASS — no blocking", "NEEDS_FIXES — blockers")
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, review))
        assert any("not closed" in message for message in _errors(findings))

    def test_round_numbering_gap_is_an_error(self, tmp_path: Path):
        review = (
            REVIEW_OK
            + "\n## 方案审查 — 第 3 轮 — 2026-01-02\n\n### 结论\nPASS\n"
        )
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, review))
        assert any("numbered 1..N" in message for message in _errors(findings))

    def test_unknown_task_id_is_an_error(self, tmp_path: Path):
        review = REVIEW_OK + "\nTask T7 was revised.\n"
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, review))
        assert any("T7" in message for message in _errors(findings))

    def test_error_wins_over_warning_status(self, tmp_path: Path):
        review = REVIEW_OK.replace("PASS — no blocking", "NEEDS_FIXES — blockers")
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, review, analysis="D7 待确认\n")
        )
        assert "STATUS=FAIL" in format_findings(findings)
        assert 'WARNINGS=1' in format_findings(findings)

    def test_summary_section_present_no_warning(self, tmp_path: Path):
        # The heading carries a parenthetical suffix on purpose: the
        # prefix match in find_section_body must still hit it.
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, REVIEW_OK))
        assert _warnings(findings) == []

    def test_missing_summary_warns_but_status_stays_pass(self, tmp_path: Path):
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_NO_SUMMARY, REVIEW_OK))
        assert any("'## 摘要'" in m for m in _warnings(findings))
        assert "STATUS=PASS" in format_findings(findings)

    def test_legacy_item_without_evidence_table_warns(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, "# 审查：demo\n\nnothing\n")
        )
        messages = _warnings(findings)
        assert any("no Evidence table" in m for m in messages)
        assert any("no plan review round" in m for m in messages)
        assert _errors(findings) == []

    def test_missing_documents_are_errors(self, tmp_path: Path):
        findings = lint_work_dir(tmp_path)
        assert len(_errors(findings)) == 2


    def test_requirements_round_trip_is_clean(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, REVIEW_COV, analysis=ANALYSIS_REQS)
        )
        assert _errors(findings) == []
        assert _warnings(findings) == []

    def test_coverage_matrix_without_baseline_warns(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(
                tmp_path, PLAN_OK, REVIEW_COV_NOREQ, analysis="# 分析\n\n无此节\n"
            )
        )
        assert _errors(findings) == []
        assert any("judged" in m for m in _warnings(findings))

    def test_legacy_item_with_neither_is_silent(self, tmp_path: Path):
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, REVIEW_OK))
        assert not any("需求原文" in m for m in _warnings(findings))

    def test_req_cited_without_a_section_is_an_error(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, REVIEW_COV, analysis="# 分析\n\n正文\n")
        )
        assert any("REQ ids" in m for m in _errors(findings))

    def test_undeclared_req_is_an_error(self, tmp_path: Path):
        analysis = ANALYSIS_REQS.replace("- **REQ2**", "- **REQ9**")
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, REVIEW_COV, analysis=analysis)
        )
        assert any("not declared" in m for m in _errors(findings))

    def test_declared_but_never_reviewed_req_is_an_error(self, tmp_path: Path):
        # REQ3 must sit inside the requirements section, not after it.
        analysis = ANALYSIS_REQS.replace(
            "\n## 根因",
            "- **REQ3** 第三条从未被任何轮次引用\n\n## 根因",
        )
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, REVIEW_COV, analysis=analysis)
        )
        assert any("REQ3" in m and "never appear" in m for m in _errors(findings))

    def test_prose_mention_does_not_fake_a_matrix_row(self, tmp_path: Path):
        # REQ3 is declared and discussed in a finding bullet, but the
        # coverage matrix has no row for it. Discussing a requirement is
        # not the same as asserting its coverage.
        analysis = ANALYSIS_REQS.replace(
            "\n## 根因",
            "- **REQ3** 第三条只在发现里被讨论过\n\n## 根因",
        )
        review = REVIEW_COV.replace(
            "### 判定",
            "- [P1] REQ3 已讨论，见结论\n\n### 判定",
        )
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, review, analysis=analysis)
        )
        assert any("REQ3" in m and "never appear" in m for m in _errors(findings))

    def test_empty_requirements_section_is_an_error(self, tmp_path: Path):
        analysis = "# 分析：demo\n\n## 需求原文\n\n（略）\n"
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, REVIEW_OK, analysis=analysis)
        )
        empty = "requirements-of-record section is empty"
        assert any(empty in m for m in _errors(findings))

    def test_p2_above_the_cap_warns(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, _review_with_findings(p1=1, p2=6))
        )
        assert any("6 P2 findings" in m for m in _warnings(findings))
        assert _errors(findings) == []

    def test_p2_at_the_cap_stays_silent(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, _review_with_findings(p1=1, p2=5))
        )
        assert not any("P2 findings" in m for m in _warnings(findings))

    def test_oscillating_rounds_warn(self, tmp_path: Path):
        round_two = (
            "\n## 方案审查 — 第 2 轮 — 2026-09-22\n\n"
            "- [P1] new one\n- [P1] another\n- [P1] third\n\n"
            "### 判定\n\nPASS — no blocking findings.\n"
        )
        findings = lint_work_dir(
            _work_dir(
                tmp_path, PLAN_OK, _review_with_findings(p1=1) + round_two
            )
        )
        assert any("oscillating" in m for m in _warnings(findings))

    def test_converging_rounds_do_not_warn(self, tmp_path: Path):
        round_two = (
            "\n## 方案审查 — 第 2 轮 — 2026-09-22\n\n"
            "第 1 轮问题全部闭环。\n\n"
            "### 判定\n\nPASS_WITH_RISKS — no blocking findings.\n"
        )
        findings = lint_work_dir(
            _work_dir(
                tmp_path, PLAN_OK, _review_with_findings(p1=4, p2=3) + round_two
            )
        )
        assert not any("oscillating" in m for m in _warnings(findings))


class TestFormatFindings:
    def test_status_line_is_first(self):
        text = format_findings([])
        assert text.splitlines()[0] == "STATUS=PASS"

    def test_counts(self):
        from mythril_agent_skills.shared.plan.plan_lint import Finding

        text = format_findings([Finding("ERROR", "x"), Finding("WARN", "y")])
        assert "CHECKS=2  WARNINGS=1" in text


class TestCli:
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(
                    Path(__file__).resolve().parent.parent
                    / "mythril_agent_skills/shared/plan/plan_lint.py"
                ),
                *args,
            ],
            capture_output=True,
            text=True,
        )

    def test_pass_exit_code(self, tmp_path: Path):
        _work_dir(tmp_path, PLAN_OK, REVIEW_OK)
        result = self._run(str(tmp_path))
        assert result.returncode == 0
        assert result.stdout.startswith("STATUS=PASS")

    def test_fail_exit_code(self, tmp_path: Path):
        review = REVIEW_OK.replace("| SC2 | 待核验 | |\n", "")
        _work_dir(tmp_path, PLAN_OK, review)
        result = self._run(str(tmp_path))
        assert result.returncode == 1
        assert result.stdout.startswith("STATUS=FAIL")

    def test_quiet_prints_status_and_errors_only(self, tmp_path: Path):
        _work_dir(tmp_path, PLAN_OK, "# 审查：demo\n", analysis="D7 待确认\n")
        result = self._run(str(tmp_path), "--quiet")
        assert "WARN" not in result.stdout

    def test_missing_directory_exits_2(self, tmp_path: Path):
        result = self._run(str(tmp_path / "nope"))
        assert result.returncode == 2


# ---------------------------------------------------------------------------
# Check 9 — Code Map
# ---------------------------------------------------------------------------

PLAN_NO_CODE_MAP = PLAN_OK.replace(CODE_MAP_BLOCK, "")

PLAN_CODE_MAP_NO_ROWS = """## 代码地图（Code Map）

还没填。
"""

PLAN_CODE_MAP_GLOB = """## 代码地图（Code Map）

| 仓库 | 路径 | 符号 | 改了什么 |
|------|------|------|---------|
| api | `src/preferences/*` | — | 偏好相关全部文件 |
"""

PLAN_CODE_MAP_ABSOLUTE = """## 代码地图（Code Map）

| 仓库 | 路径 | 符号 | 改了什么 |
|------|------|------|---------|
| api | `/Users/me/ws/api/src/dark_mode.py` | `ThemePreference` | 新增偏好接口 |
"""


def _plan_with(code_map: str) -> str:
    """PLAN_OK with its Code Map block replaced by `code_map`."""
    return PLAN_OK.replace(CODE_MAP_BLOCK, code_map)


class TestParseCodeMapRows:
    def test_reads_rows_and_skips_header(self):
        rows = parse_code_map_rows(PLAN_OK)
        assert rows == [
            {
                "repository": "api",
                "path": "src/preferences/dark_mode.py",
                "symbols": "ThemePreference",
                "change": "新增偏好接口",
            }
        ]

    def test_absent_section_returns_none(self):
        assert parse_code_map_rows(PLAN_NO_CODE_MAP) is None

    def test_prose_under_the_heading_is_not_a_row(self):
        assert parse_code_map_rows(_plan_with(PLAN_CODE_MAP_NO_ROWS)) == []

    def test_english_heading_matches(self):
        text = (
            "## Code Map\n\n"
            "| Repository | Path | Symbols | What changed |\n"
            "|---|---|---|---|\n"
            "| web | `src/App.tsx` | `App` | Toggle row |\n"
        )
        assert parse_code_map_rows(text)[0]["path"] == "src/App.tsx"


class TestCheckCodeMap:
    def test_clean_item_has_no_code_map_finding(self, tmp_path: Path):
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, REVIEW_OK))
        assert not [f for f in findings if "Code Map" in f.message]

    def test_missing_map_is_an_error(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_NO_CODE_MAP, REVIEW_OK)
        )
        assert any(
            "Code Map" in m and "file path" in m for m in _errors(findings)
        )

    def test_empty_table_is_an_error(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(tmp_path, _plan_with(PLAN_CODE_MAP_NO_ROWS), REVIEW_OK)
        )
        assert any("has no data row" in m for m in _errors(findings))

    def test_glob_row_is_an_error(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(tmp_path, _plan_with(PLAN_CODE_MAP_GLOB), REVIEW_OK)
        )
        assert any("glob or range" in m for m in _errors(findings))

    def test_machine_path_is_an_error(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(tmp_path, _plan_with(PLAN_CODE_MAP_ABSOLUTE), REVIEW_OK)
        )
        assert any("repo-relative" in m for m in _errors(findings))


# ---------------------------------------------------------------------------
# Check 10 — document-sync attestation
# ---------------------------------------------------------------------------

ATTESTATION = (
    "**文档同步**：`analysis.md` —— 目标架构图随之更新；"
    "`plan.md` —— 无（仅实现细节）；`progress.md` —— 新增当日条目；"
    "`review.md` —— 本节"
)


def _code_round(repo: str, round_no: int, attestation: str = "") -> str:
    """One `## 代码审查` section, optionally carrying the attestation."""
    return (
        f"\n## 代码审查 — {repo} — 第 {round_no} 轮 — 2026-09-2{round_no}\n\n"
        "### 结论\n\nPASS — 无阻塞。\n\n"
        "### 提交记录\n\n| Hash | Message |\n|---|---|\n| `abc1234` | feat: x |\n\n"
        "### 文档同步\n\n" + (attestation + "\n" if attestation else "")
    )


class TestDocumentSync:
    def test_plan_only_item_is_silent(self, tmp_path: Path):
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, REVIEW_OK))
        assert not [f for f in findings if "文档同步" in f.message]

    def test_newest_round_without_attestation_is_an_error(self, tmp_path: Path):
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, REVIEW_OK + _code_round("api", 1))
        )
        assert any(
            "newest code review round" in m for m in _errors(findings)
        )

    def test_older_rounds_are_not_back_filled(self, tmp_path: Path):
        # two rounds, neither attested: only the newest is demanded
        review = REVIEW_OK + _code_round("api", 1) + _code_round("api", 2)
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, review))
        missing = [m for m in _errors(findings) if "文档同步" in m]
        assert len(missing) == 1
        assert "第 2 轮" in missing[0]

    def test_earlier_rounds_need_no_backfill(self, tmp_path: Path):
        review = REVIEW_OK + _code_round("api", 1) + _code_round("api", 2, ATTESTATION)
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, review))
        assert not [f for f in findings if "文档同步" in f.message]

    def test_round_after_the_first_attestation_must_attest(self, tmp_path: Path):
        review = (
            REVIEW_OK
            + _code_round("api", 1, ATTESTATION)
            + _code_round("web", 1)
            + _code_round("web", 2)
        )
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, review))
        errors = _errors(findings)
        assert any(
            "changes code but carries no" in m and "web — 第 1 轮" in m
            for m in errors
        )
        assert any("newest code review round" in m for m in errors)

    def test_attestation_naming_three_of_four_is_an_error(self, tmp_path: Path):
        partial = ATTESTATION.replace("`progress.md` —— 新增当日条目；", "")
        findings = lint_work_dir(
            _work_dir(tmp_path, PLAN_OK, REVIEW_OK + _code_round("api", 1, partial))
        )
        errors = _errors(findings)
        assert any("omits progress.md" in m for m in errors)

    def test_heading_without_line_is_not_an_attestation(self, tmp_path: Path):
        review = REVIEW_OK + _code_round("api", 1).replace(
            "### 文档同步\n\n", "### 文档同步\n\n本轮改了些东西。\n\n"
        )
        findings = lint_work_dir(_work_dir(tmp_path, PLAN_OK, review))
        assert any(
            "newest code review round" in m for m in _errors(findings)
        )


# ---------------------------------------------------------------------------
# --find reverse lookup
# ---------------------------------------------------------------------------


class TestMatchCodeMapRow:
    def setup_method(self):
        self.row = {
            "repository": "api",
            "path": "src/preferences/dark_mode.py",
            "symbols": "ThemePreference, GET /pref",
            "change": "新增偏好接口",
        }

    def test_repo_relative_and_workspace_paths_both_score_3(self):
        assert match_code_map_row("src/preferences/dark_mode.py", self.row) == 3
        assert match_code_map_row("api/src/preferences/dark_mode.py", self.row) == 3

    def test_trailing_segment_and_basename_score_2(self):
        assert match_code_map_row("preferences/dark_mode.py", self.row) == 2
        assert match_code_map_row("dark_mode.py", self.row) == 2

    def test_symbol_scores_2(self):
        assert match_code_map_row("ThemePreference", self.row) == 2

    def test_unrelated_path_scores_0(self):
        assert match_code_map_row("src/orders/dark_mode.py", self.row) == 0

    def test_case_and_separators_are_ignored(self):
        assert match_code_map_row("./API/src/Preferences/Dark_Mode.PY", self.row) == 3

    def test_normalize_path(self):
        assert normalize_path(".\\src//preferences\\") == "src/preferences"
        assert normalize_path("/abs/path.py") == "abs/path.py"


def _docs_dir_with(tmp_path: Path, items: dict[str, str]) -> Path:
    """Build `<tmp>/central-docs/changes/<key>/plan.md` for each item."""
    docs = tmp_path / "central-docs"
    for key, plan in items.items():
        work = docs / "changes" / Path(key)
        work.mkdir(parents=True, exist_ok=True)
        (work / "plan.md").write_text(plan, encoding="utf-8")
    return docs


class TestFindInDocsDir:
    def test_finds_the_owning_work_item(self, tmp_path: Path):
        docs = _docs_dir_with(tmp_path, {"feat/dark-mode": PLAN_OK})
        hits, mentions = find_in_docs_dir(docs, "api/src/preferences/dark_mode.py")
        assert len(hits) == 1
        assert hits[0].startswith("CODEMAP: changes/feat/dark-mode | api |")

    def test_symbol_lookup_finds_the_item(self, tmp_path: Path):
        docs = _docs_dir_with(tmp_path, {"feat/dark-mode": PLAN_OK})
        hits, _ = find_in_docs_dir(docs, "ThemePreference")
        assert len(hits) == 1

    def test_archived_items_are_scanned(self, tmp_path: Path):
        docs = _docs_dir_with(
            tmp_path, {"archive/2026-09-01-feat/dark-mode": PLAN_OK}
        )
        hits, _ = find_in_docs_dir(docs, "src/preferences/dark_mode.py")
        assert len(hits) == 1

    def test_no_owner_falls_back_to_prose_mentions(self, tmp_path: Path):
        docs = _docs_dir_with(tmp_path, {"feat/dark-mode": PLAN_NO_CODE_MAP})
        (docs / "changes/feat/dark-mode/analysis.md").write_text(
            "## 目标架构\n\n`src/preferences/dark_mode.py` 承载偏好读写。\n",
            encoding="utf-8",
        )
        hits, mentions = find_in_docs_dir(docs, "src/preferences/dark_mode.py")
        assert hits == []
        assert len(mentions) == 1
        assert mentions[0].startswith("MENTION: dark-mode | analysis.md:3 |")

    def test_exact_owner_ranks_above_substring_owner(self, tmp_path: Path):
        loose = _plan_with(
            "## 代码地图（Code Map）\n\n"
            "| 仓库 | 路径 | 符号 | 改了什么 |\n|---|---|---|---|\n"
            "| docs | `notes/dark_mode.py` | — | 文档脚本 |\n"
        )
        docs = _docs_dir_with(tmp_path, {"feat/precise": PLAN_OK, "feat/loose": loose})
        hits, _ = find_in_docs_dir(docs, "src/preferences/dark_mode.py")
        assert len(hits) == 1
        assert "precise" in hits[0]

    def test_git_directories_are_skipped(self, tmp_path: Path):
        docs = _docs_dir_with(tmp_path, {"feat/dark-mode": PLAN_OK})
        junk = docs / "changes/feat/dark-mode/.git/plan.md"
        junk.parent.mkdir(parents=True, exist_ok=True)
        junk.write_text(PLAN_OK, encoding="utf-8")
        hits, _ = find_in_docs_dir(docs, "src/preferences/dark_mode.py")
        assert len(hits) == 1


class TestDiscoverDocsDir:
    def test_reads_docs_dir_from_config(self, tmp_path: Path):
        docs = _docs_dir_with(tmp_path, {"feat/x": PLAN_OK})
        (tmp_path / "fullstack.json").write_text(
            json.dumps({"docs_dir": docs.name}), encoding="utf-8"
        )
        assert discover_docs_dir(tmp_path / "api" / "src") == docs.resolve()

    def test_falls_back_to_a_directory_holding_changes(self, tmp_path: Path):
        docs = _docs_dir_with(tmp_path, {"feat/x": PLAN_OK})
        assert discover_docs_dir(docs / "changes/feat/x") == docs.resolve()

    def test_returns_none_when_nothing_matches(self, tmp_path: Path):
        assert discover_docs_dir(tmp_path) is None


class TestFindCli:
    def _run(self, *args: str, cwd: Path | None = None):
        return subprocess.run(
            [
                sys.executable,
                str(
                    Path(__file__).resolve().parent.parent
                    / "mythril_agent_skills/shared/plan/plan_lint.py"
                ),
                *args,
            ],
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
        )

    def test_match_exits_0(self, tmp_path: Path):
        docs = _docs_dir_with(tmp_path, {"feat/dark-mode": PLAN_OK})
        result = self._run("--find", "src/preferences/dark_mode.py", str(docs))
        assert result.returncode == 0
        assert result.stdout.startswith("STATUS=MATCH")
        assert "CODEMAP:" in result.stdout

    def test_no_match_exits_1_and_tells_the_agent_to_ask(self, tmp_path: Path):
        docs = _docs_dir_with(tmp_path, {"feat/dark-mode": PLAN_OK})
        result = self._run("--find", "src/unrelated/thing.py", str(docs))
        assert result.returncode == 1
        assert "STATUS=NOMATCH" in result.stdout
        assert "never edit code silently" in result.stdout

    def test_discovery_from_the_workspace_root(self, tmp_path: Path):
        docs = _docs_dir_with(tmp_path, {"feat/dark-mode": PLAN_OK})
        (tmp_path / "fullstack.json").write_text(
            json.dumps({"docs_dir": "central-docs"}), encoding="utf-8"
        )
        result = self._run("--find", "ThemePreference", cwd=tmp_path)
        assert result.returncode == 0
        assert f"DOCS_DIR={docs}" in result.stdout

    def test_bad_docs_dir_exits_2(self, tmp_path: Path):
        result = self._run("--find", "x", str(tmp_path / "nope"))
        assert result.returncode == 2

    def test_lint_mode_still_requires_work_dir(self):
        result = self._run("--quiet")
        assert result.returncode == 2
