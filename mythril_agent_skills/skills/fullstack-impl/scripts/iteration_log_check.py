#!/usr/bin/env python3
"""Validate the consistency of a fullstack-impl work directory's iteration log.

This is a structural check, not a semantic one. It catches the most common
"AI agent forgot to maintain the audit trail" failure modes for the
post-finalization sticky loop defined in fullstack-impl/SKILL.md
(see "Iteration Mode — Post-Implementation Sticky Loop").

What it checks:
    1. progress.md exists and contains an "## Iteration Log" (English) or
       "## 迭代记录" (Chinese) section.
    2. review.md exists.
    3. The Iteration Log table is parseable (markdown table format).
    4. Each iteration row has all required columns filled (no blank cells
       in mandatory fields), including the explicit "unchanged" marker for
       analysis.md and plan.md.
    5. Iteration numbers are sequential (1, 2, 3, ...) with no gaps or
       duplicates.
    6. The number of iteration rows in progress.md does NOT exceed the
       number of review-round headers in review.md (every iteration MUST
       have produced at least one staged-review round).

What it does NOT check:
    - Whether the actual code changes match the iteration descriptions.
    - Whether the docs commits actually happened (that needs git access).
    - Whether the chosen "unchanged" / "updated" status is truthful.
    - Cross-repo semantic consistency (that is the agent's job).

Usage:
    python3 iteration_log_check.py <work-directory>

Exit codes:
    0 — all checks passed (or only warnings)
    1 — at least one error found
    2 — work directory missing or invalid arguments

Output (machine + human readable):
    STATUS=PASS|WARN|FAIL
    ITERATION_ROWS=<N>
    REVIEW_ROUNDS=<N>
    Followed by one line per finding:
        ERROR:   <message>
        WARNING: <message>
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ITERATION_LOG_HEADERS = ("## Iteration Log", "## 迭代记录")

REQUIRED_COLUMNS_EN = (
    "#",
    "date",
    "trigger",
    "repos",
    "files",
    "review",
    "analysis.md",
    "plan.md",
    "commit",
)

REQUIRED_COLUMNS_ZH = (
    "#",
    "日期",
    "触发",
    "仓库",
    "文件",
    "审查",
    "analysis.md",
    "plan.md",
    "提交",
)

REVIEW_ROUND_PATTERN = re.compile(
    r"^##\s+\S+.*?(?:Review Round|第\s*\d+\s*轮审查)",
    re.MULTILINE,
)

DOC_STATUS_PATTERN = re.compile(
    r"^(unchanged|updated\b.*|未变|已更新\b.*)$",
    re.IGNORECASE,
)


@dataclass
class IterationRow:
    """A single parsed Iteration Log row."""

    number: int | None
    cells: dict[str, str]
    raw: str


@dataclass
class CheckResult:
    """Aggregated check result for one work directory."""

    iteration_rows: list[IterationRow] = field(default_factory=list)
    review_round_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.errors:
            return "FAIL"
        if self.warnings:
            return "WARN"
        return "PASS"


def find_iteration_log_section(progress_text: str) -> str | None:
    """Return the body of the Iteration Log section, or None if absent."""
    lines = progress_text.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if any(stripped.startswith(h) for h in ITERATION_LOG_HEADERS):
            start_idx = i + 1
            break
    if start_idx is None:
        return None
    end_idx = len(lines)
    for j in range(start_idx, len(lines)):
        if lines[j].startswith("## ") and not any(
            lines[j].strip().startswith(h) for h in ITERATION_LOG_HEADERS
        ):
            end_idx = j
            break
    return "\n".join(lines[start_idx:end_idx])


def parse_markdown_table(section: str) -> tuple[list[str], list[list[str]]]:
    """Parse a markdown table from a section body.

    Returns (header_cells, data_rows). Returns ([], []) if no table is
    present or the table has no data rows.
    """
    table_lines = [
        line.rstrip()
        for line in section.splitlines()
        if line.lstrip().startswith("|")
    ]
    if len(table_lines) < 2:
        return [], []

    def split_row(line: str) -> list[str]:
        parts = line.strip().strip("|").split("|")
        return [p.strip() for p in parts]

    header = split_row(table_lines[0])
    if not all(set(cell) <= set("-:| ") for cell in split_row(table_lines[1])):
        return header, []

    data_rows = []
    for line in table_lines[2:]:
        cells = split_row(line)
        if all(c == "" for c in cells):
            continue
        data_rows.append(cells)
    return header, data_rows


def detect_language(header: list[str]) -> str:
    """Return 'zh' if header looks Chinese, else 'en'."""
    joined = " ".join(header).lower()
    if any(zh in joined for zh in ("日期", "触发", "仓库", "审查")):
        return "zh"
    return "en"


def parse_iteration_rows(
    header: list[str], data_rows: list[list[str]]
) -> list[IterationRow]:
    """Convert raw table rows into IterationRow objects."""
    normalized_header = [h.lower() for h in header]
    rows: list[IterationRow] = []
    for raw_cells in data_rows:
        cells: dict[str, str] = {}
        for col_name, value in zip(normalized_header, raw_cells):
            cells[col_name] = value
        number_str = cells.get("#", "").strip()
        try:
            number = int(number_str) if number_str else None
        except ValueError:
            number = None
        rows.append(
            IterationRow(
                number=number,
                cells=cells,
                raw=" | ".join(raw_cells),
            )
        )
    return rows


def count_review_rounds(review_text: str) -> int:
    """Count the number of per-repo review-round headers in review.md."""
    return len(REVIEW_ROUND_PATTERN.findall(review_text))


def check_required_columns(
    rows: list[IterationRow], lang: str
) -> list[str]:
    """Verify each row has every required column non-empty."""
    required = REQUIRED_COLUMNS_ZH if lang == "zh" else REQUIRED_COLUMNS_EN
    errors: list[str] = []
    for row in rows:
        missing = [
            col for col in required if not row.cells.get(col, "").strip()
        ]
        if missing:
            label = row.cells.get("#") or "?"
            errors.append(
                f"row #{label}: missing required columns: {', '.join(missing)}"
            )
    return errors


def check_doc_status_columns(rows: list[IterationRow]) -> list[str]:
    """Verify analysis.md and plan.md columns use the explicit-status form."""
    warnings: list[str] = []
    for row in rows:
        for col in ("analysis.md", "plan.md"):
            value = row.cells.get(col, "").strip()
            if not value:
                continue
            if not DOC_STATUS_PATTERN.match(value):
                label = row.cells.get("#") or "?"
                warnings.append(
                    f"row #{label}: {col} value '{value}' should be "
                    "'unchanged' / 'updated: <section>' (or '未变' / "
                    "'已更新: <section>')"
                )
    return warnings


def check_sequential_numbers(rows: list[IterationRow]) -> list[str]:
    """Verify iteration numbers form 1..N with no gaps or duplicates."""
    errors: list[str] = []
    numbers = [r.number for r in rows]
    if any(n is None for n in numbers):
        errors.append(
            "one or more rows have a non-integer or missing iteration number"
        )
        return errors
    expected = list(range(1, len(rows) + 1))
    if numbers != expected:
        errors.append(
            f"iteration numbers must be sequential 1..{len(rows)}, got {numbers}"
        )
    return errors


def check_review_round_count(
    iteration_count: int, review_round_count: int
) -> list[str]:
    """Every iteration must have produced at least one review round."""
    errors: list[str] = []
    if iteration_count > review_round_count:
        errors.append(
            f"progress.md has {iteration_count} iteration rows but "
            f"review.md only has {review_round_count} review-round headers; "
            "every iteration MUST have at least one staged-review round "
            "appended to review.md"
        )
    return errors


def check_work_directory(work_dir: Path) -> CheckResult:
    """Run all consistency checks on a work directory."""
    result = CheckResult()

    progress_path = work_dir / "progress.md"
    review_path = work_dir / "review.md"

    if not progress_path.is_file():
        result.errors.append(f"progress.md not found at {progress_path}")
        return result
    if not review_path.is_file():
        result.errors.append(f"review.md not found at {review_path}")
        return result

    progress_text = progress_path.read_text(encoding="utf-8")
    review_text = review_path.read_text(encoding="utf-8")

    section = find_iteration_log_section(progress_text)
    if section is None:
        result.warnings.append(
            "progress.md has no '## Iteration Log' / '## 迭代记录' section "
            "— add one if any post-finalization iterations have occurred"
        )
        result.review_round_count = count_review_rounds(review_text)
        return result

    header, data_rows = parse_markdown_table(section)
    if not header:
        result.warnings.append(
            "Iteration Log section has no parseable markdown table "
            "(check the table syntax)"
        )
        result.review_round_count = count_review_rounds(review_text)
        return result

    if not data_rows:
        result.review_round_count = count_review_rounds(review_text)
        return result

    lang = detect_language(header)
    rows = parse_iteration_rows(header, data_rows)
    result.iteration_rows = rows
    result.review_round_count = count_review_rounds(review_text)

    result.errors.extend(check_required_columns(rows, lang))
    result.errors.extend(check_sequential_numbers(rows))
    result.errors.extend(
        check_review_round_count(len(rows), result.review_round_count)
    )
    result.warnings.extend(check_doc_status_columns(rows))

    return result


def format_result(result: CheckResult) -> str:
    """Render CheckResult as machine-readable + human-readable text."""
    lines = [
        f"STATUS={result.status}",
        f"ITERATION_ROWS={len(result.iteration_rows)}",
        f"REVIEW_ROUNDS={result.review_round_count}",
    ]
    for err in result.errors:
        lines.append(f"ERROR:   {err}")
    for warn in result.warnings:
        lines.append(f"WARNING: {warn}")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: iteration_log_check.py <work-directory>",
            file=sys.stderr,
        )
        sys.exit(2)

    work_dir = Path(sys.argv[1]).resolve()
    if not work_dir.is_dir():
        print(f"ERROR: not a directory: {work_dir}", file=sys.stderr)
        sys.exit(2)

    result = check_work_directory(work_dir)
    print(format_result(result))
    sys.exit(1 if result.errors else 0)


if __name__ == "__main__":
    main()
