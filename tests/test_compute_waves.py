"""Tests for the shared dependency-wave calculator (compute_waves.py).

Covers plan.md table parsing (English and Chinese headers), wave
layering semantics, structural validation (cycles, unknown/self/duplicate
dependencies), and the CLI contract used by the fullstack skills.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from mythril_agent_skills.shared.waves.compute_waves import (
    compute_waves,
    parse_plan_tables,
)

CANONICAL = (
    Path(__file__).resolve().parent.parent
    / "mythril_agent_skills"
    / "shared"
    / "waves"
    / "compute_waves.py"
)

EN_TABLE_HEADING = "## Affected Repositories (in dependency order)\n"


def _plan(table_rows: str, heading: str = EN_TABLE_HEADING) -> str:
    return (
        "# Work\n\n"
        f"{heading}\n\n"
        "| # | Repository | Branch | Changes Needed | Depends On | Priority |\n"
        "|---|-----------|--------|---------------|-----------|----------|\n"
        f"{table_rows}"
    )


class TestWaveLayering:
    def test_independent_repos_share_one_wave(self):
        plan = _plan(
            "| 1 | web | feat/A | x | — | P1 |\n"
            "| 2 | android | feat/B | y | none | P1 |\n"
        )
        assert compute_waves(plan) == {
            "REPOS": "2",
            "WAVES": "1",
            "WAVE_1": "web,android",
        }

    def test_linear_chain_one_repo_per_wave(self):
        plan = _plan(
            "| 1 | lib | b | t | - | P0 |\n"
            "| 2 | api | b | t | lib | P0 |\n"
            "| 3 | web | b | t | api | P0 |\n"
        )
        result = compute_waves(plan)
        assert result["WAVES"] == "3"
        assert result["WAVE_1"] == "lib"
        assert result["WAVE_2"] == "api"
        assert result["WAVE_3"] == "web"

    def test_fan_out_after_shared_upstream(self):
        plan = _plan(
            "| 1 | shared-lib | b | types | — | P0 |\n"
            "| 2 | api | b | endpoint | shared-lib | P0 |\n"
            "| 3 | web | b | screen | api, `shared-lib` | P1 |\n"
            "| 4 | android/ | b | screen | api | P1 |\n"
        )
        result = compute_waves(plan)
        assert result == {
            "REPOS": "4",
            "WAVES": "3",
            "WAVE_1": "shared-lib",
            "WAVE_2": "api",
            "WAVE_3": "web,android",
        }

    def test_multiple_roots_start_together(self):
        plan = _plan(
            "| 1 | lib-a | b | t | | P0 |\n"
            "| 2 | lib-b | b | t | — | P0 |\n"
            "| 3 | app | b | t | lib-a, lib-b | P0 |\n"
        )
        result = compute_waves(plan)
        assert result["WAVE_1"] == "lib-a,lib-b"
        assert result["WAVE_2"] == "app"

    def test_within_wave_order_follows_declaration(self):
        plan = _plan(
            "| 2 | zeta | b | t | — | P0 |\n"
            "| 1 | alpha | b | t | — | P0 |\n"
        )
        assert compute_waves(plan)["WAVE_1"] == "zeta,alpha"


class TestParsing:
    def test_chinese_headers_and_no_dep_tokens(self):
        plan = (
            "# 工作\n\n## 涉及仓库（按依赖顺序）\n\n"
            "| # | 仓库 | 分支 | 变更内容 | 依赖 | 优先级 |\n"
            "|---|------|------|---------|------|--------|\n"
            "| 1 | shared-lib | feat/A | 类型 | 无 | P0 |\n"
            "| 2 | api | feat/B | 接口 | shared-lib | P0 |\n"
        )
        assert compute_waves(plan)["WAVES"] == "2"

    def test_trailing_slash_normalized_matches_dep_reference(self):
        graph = parse_plan_tables(
            _plan("| 1 | api/ | b | t | — | P0 |\n| 2 | web | b | t | api | P0 |\n")
        )
        assert graph == {"api": [], "web": ["api"]}
        assert compute_waves(_plan(
            "| 1 | api/ | b | t | — | P0 |\n| 2 | web | b | t | api | P0 |\n"
        ))["WAVES"] == "2"

    def test_column_order_is_discovered_from_header(self):
        # Depends On column placed before Repository.
        plan = (
            f"{EN_TABLE_HEADING}\n\n"
            "| Depends On | Repository |\n|---|---|\n"
            "| base | consumer |\n| — | base |\n"
        )
        result = compute_waves(plan)
        assert result["WAVE_1"] == "base"
        assert result["WAVE_2"] == "consumer"

    def test_table_without_heading_found_by_header_scan(self):
        plan = (
            "# Work\n\nSome prose.\n\n"
            "| Repository | Branch | Depends On |\n"
            "|---|---|---|\n"
            "| solo | b | — |\n"
        )
        assert compute_waves(plan)["REPOS"] == "1"

    def test_unrelated_later_table_is_not_captured(self):
        plan = (
            f"{EN_TABLE_HEADING}\n\n"
            "| Repository | Branch | Changes Needed | Depends On |\n"
            "|---|---|---|---|\n"
            "| real | b | t | — |\n"
            "\n## Risks\n\n"
            "| Risk | Mitigation |\n|---|---|\n"
            "| thing | other |\n"
        )
        assert compute_waves(plan)["REPOS"] == "1"


class TestStructuralErrors:
    def test_cycle_lists_remaining_repos(self):
        # Cycle detection lives in the layering step, so exercise the
        # full pipeline (parse + validate + layer).
        with pytest.raises(ValueError, match=r"CYCLE_REPOS="):
            compute_waves(
                _plan(
                    "| 1 | a | b | t | b | P0 |\n"
                    "| 2 | b | b | t | a | P0 |\n"
                )
            )

    def test_unknown_dependency_names_repo_and_ghost(self):
        with pytest.raises(ValueError, match=r"ERROR_UNKNOWN_DEP=web: ghost"):
            parse_plan_tables(_plan("| 1 | web | b | t | ghost | P0 |\n"))

    def test_self_dependency_rejected(self):
        with pytest.raises(ValueError, match=r"ERROR_SELF_DEPENDENCY=api"):
            parse_plan_tables(_plan("| 1 | api | b | t | api | P0 |\n"))

    def test_duplicate_repo_row_rejected(self):
        with pytest.raises(ValueError, match=r"ERROR_DUPLICATE_REPO=web"):
            parse_plan_tables(
                _plan(
                    "| 1 | web | b | t | — | P0 |\n"
                    "| 2 | web | b | t | — | P1 |\n"
                )
            )

    def test_missing_table_rejected(self):
        with pytest.raises(ValueError, match=r"ERROR_NO_REPOS_TABLE"):
            parse_plan_tables("# Work\n\nNo tables here.\n")

    def test_all_problems_reported_together(self):
        with pytest.raises(ValueError) as excinfo:
            parse_plan_tables(
                _plan(
                    "| 1 | web | b | t | ghost | P0 |\n"
                    "| 2 | api | b | t | api | P0 |\n"
                )
            )
        message = str(excinfo.value)
        assert "ERROR_UNKNOWN_DEP=web: ghost" in message
        assert "ERROR_SELF_DEPENDENCY=api" in message


class TestCli:
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CANONICAL), *args],
            capture_output=True,
            text=True,
        )

    def test_success_prints_key_value_lines(self, tmp_path):
        workdir = tmp_path / "add-dark-mode"
        workdir.mkdir()
        (workdir / "plan.md").write_text(
            _plan(
                "| 1 | lib | b | t | — | P0 |\n"
                "| 2 | app | b | t | lib | P0 |\n"
            ),
            encoding="utf-8",
        )
        proc = self._run(str(workdir))
        assert proc.returncode == 0
        assert "REPOS=2" in proc.stdout.splitlines()
        assert "WAVE_2=app" in proc.stdout.splitlines()

    def test_plan_file_path_accepted_directly(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(_plan("| 1 | solo | b | t | — | P0 |\n"), encoding="utf-8")
        proc = self._run(str(plan_file))
        assert proc.returncode == 0
        assert "WAVES=1" in proc.stdout

    def test_structural_error_exits_one_with_error_line(self, tmp_path):
        workdir = tmp_path / "broken"
        workdir.mkdir()
        (workdir / "plan.md").write_text(
            _plan("| 1 | a | b | t | a | P0 |\n"), encoding="utf-8"
        )
        proc = self._run(str(workdir))
        assert proc.returncode == 1
        assert "ERROR_SELF_DEPENDENCY=a" in proc.stdout

    def test_missing_target_exits_two(self, tmp_path):
        assert self._run(str(tmp_path / "nope")).returncode == 2

    def test_no_args_exits_two(self):
        assert self._run().returncode == 2
