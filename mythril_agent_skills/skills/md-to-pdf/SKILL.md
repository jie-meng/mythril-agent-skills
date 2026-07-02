---
name: md-to-pdf
description: >
  Convert Markdown files to PDF via a bundled Python script. Supports custom
  CSS styling, table of contents generation, paper size selection, and
  landscape orientation. Trigger whenever the user asks to convert, export,
  or render a Markdown file as PDF, or says phrases like "markdown to pdf",
  "md to pdf", "convert md to pdf", "export markdown as pdf", "render
  markdown to pdf", "generate pdf from markdown", "markdown 转 pdf",
  "md 转 pdf", "把 markdown 转成 pdf", "导出 pdf", "markdown 导出 pdf",
  "md 导出", "生成 pdf". Also trigger when the user mentions a .md file
  and wants a PDF version of it.
license: Apache-2.0
---

# When to Use This Skill

- User mentions a `.md` file and wants to convert it to PDF
- Export markdown notes, documentation, or README files as PDF
- Generate printable PDF from markdown with styling

# Prerequisites

- `markdown-pdf` — converts markdown to PDF using markdown-it-py + PyMuPDF

Pre-flight check:

```bash
python3 -c "import markdown_pdf; print('markdown-pdf', markdown_pdf.__version__)"
```

Install if missing:

```bash
pip install mythril-agent-skills[md-to-pdf]
```

Or standalone:

```bash
pip install markdown-pdf
```

# Workflow

1. User provides a markdown file path (and optionally an output path)
2. Run the conversion script
3. Report the output PDF path to the user

All commands use:

```bash
python3 scripts/md_to_pdf.py [options] <input.md>
```

The script path is relative to this skill directory.

# Command Reference

## Basic conversion

```bash
# Convert to PDF (output next to input: README.md -> README.pdf)
python3 scripts/md_to_pdf.py document.md

# Specify output path
python3 scripts/md_to_pdf.py document.md -o /path/to/output.pdf
```

## Table of contents

```bash
# Generate TOC from h1-h2 headings (default: no TOC)
python3 scripts/md_to_pdf.py document.md --toc 2

# TOC from h1-h3
python3 scripts/md_to_pdf.py document.md --toc 3
```

## Paper size and orientation

```bash
# Use Letter paper
python3 scripts/md_to_pdf.py document.md --paper-size Letter

# A4 landscape
python3 scripts/md_to_pdf.py document.md --paper-size A4-L
```

Supported sizes: A3, A4, A5, A6, B4, B5, Letter, Legal (append `-L` for landscape).

## Custom CSS

```bash
# Apply custom CSS file
python3 scripts/md_to_pdf.py document.md --css style.css
```

## PDF metadata

```bash
# Set title and author
python3 scripts/md_to_pdf.py document.md --title "User Guide" --author "Jane Doe"
```

## Optimize file size

```bash
python3 scripts/md_to_pdf.py document.md --optimize
```

## Combining options

```bash
python3 scripts/md_to_pdf.py README.md \
  -o guide.pdf \
  --toc 2 \
  --paper-size A4 \
  --title "Project Guide" \
  --author "Team" \
  --optimize
```

# Guidelines

- **Output defaults to same directory as input**: `notes.md` produces `notes.pdf` in the same folder
- **Images**: relative image paths in markdown are resolved from the markdown file's directory
- **UTF-8**: full Unicode support for any language
- **Large documents**: use `--optimize` to reduce file size
