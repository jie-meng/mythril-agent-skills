#!/usr/bin/env python3
"""Skills Clean Cache - Remove cached files created by skills at runtime.

All skills store cached files under a unified per-user cache directory:
    macOS:   ~/Library/Caches/mythril-skills-cache/
    Linux:   ${XDG_CACHE_HOME:-~/.cache}/mythril-skills-cache/
    Windows: %LOCALAPPDATA%\\mythril-skills-cache\\

The cache contains two categories:
  - **Temp files** (images, exports, etc.) — ephemeral, safe to delete anytime
  - **Repo cache** (git-repo-cache/) — long-lived, shared across skills,
    reusable across sessions; deleting forces re-clone on next use

This command scans the cache, shows what's there (distinguishing the two
categories), and lets the user selectively or fully clean it up.

Usage:
    skills-clean-cache          # Interactive: list + confirm
    skills-clean-cache --force  # Delete without confirmation
    skills-clean-cache --repos  # Interactive: select repos to delete
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

IS_WINDOWS = platform.system() == "Windows"

CACHE_DIR_NAME = "mythril-skills-cache"
REPO_CACHE_DIR = "git-repo-cache"

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


def _enable_windows_ansi() -> None:
    """Enable ANSI escape sequences on Windows 10+ terminals."""
    if not IS_WINDOWS:
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 4)
    except Exception:
        pass


def _ensure_curses() -> None:
    """Import curses, auto-installing windows-curses on Windows if needed."""
    try:
        import curses as _  # noqa: F401
    except ImportError:
        if IS_WINDOWS:
            print("Installing windows-curses ...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "windows-curses"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("Installed. Please re-run the command.")
            sys.exit(0)
        else:
            print(
                "Error: curses module not available. "
                "Please install Python with curses support."
            )
            sys.exit(1)


def get_cache_root() -> Path:
    """Return the unified per-user skill cache root directory."""
    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        base = home / "Library" / "Caches"
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data)
        else:
            base = home / "AppData" / "Local"
    else:
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache_home:
            base = Path(xdg_cache_home)
        else:
            base = home / ".cache"

    return base / CACHE_DIR_NAME


def format_size(size_bytes: int) -> str:
    """Format byte count as human-readable string."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def dir_size(path: Path) -> int:
    """Calculate total size of a directory tree."""
    total = 0
    for f in path.rglob("*"):
        try:
            if f.is_file():
                total += f.stat().st_size
        except OSError:
            pass
    return total


def count_items(path: Path) -> int:
    """Count immediate children (files + dirs) in a directory."""
    return sum(1 for _ in path.iterdir()) if path.is_dir() else 0


def count_repos(repo_cache_path: Path) -> int:
    """Count cached git repos by looking for .git directories."""
    repos_dir = repo_cache_path / "repos"
    if not repos_dir.exists():
        return 0
    return sum(1 for p in repos_dir.rglob(".git") if p.is_dir())


def list_one_level(path: Path) -> list[Path]:
    """Return immediate directory contents, files first."""
    return sorted(
        path.iterdir(),
        key=lambda p: (0 if p.is_file() else 1, p.name.lower()),
    )


def list_cached_repos(repo_cache_path: Path) -> list[tuple[str, int]]:
    """List cached repos as <host>/<owner>/<repo> with their sizes."""
    repos_root = repo_cache_path / "repos"
    if not repos_root.exists():
        return []

    repos: list[tuple[str, int]] = []
    for repo_dir in repos_root.glob("*/*/*"):
        if not repo_dir.is_dir():
            continue
        if not (repo_dir / ".git").exists():
            continue
        repo_rel = repo_dir.relative_to(repos_root).as_posix()
        repos.append((repo_rel, dir_size(repo_dir)))

    repos.sort(key=lambda item: item[0].lower())
    return repos


class RepoEntry:
    """A selectable cached repo."""

    def __init__(self, rel_path: str, abs_path: Path, size: int) -> None:
        self.rel_path = rel_path
        self.abs_path = abs_path
        self.size = size
        self.selected = False


def _curses_repo_select(
    stdscr: Any,
    repos: list[RepoEntry],
    cache_root: Path,
) -> bool | None:
    """Multi-select UI for cached repos. Returns True if confirmed, None if cancelled."""
    import curses

    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_GREEN, -1)

    cursor = 0
    scroll_offset = 0
    total_items = 1 + len(repos)

    # Fixed header lines (not scrollable):
    #   0: === Skill Repo Cache ===
    #   1: Location: <path>/git-repo-cache/repos/
    #   2: Total: <size>
    #   3: (blank)
    #   4: hint
    #   5: (blank)
    HEADER_LINES = 6

    def selected_bytes() -> int:
        return sum(r.size for r in repos if r.selected)

    def _next_selectable(pos: int, direction: int) -> int:
        return (pos + direction) % total_items

    def draw() -> None:
        nonlocal scroll_offset
        stdscr.clear()
        max_y, _ = stdscr.getmaxyx()

        # --- fixed header ---
        try:
            stdscr.addstr(0, 0, "=== Skill Repo Cache ===", curses.A_BOLD)
        except curses.error:
            pass
        try:
            stdscr.addstr(
                1,
                0,
                f"  Location: {cache_root}/{REPO_CACHE_DIR}/repos/",
                curses.A_DIM,
            )
        except curses.error:
            pass
        try:
            total_size = sum(r.size for r in repos)
            stdscr.addstr(
                2,
                0,
                f"  Total: {format_size(total_size)}",
                curses.A_DIM,
            )
        except curses.error:
            pass
        hint = "Up/Down move | Space toggle | a all/none | Enter confirm | q quit"
        try:
            stdscr.addstr(4, 0, f"  {hint}", curses.color_pair(3))
        except curses.error:
            pass

        content_start = HEADER_LINES
        visible_lines = max_y - content_start - 2

        if cursor == 0:
            visual_cursor = 0
        else:
            visual_cursor = 2 + (cursor - 1)

        if visual_cursor < scroll_offset:
            scroll_offset = visual_cursor
        elif visual_cursor >= scroll_offset + visible_lines:
            scroll_offset = visual_cursor - visible_lines + 1

        line = 0

        if line >= scroll_offset and line < scroll_offset + visible_lines:
            screen_row = content_start + (line - scroll_offset)
            all_selected = all(r.selected for r in repos)
            marker = "[x]" if all_selected else "[ ]"
            attr = curses.A_REVERSE if cursor == 0 else 0
            text = f"  {marker}  Select All / Deselect All"
            try:
                stdscr.addstr(screen_row, 0, text, attr | curses.color_pair(1))
            except curses.error:
                pass
        line += 1

        if line >= scroll_offset and line < scroll_offset + visible_lines:
            screen_row = content_start + (line - scroll_offset)
            try:
                stdscr.addstr(screen_row, 0, "  " + "-" * 36, curses.color_pair(1))
            except curses.error:
                pass
        line += 1

        for repo_idx, repo in enumerate(repos):
            if line >= scroll_offset and line < scroll_offset + visible_lines:
                screen_row = content_start + (line - scroll_offset)
                item_cursor = repo_idx + 1
                marker = "[x]" if repo.selected else "[ ]"
                attr = curses.A_REVERSE if cursor == item_cursor else 0
                color = curses.color_pair(2) if repo.selected else curses.color_pair(4)
                size_str = format_size(repo.size)
                main_text = f"    {marker}  {repo.rel_path}/  "
                size_text = f"({size_str})"
                try:
                    stdscr.addstr(screen_row, 0, main_text, attr | color)
                    stdscr.addstr(size_text, attr | curses.A_DIM)
                except curses.error:
                    pass
            line += 1

        count = sum(1 for r in repos if r.selected)
        total = len(repos)
        sel_bytes = selected_bytes()
        footer_row = min(content_start + visible_lines, max_y - 1)
        try:
            stdscr.addstr(
                footer_row,
                0,
                f"  {count}/{total} selected  ",
                curses.color_pair(3),
            )
            stdscr.addstr(
                f"({format_size(sel_bytes)})",
                curses.color_pair(3) | curses.A_DIM,
            )
        except curses.error:
            pass

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord("k"):
            cursor = _next_selectable(cursor, -1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = _next_selectable(cursor, 1)
        elif key == ord(" "):
            if cursor == 0:
                new_val = not all(r.selected for r in repos)
                for r in repos:
                    r.selected = new_val
            else:
                repo_idx = cursor - 1
                if repo_idx < len(repos):
                    repos[repo_idx].selected = not repos[repo_idx].selected
        elif key == ord("a"):
            new_val = not all(r.selected for r in repos)
            for r in repos:
                r.selected = new_val
        elif key in (curses.KEY_ENTER, 10, 13):
            return True
        elif key in (ord("q"), 27):
            return None


def _interactive_repo_delete(repos: list[RepoEntry], cache_root: Path) -> None:
    """Launch curses UI, then delete selected repos."""
    _enable_windows_ansi()
    _ensure_curses()
    import curses

    confirmed = curses.wrapper(_curses_repo_select, repos, cache_root)
    if confirmed is None:
        print("Cancelled.")
        return

    selected = [r for r in repos if r.selected]
    if not selected:
        print("No repos selected for removal.")
        return

    total_deleted = 0
    for repo in selected:
        try:
            shutil.rmtree(repo.abs_path)
            total_deleted += repo.size
            print(f"{GREEN}Removed:{NC} {repo.rel_path}/")
        except Exception as e:
            print(f"{RED}Failed to delete {repo.rel_path}/: {e}{NC}")

    print(
        f"\n{GREEN}Cleaned up {format_size(total_deleted)} ({len(selected)} repo(s)).{NC}"
    )


def main() -> None:
    force = "--force" in sys.argv
    repos_mode = "--repos" in sys.argv

    cache_root = get_cache_root()

    if not cache_root.exists():
        print(f"No skill cache found at {cache_root}/")
        print("Nothing to clean.")
        return

    all_dirs = sorted(p for p in cache_root.iterdir() if p.is_dir())
    loose_files = sorted(p for p in cache_root.iterdir() if p.is_file())

    if not all_dirs and not loose_files:
        print(f"Cache directory is empty: {cache_root}/")
        print("Nothing to clean.")
        return

    repo_cache = cache_root / REPO_CACHE_DIR
    has_repo_cache = repo_cache.exists() and any(repo_cache.iterdir())

    if repos_mode:
        if not has_repo_cache:
            print(f"No repo cache found at {cache_root}/{REPO_CACHE_DIR}/")
            print("Nothing to clean.")
            return
        cached = list_cached_repos(repo_cache)
        if not cached:
            print(f"No repos found in {cache_root}/{REPO_CACHE_DIR}/")
            print("Nothing to clean.")
            return
        repos_root = repo_cache / "repos"
        repos: list[RepoEntry] = []
        for rel, size in cached:
            abs_path = repos_root / rel
            repos.append(RepoEntry(rel, abs_path, size))
        _interactive_repo_delete(repos, cache_root)
        return

    temp_dirs = [d for d in all_dirs if d.name != REPO_CACHE_DIR]

    print(f"{BOLD}=== Skill Cache Contents ==={NC}")
    print(f"  Location: {DIM}{cache_root}/{NC}\n")

    temp_size = 0
    repo_size = 0

    if temp_dirs or loose_files:
        print(f"  {BOLD}Temp files{NC} {DIM}(ephemeral, safe to delete){NC}")
        for d in temp_dirs:
            size = dir_size(d)
            items = count_items(d)
            temp_size += size
            print(
                f"    {d.name}/"
                f"  {DIM}({items} item{'s' if items != 1 else ''},"
                f" {format_size(size)}){NC}"
            )
        for f in loose_files:
            size = f.stat().st_size
            temp_size += size
            print(f"    {f.name}  {DIM}({format_size(size)}){NC}")
        print()

    if has_repo_cache:
        repo_size = dir_size(repo_cache)
        num_repos = count_repos(repo_cache)
        print(
            f"  {BOLD}Repo cache{NC}"
            f" {DIM}(shared across skills, reusable across sessions){NC}"
        )
        print(
            f"    {REPO_CACHE_DIR}/"
            f"  {DIM}({num_repos} repo{'s' if num_repos != 1 else ''},"
            f" {format_size(repo_size)}){NC}"
        )
        print()

    total_size = temp_size + repo_size
    print(f"  {BOLD}Total: {format_size(total_size)}{NC}")

    if total_size == 0:
        print(f"\n{DIM}Cache is empty, nothing to delete.{NC}")
        return

    if not force:
        if has_repo_cache and temp_dirs:
            print(
                f"\n{CYAN}Tip:{NC} To remove only temp files and keep the"
                f" repo cache, answer {BOLD}t{NC}."
            )
            print(f"     To remove only the repo cache, answer {BOLD}r{NC}.")
            try:
                answer = (
                    input(
                        f"\n{YELLOW}Delete: [a]ll / [t]emp only /"
                        f" [r]epo cache only / [N]one?{NC} "
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return

            if answer == "a":
                delete_temp = True
                delete_repos = True
            elif answer == "t":
                delete_temp = True
                delete_repos = False
            elif answer == "r":
                delete_temp = False
                delete_repos = True
            else:
                print("Cancelled.")
                return
        elif has_repo_cache:
            try:
                answer = (
                    input(
                        f"\n{YELLOW}Delete repo cache?"
                        f" (will need to re-clone on next use){NC} [y/N] "
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return
            if answer != "y":
                print("Cancelled.")
                return
            delete_temp = False
            delete_repos = True
        else:
            try:
                answer = (
                    input(f"\n{YELLOW}Delete all cached files?{NC} [y/N] ")
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return
            if answer != "y":
                print("Cancelled.")
                return
            delete_temp = True
            delete_repos = False
    else:
        delete_temp = True
        delete_repos = True

    cleaned_size = 0

    if delete_temp:
        for d in temp_dirs:
            try:
                shutil.rmtree(d)
                cleaned_size += dir_size(d) if d.exists() else 0
            except Exception as e:
                print(
                    f"{RED}Failed to delete {d.name}/: {e}{NC}",
                    file=sys.stderr,
                )
        for f in loose_files:
            try:
                f.unlink()
            except Exception as e:
                print(
                    f"{RED}Failed to delete {f.name}: {e}{NC}",
                    file=sys.stderr,
                )
        cleaned_size += temp_size

    if delete_repos and has_repo_cache:
        try:
            shutil.rmtree(repo_cache)
            cleaned_size += repo_size
        except Exception as e:
            print(
                f"{RED}Failed to delete {REPO_CACHE_DIR}/: {e}{NC}",
                file=sys.stderr,
            )

    parts: list[str] = []
    if delete_temp and (temp_dirs or loose_files):
        parts.append("temp files")
    if delete_repos and has_repo_cache:
        parts.append("repo cache")

    what = " and ".join(parts) if parts else "cache"
    print(f"\n{GREEN}Cleaned up {format_size(cleaned_size)} ({what}).{NC}")


if __name__ == "__main__":
    main()
