#!/usr/bin/env python3
"""Shared helpers for the figma skill scripts: auth, URL parsing, HTTP.

Used by figma_fetch.py and figma_export.py (same directory). Standard library
only. Parsing helpers are pure and raise ValueError on bad input; callers turn
that into a CLI error (exit code 2).
"""

from __future__ import annotations

import json
import os
import platform
import re
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from secret_guard import guard_args, install as install_secret_guard  # noqa: E402

API_BASE = "https://api.figma.com"

# Editor types whose links carry a file key that the REST API accepts.
URL_KINDS = ("design", "file", "proto", "board", "slides", "make")

# 1:2, I1:2;3:4 (instance sublayer path). URL form uses '-' instead of ':'.
_NODE_ID_RE = re.compile(r"^I?\d+:\d+(?:;\d+:\d+)*$")
_FILE_KEY_RE = re.compile(r"^[A-Za-z0-9]+$")


class FigmaAPIError(Exception):
    """A Figma API call failed; `message` is already user-facing."""

    def __init__(self, status: int | None, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class FigmaRef:
    """A parsed Figma link: the key to call the API with, plus an optional node."""

    file_key: str
    node_id: str | None
    branch_of: str | None = None  # main file key when file_key is a branch key


def get_token() -> str:
    """Read FIGMA_ACCESS_TOKEN and install the output redaction guard."""
    token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: FIGMA_ACCESS_TOKEN not set.", file=sys.stderr)
        print("Add to ~/.zshrc:  export FIGMA_ACCESS_TOKEN=your_token", file=sys.stderr)
        print(
            "Get token: https://www.figma.com/settings → Security → "
            "Personal access tokens",
            file=sys.stderr,
        )
        sys.exit(1)
    install_secret_guard(("FIGMA_ACCESS_TOKEN",))
    return token


def normalize_node_id(raw: str) -> str:
    """Normalize a node id from URL or API form to API form ('1-2' → '1:2').

    Raises ValueError when the value is not a node id — e.g. when extra text
    such as a label was glued onto the URL.
    """
    value = unquote(raw).strip()
    node_id = value.replace("-", ":")
    if not _NODE_ID_RE.match(node_id):
        raise ValueError(
            f"Invalid node id {value!r}. Node ids look like '1-2' (URL form), "
            "'1:2', or 'I1:2;3:4'. Pass the URL alone, quoted, with nothing "
            "appended after it."
        )
    return node_id


def parse_figma_ref(url: str) -> FigmaRef:
    """Parse a Figma link into the API file key (branch-aware) and node id.

    Accepts design/file/proto/board/slides/make links. For branch links
    (`/design/<main>/branch/<branch>/...`) the branch key is the API key.
    Raises ValueError on anything that is not a usable Figma link.
    """
    text = url.strip()
    if re.search(r"\s", text):
        raise ValueError(
            f"URL contains whitespace: {text!r}. Pass one URL per argument, "
            "quoted, with nothing appended after it."
        )
    if "://" not in text:
        text = "https://" + text
    parts = urlsplit(text)
    host = (parts.hostname or "").lower()
    if host != "figma.com" and not host.endswith(".figma.com"):
        raise ValueError(f"Not a figma.com URL: {url!r}")

    segments = [s for s in parts.path.split("/") if s]
    if len(segments) < 2 or segments[0] not in URL_KINDS:
        raise ValueError(
            f"Could not find a file key in {url!r}. Expected "
            f"figma.com/<{'|'.join(URL_KINDS)}>/<file-key>/..."
        )
    file_key = segments[1]
    branch_of: str | None = None
    if len(segments) >= 4 and segments[2] == "branch":
        branch_of, file_key = file_key, segments[3]
    for key in (file_key, branch_of):
        if key is not None and not _FILE_KEY_RE.match(key):
            raise ValueError(f"Invalid file key {key!r} in {url!r}")

    node_id = None
    query = parse_qs(parts.query)
    values = query.get("node-id") or query.get("node_id")
    if values:
        node_id = normalize_node_id(values[0])
    return FigmaRef(file_key=file_key, node_id=node_id, branch_of=branch_of)


def parse_figma_url(url: str) -> tuple[str, str | None]:
    """Return (api_file_key, node_id) for a Figma link. Raises ValueError."""
    ref = parse_figma_ref(url)
    return ref.file_key, ref.node_id


def collect_targets(urls: list[str], extra_ids: str | None) -> tuple[str, list[str]]:
    """Resolve URLs plus a comma-separated id list into (file_key, node_ids).

    All URLs must point at the same file (one API call covers one file).
    Node ids are de-duplicated, keeping first-seen order. Raises ValueError.
    """
    if not urls:
        raise ValueError("At least one Figma URL is required.")
    refs = [parse_figma_ref(u) for u in urls]
    keys = {r.file_key for r in refs}
    if len(keys) > 1:
        raise ValueError(
            "All URLs must belong to the same Figma file (or branch); got keys: "
            + ", ".join(sorted(keys))
            + ". Run once per file."
        )
    node_ids: list[str] = []
    for ref in refs:
        if ref.node_id and ref.node_id not in node_ids:
            node_ids.append(ref.node_id)
    for raw in (extra_ids or "").split(","):
        if raw.strip():
            nid = normalize_node_id(raw)
            if nid not in node_ids:
                node_ids.append(nid)
    return refs[0].file_key, node_ids


def build_query(params: dict[str, object]) -> str:
    """Encode query params, dropping None and rendering bools as 'true'/'false'."""
    clean: dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            clean[key] = "true" if value else "false"
        else:
            clean[key] = str(value)
    return urlencode(clean, safe=":,;")


def rate_limit_message(headers: dict[str, str], path: str) -> str:
    """Build the actionable diagnostic for a 429 (header names case-insensitive)."""
    h = {k.lower(): v for k, v in headers.items()}
    retry_after = h.get("retry-after", "")
    plan_tier = h.get("x-figma-plan-tier", "unknown")
    limit_type = h.get("x-figma-rate-limit-type", "unknown")
    upgrade_link = h.get("x-figma-upgrade-link", "")

    lines = [
        f"Figma API 429 Rate Limited for {path}",
        f"  Plan tier   : {plan_tier}",
        f"  Limit type  : {limit_type}",
    ]
    if retry_after:
        lines.append(f"  Retry after : {retry_after}s")
    lines.append("")
    if limit_type == "low":
        lines += [
            "  Your Figma seat is View or Collab. Tier 1 endpoints (GET /files,",
            "  /files/nodes, /images) are limited to 6 requests PER MONTH for",
            "  View/Collab seats (since Nov 2025). This is NOT a per-minute limit.",
            "",
            "  FIX: Upgrade to a Dev or Full seat to get 10–20 requests/minute.",
        ]
    else:
        lines.append("  You have a Dev/Full seat but exceeded per-minute limits.")
        if retry_after:
            lines.append(f"  Wait {retry_after} seconds before retrying.")
    if upgrade_link:
        lines.append(f"  Upgrade/settings: {upgrade_link}")
    return "\n".join(lines)


def figma_get(path: str, token: str, params: dict[str, object] | None = None) -> dict:
    """GET an API path and return parsed JSON. Raises FigmaAPIError."""
    guard_args(path=path)
    url = f"{API_BASE}{path}"
    query = build_query(params or {})
    if query:
        url += "?" + query
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise FigmaAPIError(429, rate_limit_message(dict(e.headers.items()), path))
        body = e.read().decode(errors="replace")
        raise FigmaAPIError(e.code, f"Figma API {e.code} for {path}: {body}")
    except urllib.error.URLError as e:
        raise FigmaAPIError(None, f"Network error: {e.reason}")


def skill_cache_dir(skill: str = "figma") -> Path:
    """Return the unified per-user cache directory for this skill (not created)."""
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        root = home / "Library" / "Caches" / "mythril-skills-cache"
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA")
        root = (Path(local) if local else home / "AppData" / "Local") / "mythril-skills-cache"
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        root = (Path(xdg) if xdg else home / ".cache") / "mythril-skills-cache"
    return root / skill


def new_cache_run_dir() -> Path:
    """Create and return a fresh random directory under the figma cache dir."""
    cache = skill_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(dir=cache))


def fail(message: str, code: int = 1) -> None:
    """Print an ERROR line to stderr and exit with `code`."""
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)
