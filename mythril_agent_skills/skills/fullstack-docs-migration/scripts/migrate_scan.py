#!/usr/bin/env python3
"""Scan a legacy fullstack docs repo and inventory its structure.

This script is the deterministic front-end for the fullstack-docs-migration
skill. It walks the legacy structure (top-level feat/refactor/fix/spike
directories), reads each work directory's documents, and outputs a JSON
inventory that the AI agent uses to plan the migration.

The script only READS. It never moves, renames, or deletes anything.

Usage:
    python3 migrate_scan.py <docs-dir>

Output (JSON):
    {
      "work_items": [ {old_path, type, name, four_files, plan_status,
                       progress_status, last_active, matching_spike} ],
      "spikes": [ {old_path, name, verdict, impl_counterpart} ],
      "non_convention_dirs": ["docs", ...]
    }
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

WORK_TYPES = ("feat", "refactor", "fix")

# Completion markers in progress.md (case-insensitive substring match).
COMPLETION_MARKERS = (
    "complete",
    "completed",
    "done",
    "已完成",
    "已合并",
    "merged",
    "shipped",
)


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


def extract_progress_status(text: str) -> str:
    """Extract a completion marker from progress.md, or empty."""
    if not text:
        return ""
    lowered = text.lower()
    for marker in COMPLETION_MARKERS:
        if marker in lowered:
            # Return the canonical marker (skip the empty first element).
            marker_lower = marker.lower()
            return marker_lower
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


def last_active_date(root: Path, item_dir: Path, name: str) -> str:
    """Best-effort last-active date: git log, else empty."""
    return git_last_commit_date(root, str(item_dir.relative_to(root)))


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
            items.append(
                {
                    "old_path": f"{work_type}/{name}",
                    "type": work_type,
                    "name": name,
                    "four_files": four_files,
                    "plan_status": plan_status,
                    "progress_status": progress_status,
                    "last_active": last_active_date(root, item_dir, name),
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
