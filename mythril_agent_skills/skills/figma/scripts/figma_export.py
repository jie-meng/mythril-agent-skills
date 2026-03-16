#!/usr/bin/env python3

import os, sys, re, argparse
import urllib.request
import urllib.error
from urllib.parse import urlencode, unquote

VALID_FORMATS = ("png", "jpg", "svg", "pdf")


def get_token():
    token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: FIGMA_ACCESS_TOKEN not set.", file=sys.stderr)
        print("Add to ~/.zshrc:  export FIGMA_ACCESS_TOKEN=your_token", file=sys.stderr)
        print(
            "Get token: https://www.figma.com/settings → Security → Personal access tokens",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def parse_figma_url(url):
    m = re.search(r"figma\.com/(?:design|file|proto)/([A-Za-z0-9_-]+)", url)
    if not m:
        print(f"ERROR: Could not parse file key from URL: {url}", file=sys.stderr)
        sys.exit(2)
    file_key = m.group(1)

    node_id = None
    nid_m = re.search(r"node[-_]id=([^&]+)", url)
    if nid_m:
        raw = unquote(nid_m.group(1))  # decode %3A → :
        node_id = raw.replace("-", ":")  # normalize 1-2 → 1:2
    return file_key, node_id


def _handle_rate_limit(e, path):
    """Parse 429 response headers and print actionable diagnostics."""
    retry_after = e.headers.get("Retry-After", "")
    plan_tier = e.headers.get("X-Figma-Plan-Tier", "unknown")
    limit_type = e.headers.get("X-Figma-Rate-Limit-Type", "unknown")
    upgrade_link = e.headers.get("X-Figma-Upgrade-Link", "")

    print(f"ERROR: Figma API 429 Rate Limited for {path}", file=sys.stderr)
    print(f"  Plan tier   : {plan_tier}", file=sys.stderr)
    print(f"  Limit type  : {limit_type}", file=sys.stderr)
    if retry_after:
        print(f"  Retry after : {retry_after}s", file=sys.stderr)

    if limit_type == "low":
        print("", file=sys.stderr)
        print(
            "  Your Figma seat is View or Collab. Tier 1 endpoints (GET /files,",
            file=sys.stderr,
        )
        print(
            "  /files/nodes, /images) are limited to 6 requests PER MONTH for",
            file=sys.stderr,
        )
        print(
            "  View/Collab seats (since Nov 2025). This is NOT a per-minute limit.",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print(
            "  FIX: Upgrade to a Dev or Full seat to get 10–20 requests/minute.",
            file=sys.stderr,
        )
    else:
        print("", file=sys.stderr)
        print(
            "  You have a Dev/Full seat but exceeded per-minute limits.",
            file=sys.stderr,
        )
        if retry_after:
            print(
                f"  Wait {retry_after} seconds before retrying.",
                file=sys.stderr,
            )

    if upgrade_link:
        print(f"  Upgrade/settings: {upgrade_link}", file=sys.stderr)


def figma_get(path, token, **params):
    import json

    url = f"https://api.figma.com{path}"
    if params:
        url += "?" + urlencode(params)
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            _handle_rate_limit(e, path)
            sys.exit(1)
        body = e.read().decode(errors="replace")
        print(f"ERROR: Figma API {e.code} for {path}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def download_file(url, dest_path):
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
        with open(dest_path, "wb") as f:
            f.write(data)
    except urllib.error.URLError as e:
        print(f"ERROR: Failed to download image: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"ERROR: Could not write file '{dest_path}': {e}", file=sys.stderr)
        sys.exit(1)


def safe_filename(name):
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s]+", "_", name.strip())
    return name or "figma_export"


def main():
    parser = argparse.ArgumentParser(
        description="Export a Figma node as an image (PNG/JPG/SVG/PDF) and save to disk."
    )
    parser.add_argument("url", help="Figma URL with a node-id (design/file/proto)")
    parser.add_argument(
        "--format",
        choices=VALID_FORMATS,
        default="png",
        help="Image format: png, jpg, svg, pdf (default: png)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=2.0,
        help="Export scale factor 0.01–4 (default: 2.0)",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Output file path (default: ./<node-name>.<format>)",
    )
    args = parser.parse_args()

    if not 0.01 <= args.scale <= 4:
        print("ERROR: --scale must be between 0.01 and 4.", file=sys.stderr)
        sys.exit(2)

    token = get_token()
    file_key, node_id = parse_figma_url(args.url)

    if not node_id:
        print(
            "ERROR: URL has no node-id. Open the file in Figma, right-click a layer → "
            "'Copy link to selection', then use that URL.",
            file=sys.stderr,
        )
        sys.exit(2)

    render_params = {
        "ids": node_id,
        "format": args.format,
        "scale": args.scale,
    }
    if args.format == "svg":
        render_params["svg_include_id"] = "true"

    data = figma_get(f"/v1/images/{file_key}", token, **render_params)

    err = data.get("err")
    if err:
        print(f"ERROR: Figma render failed: {err}", file=sys.stderr)
        sys.exit(1)

    images = data.get("images", {})
    image_url = images.get(node_id) or next(iter(images.values()), None)

    if not image_url:
        print(
            f"ERROR: No image returned for node '{node_id}'. "
            "The node may be empty or the ID may be wrong.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.output:
        dest = args.output
    else:
        dest = f"figma_{node_id.replace(':', '-')}.{args.format}"

    dest = os.path.abspath(dest)
    download_file(image_url, dest)
    print(dest)


if __name__ == "__main__":
    main()
