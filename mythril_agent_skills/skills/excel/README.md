# Excel Skill

Read, write, search, and manipulate Excel workbooks (.xlsx) via a bundled Python CLI script powered by [openpyxl](https://openpyxl.readthedocs.io/).

## What It Does

Provides a single CLI entry point (`scripts/excel_ops.py`) with 23 subcommands covering the full range of common Excel operations:

| Category | Subcommands |
|---|---|
| **Inspect** | `info` |
| **Read** | `read`, `search` |
| **Write** | `write`, `write-range`, `create` |
| **Sheets** | `add-sheet`, `delete-sheet`, `rename-sheet`, `copy-sheet` |
| **Columns** | `add-column`, `delete-column`, `rename-column` |
| **Rows** | `add-row`, `delete-row` |
| **Styling** | `set-style`, `merge`, `unmerge` |
| **Layout** | `freeze`, `autofilter`, `column-width`, `row-height` |
| **CSV** | `export-csv`, `import-csv` |

### Safe-Save Default

All write operations save to a **timestamped copy** by default (e.g. `report_modified_20260327_143022.xlsx`), preserving the original file. Use `--in-place` (`-i`) to overwrite the original when explicitly intended.

## Format Support

- `.xlsx`, `.xlsm`, `.xltx`, `.xltm` (Excel 2010+) — native via openpyxl
- `.xls` (Excel 97-2003) — auto-converted to `.xlsx` via xls2xlsx before processing

## Setup

### Via mythril-agent-skills

```bash
pip install mythril-agent-skills          # xlsx support
pip install mythril-agent-skills[xls]     # xlsx + xls support
```

### Standalone

```bash
pip install openpyxl            # xlsx only
pip install openpyxl xls2xlsx   # xlsx + xls
```

## Quick Examples

```bash
# Inspect a workbook
python3 scripts/excel_ops.py info report.xlsx

# Read with headers as markdown table
python3 scripts/excel_ops.py read report.xlsx --header --limit 20

# Search across all sheets
python3 scripts/excel_ops.py search report.xlsx "revenue"

# Write cells (saves to timestamped copy)
python3 scripts/excel_ops.py write report.xlsx A1=Name B1=Score

# Write in place
python3 scripts/excel_ops.py write report.xlsx --in-place A1=Name B1=Score

# Create a new workbook with named sheets
python3 scripts/excel_ops.py create report.xlsx --sheets "Data" "Summary"

# Import CSV
python3 scripts/excel_ops.py import-csv report.xlsx data.csv
```

## Dependencies

- Python 3.10+
- `openpyxl` >= 3.1.0 — .xlsx read/write
- `xls2xlsx` >= 0.2.0 (optional) — .xls auto-conversion
