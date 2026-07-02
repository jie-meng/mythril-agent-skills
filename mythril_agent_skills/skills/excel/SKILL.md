---
name: excel
description: >
  Read, write, search, and manipulate Excel workbooks (.xlsx/.xls) via a
  bundled Python script. Trigger whenever the user asks to open, read, edit,
  create, or analyze an Excel or spreadsheet file, or says phrases like
  "read xlsx", "write excel", "open spreadsheet", "add column", "search
  excel", "export csv", "看 excel", "读表格", "写 excel", "操作 xlsx",
  "打开 xls", "增加一列", "表格搜索", "导出 csv", "csv 转 excel",
  "重命名工作表", "合并单元格", "设置样式". Also trigger when the user
  mentions a .xlsx or .xls file path and wants to inspect or modify it.
license: Apache-2.0
---

# When to Use This Skill

- User mentions a `.xlsx` or `.xls` file and wants to read, inspect, or modify it
- Spreadsheet operations: read cells/ranges, write values, search content
- Workbook structure: list sheets, add/delete/rename/copy sheets
- Column/row manipulation: add, delete, rename columns; add, delete rows
- Styling: bold, colors, alignment, borders, merge/unmerge cells
- Import/export: CSV to/from Excel conversion
- Creating new workbooks from scratch

> **Format support**: natively handles `.xlsx`, `.xlsm`, `.xltx`, `.xltm` (Excel 2010+). Legacy `.xls` (Excel 97-2003) is also supported — the script auto-converts it to `.xlsx` via xls2xlsx before processing. Write operations on `.xls` source files always output `.xlsx`.

# Prerequisites

- `openpyxl` — install with: `pip install openpyxl`
- `xls2xlsx` (optional) — needed only for `.xls` files: `pip install xls2xlsx` or `pip install mythril-agent-skills[xls]`

Pre-flight check:

```bash
python3 -c "import openpyxl; print(openpyxl.__version__)"
# Optional: check xls support
python3 -c "from xls2xlsx import XLS2XLSX; print('xls2xlsx OK')"
```

# Safe-Save Behavior

All write operations save to a **timestamped copy** by default (e.g. `report_modified_20260327_143022.xlsx`), preserving the original file. This prevents accidental data loss.

- Default: `report.xlsx` -> `report_modified_20260327_143022.xlsx`
- With `--in-place` (`-i`): overwrites `report.xlsx` directly

Use `--in-place` only when the user explicitly asks to modify the original file. When chaining multiple write operations, use `--in-place` on the first command's output for subsequent steps, or pass `--in-place` on all if the user wants all changes on the original.

# Workflow

1. Determine what the user wants (read, write, search, restructure, style, convert)
2. Run the appropriate script subcommand
3. Read the output (markdown table or confirmation) and present it to the user
4. For multi-step tasks, chain subcommands in sequence

All commands use:

```bash
python3 scripts/excel_ops.py <subcommand> [options] <file>
```

The script path is relative to this skill directory.

# Command Reference

## Inspect workbook

```bash
python3 scripts/excel_ops.py info report.xlsx
```

Shows all sheets with dimensions, row/column counts, and column headers (row 1 values).

## Read data

```bash
# Read entire active sheet as markdown table (first row = header)
python3 scripts/excel_ops.py read report.xlsx --header

# Read a specific range
python3 scripts/excel_ops.py read report.xlsx --range A1:D20 --header

# Read a specific sheet
python3 scripts/excel_ops.py read report.xlsx --sheet "Sales" --header

# Read first 50 rows
python3 scripts/excel_ops.py read report.xlsx --header --limit 50

# Read as JSON (useful for programmatic processing)
python3 scripts/excel_ops.py read report.xlsx --header --format json
```

## Search

```bash
# Case-insensitive search across all sheets
python3 scripts/excel_ops.py search report.xlsx "revenue"

# Exact match in one sheet
python3 scripts/excel_ops.py search report.xlsx "Q4 2024" --sheet "Sales" --exact

# Limit results
python3 scripts/excel_ops.py search report.xlsx "error" --limit 20
```

## Write cells

```bash
# Write individual cells (auto-detects numbers, booleans, formulas)
python3 scripts/excel_ops.py write report.xlsx A1=Name B1=Revenue C1=Margin

# Write to a specific sheet, in place
python3 scripts/excel_ops.py write report.xlsx --sheet "Summary" --in-place A1="Total" B1=42000

# Write a formula
python3 scripts/excel_ops.py write report.xlsx C2="=B2/A2*100"
```

## Write bulk data

```bash
# Write a JSON array of objects (with headers)
python3 scripts/excel_ops.py write-range report.xlsx \
  '[{"Name":"Alice","Score":95},{"Name":"Bob","Score":87}]' --header

# Write a JSON array of arrays starting at a specific position
python3 scripts/excel_ops.py write-range report.xlsx \
  '[["Q1",1000],["Q2",1200]]' --start-row 5 --start-col C
```

## Create workbook

```bash
# Create empty workbook
python3 scripts/excel_ops.py create new_report.xlsx

# Create with named sheets
python3 scripts/excel_ops.py create new_report.xlsx --sheets "Data" "Summary" "Charts"
```

## Sheet operations

```bash
python3 scripts/excel_ops.py add-sheet report.xlsx "Q4 Data"
python3 scripts/excel_ops.py add-sheet report.xlsx "Cover" --position 0
python3 scripts/excel_ops.py delete-sheet report.xlsx "Old Data"
python3 scripts/excel_ops.py rename-sheet report.xlsx "Sheet1" "Revenue"
python3 scripts/excel_ops.py copy-sheet report.xlsx "Template" --name "January"
```

## Column operations

```bash
# Add column at end
python3 scripts/excel_ops.py add-column report.xlsx "Profit Margin"

# Insert at position B with default value
python3 scripts/excel_ops.py add-column report.xlsx "Category" --position B --default "Uncategorized"

# Delete / rename
python3 scripts/excel_ops.py delete-column report.xlsx C
python3 scripts/excel_ops.py rename-column report.xlsx B "New Header"
```

## Row operations

```bash
python3 scripts/excel_ops.py add-row report.xlsx --values "Alice" 95 "A"
python3 scripts/excel_ops.py add-row report.xlsx --position 3 --values "Bob" 87 "B"
python3 scripts/excel_ops.py add-row report.xlsx --json '{"Name":"Carol","Score":92}'
python3 scripts/excel_ops.py delete-row report.xlsx 5 6 7
```

## Styling

```bash
python3 scripts/excel_ops.py set-style report.xlsx A1:D1 --bold true --font-size 14
python3 scripts/excel_ops.py set-style report.xlsx A1:D1 --bg-color "#4472C4" --font-color "#FFFFFF"
python3 scripts/excel_ops.py set-style report.xlsx B2:D10 --align center --border thin
python3 scripts/excel_ops.py merge report.xlsx A1:D1
python3 scripts/excel_ops.py unmerge report.xlsx A1:D1
```

## Layout

```bash
python3 scripts/excel_ops.py freeze report.xlsx A2           # freeze top row
python3 scripts/excel_ops.py freeze report.xlsx NONE          # unfreeze
python3 scripts/excel_ops.py autofilter report.xlsx A1:D100
python3 scripts/excel_ops.py column-width report.xlsx A 25
python3 scripts/excel_ops.py row-height report.xlsx 1 30
```

## CSV conversion

```bash
python3 scripts/excel_ops.py export-csv report.xlsx --output data.csv
python3 scripts/excel_ops.py export-csv report.xlsx --sheet "Sales" --output sales.csv
python3 scripts/excel_ops.py import-csv report.xlsx data.csv
python3 scripts/excel_ops.py import-csv report.xlsx data.tsv --delimiter "\t"
```

# Composing Multi-Step Workflows

The commands above are building blocks. Combine them to accomplish complex user requests. Examples:

**"Add a profit margin column calculated from revenue and cost":**
1. `info` to identify which columns contain revenue and cost
2. `add-column` to add "Profit Margin" header
3. `write` to fill formulas like `D2="=(B2-C2)/B2*100"` for each data row

**"Convert this CSV to a formatted Excel file":**
1. `import-csv` the CSV into a new workbook
2. `set-style` the header row (bold, background color)
3. `column-width` for readability
4. `freeze` the header row
5. `autofilter` the data range

When chaining multiple writes on the same file, apply `--in-place` to avoid creating a new copy at each step — or use the first command's output path for subsequent commands.

# Guidelines

- **Read before write**: always `info` or `read` first to understand the file structure
- **Large files**: use `--limit` when reading to avoid overwhelming output
- **Auto-type conversion**: the script auto-converts string inputs — `42` becomes int, `3.14` becomes float, `=SUM(A:A)` stays as formula, `true`/`false` become booleans
