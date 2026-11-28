# ImageMagick Command Recipes

Copy-ready commands for common jobs (ImageMagick 7 `magick` syntax). Replace
`input.*` / `output.*` with real paths (quoted), and follow the output-naming
rules in SKILL.md — never write over the source file unless the user asked.
With v7 installs that lack the standalone tools, run `mogrify` / `montage` /
`identify` as `magick mogrify` etc.; with v6, replace `magick` with `convert`.

## Contents

- [Format Conversion](#format-conversion)
- [Resizing](#resizing)
- [Cropping](#cropping)
- [Thumbnail Generation (Resize + Crop)](#thumbnail-generation-resize--crop)
- [Effects and Filters](#effects-and-filters)
- [Adjustments](#adjustments)
- [Rotation and Flipping](#rotation-and-flipping)
- [Borders and Frames](#borders-and-frames)
- [Text and Watermarks](#text-and-watermarks)
- [Compositing](#compositing)
- [Image Information](#image-information)
- [Batch Processing](#batch-processing)
- [Animated GIFs](#animated-gifs)
- [Contact Sheets (Montage)](#contact-sheets-montage)
- [Performance Tips](#performance-tips)

## Format Conversion

```bash
# Basic conversion (format inferred from extension)
magick input.png output.jpg

# PNG/WebP with transparency to JPEG (flatten first, or transparent areas turn black)
magick input.png -background white -alpha remove -alpha off output.jpg

# With quality control
magick input.png -quality 85 -strip output.jpg

# To WebP
magick input.jpg -quality 80 output.webp

# Lossless WebP
magick input.png -define webp:lossless=true output.webp

# Progressive JPEG (better for web)
magick input.png -quality 85 -interlace Plane -strip output.jpg
```

## Resizing

```bash
# Fit within dimensions (maintains aspect ratio)
magick input.jpg -resize 800x600 output.jpg

# Width only (auto height)
magick input.jpg -resize 800x output.jpg

# Height only (auto width)
magick input.jpg -resize x600 output.jpg

# Exact dimensions (ignores aspect ratio)
magick input.jpg -resize '800x600!' output.jpg

# Scale by percentage
magick input.jpg -resize 50% output.jpg

# Shrink only (don't enlarge)
magick input.jpg -resize '800x600>' output.jpg

# Enlarge only (don't shrink)
magick input.jpg -resize '800x600<' output.jpg
```

## Cropping

```bash
# Crop region at offset
magick input.jpg -crop 400x400+100+100 +repage output.jpg

# Center crop
magick input.jpg -gravity center -crop 400x400+0+0 +repage output.jpg
```

## Thumbnail Generation (Resize + Crop)

```bash
# Square thumbnail from any aspect ratio
magick input.jpg -resize '200x200^' -gravity center -extent 200x200 thumb.jpg

# With specific background for padding
magick input.jpg -resize 200x200 -background white -gravity center -extent 200x200 thumb.jpg
```

## Effects and Filters

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

## Adjustments

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

## Rotation and Flipping

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

## Borders and Frames

```bash
# Add border
magick input.jpg -bordercolor black -border 10x10 output.jpg

# Add shadow
magick input.jpg \( +clone -background black -shadow 80x3+5+5 \) \
  +swap -background white -layers merge +repage output.jpg
```

## Text and Watermarks

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

## Compositing

```bash
# Side-by-side
magick input1.jpg input2.jpg +append output.jpg

# Stack vertically
magick input1.jpg input2.jpg -append output.jpg

# Overlay
magick input.jpg overlay.png -gravity center -compose over -composite output.jpg
```

## Image Information

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

## Batch Processing

**Using mogrify (prefer `-path` to preserve originals):**

```bash
# Resize all JPEGs to output directory (originals preserved)
mkdir -p resized
mogrify -path ./resized -resize 800x600 *.jpg

# Convert all PNGs to JPEG (output directory preserves originals;
# -alpha remove flattens transparency onto white instead of black)
mkdir -p output
mogrify -path ./output -format jpg -background white -alpha remove -alpha off \
  -quality 85 -strip *.png

# Batch thumbnails
mkdir -p thumbnails
mogrify -path ./thumbnails -resize '200x200^' -gravity center \
  -extent 200x200 *.jpg

# In-place overwrite (ONLY when user explicitly requests it)
mogrify -resize 800x600 *.jpg
```

**Using shell loops (more control):**

```bash
# Responsive image variants
for size in 320 640 1024 1920; do
  magick input.jpg -resize ${size}x -quality 85 "output-${size}w.jpg"
done

# Convert with custom naming (flatten transparency for JPEG)
for img in *.png; do
  magick "$img" -background white -alpha remove -alpha off -quality 90 "${img%.png}.jpg"
done
```

## Animated GIFs

```bash
# Create GIF from frames
magick -delay 100 -loop 0 frame*.png animated.gif

# Optimize existing GIF
magick animated.gif -fuzz 5% -layers Optimize optimized.gif

# Extract frames (-coalesce rebuilds full frames; optimized GIFs store only
# the changed region of each frame)
magick animated.gif -coalesce frame_%03d.png
```

## Contact Sheets (Montage)

```bash
# Basic grid with labels (-label is a setting: it must come BEFORE the inputs)
montage -label '%f' *.jpg -geometry 200x200+5+5 contact-sheet.jpg

# 3-column layout
montage *.jpg -tile 3x -geometry 200x200+5+5 contact-sheet.jpg
```

## Performance Tips

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
