#!/usr/bin/env python3
"""Export one or more Figma nodes as images (PNG/JPG/SVG/PDF) in ONE API call.

Every node must belong to the same file. Pass several URLs and/or --ids to
render them together: GET /v1/images is a Tier 1 endpoint (View/Collab seats
get 6 calls per month), so batching saves quota. Prints one saved path per line.

--image-fills downloads the ORIGINAL uploaded images behind image fills (the
`ref:` values figma_fetch.py prints) via GET /v1/files/:key/images — a Tier 2
endpoint, so it does not spend Tier 1 quota.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figma_common import (  # noqa: E402
    FigmaAPIError,
    collect_targets,
    fail,
    figma_get,
    get_token,
)

VALID_FORMATS = ("png", "jpg", "svg", "pdf")

__all__ = [
    "get_token",
    "safe_filename",
    "build_render_params",
    "plan_outputs",
    "parse_image_refs",
    "sniff_image_ext",
]

IMAGE_REF_RE = re.compile(r"^[0-9a-fA-F]{8,64}$")


def parse_image_refs(raw: str) -> list[str]:
    """Split a comma-separated imageRef list, validating and de-duplicating."""
    refs = [r.strip() for r in raw.split(",") if r.strip()]
    if not refs:
        raise ValueError("--image-fills needs at least one imageRef.")
    bad = [r for r in refs if not IMAGE_REF_RE.match(r)]
    if bad:
        raise ValueError(
            f"Not an imageRef: {', '.join(bad)}. Use the hex 'ref:' value that "
            "figma_fetch.py prints for an image fill."
        )
    return list(dict.fromkeys(refs))


def sniff_image_ext(head: bytes) -> str:
    """Guess a file extension from an image's first bytes (default 'png')."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head.lstrip().startswith((b"<svg", b"<?xml")):
        return "svg"
    return "png"


def safe_filename(name: str) -> str:
    """Reduce a string to a filesystem-safe stem (letters, digits, _ and -)."""
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s]+", "_", name.strip())
    return name or "figma_export"


def build_render_params(
    node_ids: list[str],
    fmt: str,
    scale: float,
    *,
    version: str | None = None,
    contents_only: bool | None = None,
    use_absolute_bounds: bool | None = None,
    svg_outline_text: bool | None = None,
) -> dict[str, object]:
    """Build the GET /v1/images query params (None values are omitted)."""
    params: dict[str, object] = {
        "ids": ",".join(node_ids),
        "format": fmt,
        "scale": scale,
        "version": version,
        "contents_only": contents_only,
        "use_absolute_bounds": use_absolute_bounds,
    }
    if fmt == "svg":
        params["svg_include_id"] = True
        params["svg_outline_text"] = svg_outline_text
    return params


def plan_outputs(
    node_ids: list[str],
    fmt: str,
    *,
    output: str | None = None,
    out_dir: str | None = None,
    names: list[str] | None = None,
) -> dict[str, Path]:
    """Map each node id to its destination file. Raises ValueError on misuse.

    `output` is only valid for a single node. Otherwise files go into `out_dir`
    (default: current dir) as `<name>.<fmt>`, where name comes from `names`
    (same order as node ids) or defaults to `figma_<node-id>`.
    """
    if output and out_dir:
        raise ValueError("Use either --output or --out-dir, not both.")
    if output and len(node_ids) > 1:
        raise ValueError(
            f"--output takes one file but {len(node_ids)} nodes were requested; "
            "use --out-dir (and optionally --names) instead."
        )
    if names is not None and len(names) != len(node_ids):
        raise ValueError(
            f"--names has {len(names)} entries but {len(node_ids)} nodes were "
            "requested; give one name per node, in the same order."
        )
    if output:
        return {node_ids[0]: Path(output).expanduser().resolve()}

    base = Path(out_dir or ".").expanduser().resolve()
    plan: dict[str, Path] = {}
    used: set[str] = set()
    for i, nid in enumerate(node_ids):
        default = "figma_" + nid.replace(":", "-").replace(";", "_")
        stem = safe_filename(names[i]) if names else safe_filename(default)
        if stem in used:
            raise ValueError(f"Duplicate output name {stem!r}; names must be unique.")
        used.add(stem)
        plan[nid] = base / f"{stem}.{fmt}"
    return plan


def download_file(url: str, dest: Path) -> None:
    """Download a rendered image URL (pre-signed, no auth) to `dest`."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as resp:
        dest.write_bytes(resp.read())


def download_image_fills(
    file_key: str, token: str, refs: list[str], out_dir: Path, names: list[str] | None
) -> int:
    """Download original image-fill files; print each path; return failures."""
    try:
        data = figma_get(f"/v1/files/{file_key}/images", token)
    except FigmaAPIError as e:
        fail(e.message)
    urls = (data.get("meta") or {}).get("images") or {}
    out_dir.mkdir(parents=True, exist_ok=True)
    failed = 0
    for i, ref in enumerate(refs):
        url = urls.get(ref)
        if not url:
            print(
                f"ERROR: imageRef {ref} not found in this file (wrong ref or file).",
                file=sys.stderr,
            )
            failed += 1
            continue
        stem = safe_filename(names[i]) if names else f"figma_fill_{ref[:12]}"
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                body = resp.read()
        except (urllib.error.URLError, OSError) as e:
            print(f"ERROR: Could not download imageRef {ref}: {e}", file=sys.stderr)
            failed += 1
            continue
        dest = out_dir / f"{stem}.{sniff_image_ext(body[:16])}"
        dest.write_bytes(body)
        print(dest)
    return failed


def parse_bool(value: str) -> bool:
    """argparse type for explicit true/false flags."""
    lowered = value.strip().lower()
    if lowered in ("true", "1", "yes"):
        return True
    if lowered in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError(f"expected true or false, got {value!r}")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Export Figma node(s) as images in one API call and print the saved "
            "paths, one per line."
        )
    )
    parser.add_argument(
        "urls",
        nargs="+",
        metavar="URL",
        help="Figma URL(s) with node-id, all from the same file (with "
        "--image-fills, any link to the file). Quote each one.",
    )
    parser.add_argument(
        "--ids",
        help="Extra comma-separated node ids from the same file (e.g. 1-2,3:4)",
    )
    parser.add_argument(
        "--image-fills",
        metavar="REF,REF",
        help="Download the original images behind these image fills (the 'ref:' "
        "values from figma_fetch.py) instead of rendering nodes. Tier 2.",
    )
    parser.add_argument("--format", choices=VALID_FORMATS, default="png")
    parser.add_argument(
        "--scale", type=float, default=2.0, help="Scale 0.01–4 (default: 2)"
    )
    parser.add_argument(
        "--output", metavar="PATH", help="Destination file (single node only)"
    )
    parser.add_argument(
        "--out-dir", metavar="DIR", help="Destination directory (multiple nodes)"
    )
    parser.add_argument(
        "--names",
        help="Comma-separated file names (no extension), one per node, in order",
    )
    parser.add_argument("--version", help="Render a specific file version id")
    parser.add_argument(
        "--contents-only",
        type=parse_bool,
        metavar="true|false",
        help="false also renders content overlapping the node (API default: true)",
    )
    parser.add_argument(
        "--absolute-bounds",
        action="store_true",
        help="Use the node's full dimensions even if cropped (use_absolute_bounds)",
    )
    parser.add_argument(
        "--svg-outline-text",
        type=parse_bool,
        metavar="true|false",
        help="SVG only: false keeps text as <text> elements (API default: true)",
    )
    return parser


def main() -> None:
    """CLI entry point."""
    args = build_parser().parse_args()
    if not 0.01 <= args.scale <= 4:
        fail("--scale must be between 0.01 and 4.", 2)

    if args.image_fills:
        try:
            file_key, node_ids = collect_targets(args.urls, args.ids)
            if args.ids or args.output:
                raise ValueError(
                    "--image-fills cannot be combined with --ids or --output; "
                    "use --out-dir (and optionally --names)."
                )
            refs = parse_image_refs(args.image_fills)
            names = (
                [n.strip() for n in args.names.split(",")] if args.names else None
            )
            if names is not None and len(names) != len(refs):
                raise ValueError(
                    f"--names has {len(names)} entries but {len(refs)} image "
                    "refs were given; give one name per ref, in order."
                )
        except ValueError as e:
            fail(str(e), 2)
        out_dir = Path(args.out_dir or ".").expanduser().resolve()
        token = get_token()
        if download_image_fills(file_key, token, refs, out_dir, names):
            sys.exit(1)
        return

    try:
        file_key, node_ids = collect_targets(args.urls, args.ids)
        if not node_ids:
            raise ValueError(
                "No node id given. In Figma, right-click a layer → 'Copy link to "
                "selection' and pass that URL, or add --ids."
            )
        names = [n.strip() for n in args.names.split(",")] if args.names else None
        plan = plan_outputs(
            node_ids,
            args.format,
            output=args.output,
            out_dir=args.out_dir,
            names=names,
        )
    except ValueError as e:
        fail(str(e), 2)

    params = build_render_params(
        node_ids,
        args.format,
        args.scale,
        version=args.version,
        contents_only=args.contents_only,
        use_absolute_bounds=True if args.absolute_bounds else None,
        svg_outline_text=args.svg_outline_text,
    )
    token = get_token()
    try:
        data = figma_get(f"/v1/images/{file_key}", token, params)
    except FigmaAPIError as e:
        fail(e.message)
    if data.get("err"):
        fail(f"Figma render failed: {data['err']}")

    images = data.get("images") or {}
    failed = 0
    for nid, dest in plan.items():
        image_url = images.get(nid)
        if not image_url:
            print(
                f"ERROR: No image rendered for node {nid} (empty, invisible, or "
                "wrong id).",
                file=sys.stderr,
            )
            failed += 1
            continue
        try:
            download_file(image_url, dest)
        except (urllib.error.URLError, OSError) as e:
            print(f"ERROR: Could not save node {nid} to {dest}: {e}", file=sys.stderr)
            failed += 1
            continue
        print(dest)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
