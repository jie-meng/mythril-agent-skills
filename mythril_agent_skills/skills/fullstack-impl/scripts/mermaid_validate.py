#!/usr/bin/env python3
"""Validate Mermaid diagrams inside Markdown files for 10.2.3 compatibility.

Many platforms used to render Markdown (older GitHub Enterprise,
Confluence, Notion exports, internal wikis, IDE preview plugins) ship
Mermaid 10.2.3 or earlier. Newer syntax causes "Syntax error in text"
rendering failures that block readers — most commonly when the agent
writes ```mermaid blocks with unquoted parentheses inside edge labels.

This script extracts every fenced ```mermaid block from each input file
and runs a focused static lint against patterns that are KNOWN to fail
on Mermaid 10.2.3. Each rule is empirically verified against
`mermaid@10.2.3` (see tests/skills/test_fullstack_impl.py).

Rules:

    1. Edge labels (`A -->|...| B`) in `flowchart` / `graph` blocks
       MUST be wrapped in double quotes when the label contains any of
       `(`, `)`, `[`, `]`, `{`, `}`. Other characters work unquoted.

           A -->|hello (world)| B          ← FAIL
           A -->|"hello (world)"| B        ← OK

    2. `subgraph` titles MUST be wrapped in double quotes when they
       contain `(` or `)`.

           subgraph My (Group)             ← FAIL
           subgraph "My (Group)"           ← OK

    3. Post-10.2.3 node-shape syntax `<id>@{ ... }` is not supported.

           A@{ shape: rect, label: "x" }   ← FAIL

    4. Beta diagram types introduced after 10.2.3 are not supported.

           block-beta                       ← FAIL
           quadrantChart                    ← FAIL
           xychart-beta                     ← FAIL
           sankey-beta, packet-beta,
           architecture-beta, treemap,
           radar, kanban                    ← FAIL

Usage:
    python3 mermaid_validate.py FILE [FILE ...]

Output (machine + human readable):
    STATUS=PASS|FAIL
    BLOCKS_CHECKED=<N>
    Followed by one line per finding:
        ERROR: <file>:<line>: <message>

Exit codes:
    0 — all blocks pass
    1 — at least one issue detected
    2 — invocation error (no files, missing file)
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

MERMAID_FENCE_OPEN = re.compile(r"^(\s*)```mermaid\s*$")
MERMAID_FENCE_CLOSE = re.compile(r"^\s*```\s*$")

EDGE_LABEL_RE = re.compile(r"\|([^|\n]*)\|")
SUBGRAPH_RE = re.compile(r"^\s*subgraph\s+(.*?)\s*$")
NEW_SHAPE_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*@\{")

BETA_DIAGRAM_TYPES = (
    "block-beta",
    "quadrantChart",
    "xychart-beta",
    "sankey-beta",
    "packet-beta",
    "architecture-beta",
    "treemap",
    "radar",
    "kanban",
)

FLOWCHART_PREFIXES = ("flowchart", "graph")

EDGE_LABEL_BAD_CHARS = "()[]{}"


@dataclass
class MermaidBlock:
    """A single ```mermaid block extracted from a Markdown file."""

    start_line: int
    end_line: int
    body: list[str]

    @property
    def diagram_type(self) -> str:
        """First non-empty word from the block body (e.g. 'flowchart')."""
        for line in self.body:
            stripped = line.strip()
            if not stripped or stripped.startswith("%%"):
                continue
            return stripped.split()[0] if stripped else ""
        return ""


@dataclass
class Issue:
    """A single lint finding for one mermaid block."""

    file: str
    line: int
    rule: str
    message: str

    def format(self) -> str:
        return f"ERROR: {self.file}:{self.line}: [{self.rule}] {self.message}"


def extract_mermaid_blocks(text: str) -> list[MermaidBlock]:
    """Extract every ```mermaid block from Markdown text.

    Returns blocks with 1-based line numbers pointing at the opening and
    closing fences. The body excludes the fences themselves.
    """
    lines = text.splitlines()
    blocks: list[MermaidBlock] = []
    in_block = False
    cur_start = 0
    cur_body: list[str] = []
    for idx, line in enumerate(lines, start=1):
        if not in_block:
            if MERMAID_FENCE_OPEN.match(line):
                in_block = True
                cur_start = idx
                cur_body = []
            continue
        if MERMAID_FENCE_CLOSE.match(line):
            blocks.append(
                MermaidBlock(start_line=cur_start, end_line=idx, body=cur_body)
            )
            in_block = False
            cur_body = []
            continue
        cur_body.append(line)
    return blocks


def is_quoted(label: str) -> bool:
    """Return True iff label is wrapped in matching double quotes."""
    s = label.strip()
    return len(s) >= 2 and s.startswith('"') and s.endswith('"')


def find_edge_label_issues(line: str) -> list[tuple[int, str]]:
    """Return (column, label) tuples for unquoted edge labels with bad chars.

    The column is 1-based and points at the opening pipe of the offending
    label. Only the labels that actually need quoting are returned.
    """
    issues: list[tuple[int, str]] = []
    for match in EDGE_LABEL_RE.finditer(line):
        label = match.group(1)
        if is_quoted(label):
            continue
        if any(ch in label for ch in EDGE_LABEL_BAD_CHARS):
            issues.append((match.start() + 1, label))
    return issues


def find_subgraph_issue(line: str) -> str | None:
    """Return the offending title if a subgraph line has unquoted parens."""
    match = SUBGRAPH_RE.match(line)
    if not match:
        return None
    title = match.group(1).strip()
    if not title:
        return None
    if is_quoted(title):
        return None
    if "(" in title or ")" in title:
        return title
    return None


def find_new_shape_issue(line: str) -> str | None:
    """Return the offending substring if line uses post-10.2.3 @{ ... }."""
    match = NEW_SHAPE_RE.search(line)
    return match.group(0) if match else None


def find_beta_diagram_issue(diagram_type: str) -> str | None:
    """Return the diagram type if it is a post-10.2.3 beta type."""
    if diagram_type in BETA_DIAGRAM_TYPES:
        return diagram_type
    return None


def lint_block(block: MermaidBlock, file: str) -> list[Issue]:
    """Lint one mermaid block, returning all issues found.

    File is the displayed path passed through to the issue. Line numbers
    are 1-based against the original Markdown file (i.e. block.start_line
    + index inside the body + 1).
    """
    issues: list[Issue] = []
    diagram_type = block.diagram_type

    beta = find_beta_diagram_issue(diagram_type)
    if beta is not None:
        issues.append(
            Issue(
                file=file,
                line=block.start_line + 1,
                rule="beta-diagram-type",
                message=(
                    f"diagram type '{beta}' is not supported in Mermaid 10.2.3 "
                    f"(introduced after 10.2.3)"
                ),
            )
        )

    is_flowchart = any(
        diagram_type.startswith(prefix) for prefix in FLOWCHART_PREFIXES
    )

    for offset, raw_line in enumerate(block.body, start=1):
        line_no = block.start_line + offset
        line_for_lint = _strip_line_comment(raw_line)

        new_shape = find_new_shape_issue(line_for_lint)
        if new_shape:
            issues.append(
                Issue(
                    file=file,
                    line=line_no,
                    rule="new-shape-syntax",
                    message=(
                        f"node-shape syntax '{new_shape}...' is not supported "
                        f"in Mermaid 10.2.3 (introduced in 11.x); use the "
                        f"basic shapes [rect], (round), {{diamond}}, etc."
                    ),
                )
            )

        if is_flowchart:
            for col, label in find_edge_label_issues(line_for_lint):
                issues.append(
                    Issue(
                        file=file,
                        line=line_no,
                        rule="unquoted-edge-label",
                        message=(
                            f"edge label '{label.strip()}' contains "
                            f"'(', ')', '[', ']', '{{' or '}}' but is not "
                            f"wrapped in double quotes; this fails to parse "
                            f"in Mermaid 10.2.3 — wrap the label in quotes: "
                            f'|"{label.strip()}"|'
                        ),
                    )
                )

            sub_title = find_subgraph_issue(line_for_lint)
            if sub_title is not None:
                issues.append(
                    Issue(
                        file=file,
                        line=line_no,
                        rule="unquoted-subgraph-title",
                        message=(
                            f"subgraph title '{sub_title}' contains parens "
                            f"but is not quoted; wrap it: "
                            f'subgraph "{sub_title}"'
                        ),
                    )
                )

    return issues


def _strip_line_comment(line: str) -> str:
    """Strip Mermaid line comments (`%% ...`) from a line of source."""
    idx = line.find("%%")
    if idx < 0:
        return line
    return line[:idx]


def lint_file(path: Path) -> tuple[int, list[Issue]]:
    """Lint a single Markdown file. Returns (block_count, issues)."""
    text = path.read_text(encoding="utf-8")
    blocks = extract_mermaid_blocks(text)
    all_issues: list[Issue] = []
    for block in blocks:
        all_issues.extend(lint_block(block, str(path)))
    return len(blocks), all_issues


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print(
            "usage: mermaid_validate.py FILE [FILE ...]",
            file=sys.stderr,
        )
        return 2

    total_blocks = 0
    total_issues: list[Issue] = []
    for raw in args:
        path = Path(raw)
        if not path.is_file():
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            return 2
        blocks, issues = lint_file(path)
        total_blocks += blocks
        total_issues.extend(issues)

    status = "FAIL" if total_issues else "PASS"
    print(f"STATUS={status}")
    print(f"BLOCKS_CHECKED={total_blocks}")
    for issue in total_issues:
        print(issue.format())
    return 1 if total_issues else 0


if __name__ == "__main__":
    sys.exit(main())
