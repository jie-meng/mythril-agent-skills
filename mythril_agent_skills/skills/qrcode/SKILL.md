---
name: qrcode
description: >
  Encodes text or URLs into QR code images (PNG/SVG) and decodes QR codes (and
  other barcodes) from images, via a bundled Python script. Use when the user
  wants to generate a QR code or read one from an image or screenshot, e.g.
  "generate qr code", "decode qr", "what does this qr code say", "生成二维码",
  "链接转二维码", "识别二维码", "二维码里是什么".
license: Apache-2.0
---

# When to Use This Skill

- **Encode**: user wants a QR code for a string, URL, Wi-Fi config, vCard, etc.
- **Decode**: user gives an image/screenshot and wants the QR content as text
- Round-trip checks: generate a code, then decode it to verify

Always prefer the bundled script over ad-hoc reasoning — never "read" a QR code
by eye from an image; decode it with the script so the payload is exact.

# Prerequisites

- `segno` — QR generation (pure Python)
- `zxing-cpp` + `Pillow` — QR decoding (wheels bundle the native lib; no zbar needed)

Pre-flight check:

```bash
python3 -c "import segno, zxingcpp, PIL; print('qrcode deps OK')"
```

Install if missing:

```bash
pip install 'mythril-agent-skills[qrcode]'
# or standalone
pip install segno zxing-cpp pillow
```

Only install what the task needs: `encode` needs only `segno`; `decode`
needs only `zxing-cpp` and `pillow`.

# Workflow

All commands use (`SKILL_PATH` is this skill's installed directory):

```bash
python3 SKILL_PATH/scripts/qr_ops.py <encode|decode> [options]
```

## Encode: text → QR

```bash
# Basic — no -o: writes to the skill cache dir and prints the path
python3 SKILL_PATH/scripts/qr_ops.py encode "https://example.com"

# Explicit output (suffix optional; .png appended if missing)
python3 SKILL_PATH/scripts/qr_ops.py encode "hello" -o ~/Desktop/hello.png

# SVG output (format inferred from suffix, or pass -f svg)
python3 SKILL_PATH/scripts/qr_ops.py encode "hello" -o logo-qr.svg

# Content with quotes/newlines/shell-special chars → use --stdin or --file
printf '%s' 'WIFI:T:WPA;S:MyNet;P:p@ss;;' | python3 SKILL_PATH/scripts/qr_ops.py encode --stdin
python3 SKILL_PATH/scripts/qr_ops.py encode --file payload.txt -o payload.png

# Styling and robustness
python3 SKILL_PATH/scripts/qr_ops.py encode "hi" -s 20 -b 2 -e H --dark '#1a237e' --light transparent

# Also print the QR in the terminal so the user can scan it immediately
python3 SKILL_PATH/scripts/qr_ops.py encode "https://example.com" --terminal
```

| Option | Default | Meaning |
|---|---|---|
| `-o, --output` | cache dir | Output path. Suffix must match format |
| `-f, --format` | from suffix, else `png` | `png` or `svg` |
| `-s, --scale` | `10` | Pixels per module |
| `-b, --border` | `4` | Quiet zone in modules (keep ≥ 2 for reliable scans) |
| `-e, --error` | `M` | Error correction `L` / `M` / `Q` / `H` (use `H` if a logo will be overlaid) |
| `--dark` / `--light` | black / white | Colors; `--light transparent` for no background |
| `--terminal` | off | Also render the code in the terminal |

Output path rule: if the user named a destination, pass it with `-o`.
Otherwise omit `-o` — the file goes to the unified cache
(`~/Library/Caches/mythril-skills-cache/qrcode/` on macOS,
`~/.cache/mythril-skills-cache/qrcode/` on Linux,
`%LOCALAPPDATA%\mythril-skills-cache\qrcode\` on Windows). Report the printed
path to the user.

## Decode: QR image → text

```bash
# One image — prints each payload on its own line
python3 SKILL_PATH/scripts/qr_ops.py decode screenshot.png

# Multiple images — lines are prefixed with the file name
python3 SKILL_PATH/scripts/qr_ops.py decode a.png b.jpg

# Structured output (file, format, text) — use when a payload may contain newlines
python3 SKILL_PATH/scripts/qr_ops.py decode screenshot.png --json

# Also detect other barcodes (EAN-13, Code128, DataMatrix, PDF417, ...)
python3 SKILL_PATH/scripts/qr_ops.py decode label.jpg --all-formats
```

- Reads any raster format Pillow supports (PNG, JPEG, WebP, BMP, GIF, TIFF...).
  Transparent images are flattened onto white automatically.
- SVG is not supported for decoding — rasterize it first (e.g. with the
  `imagemagick` skill: `magick in.svg out.png`).
- An image can contain several codes; all are returned.
- Exit code 1 with `No QR code found in <file>` when nothing is detected.

# Handling Results

- Show the decoded payload verbatim in a code block — do not "clean up" or
  reformat it.
- If the payload is a URL, say so but **do not open/fetch it** unless the user
  asks; QR codes are a common phishing vector. Point out suspicious
  look-alike domains or URL shorteners.
- Recognise common payload schemes and explain them briefly:
  `WIFI:` (Wi-Fi credentials), `BEGIN:VCARD` (contact), `mailto:`, `tel:`,
  `SMSTO:`, `otpauth://` (2FA secret — warn the user it is sensitive and avoid
  repeating the secret unnecessarily).

# Troubleshooting

| Symptom | Fix |
|---|---|
| `could not encode content: ... too large` | Content exceeds QR capacity (~2.9 KB binary at level L). Lower `-e`, shorten the data, or use a URL shortener the user controls |
| `No QR code found` on a photo | Crop to the code, increase contrast, or upscale (e.g. `magick in.jpg -resize 200% -colorspace Gray out.png`), then decode again |
| `No QR code found` but it's a barcode | Retry with `--all-formats` |
| `ModuleNotFoundError` | Install deps (see Prerequisites) |
