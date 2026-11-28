"""Cross-file consistency of the fullstack family's routing rules.

The quick-fix conditions and the lean-tier conditions are stated in several
places — the canonical reference plus short summaries in other skills and in
the generated workspace AGENTS.md. Prose duplication drifts silently; these
tests pin the load-bearing terms so a change made in one place and forgotten
in another fails CI instead of reaching a workspace.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parent.parent / "mythril_agent_skills" / "skills"

QUICK_FIX_TERMS = ("root cause", "one repo", "contract", "schema", "small")


def _read(relative: str) -> str:
    return (SKILLS / relative).read_text(encoding="utf-8").lower()


def _workspace_agents_md() -> str:
    from workspace_init import generate_agents_md

    return generate_agents_md("proj", "| t |", "docs").lower()


class TestQuickFixConditions:
    """Every place that routes to the quick fix names all of its conditions."""

    @pytest.mark.parametrize(
        "relative",
        [
            "fullstack-apply/references/quick-fix.md",
            "fullstack-apply/SKILL.md",
            "fullstack-propose/SKILL.md",
            "fullstack-explore/SKILL.md",
        ],
    )
    def test_skill_files_name_every_condition(self, relative: str):
        text = _read(relative)
        missing = [term for term in QUICK_FIX_TERMS if term not in text]
        assert not missing, f"{relative} omits quick-fix terms: {missing}"

    def test_workspace_agents_md_names_every_condition(self):
        text = _workspace_agents_md()
        missing = [term for term in QUICK_FIX_TERMS if term not in text]
        assert not missing, f"workspace AGENTS.md omits quick-fix terms: {missing}"

    def test_active_owner_blocks_quick_fix_everywhere(self):
        for relative in (
            "fullstack-apply/references/quick-fix.md",
            "fullstack-propose/SKILL.md",
        ):
            assert "active work item" in _read(relative), relative
        assert "active work item owns" in _workspace_agents_md()

    def test_summaries_point_at_the_canonical_reference(self):
        for relative in ("fullstack-propose/SKILL.md", "fullstack-apply/SKILL.md"):
            assert "references/quick-fix.md" in _read(relative), relative


class TestLeanTierConditions:
    """Propose decides the tier and apply re-checks it — same conditions."""

    LEAN_TERMS = ("single repo", "cross-repo contract", "schema", "migration")

    @pytest.mark.parametrize(
        "relative", ["fullstack-propose/SKILL.md", "fullstack-apply/SKILL.md"]
    )
    def test_both_skills_state_the_same_lean_conditions(self, relative: str):
        text = _read(relative)
        missing = [term for term in self.LEAN_TERMS if term not in text]
        assert not missing, f"{relative} omits lean-tier terms: {missing}"
        assert "external" in text and "api" in text, relative


class TestContextBudgetRules:
    """Round 4 rules that keep agent contexts short; pinned against drift."""

    def test_apply_sends_fix_rounds_to_a_fresh_developer(self):
        text = _read("fullstack-apply/references/full-tier.md")
        assert "fix rounds go to a fresh developer" in text
        assert "one developer per phase" in text
        assert "back to that repo's developer" not in text
        assert "fix rounds go to\na fresh developer" in _read(
            "fullstack-apply/SKILL.md"
        )

    def test_apply_skill_points_at_the_full_tier_reference(self):
        assert "references/full-tier.md" in _read("fullstack-apply/SKILL.md")

    def test_developer_reads_its_brief_and_uses_real_paths(self):
        text = _read("fullstack-init/agents/developer.md")
        assert "read your brief, not the whole plan" in text
        assert "evidence tests use the real path" in text
        assert "differential check" in text

    def test_code_reviewer_rejects_mocked_evidence(self):
        text = _read("fullstack-init/agents/code-reviewer.md")
        assert "does not prove the criterion" in text

    @pytest.mark.parametrize("lang", ["en", "zh"])
    def test_analysis_template_has_no_risk_table(self, lang: str):
        text = _read(f"fullstack-propose/references/template-analysis.{lang}.md")
        assert "## risks & mitigations" not in text
        assert "## 风险与应对" not in text


class TestApplyFinalizeOrder:
    """Nothing leaves the machine — push or PR — before the finalize gates."""

    def test_finalize_gates_precede_pull_requests(self):
        text = _read("fullstack-apply/SKILL.md")
        gates = text.index("## step 6 — finalize the documents")
        prs = text.index("## step 7 — push, pull requests, report")
        assert gates < prs
        assert "plan_lint.py" in text[gates:prs]
        assert "pr-creation.md" in text[prs:]
        assert "pr-creation.md" not in text[gates:prs]

    def test_generic_fix_triggers_are_scoped_to_a_workspace(self):
        text = _read("fullstack-apply/SKILL.md")
        description = text.split("---")[1]
        assert "inside a fullstack" in description
        assert description.index("inside a fullstack") < description.index(
            "fix this"
        )
