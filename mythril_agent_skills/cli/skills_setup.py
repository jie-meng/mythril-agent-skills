#!/usr/bin/env python3
"""Skills Setup - Interactive installer for AI assistant skill directories.

Provides a curses-based multi-select UI for choosing which skills to install.
Supports macOS, Linux, and Windows (auto-installs windows-curses if needed).

Usage:
    skills-setup            # Interactive mode (after pip install)
    skills-setup .cursor    # Direct target mode
"""

from __future__ import annotations

import filecmp
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

CLI_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CLI_DIR.parent
BUILTIN_SKILLS_DIR = PACKAGE_DIR / "skills"

IS_WINDOWS = platform.system() == "Windows"


@dataclass
class SkillEntry:
    """Represents a skill to be installed, either builtin or local."""

    path: Path
    name: str
    is_local: bool  # False = builtin (from package), True = local (from cwd)
    has_conflict: bool  # local skill whose name matches a builtin skill


TOOLS: list[tuple[str, str, str]] = [
    ("Copilot CLI", ".copilot", "skills"),
    ("Claude Code", ".claude", "skills"),
    ("Cursor", ".cursor", "skills"),
    ("Codex", ".codex", "skills"),
    ("Gemini CLI", ".gemini", "skills"),
    ("Qwen CLI", ".qwen", "skills"),
    ("Opencode", ".config/opencode", "skills"),
    ("Grok CLI", ".grok", "skills"),
    ("OpenClaw", ".openclaw", "skills"),
    ("Hermes", ".hermes", "skills"),
]


# --- Platform bootstrap ---


def _enable_windows_ansi() -> None:
    """Enable ANSI escape sequences on Windows 10+ terminals."""
    if not IS_WINDOWS:
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        # STD_OUTPUT_HANDLE = -11, ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4
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
            )
        else:
            print(
                "Error: curses module not available. "
                "Please install Python with curses support."
            )
            sys.exit(1)


_enable_windows_ansi()
_ensure_curses()

import curses  # noqa: E402 — must import after _ensure_curses()

# --- Colors for non-curses output ---

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
NC = "\033[0m"


# --- Utilities ---


def validate_source() -> None:
    """Ensure the builtin skills directory exists and is non-empty."""
    if not BUILTIN_SKILLS_DIR.is_dir():
        print(f"{RED}Error: Builtin skills directory not found: {BUILTIN_SKILLS_DIR}{NC}")
        sys.exit(1)
    if not any(BUILTIN_SKILLS_DIR.iterdir()):
        print(f"{RED}Error: Builtin skills directory is empty: {BUILTIN_SKILLS_DIR}{NC}")
        sys.exit(1)


def get_builtin_skill_dirs() -> list[Path]:
    """Return sorted list of builtin skill directories from the installed package."""
    return sorted(
        p
        for p in BUILTIN_SKILLS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def get_local_skill_dirs() -> list[Path]:
    """Return sorted skill dirs found in the current working directory.

    Scans immediate non-hidden subdirectories of cwd for a SKILL.md file.
    """
    cwd = Path.cwd()
    return sorted(
        p
        for p in cwd.iterdir()
        if p.is_dir() and not p.name.startswith(".") and (p / "SKILL.md").exists()
    )


def build_skill_entries(
    builtin_dirs: list[Path],
    local_dirs: list[Path],
) -> tuple[list[SkillEntry], list[SkillEntry]]:
    """Build SkillEntry lists for builtin and local skills, with conflict detection.

    A local entry is marked has_conflict=True if its name matches a builtin skill.
    Installing both lets the local version override the builtin.
    Returns (builtin_entries, local_entries).
    """
    builtin_names = {p.name for p in builtin_dirs}
    builtin_entries = [
        SkillEntry(path=p, name=p.name, is_local=False, has_conflict=False)
        for p in builtin_dirs
    ]
    local_entries = [
        SkillEntry(
            path=p,
            name=p.name,
            is_local=True,
            has_conflict=p.name in builtin_names,
        )
        for p in local_dirs
    ]
    return builtin_entries, local_entries


def dirs_differ(src: Path, dst: Path) -> bool:
    """Return True if src and dst directory trees differ."""
    cmp = filecmp.dircmp(src, dst)
    if cmp.left_only or cmp.right_only or cmp.diff_files:
        return True
    for sub in cmp.subdirs.values():
        if sub.left_only or sub.right_only or sub.diff_files:
            return True
    return False


def sync_skill_entries(
    label: str,
    config_dir: str,
    skills_subpath: str,
    entries: list[SkillEntry],
) -> bool:
    """Sync selected skill entries to a tool's config directory.

    Builtin skills are installed first; local skills follow so they override
    builtin skills with the same name.
    """
    config_path = Path.home() / config_dir
    target_skills_dir = config_path / skills_subpath

    if not config_path.is_dir():
        print(
            f"{YELLOW}⚠ {label} is not installed "
            f"(~/{config_dir} not found), skipping.{NC}"
        )
        return False

    target_skills_dir.mkdir(parents=True, exist_ok=True)

    added: list[str] = []
    updated: list[str] = []

    # Builtin first (is_local=False sorts before True), then local by name
    ordered = sorted(entries, key=lambda e: (e.is_local, e.name))

    for entry in ordered:
        skill_name = entry.name
        target_skill = target_skills_dir / skill_name

        if not target_skill.is_dir():
            added.append(skill_name)
        elif dirs_differ(entry.path, target_skill):
            updated.append(skill_name)

        if target_skill.exists():
            shutil.rmtree(target_skill)
        shutil.copytree(entry.path, target_skill)

    print(f"{GREEN}✓ [{label}] Skills synced to {target_skills_dir}{NC}")
    if added:
        print(f"  {GREEN}Added:{NC} {' '.join(added)}")
    if updated:
        print(f"  {YELLOW}Updated:{NC} {' '.join(updated)}")
    if not added and not updated:
        print("  No skill changes detected.")
    return True


# --- Curses multi-select UI ---


def curses_multi_select(
    stdscr: curses.window,
    title: str,
    items: list[str],
    preselected: list[bool] | None = None,
    disabled: set[int] | None = None,
) -> list[int] | None:
    """Interactive multi-select with arrow keys, space, and enter.

    Returns list of selected indices, or None if user cancelled (q/Esc).
    Disabled indices are shown dimmed and cannot be selected or toggled.
    """
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)

    disabled = disabled or set()
    if preselected:
        selected = list(preselected)
    else:
        selected = [False] * len(items)
    for i in disabled:
        selected[i] = False

    cursor = 0
    all_item = "Select All / Deselect All"
    total_items = 1 + len(items)
    enabled_count = len(items) - len(disabled)

    def _next_enabled(pos: int, direction: int) -> int:
        """Find next non-disabled position, wrapping around."""
        candidate = (pos + direction) % total_items
        attempts = 0
        while attempts < total_items:
            if candidate == 0 or candidate - 1 not in disabled:
                return candidate
            candidate = (candidate + direction) % total_items
            attempts += 1
        return 0

    def draw() -> None:
        stdscr.clear()
        stdscr.addstr(0, 0, title, curses.A_BOLD)
        hint = "Up/Down move | Space toggle | a all/none | Enter confirm | q quit"
        stdscr.addstr(1, 0, hint, curses.color_pair(3))

        row = 3
        enabled_sel = [s for i, s in enumerate(selected) if i not in disabled]
        all_selected = bool(enabled_sel) and all(enabled_sel)
        marker = "[x]" if all_selected else "[ ]"
        attr = curses.A_REVERSE if cursor == 0 else 0
        try:
            stdscr.addstr(
                row, 0, f"  {marker}  {all_item}", attr | curses.color_pair(1)
            )
        except curses.error:
            pass

        row += 1
        try:
            stdscr.addstr(row, 0, "  " + "-" * 36, curses.color_pair(1))
        except curses.error:
            pass

        row += 1
        for i, item in enumerate(items):
            is_disabled = i in disabled
            if is_disabled:
                marker = "[-]"
                attr = curses.A_DIM
                color = 0
            else:
                marker = "[x]" if selected[i] else "[ ]"
                attr = curses.A_REVERSE if cursor == i + 1 else 0
                color = curses.color_pair(2) if selected[i] else 0
            try:
                stdscr.addstr(row + i, 0, f"  {marker}  {item}", attr | color)
            except curses.error:
                pass

        count = sum(1 for i, s in enumerate(selected) if s and i not in disabled)
        try:
            stdscr.addstr(
                row + len(items) + 1,
                0,
                f"  {count}/{enabled_count} selected",
                curses.color_pair(3),
            )
        except curses.error:
            pass

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord("k"):
            cursor = _next_enabled(cursor, -1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = _next_enabled(cursor, 1)
        elif key == ord(" "):
            if cursor == 0:
                enabled_sel = [s for i, s in enumerate(selected) if i not in disabled]
                new_val = not (bool(enabled_sel) and all(enabled_sel))
                selected = [
                    new_val if i not in disabled else False for i in range(len(items))
                ]
            elif cursor - 1 not in disabled:
                selected[cursor - 1] = not selected[cursor - 1]
        elif key == ord("a"):
            enabled_sel = [s for i, s in enumerate(selected) if i not in disabled]
            new_val = not (bool(enabled_sel) and all(enabled_sel))
            selected = [
                new_val if i not in disabled else False for i in range(len(items))
            ]
        elif key in (curses.KEY_ENTER, 10, 13):
            return [i for i, s in enumerate(selected) if s and i not in disabled]
        elif key in (ord("q"), 27):
            return None


def select_skills_interactive(
    builtin_entries: list[SkillEntry],
    local_entries: list[SkillEntry],
) -> list[SkillEntry] | None:
    """Launch curses UI to select skills. Returns selected entries or None."""
    return curses.wrapper(_curses_skills_select, builtin_entries, local_entries)


def _curses_skills_select(
    stdscr: curses.window,
    builtin_entries: list[SkillEntry],
    local_entries: list[SkillEntry],
) -> list[SkillEntry] | None:
    """Two-section interactive skill selector.

    Shows builtin skills in the first section and local (cwd-discovered) skills
    in the second section. Local skills that conflict with a builtin skill are
    highlighted in magenta with an "(overrides builtin)" note.

    Returns the selected SkillEntry list, or None if cancelled.
    """
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)      # section headers, info
    curses.init_pair(2, curses.COLOR_GREEN, -1)     # selected items
    curses.init_pair(3, curses.COLOR_YELLOW, -1)    # hints, counts
    curses.init_pair(4, curses.COLOR_WHITE, -1)     # normal items
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)   # conflict items

    # All selectable skills: builtin first, local second
    all_skills: list[SkillEntry] = builtin_entries + local_entries
    n = len(all_skills)
    selected = [False] * n

    # Row structure: ("header", label) — non-navigable separator/heading
    #                ("skill", skill_idx) — navigable, index into all_skills
    rows: list[tuple[str, ...]] = []
    row_to_skill: dict[int, int] = {}  # row index → all_skills index

    rows.append(("header", f"  Builtin Skills ({len(builtin_entries)})"))
    for i in range(len(builtin_entries)):
        row_to_skill[len(rows)] = i
        rows.append(("skill", str(i)))

    if local_entries:
        cwd_label = Path.cwd().name
        rows.append(("header", f"  Local Skills ({len(local_entries)})  [{cwd_label}/]"))
        for j in range(len(local_entries)):
            si = len(builtin_entries) + j
            row_to_skill[len(rows)] = si
            rows.append(("skill", str(si)))

    # cursor: 0 = Select All row, 1..len(rows) = row index (1-based)
    total_positions = 1 + len(rows)
    cursor = 0

    def _is_selectable(pos: int) -> bool:
        if pos == 0:
            return True
        ri = pos - 1
        return ri < len(rows) and rows[ri][0] == "skill"

    def _next(pos: int, d: int) -> int:
        candidate = (pos + d) % total_positions
        for _ in range(total_positions):
            if _is_selectable(candidate):
                return candidate
            candidate = (candidate + d) % total_positions
        return 0

    def draw() -> None:
        stdscr.clear()
        stdscr.addstr(0, 0, "Select skills to install:", curses.A_BOLD)
        stdscr.addstr(
            1,
            0,
            "Up/Down move | Space toggle | a all/none | Enter confirm | q quit",
            curses.color_pair(3),
        )

        # Select All row (position 0)
        all_sel = all(selected)
        marker = "[x]" if all_sel else "[ ]"
        attr = curses.A_REVERSE if cursor == 0 else 0
        try:
            stdscr.addstr(
                3, 0, f"  {marker}  Select All / Deselect All", attr | curses.color_pair(1)
            )
        except curses.error:
            pass
        try:
            stdscr.addstr(4, 0, "  " + "-" * 36, curses.color_pair(1))
        except curses.error:
            pass

        display_row = 5
        for ri, row in enumerate(rows):
            pos = ri + 1
            if row[0] == "header":
                try:
                    stdscr.addstr(
                        display_row, 0, row[1], curses.color_pair(1) | curses.A_BOLD
                    )
                except curses.error:
                    pass
            else:
                si = int(row[1])
                entry = all_skills[si]
                is_sel = selected[si]
                marker = "[x]" if is_sel else "[ ]"
                attr = curses.A_REVERSE if cursor == pos else 0

                if entry.has_conflict:
                    label = f"{entry.name}  (overrides builtin)"
                    color = curses.color_pair(5)  # magenta
                elif is_sel:
                    label = entry.name
                    color = curses.color_pair(2)  # green
                else:
                    label = entry.name
                    color = 0

                try:
                    stdscr.addstr(display_row, 0, f"  {marker}  {label}", attr | color)
                except curses.error:
                    pass

            display_row += 1

        count = sum(selected)
        try:
            stdscr.addstr(
                display_row + 1, 0, f"  {count}/{n} selected", curses.color_pair(3)
            )
        except curses.error:
            pass

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            cursor = _next(cursor, -1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = _next(cursor, 1)
        elif key == ord(" "):
            if cursor == 0:
                new_val = not all(selected)
                selected[:] = [new_val] * n
            elif _is_selectable(cursor):
                si = row_to_skill[cursor - 1]
                selected[si] = not selected[si]
        elif key == ord("a"):
            new_val = not all(selected)
            selected[:] = [new_val] * n
        elif key in (curses.KEY_ENTER, 10, 13):
            return [all_skills[i] for i, s in enumerate(selected) if s]
        elif key in (ord("q"), 27):
            return None


def _detect_uninstalled_tools() -> set[int]:
    """Return indices of tools whose config directories don't exist."""
    uninstalled: set[int] = set()
    for i, (_, config_dir, _) in enumerate(TOOLS):
        if not (Path.home() / config_dir).is_dir():
            uninstalled.add(i)
    return uninstalled


def select_tools_interactive() -> list[int] | None:
    """Launch curses UI to select AI tools. Returns selected indices or None."""
    uninstalled = _detect_uninstalled_tools()
    items = [
        f"{t[0]}  (not installed)" if i in uninstalled else t[0]
        for i, t in enumerate(TOOLS)
    ]
    return curses.wrapper(
        curses_multi_select,
        "Select AI tools to install skills to:",
        items,
        disabled=uninstalled,
    )


# --- CLI modes ---


def run_skills_check(selected_entries: list[SkillEntry]) -> None:
    """Run the dependency checker for selected builtin skills.

    Local skills are excluded — their dependencies are the user's responsibility.
    """
    from mythril_agent_skills.cli.skills_check import main as check_main

    builtin_names = [e.name for e in selected_entries if not e.is_local]
    if not builtin_names:
        return
    sys.stdout.flush()
    original_argv = sys.argv
    sys.argv = ["skills-check"] + builtin_names
    try:
        check_main()
    finally:
        sys.argv = original_argv


def direct_target_mode(target_dir: str) -> None:
    """Install selected skills to a specific target directory."""
    target_path = Path.home() / target_dir
    if not target_path.is_dir():
        print(
            f"{RED}Error: ~/{target_dir} not found. "
            f"The tool does not appear to be installed.{NC}"
        )
        sys.exit(1)

    builtin_dirs = get_builtin_skill_dirs()
    local_dirs = get_local_skill_dirs()
    builtin_entries, local_entries = build_skill_entries(builtin_dirs, local_dirs)

    selected = select_skills_interactive(builtin_entries, local_entries)
    if selected is None or len(selected) == 0:
        print("No skills selected. Aborted.")
        sys.exit(0)

    sync_skill_entries(target_dir, target_dir, "skills", selected)
    run_skills_check(selected)


def interactive_mode() -> None:
    """Full interactive mode: select tools, then select skills."""
    tool_indices = select_tools_interactive()
    if tool_indices is None or len(tool_indices) == 0:
        print("No tools selected. Aborted.")
        sys.exit(0)

    builtin_dirs = get_builtin_skill_dirs()
    local_dirs = get_local_skill_dirs()
    builtin_entries, local_entries = build_skill_entries(builtin_dirs, local_dirs)

    selected_entries = select_skills_interactive(builtin_entries, local_entries)
    if selected_entries is None or len(selected_entries) == 0:
        print("No skills selected. Aborted.")
        sys.exit(0)

    print()
    installed = 0
    skipped = 0

    for idx in tool_indices:
        label, config_dir, skills_subpath = TOOLS[idx]
        if sync_skill_entries(label, config_dir, skills_subpath, selected_entries):
            installed += 1
        else:
            skipped += 1
        print()

    print(
        f"{BOLD}Done.{NC} Installed: {GREEN}{installed}{NC}, "
        f"Skipped: {YELLOW}{skipped}{NC}"
    )

    run_skills_check(selected_entries)


def main() -> None:
    validate_source()

    if len(sys.argv) > 1:
        direct_target_mode(sys.argv[1])
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
