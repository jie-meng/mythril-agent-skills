---
name: word
description: >
  Reads Word documents (.docx/.docm) via a bundled Python script: text, tables
  (markdown/JSON/CSV), metadata, embedded images, and Markdown conversion. Use
  when the user wants to read, inspect, or convert a Word file, or mentions a
  .docx/.docm path, e.g. "read docx", "word to markdown", "word tables", "打开
  word", "读 docx", "word 转 markdown".
license: Apache-2.0
---

# When to Use This Skill

- User mentions a `.docx` or `.docm` file and wants to read, extract, or inspect its content
- Text extraction: extract text from paragraphs with heading detection
- Table extraction: extract tables as markdown, JSON, or CSV
- Metadata inspection: author, title, creation date, word count, structure
- Image extraction: extract embedded images from the document
- Markdown conversion: convert the full document to Markdown format

> **Legacy .doc files**: This skill handles `.docx` and `.docm` (modern Word formats). For legacy `.doc` files, the script will suggest converting to `.docx` first using LibreOffice (`libreoffice --headless --convert-to docx file.doc`) or an online converter.

# Prerequisites

- `python-docx` — install with: `pip install python-docx`

Pre-flight check:

```bash
python3 -c "import docx; print(docx.__version__)"
```

Install if missing:

```bash
pip install python-docx
```

# Workflow

1. Determine what the user wants (read text, extract tables, inspect metadata, convert to markdown, extract images)
2. Run the appropriate script subcommand
3. Read the output (text, markdown table, JSON, or confirmation) and present it to the user
4. For multi-step tasks, chain subcommands in sequence

All commands use:

```bash
python3 SKILL_PATH/scripts/word_ops.py <subcommand> [options] <file>
```

`SKILL_PATH` is this skill's installed directory (the folder containing this SKILL.md).

# Command Reference

## Inspect document metadata

```bash
python3 SKILL_PATH/scripts/word_ops.py info document.docx
```

Shows file size, title, author, subject, creation/modification dates, paragraph count, table count, word count, section count, and heading outline.

## Extract text

```bash
# Extract all text
python3 SKILL_PATH/scripts/word_ops.py text document.docx

# Extract first 50 paragraphs
python3 SKILL_PATH/scripts/word_ops.py text document.docx --limit 50

# Skip empty paragraphs
python3 SKILL_PATH/scripts/word_ops.py text document.docx --skip-empty
```

Headings are shown with `#` markers for visual hierarchy. `text` covers paragraphs only — table content is not included; use `to-markdown` when tables matter.

## Extract tables

```bash
# Extract all tables as markdown (default)
python3 SKILL_PATH/scripts/word_ops.py tables document.docx

# Extract as JSON
python3 SKILL_PATH/scripts/word_ops.py tables document.docx --format json

# Extract as CSV (one file per table)
python3 SKILL_PATH/scripts/word_ops.py tables document.docx --format csv --output-dir ./tables/
```

## Extract embedded images

```bash
# Extract all images to a directory
python3 SKILL_PATH/scripts/word_ops.py extract-images document.docx --output-dir ./images/
```

Output files are named `<stem>_image_1.png`, `<stem>_image_2.png`, etc.

## Convert to Markdown

```bash
# Print to stdout
python3 SKILL_PATH/scripts/word_ops.py to-markdown document.docx

# Save to file
python3 SKILL_PATH/scripts/word_ops.py to-markdown document.docx -o document.md
```

Preserves heading hierarchy, bold/italic formatting, hyperlinks (as `[text](url)`), tracked insertions, and tables in document order.

# Composing Multi-Step Workflows

The commands above are building blocks. Combine them to accomplish complex user requests. Examples:

**"What's in this Word document?":**
1. `info` to see page count, title, author, etc.
2. `text --limit 30` to read the first 30 paragraphs for a quick overview

**"Extract the tables and save as CSV":**
1. `tables --format csv --output-dir ./tables/` to extract and save

**"Convert this docx to markdown and show me":**
1. `to-markdown` to convert and print the full document

**"Read this Word doc and summarize it":**
1. `info` to understand the structure
2. `to-markdown` to extract all content, including tables, in document order
3. Summarize based on the extracted Markdown

# Guidelines

- **Read before manipulate**: always `info` or `text --limit 10` first to understand the document
- **Large documents**: use `--limit` to avoid overwhelming output
- **Legacy .doc**: the script handles `.docx` only; for `.doc` files, convert first with LibreOffice
- **Tables**: first row is treated as the header in markdown/JSON output
- **Images**: extracted in their original format (PNG, JPEG, etc.)
