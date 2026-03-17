---
name: imagemagick
description: >
  Process and manipulate images using ImageMagick CLI (`magick`). Supports resizing,
  format conversion, cropping, thumbnails, effects, watermarks, batch processing,
  and metadata extraction. Trigger whenever the user asks to resize, convert, crop,
  compress, optimize, or transform images, create thumbnails, add watermarks,
  apply filters/effects, batch process images, get image dimensions/metadata,
  or says phrases like "resize image", "convert to webp", "image thumbnail",
  "batch resize", "compress image", "image dimensions", "add watermark",
  "图片处理", "图片转换", "图片压缩", "缩略图", "批量处理图片", "图片裁剪",
  "imagemagick", "magick".
license: Apache-2.0
---

# When to Use This Skill

- User asks to resize, crop, rotate, or transform images
- User asks to convert images between formats (PNG, JPEG, WebP, GIF, SVG, etc.)
- User asks to create thumbnails or responsive image variants
- User asks to add watermarks, borders, text overlays, or frames
- User asks to apply effects/filters (blur, sharpen, grayscale, sepia, etc.)
- User asks to batch process or bulk-transform multiple images
- User asks to get image dimensions, metadata, or file info
- User asks to optimize/compress images for web
- User mentions "imagemagick", "magick", or any image manipulation task

# Prerequisites

Requires `magick` CLI (ImageMagick v7+) installed and on PATH.

**Verify installation:**

```bash
magick -version
```

**Install if missing:**

- macOS: `brew install imagemagick`
- Ubuntu/Debian: `sudo apt-get install imagemagick`
- Windows: Download from https://imagemagick.org/script/download.php

> On older systems with ImageMagick 6.x, use `convert` instead of `magick`.

# Workflow

## 1) Pre-flight check

Verify `magick` is available before running any operation:

```bash
command -v magick &> /dev/null || { echo "ImageMagick not found. Install: brew install imagemagick (macOS) or sudo apt-get install imagemagick (Linux)"; exit 1; }
```

## 2) Determine the operation

Identify what the user needs from these categories:

| Category | Operations |
|---|---|
| Info | Dimensions, metadata, format, color space |
| Convert | Format conversion, quality settings |
| Resize | Scale, fit, fill, percentage |
| Crop | Region extraction, center crop, aspect ratio crop |
| Thumbnail | Resize + crop for fixed dimensions |
| Effects | Blur, sharpen, grayscale, sepia, negate, edge, emboss |
| Adjust | Brightness, contrast, saturation, hue, auto-level |
| Transform | Rotate, flip, flop, auto-orient |
| Overlay | Text, watermarks, compositing, borders |
| Batch | mogrify or shell loops for multiple files |
| Animate | GIF creation, optimization, frame extraction |

## 3) Determine output filename

**Default: write to a new file, never overwrite the original.**

- If the user did NOT say to overwrite or modify in-place → generate a descriptive output filename in the same directory (e.g. `photo_resized.jpg`, `banner_gray.png`).
- If the user explicitly asks to overwrite (e.g. "覆盖", "replace", "in-place", "same name", "原图修改") → output to the same filename or use `mogrify`.
- For format conversion the extension naturally changes, so `photo.png` → `photo.jpg` already preserves the original.
- For batch operations, prefer outputting to a subdirectory (`mkdir -p output && mogrify -path ./output ...`) unless the user says to overwrite.

## 4) Execute the operation

### Geometry Specifications

ImageMagick uses geometry strings for dimensions:

| Syntax | Meaning |
|---|---|
| `100x100` | Fit within 100×100 (maintains aspect ratio) |
| `100x100!` | Force exact size (ignores aspect ratio) |
| `100x100^` | Fill 100×100 (may exceed, maintains aspect ratio) |
| `100x` | Width 100, auto height |
| `x100` | Height 100, auto width |
| `50%` | Scale to 50% |
| `100x100+10+20` | 100×100 region at offset (10, 20) |

### Format Conversion

```bash
# Basic conversion (format inferred from extension)
magick input.png output.jpg

# With quality control
magick input.png -quality 85 -strip output.jpg

# To WebP
magick input.jpg -quality 80 output.webp

# Lossless WebP
magick input.png -define webp:lossless=true output.webp

# Progressive JPEG (better for web)
magick input.png -quality 85 -interlace Plane -strip output.jpg
```

### Resizing

```bash
# Fit within dimensions (maintains aspect ratio)
magick input.jpg -resize 800x600 output.jpg

# Width only (auto height)
magick input.jpg -resize 800x output.jpg

# Height only (auto width)
magick input.jpg -resize x600 output.jpg

# Exact dimensions (ignores aspect ratio)
magick input.jpg -resize 800x600! output.jpg

# Scale by percentage
magick input.jpg -resize 50% output.jpg

# Shrink only (don't enlarge)
magick input.jpg -resize '800x600>' output.jpg

# Enlarge only (don't shrink)
magick input.jpg -resize '800x600<' output.jpg
```

### Cropping

```bash
# Crop region at offset
magick input.jpg -crop 400x400+100+100 +repage output.jpg

# Center crop
magick input.jpg -gravity center -crop 400x400+0+0 +repage output.jpg
```

### Thumbnail Generation (Resize + Crop)

```bash
# Square thumbnail from any aspect ratio
magick input.jpg -resize 200x200^ -gravity center -extent 200x200 thumb.jpg

# With specific background for padding
magick input.jpg -resize 200x200 -background white -gravity center -extent 200x200 thumb.jpg
```

### Effects and Filters

```bash
# Blur
magick input.jpg -blur 0x8 output.jpg

# Sharpen
magick input.jpg -sharpen 0x1 output.jpg

# Grayscale
magick input.jpg -colorspace Gray output.jpg

# Sepia tone
magick input.jpg -sepia-tone 80% output.jpg

# Negate (invert)
magick input.jpg -negate output.jpg

# Edge detection
magick input.jpg -edge 3 output.jpg

# Oil painting
magick input.jpg -paint 4 output.jpg

# Charcoal drawing
magick input.jpg -charcoal 2 output.jpg
```

### Adjustments

```bash
# Brightness and contrast
magick input.jpg -brightness-contrast 10x20 output.jpg

# Saturation (modulate: brightness, saturation, hue)
magick input.jpg -modulate 100,150,100 output.jpg

# Auto-level (normalize contrast)
magick input.jpg -auto-level output.jpg

# Auto-orient based on EXIF
magick input.jpg -auto-orient output.jpg

# Strip metadata (reduce file size)
magick input.jpg -strip output.jpg
```

### Rotation and Flipping

```bash
# Rotate 90° clockwise
magick input.jpg -rotate 90 output.jpg

# Rotate with background color
magick input.jpg -background white -rotate 45 output.jpg

# Flip vertically
magick input.jpg -flip output.jpg

# Mirror horizontally
magick input.jpg -flop output.jpg
```

### Borders and Frames

```bash
# Add border
magick input.jpg -bordercolor black -border 10x10 output.jpg

# Add shadow
magick input.jpg \( +clone -background black -shadow 80x3+5+5 \) \
  +swap -background white -layers merge +repage output.jpg
```

### Text and Watermarks

```bash
# Add text
magick input.jpg -gravity south -pointsize 20 -fill white \
  -annotate +0+10 "Copyright 2025" output.jpg

# Semi-transparent watermark
magick input.jpg \( -background none -fill "rgba(255,255,255,0.5)" \
  -pointsize 50 label:"DRAFT" \) -gravity center -compose over -composite output.jpg

# Image watermark (bottom-right)
magick input.jpg watermark.png -gravity southeast \
  -geometry +10+10 -composite output.jpg
```

### Compositing

```bash
# Side-by-side
magick input1.jpg input2.jpg +append output.jpg

# Stack vertically
magick input1.jpg input2.jpg -append output.jpg

# Overlay
magick input.jpg overlay.png -gravity center -compose over -composite output.jpg
```

### Image Information

```bash
# Basic info
magick identify image.jpg

# Dimensions only
magick identify -format "%wx%h" image.jpg

# Detailed info
magick identify -verbose image.jpg

# Format string: filename, size, format
magick identify -format "%f: %wx%h %b %m\n" image.jpg
```

Common format tokens: `%f` filename, `%w` width, `%h` height, `%b` file size, `%m` format, `%[colorspace]` colorspace, `%[depth]` bit depth.

### Batch Processing

**Using mogrify (prefer `-path` to preserve originals):**

```bash
# Resize all JPEGs to output directory (originals preserved)
mkdir -p resized
mogrify -path ./resized -resize 800x600 *.jpg

# Convert all PNGs to JPEG (output directory preserves originals)
mkdir -p output
mogrify -path ./output -format jpg -quality 85 -strip *.png

# Batch thumbnails
mkdir -p thumbnails
mogrify -path ./thumbnails -resize 200x200^ -gravity center \
  -crop 200x200+0+0 +repage *.jpg

# In-place overwrite (ONLY when user explicitly requests it)
mogrify -resize 800x600 *.jpg
```

**Using shell loops (more control):**

```bash
# Responsive image variants
for size in 320 640 1024 1920; do
  magick input.jpg -resize ${size}x -quality 85 "output-${size}w.jpg"
done

# Convert with custom naming
for img in *.png; do
  magick "$img" -quality 90 "${img%.png}.jpg"
done
```

### Animated GIFs

```bash
# Create GIF from frames
magick -delay 100 -loop 0 frame*.png animated.gif

# Optimize existing GIF
magick animated.gif -fuzz 5% -layers Optimize optimized.gif

# Extract frames
magick animated.gif frame_%03d.png
```

### Contact Sheets (Montage)

```bash
# Basic grid with labels
montage *.jpg -geometry 200x200+5+5 -label '%f' contact-sheet.jpg

# 3-column layout
montage *.jpg -tile 3x -geometry 200x200+5+5 contact-sheet.jpg
```

## 5) Performance Tips

```bash
# Limit memory for large images
magick -limit memory 2GB -limit map 4GB input.jpg -resize 50% output.jpg

# Set thread count
magick -limit thread 4 input.jpg -resize 50% output.jpg
```

### Web Optimization Quick Reference

| Goal | Command flags |
|---|---|
| High quality | `-quality 95` |
| Balanced (recommended) | `-quality 85 -strip` |
| Smaller file | `-quality 70 -sampling-factor 4:2:0 -strip` |
| Progressive JPEG | `-quality 85 -interlace Plane -strip` |

# Guidelines

1. **Preserve original files by default.** Unless the user explicitly asks to overwrite the original (e.g. "覆盖原图", "replace in-place", "modify the original", "same filename"), ALWAYS output to a new filename in the same directory. Naming conventions:
   - Resize: `photo.jpg` → `photo_800x600.jpg`
   - Convert: `photo.png` → `photo.jpg`
   - Effect: `photo.jpg` → `photo_blur.jpg`, `photo_gray.jpg`
   - Thumbnail: `photo.jpg` → `photo_thumb.jpg`
   - General: `photo.jpg` → `photo_processed.jpg`
   - Batch: output to a subdirectory (e.g. `resized/`, `thumbnails/`) or add a prefix/suffix to each filename

   Only use `mogrify` (in-place modification) when the user explicitly requests overwriting originals. When using `mogrify` for batch operations, prefer `-path ./output_dir` to preserve originals.

2. **Always quote file paths** that might contain spaces
3. **Use `+repage`** after crop to reset virtual canvas
4. **Use `-strip`** to remove metadata when optimizing for web
5. **Use `-auto-orient`** to respect EXIF orientation before processing
6. **Test on a sample** before running batch operations
7. **Set quality explicitly** — default is lossless for some formats, which means large files
8. **Use progressive JPEG** (`-interlace Plane`) for web delivery

# Troubleshooting

**"magick: not found"** — ImageMagick not installed or not on PATH. Install via `brew install imagemagick` (macOS) or `sudo apt-get install imagemagick` (Linux).

**"not authorized"** — ImageMagick security policy blocking the operation. Check/edit `/etc/ImageMagick-7/policy.xml`.

**"no decode delegate"** — Missing format support library (libjpeg, libpng, libwebp). Install the missing library and reinstall ImageMagick.

**"memory allocation failed"** — Image too large. Use `-limit memory` and `-limit map` flags, or process in smaller chunks.
