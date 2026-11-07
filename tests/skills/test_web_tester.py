"""Tests for web-tester skill structure.

The web-tester runtime is JavaScript (Playwright) and cannot be imported by
pytest — see the documented deviation in the work item plan (JS pure-function
tests live in the skill's lib.test.mjs, run via `node --test`). This file
therefore asserts the skill's structure and registration invariants.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "mythril_agent_skills" / "skills" / "web-tester"


class TestSkillStructure:
    """SKILL.md frontmatter and required sections."""

    @pytest.fixture(autouse=True)
    def _skill_md(self):
        path = SKILL_DIR / "SKILL.md"
        assert path.is_file(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---"), "SKILL.md must start with YAML frontmatter"
        self.text = text
        frontmatter = text.split("---", 2)[1]
        self.frontmatter = frontmatter

    def test_frontmatter_fields(self):
        assert "name: web-tester" in self.frontmatter
        assert "license: Apache-2.0" in self.frontmatter
        assert "description:" in self.frontmatter

    def test_description_under_1024_chars(self):
        # Mirrors scripts/validate-skill-descriptions.py for this one skill.
        lines = self.frontmatter.splitlines()
        desc_lines = []
        in_desc = False
        for line in lines:
            if line.startswith("description:"):
                in_desc = True
                continue
            if in_desc:
                if line.startswith("  ") or line.strip() == "":
                    desc_lines.append(line.strip())
                else:
                    break
        desc = " ".join(desc_lines)
        assert 0 < len(desc) <= 1024, f"description length {len(desc)}"

    def test_capability_ladder_documented(self):
        assert "Capability Detection" in self.text
        assert "@playwright/mcp" in self.text

    def test_three_profiles_documented(self):
        assert "Profile: desktop" in self.text
        assert "Profile: mobile" in self.text
        assert "Profile: canvas" in self.text

    def test_test_loop_and_report_documented(self):
        assert "Universal Test Loop" in self.text
        assert "Report Format" in self.text


class TestSkillScripts:
    """Scripts directory contents."""

    def test_setup_sh_executable(self):
        path = SKILL_DIR / "scripts" / "setup.sh"
        assert path.is_file()
        import os

        assert os.access(path, os.X_OK), "setup.sh must be executable"

    def test_lib_mjs_exports_expected_api(self):
        text = (SKILL_DIR / "scripts" / "lib.mjs").read_text(encoding="utf-8")
        for symbol in [
            "DEVICES",
            "lookupDevice",
            "createSession",
            "tap",
            "swipe",
            "longPress",
            "saveShot",
            "closeSession",
        ]:
            assert f"export const {symbol}" in text or f"export async function {symbol}" in text or f"export function {symbol}" in text

    def test_lib_test_mjs_exists(self):
        assert (SKILL_DIR / "scripts" / "lib.test.mjs").is_file()

    def test_examples_exist(self):
        examples = SKILL_DIR / "examples"
        assert (examples / "example-mobile-tap.mjs").is_file()
        assert (examples / "example-canvas-swipe.mjs").is_file()


class TestMarketplaceRegistration:
    """Plugin wrapper symlink and marketplace entry (T6/T7 invariants)."""

    def test_plugin_wrapper_symlink_resolves_to_skill(self):
        link = REPO_ROOT / "plugins" / "web-tester" / "skills" / "web-tester"
        assert link.is_symlink(), f"missing symlink {link}"
        assert link.resolve() == SKILL_DIR.resolve()

    def test_canonical_marketplace_has_entry(self):
        catalog = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        entries = [p for p in catalog["plugins"] if p["name"] == "web-tester"]
        assert len(entries) == 1
        entry = entries[0]
        assert entry["source"] == "./plugins/web-tester"
        assert entry["strict"] is False
