#!/usr/bin/env python3
"""Generate a formatted XLSX estimation workbook from JSON data.

Supports dynamic per-platform columns: when the JSON includes a "platforms"
array, the Estimates sheet gains one column per platform between "So that..."
and "Points", and an extra "Platform Summary" sheet is created.

Every total in the workbook is a live Excel formula (SUMIF / SUM over the
Estimates sheet), so editing a point value in Excel updates all totals. The
single planning basis is the sum of the combined `points` column; platform
columns are a breakdown only.

Usage:
    python3 generate_report.py --print-cache-dir
    python3 generate_report.py --output estimate.xlsx --data estimate_data.json
    python3 generate_report.py --output estimate.xlsx --data d.json --force
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import platform as platform_mod
import sys
import unicodedata
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:  # pragma: no cover - exercised only without openpyxl
    Workbook = None  # type: ignore[assignment,misc]

SKILL_NAME = "story-point-estimate"

if Workbook is not None:
    HEADER_FONT = Font(bold=True, size=11, color="FFFFFF")
    HEADER_FILL = PatternFill(
        start_color="2F5496", end_color="2F5496", fill_type="solid"
    )
    TOTAL_FONT = Font(bold=True, size=12)
    TITLE_FONT = Font(bold=True, size=14, color="2F5496")
    THIN_BORDER = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

UNCERTAINTY_COLORS = {
    "Low": "C6EFCE",
    "Medium": "FFEB9C",
    "High": "FFC7CE",
}

# Zero renders as an em dash; negatives keep their sign.
POINTS_FORMAT = '0;-0;"—"'
PERCENT_FORMAT = "0%"

_BASE_HEADERS = [
    "#",
    "Category",
    "Epic",
    "Area",
    "Story",
    "Role",
    "I want...",
    "So that...",
]
_POINTS_COL = "Points"
_RATIONALE_COL = "Rationale"
_UNCERTAINTY_COL = "Uncertainty"
# platform columns are inserted between _BASE_HEADERS and _POINTS_COL

ESTIMATES_SHEET = "Estimates"
SUMMARY_SHEET = "Summary"
PLATFORM_SHEET = "Platform Summary"

CATEGORY_ALIASES = {
    "functional": "Functional",
    "function": "Functional",
    "feature": "Functional",
    "功能": "Functional",
    "功能性": "Functional",
    "cfr": "CFR",
    "nfr": "CFR",
    "non-functional": "CFR",
    "nonfunctional": "CFR",
    "non functional": "CFR",
    "非功能": "CFR",
    "非功能性": "CFR",
}

UNCERTAINTY_ALIASES = {
    "low": "Low",
    "medium": "Medium",
    "med": "Medium",
    "high": "High",
    "低": "Low",
    "中": "Medium",
    "高": "High",
}


class EstimateDataError(ValueError):
    """Raised when the estimation JSON is malformed."""


# ---------------------------------------------------------------------------
# Pure helpers: cache dir, validation, formulas, widths
# ---------------------------------------------------------------------------


def cache_dir_for(
    system: str, env: dict[str, str], home: Path
) -> Path:
    """Return the unified per-user cache dir for this skill (no side effects)."""
    if system == "Darwin":
        root = home / "Library" / "Caches" / "mythril-skills-cache"
    elif system == "Windows":
        local = env.get("LOCALAPPDATA")
        base = Path(local) if local else home / "AppData" / "Local"
        root = base / "mythril-skills-cache"
    else:
        xdg = env.get("XDG_CACHE_HOME")
        base = Path(xdg) if xdg else home / ".cache"
        root = base / "mythril-skills-cache"
    return root / SKILL_NAME


def normalize_category(value: object) -> str:
    """Map a category label to "Functional" or "CFR"; raise on anything else."""
    if not isinstance(value, str) or not value.strip():
        raise EstimateDataError(f"category is required, got {value!r}")
    key = value.strip().lower().replace("_", "-")
    if key in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[key]
    raise EstimateDataError(
        f"category {value!r} is not recognized — use 'Functional' or 'CFR'"
    )


def normalize_uncertainty(value: object) -> str:
    """Map an uncertainty label to Low/Medium/High ('' stays '')."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    if isinstance(value, str):
        key = value.strip().lower()
        if key in UNCERTAINTY_ALIASES:
            return UNCERTAINTY_ALIASES[key]
    raise EstimateDataError(
        f"uncertainty {value!r} is not recognized — use Low, Medium, or High"
    )


def to_points(value: object, where: str) -> int | float:
    """Coerce a point value to a non-negative number; raise with context."""
    if isinstance(value, bool):
        raise EstimateDataError(f"{where}: points must be a number, got {value!r}")
    if isinstance(value, (int, float)):
        number: int | float = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            number = int(text)
        except ValueError:
            try:
                number = float(text)
            except ValueError:
                raise EstimateDataError(
                    f"{where}: points must be a number, got {value!r}"
                ) from None
    else:
        raise EstimateDataError(f"{where}: points must be a number, got {value!r}")
    if number < 0:
        raise EstimateDataError(f"{where}: points must be >= 0, got {value!r}")
    if isinstance(number, float) and number.is_integer():
        return int(number)
    return number


def validate_data(data: object) -> dict:
    """Validate and normalize estimation JSON. Returns a normalized copy.

    Collects every problem and raises one EstimateDataError listing them all.
    """
    if not isinstance(data, dict):
        raise EstimateDataError("top-level JSON must be an object")
    out = copy.deepcopy(data)
    errors: list[str] = []

    platforms = out.get("platforms") or []
    if not isinstance(platforms, list) or not all(
        isinstance(p, str) and p.strip() for p in platforms
    ):
        errors.append("platforms must be a list of non-empty strings")
        platforms = []
    if len(set(platforms)) != len(platforms):
        errors.append(f"platforms contains duplicates: {platforms!r}")
    reserved = set(_BASE_HEADERS) | {_POINTS_COL, _RATIONALE_COL, _UNCERTAINTY_COL}
    for p in platforms:
        if p in reserved:
            errors.append(f"platform name {p!r} collides with a column header")
    out["platforms"] = platforms

    estimates = out.get("estimates") or []
    if not isinstance(estimates, list):
        errors.append("estimates must be a list")
        estimates = []
    for idx, est in enumerate(estimates, 1):
        where = f"estimates[{idx}] ({est.get('story', '') if isinstance(est, dict) else ''})"
        if not isinstance(est, dict):
            errors.append(f"estimates[{idx}] must be an object")
            continue
        try:
            est["category"] = normalize_category(est.get("category"))
        except EstimateDataError as exc:
            errors.append(f"{where}: {exc}")
        try:
            est["points"] = to_points(est.get("points", 0), where)
        except EstimateDataError as exc:
            errors.append(str(exc))
        try:
            est["uncertainty"] = normalize_uncertainty(est.get("uncertainty"))
        except EstimateDataError as exc:
            errors.append(f"{where}: {exc}")
        pp = est.get("platform_points") or {}
        if not isinstance(pp, dict):
            errors.append(f"{where}: platform_points must be an object")
            pp = {}
        unknown = [k for k in pp if k not in platforms]
        if unknown:
            errors.append(
                f"{where}: platform_points has keys not in platforms: {unknown!r}"
            )
        normalized_pp: dict[str, int | float] = {}
        for plat in platforms:
            try:
                normalized_pp[plat] = to_points(
                    pp.get(plat, 0), f"{where} platform {plat!r}"
                )
            except EstimateDataError as exc:
                errors.append(str(exc))
        est["platform_points"] = normalized_pp
    out["estimates"] = estimates

    buffers = out.get("buffers") or []
    if not isinstance(buffers, list):
        errors.append("buffers must be a list")
        buffers = []
    for idx, buf in enumerate(buffers, 1):
        if not isinstance(buf, dict):
            errors.append(f"buffers[{idx}] must be an object")
            continue
        try:
            buf["points"] = to_points(buf.get("points", 0), f"buffers[{idx}]")
        except EstimateDataError as exc:
            errors.append(str(exc))
    out["buffers"] = buffers

    raid = out.get("raid") or []
    if not isinstance(raid, list):
        errors.append("raid must be a list")
        raid = []
    out["raid"] = raid

    if errors:
        raise EstimateDataError("\n".join(errors))
    return out


def compute_totals(estimates: list[dict], buffers: list[dict]) -> dict[str, float]:
    """Python-side totals (mirrors the workbook formulas; used for stdout)."""
    functional = sum(e["points"] for e in estimates if e["category"] == "Functional")
    cfr = sum(e["points"] for e in estimates if e["category"] == "CFR")
    buffer_total = sum(b["points"] for b in buffers)
    return {
        "functional": functional,
        "cfr": cfr,
        "grand": functional + cfr,
        "buffer": buffer_total,
        "planning": functional + cfr + buffer_total,
    }


def field_order(platforms: list[str]) -> list[str]:
    """Full header list for the Estimates sheet, with platforms inserted."""
    headers = list(_BASE_HEADERS)
    headers.extend(platforms)
    headers.append(_POINTS_COL)
    headers.append(_RATIONALE_COL)
    headers.append(_UNCERTAINTY_COL)
    return headers


def _col_idx_for(field_name: str, platforms: list[str]) -> int:
    """Return 1-based column index for a named field."""
    mapping = {h: idx for idx, h in enumerate(field_order(platforms), 1)}
    return mapping[field_name]


def column_letter(idx: int) -> str:
    """1-based column index -> Excel letters (A, B, ..., AA)."""
    letters = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def sheet_ref(sheet: str) -> str:
    """Quote a sheet name for use in a formula when needed."""
    if any(not (ch.isalnum() or ch == "_") for ch in sheet):
        return "'" + sheet.replace("'", "''") + "'"
    return sheet


def sumif_formula(criteria: str, crit_col: str, sum_col: str) -> str:
    """=SUMIF over whole columns of the Estimates sheet."""
    est = sheet_ref(ESTIMATES_SHEET)
    crit = criteria.replace('"', '""')
    return f'=SUMIF({est}!${crit_col}:${crit_col},"{crit}",{est}!${sum_col}:${sum_col})'


def display_width(text: str) -> int:
    """Approximate rendered width: East Asian wide/fullwidth chars count as 2."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


# ---------------------------------------------------------------------------
# Sheet builders
# ---------------------------------------------------------------------------


def _style_header_cell(cell) -> None:
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = THIN_BORDER


def _style_header(ws, num_cols: int) -> None:
    for col in range(1, num_cols + 1):
        _style_header_cell(ws.cell(row=1, column=col))


def _auto_width(ws, max_width: int = 50) -> None:
    for col_cells in ws.columns:
        lengths = []
        for cell in col_cells:
            if cell.value is None:
                continue
            text = str(cell.value)
            if text.startswith("="):
                continue  # formula text is not what the user sees
            for line in text.split("\n"):
                lengths.append(display_width(line))
        if lengths:
            col_letter = get_column_letter(col_cells[0].column)
            ws.column_dimensions[col_letter].width = min(max(lengths) + 3, max_width)


def _bordered(ws, row: int, col: int, value=None, *, bold: bool = False,
              font=None, center: bool = False, fmt: str | None = None):
    cell = ws.cell(row=row, column=col, value=value)
    cell.border = THIN_BORDER
    if font is not None:
        cell.font = font
    elif bold:
        cell.font = Font(bold=True)
    if center:
        cell.alignment = Alignment(horizontal="center")
    if fmt:
        cell.number_format = fmt
    return cell


def _build_estimates_sheet(
    wb: Workbook, estimates: list[dict], platforms: list[str]
) -> None:
    ws = wb.active
    ws.title = ESTIMATES_SHEET

    headers = field_order(platforms)
    ws.append(headers)
    _style_header(ws, len(headers))

    points_col = _col_idx_for(_POINTS_COL, platforms)
    unc_col = _col_idx_for(_UNCERTAINTY_COL, platforms)

    for i, est in enumerate(estimates, 1):
        row_data = [
            i,
            est.get("category", ""),
            est.get("epic", ""),
            est.get("area", ""),
            est.get("story", ""),
            est.get("role", ""),
            est.get("want", ""),
            est.get("so_that", ""),
        ]
        pp = est.get("platform_points", {})
        for plat in platforms:
            row_data.append(pp.get(plat, 0))
        row_data.append(est.get("points", 0))
        row_data.append(est.get("rationale", ""))
        row_data.append(est.get("uncertainty", ""))

        ws.append(row_data)
        row_num = i + 1

        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=row_num, column=col)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True)

        ws.cell(row=row_num, column=points_col).font = Font(bold=True, size=11)
        ws.cell(row=row_num, column=points_col).alignment = Alignment(
            horizontal="center", vertical="top"
        )

        for plat in platforms:
            plat_col = _col_idx_for(plat, platforms)
            ws.cell(row=row_num, column=plat_col).alignment = Alignment(
                horizontal="center", vertical="top"
            )

        fill_color = UNCERTAINTY_COLORS.get(est.get("uncertainty", ""))
        if fill_color:
            ws.cell(row=row_num, column=unc_col).fill = PatternFill(
                start_color=fill_color, end_color=fill_color, fill_type="solid"
            )
            ws.cell(row=row_num, column=unc_col).alignment = Alignment(
                horizontal="center", vertical="top"
            )

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    _auto_width(ws)


def _build_summary_sheet(
    wb: Workbook, data: dict, platforms: list[str]
) -> dict[str, str]:
    """Write the Summary sheet; return absolute refs of the key total cells."""
    ws = wb.create_sheet(SUMMARY_SHEET)
    points_letter = column_letter(_col_idx_for(_POINTS_COL, platforms))
    unc_letter = column_letter(_col_idx_for(_UNCERTAINTY_COL, platforms))
    category_letter = column_letter(_BASE_HEADERS.index("Category") + 1)
    refs: dict[str, str] = {}

    row = 1
    ws.cell(row=row, column=1, value="Scope Summary").font = TITLE_FONT
    row += 1
    ws.cell(row=row, column=1, value=data.get("scope_summary", "")).alignment = (
        Alignment(wrap_text=True)
    )
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)

    # --- Category Breakdown ---
    row += 2
    ws.cell(row=row, column=1, value="Category Breakdown").font = TITLE_FONT
    row += 1
    for ci, h in enumerate(["Category", "Total Points", "%"], 1):
        _style_header_cell(ws.cell(row=row, column=ci, value=h))

    row += 1
    first_cat_row = row
    grand_row = row + 2
    for cat_label, criteria in [
        ("Functional Stories", "Functional"),
        ("Non-Functional (CFR)", "CFR"),
    ]:
        _bordered(ws, row, 1, cat_label, bold=True)
        _bordered(
            ws, row, 2, sumif_formula(criteria, category_letter, points_letter),
            bold=True, center=True,
        )
        _bordered(
            ws, row, 3, f"=IF($B${grand_row}>0,B{row}/$B${grand_row},0)",
            center=True, fmt=PERCENT_FORMAT,
        )
        refs[criteria.lower()] = f"$B${row}"
        row += 1

    _bordered(ws, row, 1, "Grand Total", font=TOTAL_FONT)
    _bordered(
        ws, row, 2, f"=SUM(B{first_cat_row}:B{row - 1})",
        font=TOTAL_FONT, center=True,
    )
    _bordered(ws, row, 3, f"=IF(B{row}>0,1,0)", font=TOTAL_FONT, center=True,
              fmt=PERCENT_FORMAT)
    refs["grand"] = f"$B${row}"

    # --- Buffers & planning estimate (always present) ---
    row += 2
    ws.cell(row=row, column=1, value="Buffers & Planning Estimate").font = TITLE_FONT
    row += 1
    for ci, h in enumerate(["Buffer", "Points", "%", "Rationale"], 1):
        _style_header_cell(ws.cell(row=row, column=ci, value=h))
    row += 1
    buffers = data.get("buffers", [])
    first_buf_row = row
    for buf in buffers:
        _bordered(ws, row, 1, buf.get("type", ""), bold=True)
        _bordered(ws, row, 2, buf.get("points", 0), bold=True, center=True)
        _bordered(ws, row, 3, buf.get("pct", ""), center=True)
        rc = _bordered(ws, row, 4, buf.get("rationale", ""))
        rc.alignment = Alignment(wrap_text=True, vertical="top")
        row += 1
    _bordered(ws, row, 1, "Buffer Total", font=TOTAL_FONT)
    buf_formula = f"=SUM(B{first_buf_row}:B{row - 1})" if buffers else 0
    _bordered(ws, row, 2, buf_formula, font=TOTAL_FONT, center=True)
    refs["buffer"] = f"$B${row}"
    row += 1
    _bordered(ws, row, 1, "Recommended Planning Estimate", font=TOTAL_FONT)
    _bordered(
        ws, row, 2, f"={refs['grand']}+{refs['buffer']}",
        font=TOTAL_FONT, center=True,
    )
    refs["planning"] = f"$B${row}"

    # --- Confidence Analysis ---
    row += 2
    ws.cell(row=row, column=1, value="Confidence Analysis").font = TITLE_FONT
    row += 1
    ws.cell(
        row=row, column=1,
        value=f"Overall Confidence: {data.get('confidence', 'N/A')}",
    ).font = Font(bold=True, size=11)

    row += 1
    for ci, h in enumerate(["Uncertainty Level", "Points", "% of Total"], 1):
        _style_header_cell(ws.cell(row=row, column=ci, value=h))

    row += 1
    for level in ("Low", "Medium", "High"):
        c = _bordered(ws, row, 1, level, bold=True)
        c.fill = PatternFill(
            start_color=UNCERTAINTY_COLORS[level],
            end_color=UNCERTAINTY_COLORS[level],
            fill_type="solid",
        )
        _bordered(
            ws, row, 2, sumif_formula(level, unc_letter, points_letter),
            bold=True, center=True,
        )
        _bordered(
            ws, row, 3, f"=IF({refs['grand']}>0,B{row}/{refs['grand']},0)",
            center=True, fmt=PERCENT_FORMAT,
        )
        row += 1

    # --- Key Assumptions ---
    row += 1
    ws.cell(row=row, column=1, value="Key Assumptions").font = TITLE_FONT
    row += 1
    for assumption in data.get("key_assumptions", []):
        ws.cell(row=row, column=1, value=f"  {assumption}").alignment = Alignment(
            wrap_text=True
        )
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 1

    # --- Recommendations ---
    if data.get("recommendations"):
        row += 1
        ws.cell(row=row, column=1, value="Recommendations").font = TITLE_FONT
        row += 1
        ws.cell(row=row, column=1, value=data["recommendations"]).alignment = (
            Alignment(wrap_text=True)
        )
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 40
    return refs


def _build_platform_summary(
    wb: Workbook,
    platforms: list[str],
    summary_refs: dict[str, str],
    index: int = 1,
) -> None:
    """Per-platform breakdown (formulas) plus links to the Summary totals."""
    ws = wb.create_sheet(PLATFORM_SHEET, index)
    category_letter = column_letter(_BASE_HEADERS.index("Category") + 1)
    total_col = len(platforms) + 2
    summary = sheet_ref(SUMMARY_SHEET)

    headers = ["Module", *platforms, "Sum across platforms"]
    for col, h in enumerate(headers, 1):
        _style_header_cell(ws.cell(row=1, column=col, value=h))

    row = 2
    first_row = row
    for label, criteria in [("Functional Stories", "Functional"), ("CFR Items", "CFR")]:
        _bordered(ws, row, 1, label, bold=True)
        for j, plat in enumerate(platforms, 2):
            plat_letter = column_letter(_col_idx_for(plat, platforms))
            _bordered(
                ws, row, j, sumif_formula(criteria, category_letter, plat_letter),
                center=True, fmt=POINTS_FORMAT,
            )
        _bordered(
            ws, row, total_col,
            f"=SUM(B{row}:{column_letter(total_col - 1)}{row})",
            bold=True, center=True, fmt=POINTS_FORMAT,
        )
        row += 1

    _bordered(ws, row, 1, "Platform Total", font=TOTAL_FONT)
    for col in range(2, total_col + 1):
        letter = column_letter(col)
        _bordered(
            ws, row, col, f"=SUM({letter}{first_row}:{letter}{row - 1})",
            font=TOTAL_FONT, center=True, fmt=POINTS_FORMAT,
        )
    row += 2

    note = ws.cell(
        row=row, column=1,
        value=(
            "Platform columns are a breakdown of where effort lands. Their sum can "
            "exceed the combined story points (platforms built in parallel), so "
            "planning uses the combined Points column."
        ),
    )
    note.font = Font(italic=True, size=10, color="666666")
    note.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=total_col)
    ws.row_dimensions[row].height = 45
    row += 2

    for label, key, font in [
        ("Combined Story Points", "grand", Font(bold=True)),
        ("Buffer Total", "buffer", Font(bold=True)),
        ("Recommended Planning Estimate", "planning", TOTAL_FONT),
    ]:
        _bordered(ws, row, 1, label, font=font)
        _bordered(
            ws, row, total_col, f"={summary}!{summary_refs[key]}",
            font=font, center=True,
        )
        row += 1

    _auto_width(ws, max_width=30)
    ws.column_dimensions["A"].width = 32


def _build_raid_sheet(wb: Workbook, raid: list[dict]) -> None:
    ws = wb.create_sheet("RAID")

    headers = ["Type", "Item", "Impact", "Mitigation"]
    ws.append(headers)
    _style_header(ws, len(headers))

    for i, item in enumerate(raid, 1):
        row_data = [
            item.get("type", ""),
            item.get("item", ""),
            item.get("impact", ""),
            item.get("mitigation", ""),
        ]
        ws.append(row_data)
        row_num = i + 1
        for col in range(1, len(headers) + 1):
            ws.cell(row=row_num, column=col).border = THIN_BORDER
            ws.cell(row=row_num, column=col).alignment = Alignment(
                vertical="top", wrap_text=True
            )
        ws.cell(row=row_num, column=1).font = Font(bold=True)
        ws.cell(row=row_num, column=1).alignment = Alignment(
            horizontal="center", vertical="top"
        )

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    _auto_width(ws, max_width=60)


def build_workbook(data: dict) -> Workbook:
    """Build the full workbook from *validated* data (see validate_data)."""
    estimates: list[dict] = data.get("estimates", [])
    platforms: list[str] = data.get("platforms", [])

    wb = Workbook()
    _build_estimates_sheet(wb, estimates, platforms)
    _build_raid_sheet(wb, data.get("raid", []))
    refs = _build_summary_sheet(wb, data, platforms)
    if platforms:
        _build_platform_summary(wb, platforms, refs, index=1)
    # Ask Excel / LibreOffice to recalculate every formula on open.
    wb.calculation.fullCalcOnLoad = True
    return wb


def _fmt(n: float) -> str:
    return f"{n:g}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a formatted XLSX estimation workbook."
    )
    parser.add_argument("--output", "-o", help="Output XLSX file path")
    parser.add_argument("--data", "-d", help="JSON data file with estimation data")
    parser.add_argument(
        "--force", action="store_true",
        help="overwrite --output if it exists (only after the user agreed)",
    )
    parser.add_argument(
        "--print-cache-dir", action="store_true",
        help="create and print the cache dir for the intermediate JSON, then exit",
    )
    args = parser.parse_args()

    if args.print_cache_dir:
        cache_dir = cache_dir_for(platform_mod.system(), dict(os.environ), Path.home())
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(cache_dir)
        return

    if not args.output or not args.data:
        parser.error("--output and --data are required")

    if Workbook is None:
        print(
            "Error: openpyxl is not installed. Run: pip install openpyxl",
            file=sys.stderr,
        )
        sys.exit(1)

    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        print(
            f"Error: {output_path} already exists. Choose a new name "
            "(e.g. a fresh timestamp) or pass --force after the user agrees.",
            file=sys.stderr,
        )
        sys.exit(1)

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Error: data file not found: {args.data}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(data_path, encoding="utf-8") as f:
            raw = json.load(f)
        data = validate_data(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: {args.data} is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    except EstimateDataError as exc:
        print(f"Error: invalid estimation data:\n{exc}", file=sys.stderr)
        sys.exit(1)

    wb = build_workbook(data)
    wb.save(output_path)
    totals = compute_totals(data["estimates"], data["buffers"])
    print(f"Estimation workbook saved to: {output_path.resolve()}")
    print(
        f"Functional {_fmt(totals['functional'])} + CFR {_fmt(totals['cfr'])} = "
        f"{_fmt(totals['grand'])} points; buffers +{_fmt(totals['buffer'])}; "
        f"planning estimate {_fmt(totals['planning'])} (all totals are live formulas)"
    )


if __name__ == "__main__":
    main()
