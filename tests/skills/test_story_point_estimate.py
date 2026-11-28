"""Tests for story-point-estimate skill scripts."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "mythril_agent_skills"
    / "skills"
    / "story-point-estimate"
    / "scripts"
    / "generate_report.py"
)


# ---------------------------------------------------------------------------
# Tiny evaluator for the formula shapes generate_report.py writes, so tests
# can check that totals are wired to the right columns (no Excel needed).
# ---------------------------------------------------------------------------

_SUMIF_RE = re.compile(
    r"^SUMIF\((?P<s1>'[^']+'|\w+)!\$(?P<c1>[A-Z]+):\$[A-Z]+,"
    r"\"(?P<crit>[^\"]*)\",(?P<s2>'[^']+'|\w+)!\$(?P<c2>[A-Z]+):\$[A-Z]+\)$"
)
_SUM_RE = re.compile(r"^SUM\(([A-Z]+)(\d+):([A-Z]+)(\d+)\)$")
_REF_RE = re.compile(r"^(?:(?P<sheet>'[^']+'|\w+)!)?\$?(?P<col>[A-Z]+)\$?(?P<row>\d+)$")


def _sheet(wb, name: str):
    return wb[name.strip("'")]


def _col_values(ws, col: str) -> list:
    return [c.value for c in ws[col]]


def evaluate(wb, ws, value):
    """Evaluate a cell value (number or supported formula) to a number."""
    if not isinstance(value, str) or not value.startswith("="):
        return value
    expr = value[1:]
    m = _SUMIF_RE.match(expr)
    if m:
        crit_vals = _col_values(_sheet(wb, m["s1"]), m["c1"])
        sum_vals = _col_values(_sheet(wb, m["s2"]), m["c2"])
        return sum(
            s for c, s in zip(crit_vals, sum_vals)
            if c == m["crit"] and isinstance(s, (int, float))
        )
    m = _SUM_RE.match(expr)
    if m:
        total = 0
        for row in ws[f"{m[1]}{m[2]}:{m[3]}{m[4]}"]:
            for cell in row:
                total += evaluate(wb, ws, cell.value) or 0
        return total
    if "+" in expr:
        return sum(evaluate(wb, ws, "=" + part) for part in expr.split("+"))
    m = _REF_RE.match(expr)
    if m:
        target = _sheet(wb, m["sheet"]) if m["sheet"] else ws
        return evaluate(wb, target, target[f"{m['col']}{m['row']}"].value)
    raise AssertionError(f"unsupported formula in test evaluator: {value}")


def find_row(ws, label: str) -> int:
    for row in ws.iter_rows(min_col=1, max_col=1):
        if row[0].value == label:
            return row[0].row
    raise AssertionError(f"label {label!r} not found in {ws.title}")


def sample_data() -> dict:
    return {
        "platforms": ["设备端", "后端", "Android", "iOS"],
        "scope_summary": "定位功能",
        "key_assumptions": ["A1"],
        "confidence": "Medium",
        "estimates": [
            {
                "category": "Functional",
                "story": "设备定位",
                "points": 8,
                "platform_points": {"设备端": 5, "后端": 3, "Android": 3, "iOS": 3},
                "uncertainty": "Medium",
            },
            {
                "category": "functional",
                "story": "历史轨迹",
                "points": "5",
                "platform_points": {"后端": 3, "Android": 2, "iOS": 2},
                "uncertainty": "low",
            },
            {
                "category": "CFR",
                "area": "Security",
                "story": "鉴权",
                "points": 3,
                "platform_points": {"后端": 3},
                "uncertainty": "High",
            },
        ],
        "raid": [{"type": "Risk", "item": "GNSS", "impact": "x", "mitigation": "y"}],
        "buffers": [
            {"type": "集成联调", "pct": "10%", "points": 2, "rationale": "跨端"},
            {"type": "Ramp-up", "pct": "20%", "points": 3},
        ],
    }


@pytest.fixture
def built():
    from generate_report import build_workbook, validate_data

    data = validate_data(sample_data())
    return build_workbook(data), data


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestNormalizeCategory:
    @pytest.fixture(autouse=True)
    def _import(self):
        from generate_report import EstimateDataError, normalize_category

        self.func = normalize_category
        self.err = EstimateDataError

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Functional", "Functional"),
            (" functional ", "Functional"),
            ("功能", "Functional"),
            ("CFR", "CFR"),
            ("nfr", "CFR"),
            ("Non-Functional", "CFR"),
            ("non_functional", "CFR"),
            ("非功能", "CFR"),
        ],
    )
    def test_aliases(self, raw, expected):
        assert self.func(raw) == expected

    @pytest.mark.parametrize("raw", ["Infra", "", None, 3])
    def test_rejects_unknown(self, raw):
        with pytest.raises(self.err):
            self.func(raw)


class TestToPoints:
    @pytest.fixture(autouse=True)
    def _import(self):
        from generate_report import EstimateDataError, to_points

        self.func = to_points
        self.err = EstimateDataError

    def test_numbers_and_numeric_strings(self):
        assert self.func(5, "x") == 5
        assert self.func("8", "x") == 8
        assert self.func(" 2.5 ", "x") == 2.5
        assert self.func(3.0, "x") == 3
        assert isinstance(self.func(3.0, "x"), int)

    @pytest.mark.parametrize("raw", ["five", True, None, [1], -1])
    def test_rejects(self, raw):
        with pytest.raises(self.err):
            self.func(raw, "estimates[1]")


class TestValidateData:
    @pytest.fixture(autouse=True)
    def _import(self):
        from generate_report import EstimateDataError, validate_data

        self.func = validate_data
        self.err = EstimateDataError

    def test_normalizes_sample(self):
        out = self.func(sample_data())
        ests = out["estimates"]
        assert ests[1]["category"] == "Functional"
        assert ests[1]["points"] == 5
        assert ests[1]["uncertainty"] == "Low"
        # Missing platform keys are filled with 0
        assert ests[1]["platform_points"]["设备端"] == 0

    def test_does_not_mutate_input(self):
        raw = sample_data()
        self.func(raw)
        assert raw["estimates"][1]["points"] == "5"

    def test_collects_all_errors(self):
        raw = sample_data()
        raw["estimates"][0]["category"] = "Infra"
        raw["estimates"][1]["points"] = "lots"
        raw["estimates"][2]["platform_points"] = {"Backend": 3}
        raw["buffers"][0]["points"] = "two"
        with pytest.raises(self.err) as exc:
            self.func(raw)
        msg = str(exc.value)
        assert "Infra" in msg
        assert "lots" in msg
        assert "Backend" in msg
        assert "buffers[1]" in msg

    def test_rejects_platform_named_like_header(self):
        raw = sample_data()
        raw["platforms"] = ["Points"]
        for est in raw["estimates"]:
            est["platform_points"] = {}
        with pytest.raises(self.err):
            self.func(raw)

    def test_rejects_bad_uncertainty(self):
        raw = sample_data()
        raw["estimates"][0]["uncertainty"] = "Huge"
        with pytest.raises(self.err):
            self.func(raw)


class TestComputeTotals:
    def test_uses_combined_points_not_platform_sum(self):
        from generate_report import compute_totals, validate_data

        data = validate_data(sample_data())
        totals = compute_totals(data["estimates"], data["buffers"])
        assert totals == {
            "functional": 13,
            "cfr": 3,
            "grand": 16,
            "buffer": 5,
            "planning": 21,
        }


# ---------------------------------------------------------------------------
# Pure formula / layout helpers
# ---------------------------------------------------------------------------


class TestFormulaHelpers:
    def test_column_letter(self):
        from generate_report import column_letter

        assert column_letter(1) == "A"
        assert column_letter(26) == "Z"
        assert column_letter(27) == "AA"
        assert column_letter(53) == "BA"

    def test_sheet_ref_quotes_spaces(self):
        from generate_report import sheet_ref

        assert sheet_ref("Summary") == "Summary"
        assert sheet_ref("Platform Summary") == "'Platform Summary'"

    def test_sumif_formula(self):
        from generate_report import sumif_formula

        assert sumif_formula("CFR", "B", "N") == (
            '=SUMIF(Estimates!$B:$B,"CFR",Estimates!$N:$N)'
        )

    def test_display_width_counts_cjk_double(self):
        from generate_report import display_width

        assert display_width("abc") == 3
        assert display_width("后端") == 4

    def test_field_order_with_platforms(self):
        from generate_report import field_order

        headers = field_order(["后端", "WEB"])
        assert headers[8:10] == ["后端", "WEB"]
        assert headers[10:] == ["Points", "Rationale", "Uncertainty"]


class TestCacheDir:
    def test_darwin(self):
        from generate_report import cache_dir_for

        got = cache_dir_for("Darwin", {}, Path("/Users/u"))
        assert got == Path(
            "/Users/u/Library/Caches/mythril-skills-cache/story-point-estimate"
        )

    def test_linux_xdg(self):
        from generate_report import cache_dir_for

        got = cache_dir_for("Linux", {"XDG_CACHE_HOME": "/x"}, Path("/home/u"))
        assert got == Path("/x/mythril-skills-cache/story-point-estimate")

    def test_linux_default(self):
        from generate_report import cache_dir_for

        got = cache_dir_for("Linux", {}, Path("/home/u"))
        assert got == Path("/home/u/.cache/mythril-skills-cache/story-point-estimate")

    def test_windows(self):
        from generate_report import cache_dir_for

        got = cache_dir_for("Windows", {"LOCALAPPDATA": "/lad"}, Path("/h"))
        assert got == Path("/lad/mythril-skills-cache/story-point-estimate")


# ---------------------------------------------------------------------------
# Workbook structure
# ---------------------------------------------------------------------------


class TestEstimatesSheet:
    def test_headers_and_values(self, built):
        wb, _ = built
        ws = wb["Estimates"]
        assert ws.cell(row=1, column=9).value == "设备端"
        assert ws.cell(row=1, column=13).value == "Points"
        assert ws.cell(row=3, column=2).value == "Functional"  # normalized
        assert ws.cell(row=3, column=13).value == 5  # numeric, not "5"
        assert ws.cell(row=3, column=15).value == "Low"

    def test_no_platforms_layout(self):
        from generate_report import build_workbook, validate_data

        raw = sample_data()
        raw["platforms"] = []
        for est in raw["estimates"]:
            est.pop("platform_points")
        wb = build_workbook(validate_data(raw))
        assert wb.sheetnames == ["Estimates", "RAID", "Summary"]
        assert wb["Estimates"].cell(row=1, column=9).value == "Points"

    def test_sheet_order_with_platforms(self, built):
        wb, _ = built
        assert wb.sheetnames == ["Estimates", "Platform Summary", "RAID", "Summary"]


class TestSummaryFormulas:
    def test_totals_are_formulas(self, built):
        wb, _ = built
        ws = wb["Summary"]
        for label in (
            "Functional Stories",
            "Non-Functional (CFR)",
            "Grand Total",
            "Buffer Total",
            "Recommended Planning Estimate",
        ):
            value = ws.cell(row=find_row(ws, label), column=2).value
            assert isinstance(value, str) and value.startswith("="), label

    def test_formulas_evaluate_to_combined_totals(self, built):
        wb, _ = built
        ws = wb["Summary"]

        def val(label):
            return evaluate(wb, ws, ws.cell(row=find_row(ws, label), column=2).value)

        assert val("Functional Stories") == 13
        assert val("Non-Functional (CFR)") == 3
        assert val("Grand Total") == 16
        assert val("Buffer Total") == 5
        assert val("Recommended Planning Estimate") == 21
        assert val("High") == 3
        assert val("Low") == 5

    def test_formulas_follow_edits(self, built):
        """Editing a point in Estimates changes the evaluated totals."""
        wb, _ = built
        wb["Estimates"].cell(row=2, column=13).value = 13  # 8 -> 13
        ws = wb["Summary"]
        row = find_row(ws, "Recommended Planning Estimate")
        assert evaluate(wb, ws, ws.cell(row=row, column=2).value) == 26

    def test_buffers_present_without_platforms(self):
        from generate_report import build_workbook, validate_data

        raw = sample_data()
        raw["platforms"] = []
        for est in raw["estimates"]:
            est.pop("platform_points")
        wb = build_workbook(validate_data(raw))
        ws = wb["Summary"]
        assert ws.cell(row=find_row(ws, "集成联调"), column=2).value == 2
        row = find_row(ws, "Recommended Planning Estimate")
        assert evaluate(wb, ws, ws.cell(row=row, column=2).value) == 21

    def test_no_buffers_total_is_zero(self):
        from generate_report import build_workbook, validate_data

        raw = sample_data()
        raw["buffers"] = []
        wb = build_workbook(validate_data(raw))
        ws = wb["Summary"]
        assert ws.cell(row=find_row(ws, "Buffer Total"), column=2).value == 0
        row = find_row(ws, "Recommended Planning Estimate")
        assert evaluate(wb, ws, ws.cell(row=row, column=2).value) == 16

    def test_scope_and_confidence(self, built):
        wb, _ = built
        ws = wb["Summary"]
        assert ws.cell(row=1, column=1).value == "Scope Summary"
        assert ws.cell(row=2, column=1).value == "定位功能"
        find_row(ws, "Overall Confidence: Medium")

    def test_full_calc_on_load(self, built):
        wb, _ = built
        assert wb.calculation.fullCalcOnLoad is True


class TestPlatformSummary:
    def test_platform_rows_are_breakdown_formulas(self, built):
        wb, _ = built
        ws = wb["Platform Summary"]
        assert ws.cell(row=1, column=2).value == "设备端"
        func_row = find_row(ws, "Functional Stories")
        assert ws.cell(row=func_row, column=2).value.startswith("=SUMIF(")
        # 后端 functional = 3 + 3
        assert evaluate(wb, ws, ws.cell(row=func_row, column=3).value) == 6
        # Sum across platforms for functional: 5+3+3+3 + 0+3+2+2 = 21
        assert evaluate(wb, ws, ws.cell(row=func_row, column=6).value) == 21

    def test_planning_estimate_matches_summary_not_platform_sum(self, built):
        """Regression: planning used to be built from the platform sum."""
        wb, _ = built
        ws = wb["Platform Summary"]
        total_col = 6
        combined = ws.cell(row=find_row(ws, "Combined Story Points"), column=total_col)
        planning = ws.cell(
            row=find_row(ws, "Recommended Planning Estimate"), column=total_col
        )
        assert combined.value.startswith("=Summary!")
        assert evaluate(wb, ws, combined.value) == 16
        assert evaluate(wb, ws, planning.value) == 21
        platform_total = ws.cell(row=find_row(ws, "Platform Total"), column=total_col)
        assert evaluate(wb, ws, platform_total.value) == 24  # breakdown only


class TestRaidSheet:
    def test_raid_rows(self, built):
        wb, _ = built
        ws = wb["RAID"]
        assert ws.cell(row=1, column=1).value == "Type"
        assert ws.cell(row=2, column=2).value == "GNSS"


# ---------------------------------------------------------------------------
# CLI (subprocess against tmp_path; no network)
# ---------------------------------------------------------------------------


class TestCli:
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_generates_xlsx_with_formula_cells(self, tmp_path):
        from openpyxl import load_workbook

        data = tmp_path / "d.json"
        data.write_text(json.dumps(sample_data(), ensure_ascii=False), "utf-8")
        out = tmp_path / "e.xlsx"
        res = self._run("--output", str(out), "--data", str(data))
        assert res.returncode == 0, res.stderr
        assert "planning estimate 21" in res.stdout
        wb = load_workbook(out)
        ws = wb["Summary"]
        cell = ws.cell(row=find_row(ws, "Grand Total"), column=2)
        assert cell.data_type == "f"
        assert cell.value.startswith("=SUM(")
        assert evaluate(wb, ws, cell.value) == 16

    def test_refuses_to_overwrite(self, tmp_path):
        data = tmp_path / "d.json"
        data.write_text(json.dumps(sample_data(), ensure_ascii=False), "utf-8")
        out = tmp_path / "e.xlsx"
        out.write_bytes(b"keep me")
        res = self._run("--output", str(out), "--data", str(data))
        assert res.returncode == 1
        assert "already exists" in res.stderr
        assert out.read_bytes() == b"keep me"
        res = self._run("--output", str(out), "--data", str(data), "--force")
        assert res.returncode == 0, res.stderr

    def test_invalid_data_reports_errors(self, tmp_path):
        raw = sample_data()
        raw["estimates"][0]["category"] = "Infra"
        data = tmp_path / "d.json"
        data.write_text(json.dumps(raw), "utf-8")
        out = tmp_path / "e.xlsx"
        res = self._run("--output", str(out), "--data", str(data))
        assert res.returncode == 1
        assert "Infra" in res.stderr
        assert not out.exists()


class TestSkillsCheckRegistration:
    def test_registered_in_python_package_layer(self):
        from mythril_agent_skills.cli import skills_check

        skills = skills_check.CHECKABLE_SKILLS
        assert skills_check.SKILL_STORY_POINT_ESTIMATE == "story-point-estimate"
        assert skills_check.SKILL_STORY_POINT_ESTIMATE in skills
        idx = skills.index(skills_check.SKILL_STORY_POINT_ESTIMATE)
        # Python-package layer: after the other pip deps, before media binaries
        assert idx > skills.index(skills_check.SKILL_EXCEL)
        assert idx < skills.index(skills_check.SKILL_IMAGEMAGICK)
