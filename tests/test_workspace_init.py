"""Tests for fullstack-init's AGENTS.md template and incremental merge.

The Repo Skills convention has to reach two populations: new workspaces
(generated from the template) and existing workspaces (merged on re-init).
The merge only appends bullets whose bold title is new, so these tests
pin that path — plus the migration of the legacy `SKILL_PATH` placeholder,
which cannot run from the workspace root.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

INIT_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "mythril_agent_skills"
    / "skills"
    / "fullstack-init"
    / "scripts"
    / "workspace_init.py"
)


def _load_init_module():
    spec = importlib.util.spec_from_file_location(
        "_workspace_init_under_test", INIT_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_workspace_init_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def init_module():
    return _load_init_module()


def _installed_home(tmp_path: Path) -> Path:
    scripts = tmp_path / ".agents" / "skills" / "fullstack-init" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "repo_skills.py").write_text("", encoding="utf-8")
    (scripts / "graphify_check.py").write_text("", encoding="utf-8")
    return tmp_path


def _generated(init_module, home: Path) -> str:
    return init_module.generate_agents_md("ws", "| x |", "docs", home=home)


def test_generated_agents_md_carries_repo_skills_bullet(
    init_module, tmp_path: Path
):
    text = _generated(init_module, _installed_home(tmp_path))
    assert "**Repo Skills**" in text
    assert (
        "~/.agents/skills/fullstack-init/scripts/repo_skills.py <repo>"
        in text
    )


def test_generated_agents_md_has_no_unresolved_placeholder(
    init_module, tmp_path: Path
):
    text = _generated(init_module, _installed_home(tmp_path))
    assert "SKILL_PATH" not in text
    assert (
        "~/.agents/skills/fullstack-init/scripts/graphify_check.py <repo-path>"
        in text
    )


def test_old_workspace_gets_the_bullet_on_merge(init_module, tmp_path: Path):
    home = _installed_home(tmp_path)
    existing = (
        "# ws\n\n## Workspace Conventions\n\n"
        "- **My Own Rule**: hand-written here\n"
        "- **Knowledge Graph (graphify)**: old shipped text\n"
        "  - **Check for graphify-out/**: Run\n"
        "    `python3 SKILL_PATH/scripts/graphify_check.py <repo-path>` to check.\n"
    )
    merged = init_module.merge_agents_md(existing, _generated(init_module, home))
    assert merged.count("**Repo Skills**") == 1
    assert "- **My Own Rule**: hand-written here" in merged
    # A shipped bullet is replaced, not preserved: its command is the
    # skill's, and the old copy carried a placeholder no agent can run.
    assert "old shipped text" not in merged
    assert (
        "~/.agents/skills/fullstack-init/scripts/graphify_check.py <repo-path>"
        in merged
    )
    assert merged.count("**Check for graphify-out/**") == 1


def test_shipped_bullet_is_refreshed_when_the_template_changes(
    init_module, tmp_path: Path
):
    """The case this rule exists for: a workspace that already carries the
    bullet must receive the revised text, not keep the version it was
    first written with."""
    home = _installed_home(tmp_path)
    shipped_once = _generated(init_module, home)
    existing = _extract_conventions(init_module, shipped_once)
    revised = shipped_once.replace(
        "Do not bulk-load non-matching skills.",
        "Do not bulk-load non-matching skills. NEW SHIPPED CLAUSE.",
    )
    merged = init_module.merge_agents_md(existing, revised)
    assert "NEW SHIPPED CLAUSE" in merged
    assert merged.count("**Repo Skills**") == 1
    assert "Do not bulk-load" in merged


def test_user_worded_convention_is_never_replaced(
    init_module, tmp_path: Path
):
    home = _installed_home(tmp_path)
    existing = (
        "# ws\n\n## Workspace Conventions\n\n"
        "- **Scripts**: our automation lives in `ops/`, do not move it\n"
    )
    merged = init_module.merge_agents_md(existing, _generated(init_module, home))
    assert "our automation lives in `ops/`" in merged
    assert merged.count("- **Scripts**:") == 1


def test_re_init_after_a_refresh_changes_nothing(init_module, tmp_path: Path):
    home = _installed_home(tmp_path)
    generated = _generated(init_module, home)
    once = init_module.merge_agents_md(
        "# ws\n\n## Workspace Conventions\n\n- **Existing**: x\n", generated
    )
    twice = init_module.merge_agents_md(once, generated)
    assert once == twice


def _extract_conventions(init_module, text: str) -> str:
    """Return an AGENTS.md holding only the generated conventions section."""
    body = text[text.index("## Workspace Conventions") :]
    if "\n## " in body[len("## Workspace Conventions") :]:
        body = body[: body.index("\n## ", len("## Workspace Conventions"))]
    return "# ws\n\n" + body.rstrip() + "\n"


def test_repeated_reinit_does_not_duplicate_the_bullet(
    init_module, tmp_path: Path
):
    home = _installed_home(tmp_path)
    generated = _generated(init_module, home)
    once = init_module.merge_agents_md(
        "# ws\n\n## Workspace Conventions\n\n- **Existing**: x\n", generated
    )
    twice = init_module.merge_agents_md(once, generated)
    assert twice.count("**Repo Skills**") == 1


def test_legacy_graphify_placeholder_is_upgraded(init_module, tmp_path: Path):
    home = _installed_home(tmp_path)
    old = (
        "Run `python3 SKILL_PATH/scripts/graphify_check.py <repo-path>` "
        "to check.\n"
    )
    upgraded = init_module.upgrade_legacy_skill_commands(old, home=home)
    assert "SKILL_PATH" not in upgraded
    assert (
        "~/.agents/skills/fullstack-init/scripts/graphify_check.py <repo-path>"
        in upgraded
    )


def test_upgrade_does_not_duplicate_the_argument(
    init_module, tmp_path: Path
):
    """`graphify_check.py` takes exactly one path — a second argument makes
    the command exit 2, so the migrated line must carry one."""
    home = _installed_home(tmp_path)
    old = "`python3 SKILL_PATH/scripts/graphify_check.py <repo-path>` to check\n"
    upgraded = init_module.upgrade_legacy_skill_commands(old, home=home)
    assert upgraded.count("<repo-path>") == 1


def test_placeholder_is_left_alone_without_an_install(
    init_module, tmp_path: Path
):
    old = "Run `python3 SKILL_PATH/scripts/graphify_check.py <repo-path>` now.\n"
    assert init_module.upgrade_legacy_skill_commands(old, home=tmp_path) == old


def test_doubled_argument_from_an_earlier_migration_is_repaired(
    init_module, tmp_path: Path
):
    """The first migration left `<repo-path> <repo-path>`, which the script
    rejects with exit 2. Repaired even with no install to resolve."""
    broken = (
        "`python3 ~/.agents/skills/fullstack-init/scripts/"
        "graphify_check.py <repo-path> <repo-path>` to check\n"
    )
    repaired = init_module.upgrade_legacy_skill_commands(broken, home=tmp_path)
    assert repaired.count("<repo-path>") == 1
    assert "SKILL_PATH" not in repaired
