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

A structured layout with modules (Functional Stories / CFR Items / Total) as rows and
platforms as columns. Bottom section shows each buffer line item with type, percentage,
points, and rationale. Final row shows the recommended planning estimate. Uses bold
formatting for totals.

**Sheet 3: "RAID"** — risk/assumption/issue/dependency log:

| Column | Content |
|---|---|
| Type | Risk / Assumption / Issue / Dependency |
| Item | Description |
| Impact | What happens if this materializes |
| Mitigation | How to reduce or eliminate |

**Sheet 4: "Summary"** — categorical breakdown, confidence analysis, key assumptions,
and recommendations (same as before).

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
are omitted (backward compatible).

## Generation tips

- Always include `platforms` in the JSON data — it is populated from Phase 1.5
- Each estimate MUST have `platform_points` matching all keys in `platforms`; use 0 for
  platforms the story doesn't touch
- The `points` field is the combined Fibonacci estimate for the whole story (not the sum of platform points)
- Include `buffers` in the JSON data for the Platform Summary sheet
- Save to the current working directory unless the user specifies a different path
- Never overwrite an existing file without asking; use a unique timestamp suffix
