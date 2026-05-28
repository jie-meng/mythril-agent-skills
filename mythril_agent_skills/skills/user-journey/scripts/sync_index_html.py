#!/usr/bin/env python3
"""Re-inject the latest journey.json + DESIGN.md tokens into index.html.

Why this exists
---------------
`index.html` carries two inline JSON blocks (`<script id="journey-data">` and
`<script id="design-tokens">`) so that double-clicking the file (file:// URL)
still gives a working viewer — browsers block fetch() against file:// for
sibling files, which would otherwise leave the canvas empty.

The trade-off is that the inline copies go stale the moment anyone edits
`journey.json` or `DESIGN.md`. This script is the dual of `init_workspace.py`:
it reads the *current* source files and rewrites the two inline `<script>`
blocks in place, so the double-click path keeps working.

Phase 3 of the skill (Sync Discipline) treats this as a mandatory gate. The
companion `validate_sync.py` script will flag inline-JSON drift as an error,
so a missed sync gets caught before the user reopens the workspace.

Exit codes:
    0 — index.html updated (or already in sync; no diff)
    1 — workspace structure invalid (missing files, malformed JSON, etc.)

Usage:
    python3 sync_index_html.py <workspace>
    python3 sync_index_html.py <workspace> --check    # exit 1 if drift exists, no write
    python3 sync_index_html.py <workspace> --quiet

Pure stdlib (Python 3.10+).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"

SCRIPT_DIR = Path(__file__).resolve().parent

# Import the YAML mini-parser from init_workspace.py to keep one source of
# truth for the design-token shape. The init script is already on the same
# `scripts/` directory.
sys.path.insert(0, str(SCRIPT_DIR))
from init_workspace import parse_design_frontmatter  # noqa: E402


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

_JOURNEY_BLOCK_RE = re.compile(
    r'(<script\s+id="journey-data"\s+type="application/json">)'
    r'(.*?)'
    r'(</script>)',
    flags=re.DOTALL,
)
_DESIGN_BLOCK_RE = re.compile(
    r'(<script\s+id="design-tokens"\s+type="application/json">)'
    r'(.*?)'
    r'(</script>)',
    flags=re.DOTALL,
)


def serialize_journey(journey: dict) -> str:
    """Match init_workspace.py exactly so byte-equality is achievable."""
    return json.dumps(journey, indent=2, ensure_ascii=False)


def serialize_design_tokens(tokens: dict) -> str:
    """Match init_workspace.py exactly so byte-equality is achievable."""
    return json.dumps(tokens, indent=2, ensure_ascii=False)


def inject_inline_blocks(
    html: str,
    *,
    journey_json: str,
    design_tokens_json: str,
) -> str:
    """Rewrite both inline `<script>` blocks. Raises if either is missing."""
    new_html, n_journey = _JOURNEY_BLOCK_RE.subn(
        lambda m: m.group(1) + journey_json + m.group(3),
        html,
        count=1,
    )
    if n_journey != 1:
        raise ValueError(
            'index.html is missing the <script id="journey-data" '
            'type="application/json"> block; cannot sync.'
        )
    new_html, n_design = _DESIGN_BLOCK_RE.subn(
        lambda m: m.group(1) + design_tokens_json + m.group(3),
        new_html,
        count=1,
    )
    if n_design != 1:
        raise ValueError(
            'index.html is missing the <script id="design-tokens" '
            'type="application/json"> block; cannot sync.'
        )
    return new_html


def extract_inline_journey(html: str) -> str | None:
    """Return the current inline journey-data body, or None if absent."""
    m = _JOURNEY_BLOCK_RE.search(html)
    return m.group(2) if m else None


def extract_inline_design(html: str) -> str | None:
    """Return the current inline design-tokens body, or None if absent."""
    m = _DESIGN_BLOCK_RE.search(html)
    return m.group(2) if m else None


# ---------------------------------------------------------------------------
# Filesystem orchestration
# ---------------------------------------------------------------------------

def run_sync(workspace: Path, *, check_only: bool, quiet: bool) -> int:
    journey_path = workspace / "journey.json"
    design_path = workspace / "DESIGN.md"
    html_path = workspace / "index.html"

    for required in (journey_path, design_path, html_path):
        if not required.exists():
            print(f"{RED}!! missing {required.name}{NC}", file=sys.stderr)
            return 1

    try:
        journey = json.loads(journey_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{RED}!! journey.json is not valid JSON: {exc}{NC}", file=sys.stderr)
        return 1
    design_md = design_path.read_text(encoding="utf-8")
    design_tokens = parse_design_frontmatter(design_md)
    html = html_path.read_text(encoding="utf-8")

    journey_json = serialize_journey(journey)
    design_tokens_json = serialize_design_tokens(design_tokens)

    try:
        new_html = inject_inline_blocks(
            html,
            journey_json=journey_json,
            design_tokens_json=design_tokens_json,
        )
    except ValueError as exc:
        print(f"{RED}!! {exc}{NC}", file=sys.stderr)
        return 1

    if new_html == html:
        if not quiet:
            print(f"{GREEN}OK: index.html already in sync.{NC}")
        return 0

    if check_only:
        if not quiet:
            print(
                f"{RED}!! index.html inline JSON is OUT OF SYNC with "
                f"journey.json / DESIGN.md.{NC}",
                file=sys.stderr,
            )
            print(
                "   Run: python3 SKILL_PATH/scripts/sync_index_html.py "
                f"{workspace}",
                file=sys.stderr,
            )
        return 1

    html_path.write_text(new_html, encoding="utf-8")
    if not quiet:
        print(f"{GREEN}OK: index.html re-inlined journey + design tokens.{NC}")
    return 0


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("workspace", help="path to the user-journey workspace")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if index.html is out of sync; do not write",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress success messages (errors still printed)",
    )
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        print(f"{RED}!! workspace not found: {workspace}{NC}", file=sys.stderr)
        return 1
    return run_sync(workspace, check_only=args.check, quiet=args.quiet)


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
