"""Tests for story-point-estimate skill scripts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestBuildEstimatesSheet:
    """Tests that the workbook is generated with correct structure."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from generate_report import _build_estimates_sheet
        self._build_estimates_sheet = _build_estimates_sheet

    def test_sheet_headers_and_data(self, tmp_path: Path):
        from openpyxl import Workbook

        wb = Workbook()
        estimates = [
            {
                "category": "Functional",
                "epic": "Auth",
                "area": "",
                "story": "Login",
                "role": "User",
                "want": "log in",
                "so_that": "access account",
                "points": 3,
                "rationale": "Standard form",
                "uncertainty": "Low",
            },
        ]
        self._build_estimates_sheet(wb, estimates)
        ws = wb.active

        assert ws.cell(row=1, column=1).value == "#"
        assert ws.cell(row=1, column=9).value == "Points"
        assert ws.cell(row=2, column=1).value == 1
        assert ws.cell(row=2, column=5).value == "Login"
        assert ws.cell(row=2, column=9).value == 3
        assert ws.cell(row=2, column=11).value == "Low"

    def test_multiple_rows(self, tmp_path: Path):
        from openpyxl import Workbook

        wb = Workbook()
        estimates = [
            {
                "category": "Functional",
                "epic": "Auth",
                "area": "",
                "story": "S1",
                "role": "User",
                "want": "w1",
                "so_that": "st1",
                "points": 5,
                "rationale": "r1",
                "uncertainty": "Medium",
            },
            {
                "category": "CFR",
                "epic": "",
                "area": "Security",
                "story": "S2",
                "role": "",
                "want": "",
                "so_that": "",
                "points": 8,
                "rationale": "r2",
                "uncertainty": "High",
            },
        ]
        self._build_estimates_sheet(wb, estimates)
        ws = wb.active

        assert ws.cell(row=2, column=9).value == 5
        assert ws.cell(row=3, column=9).value == 8
        assert ws.cell(row=2, column=11).value == "Medium"
        assert ws.cell(row=3, column=11).value == "High"

    def test_empty_estimates(self, tmp_path: Path):
        from openpyxl import Workbook

        wb = Workbook()
        self._build_estimates_sheet(wb, [])
        ws = wb.active
        assert ws.cell(row=1, column=1).value == "#"
        assert ws.cell(row=2, column=1).value is None


class TestBuildRaidSheet:
    """Tests for RAID sheet generation."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from generate_report import _build_raid_sheet
        self._build_raid_sheet = _build_raid_sheet

    def test_raid_headers_and_data(self, tmp_path: Path):
        from openpyxl import Workbook

        wb = Workbook()
        raid = [
            {
                "type": "Risk",
                "item": "API downtime",
                "impact": "Service unavailable",
                "mitigation": "Circuit breaker",
            },
        ]
        self._build_raid_sheet(wb, raid)
        ws = wb["RAID"]

        assert ws.cell(row=1, column=1).value == "Type"
        assert ws.cell(row=2, column=1).value == "Risk"
        assert ws.cell(row=2, column=2).value == "API downtime"
        assert ws.cell(row=2, column=3).value == "Service unavailable"
        assert ws.cell(row=2, column=4).value == "Circuit breaker"


class TestBuildSummarySheet:
    """Tests for Summary sheet generation."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from generate_report import _build_summary_sheet
        self._build_summary_sheet = _build_summary_sheet

    def test_summary_contains_scope(self, tmp_path: Path):
        from openpyxl import Workbook

        wb = Workbook()
        data = {
            "scope_summary": "Test scope",
            "key_assumptions": ["A1"],
            "recommendations": "R1",
            "confidence": "Medium",
            "estimates": [],
        }
        self._build_summary_sheet(wb, data, 10, 5, 15)
        ws = wb["Summary"]

        assert ws.cell(row=1, column=1).value == "Scope Summary"
        assert ws.cell(row=2, column=1).value == "Test scope"

    def test_totals(self, tmp_path: Path):
        from openpyxl import Workbook

        wb = Workbook()
        data = {
            "scope_summary": "",
            "key_assumptions": [],
            "recommendations": "",
            "confidence": "High",
            "estimates": [],
        }
        self._build_summary_sheet(wb, data, 20, 10, 30)
        ws = wb["Summary"]

        found = False
        for row in ws.iter_rows(min_row=1, max_col=3):
            for cell in row:
                if cell.value == "Grand Total":
                    total_cell = ws.cell(row=cell.row, column=2)
                    assert total_cell.value == 30
                    found = True
        assert found

    def test_confidence(self, tmp_path: Path):
        from openpyxl import Workbook

        wb = Workbook()
        data = {
            "scope_summary": "",
            "key_assumptions": [],
            "recommendations": "",
            "confidence": "Low",
            "estimates": [],
        }
        self._build_summary_sheet(wb, data, 0, 0, 0)
        ws = wb["Summary"]

        found = False
        for row in ws.iter_rows(min_row=1, max_col=3):
            for cell in row:
                if cell.value and "Low" in str(cell.value) and "Confidence" in str(cell.value):
                    found = True
        assert found
