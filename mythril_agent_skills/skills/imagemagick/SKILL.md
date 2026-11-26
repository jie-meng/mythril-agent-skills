---
name: imagemagick
description: >
  Processes images with the ImageMagick CLI (magick): resize, convert formats,
  crop, compress, make thumbnails, add watermarks or effects, batch-process
  folders, and read dimensions or metadata. Use when the user wants to transform
  or inspect an image file, e.g. "resize image", "convert to webp", "compress
  image", "batch resize", "add watermark", "image dimensions", "图片压缩", "图片转换",
  "缩略图", "批量处理图片", "imagemagick".
license: Apache-2.0
---

# ImageMagick

Image processing with the ImageMagick CLI. You already know most ImageMagick
syntax; this skill adds the workflow, the safety rules, and the pitfalls that
commonly produce wrong sizes, lost transparency, or overwritten originals.

**Recipe catalog:** [references/recipes.md](references/recipes.md) has
copy-ready commands for format conversion, resizing, cropping, thumbnails,
effects, adjustments, rotation, borders, text/watermarks, compositing, image
info, batch processing, animated GIFs, contact sheets, performance limits, and
web-optimization flags. Read the relevant section when you need exact flags.

# Prerequisites

```bash
command -v magick >/dev/null && magick -version | head -1 || command -v convert
```

Install if missing:

- macOS: `brew install imagemagick`
- Ubuntu/Debian: `sudo apt-get install imagemagick`
- Windows: https://imagemagick.org/script/download.php

# Workflow

1. **Pre-flight** — detect the version (below decides the command names).
2. **Inspect the input** — size, format, alpha, and orientation decide the
   flags: `magick identify -format "%f %wx%h %m alpha=%A orient=%[orientation]\n" "input.jpg"`
3. **Pick the output filename** (rules below).
4. **Run the command** — look up the recipe in `references/recipes.md` for
   exact flags. Quote every path.
5. **Verify** — `magick identify` the output and report its size, dimensions,
   and path to the user.

# Output Files — preserve the original

Write to a new file unless the user explicitly asks to overwrite ("覆盖原图",
"replace in-place", "modify the original", "same filename"). Image edits are
usually lossy, so overwriting silently destroys the user's source.

| Operation | Example output name |
|---|---|
| Resize | `photo.jpg` → `photo_800x600.jpg` |
| Convert | `photo.png` → `photo.jpg` |
| Effect | `photo.jpg` → `photo_blur.jpg`, `photo_gray.jpg` |
| Thumbnail | `photo.jpg` → `photo_thumb.jpg` |
| Other | `photo.jpg` → `photo_processed.jpg` |
| Batch | a subdirectory (`resized/`, `thumbnails/`) |

- **`mogrify` overwrites its inputs in place.** Always give it
  `-path ./outdir` (after `mkdir -p outdir`) unless the user asked to
  overwrite. `-format jpg` without `-path` still writes next to the originals.
- For batch jobs, process one file first and check the result before running
  the whole set.

# Pitfalls (the non-obvious parts)

**v7 vs v6 command names.** ImageMagick 7 uses `magick` (`magick in out`,
`magick identify`, `magick mogrify`, `magick montage`). Version 6 has no
`magick`; use `convert`, `identify`, `mogrify`, `montage`. On Windows, a bare
`convert` is the system disk tool, not ImageMagick — never call it there.

**Geometry flags change the meaning of a size.** Quote geometries containing
`>`, `<`, `^`, or `!` — the shell treats them as redirection or history.

| Geometry | Meaning |
|---|---|
| `800x600` | Fit inside, keep aspect ratio (result may be smaller on one side) |
| `800x600!` | Force exact size, distorts |
| `'800x600^'` | Fill — cover the box, keep aspect ratio; follow with `-gravity center -extent 800x600` to crop to exact size |
| `'800x600>'` | Shrink only — never enlarge small images |
| `'800x600<'` | Enlarge only |
| `800x` / `x600` | Fix one side, auto the other |
| `50%` | Scale by percent |
| `400x400+10+20` | Region of 400×400 at offset (10,20) — for `-crop` |

**Crop leaves a virtual canvas.** Add `+repage` after `-crop` or later steps
and PNG/GIF output keep the old offset. `-crop WxH` without an offset tiles the
image into many output files.

**Orientation.** Phone photos store rotation in EXIF. Run `-auto-orient` first,
or resizing/cropping applies to the unrotated pixels — and `-strip` then
removes the EXIF tag, leaving the image sideways.

**Transparency into JPEG.** JPEG has no alpha; transparent areas turn black
(or random colors). Flatten onto a background first:
`magick in.png -background white -alpha remove -alpha off out.jpg`.

**`-quality` means different things per format.**
- JPEG/WebP: 1–100 lossy quality (82–85 is a good web default). Without
  `-quality`, JPEG uses the input's estimated quality or 92.
- PNG: not a quality — the two digits pick zlib level and filter; PNG stays
  lossless. Shrink PNGs by reducing colors (`-colors 256`) or converting to
  WebP instead.
- WebP lossless needs `-define webp:lossless=true`.

**`-strip` removes metadata, including color profiles.** Good for web
size; for wide-gamut photos, convert to sRGB first (`-colorspace sRGB` or
`-profile`) or colors shift.

**Option order matters in v7.** Settings (`-gravity`, `-background`,
`-quality`, `-fill`) must come *before* the operator they affect
(`-extent`, `-annotate`, `-composite`) and after the input is read.

**Security policy.** "not authorized" errors for PDF/PS/SVG come from
`policy.xml` (e.g. `/etc/ImageMagick-7/policy.xml`). Tell the user rather than
editing the system policy yourself.

# Troubleshooting

| Error | Cause / fix |
|---|---|
| `magick: not found` | Not installed, or v6 (use `convert`) — see Prerequisites. |
| `not authorized` | Security policy blocks the format — see above; ask the user. |
| `no decode delegate for this image format` | Missing format library (libjpeg/libpng/libwebp/libheif); reinstall with that support. |
| `memory allocation failed` / cache resources exhausted | Image too large — add `-limit memory 2GB -limit map 4GB`, or process in chunks. |
| Black background in JPEG output | Source had alpha — flatten with `-background white -alpha remove`. |
| Output sideways after resize | Add `-auto-orient` before other operations. |
