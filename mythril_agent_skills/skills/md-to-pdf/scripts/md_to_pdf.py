#!/usr/bin/env python3
"""Markdown to PDF converter CLI for AI coding assistants.

Converts Markdown files to PDF with optional TOC, custom CSS, paper size,
metadata, and file-size optimization.

Requires: markdown-pdf (pip install markdown-pdf)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from markdown_pdf import MarkdownPdf, Section
except ImportError:
    print(
        "ERROR: markdown-pdf is not installed.\n"
        "Install it with: pip install markdown-pdf\n"
        "Or: pip install mythril-agent-skills[md-to-pdf]",
        file=sys.stderr,
    )
    sys.exit(1)


VALID_PAPER_SIZES = [
    "A3", "A3-L", "A4", "A4-L", "A5", "A5-L", "A6", "A6-L",
    "B4", "B4-L", "B5", "B5-L",
    "Letter", "Letter-L", "Legal", "Legal-L",
]


def resolve_output_path(input_path: Path, output: str | None) -> Path:
    """Determine the output PDF path.

    If *output* is provided, use it directly.
    Otherwise, place the PDF next to the input with the same stem.
    """
    if output:
        return Path(output)
    return input_path.with_suffix(".pdf")


def read_css_file(css_path: str) -> str:
    """Read a CSS file and return its contents."""
    p = Path(css_path)
    if not p.exists():
        print(f"ERROR: CSS file not found: {css_path}", file=sys.stderr)
        sys.exit(2)
    return p.read_text(encoding="utf-8")


def convert(
    input_path: Path,
    output_path: Path,
    *,
    toc_level: int = 0,
    paper_size: str = "A4",
    css: str | None = None,
    title: str | None = None,
    author: str | None = None,
    optimize: bool = False,
) -> None:
    """Convert a Markdown file to PDF."""
    md_text = input_path.read_text(encoding="utf-8")

    pdf = MarkdownPdf(toc_level=toc_level, optimize=optimize)

    if title:
        pdf.meta["title"] = title
    if author:
        pdf.meta["author"] = author

    root_dir = str(input_path.parent)
    section = Section(md_text, toc=(toc_level > 0), root=root_dir, paper_size=paper_size)

    if css:
        pdf.add_section(section, user_css=css)
    else:
        pdf.add_section(section)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.save(str(output_path))


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Convert Markdown to PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "file",
        help="Input Markdown file path",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output PDF path (default: same directory and name as input, with .pdf extension)",
    )
    parser.add_argument(
        "--toc",
        type=int,
        default=0,
        metavar="LEVEL",
        help="Generate table of contents from headings up to this level (e.g. 2 = h1-h2). 0 = no TOC (default)",
    )
    parser.add_argument(
        "--paper-size",
        default="A4",
        metavar="SIZE",
        help=f"Paper size (default: A4). Append -L for landscape. Options: {', '.join(VALID_PAPER_SIZES)}",
    )
    parser.add_argument(
        "--css",
        metavar="FILE",
        help="Path to a custom CSS file for styling",
    )
    parser.add_argument(
        "--title",
        help="PDF metadata title",
    )
    parser.add_argument(
        "--author",
        help="PDF metadata author",
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Optimize PDF file size",
    )

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(2)
    if not input_path.is_file():
        print(f"ERROR: Not a file: {args.file}", file=sys.stderr)
        sys.exit(2)

    output_path = resolve_output_path(input_path, args.output)

    css_text = None
    if args.css:
        css_text = read_css_file(args.css)

    if args.paper_size not in VALID_PAPER_SIZES:
        print(
            f"ERROR: Invalid paper size '{args.paper_size}'. "
            f"Valid options: {', '.join(VALID_PAPER_SIZES)}",
            file=sys.stderr,
        )
        sys.exit(2)

    convert(
        input_path,
        output_path,
        toc_level=args.toc,
        paper_size=args.paper_size,
        css=css_text,
        title=args.title,
        author=args.author,
        optimize=args.optimize,
    )

    print(f"PDF saved: {output_path}")


if __name__ == "__main__":
    main()
