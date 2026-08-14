#!/usr/bin/env python3
"""Pure helpers for referencing images in Markdown documents.

Mirrors the nvim markdown paste-image convention so that asset locations and
filenames stay consistent between this skill and the user's editor:

  * assets live in a ``<doc-stem>.assets/`` directory co-located with the doc
  * files keep their basename; name collisions get ``-1``, ``-2``, ... suffixes
  * byte-identical files are reused instead of duplicated

Exposes pure, deterministic functions (no I/O beyond reading files for the
byte-identity check):

  * :func:`assets_dir_for`   co-located assets directory
  * :func:`slugify`          sanitize to ``mobile-arch.png`` style names
  * :func:`unique_path`      collision-safe destination (reuse if identical)
  * :func:`rel_asset_path`   relative link target from the document
  * :func:`markdown_link`    render ``![alt](path)``
"""

from __future__ import annotations

import re
from pathlib import Path

# Recognized image extensions (lowercase). Kept when slugifying a filename.
IMAGE_EXTS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "bmp",
    "svg",
    "tiff",
    "tif",
    "ico",
    "avif",
    "heic",
    "heif",
}


def assets_dir_for(md_path: Path) -> Path:
    """Return the assets directory co-located with a Markdown file.

    ``dir/foo.md`` -> ``dir/foo.assets`` (same convention as nvim).
    """
    return md_path.parent / (md_path.stem + ".assets")


def slugify(name: str) -> str:
    """Sanitize a filename into a lowercase ASCII slug such as ``mobile-arch.png``.

    A recognized image extension is preserved (lowercased). Every run of
    non-alphanumeric characters (spaces, punctuation, CJK, emoji) becomes a
    single hyphen; leading/trailing hyphens are trimmed. Falls back to
    ``image`` when nothing usable remains.
    """
    raw = Path(name).name
    stem, dot, ext = raw.rpartition(".")
    if dot and ext.lower() in IMAGE_EXTS:
        saved_ext = ext.lower()
        base = stem
    else:
        saved_ext = ""
        base = raw
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    if not slug:
        slug = "image"
    return f"{slug}.{saved_ext}" if saved_ext else slug


def unique_path(dest_dir: Path, desired: str, src_path: Path) -> Path:
    """Return a non-clobbering destination for *src_path* inside *dest_dir*.

    * If *desired* is free, return it directly.
    * If an existing file with that name is byte-identical to *src_path*, reuse it.
    * Otherwise append ``-1``, ``-2``, ... until a free (or identical) name.
    """
    def _identical(a: Path, b: Path) -> bool:
        try:
            return a.read_bytes() == b.read_bytes()
        except OSError:
            return False

    desired_path = dest_dir / desired
    if not desired_path.exists():
        return desired_path
    if _identical(desired_path, src_path):
        return desired_path

    stem, dot, ext = desired.rpartition(".")
    i = 1
    while True:
        suffix = f"-{i}"
        candidate_name = f"{stem}{suffix}.{ext}" if dot else f"{stem}{suffix}"
        candidate = dest_dir / candidate_name
        if not candidate.exists():
            return candidate
        if _identical(candidate, src_path):
            return candidate
        i += 1


def rel_asset_path(md_path: Path, filename: str) -> str:
    """Relative link target from the document to an asset in its assets dir.

    ``dir/foo.md``, ``bar.png`` -> ``foo.assets/bar.png``.
    """
    return f"{assets_dir_for(md_path).name}/{filename}"


def markdown_link(rel_path: str, alt: str | None = None) -> str:
    """Build a Markdown image reference; *alt* defaults to the filename stem."""
    if not alt or not alt.strip():
        alt = Path(rel_path).stem
    return f"![{alt}]({rel_path})"


def main() -> None:
    """Tiny CLI exposing the helpers for AI coding assistants.

    The real naming decision (content-based slug) is made by the agent reading
    the image; this CLI performs the deterministic math.
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Image reference helpers for Markdown documents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_assets = sub.add_parser(
        "assets-dir", help="print the co-located assets dir for a Markdown file"
    )
    p_assets.add_argument("md_path", type=Path)

    p_slug = sub.add_parser(
        "slug-filter", help="sanitize a filename to a lowercase ASCII slug"
    )
    p_slug.add_argument("name")

    p_unique = sub.add_parser(
        "unique", help="resolve a collision-safe destination filename"
    )
    p_unique.add_argument("dest_dir", type=Path)
    p_unique.add_argument("desired")
    p_unique.add_argument("src_path", type=Path)

    p_rel = sub.add_parser(
        "rel-link", help="relative link target from a Markdown file to an asset"
    )
    p_rel.add_argument("md_path", type=Path)
    p_rel.add_argument("filename")

    p_md = sub.add_parser("md-link", help="render a Markdown image reference")
    p_md.add_argument("rel_path")
    p_md.add_argument("alt", nargs="?", default=None)

    args = parser.parse_args()

    if args.command == "assets-dir":
        print(assets_dir_for(args.md_path))
    elif args.command == "slug-filter":
        print(slugify(args.name))
    elif args.command == "unique":
        print(unique_path(args.dest_dir, args.desired, args.src_path))
    elif args.command == "rel-link":
        print(rel_asset_path(args.md_path, args.filename))
    elif args.command == "md-link":
        print(markdown_link(args.rel_path, args.alt))
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()