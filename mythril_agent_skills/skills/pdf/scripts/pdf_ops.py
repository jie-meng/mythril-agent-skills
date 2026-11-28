#!/usr/bin/env python3
"""PDF file operations CLI for AI coding assistants.

Provides subcommands for reading, extracting, and manipulating PDF files.

Requires: pypdf (pip install pypdf), pdfplumber (pip install pdfplumber)
Optional: pypdfium2 (pip install pypdfium2) — for PDF-to-image conversion
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print(
        "ERROR: pypdf is not installed.\n"
        "Install it with: pip install pypdf",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import pdfplumber
except ImportError:
    print(
        "ERROR: pdfplumber is not installed.\n"
        "Install it with: pip install pdfplumber",
        file=sys.stderr,
    )
    sys.exit(1)


SKILL_NAME = "pdf"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_cache_root(
    system: str | None = None,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return the per-user mythril-skills-cache root for the given platform."""
    system = system if system is not None else platform.system()
    env = env if env is not None else dict(os.environ)
    home = home if home is not None else Path.home()
    if system == "Darwin":
        return home / "Library" / "Caches" / "mythril-skills-cache"
    if system == "Windows":
        local = env.get("LOCALAPPDATA")
        base = Path(local) if local else home / "AppData" / "Local"
        return base / "mythril-skills-cache"
    xdg = env.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else home / ".cache"
    return base / "mythril-skills-cache"


def output_conflict(output: Path, inputs: list[Path], force: bool) -> str | None:
    """Return an error message if writing *output* is unsafe, else None.

    Writing over an input is always refused (even with --force); an existing
    unrelated file is refused unless *force* is set.
    """
    out_resolved = output.expanduser().resolve()
    for inp in inputs:
        if inp.expanduser().resolve() == out_resolved:
            return (
                f"output {output} is also an input file; "
                "write to a different path"
            )
    if output.exists() and not force:
        return f"output {output} already exists; pass --force to overwrite"
    return None


def _check_outputs(outputs: list[Path], inputs: list[Path], force: bool) -> None:
    """Exit with an error if any planned output is unsafe to write."""
    for out in outputs:
        problem = output_conflict(out, inputs, force)
        if problem:
            print(f"ERROR: {problem}", file=sys.stderr)
            sys.exit(2)


def _resolve_output_dir(raw: str | None, stem: str) -> Path:
    """Return the user's --output-dir, or a fresh run dir in the skill cache."""
    if raw:
        out = Path(raw).expanduser()
        out.mkdir(parents=True, exist_ok=True)
        return out
    cache_dir = get_cache_root() / SKILL_NAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{stem}-", dir=cache_dir))


def _require_file(path: str) -> None:
    """Exit with a clear error if *path* does not exist."""
    if not Path(path).exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(2)


def _parse_page_spec(spec: str, total_pages: int) -> list[int]:
    """Parse a page specification string into a sorted list of 0-based indices.

    Accepts comma-separated values and ranges (1-based):
      "1"       -> [0]
      "1,3,5"   -> [0, 2, 4]
      "1-5"     -> [0, 1, 2, 3, 4]
      "2,5-8"   -> [1, 4, 5, 6, 7]
    """
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = int(start_s)
            end = int(end_s)
            if start < 1 or end > total_pages or start > end:
                print(
                    f"ERROR: Invalid page range '{part}'. "
                    f"Document has {total_pages} pages.",
                    file=sys.stderr,
                )
                sys.exit(2)
            pages.update(range(start - 1, end))
        else:
            page_num = int(part)
            if page_num < 1 or page_num > total_pages:
                print(
                    f"ERROR: Page {page_num} out of range. "
                    f"Document has {total_pages} pages.",
                    file=sys.stderr,
                )
                sys.exit(2)
            pages.add(page_num - 1)
    return sorted(pages)


def _load_reader(path: str) -> PdfReader:
    """Load a PdfReader, handling common errors."""
    p = Path(path)
    if not p.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(2)
    if p.suffix.lower() != ".pdf":
        print(f"ERROR: Not a PDF file: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        return PdfReader(str(p))
    except Exception as exc:
        print(f"ERROR: Cannot read PDF: {exc}", file=sys.stderr)
        sys.exit(2)
        raise  # unreachable, satisfies type checker


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _resolve_pages(
    args: argparse.Namespace, total_pages: int
) -> list[int]:
    """Resolve --pages argument to 0-based page indices, or all pages."""
    if args.pages:
        return _parse_page_spec(args.pages, total_pages)
    return list(range(total_pages))


def _write_pdf(writer: PdfWriter, output_path: str) -> None:
    """Write a PdfWriter to disk."""
    try:
        with open(output_path, "wb") as f:
            writer.write(f)
    except Exception as exc:
        print(f"ERROR: Failed to write PDF: {exc}", file=sys.stderr)
        sys.exit(3)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_info(args: argparse.Namespace) -> None:
    """Show PDF metadata and structure."""
    reader = _load_reader(args.file)
    p = Path(args.file)
    meta = reader.metadata

    print(f"# PDF Info: {p.name}\n")
    print(f"- **Pages**: {len(reader.pages)}")
    print(f"- **File size**: {_format_size(p.stat().st_size)}")
    print(f"- **Encrypted**: {'Yes' if reader.is_encrypted else 'No'}")

    if meta:
        if meta.title:
            print(f"- **Title**: {meta.title}")
        if meta.author:
            print(f"- **Author**: {meta.author}")
        if meta.subject:
            print(f"- **Subject**: {meta.subject}")
        if meta.creator:
            print(f"- **Creator**: {meta.creator}")
        if meta.producer:
            print(f"- **Producer**: {meta.producer}")
        if meta.creation_date:
            print(f"- **Created**: {meta.creation_date}")
        if meta.modification_date:
            print(f"- **Modified**: {meta.modification_date}")

    for i, page in enumerate(reader.pages):
        box = page.mediabox
        w = float(box.width)
        h = float(box.height)
        w_in = w / 72
        h_in = h / 72
        print(
            f"- **Page {i + 1}**: {w:.0f} x {h:.0f} pt "
            f"({w_in:.1f} x {h_in:.1f} in)"
        )


def cmd_text(args: argparse.Namespace) -> None:
    """Extract text from PDF pages."""
    _require_file(args.file)
    with pdfplumber.open(args.file) as pdf:
        total = len(pdf.pages)
        page_indices = _resolve_pages(args, total)

        for idx in page_indices:
            page = pdf.pages[idx]
            if args.layout:
                text = page.extract_text(
                    layout=True, keep_blank_chars=True
                )
            else:
                text = page.extract_text()

            if text:
                print(f"--- Page {idx + 1} ---")
                print(text)
                print()
            else:
                print(f"--- Page {idx + 1} ---")
                print("(no extractable text)")
                print()


def cmd_tables(args: argparse.Namespace) -> None:
    """Extract tables from PDF pages."""
    _require_file(args.file)
    with pdfplumber.open(args.file) as pdf:
        total = len(pdf.pages)
        page_indices = _resolve_pages(args, total)

        all_tables: list[dict[str, Any]] = []
        table_num = 0

        for idx in page_indices:
            page = pdf.pages[idx]
            tables = page.extract_tables()
            if not tables:
                continue
            for table_data in tables:
                if not table_data or not any(table_data):
                    continue
                table_num += 1
                all_tables.append(
                    {
                        "page": idx + 1,
                        "table_number": table_num,
                        "rows": table_data,
                    }
                )

        if not all_tables:
            print("No tables found in the specified pages.")
            return

        fmt = args.format

        if fmt == "json":
            print(json.dumps(all_tables, indent=2, ensure_ascii=False))

        elif fmt == "csv":
            stem = Path(args.file).stem
            output_dir = _resolve_output_dir(args.output_dir, stem)
            csv_paths = [
                output_dir / f"{stem}_p{tbl['page']}_t{tbl['table_number']}.csv"
                for tbl in all_tables
            ]
            _check_outputs(csv_paths, [Path(args.file)], args.force)
            for tbl, csv_path in zip(all_tables, csv_paths):
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for row in tbl["rows"]:
                        writer.writerow(
                            [cell if cell is not None else "" for cell in row]
                        )
                print(f"Saved: {csv_path}")

        else:
            for tbl in all_tables:
                print(
                    f"## Table {tbl['table_number']} "
                    f"(Page {tbl['page']})\n"
                )
                rows = tbl["rows"]
                if not rows:
                    continue
                clean_rows = [
                    [
                        str(cell).replace("|", "\\|") if cell is not None else ""
                        for cell in row
                    ]
                    for row in rows
                ]
                header = clean_rows[0]
                print("| " + " | ".join(header) + " |")
                print(
                    "| " + " | ".join("---" for _ in header) + " |"
                )
                for row in clean_rows[1:]:
                    while len(row) < len(header):
                        row.append("")
                    print("| " + " | ".join(row[: len(header)]) + " |")
                print()


def cmd_to_images(args: argparse.Namespace) -> None:
    """Convert PDF pages to PNG images."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        print(
            "ERROR: pypdfium2 is not installed.\n"
            "Install it with: pip install pypdfium2\n"
            "Or: pip install mythril-agent-skills[pdf-images]",
            file=sys.stderr,
        )
        sys.exit(1)

    p = Path(args.file)
    if not p.exists():
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(2)

    pdf = pdfium.PdfDocument(str(p))
    try:
        total = len(pdf)
        page_indices = _resolve_pages(args, total)

        output_dir = _resolve_output_dir(args.output_dir, p.stem)
        out_paths = [output_dir / f"{p.stem}_page_{idx + 1}.png" for idx in page_indices]
        _check_outputs(out_paths, [p], args.force)

        scale = args.scale if args.scale else 2.0

        for idx, out_path in zip(page_indices, out_paths):
            page = pdf[idx]
            bitmap = page.render(scale=scale)
            img = bitmap.to_pil()
            img.save(str(out_path), "PNG")
            print(f"Saved: {out_path} ({img.width}x{img.height})")
    finally:
        pdf.close()


def cmd_merge(args: argparse.Namespace) -> None:
    """Merge multiple PDFs into one."""
    if len(args.files) < 2:
        print("ERROR: At least 2 PDF files required for merge.", file=sys.stderr)
        sys.exit(2)

    _check_outputs([Path(args.output)], [Path(f) for f in args.files], args.force)
    writer = PdfWriter()
    for pdf_path in args.files:
        reader = _load_reader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)
        print(f"Added: {pdf_path} ({len(reader.pages)} pages)")

    _write_pdf(writer, args.output)
    print(f"\nMerged {len(args.files)} files -> {args.output}")


def cmd_split(args: argparse.Namespace) -> None:
    """Split a PDF by extracting specific pages."""
    reader = _load_reader(args.file)
    total = len(reader.pages)

    if args.each:
        stem = Path(args.file).stem
        output_dir = _resolve_output_dir(args.output_dir, stem)
        page_indices = _resolve_pages(args, total)
        outs = [output_dir / f"{stem}_page_{idx + 1}.pdf" for idx in page_indices]
        _check_outputs(outs, [Path(args.file)], args.force)
        for idx, out in zip(page_indices, outs):
            w = PdfWriter()
            w.add_page(reader.pages[idx])
            _write_pdf(w, str(out))
            print(f"Saved: {out}")
        return

    if not args.pages:
        print(
            "ERROR: Specify --pages or --each for split.",
            file=sys.stderr,
        )
        sys.exit(2)

    if not args.output:
        print("ERROR: -o/--output is required for split.", file=sys.stderr)
        sys.exit(2)

    _check_outputs([Path(args.output)], [Path(args.file)], args.force)
    page_indices = _parse_page_spec(args.pages, total)
    writer = PdfWriter()
    for idx in page_indices:
        writer.add_page(reader.pages[idx])

    _write_pdf(writer, args.output)
    print(f"Split {len(page_indices)} pages -> {args.output}")


def cmd_rotate(args: argparse.Namespace) -> None:
    """Rotate pages in a PDF."""
    reader = _load_reader(args.file)
    total = len(reader.pages)

    angle = args.angle
    if angle not in (90, 180, 270):
        print("ERROR: Angle must be 90, 180, or 270.", file=sys.stderr)
        sys.exit(2)

    if not args.output:
        print("ERROR: -o/--output is required for rotate.", file=sys.stderr)
        sys.exit(2)
    _check_outputs([Path(args.output)], [Path(args.file)], args.force)

    page_indices = set(_resolve_pages(args, total))

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i in page_indices:
            page.rotate(angle)
        writer.add_page(page)

    _write_pdf(writer, args.output)
    rotated_desc = "all pages" if len(page_indices) == total else f"{len(page_indices)} pages"
    print(f"Rotated {rotated_desc} by {angle}° -> {args.output}")


def image_filename(stem: str, page_num: int, index: int, name: str) -> str:
    """Build an output name like ``doc_p3_img2.png`` from pypdf's image name.

    pypdf names images ``Im1.png`` / ``X5.jpg``; only the extension is kept
    (lowercased), defaulting to ``bin`` when it has none.
    """
    suffix = Path(name).suffix.lower().lstrip(".")
    ext = suffix if suffix.isalnum() else "bin"
    return f"{stem}_p{page_num}_img{index}.{ext or 'bin'}"


def cmd_extract_images(args: argparse.Namespace) -> None:
    """Extract embedded images from a PDF via pypdf's image decoder."""
    reader = _load_reader(args.file)
    total = len(reader.pages)
    page_indices = _resolve_pages(args, total)
    stem = Path(args.file).stem
    output_dir = _resolve_output_dir(args.output_dir, stem)

    img_count = 0
    for idx in page_indices:
        page = reader.pages[idx]
        try:
            images = list(page.images)
        except Exception as exc:  # pypdf raises on unsupported filters
            print(f"WARNING: page {idx + 1}: cannot decode images ({exc})",
                  file=sys.stderr)
            continue
        for image in images:
            img_count += 1
            out_path = output_dir / image_filename(stem, idx + 1, img_count, image.name)
            _check_outputs([out_path], [Path(args.file)], args.force)
            out_path.write_bytes(image.data)
            size = ""
            if getattr(image, "image", None) is not None:
                size = f" ({image.image.width}x{image.image.height})"
            print(f"Extracted: {out_path}{size}")

    if img_count == 0:
        print("No embedded images found in the specified pages.")
    else:
        print(f"\nExtracted {img_count} image(s) to {output_dir}")


def decrypt_succeeded(result: Any) -> bool:
    """True if pypdf's decrypt() result is not PasswordType.NOT_DECRYPTED (0)."""
    return int(result) != 0


def cmd_decrypt(args: argparse.Namespace) -> None:
    """Decrypt a password-protected PDF."""
    if not args.output:
        print("ERROR: -o/--output is required for decrypt.", file=sys.stderr)
        sys.exit(2)

    reader = _load_reader(args.file)

    if not reader.is_encrypted:
        print("This PDF is not encrypted.")
        return

    _check_outputs([Path(args.output)], [Path(args.file)], args.force)
    try:
        result = reader.decrypt(args.password)
    except Exception as exc:
        print(f"ERROR: Failed to decrypt: {exc}", file=sys.stderr)
        sys.exit(2)
    if not decrypt_succeeded(result):
        print("ERROR: Wrong password — the PDF could not be decrypted.",
              file=sys.stderr)
        sys.exit(2)

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    _write_pdf(writer, args.output)
    print(f"Decrypted -> {args.output}")


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="pdf_ops.py",
        description="PDF file operations for AI coding assistants.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # info
    p_info = sub.add_parser("info", help="Show PDF metadata and structure")
    p_info.add_argument("file", help="PDF file path")

    # text
    p_text = sub.add_parser("text", help="Extract text from PDF")
    p_text.add_argument("file", help="PDF file path")
    p_text.add_argument("--pages", help="Page spec: 1,3,5-8")
    p_text.add_argument(
        "--layout", action="store_true", help="Preserve spatial layout"
    )

    # tables
    p_tables = sub.add_parser("tables", help="Extract tables from PDF")
    p_tables.add_argument("file", help="PDF file path")
    p_tables.add_argument("--pages", help="Page spec: 1,3,5-8")
    p_tables.add_argument(
        "--format",
        choices=["markdown", "json", "csv"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    p_tables.add_argument(
        "--output-dir", help="Output directory for CSV files"
    )
    p_tables.add_argument(
        "--force", action="store_true",
        help="Overwrite existing output files (never an input file)",
    )

    # to-images
    p_imgs = sub.add_parser("to-images", help="Convert PDF pages to PNG")
    p_imgs.add_argument("file", help="PDF file path")
    p_imgs.add_argument("--pages", help="Page spec: 1,3,5-8")
    p_imgs.add_argument(
        "--output-dir",
        help="Output directory (default: a new dir in the skill cache)",
    )
    p_imgs.add_argument(
        "--scale", type=float, default=2.0, help="Render scale (default: 2.0)"
    )
    p_imgs.add_argument(
        "--force", action="store_true",
        help="Overwrite existing output files (never an input file)",
    )

    # merge
    p_merge = sub.add_parser("merge", help="Merge multiple PDFs")
    p_merge.add_argument("files", nargs="+", help="PDF files to merge")
    p_merge.add_argument("-o", "--output", required=True, help="Output file")
    p_merge.add_argument(
        "--force", action="store_true",
        help="Overwrite existing output files (never an input file)",
    )

    # split
    p_split = sub.add_parser("split", help="Split PDF by pages")
    p_split.add_argument("file", help="PDF file path")
    p_split.add_argument("--pages", help="Page spec: 1,3,5-8")
    p_split.add_argument(
        "--each",
        action="store_true",
        help="Split into individual page files",
    )
    p_split.add_argument("-o", "--output", help="Output file (for page range)")
    p_split.add_argument(
        "--output-dir", help="Output directory (for --each)"
    )
    p_split.add_argument(
        "--force", action="store_true",
        help="Overwrite existing output files (never an input file)",
    )

    # rotate
    p_rotate = sub.add_parser("rotate", help="Rotate PDF pages")
    p_rotate.add_argument("file", help="PDF file path")
    p_rotate.add_argument("angle", type=int, help="Rotation angle: 90, 180, 270")
    p_rotate.add_argument("--pages", help="Page spec: 1,3,5-8 (default: all)")
    p_rotate.add_argument("-o", "--output", help="Output file")
    p_rotate.add_argument(
        "--force", action="store_true",
        help="Overwrite existing output files (never an input file)",
    )

    # extract-images
    p_eimg = sub.add_parser(
        "extract-images", help="Extract embedded images from PDF"
    )
    p_eimg.add_argument("file", help="PDF file path")
    p_eimg.add_argument("--pages", help="Page spec: 1,3,5-8")
    p_eimg.add_argument("--output-dir", help="Output directory for images")
    p_eimg.add_argument(
        "--force", action="store_true",
        help="Overwrite existing output files (never an input file)",
    )

    # decrypt
    p_dec = sub.add_parser("decrypt", help="Decrypt a password-protected PDF")
    p_dec.add_argument("file", help="PDF file path")
    p_dec.add_argument("--password", required=True, help="PDF password")
    p_dec.add_argument("-o", "--output", help="Output file")
    p_dec.add_argument(
        "--force", action="store_true",
        help="Overwrite existing output files (never an input file)",
    )

    return parser


COMMAND_DISPATCH: dict[str, Any] = {
    "info": cmd_info,
    "text": cmd_text,
    "tables": cmd_tables,
    "to-images": cmd_to_images,
    "merge": cmd_merge,
    "split": cmd_split,
    "rotate": cmd_rotate,
    "extract-images": cmd_extract_images,
    "decrypt": cmd_decrypt,
}


def main() -> None:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()
    handler = COMMAND_DISPATCH.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
