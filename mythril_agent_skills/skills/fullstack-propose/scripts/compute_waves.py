#!/usr/bin/env python3
"""Compute parallel execution waves from a plan.md repository table.

This script is the deterministic core of fullstack-apply Step 4's
dependency-wave model (and fullstack-propose's plan-time DAG check).
It parses the "Affected Repositories" table from a work item's
plan.md, validates the dependency graph, and layers the repositories
into topological waves:

    wave(repo) = 0                                  if no dependencies
    wave(repo) = max(wave(dep) for dep) + 1         otherwise

Repos in the same wave share no dependency edges and may be developed,
reviewed, and committed in parallel. A repo in wave N+1 starts only
after every repo in wave N has committed.

Why a script instead of LLM reasoning: transitive-closure mistakes and
missed cycles are silent failure modes when done by eye. As with
check_workspace.py, this replaces an ad-hoc judgment call with a
deterministic answer.

Usage:
    python3 compute_waves.py <work-dir-or-plan.md>

Output (machine-readable key=value lines, on success):
    REPOS=<count>
    WAVES=<wave count>
    WAVE_1=<repo-a>,<repo-b>
    WAVE_2=<repo-c>
    ...

On structural errors (cycle, unknown/self dependency, duplicate row,
missing table) nothing is announced as valid: every problem found is
printed as an ERROR_ line and the exit code is 1.

Exit codes:
    0 — graph parsed and layered successfully
    1 — structural error(s) in the repository table
    2 — invalid arguments or unreadable input
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Column detectors (case-insensitive substring match against header cells)
_REPO_HEADER = re.compile(r"repositor|^repo\b|仓库")
_DEP_HEADER = re.compile(r"depend|依赖")
_HEADING_EN = re.compile(r"^#+.*affected repos", re.IGNORECASE)
_HEADING_ZH = re.compile(r"^#+.*涉及仓库")

# Values that mean "no dependencies"
_NO_DEP_TOKENS = {"", "-", "—", "–", "--", "none", "n/a", "na", "无", "—无"}

_DEP_SPLIT = re.compile(r"[,，;；、]")


def _normalize_repo(raw: str) -> str:
    """Normalize a repo-name cell: strip decoration and trailing slash."""
    name = raw.strip().strip("`*").strip()
    while name.endswith("/"):
        name = name[:-1].rstrip()
    return name


def _parse_dep_cell(raw: str) -> list[str]:
    """Split a Depends On cell into normalized repo names."""
    deps: list[str] = []
    for token in _DEP_SPLIT.split(raw.replace("`", "")):
        name = _normalize_repo(token)
        if name.lower() in _NO_DEP_TOKENS or name == "":
            continue
        deps.append(name)
    return deps


def _table_rows(lines: list[str]) -> tuple[list[str], list[list[str]]] | None:
    """Find the repositories table; return (header_cells, data_rows).

    Preference order:
      1. The table under an "Affected Repositories"/“涉及仓库” heading.
      2. Any table whose header has both a repo column and a
         dependencies column.

    Returns None when no qualifying table exists.
    """
    candidate = _find_table_after_heading(lines)
    if candidate is not None:
        return candidate
    # Fallback: scan every table for a dual-repo/deps header.
    i = 0
    while i < len(lines):
        block, next_i = _md_table_block(lines, i)
        if block and len(block) >= 2:
            header = _split_header(block[0])
            if _find_columns(header) is not None:
                return header, block[2:]
        i = max(next_i, i + 1)
    return None


def _find_table_after_heading(
    lines: list[str],
) -> tuple[list[str], list[list[str]]] | None:
    """Find the first qualifying pipe table under a repositories heading.

    Scans past prose between the heading and the table; stops at the
    next markdown heading so an unrelated later table is not captured.
    """
    in_target_section = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("#"):
            in_target_section = bool(
                _HEADING_EN.search(line) or _HEADING_ZH.search(line)
            )
            i += 1
            continue
        if in_target_section and line.lstrip().startswith("|"):
            block, next_i = _md_table_block(lines, i)
            if len(block) >= 2:
                header = _split_header(block[0])
                if _find_columns(header) is not None:
                    return header, block[2:]
            i = max(next_i, i + 1)
            continue
        i += 1
    return None


def _md_table_block(lines: list[str], start: int) -> tuple[list[str], int]:
    """Return the pipe-table block beginning at/before `start`, and the
    index of the first line after it. Returns ([], start+1) if none."""
    # Locate first line that looks like a table row.
    i = start
    n = len(lines)
    while i < n and "|" not in lines[i]:
        # Allow at most one blank between prose and table
        if lines[i].strip() == "":
            i += 1
            continue
        break
    if i >= n or "|" not in lines[i] or not lines[i].lstrip().startswith("|"):
        return [], min(i + 1, n)
    block: list[str] = []
    while i < n and lines[i].lstrip().startswith("|"):
        block.append(lines[i])
        i += 1
    return block, i


def _split_header(header_line: str) -> list[str]:
    cleaned = header_line.replace("\\|", "\x00")
    return [c.strip() for c in cleaned.strip().strip("|").split("|")]


def _split_row(row_line: str) -> list[str]:
    cleaned = row_line.replace("\\|", "\x00")
    return [c.strip().replace("\x00", "\\|") for c in cleaned.strip().strip("|").split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c != "")


def _find_columns(header: list[str]) -> tuple[int, int] | None:
    """Return (repo_col_index, deps_col_index), or None."""
    repo_idx = dep_idx = None
    for i, cell in enumerate(header):
        lowered = cell.lower()
        if repo_idx is None and _REPO_HEADER.search(lowered):
            repo_idx = i
        elif dep_idx is None and _DEP_HEADER.search(lowered):
            dep_idx = i
    if repo_idx is None or dep_idx is None:
        return None
    return repo_idx, dep_idx


def parse_plan_tables(plan_text: str) -> dict[str, list[str]]:
    """Parse plan.md text into {repo_name: [dependency names]}.

    Raises ValueError with an ``ERROR_<KIND>`` message for structural
    problems (no table, duplicate rows, self-dependency, unknown
    dependency). Cycle detection happens separately in compute().
    """
    lines = plan_text.splitlines()
    found = _table_rows(lines)
    if found is None:
        raise ValueError(
            "ERROR_NO_REPOS_TABLE=no 'Affected Repositories'/“涉及仓库” "
            "table with Repository and Depends On columns found in plan.md"
        )
    header, data_rows = found
    cols = _find_columns(header)
    assert cols is not None  # guaranteed by callers
    repo_i, dep_i = cols

    graph: dict[str, list[str]] = {}
    declared: set[str] = set()
    problems: list[str] = []

    for raw_row in data_rows:
        cells = _split_row(raw_row)
        if _is_separator_row([c for c in cells]):
            continue
        if all(c == "" for c in cells):
            continue
        repo_raw = cells[repo_i] if repo_i < len(cells) else ""
        dep_raw = cells[dep_i] if dep_i < len(cells) else ""
        repo = _normalize_repo(repo_raw)
        if repo == "" or repo.lower() in _NO_DEP_TOKENS:
            continue
        if repo in graph:
            problems.append(f"ERROR_DUPLICATE_REPO={repo}")
            continue
        declared.add(repo)
        graph[repo] = _parse_dep_cell(dep_raw)

    if not graph:
        raise ValueError("ERROR_NO_REPO_ROWS=repositories table parsed but contained no repo rows")

    # Cross-check only now that every row contributed its name.
    for repo, deps in graph.items():
        if repo in deps:
            problems.append(f"ERROR_SELF_DEPENDENCY={repo}")
        for dep in deps:
            if dep not in declared:
                problems.append(f"ERROR_UNKNOWN_DEP={repo}: {dep}")

    if problems:
        raise ValueError("\n".join(problems))
    return graph


def compute(graph: dict[str, list[str]]) -> dict[str, list[str]]:
    """Layer a validated {repo: deps} graph into topological waves.

    Raises ValueError("CYCLE_REPOS=a,b,c") listing at least the cycle
    members (and anything stuck behind them) when peeling stalls.
    """
    remaining = dict(graph)
    resolved: dict[str, int] = {}
    waves: list[list[str]] = []
    level = 0

    while remaining:
        ready = [
            repo
            for repo, deps in remaining.items()
            if all(dep in resolved for dep in deps)
        ]
        if not ready:
            raise ValueError("CYCLE_REPOS=" + ",".join(sorted(remaining)))
        # Keep within-wave order stable: original declaration order wins.
        order = list(graph.keys())
        ready.sort(key=order.index)
        waves.append(ready)
        for repo in ready:
            resolved[repo] = level
            del remaining[repo]
        level += 1

    return {f"WAVE_{i + 1}": repos for i, repos in enumerate(waves)}


def compute_waves(plan_text: str) -> dict[str, str]:
    """Full pipeline: parse → validate → layer. Returns result fields.

    Raises ValueError on any structural problem; the message contains
    machine-readable ERROR_* / CYCLE_REPOS keys (newline-separated).
    """
    graph = parse_plan_tables(plan_text)
    waves = compute(graph)
    out: dict[str, str] = {"REPOS": str(len(graph))}
    out["WAVES"] = str(len(waves))
    out.update({k: ",".join(v) for k, v in waves.items()})
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: compute_waves.py <work-dir-or-plan.md>", file=sys.stderr)
        return 2

    target = Path(sys.argv[1]).resolve()
    if target.is_dir():
        plan_path = target / "plan.md"
    elif target.is_file():
        plan_path = target
    else:
        print(f"ERROR: not a file or directory: {target}", file=sys.stderr)
        return 2

    try:
        plan_text = plan_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {plan_path}: {exc}", file=sys.stderr)
        return 2

    try:
        result = compute_waves(plan_text)
    except ValueError as exc:
        for line in str(exc).splitlines():
            print(line)
        return 1

    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
