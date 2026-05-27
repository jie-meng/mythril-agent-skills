#!/usr/bin/env python3
"""Sync shared assets from the canonical source to each consumer skill.

The repo holds canonical copies of cross-skill assets under
`mythril_agent_skills/shared/`. To keep each skill self-contained
(skills install individually into per-tool dirs), every consumer
bundles a byte-identical copy under its own `scripts/` or
`references/` directory.

This script is the single tool to keep those copies in sync.

Usage:
    python3 scripts/sync-shared-assets.py           # copy canonical → bundled
    python3 scripts/sync-shared-assets.py --check   # CI mode: nonzero exit on drift
    python3 scripts/sync-shared-assets.py --dry-run # show what would change

Exit codes:
    0 — all bundled copies already match the canonical source (--check)
        or successfully updated (normal mode)
    1 — drift detected (--check mode) or write failed
    2 — invocation error
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "mythril_agent_skills"
SHARED_ROOT = PACKAGE_ROOT / "shared"
SKILLS_ROOT = PACKAGE_ROOT / "skills"


@dataclass(frozen=True)
class SyncSpec:
    """One (canonical-file → bundled-target) mapping."""

    source: Path
    targets: tuple[Path, ...]
    description: str


def specs() -> list[SyncSpec]:
    """Return every (source, targets) sync mapping in this repo.

    Add a new SyncSpec here when introducing a new shared asset.
    """
    out: list[SyncSpec] = []

    # --- shared/mermaid/mermaid_lint.py → <skill>/scripts/mermaid_lint.py
    mermaid_consumers = ("fullstack-impl", "fullstack-spike", "user-journey")
    lint_source = SHARED_ROOT / "mermaid" / "mermaid_lint.py"
    out.append(
        SyncSpec(
            source=lint_source,
            targets=tuple(
                SKILLS_ROOT / skill / "scripts" / "mermaid_lint.py"
                for skill in mermaid_consumers
            ),
            description="mermaid lint script",
        )
    )

    # --- shared/mermaid/MERMAID-RULES.md → <skill>/references/MERMAID-RULES.md
    rules_source = SHARED_ROOT / "mermaid" / "MERMAID-RULES.md"
    out.append(
        SyncSpec(
            source=rules_source,
            targets=tuple(
                SKILLS_ROOT / skill / "references" / "MERMAID-RULES.md"
                for skill in mermaid_consumers
            ),
            description="mermaid rules doc",
        )
    )

    return out


def check_one(spec: SyncSpec) -> tuple[list[Path], list[Path]]:
    """Return (in_sync, out_of_sync) target lists for one spec.

    A target is "out of sync" if it does not exist or differs byte-wise
    from the source.
    """
    if not spec.source.is_file():
        raise FileNotFoundError(f"canonical source missing: {spec.source}")
    in_sync: list[Path] = []
    out_of_sync: list[Path] = []
    for target in spec.targets:
        if target.is_file() and filecmp.cmp(spec.source, target, shallow=False):
            in_sync.append(target)
        else:
            out_of_sync.append(target)
    return in_sync, out_of_sync


def copy_one(spec: SyncSpec, dry_run: bool) -> list[Path]:
    """Copy spec.source → each missing/drifted target. Returns updated list."""
    updated: list[Path] = []
    _, out_of_sync = check_one(spec)
    for target in out_of_sync:
        if dry_run:
            updated.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(spec.source, target)
        updated.append(target)
    return updated


def _rel(path: Path) -> str:
    """Display path relative to REPO_ROOT when possible."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync shared assets to each consumer skill.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI mode: nonzero exit if any bundled copy has drifted",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would change without writing",
    )
    args = parser.parse_args(argv)

    if args.check and args.dry_run:
        print("error: --check and --dry-run are mutually exclusive", file=sys.stderr)
        return 2

    total_drift = 0
    total_targets = 0
    for spec in specs():
        try:
            in_sync, out_of_sync = check_one(spec)
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        total_targets += len(in_sync) + len(out_of_sync)

        if args.check:
            for target in out_of_sync:
                total_drift += 1
                print(
                    f"DRIFT: {spec.description}: {_rel(target)} differs from "
                    f"{_rel(spec.source)}"
                )
            for target in in_sync:
                print(f"OK:    {spec.description}: {_rel(target)}")
            continue

        # write mode (real or dry-run)
        updated = copy_one(spec, dry_run=args.dry_run)
        for target in updated:
            label = "WOULD UPDATE" if args.dry_run else "UPDATED"
            print(f"{label}: {spec.description}: {_rel(target)}")
        for target in in_sync:
            print(f"OK:    {spec.description}: {_rel(target)}")

    if args.check:
        if total_drift:
            print(
                f"\nFAIL: {total_drift} bundled copy/copies drifted from "
                f"canonical source. Run `python3 scripts/sync-shared-assets.py` "
                f"to fix.",
                file=sys.stderr,
            )
            return 1
        print(f"\nPASS: all {total_targets} bundled copies in sync.")
        return 0

    print(f"\nDone. {total_targets} target(s) processed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
