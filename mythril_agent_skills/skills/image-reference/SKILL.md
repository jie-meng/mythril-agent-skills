---
name: image-reference
description: >
  Reference a specific image in a document, copying the source into an assets
  directory next to the document (named after the doc, e.g. `guide.assets/`)
  and inserting the correct Markdown image link — mirroring the nvim markdown
  paste-image workflow. Trigger whenever the user asks to insert, embed, paste,
  add, or reference an image/file in a document — e.g. one dropped into the
  chat, pasted, or given as a path. Example phrases: "把这个图加进文档", "把截图
  放进 README", "put this image in the doc", "insert screenshot.png", "embed the
  diagram in implementation.md", "引用这张图", "在这篇文章里加一张架构图". Use it
  whenever a user wants an image to live alongside a specific document and be
  cited with a local relative link. When the source has no name or a messy
  auto-generated name, derive a clean content-based slug filename (lowercase
  ASCII letters/digits + hyphens, e.g. `mobile-arch.png`).
license: Apache-2.0
---

# Image Reference

Insert references to a specific image into a document so the media file lives
*beside* the document and is cited with a stable local relative link. This is the
AI-equivalent of the nvim Markdown `<Leader>mi` "paste media" keybinding: same
assets-directory layout, same filename and collision rules.

## Goals

- Put every referenced image in a per-document assets directory next to the doc.
- Reuse the exact nvim naming convention (`<basename>.assets/`, basename kept,
  `-1`/`-2` on collision) so the layout is consistent with the user's editor.
- When a source name is missing or meaningless (chat attachment, `pasted-image.png`,
  `Screen Shot 2024-01-01 at 3.42.12 PM.png`, `IMG_9527.heic`, a temp path with
  random characters), derive a clean, descriptive name from the image **content /
  subject**, not its filename.
- Insert the correct Markdown image reference at the requested location.

## The nvim convention (mirror these rules exactly)

For a document at `docs/implementation.md`:

1. **Assets directory**: name it `implementation.assets/` and place it in the same
   folder as the document. (`docs/implementation.md` → `docs/implementation.assets/`).
   General rule: take the document filename *without extension* and append `.assets`.
2. **Filename**: keep the source file's basename when it is already clean and
   meaningful (a lowercase slug like `mobile-arch.png` stays `mobile-arch.png`;
   `MyDiagram.v2.png` stays as-is if it reads fine).
3. **Extension**: preserve the original extension (case-insensitive). Normalize the
   saved filename so spaces/punctuation/weird characters are not carried over when
   you pick a content-based name.
4. **Collision**: if the target name already exists in the assets dir but holds
   *different* bytes, rename to `<stem>-1`, `<stem>-2`, ... until free
   (e.g. `mobile-arch.png` → `mobile-arch-1.png`). If the existing file is
   **byte-identical**, reuse it — never create a duplicate.
5. **Link**: reference the image with a path relative to the document:
   `![alt-text](implementation.assets/mobile-arch.png)`.
   The alt text should describe the image subject, not the filename.

Example result for `docs/implementation.md`, source `My Mobile Arch!!.PNG`:

```text
docs/
└── implementation.md
└── implementation.assets/
    └── my-mobile-arch.png
```

And in the document:

```markdown
![Mobile app architecture](implementation.assets/my-mobile-arch.png)
```

## Naming the file (the most important judgment call)

This is where you do the real work. Rules, in priority order:

1. If the user gave an explicit, clean name for the image, use it verbatim
   (slugified).
2. If the source basename is already clean and descriptive (e.g. `mobile-arch.png`,
   `auth-flow.jpg`, `redis-cache.svg`) — **keep it**. Do not rename an existing
   meaningful name.
3. Otherwise (chat attachment, generic `image.png`, `pasted-image-<random>.png`,
   `Screen Shot ...`, `IMG_xxxx`, a `/tmp/...` temp path, or any name not
   descriptive) — **derive a name from the image's content/subject**:
   - Look at what the image actually depicts: an architecture diagram, a login form,
     a chart, a table, a photo, a logo.
   - Summarize it in 2–4 English words, lowercase, joined by a single hyphen
     (`-`), ASCII letters and digits only.
   - Examples: `mobile-arch.png`, `redis-cache-flow.svg`, `auth-login-form.png`,
     `q1-revenue-chart.jpg`, `unified-search-ui.png`, `ci-pipeline-diagram.png`.
   - If you genuinely cannot tell what the image is (no vision available), fall back
     to a generic but stable name like `image-<n>.png` and tell the user, then offer
     to rename it once they describe it.

Never use consecutive hyphens, leading/trailing hyphens, spaces, or non-ASCII
characters in the final filename.

## Workflow

Follow these steps in order.

### 1. Resolve the target document

- The user may name a file (`implementation.md`) or point at the doc they are editing.
- If none is given and you are already editing a document, use that document.
- **The document must have a real filesystem path.** If the document is new/unsaved
  or the path is unknown, save it first (or ask for the path) so the assets dir can
  live next to it. Never create the `.assets/` folder in an arbitrary location.

### 2. Resolve the source image

The source is one of:

- **A path the user typed** (absolute, relative, `~`, or a `file://` URL). Normalize
  it and confirm the file exists and is an image.
- **An image dropped / pasted into the chat.** Locate the actual bytes:
  - If the tool exposed a path for the attachment, read from that path.
  - If only in-context pixels are available (no writable file), save the image to the
    unified cache directory first
    (`<user-cache>/mythril-skills-cache/image-reference/<random>/`), then copy it into
    the assets dir from there. Never invent a path that does not exist.

### 3. Copy into the assets directory

Compute everything deterministically — you can and should use the bundled helper
script so the rules are exact:

```bash
python3 scripts/image_assets.py assets-dir docs/implementation.md
python3 scripts/image_assets.py slug-filter "My Mobile Arch!!.PNG"
python3 scripts/image_assets.py unique   docs/implementation.assets "my-mobile-arch.png" /path/to/source.png
python3 scripts/image_assets.py rel-link docs/implementation.md my-mobile-arch.png
python3 scripts/image_assets.py md-link  implementation.assets/my-mobile-arch.png "Mobile app architecture"
```

Steps (mirror the nvim logic exactly):

1. `assets_dir = assets-dir <md_path>` and `mkdir -p` it.
2. Decide the desired filename (see "Naming the file").
3. `dst = unique <assets_dir> <desired> <src>` — this reuses byte-identical files
   and adds `-1`/`-2` on conflicts.
4. If `dst` already exists and holds identical bytes, skip the copy. Otherwise copy
   the source bytes to `dst`.
5. `rel = rel-link <md_path> <dst.name>`.
6. Insert `md-link <rel> <alt>` at the requested spot (start of a new line, or right
   after the sentence/paragraph the user wants the image to accompany). Use a
   descriptive, image-content-based alt text. For GIFs that animate meaningfully,
   you may keep the `![alt](path)` form; no special syntax is required.

The helper is deterministic, but **deciding the content-based name is yours** — pick
it from what the image shows before you sanitize it.

### 4. Report

Tell the user concisely:

- the absolute path of the copied asset,
- the exact Markdown reference you inserted,
- the relative path used, and
- if you renamed the file (generic/messy → content-based), say so and note they can
  rename it later — the link updates automatically since you reuse the same stem.

## Rules & edge cases

- **Never duplicate.** If the identical bytes already exist in the assets dir, reuse
  the existing file and reference it.
- **Never touch the source.** Copy, never move or delete the original unless the user
  explicitly asks.
- **Not just Markdown.** The `<stem>.assets/` rule generalizes to other text docs; but
  Markdown is the primary target and the link syntax below is Markdown. For non-Markdown
  docs, produce whatever relative-reference syntax that format uses and note it.
- **Only copy real images.** If the path is not an existing image file (or you cannot
  obtain bytes), stop and ask rather than guessing.
- **Don't fabricate** byte-identity: read actual bytes, never assume.
- If the user is referencing images in an existing doc that already has an
  established assets directory with a different name, prefer the document's existing
  convention over creating a new one.