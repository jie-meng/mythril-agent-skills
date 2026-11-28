# Estimation Workbook Format

Reference for `scripts/generate_report.py`: the sheets it writes and the JSON it
expects. Read this before building the `--data` JSON in Phase 7.

## Contents

- Sheets
- JSON data format
- Generation tips

## Sheets

The script creates a workbook with 3–4 sheets depending on whether platforms were specified:

**Sheet 1: "Estimates"** — all estimated items (functional + CFR) in one table.
**Platform columns** (one per confirmed platform) are inserted between "So that..." and "Points":

| Column | Content |
|---|---|
| # | Sequential number |
| Category | "Functional" or "CFR" |
| Epic | Epic name (for functional items) |
| Area | CFR area — Security, Performance, Monitoring, etc. (for CFR items) |
| Story | Story title |
| Role | User role |
| I want... | User story intent |
| So that... | Business value |
| *[Platform 1]* | Points for this platform (0 if N/A) — e.g., 设备端 |
| *[Platform 2]* | e.g., 后端 |
| *[Platform N]* | e.g., Android, iOS, WEB |
| Points | Combined Fibonacci point value (**numeric, bold**) |
| Rationale | Why this point value — effort, complexity, and uncertainty drivers |
| Uncertainty | "Low" / "Medium" / "High" |

Each story row includes per-platform point values. Platform columns are center-aligned
for easy scanning. A story that doesn't touch a platform gets 0.

**Sheet 2: "Platform Summary"** (only when platforms are specified) — breakdown by module and platform:

Modules (Functional Stories / CFR Items / Platform Total) as rows and platforms as
columns, each cell a `SUMIF` over the platform column of the Estimates sheet. The
platform sum is a *breakdown* — it can exceed the combined story points when platforms
are built in parallel. Below it, "Combined Story Points", "Buffer Total", and
"Recommended Planning Estimate" link to the Summary sheet, so both sheets always show
the same planning number.

**Sheet 3: "RAID"** — risk/assumption/issue/dependency log:

| Column | Content |
|---|---|
| Type | Risk / Assumption / Issue / Dependency |
| Item | Description |
| Impact | What happens if this materializes |
| Mitigation | How to reduce or eliminate |

**Sheet 4: "Summary"** — category breakdown (Functional / CFR / Grand Total), the
buffer line items with Buffer Total and **Recommended Planning Estimate** (Grand Total +
Buffer Total — present even without platforms), confidence analysis by uncertainty
level, key assumptions, and recommendations.

**All totals are live formulas** (`SUMIF` / `SUM` over the Estimates sheet), and the
workbook is flagged to recalculate on open, so editing a point value in Excel or
LibreOffice updates every total. Buffer point values are plain numbers the user can
adjust; the totals follow.

The script auto-formats all sheets: bold header rows, frozen top rows, auto-filters,
column widths, number formatting, and conditional coloring for Uncertainty.

## JSON data format

```json
{
  "platforms": ["设备端", "后端", "Android", "iOS", "WEB"],
  "scope_summary": "2-3 sentences...",
  "key_assumptions": ["..."],
  "confidence": "Medium",
  "estimates": [
    {
      "category": "Functional",
      "epic": "GPS定位",
      "area": "",
      "story": "GNSS 定位引擎",
      "role": "设备",
      "want": "GPS 定位并上报",
      "so_that": "让家长知道设备位置",
      "points": 5,
      "platform_points": {"设备端": 5, "后端": 0, "Android": 0, "iOS": 0, "WEB": 0},
      "rationale": "多模 GNSS + NMEA 解析",
      "uncertainty": "Medium"
    }
  ],
  "raid": [...],
  "buffers": [
    {"type": "集成联调", "pct": "10%", "points": 8, "rationale": "跨端集成测试"}
  ]
}
```

If `platforms` is empty or missing, platform columns and the Platform Summary sheet
are omitted; buffers and the planning estimate still appear on the Summary sheet.

Validation (the script stops and lists every problem):

- `category` must be `Functional` or `CFR` (case-insensitive; `NFR`, `non-functional`,
  `功能`, `非功能` are accepted and normalized)
- `points`, every `platform_points` value, and buffer `points` must be non-negative
  numbers (numeric strings like `"5"` are converted)
- `platform_points` keys must appear in `platforms` (missing keys count as 0)
- `uncertainty` must be `Low` / `Medium` / `High` (or empty)

## Generation tips

- Always include `platforms` in the JSON data — it is populated from Phase 1.5
- Each estimate MUST have `platform_points` matching all keys in `platforms`; use 0 for
  platforms the story doesn't touch
- The `points` field is the combined Fibonacci estimate for the whole story (not the sum of platform points)
- Include `buffers` in the JSON data for the Platform Summary sheet
- Write the JSON into the skill cache (`--print-cache-dir`), not the user's project
- Save the XLSX to the current working directory unless the user specifies a different path
- The script refuses to overwrite an existing output; use a unique timestamp suffix, or
  `--force` only after the user agrees
