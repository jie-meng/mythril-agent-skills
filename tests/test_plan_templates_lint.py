"""Run the shipped work-item templates through plan_lint.

The templates and the linter are edited separately, so they drift: a
template that writes `Criterion 1` where the linter expects `SC1` turns a
blocking check into a silent one. These tests assemble a minimal work
directory from the bundled template files — filling only the `<...>`
slots a writer must fill — and require the linter to accept it, then
break the chain the templates promise and require the linter to notice.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from mythril_agent_skills.shared.plan.plan_lint import lint_work_dir

REFERENCES = (
    Path(__file__).resolve().parent.parent
    / "mythril_agent_skills"
    / "skills"
    / "fullstack-propose"
    / "references"
)
FENCE_RE = re.compile(r"^```markdown\n(.*?)^```$", re.MULTILINE | re.DOTALL)


def _blocks(name: str) -> list[str]:
    """Return the ```markdown blocks of a bundled template file."""
    return FENCE_RE.findall((REFERENCES / name).read_text(encoding="utf-8"))


def _section(text: str, heading: str) -> str:
    """Return one `## ` section of a template, heading included."""
    start = text.index(heading)
    following = text.find("\n## ", start + len(heading))
    return text[start:] if following == -1 else text[start:following] + "\n"


def _fill_round(block: str) -> str:
    """Fill the slots of a plan-review round the way a reviewer would."""
    return (
        block.replace("<N>", "1")
        .replace("<date>", "2026-01-01")
        .replace(
            "<PASS | PASS_WITH_RISKS | NEEDS_FIXES | NEEDS_USER_DECISION>",
            "PASS",
        )
    )


def _template_work_dir(tmp_path: Path, lang: str) -> Path:
    """Assemble analysis.md / plan.md / review.md from the shipped templates."""
    plan = _blocks(f"template-plan.{lang}.md")[0]
    analysis_heading = "## Original Requirements" if lang == "en" else "## 需求原文"
    analysis = _section(
        (REFERENCES / f"template-analysis.{lang}.md").read_text(encoding="utf-8"),
        analysis_heading,
    )
    # The coverage-matrix example cites REQ1–REQ3; declare the third ask.
    analysis += '\n- **REQ3** "a third ask" — user prompt\n'
    header, plan_round = _blocks(f"template-review.{lang}.md")[:2]
    review = header + "\n" + _fill_round(plan_round)

    (tmp_path / "plan.md").write_text(plan, encoding="utf-8")
    (tmp_path / "analysis.md").write_text(analysis, encoding="utf-8")
    (tmp_path / "review.md").write_text(review, encoding="utf-8")
    return tmp_path


def _errors(work_dir: Path) -> list[str]:
    return [f.message for f in lint_work_dir(work_dir) if f.level == "ERROR"]


@pytest.mark.parametrize("lang", ["en", "zh"])
class TestShippedTemplatesLint:
    def test_template_work_dir_passes(self, tmp_path: Path, lang: str):
        assert _errors(_template_work_dir(tmp_path, lang)) == []

    def test_template_criteria_reach_the_evidence_check(
        self, tmp_path: Path, lang: str
    ):
        """Dropping an Evidence row must fail — the check is live, not inert."""
        work_dir = _template_work_dir(tmp_path, lang)
        review = work_dir / "review.md"
        text = review.read_text(encoding="utf-8")
        row = next(line for line in text.splitlines() if line.startswith("| SC3 "))
        review.write_text(text.replace(row + "\n", ""), encoding="utf-8")
        assert any("missing a row for: SC3" in m for m in _errors(work_dir))

    def test_template_tasks_reach_the_task_check(self, tmp_path: Path, lang: str):
        """The coverage matrix cites task ids the plan template declares."""
        work_dir = _template_work_dir(tmp_path, lang)
        plan = work_dir / "plan.md"
        text = plan.read_text(encoding="utf-8")
        plan.write_text(text.replace("**T3**", "**T9**"), encoding="utf-8")
        assert any("T3" in m and "not in plan.md" in m for m in _errors(work_dir))

    def test_template_records_the_tier(self, tmp_path: Path, lang: str):
        """fullstack-apply reads the tier from the summary status line."""
        plan = _blocks(f"template-plan.{lang}.md")[0]
        status = next(
            line
            for line in plan.splitlines()
            if line.startswith(("**Status**", "**状态**"))
        )
        assert "lean | full" in status
