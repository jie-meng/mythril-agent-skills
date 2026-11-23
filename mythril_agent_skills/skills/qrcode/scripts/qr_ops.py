#!/usr/bin/env python3
"""Encode text into QR code images and decode QR codes from images.

Subcommands:
    encode  text -> QR image (PNG or SVG), powered by segno
    decode  image(s) -> text payload(s), powered by zxing-cpp + Pillow

When no output path is given, encoded images are written to the unified
per-user skill cache: <user-cache-root>/mythril-skills-cache/qrcode/.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import NoReturn

SKILL_NAME = "qrcode"
SUPPORTED_FORMATS = ("png", "svg")
ERROR_LEVELS = ("L", "M", "Q", "H")
INSTALL_HINT = "pip install 'mythril-agent-skills[qrcode]'  (or: pip install {pkgs})"


# --- Pure helpers ---------------------------------------------------------


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


def slugify(text: str, max_len: int = 32) -> str:
    """Turn arbitrary content into a short filesystem-safe slug."""
    text = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", text.strip())
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    slug = slug[:max_len].rstrip("-")
    return slug or "qr"


def default_output_name(content: str, fmt: str, now: datetime) -> str:
    """Build a default filename like ``qr-example-com-20260101-120000.png``."""
    return f"qr-{slugify(content)}-{now.strftime('%Y%m%d-%H%M%S')}.{fmt}"


def resolve_format(output: str | None, fmt: str | None) -> str:
    """Decide output format from an explicit --format or the output suffix."""
    if fmt:
        fmt = fmt.lower()
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(f"unsupported format: {fmt}")
        return fmt
    if output:
        suffix = Path(output).suffix.lower().lstrip(".")
        if suffix in SUPPORTED_FORMATS:
            return suffix
    return "png"


def resolve_output_path(raw: str | None, fmt: str, default_dir: Path,
                        default_name: str) -> Path:
    """Return the final output path, normalising suffix to ``fmt``.

    - ``raw`` is None → ``default_dir / default_name``
    - ``raw`` without suffix → suffix appended
    - ``raw`` with a different image suffix → ValueError
    """
    if raw is None:
        return default_dir / default_name
    path = Path(raw).expanduser()
    suffix = path.suffix.lower().lstrip(".")
    if not suffix:
        return path.with_suffix(f".{fmt}")
    if suffix != fmt:
        raise ValueError(
            f"output suffix '.{suffix}' does not match format '{fmt}'"
        )
    return path


def validate_encode_params(scale: int, border: int, error: str) -> None:
    """Validate numeric/enum encode parameters; raise ValueError on bad input."""
    if scale < 1:
        raise ValueError(f"scale must be >= 1, got {scale}")
    if border < 0:
        raise ValueError(f"border must be >= 0, got {border}")
    if error.upper() not in ERROR_LEVELS:
        raise ValueError(f"error level must be one of {ERROR_LEVELS}, got {error}")


def format_decode_results(results: list[dict[str, str]], as_json: bool) -> str:
    """Render decode results (dicts with file/format/text) as text or JSON."""
    if as_json:
        return json.dumps(results, ensure_ascii=False, indent=2)
    files = {r["file"] for r in results}
    lines: list[str] = []
    for r in results:
        prefix = f"{r['file']}: " if len(files) > 1 else ""
        lines.append(f"{prefix}{r['text']}")
    return "\n".join(lines)


# --- Side-effecting commands ---------------------------------------------


def _fail(msg: str) -> NoReturn:
    """Print an error to stderr and exit 1."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def cmd_encode(args: argparse.Namespace) -> None:
    """Encode text into a QR image."""
    try:
        import segno
    except ImportError:
        _fail("segno is not installed. Install with: "
              + INSTALL_HINT.format(pkgs="segno"))

    if args.stdin:
        content = sys.stdin.read()
        if content.endswith("\n"):
            content = content[:-1]
    elif args.file:
        content = Path(args.file).expanduser().read_text(encoding="utf-8")
    else:
        content = args.content
    if content is None or content == "":
        _fail("no content to encode (pass TEXT, --stdin, or --file)")

    try:
        validate_encode_params(args.scale, args.border, args.error)
        fmt = resolve_format(args.output, args.format)
        default_dir = get_cache_root() / SKILL_NAME
        output = resolve_output_path(
            args.output, fmt, default_dir,
            default_output_name(content, fmt, datetime.now()),
        )
    except ValueError as exc:
        _fail(str(exc))

    if output.is_dir():
        _fail(f"output is a directory: {output}")

    try:
        qr = segno.make_qr(content, error=args.error.lower(), boost_error=False)
    except (ValueError, segno.DataOverflowError) as exc:
        _fail(f"could not encode content: {exc}")

    output.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs: dict[str, object] = {"scale": args.scale, "border": args.border}
    if args.dark:
        save_kwargs["dark"] = args.dark
    if args.light:
        save_kwargs["light"] = None if args.light == "transparent" else args.light
    qr.save(str(output), kind=fmt, **save_kwargs)

    if args.terminal:
        qr.terminal(compact=True, border=args.border)

    print(f"Wrote {output}")
    print(f"QR version {qr.version}, error level {qr.error}, "
          f"{len(content)} chars")


def cmd_decode(args: argparse.Namespace) -> None:
    """Decode all QR codes in one or more images."""
    try:
        import zxingcpp
        from PIL import Image
    except ImportError:
        _fail("zxing-cpp / Pillow not installed. Install with: "
              + INSTALL_HINT.format(pkgs="zxing-cpp pillow"))

    formats = None if args.all_formats else zxingcpp.BarcodeFormat.QRCode
    results: list[dict[str, str]] = []
    missing: list[str] = []
    for raw in args.images:
        path = Path(raw).expanduser()
        if not path.is_file():
            _fail(f"file not found: {path}")
        try:
            with Image.open(path) as image:
                image.load()
                if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
                    # Flatten onto white so dark-on-transparent codes are readable.
                    rgba = image.convert("RGBA")
                    image = Image.new("RGB", rgba.size, "white")
                    image.paste(rgba, mask=rgba.getchannel("A"))
                found = (zxingcpp.read_barcodes(image, formats=formats)
                         if formats is not None
                         else zxingcpp.read_barcodes(image))
        except OSError as exc:
            _fail(f"could not read image {path}: {exc}")
        if not found:
            missing.append(str(path))
        for item in found:
            results.append({
                "file": str(path),
                "format": str(item.format).split(".")[-1],
                "text": item.text,
            })

    if results:
        print(format_decode_results(results, args.json))
    for m in missing:
        print(f"No QR code found in {m}", file=sys.stderr)
    if missing:
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Encode text to QR images and decode QR images to text.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encode", help="text -> QR image")
    enc.add_argument("content", nargs="?", help="text to encode")
    src = enc.add_mutually_exclusive_group()
    src.add_argument("--stdin", action="store_true", help="read text from stdin")
    src.add_argument("--file", help="read text from a UTF-8 file")
    enc.add_argument("-o", "--output",
                     help="output path (default: skill cache dir)")
    enc.add_argument("-f", "--format", choices=SUPPORTED_FORMATS,
                     help="png or svg (default: from -o suffix, else png)")
    enc.add_argument("-s", "--scale", type=int, default=10,
                     help="pixels per module (default: 10)")
    enc.add_argument("-b", "--border", type=int, default=4,
                     help="quiet zone in modules (default: 4)")
    enc.add_argument("-e", "--error", type=str.upper, choices=ERROR_LEVELS,
                     default="M", help="error correction level (default: M)")
    enc.add_argument("--dark", help="dark module color, e.g. '#000' or 'darkblue'")
    enc.add_argument("--light",
                     help="background color, or 'transparent'")
    enc.add_argument("--terminal", action="store_true",
                     help="also print the QR code to the terminal")
    enc.set_defaults(func=cmd_encode)

    dec = sub.add_parser("decode", help="QR image(s) -> text")
    dec.add_argument("images", nargs="+", help="image file(s) to scan")
    dec.add_argument("--json", action="store_true",
                     help="output JSON list of {file, format, text}")
    dec.add_argument("--all-formats", action="store_true",
                     help="also detect other barcodes (EAN, Code128, DataMatrix...)")
    dec.set_defaults(func=cmd_decode)
    return parser


def main() -> None:
    """CLI entry point."""
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
