#!/usr/bin/env python3
"""Scan a legacy fullstack docs repo and inventory its structure.

This script is the deterministic front-end for the fullstack-docs-migration
skill. It walks the legacy structure (top-level feat/refactor/fix/spike
directories), reads each work directory's documents, and outputs a JSON
inventory that the AI agent uses to plan the migration.

The script only READS. It never moves, renames, or deletes anything.

Usage:
    python3 migrate_scan.py <docs-dir>

Exit codes: 0 = inventory printed, 1 = <docs-dir> is not a git repository,
2 = usage error / not a directory.

Output (JSON):
    {
      "work_items": [ {old_path, type, name, four_files, plan_status,
                       progress_status, last_active, last_active_source,
                       matching_spike} ],
      "spikes": [ {old_path, name, verdict, impl_counterpart} ],
      "non_convention_dirs": ["docs", ...]
    }
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

WORK_TYPES = ("feat", "refactor", "fix")

# Completion markers in progress.md, matched as whole words (so
# "Incomplete", "undone", "abandoned" never count) and mapped to a
# canonical value. Chinese markers carry the 已 prefix, so 未完成 / 尚未合并
# cannot match.
COMPLETION_WORDS = {
    "complete": "complete",
    "completed": "complete",
    "done": "done",
    "finished": "done",
    "merged": "merged",
    "shipped": "shipped",
}
COMPLETION_WORD_RE = re.compile(
    r"(?<![A-Za-z])(" + "|".join(COMPLETION_WORDS) + r")(?![A-Za-z])", re.I
)
COMPLETION_ZH = ("已完成", "已合并", "已上线")
# A marker preceded (within three words) by one of these is not a claim of
# completion: "not done", "not yet merged", "almost complete".
NEGATION_WORDS = frozenset(
    {
        "not", "never", "no", "isn't", "wasn't", "aren't", "hasn't",
        "haven't", "nothing", "almost", "nearly", "partially", "half",
    }
)
STATUS_LINE_RE = re.compile(r"(?i)\bstatus\b|状态")
UNCHECKED_BOX_RE = re.compile(r"^\s*[-*]\s*\[\s\]")
ISO_DATE_RE = re.compile(r"(?<!\d)(20\d{2})-(\d{2})-(\d{2})(?!\d)")


def read_file_text(path: Path) -> str:
    """Read a file as UTF-8, tolerating missing files and decode errors."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def extract_status(text: str) -> str:
    """Extract the raw **Status**: value from a document, or empty."""
    match = re.search(r"\*\*Status\*\*[:：]\s*(.+)", text)
    if match:
        return match.group(1).strip()
    match = re.search(r"\*\*状态\*\*[:：]\s*(.+)", text)
    if match:
        return match.group(1).strip()
    return ""


def _line_marker(line: str) -> str:
    """Return the canonical completion marker one line asserts, or ""."""
    for marker in COMPLETION_ZH:
        if marker in line:
            return marker
    for match in COMPLETION_WORD_RE.finditer(line):
        before = re.findall(r"[A-Za-z']+", line[: match.start()].lower())[-3:]
        if NEGATION_WORDS.intersection(before):
            continue
        return COMPLETION_WORDS[match.group(1).lower()]
    return ""


def extract_progress_status(text: str) -> str:
    """Extract a completion marker from progress.md, or empty.

    Status lines (containing "status" / "状态") decide when present — the
    last one wins, since progress logs append — so "Status: In Progress"
    is not overridden by a stray "done" elsewhere. Without a status line,
    any non-heading line may assert completion. Headings (e.g.
    "## Completed Steps") and unchecked checklist items never count, and
    negated markers ("not done", "almost complete") are ignored.
    """
    if not text:
        return ""
    lines = text.splitlines()
    status_lines = [line for line in lines if STATUS_LINE_RE.search(line)]
    if status_lines:
        return _line_marker(status_lines[-1])
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or UNCHECKED_BOX_RE.match(line):
            continue
        marker = _line_marker(stripped)
        if marker:
            return marker
    return ""


def extract_verdict(text: str) -> str:
    """Extract the **Verdict**: value from a spike verdict.md, or empty."""
    match = re.search(r"\*\*Verdict\*\*[:：]\s*([A-Z_]+)", text)
    if match:
        return match.group(1).strip()
    match = re.search(r"\*\*结论\*\*[:：]\s*(.+)", text)
    if match:
        value = match.group(1).strip()
        if "不可行" in value:
            return "NOT_FEASIBLE"
        if "更多调研" in value or "更多研究" in value:
            return "NEEDS_MORE_RESEARCH"
        if "可行" in value:
            return "FEASIBLE"
    return ""


def git_last_commit_date(root: Path, rel_path: str) -> str:
    """Return the date (YYYY-MM-DD) of the last commit touching rel_path."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%cs", "--", rel_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        value = result.stdout.strip()
        return value if value else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def latest_date_in_text(text: str, today: date | None = None) -> str:
    """Return the latest valid ISO date (YYYY-MM-DD) in text, not in the future."""
    limit = today or date.today()
    best: date | None = None
    for year, month, day in ISO_DATE_RE.findall(text):
        try:
            found = date(int(year), int(month), int(day))
        except ValueError:
            continue
        if found <= limit and (best is None or found > best):
            best = found
    return best.isoformat() if best else ""


def last_active_info(root: Path, item_dir: Path) -> tuple[str, str]:
    """Return (date, source) for a work item's last activity.

    Sources, in order: the last git commit touching the directory
    (`git`), the latest date written in progress.md (`progress`), the
    newest file modification time (`mtime`). ("", "") when none applies.
    """
    committed = git_last_commit_date(root, str(item_dir.relative_to(root)))
    if committed:
        return committed, "git"
    written = latest_date_in_text(read_file_text(item_dir / "progress.md"))
    if written:
        return written, "progress"
    mtimes = [p.stat().st_mtime for p in item_dir.rglob("*") if p.is_file()]
    if mtimes:
        return datetime.fromtimestamp(max(mtimes)).date().isoformat(), "mtime"
    return "", ""


def last_active_date(root: Path, item_dir: Path, name: str = "") -> str:
    """Best-effort last-active date; see `last_active_info`."""
    return last_active_info(root, item_dir)[0]


def is_git_work_tree(root: Path) -> bool:
    """True when root is inside a git work tree (and git is installed)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def normalize_name(name: str) -> str:
    """Normalize a directory name for matching: lowercase, hyphens to underscores."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def find_impl_counterpart(spike_dir: Path, root: Path, work_dirs: dict[str, list[Path]]) -> Path | None:
    """Find an impl work directory whose name matches this spike's name."""
    spike_name = normalize_name(spike_dir.name)
    if not spike_name:
        return None
    for work_type in WORK_TYPES:
        for candidate in work_dirs.get(work_type, []):
            if normalize_name(candidate.name) == spike_name:
                return candidate
    return None


def scan_work_items(root: Path) -> tuple[list[dict], dict[str, list[Path]]]:
    """Inventory feat/refactor/fix work items and collect impl dirs by type."""
    work_dirs: dict[str, list[Path]] = {t: [] for t in WORK_TYPES}
    items: list[dict] = []

    for work_type in WORK_TYPES:
        type_dir = root / work_type
        if not type_dir.is_dir():
            continue
        for item_dir in sorted(type_dir.iterdir()):
            if not item_dir.is_dir():
                continue
            name = item_dir.name
            work_dirs[work_type].append(item_dir)

            four_files = {
                "analysis": (item_dir / "analysis.md").is_file(),
                "plan": (item_dir / "plan.md").is_file(),
                "progress": (item_dir / "progress.md").is_file(),
                "review": (item_dir / "review.md").is_file(),
            }
            plan_status = extract_status(read_file_text(item_dir / "plan.md"))
            progress_status = extract_progress_status(
                read_file_text(item_dir / "progress.md")
            )
            last_active, last_active_source = last_active_info(root, item_dir)
            items.append(
                {
                    "old_path": f"{work_type}/{name}",
                    "type": work_type,
                    "name": name,
                    "four_files": four_files,
                    "plan_status": plan_status,
                    "progress_status": progress_status,
                    "last_active": last_active,
                    "last_active_source": last_active_source,
                    "matching_spike": None,  # filled by scan_spikes
                }
            )

    return items, work_dirs


def scan_spikes(root: Path, work_dirs: dict[str, list[Path]], items: list[dict]) -> list[dict]:
    """Inventory spike directories and find their impl counterparts."""
    spikes: list[dict] = []
    spike_dir = root / "spike"
    if not spike_dir.is_dir():
        return spikes

    for item_dir in sorted(spike_dir.iterdir()):
        if not item_dir.is_dir():
            continue
        verdict = extract_verdict(read_file_text(item_dir / "verdict.md"))
        counterpart = find_impl_counterpart(item_dir, root, work_dirs)
        spikes.append(
            {
                "old_path": f"spike/{item_dir.name}",
                "name": item_dir.name,
                "verdict": verdict,
                "impl_counterpart": str(counterpart.relative_to(root)) if counterpart else None,
            }
        )
        # Back-fill matching_spike on the counterpart work item.
        if counterpart is not None:
            norm = str(counterpart.relative_to(root))
            for item in items:
                if item["old_path"] == norm:
                    item["matching_spike"] = f"spike/{item_dir.name}"

    return spikes


def scan_non_convention_dirs(root: Path) -> list[str]:
    """Top-level directories that are not part of the work-tracking convention."""
    return sorted(
        d.name
        for d in root.iterdir()
        if d.is_dir()
        and not d.name.startswith(".")
        and d.name not in WORK_TYPES
        and d.name not in ("spike", "changes", "archive")
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: migrate_scan.py <docs-dir>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2

    if not is_git_work_tree(root):
        print(
            f"ERROR: not a git repository: {root} — the docs repo must be a "
            "git repo (the migration is committed as one atomic commit)",
            file=sys.stderr,
        )
        return 1

    items, work_dirs = scan_work_items(root)
    spikes = scan_spikes(root, work_dirs, items)
    non_convention = scan_non_convention_dirs(root)

    print(json.dumps(
        {
            "work_items": items,
            "spikes": spikes,
            "non_convention_dirs": non_convention,
        },
        indent=2,
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
