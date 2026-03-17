#!/usr/bin/env python3
"""Initialize an independent fork from a cloned mythril-agent-skills repository.

Removes git history, creates a fresh git repo, and optionally renames the
root directory. The Python package name (mythril_agent_skills) is kept
unchanged so all scripts, imports, and entry points continue to work.

THIS IS A DESTRUCTIVE, ONE-TIME OPERATION. It cannot be undone.

Usage:
    python3 scripts/init-fork.py              # Interactive
    python3 scripts/init-fork.py --dry-run     # Preview only
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"

REPO_ROOT = Path(__file__).resolve().parent.parent


def remove_git_dir(root: Path, dry_run: bool) -> None:
    """Remove the .git directory."""
    git_dir = root / ".git"
    if not git_dir.is_dir():
        print(f"  No .git directory found — skipping.")
        return
    if dry_run:
        print(f"  Would remove: .git/")
    else:
        shutil.rmtree(git_dir)
        print(f"  Removed: .git/")


def init_git(cwd: Path, dry_run: bool) -> None:
    """Initialize a fresh git repository (without committing)."""
    if dry_run:
        print(f"  Would run: git init")
    else:
        subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
        print(f"  Initialized empty git repo.")


def rename_root_dir(root: Path, new_name: str, dry_run: bool) -> Path:
    """Rename the repository root directory. Returns the new path."""
    if root.name == new_name:
        print(f"  Root directory already named '{new_name}' — skipping.")
        return root

    new_root = root.parent / new_name
    if new_root.exists():
        print(f"  {RED}Directory {new_root} already exists — cannot rename.{NC}")
        return root

    if dry_run:
        print(f"  Would rename: {root.name}/ → {new_name}/")
        return root
    else:
        root.rename(new_root)
        print(f"  Renamed: {root.name}/ → {new_name}/")
        return new_root


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    print(f"\n{BOLD}{'=' * 56}{NC}")
    print(f"{BOLD}  Initialize Independent Fork{NC}")
    print(f"{BOLD}{'=' * 56}{NC}\n")

    print(f"  {RED}{BOLD}WARNING: This is a destructive, one-time operation.{NC}")
    print(f"  It will:")
    print(f"    1. Delete .git history (sever link to upstream)")
    print(f"    2. Run git init (empty repo, no commit)")
    print(f"    3. Optionally rename the root directory")
    print(f"\n  {YELLOW}This cannot be undone. Make sure you are working on a")
    print(f"  fresh clone, not your only copy.{NC}\n")

    if not (REPO_ROOT / "mythril_agent_skills").is_dir():
        print(f"  {RED}Error: Cannot find mythril_agent_skills/ directory.{NC}")
        print(f"  Are you running this from the correct repository?")
        sys.exit(1)

    try:
        answer = input(f"  Continue? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Aborted.")
        sys.exit(1)
    if answer != "y":
        print("  Aborted.")
        sys.exit(0)

    mode_label = f" {DIM}(dry run){NC}" if dry_run else ""

    # --- Step 1: Remove .git ---
    print(f"\n{BOLD}--- Step 1: Remove .git{mode_label}{NC}\n")
    remove_git_dir(REPO_ROOT, dry_run)

    # --- Step 2: git init ---
    print(f"\n{BOLD}--- Step 2: Initialize fresh git repo{mode_label}{NC}\n")
    init_git(REPO_ROOT, dry_run)

    # --- Step 3: Optionally rename root directory ---
    print(f"\n{BOLD}--- Step 3: Rename root directory (optional){mode_label}{NC}\n")
    try:
        new_name = input(
            f"  Enter new directory name, or press Enter to keep '{REPO_ROOT.name}'\n"
            f"  New name: "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        new_name = ""

    if new_name:
        new_root = rename_root_dir(REPO_ROOT, new_name, dry_run)
    else:
        new_root = REPO_ROOT
        print(f"  Keeping current name: {REPO_ROOT.name}/")

    # --- Done ---
    print(f"\n{BOLD}{'=' * 56}{NC}")
    print(f"{GREEN}{BOLD}  Done!{NC}")
    print(f"{BOLD}{'=' * 56}{NC}\n")

    final_dir = new_root if not dry_run else (REPO_ROOT.parent / new_name if new_name else REPO_ROOT)
    print(f"  Your new repository is ready at:")
    print(f"    {BOLD}{final_dir}{NC}\n")
    renamed = new_name and new_root != REPO_ROOT

    if renamed:
        print(f"  {YELLOW}Note: Your shell prompt may still show the old directory name.")
        print(f"  Run the command below to refresh it:{NC}\n")
        print(f"    {BOLD}cd .{NC}\n")

    print(f"  Next steps:")
    step = 1
    if renamed:
        print(f"    {step}. cd .                    # refresh shell path")
        step += 1
    print(f"    {step}. git add . && git commit -m 'Initial commit'")
    step += 1
    print(f"    {step}. Create a new repo on GitHub / GitLab / Gitee / etc.")
    step += 1
    print(f"    {step}. git remote add origin <your-repo-url>")
    step += 1
    print(f"    {step}. git push -u origin main")
    print(f"\n  {DIM}The Python package name (mythril_agent_skills) is unchanged,")
    print(f"  so all scripts, imports, and CLI commands work as before.{NC}\n")


if __name__ == "__main__":
    main()
