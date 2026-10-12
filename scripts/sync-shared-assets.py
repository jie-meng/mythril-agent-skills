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
    mermaid_consumers = (
        "fullstack-apply",
        "fullstack-propose",
        "fullstack-brief",
        "user-journey",
    )
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

    # --- shared/graphify/graphify_check.py → <skill>/scripts/graphify_check.py
    graphify_consumers = (
        "fullstack-init",
        "fullstack-apply",
        "fullstack-explore",
        "fullstack-propose",
        "fullstack-archive",
        "fullstack-brief",
    )
    graphify_source = SHARED_ROOT / "graphify" / "graphify_check.py"
    out.append(
        SyncSpec(
            source=graphify_source,
            targets=tuple(
                SKILLS_ROOT / skill / "scripts" / "graphify_check.py"
                for skill in graphify_consumers
            ),
            description="graphify-out check script",
        )
    )

    # --- shared/waves/compute_waves.py → <skill>/scripts/compute_waves.py
    # Canonical dependency-wave calculator for the fullstack family:
    # apply layers repos into parallel waves; propose validates the
    # plan's DAG at authoring time.
    waves_consumers = (
        "fullstack-apply",
        "fullstack-propose",
    )
    waves_source = SHARED_ROOT / "waves" / "compute_waves.py"
    out.append(
        SyncSpec(
            source=waves_source,
            targets=tuple(
                SKILLS_ROOT / skill / "scripts" / "compute_waves.py"
                for skill in waves_consumers
            ),
            description="dependency-wave calculator script",
        )
    )

    # --- shared/plan/plan_lint.py → <skill>/scripts/plan_lint.py
    # Cross-document consistency gate: propose runs it before handing a
    # plan to apply; apply runs it before finalizing the work item.
    plan_consumers = (
        "fullstack-apply",
        "fullstack-propose",
    )
    plan_source = SHARED_ROOT / "plan" / "plan_lint.py"
    out.append(
        SyncSpec(
            source=plan_source,
            targets=tuple(
                SKILLS_ROOT / skill / "scripts" / "plan_lint.py"
                for skill in plan_consumers
            ),
            description="work-tracking document linter",
        )
    )

    # --- shared/workspace/check_workspace.py → <skill>/scripts/check_workspace.py
    # Workspace-validation gate: every skill that refuses to run outside an
    # initialized fullstack workspace bundles its own copy, because skills
    # install individually and must stay self-contained.
    workspace_consumers = (
        "fullstack-apply",
        "fullstack-archive",
        "fullstack-issue-create",
        "fullstack-propose",
    )
    workspace_source = SHARED_ROOT / "workspace" / "check_workspace.py"
    out.append(
        SyncSpec(
            source=workspace_source,
            targets=tuple(
                SKILLS_ROOT / skill / "scripts" / "check_workspace.py"
                for skill in workspace_consumers
            ),
            description="workspace validation gate script",
        )
    )

    # --- shared/git/repo_manager.py → <skill>/scripts/repo_manager.py
    git_consumers = (
        "git-repo-reader",
        "github-code-review-pr",
    )
    git_source = SHARED_ROOT / "git" / "repo_manager.py"
    out.append(
        SyncSpec(
            source=git_source,
            targets=tuple(
                SKILLS_ROOT / skill / "scripts" / "repo_manager.py"
                for skill in git_consumers
            ),
            description="git clone/cache manager",
        )
    )

    # --- shared/plan/review-formats.md → <skill>/references/review-formats.md
    # The review-record format both stages of the fullstack flow write to.
    review_format_consumers = (
        "fullstack-apply",
        "fullstack-propose",
    )
    review_format_source = SHARED_ROOT / "plan" / "review-formats.md"
    out.append(
        SyncSpec(
            source=review_format_source,
            targets=tuple(
                SKILLS_ROOT / skill / "references" / "review-formats.md"
                for skill in review_format_consumers
            ),
            description="review record format",
        )
    )

    # --- shared/plan/document-templates.md → <skill>/references/document-templates.md
    # The four work-tracking document templates.
    templates_consumers = (
        "fullstack-apply",
        "fullstack-propose",
    )
    templates_source = SHARED_ROOT / "plan" / "document-templates.md"
    out.append(
        SyncSpec(
            source=templates_source,
            targets=tuple(
                SKILLS_ROOT / skill / "references" / "document-templates.md"
                for skill in templates_consumers
            ),
            description="work-tracking document templates",
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
