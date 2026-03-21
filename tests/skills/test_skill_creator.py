"""Tests for skill-creator skill scripts.

Covers:
- quick_validate: validate_skill with temp directories
- utils: parse_skill_md with temp files
- aggregate_benchmark: calculate_stats, aggregate_results, generate_markdown
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest


# ── quick_validate ─────────────────────────────────────────────────────────────


class TestValidateSkill:
    @pytest.fixture(autouse=True)
    def _import(self):
        from quick_validate import validate_skill
        self.validate = validate_skill

    def _write_skill(self, tmp_path: Path, content: str) -> Path:
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        return skill_dir

    def test_valid_skill(self, tmp_path):
        content = "---\nname: test-skill\ndescription: A test skill.\n---\n\n# Test\n"
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is True
        assert "valid" in msg.lower()

    def test_missing_skill_md(self, tmp_path):
        skill_dir = tmp_path / "empty-skill"
        skill_dir.mkdir()
        ok, msg = self.validate(skill_dir)
        assert ok is False
        assert "SKILL.md not found" in msg

    def test_no_frontmatter(self, tmp_path):
        content = "# Just a heading\nNo frontmatter here."
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is False
        assert "frontmatter" in msg.lower()

    def test_missing_name(self, tmp_path):
        content = "---\ndescription: Has description but no name.\n---\n"
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is False
        assert "name" in msg.lower()

    def test_missing_description(self, tmp_path):
        content = "---\nname: my-skill\n---\n"
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is False
        assert "description" in msg.lower()

    def test_invalid_name_uppercase(self, tmp_path):
        content = "---\nname: MySkill\ndescription: test\n---\n"
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is False
        assert "kebab-case" in msg.lower()

    def test_name_with_consecutive_hyphens(self, tmp_path):
        content = "---\nname: my--skill\ndescription: test\n---\n"
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is False
        assert "consecutive" in msg.lower()

    def test_name_starting_with_hyphen(self, tmp_path):
        content = "---\nname: -my-skill\ndescription: test\n---\n"
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is False

    def test_description_too_long(self, tmp_path):
        desc = "A" * 1025
        content = f"---\nname: my-skill\ndescription: {desc}\n---\n"
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is False
        assert "1024" in msg

    def test_description_with_angle_brackets(self, tmp_path):
        content = "---\nname: my-skill\ndescription: Use <tool> for work.\n---\n"
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is False
        assert "angle" in msg.lower()

    def test_unexpected_frontmatter_key(self, tmp_path):
        content = "---\nname: my-skill\ndescription: test\nauthor: someone\n---\n"
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is False
        assert "Unexpected" in msg

    def test_optional_fields_accepted(self, tmp_path):
        content = "---\nname: my-skill\ndescription: test\nlicense: MIT\n---\n"
        ok, msg = self.validate(self._write_skill(tmp_path, content))
        assert ok is True


# ── utils.parse_skill_md ───────────────────────────────────────────────────────


class TestParseSkillMd:
    @pytest.fixture(autouse=True)
    def _import(self):
        from utils import parse_skill_md
        self.parse = parse_skill_md

    def _write_skill(self, tmp_path: Path, content: str) -> Path:
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir(exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        return skill_dir

    def test_basic_parse(self, tmp_path):
        content = "---\nname: my-skill\ndescription: A description.\n---\n\n# Body\n"
        name, desc, full = self.parse(self._write_skill(tmp_path, content))
        assert name == "my-skill"
        assert desc == "A description."
        assert "# Body" in full

    def test_multiline_description_folded(self, tmp_path):
        content = (
            "---\nname: my-skill\ndescription: >\n"
            "  Line one of the\n  description text.\n---\n"
        )
        name, desc, full = self.parse(self._write_skill(tmp_path, content))
        assert name == "my-skill"
        assert "Line one" in desc
        assert "description text" in desc

    def test_multiline_description_literal(self, tmp_path):
        content = (
            "---\nname: my-skill\ndescription: |\n"
            "  First line.\n  Second line.\n---\n"
        )
        name, desc, full = self.parse(self._write_skill(tmp_path, content))
        assert "First line." in desc

    def test_missing_frontmatter_raises(self, tmp_path):
        content = "# No frontmatter\nJust content."
        with pytest.raises(ValueError, match="missing frontmatter"):
            self.parse(self._write_skill(tmp_path, content))

    def test_unclosed_frontmatter_raises(self, tmp_path):
        content = "---\nname: x\ndescription: y\n"
        with pytest.raises(ValueError, match="missing frontmatter"):
            self.parse(self._write_skill(tmp_path, content))


# ── aggregate_benchmark ────────────────────────────────────────────────────────


class TestCalculateStats:
    @pytest.fixture(autouse=True)
    def _import(self):
        from aggregate_benchmark import calculate_stats
        self.stats = calculate_stats

    def test_empty_list(self):
        result = self.stats([])
        assert result == {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}

    def test_single_value(self):
        result = self.stats([1.0])
        assert result["mean"] == 1.0
        assert result["stddev"] == 0.0
        assert result["min"] == 1.0
        assert result["max"] == 1.0

    def test_multiple_values(self):
        result = self.stats([1.0, 2.0, 3.0])
        assert result["mean"] == 2.0
        assert result["min"] == 1.0
        assert result["max"] == 3.0
        assert result["stddev"] == 1.0

    def test_identical_values_zero_stddev(self):
        result = self.stats([5.0, 5.0, 5.0])
        assert result["mean"] == 5.0
        assert result["stddev"] == 0.0


class TestAggregateResults:
    @pytest.fixture(autouse=True)
    def _import(self):
        from aggregate_benchmark import aggregate_results
        self.aggregate = aggregate_results

    def test_single_config(self):
        results = {
            "with_skill": [
                {"pass_rate": 0.8, "time_seconds": 10.0, "tokens": 100},
                {"pass_rate": 1.0, "time_seconds": 12.0, "tokens": 120},
            ],
        }
        summary = self.aggregate(results)
        assert "with_skill" in summary
        assert "delta" in summary
        assert summary["with_skill"]["pass_rate"]["mean"] == 0.9

    def test_two_configs_delta(self):
        results = {
            "with_skill": [
                {"pass_rate": 1.0, "time_seconds": 10.0, "tokens": 100},
            ],
            "without_skill": [
                {"pass_rate": 0.5, "time_seconds": 8.0, "tokens": 80},
            ],
        }
        summary = self.aggregate(results)
        assert summary["delta"]["pass_rate"] == "+0.50"

    def test_empty_config(self):
        results = {"empty": []}
        summary = self.aggregate(results)
        assert summary["empty"]["pass_rate"]["mean"] == 0.0


class TestGenerateMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from aggregate_benchmark import generate_markdown
        self.generate = generate_markdown

    def test_basic_markdown(self):
        benchmark = {
            "metadata": {
                "skill_name": "test-skill",
                "executor_model": "claude",
                "timestamp": "2025-01-01T00:00:00Z",
                "evals_run": [1, 2],
                "runs_per_configuration": 3,
            },
            "run_summary": {
                "with_skill": {
                    "pass_rate": {"mean": 0.9, "stddev": 0.1, "min": 0.8, "max": 1.0},
                    "time_seconds": {"mean": 10.0, "stddev": 2.0, "min": 8.0, "max": 12.0},
                    "tokens": {"mean": 100, "stddev": 10, "min": 90, "max": 110},
                },
                "without_skill": {
                    "pass_rate": {"mean": 0.6, "stddev": 0.2, "min": 0.4, "max": 0.8},
                    "time_seconds": {"mean": 8.0, "stddev": 1.0, "min": 7.0, "max": 9.0},
                    "tokens": {"mean": 80, "stddev": 5, "min": 75, "max": 85},
                },
                "delta": {
                    "pass_rate": "+0.30",
                    "time_seconds": "+2.0",
                    "tokens": "+20",
                },
            },
            "notes": [],
        }
        md = self.generate(benchmark)
        assert "# Skill Benchmark: test-skill" in md
        assert "With Skill" in md
        assert "Without Skill" in md
        assert "Pass Rate" in md
        assert "90%" in md
