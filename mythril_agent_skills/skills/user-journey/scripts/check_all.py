#!/usr/bin/env python3
"""Run all four user-journey sync gates in one command.

Order:
    1. sync_index_html.py   — re-inline journey.json + DESIGN.md into index.html
                              (with --check: report drift, write nothing)
    2. validate_sync.py     — JOURNEY.md <-> journey.json drift (+ inline drift)
    3. validate_screens.py  — screens + arrows rules (--strict before "done")
    4. mermaid_lint.py      — mermaid compatibility of JOURNEY.md

The inline sync runs first so Gate 2's inline-drift check sees fresh copies.
Every gate runs even if an earlier one fails, so one pass shows all problems.

Exit codes:
    0 — all gates passed
    1 — at least one gate failed

Usage:
    python3 check_all.py <workspace>
    python3 check_all.py <workspace> --strict   # before declaring the journey done
    python3 check_all.py <workspace> --check    # read-only: never writes index.html

Pure stdlib (Python 3.10+).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def build_gate_commands(
    workspace: Path,
    *,
    strict: bool = False,
    check_only: bool = False,
    python: str = sys.executable,
    script_dir: Path = SCRIPT_DIR,
) -> list[tuple[str, list[str]]]:
    """Return (gate name, argv) pairs in run order. Pure: no side effects."""
    ws = str(workspace)
    sync_cmd = [python, str(script_dir / "sync_index_html.py"), ws, "--quiet"]
    if check_only:
        sync_cmd.append("--check")
    screens_cmd = [python, str(script_dir / "validate_screens.py"), ws]
    if strict:
        screens_cmd.append("--strict")
    sync_md_cmd = [python, str(script_dir / "validate_sync.py"), ws]
    lint_cmd = [
        python,
        str(script_dir / "mermaid_lint.py"),
        str(workspace / "JOURNEY.md"),
    ]
    return [
        ("inline sync (index.html)", sync_cmd),
        ("JOURNEY.md <-> journey.json", sync_md_cmd),
        ("screens + arrows", screens_cmd),
        ("mermaid lint", lint_cmd),
    ]


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("workspace", help="path to the user-journey workspace")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="strict screens gate (screen-count floor becomes an error)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="read-only: verify index.html is in sync instead of rewriting it",
    )
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        print(f"!! workspace not found: {workspace}", file=sys.stderr)
        return 1

    results: list[tuple[str, int]] = []
    for name, cmd in build_gate_commands(
        workspace, strict=args.strict, check_only=args.check
    ):
        print(f"--- gate: {name}", flush=True)
        code = subprocess.run(cmd, check=False).returncode
        results.append((name, code))

    print("--- summary")
    for name, code in results:
        print(f"{'PASS' if code == 0 else 'FAIL'}  {name}")
    failed = [name for name, code in results if code != 0]
    print(f"STATUS={'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
