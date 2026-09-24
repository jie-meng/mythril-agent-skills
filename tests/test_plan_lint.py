"""Tests for the shared work-tracking document linter (plan_lint.py).

Covers Success-Criteria ↔ Evidence-row reconciliation, plan-review closure
and round numbering, task-id references, placeholder detection, and the
CLI contract used by the fullstack skills.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from mythril_agent_skills.shared.plan.plan_lint import (
    detect_verdict,
    find_placeholders,
    format_findings,
    lint_work_dir,
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


PLAN_OK = """# Plan: demo

## 成功标准

- [ ] SC1 works
- [ ] SC2 also works

## 实现计划

- [ ] T1 do the thing
"""

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
