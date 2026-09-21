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
    parse_evidence_rows,
    parse_plan_review_rounds,
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
        review = REVIEW_OK + "\n## 方案审查 — 第 3 轮 — 2026-01-02\n\n### 结论\nPASS\n"
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
