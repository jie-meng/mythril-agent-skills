"""Tests for fullstack-explore: SKILL contract.

Its scripts/ holds only bundled shared assets (check_workspace.py,
graphify_check.py, repo_skills.py), covered by tests/test_repo_skills.py,
tests/skills/test_fullstack_apply.py and the shared-asset drift test.
"""

from __future__ import annotations

from pathlib import Path

SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / "mythril_agent_skills"
    / "skills"
    / "fullstack-explore"
)


def _parts() -> tuple[str, str]:
    content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = content.split("---", 2)
    return frontmatter, body


def test_description_claims_precedence_over_graphify():
    frontmatter, _ = _parts()
    assert "rather than graphify" in frontmatter
    assert "fullstack.json" in frontmatter


def test_body_explains_when_graphify_is_used_directly():
    _, body = _parts()
    assert "## Relationship to the graphify Skill" in body
    assert "only to build or" in body


def test_every_referenced_script_is_bundled():
    _, body = _parts()
    for script in ("check_workspace.py", "graphify_check.py", "repo_skills.py"):
        assert f"SKILL_PATH/scripts/{script}" in body
        assert (SKILL_DIR / "scripts" / script).is_file()
