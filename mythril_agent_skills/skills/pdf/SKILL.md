---
name: pdf
description: >
  Reads and manipulates PDF files via a bundled Python script: text and table
  extraction (markdown/JSON/CSV), metadata, page-to-image rendering, merge,
  split, rotate, embedded-image extraction, and password decryption. Use when
  the user wants to read, inspect, convert, or edit a PDF, or mentions a .pdf
  path, e.g. "read pdf", "pdf tables", "merge pdfs", "split pdf", "读 pdf", "pdf
  转图片", "合并 pdf".
license: Apache-2.0
---

# When to Use This Skill

- User mentions a `.pdf` file and wants to read, extract, or inspect its content
- Text extraction: extract text from all or specific pages, with layout preservation
- Table extraction: extract tables as markdown, JSON, or CSV
- Metadata inspection: page count, title, author, creator, file size, encryption status
- PDF to images: render pages as PNG for visual inspection (scanned/image PDFs, charts, diagrams)
- Merge: combine multiple PDFs into one
- Split: extract page ranges into separate files
- Rotate: rotate specific pages
- Extract images: extract embedded images from a PDF
- Decrypt: remove password protection (when password is known)

> **Scanned / image PDFs**: If text extraction returns empty or garbled results, the PDF is likely a scanned document. Use the `to-images` subcommand to convert pages to PNG — the AI agent can then read the content visually. This is more reliable and lightweight than OCR.

# Prerequisites

- `pypdf` — PDF manipulation (merge, split, rotate, metadata, decrypt, extract images)
- `pdfplumber` — text and table extraction
- `pypdfium2` (optional) — PDF-to-image conversion (`to-images` subcommand)

Pre-flight check:

```bash
python3 -c "import pypdf; print('pypdf', pypdf.__version__)"
python3 -c "import pdfplumber; print('pdfplumber', pdfplumber.__version__)"
# Optional: check image conversion support
python3 -c "import pypdfium2; print('pypdfium2', pypdfium2.__version__)"
```

Install if missing:

```bash
pip install pypdf pdfplumber
pip install pypdfium2  # optional, for to-images
```

# Workflow

1. Determine what the user wants (read text, extract tables, inspect metadata, convert to images, merge, split, etc.)
2. Run the appropriate script subcommand
3. Read the output (text, markdown table, JSON, or confirmation) and present it to the user
4. For multi-step tasks, chain subcommands in sequence

All commands use:

```bash
python3 SKILL_PATH/scripts/pdf_ops.py <subcommand> [options] <file>
```

`SKILL_PATH` is this skill's installed directory (the folder containing this SKILL.md).

# Command Reference

## Inspect PDF metadata

```bash
python3 SKILL_PATH/scripts/pdf_ops.py info document.pdf
```

Shows page count, title, author, subject, creator, producer, creation date, file size, and encryption status.

## Extract text

```bash
# Extract text from all pages
python3 SKILL_PATH/scripts/pdf_ops.py text document.pdf

# Extract text from specific pages (1-based)
python3 SKILL_PATH/scripts/pdf_ops.py text document.pdf --pages 1-5

# Extract text from a single page
python3 SKILL_PATH/scripts/pdf_ops.py text document.pdf --pages 3

# Combine specific pages and ranges
python3 SKILL_PATH/scripts/pdf_ops.py text document.pdf --pages 1,3,5-8

# Extract with layout preservation (keeps spatial arrangement)
python3 SKILL_PATH/scripts/pdf_ops.py text document.pdf --layout
```

## Extract tables

```bash
# Extract all tables as markdown (default)
python3 SKILL_PATH/scripts/pdf_ops.py tables document.pdf

# Extract tables from specific pages
python3 SKILL_PATH/scripts/pdf_ops.py tables document.pdf --pages 2-4

# Extract as JSON
python3 SKILL_PATH/scripts/pdf_ops.py tables document.pdf --format json

# Extract as CSV (one file per table)
python3 SKILL_PATH/scripts/pdf_ops.py tables document.pdf --format csv --output-dir ./tables/
```

Without `--output-dir`, CSV files go to a new directory in the skill cache (path printed).

## Convert PDF to images

Renders each page as a PNG image. Useful for scanned PDFs, charts, diagrams, or any visual content.

```bash
# Convert all pages (output to a new directory in the skill cache; paths printed)
python3 SKILL_PATH/scripts/pdf_ops.py to-images document.pdf

# Convert specific pages
python3 SKILL_PATH/scripts/pdf_ops.py to-images document.pdf --pages 1-3

# Output to a specific directory (only when the user wants the PNGs kept)
python3 SKILL_PATH/scripts/pdf_ops.py to-images document.pdf --output-dir ./pages/

# Control resolution (default: 2.0x scale)
python3 SKILL_PATH/scripts/pdf_ops.py to-images document.pdf --scale 3.0
```

Output files are named `<stem>_page_1.png`, `<stem>_page_2.png`, etc. Renders made only so you can read the pages visually belong in the cache — omit `--output-dir`.

## Merge PDFs

```bash
# Merge multiple PDFs into one
python3 SKILL_PATH/scripts/pdf_ops.py merge file1.pdf file2.pdf file3.pdf -o merged.pdf

# Merge all PDFs in a directory (alphabetical order)
python3 SKILL_PATH/scripts/pdf_ops.py merge *.pdf -o combined.pdf
```

## Split PDF

```bash
# Extract specific pages into a new PDF
python3 SKILL_PATH/scripts/pdf_ops.py split document.pdf --pages 1-5 -o first_five.pdf

# Extract a single page
python3 SKILL_PATH/scripts/pdf_ops.py split document.pdf --pages 3 -o page3.pdf

# Split into individual pages (one file per page)
python3 SKILL_PATH/scripts/pdf_ops.py split document.pdf --each --output-dir ./pages/
```

## Rotate pages

```bash
# Rotate all pages 90° clockwise
python3 SKILL_PATH/scripts/pdf_ops.py rotate document.pdf 90 -o rotated.pdf

# Rotate specific pages
python3 SKILL_PATH/scripts/pdf_ops.py rotate document.pdf 90 --pages 1,3 -o rotated.pdf

# Rotate counter-clockwise
python3 SKILL_PATH/scripts/pdf_ops.py rotate document.pdf 270 -o rotated.pdf
```

Valid angles: 90, 180, 270.

## Extract embedded images

```bash
# Extract all images to a directory
python3 SKILL_PATH/scripts/pdf_ops.py extract-images document.pdf --output-dir ./images/

# Extract from specific pages
python3 SKILL_PATH/scripts/pdf_ops.py extract-images document.pdf --pages 1-3 --output-dir ./images/
```

## Decrypt a password-protected PDF

```bash
python3 SKILL_PATH/scripts/pdf_ops.py decrypt encrypted.pdf --password secret -o decrypted.pdf
```

# Composing Multi-Step Workflows

The commands above are building blocks. Combine them to accomplish complex user requests. Examples:

**"Read this scanned PDF":**
1. `text` to attempt text extraction — if empty, it's a scanned document
2. `to-images` to render pages as PNGs
3. Read the images visually

**"Extract the tables from pages 3-5 and save as CSV":**
1. `tables --pages 3-5 --format csv --output-dir ./tables/` to extract and save

**"Merge these three PDFs but only include pages 1-10 from the first one":**
1. `split` to extract pages 1-10 from the first PDF
2. `merge` the split output with the other two PDFs

**"What's in this PDF?":**
1. `info` to see page count, title, etc.
2. `text --pages 1` to read the first page for a quick overview

# Guidelines

- **Read before manipulate**: always `info` or `text --pages 1` first to understand the document
- **Large PDFs**: use `--pages` to limit extraction to relevant pages
- **Empty text extraction**: if `text` returns nothing, the PDF is likely scanned/image-based — use `to-images` and read visually
- **Output files**: `merge`, `split`, `rotate`, and `decrypt` require `-o` for the output path. Every write command refuses an output path that is one of its inputs, and refuses to replace an existing file unless `--force` is passed — ask the user before adding `--force`
- **Default locations**: `to-images`, `extract-images`, `tables --format csv`, and `split --each` write to a new directory under `<user-cache>/mythril-skills-cache/pdf/` when no `--output-dir` is given; pass `--output-dir` when the user named a destination
- **Wrong password**: `decrypt` exits with `Wrong password` — ask the user for the correct one
- **Table extraction**: not all PDFs have machine-readable tables; complex layouts may need visual inspection via `to-images`
