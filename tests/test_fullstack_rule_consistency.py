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
