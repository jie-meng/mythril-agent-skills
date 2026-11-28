#!/usr/bin/env python3
"""Jira REST API client for common developer workflows.

Required environment variables:
  ATLASSIAN_API_TOKEN  — Atlassian API token
  ATLASSIAN_USER_EMAIL — Atlassian account email (Basic auth)

Optional (one of):
  JIRA_BASE_URL        — e.g. https://yoursite.atlassian.net (takes precedence)
  ATLASSIAN_BASE_URL   — e.g. https://yoursite.atlassian.net (shared fallback)
                         Not needed when passing a full Jira URL to issue commands.

Uses only Python 3.10+ standard library (zero dependencies).
"""

import os, sys, json, re, argparse, base64, ssl, platform, tempfile
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from secret_guard import guard_args, install as install_secret_guard  # noqa: E402


def _create_ssl_context() -> ssl.SSLContext | None:
    """Build an SSL context respecting enterprise network configuration.

    Checks these environment variables (in precedence order):
      SSL_NO_VERIFY=1          — disable certificate verification entirely
      SSL_CERT_FILE=<path>     — custom CA bundle path
      CURL_CA_BUNDLE=<path>    — same as SSL_CERT_FILE (curl convention)
      REQUESTS_CA_BUNDLE=<path> — same as SSL_CERT_FILE (requests convention)

    Returns None to use the default OS trust store.
    """
    if os.environ.get("SSL_NO_VERIFY", "").strip() == "1":
        return ssl._create_unverified_context()
    cert_file = (
        os.environ.get("SSL_CERT_FILE", "")
        or os.environ.get("CURL_CA_BUNDLE", "")
        or os.environ.get("REQUESTS_CA_BUNDLE", "")
    ).strip()
    if cert_file:
        return ssl.create_default_context(cafile=cert_file)
    return None


def get_token() -> str:
    """Return ATLASSIAN_API_TOKEN from environment."""
    token = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
    if not token:
        print("ERROR: ATLASSIAN_API_TOKEN not set.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Add to your shell config (~/.zshrc, ~/.bashrc, etc.):", file=sys.stderr)
        print('  export ATLASSIAN_API_TOKEN="your-api-token"', file=sys.stderr)
        print('  export ATLASSIAN_USER_EMAIL="you@example.com"', file=sys.stderr)
        print("", file=sys.stderr)
        print("Get token: https://id.atlassian.com/manage-profile/security/api-tokens", file=sys.stderr)
        sys.exit(1)
    install_secret_guard(("ATLASSIAN_API_TOKEN",), ("ATLASSIAN_USER_EMAIL",))
    return token


def get_email() -> str:
    """Return ATLASSIAN_USER_EMAIL from environment (required for Basic auth)."""
    email = os.environ.get("ATLASSIAN_USER_EMAIL", "").strip()
    if not email:
        print("ERROR: ATLASSIAN_USER_EMAIL not set.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Jira Cloud uses Basic auth with your Atlassian account email:", file=sys.stderr)
        print('  export ATLASSIAN_USER_EMAIL="you@example.com"', file=sys.stderr)
        sys.exit(1)
    return email


def configured_base_url() -> str | None:
    """Return the configured base URL (JIRA_BASE_URL > ATLASSIAN_BASE_URL)."""
    base_url = (
        os.environ.get("JIRA_BASE_URL")
        or os.environ.get("ATLASSIAN_BASE_URL")
        or ""
    ).strip().rstrip("/")
    return base_url or None


def get_base_url() -> str:
    """Return base URL from environment. Checks JIRA_BASE_URL first,
    falls back to ATLASSIAN_BASE_URL. Exits if neither is set."""
    base_url = configured_base_url()
    if base_url:
        return base_url

    print("ERROR: Neither JIRA_BASE_URL nor ATLASSIAN_BASE_URL is set, and no Jira URL provided.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Set one of:", file=sys.stderr)
    print('  export JIRA_BASE_URL="https://yoursite.atlassian.net"', file=sys.stderr)
    print('  export ATLASSIAN_BASE_URL="https://yoursite.atlassian.net"', file=sys.stderr)
    print("", file=sys.stderr)
    print("Or pass a full Jira URL instead of an issue key:", file=sys.stderr)
    print("  python3 jira_api.py view https://yoursite.atlassian.net/browse/PROJ-123", file=sys.stderr)
    sys.exit(1)


ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")


def issue_key_from_url(url: str) -> str | None:
    """Extract the issue key from any Jira Cloud issue URL, or None.

    Handles ``/browse/KEY``, ``.../issues/KEY``, service-desk queue URLs and
    board/backlog URLs with ``?selectedIssue=KEY``.
    """
    parsed = urlparse(url)
    selected = parse_qs(parsed.query).get("selectedIssue")
    if selected and ISSUE_KEY_RE.match(selected[0]):
        return selected[0]
    keys = [seg for seg in parsed.path.split("/") if ISSUE_KEY_RE.match(seg)]
    return keys[-1] if keys else None


def _is_atlassian_cloud(host: str) -> bool:
    """True for an Atlassian Cloud site host (``<site>.atlassian.net``)."""
    return host.endswith(".atlassian.net")


def resolve_url_base(url: str, configured_base: str | None) -> str:
    """Return the API base URL for a pasted URL, refusing untrusted hosts.

    The credential is only ever sent to the configured base URL's host, or to
    an Atlassian Cloud site (``*.atlassian.net``, base = scheme + host) when no
    base URL is configured or the configured one is itself an atlassian.net
    site. Plain http is refused unless it is exactly the configured base URL's
    scheme and host. Raises ValueError (message never contains a credential).
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(f"Could not find a host in URL: {url}")
    cfg = urlparse(configured_base) if configured_base else None
    cfg_host = (cfg.hostname or "").lower() if cfg else ""
    if parsed.scheme != "https" and not (
        cfg and parsed.scheme == "http" and cfg.scheme == "http" and host == cfg_host
    ):
        raise ValueError(
            f"Refusing non-https URL {url!r}: the API token would travel in clear text."
        )
    if cfg and host == cfg_host:
        return configured_base.rstrip("/")
    if _is_atlassian_cloud(host) and (not cfg or _is_atlassian_cloud(cfg_host)):
        port = f":{parsed.port}" if parsed.port else ""
        return f"https://{host}{port}"
    raise ValueError(
        f"Refusing to send credentials to {host!r}: it does not match the "
        "configured JIRA_BASE_URL / ATLASSIAN_BASE_URL host. If this is your "
        "Jira site, set JIRA_BASE_URL to it."
    )


def parse_issue_input(input_str: str) -> tuple[str, str]:
    """Parse an issue key or full Jira URL. Returns (base_url, issue_key).

    Accepts:
      PROJ-123                                                    → (from env, PROJ-123)
      https://site.atlassian.net/browse/PROJ-123                  → (https://site.atlassian.net, PROJ-123)
      https://site.atlassian.net/jira/software/c/projects/PROJ/issues/PROJ-123
      https://site.atlassian.net/jira/software/projects/PROJ/boards/1?selectedIssue=PROJ-123
    """
    if input_str.startswith("http://") or input_str.startswith("https://"):
        issue_key = issue_key_from_url(input_str)
        if not issue_key:
            print(f"ERROR: Could not parse issue key from URL: {input_str}", file=sys.stderr)
            sys.exit(2)
        try:
            base_url = resolve_url_base(input_str, configured_base_url())
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(2)
        return base_url, issue_key

    return get_base_url(), input_str


def _auth_header(token: str) -> str:
    """Build the Basic auth header used by the Jira Cloud REST API."""
    cred = base64.b64encode(f"{get_email()}:{token}".encode()).decode()
    return f"Basic {cred}"


def jira_request(
    method: str,
    path: str,
    base_url: str,
    token: str,
    data: dict | None = None,
    params: dict | None = None,
) -> dict | list | None:
    """Make an authenticated request to the Jira REST API."""
    guard_args(method=method, path=path, base_url=base_url)
    url = f"{base_url}/rest/api/3{path}"
    if params:
        url += "?" + urlencode(params)

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", _auth_header(token))
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")

    try:
        ctx = _create_ssl_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            raw = resp.read()
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"ERROR: Jira API {e.code} {method} {path}: {body_text}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _agile_request(
    base_url: str,
    path: str,
    token: str,
    params: dict | None = None,
) -> dict:
    """Make an authenticated request to the Jira Agile REST API."""
    guard_args(base_url=base_url, path=path)
    url = f"{base_url}/rest/agile/1.0{path}"
    if params:
        url += "?" + urlencode(params)

    req = urllib.request.Request(url)
    req.add_header("Authorization", _auth_header(token))
    req.add_header("Accept", "application/json")
    try:
        ctx = _create_ssl_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"ERROR: Jira Agile API {e.code}: {body_text}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def download_binary(url: str, token: str) -> bytes:
    """GET a file (e.g. an attachment) with auth and return its bytes.

    The Authorization header is not forwarded on redirects.
    """
    guard_args(url=url)
    req = urllib.request.Request(url)
    req.add_unredirected_header("Authorization", _auth_header(token))
    try:
        ctx = _create_ssl_context()
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        print(f"ERROR: download failed with HTTP {e.code}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Pure helpers: cache dir, attachments
# ---------------------------------------------------------------------------

def skill_cache_dir(skill: str = "jira") -> Path:
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


def safe_attachment_name(name: str) -> str:
    """Reduce an attachment file name to a safe file name (no directories)."""
    name = re.split(r"[\\/]", name.strip())[-1]
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name).strip()
    if name in ("", ".", ".."):
        return "attachment"
    return name


def select_attachments(attachments: list[dict], names: list[str]) -> tuple[list[dict], list[str]]:
    """Pick attachments by filename; with no names, pick every image attachment.

    Returns (selected, missing_names). Matching is exact first, then
    case-insensitive.
    """
    if not names:
        picked = [a for a in attachments if str(a.get("mimeType", "")).startswith("image/")]
        return picked, []
    selected: list[dict] = []
    missing: list[str] = []
    for name in names:
        match = next((a for a in attachments if a.get("filename") == name), None)
        if match is None:
            lowered = name.lower()
            match = next(
                (a for a in attachments if str(a.get("filename", "")).lower() == lowered), None
            )
        if match is None:
            missing.append(name)
        elif match not in selected:
            selected.append(match)
    return selected, missing


def attachment_content_url(base_url: str, attachment_id: str) -> str:
    """Build the content URL for an attachment id on ``base_url``.

    The URL is built from the id (never taken from the API response), so the
    credential can only go to ``base_url``. Raises ValueError on a bad id.
    """
    if not re.fullmatch(r"\d+", str(attachment_id)):
        raise ValueError(f"invalid attachment id: {attachment_id!r}")
    return f"{base_url}/rest/api/3/attachment/content/{attachment_id}?redirect=false"


def format_attachments_markdown(attachments: list[dict]) -> str:
    """Render an issue's attachment list as markdown bullets."""
    lines = []
    for a in attachments:
        lines.append(
            f"- {a.get('filename', '')} ({a.get('mimeType', '')}, "
            f"{a.get('size', '?')} bytes, id: {a.get('id', '')})"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown → ADF (minimal: paragraphs, headings, lists, code, quotes, links)
# ---------------------------------------------------------------------------

_MD_INLINE_RE = re.compile(
    r"(?P<code>`[^`\n]+`)"
    r"|(?P<link>\[(?P<ltext>[^\]\n]+)\]\((?P<lhref>[^)\s]+)\))"
    r"|(?P<strong>\*\*(?P<stext>[^*\n]+)\*\*|__(?P<stext2>[^_\n]+)__)"
    r"|(?P<em>(?<![\w*])\*(?P<etext>[^*\s][^*\n]*)\*(?![\w*])"
    r"|(?<![\w_])_(?P<etext2>[^_\s][^_\n]*)_(?![\w_]))"
    r"|(?P<url>https?://[^\s<>()\[\]]*[^\s<>()\[\].,;:!?'\"])"
)
_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
_MD_FENCE_RE = re.compile(r"^\s*(```|~~~)\s*([\w+#.-]*)\s*$")
_MD_LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
_MD_QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_MD_RULE_RE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")


def _md_inline(text: str) -> list[dict]:
    """Convert one line of inline markdown into ADF text nodes."""
    nodes: list[dict] = []

    def add(value: str, marks: list[dict] | None = None) -> None:
        if not value:
            return
        node: dict = {"type": "text", "text": value}
        if marks:
            node["marks"] = marks
        nodes.append(node)

    pos = 0
    for m in _MD_INLINE_RE.finditer(text):
        add(text[pos:m.start()])
        if m.group("code"):
            add(m.group("code")[1:-1], [{"type": "code"}])
        elif m.group("link"):
            add(m.group("ltext"), [{"type": "link", "attrs": {"href": m.group("lhref")}}])
        elif m.group("strong"):
            add(m.group("stext") or m.group("stext2"), [{"type": "strong"}])
        elif m.group("em"):
            add(m.group("etext") or m.group("etext2"), [{"type": "em"}])
        else:
            url = m.group("url")
            add(url, [{"type": "link", "attrs": {"href": url}}])
        pos = m.end()
    add(text[pos:])
    return nodes


def _md_paragraph(lines: list[str]) -> dict:
    content: list[dict] = []
    for i, line in enumerate(lines):
        if i:
            content.append({"type": "hardBreak"})
        content.extend(_md_inline(line))
    return {"type": "paragraph", "content": content}


def _indent(prefix: str) -> int:
    return len(prefix.expandtabs(4))


def _md_list(lines: list[str], i: int) -> tuple[dict, int]:
    """Parse a (possibly nested) list starting at line ``i``."""
    first = _MD_LIST_RE.match(lines[i])
    base = _indent(first.group(1))
    ordered = first.group(2)[0].isdigit()
    node: dict = {"type": "orderedList" if ordered else "bulletList", "content": []}
    if ordered:
        start = int(re.match(r"\d+", first.group(2)).group())
        if start != 1:
            node["attrs"] = {"order": start}
    while i < len(lines):
        line = lines[i]
        m = _MD_LIST_RE.match(line)
        if m is None or _MD_RULE_RE.match(line):
            if not line.strip():
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                nxt = _MD_LIST_RE.match(lines[j]) if j < len(lines) else None
                if nxt and _indent(nxt.group(1)) >= base:
                    i = j
                    continue
                break
            if _indent(line[: len(line) - len(line.lstrip())]) > base and node["content"]:
                para = node["content"][-1]["content"][0]
                para["content"].append({"type": "hardBreak"})
                para["content"].extend(_md_inline(line.strip()))
                i += 1
                continue
            break
        level = _indent(m.group(1))
        if level < base:
            break
        if level > base:
            child, i = _md_list(lines, i)
            node["content"][-1]["content"].append(child)
            continue
        if m.group(2)[0].isdigit() != ordered:
            break
        node["content"].append({"type": "listItem", "content": [_md_paragraph([m.group(3)])]})
        i += 1
    return node, i


def _md_blocks(lines: list[str]) -> list[dict]:
    out: list[dict] = []
    para: list[str] = []

    def flush() -> None:
        if para:
            out.append(_md_paragraph(para))
            para.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        fence = _MD_FENCE_RE.match(line)
        if fence:
            flush()
            marker, lang = fence.group(1), fence.group(2)
            body: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(marker):
                body.append(lines[i])
                i += 1
            i += 1
            code: dict = {"type": "codeBlock", "content": []}
            if body:
                code["content"] = [{"type": "text", "text": "\n".join(body)}]
            if lang:
                code["attrs"] = {"language": lang}
            out.append(code)
            continue
        if not line.strip():
            flush()
            i += 1
            continue
        heading = _MD_HEADING_RE.match(line)
        if heading:
            flush()
            out.append({
                "type": "heading",
                "attrs": {"level": len(heading.group(1))},
                "content": _md_inline(heading.group(2)),
            })
            i += 1
            continue
        if _MD_RULE_RE.match(line):
            flush()
            out.append({"type": "rule"})
            i += 1
            continue
        if _MD_QUOTE_RE.match(line):
            flush()
            quoted: list[str] = []
            while i < len(lines) and _MD_QUOTE_RE.match(lines[i]):
                quoted.append(_MD_QUOTE_RE.match(lines[i]).group(1))
                i += 1
            inner = []
            for block in _md_blocks(quoted):
                if block["type"] == "heading":
                    block = {"type": "paragraph", "content": block["content"]}
                if block["type"] != "rule":
                    inner.append(block)
            out.append({"type": "blockquote", "content": inner or [{"type": "paragraph", "content": []}]})
            continue
        if _MD_LIST_RE.match(line):
            flush()
            node, i = _md_list(lines, i)
            out.append(node)
            continue
        para.append(line.strip())
        i += 1
    flush()
    return out


def markdown_to_adf(text: str) -> dict:
    """Convert simple markdown into an ADF document.

    Supports paragraphs (single newlines become hard breaks), ATX headings,
    bullet/ordered lists with nesting, fenced code blocks, blockquotes,
    horizontal rules, and inline code, links, bare URLs, bold and italic.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    content = _md_blocks(lines) or [{"type": "paragraph", "content": []}]
    return {"version": 1, "type": "doc", "content": content}


# ---------------------------------------------------------------------------
# Formatters — convert API responses to readable markdown
# ---------------------------------------------------------------------------

def _apply_marks(text: str, marks: list[dict]) -> str:
    """Render ADF text marks (link, code, strong, em, strike) as markdown."""
    href = None
    for mark in marks or []:
        mtype = mark.get("type")
        if mtype == "code":
            text = f"`{text}`"
        elif mtype == "strong":
            text = f"**{text}**"
        elif mtype == "em":
            text = f"*{text}*"
        elif mtype == "strike":
            text = f"~~{text}~~"
        elif mtype == "link":
            href = (mark.get("attrs") or {}).get("href")
    if href and href != text:
        return f"[{text}]({href})"
    return text


def _media_text(node: dict) -> str:
    attrs = node.get("attrs") or {}
    alt = attrs.get("alt")
    if alt:
        return f"![{alt}](attachment:{alt})"
    if attrs.get("type") == "external" and attrs.get("url"):
        return f"![]({attrs['url']})"
    return f"[media: {attrs.get('id', '')}]"

def format_adf_to_text(node: dict | list | str | None, depth: int = 0) -> str:
    """Best-effort conversion of Atlassian Document Format to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(format_adf_to_text(n, depth) for n in node)
    if not isinstance(node, dict):
        return str(node)

    ntype = node.get("type", "")
    content = node.get("content", [])
    text = node.get("text", "")

    if ntype == "text":
        return _apply_marks(text, node.get("marks") or [])
    if ntype in ("inlineCard", "blockCard", "embedCard"):
        url = (node.get("attrs") or {}).get("url", "")
        return url if ntype == "inlineCard" else url + "\n"
    if ntype == "emoji":
        attrs = node.get("attrs") or {}
        return attrs.get("text") or attrs.get("shortName", "")
    if ntype == "status":
        return f"[{(node.get('attrs') or {}).get('text', '')}]"
    if ntype == "date":
        ts = (node.get("attrs") or {}).get("timestamp", "")
        try:
            return datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            return str(ts)
    if ntype == "rule":
        return "---\n"
    if ntype == "hardBreak":
        return "\n"
    if ntype == "paragraph":
        inner = "".join(format_adf_to_text(c, depth) for c in content)
        return inner + "\n"
    if ntype == "heading":
        level = node.get("attrs", {}).get("level", 1)
        inner = "".join(format_adf_to_text(c, depth) for c in content)
        return "#" * level + " " + inner + "\n"
    if ntype == "bulletList":
        items = []
        for item in content:
            item_text = format_adf_to_text(item, depth + 1).strip()
            items.append("  " * depth + "- " + item_text)
        return "\n".join(items) + "\n"
    if ntype == "orderedList":
        items = []
        for i, item in enumerate(content, 1):
            item_text = format_adf_to_text(item, depth + 1).strip()
            items.append("  " * depth + f"{i}. " + item_text)
        return "\n".join(items) + "\n"
    if ntype == "listItem":
        return "".join(format_adf_to_text(c, depth) for c in content)
    if ntype == "codeBlock":
        lang = node.get("attrs", {}).get("language", "")
        inner = "".join(format_adf_to_text(c, depth) for c in content)
        if inner and not inner.endswith("\n"):
            inner += "\n"
        return f"```{lang}\n{inner}```\n"
    if ntype == "blockquote":
        inner = "".join(format_adf_to_text(c, depth) for c in content)
        return "> " + inner.replace("\n", "\n> ") + "\n"
    if ntype == "table":
        rows = []
        for row in content:
            cells = []
            for cell in row.get("content", []):
                cells.append(format_adf_to_text(cell, depth).strip())
            rows.append(" | ".join(cells))
        return "\n".join(rows) + "\n"
    if ntype in ("mediaGroup", "mediaSingle"):
        media = [_media_text(c) for c in content if c.get("type") == "media"]
        return "\n".join(media) + "\n" if media else ""
    if ntype == "mediaInline":
        return _media_text(node)
    if ntype == "mention":
        return "@" + node.get("attrs", {}).get("text", "someone")

    inner = "".join(format_adf_to_text(c, depth) for c in content)
    return inner


def format_issue_markdown(issue: dict) -> str:
    """Convert a Jira issue JSON to readable markdown."""
    fields = issue.get("fields", {})
    key = issue.get("key", "")
    lines = [f"## {key}: {fields.get('summary', '(no summary)')}"]
    lines.append("")

    status = fields.get("status", {})
    priority = fields.get("priority", {})
    issuetype = fields.get("issuetype", {})
    assignee = fields.get("assignee") or {}
    reporter = fields.get("reporter") or {}
    labels = fields.get("labels", [])
    components = [c.get("name", "") for c in fields.get("components", [])]
    fix_versions = [v.get("name", "") for v in fields.get("fixVersions", [])]
    created = fields.get("created", "")
    updated = fields.get("updated", "")
    parent = fields.get("parent")
    resolution = fields.get("resolution")

    lines.append(f"- **Status**: {status.get('name', '')}")
    lines.append(f"- **Type**: {issuetype.get('name', '')}")
    lines.append(f"- **Priority**: {priority.get('name', '')}")
    lines.append(f"- **Assignee**: {assignee.get('displayName', 'Unassigned')}")
    lines.append(f"- **Reporter**: {reporter.get('displayName', '')}")
    if labels:
        lines.append(f"- **Labels**: {', '.join(labels)}")
    if components:
        lines.append(f"- **Components**: {', '.join(components)}")
    if fix_versions:
        lines.append(f"- **Fix Versions**: {', '.join(fix_versions)}")
    if parent:
        lines.append(f"- **Parent**: {parent.get('key', '')} — {parent.get('fields', {}).get('summary', '')}")
    if resolution:
        lines.append(f"- **Resolution**: {resolution.get('name', '')}")
    lines.append(f"- **Created**: {created}")
    lines.append(f"- **Updated**: {updated}")

    url = issue.get("self", "")
    if url:
        base = url.split("/rest/")[0]
        lines.append(f"- **URL**: {base}/browse/{key}")

    description = fields.get("description")
    if description:
        lines.append("")
        lines.append("### Description")
        lines.append("")
        lines.append(format_adf_to_text(description).strip())

    subtasks = fields.get("subtasks", [])
    if subtasks:
        lines.append("")
        lines.append("### Subtasks")
        for st in subtasks:
            st_status = st.get("fields", {}).get("status", {}).get("name", "")
            lines.append(f"- {st.get('key', '')}: {st.get('fields', {}).get('summary', '')} [{st_status}]")

    issuelinks = fields.get("issuelinks", [])
    if issuelinks:
        lines.append("")
        lines.append("### Linked Issues")
        for link in issuelinks:
            link_type = link.get("type", {}).get("outward", "")
            target = link.get("outwardIssue") or link.get("inwardIssue") or {}
            if link.get("inwardIssue"):
                link_type = link.get("type", {}).get("inward", "")
            t_key = target.get("key", "")
            t_summary = target.get("fields", {}).get("summary", "")
            lines.append(f"- {link_type} {t_key}: {t_summary}")

    attachments = fields.get("attachment") or []
    if attachments:
        lines.append("")
        lines.append("### Attachments")
        lines.append(format_attachments_markdown(attachments))

    return "\n".join(lines)


def format_search_results_markdown(data: dict) -> str:
    """Format JQL search results as a markdown table."""
    issues = data.get("issues", [])
    total = data.get("total")
    next_page_token = data.get("nextPageToken")

    noun = "issue" if len(issues) == 1 else "issues"
    if total is None:
        lines = [f"## Search Results ({len(issues)} {noun})"]
    else:
        lines = [f"## Search Results ({len(issues)} of {total} {noun})"]
    lines.append("")

    if not issues:
        lines.append("No issues found.")
        return "\n".join(lines)

    lines.append("| Key | Type | Priority | Status | Assignee | Summary |")
    lines.append("|-----|------|----------|--------|----------|---------|")

    for issue in issues:
        f = issue.get("fields", {})
        key = issue.get("key", "")
        itype = f.get("issuetype", {}).get("name", "")
        priority = f.get("priority", {}).get("name", "")
        status = f.get("status", {}).get("name", "")
        assignee = (f.get("assignee") or {}).get("displayName", "Unassigned")
        summary = f.get("summary", "")
        if len(summary) > 60:
            summary = summary[:57] + "..."
        lines.append(f"| {key} | {itype} | {priority} | {status} | {assignee} | {summary} |")

    if next_page_token:
        lines.append("")
        lines.append(f"**Next Page Token**: `{next_page_token}` (use `--next-page-token {next_page_token}` for next page)")

    return "\n".join(lines)


def format_components_markdown(data: list[dict], project_key: str) -> str:
    """Format project components as markdown table."""
    lines = [f"## Components for project {project_key} ({len(data)})"]
    lines.append("")

    if not data:
        lines.append("No components found.")
        return "\n".join(lines)

    lines.append("| ID | Name | Description | Lead |")
    lines.append("|----|------|-------------|------|")

    for c in data:
        cid = c.get("id", "")
        name = c.get("name", "")
        desc = c.get("description", "-")
        if len(desc) > 50:
            desc = desc[:47] + "..."
        lead = (c.get("lead") or {}).get("displayName", "-")
        lines.append(f"| {cid} | {name} | {desc} | {lead} |")

    return "\n".join(lines)


def format_transitions_markdown(data: dict, issue_key: str) -> str:
    """Format available transitions as a markdown list."""
    transitions = data.get("transitions", [])
    lines = [f"## Available Transitions for {issue_key}"]
    lines.append("")
    if not transitions:
        lines.append("No transitions available.")
        return "\n".join(lines)
    lines.append("| ID | Name | To Status |")
    lines.append("|----|------|-----------|")
    for t in transitions:
        to_status = t.get("to", {}).get("name", "")
        lines.append(f"| {t.get('id', '')} | {t.get('name', '')} | {to_status} |")
    return "\n".join(lines)


def format_comments_markdown(data: dict, issue_key: str) -> str:
    """Format issue comments as markdown."""
    comments = data.get("comments", [])
    total = data.get("total", len(comments))
    lines = [f"## Comments on {issue_key} ({len(comments)} of {total})"]
    lines.append("")
    if not comments:
        lines.append("No comments.")
        return "\n".join(lines)
    for c in comments:
        author = c.get("author", {}).get("displayName", "")
        created = c.get("created", "")
        body = format_adf_to_text(c.get("body")).strip()
        lines.append(f"### {author} — {created}")
        lines.append("")
        lines.append(body)
        lines.append("")
    return "\n".join(lines)


def format_sprint_markdown(data: dict) -> str:
    """Format Jira Agile sprint data as markdown."""
    values = data.get("values", [])
    lines = ["## Sprints"]
    lines.append("")
    if not values:
        lines.append("No sprints found.")
        return "\n".join(lines)
    lines.append("| ID | Name | State | Start | End |")
    lines.append("|----|------|-------|-------|-----|")
    for s in values:
        lines.append(
            f"| {s.get('id', '')} | {s.get('name', '')} | {s.get('state', '')} "
            f"| {s.get('startDate', '-')} | {s.get('endDate', '-')} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_view(args: argparse.Namespace) -> None:
    """View a single issue."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    fields_param = (
        "summary,status,issuetype,priority,assignee,reporter,labels,components,"
        "fixVersions,description,created,updated,parent,subtasks,issuelinks,resolution,"
        "attachment"
    )
    data = jira_request("GET", f"/issue/{issue_key}", base_url, token,
                        params={"fields": fields_param})
    print(format_issue_markdown(data))


def cmd_search(args: argparse.Namespace) -> None:
    """Search issues via JQL."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str | int] = {
        "jql": args.jql,
        "maxResults": args.max_results,
        "fields": "summary,status,issuetype,priority,assignee",
    }
    if args.next_page_token:
        params["nextPageToken"] = args.next_page_token
    data = jira_request("GET", "/search/jql", base_url, token, params=params)
    print(format_search_results_markdown(data))


def cmd_components(args: argparse.Namespace) -> None:
    """List components in a project."""
    token = get_token()
    base_url = get_base_url()
    data = jira_request("GET", f"/project/{args.project}/components", base_url, token)
    print(format_components_markdown(data, args.project))



def cmd_create(args: argparse.Namespace) -> None:
    """Create a new issue."""
    token = get_token()
    base_url = get_base_url()
    fields: dict = {
        "project": {"key": args.project},
        "summary": args.summary,
        "issuetype": {"name": args.type},
    }
    if args.description:
        fields["description"] = markdown_to_adf(args.description)
    if args.priority:
        fields["priority"] = {"name": args.priority}
    if args.assignee:
        fields["assignee"] = {"accountId": args.assignee}
    if args.labels:
        fields["labels"] = args.labels
    if args.parent:
        fields["parent"] = {"key": args.parent}
    if args.components:
        fields["components"] = [{"name": c} for c in args.components]

    data = jira_request("POST", "/issue", base_url, token, data={"fields": fields})
    key = data.get("key", "")
    print(f"Created {key}: {base_url}/browse/{key}")


def cmd_edit(args: argparse.Namespace) -> None:
    """Edit an existing issue."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    fields: dict = {}
    if args.summary:
        fields["summary"] = args.summary
    if args.description:
        fields["description"] = markdown_to_adf(args.description)
    if args.priority:
        fields["priority"] = {"name": args.priority}
    if args.assignee:
        fields["assignee"] = {"accountId": args.assignee}
    if args.labels is not None:
        fields["labels"] = args.labels

    if not fields:
        print("ERROR: No fields to update. Provide at least one of --summary, --description, --priority, --assignee, --labels.", file=sys.stderr)
        sys.exit(2)

    jira_request("PUT", f"/issue/{issue_key}", base_url, token,
                 data={"fields": fields})
    print(f"Updated {issue_key}: {base_url}/browse/{issue_key}")


def cmd_assign(args: argparse.Namespace) -> None:
    """Assign an issue to a user (by accountId) or unassign with 'none'."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    account_id = None if args.account_id == "none" else args.account_id
    jira_request("PUT", f"/issue/{issue_key}/assignee", base_url, token,
                 data={"accountId": account_id})
    if account_id:
        print(f"Assigned {issue_key} to {account_id}")
    else:
        print(f"Unassigned {issue_key}")


def cmd_transitions(args: argparse.Namespace) -> None:
    """List available transitions for an issue."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    data = jira_request("GET", f"/issue/{issue_key}/transitions", base_url, token)
    print(format_transitions_markdown(data, issue_key))


def cmd_transition(args: argparse.Namespace) -> None:
    """Transition (move) an issue to a new status."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    payload: dict = {"transition": {"id": args.transition_id}}
    if args.comment:
        payload["update"] = {
            "comment": [{
                "add": {"body": markdown_to_adf(args.comment)}
            }]
        }
    if args.resolution:
        payload.setdefault("fields", {})["resolution"] = {"name": args.resolution}

    jira_request("POST", f"/issue/{issue_key}/transitions", base_url, token, data=payload)
    print(f"Transitioned {issue_key} (transition id: {args.transition_id})")


def cmd_comment(args: argparse.Namespace) -> None:
    """Add a comment to an issue."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    body = {"body": markdown_to_adf(args.body)}
    data = jira_request("POST", f"/issue/{issue_key}/comment", base_url, token, data=body)
    print(f"Comment added to {issue_key} (id: {data.get('id', '')})")


def cmd_comments(args: argparse.Namespace) -> None:
    """List comments on an issue."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    params = {"maxResults": args.max_results, "orderBy": "-created"}
    data = jira_request("GET", f"/issue/{issue_key}/comment", base_url, token, params=params)
    print(format_comments_markdown(data, issue_key))


def cmd_download_attachment(args: argparse.Namespace) -> None:
    """Download issue attachments (all images by default) into the cache dir."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    data = jira_request("GET", f"/issue/{issue_key}", base_url, token,
                        params={"fields": "attachment"})
    attachments = (data.get("fields") or {}).get("attachment") or []
    selected, missing = select_attachments(attachments, args.names)
    for name in missing:
        print(f"ERROR: no attachment named {name!r} on {issue_key}", file=sys.stderr)
    if not selected:
        if not missing:
            print(f"No image attachments on {issue_key}.", file=sys.stderr)
        sys.exit(1)

    if args.out_dir:
        out_dir = Path(args.out_dir).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        cache = skill_cache_dir()
        cache.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(dir=cache))

    used: set[str] = set()
    failed = len(missing)
    for att in selected:
        try:
            url = attachment_content_url(base_url, att.get("id", ""))
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            failed += 1
            continue
        name = safe_attachment_name(str(att.get("filename", "")))
        if name in used:
            name = f"{att.get('id')}_{name}"
        used.add(name)
        dest = out_dir / name
        dest.write_bytes(download_binary(url, token))
        print(dest)
    if failed:
        sys.exit(1)


def cmd_myself(args: argparse.Namespace) -> None:
    """Print the authenticated user's info."""
    token = get_token()
    base_url = get_base_url()
    data = jira_request("GET", "/myself", base_url, token)
    print(f"Account ID: {data.get('accountId', '')}")
    print(f"Display Name: {data.get('displayName', '')}")
    print(f"Email: {data.get('emailAddress', '')}")
    print(f"Active: {data.get('active', '')}")


def cmd_link(args: argparse.Namespace) -> None:
    """Link two issues together."""
    token = get_token()
    base_url = get_base_url()
    body = {
        "type": {"name": args.link_type},
        "inwardIssue": {"key": args.inward_key},
        "outwardIssue": {"key": args.outward_key},
    }
    jira_request("POST", "/issueLink", base_url, token, data=body)
    print(f"Linked {args.outward_key} —[{args.link_type}]→ {args.inward_key}")


def cmd_sprints(args: argparse.Namespace) -> None:
    """List sprints for a board (uses Jira Agile REST API)."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str] = {}
    if args.state:
        params["state"] = args.state
    data = _agile_request(base_url, f"/board/{args.board_id}/sprint", token, params=params or None)
    print(format_sprint_markdown(data))


def cmd_sprint_issues(args: argparse.Namespace) -> None:
    """List issues in a sprint (uses Jira Agile REST API)."""
    token = get_token()
    base_url = get_base_url()
    params = {"maxResults": str(args.max_results), "fields": "summary,status,issuetype,priority,assignee"}
    data = _agile_request(base_url, f"/sprint/{args.sprint_id}/issue", token, params=params)
    print(format_search_results_markdown(data))


def cmd_boards(args: argparse.Namespace) -> None:
    """List boards (uses Jira Agile REST API)."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str] = {"maxResults": str(args.max_results)}
    if args.project:
        params["projectKeyOrId"] = args.project
    data = _agile_request(base_url, "/board", token, params=params)

    values = data.get("values", [])
    lines = ["## Boards"]
    lines.append("")
    if not values:
        lines.append("No boards found.")
    else:
        lines.append("| ID | Name | Type | Project |")
        lines.append("|----|------|------|---------|")
        for b in values:
            loc = b.get("location", {})
            proj = loc.get("projectKey", "") if loc else ""
            lines.append(f"| {b.get('id', '')} | {b.get('name', '')} | {b.get('type', '')} | {proj} |")
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

ISSUE_HELP = "Issue key (e.g. PROJ-123) or full Jira URL"


def main() -> None:
    parser = argparse.ArgumentParser(description="Jira REST API client for developer workflows.")
    sub = parser.add_subparsers(dest="command", required=True)

    # view
    p_view = sub.add_parser("view", help="View a single issue")
    p_view.add_argument("issue", help=ISSUE_HELP)
    p_view.set_defaults(func=cmd_view)

    # search
    p_search = sub.add_parser("search", help="Search issues via JQL")
    p_search.add_argument("jql", help='JQL query string (e.g. "project=PROJ AND status=Open")')
    p_search.add_argument("--max-results", type=int, default=20, help="Max results (default: 20)")
    p_search.add_argument("--next-page-token", help="Pagination token for next page")
    p_search.set_defaults(func=cmd_search)

    # components
    p_comp = sub.add_parser("components", help="List components in a project")
    p_comp.add_argument("project", help="Project key or ID (e.g. PROJ)")
    p_comp.set_defaults(func=cmd_components)

    # create
    p_create = sub.add_parser("create", help="Create a new issue")
    p_create.add_argument("--project", required=True, help="Project key (e.g. PROJ)")
    p_create.add_argument("--summary", required=True, help="Issue summary")
    p_create.add_argument("--type", default="Task", help="Issue type (default: Task)")
    p_create.add_argument("--description", help="Description (markdown, converted to ADF)")
    p_create.add_argument("--priority", help="Priority name (e.g. High)")
    p_create.add_argument("--assignee", help="Assignee account ID")
    p_create.add_argument("--labels", nargs="*", help="Labels")
    p_create.add_argument("--parent", help="Parent issue key (for subtasks/stories under epic)")
    p_create.add_argument("--components", nargs="*", help="Component names")
    p_create.set_defaults(func=cmd_create)

    # edit
    p_edit = sub.add_parser("edit", help="Edit an existing issue")
    p_edit.add_argument("issue", help=ISSUE_HELP)
    p_edit.add_argument("--summary", help="New summary")
    p_edit.add_argument("--description", help="New description (markdown, converted to ADF)")
    p_edit.add_argument("--priority", help="New priority")
    p_edit.add_argument("--assignee", help="New assignee account ID")
    p_edit.add_argument("--labels", nargs="*", help="Replace labels")
    p_edit.set_defaults(func=cmd_edit)

    # assign
    p_assign = sub.add_parser("assign", help="Assign an issue")
    p_assign.add_argument("issue", help=ISSUE_HELP)
    p_assign.add_argument("account_id", help='Assignee account ID or "none" to unassign')
    p_assign.set_defaults(func=cmd_assign)

    # transitions
    p_trans_list = sub.add_parser("transitions", help="List available transitions")
    p_trans_list.add_argument("issue", help=ISSUE_HELP)
    p_trans_list.set_defaults(func=cmd_transitions)

    # transition
    p_trans = sub.add_parser("transition", help="Transition (move) an issue")
    p_trans.add_argument("issue", help=ISSUE_HELP)
    p_trans.add_argument("transition_id", help="Transition ID (from 'transitions' command)")
    p_trans.add_argument("--comment", help="Add a comment during transition")
    p_trans.add_argument("--resolution", help="Set resolution (e.g. Done, Fixed)")
    p_trans.set_defaults(func=cmd_transition)

    # comment
    p_comment = sub.add_parser("comment", help="Add a comment to an issue")
    p_comment.add_argument("issue", help=ISSUE_HELP)
    p_comment.add_argument("body", help="Comment text (markdown, converted to ADF)")
    p_comment.set_defaults(func=cmd_comment)

    # comments
    p_comments = sub.add_parser("comments", help="List comments on an issue")
    p_comments.add_argument("issue", help=ISSUE_HELP)
    p_comments.add_argument("--max-results", type=int, default=10, help="Max results (default: 10)")
    p_comments.set_defaults(func=cmd_comments)

    # download-attachment
    p_dl = sub.add_parser(
        "download-attachment",
        help="Download issue attachments (default: all images) into the skill cache dir",
    )
    p_dl.add_argument("issue", help=ISSUE_HELP)
    p_dl.add_argument("names", nargs="*", help="Attachment file names (default: every image)")
    p_dl.add_argument("--out-dir", help="Destination directory (default: a new dir under the unified cache)")
    p_dl.set_defaults(func=cmd_download_attachment)

    # link
    p_link = sub.add_parser("link", help="Link two issues")
    p_link.add_argument("outward_key", help="Outward issue key")
    p_link.add_argument("inward_key", help="Inward issue key")
    p_link.add_argument("link_type", help='Link type name (e.g. "Blocks", "Relates")')
    p_link.set_defaults(func=cmd_link)

    # myself
    p_me = sub.add_parser("myself", help="Print current user info")
    p_me.set_defaults(func=cmd_myself)

    # boards
    p_boards = sub.add_parser("boards", help="List boards")
    p_boards.add_argument("--project", help="Filter by project key")
    p_boards.add_argument("--max-results", type=int, default=50, help="Max results (default: 50)")
    p_boards.set_defaults(func=cmd_boards)

    # sprints
    p_sprints = sub.add_parser("sprints", help="List sprints for a board")
    p_sprints.add_argument("board_id", help="Board ID")
    p_sprints.add_argument("--state", help='Filter by state: active, closed, future (comma-separated)')
    p_sprints.set_defaults(func=cmd_sprints)

    # sprint-issues
    p_si = sub.add_parser("sprint-issues", help="List issues in a sprint")
    p_si.add_argument("sprint_id", help="Sprint ID")
    p_si.add_argument("--max-results", type=int, default=50, help="Max results (default: 50)")
    p_si.set_defaults(func=cmd_sprint_issues)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
