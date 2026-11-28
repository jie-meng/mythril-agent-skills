#!/usr/bin/env python3
"""Confluence REST API client for common developer workflows.

Required environment variables:
  ATLASSIAN_API_TOKEN  — Atlassian API token
  ATLASSIAN_USER_EMAIL — Atlassian account email (for Cloud basic auth)

Optional (one of):
  CONFLUENCE_BASE_URL  — e.g. https://yoursite.atlassian.net (takes precedence)
  ATLASSIAN_BASE_URL   — e.g. https://yoursite.atlassian.net (shared fallback)
                         Not needed when passing a full Confluence URL to page commands.

Uses only Python 3.10+ standard library (zero dependencies).
"""

import os, sys, json, re, argparse, base64, html, ssl, platform, tempfile
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlencode, urlparse, quote, parse_qs

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


def configured_base_url() -> str | None:
    """Return the configured base URL (CONFLUENCE_BASE_URL > ATLASSIAN_BASE_URL)."""
    base_url = (
        os.environ.get("CONFLUENCE_BASE_URL")
        or os.environ.get("ATLASSIAN_BASE_URL")
        or ""
    ).strip().rstrip("/")
    return base_url or None


def get_base_url() -> str:
    """Return base URL from environment. Checks CONFLUENCE_BASE_URL first,
    falls back to ATLASSIAN_BASE_URL. Exits if neither is set."""
    base_url = configured_base_url()
    if base_url:
        return base_url

    print("ERROR: Neither CONFLUENCE_BASE_URL nor ATLASSIAN_BASE_URL is set, and no Confluence URL provided.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Set one of:", file=sys.stderr)
    print('  export CONFLUENCE_BASE_URL="https://yoursite.atlassian.net"', file=sys.stderr)
    print('  export ATLASSIAN_BASE_URL="https://yoursite.atlassian.net"', file=sys.stderr)
    print("", file=sys.stderr)
    print("Or pass a full Confluence URL instead of a page ID:", file=sys.stderr)
    print("  python3 confluence_api.py view https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345", file=sys.stderr)
    sys.exit(1)


def parse_page_input(input_str: str) -> tuple[str, str]:
    """Parse a page ID or full Confluence URL. Returns (base_url, page_id).

    Accepts:
      12345                                                              → (from env, 12345)
      https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345        → (https://yoursite.atlassian.net, 12345)
      https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345/Title  → (https://yoursite.atlassian.net, 12345)
    """
    if input_str.startswith("http://") or input_str.startswith("https://"):
        m = re.search(r"/pages/(\d+)", urlparse(input_str).path)
        if not m:
            print(f"ERROR: Could not parse page ID from URL: {input_str}", file=sys.stderr)
            sys.exit(2)
        page_id = m.group(1)
        try:
            base_url = resolve_url_base(input_str, configured_base_url())
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(2)
        return base_url, page_id

    return get_base_url(), input_str


def _is_atlassian_cloud(host: str) -> bool:
    """True for an Atlassian Cloud site host (``<site>.atlassian.net``)."""
    return host.endswith(".atlassian.net")


def resolve_url_base(url: str, configured_base: str | None) -> str:
    """Return the API base URL for a pasted URL, refusing untrusted hosts.

    The credential is only ever sent to the configured base URL's host, or to
    an Atlassian Cloud site (``*.atlassian.net``) when no base URL is
    configured or the configured one is itself an atlassian.net site. Plain
    http is refused unless it is exactly the configured base URL's scheme and
    host. Raises ValueError (message never contains a credential).
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
        "configured CONFLUENCE_BASE_URL / ATLASSIAN_BASE_URL host. If this is "
        "your Confluence site, set CONFLUENCE_BASE_URL to it."
    )


def _auth_header(token: str) -> str:
    """Build auth header. Uses Basic auth if ATLASSIAN_USER_EMAIL is set, otherwise Bearer."""
    email = os.environ.get("ATLASSIAN_USER_EMAIL", "").strip()
    if email:
        cred = base64.b64encode(f"{email}:{token}".encode()).decode()
        return f"Basic {cred}"
    return f"Bearer {token}"


def confluence_request(
    method: str,
    path: str,
    base_url: str,
    token: str,
    data: dict | None = None,
    params: dict | None = None,
    api_prefix: str = "/wiki/api/v2",
) -> dict | list | None:
    """Make an authenticated request to the Confluence REST API."""
    guard_args(method=method, path=path, base_url=base_url, api_prefix=api_prefix)
    url = f"{base_url}{api_prefix}{path}"
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
        print(f"ERROR: Confluence API {e.code} {method} {path}: {body_text}", file=sys.stderr)
        if e.code in (401, 403) and not os.environ.get("ATLASSIAN_USER_EMAIL", "").strip():
            print("", file=sys.stderr)
            print("HINT: Confluence Cloud requires Basic auth. Set ATLASSIAN_USER_EMAIL:", file=sys.stderr)
            print('  export ATLASSIAN_USER_EMAIL="you@example.com"', file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Formatters — convert API responses to readable markdown
# ---------------------------------------------------------------------------

def download_binary(url: str, token: str) -> bytes:
    """GET a file (e.g. an attachment) with auth and return its bytes.

    The Authorization header is not forwarded on redirects: attachment
    downloads redirect to a pre-signed media URL on another host.
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
# Pure helpers: cache dir, attachments, pagination
# ---------------------------------------------------------------------------

def skill_cache_dir(skill: str = "confluence") -> Path:
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


def safe_attachment_name(title: str) -> str:
    """Reduce an attachment title to a safe file name (no directories)."""
    name = re.split(r"[\\/]", title.strip())[-1]
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name).strip()
    if name in ("", ".", ".."):
        return "attachment"
    return name


def select_attachments(results: list[dict], names: list[str]) -> tuple[list[dict], list[str]]:
    """Pick attachments by title; with no names, pick every image attachment.

    Returns (selected, missing_names). Title matching is exact first, then
    case-insensitive.
    """
    if not names:
        picked = [a for a in results if str(a.get("mediaType", "")).startswith("image/")]
        return picked, []
    selected: list[dict] = []
    missing: list[str] = []
    for name in names:
        match = next((a for a in results if a.get("title") == name), None)
        if match is None:
            lowered = name.lower()
            match = next(
                (a for a in results if str(a.get("title", "")).lower() == lowered), None
            )
        if match is None:
            missing.append(name)
        elif match not in selected:
            selected.append(match)
    return selected, missing


def attachment_download_url(base_url: str, attachment: dict) -> str:
    """Build the authenticated download URL for a v2 attachment object.

    Only a site-relative link is accepted, so the credential can only go to
    ``base_url``. Raises ValueError otherwise.
    """
    link = attachment.get("downloadLink") or (attachment.get("_links") or {}).get("download", "")
    if not link or not link.startswith("/") or link.startswith("//"):
        raise ValueError(f"attachment {attachment.get('id', '?')} has no site-relative download link")
    if not link.startswith("/wiki/"):
        link = "/wiki" + link
    return f"{base_url}{link}"


def next_cursor(data: dict) -> str | None:
    """Return the pagination cursor from a response's ``_links.next``, if any."""
    nxt = ((data or {}).get("_links") or {}).get("next", "")
    if not nxt:
        return None
    values = parse_qs(urlparse(nxt).query).get("cursor")
    return values[0] if values else None


def cursor_note(data: dict) -> str:
    """Return a 'more results' hint for paginated list output, or ''."""
    cursor = next_cursor(data)
    if not cursor:
        return ""
    return f"\nMore results available. Re-run with --cursor '{cursor}' (or raise --limit)."


_CODE_MACRO_RE = re.compile(
    r'<ac:structured-macro\b[^>]*ac:name="(?:code|noformat)"[^>]*>(.*?)</ac:structured-macro>',
    re.DOTALL,
)
_LANG_PARAM_RE = re.compile(r'<ac:parameter\b[^>]*ac:name="language"[^>]*>(.*?)</ac:parameter>', re.DOTALL)
_PLAIN_BODY_RE = re.compile(r"<ac:plain-text-body>(.*?)</ac:plain-text-body>", re.DOTALL)
_CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)


def _code_macro_text(inner: str) -> tuple[str, str]:
    """Return (language, code) for the inside of a code/noformat macro."""
    lang_m = _LANG_PARAM_RE.search(inner)
    lang = html.unescape(lang_m.group(1)).strip() if lang_m else ""
    body_m = _PLAIN_BODY_RE.search(inner)
    body = body_m.group(1) if body_m else re.sub(r"<ac:parameter\b.*?</ac:parameter>", "", inner, flags=re.DOTALL)
    chunks = _CDATA_RE.findall(body)
    code = "".join(chunks) if chunks else html.unescape(re.sub(r"<[^>]+>", "", body))
    return lang, code.strip("\n")


def _image_markdown(m: re.Match) -> str:
    inner = m.group(0)
    att = re.search(r'ri:filename="([^"]*)"', inner)
    if att:
        return f"![{att.group(1)}](attachment:{att.group(1)})"
    url = re.search(r'ri:value="([^"]*)"', inner)
    if url:
        return f"![]({url.group(1)})"
    return ""


def _strip_html(text: str) -> str:
    """Minimal HTML-to-text conversion for Confluence storage format.

    Code/noformat macros become fenced blocks, attached and linked images
    become ``![name](attachment:name)`` / ``![](url)``, other macros keep their
    body text behind a ``[macro-name]`` marker.
    """
    code_blocks: list[str] = []

    def _stash_code(m: re.Match) -> str:
        lang, code = _code_macro_text(m.group(1))
        code_blocks.append(f"\n```{lang}\n{code}\n```\n")
        return f"\x00{len(code_blocks) - 1}\x00"

    text = _CODE_MACRO_RE.sub(_stash_code, text)
    text = _CDATA_RE.sub(lambda m: html.escape(m.group(1), quote=False), text)
    text = re.sub(r"<ac:image\b[^>]*/>|<ac:image\b.*?</ac:image>", _image_markdown, text, flags=re.DOTALL)
    text = re.sub(r'<ri:page\b[^>]*ri:content-title="([^"]*)"[^>]*/>', r"[page: \1]", text)
    text = re.sub(r"<ac:parameter\b.*?</ac:parameter>", "", text, flags=re.DOTALL)
    text = re.sub(r'<ac:structured-macro\b[^>]*ac:name="([^"]*)"[^>]*>', r"[\1] ", text)
    text = re.sub(r"</tr>", "\n", text)
    text = re.sub(r"<t[hd]\b[^>]*>", "| ", text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", lambda m: "#" * int(m.group(1)) + " " + m.group(2) + "\n", text)
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)
    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"[\2](\1)", text, flags=re.DOTALL)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: code_blocks[int(m.group(1))], text)
    return text.strip()


def format_page_markdown(page: dict, base_url: str = "") -> str:
    """Convert a Confluence page JSON to readable markdown."""
    page_id = page.get("id", "")
    title = page.get("title", "(no title)")
    status = page.get("status", "")
    space_id = page.get("spaceId", "")
    author_id = page.get("authorId", "")
    created = page.get("createdAt", "")
    version = page.get("version", {})
    version_num = version.get("number", "")
    version_date = version.get("createdAt", "")
    version_msg = version.get("message", "")

    lines = [f"## {title}"]
    lines.append("")
    lines.append(f"- **Page ID**: {page_id}")
    lines.append(f"- **Space ID**: {space_id}")
    lines.append(f"- **Status**: {status}")
    lines.append(f"- **Version**: {version_num}")
    if version_msg:
        lines.append(f"- **Version Message**: {version_msg}")
    lines.append(f"- **Author**: {author_id}")
    lines.append(f"- **Created**: {created}")
    lines.append(f"- **Last Updated**: {version_date}")

    parent_id = page.get("parentId")
    if parent_id:
        lines.append(f"- **Parent Page ID**: {parent_id}")

    links = page.get("_links", {})
    webui = links.get("webui", "")
    link_base = links.get("base", base_url)
    if webui and link_base:
        lines.append(f"- **URL**: {link_base}{webui}")

    body = page.get("body", {})
    storage = body.get("storage", {})
    if isinstance(storage, dict) and storage.get("value"):
        lines.append("")
        lines.append("### Content")
        lines.append("")
        lines.append(_strip_html(storage["value"]))

    labels = page.get("labels", {})
    if isinstance(labels, dict):
        label_results = labels.get("results", [])
        if label_results:
            names = [lb.get("name", "") for lb in label_results]
            lines.append(f"- **Labels**: {', '.join(names)}")

    return "\n".join(lines)


def format_pages_table(results: list[dict], total_label: str = "") -> str:
    """Format a list of pages as a markdown table."""
    header = total_label or f"{len(results)} pages"
    lines = [f"## {header}"]
    lines.append("")

    if not results:
        lines.append("No pages found.")
        return "\n".join(lines)

    lines.append("| ID | Title | Space ID | Status | Version | Updated |")
    lines.append("|----|-------|----------|--------|---------|---------|")

    for p in results:
        pid = p.get("id", "")
        title = p.get("title", "")
        if len(title) > 50:
            title = title[:47] + "..."
        space_id = p.get("spaceId", "")
        status = p.get("status", "")
        ver = p.get("version", {})
        ver_num = ver.get("number", "")
        ver_date = ver.get("createdAt", "")[:10] if ver.get("createdAt") else ""
        lines.append(f"| {pid} | {title} | {space_id} | {status} | {ver_num} | {ver_date} |")

    return "\n".join(lines)


def format_spaces_table(results: list[dict]) -> str:
    """Format a list of spaces as a markdown table."""
    lines = [f"## Spaces ({len(results)})"]
    lines.append("")

    if not results:
        lines.append("No spaces found.")
        return "\n".join(lines)

    lines.append("| ID | Key | Name | Type | Status |")
    lines.append("|----|-----|------|------|--------|")

    for s in results:
        sid = s.get("id", "")
        key = s.get("key", "")
        name = s.get("name", "")
        if len(name) > 40:
            name = name[:37] + "..."
        stype = s.get("type", "")
        status = s.get("status", "")
        lines.append(f"| {sid} | {key} | {name} | {stype} | {status} |")

    return "\n".join(lines)


def format_search_results(data: dict) -> str:
    """Format CQL search results as markdown."""
    results = data.get("results", [])
    total = data.get("totalSize", len(results))

    lines = [f"## Search Results ({len(results)} of {total})"]
    lines.append("")

    if not results:
        lines.append("No results found.")
        return "\n".join(lines)

    lines.append("| Type | ID | Title | Space | Last Modified |")
    lines.append("|------|----|-------|-------|---------------|")

    for r in results:
        content = r.get("content", {}) or r.get("space", {})
        ctype = content.get("type", r.get("entityType", ""))
        cid = content.get("id", "")
        title = r.get("title", content.get("title", content.get("name", "")))
        title = re.sub(r"@@@[eh]l@@@", "", title)
        if len(title) > 50:
            title = title[:47] + "..."
        space = ""
        if "space" in content:
            space = content["space"].get("key", "")
        elif "_expandable" in content and "space" in content["_expandable"]:
            space_path = content["_expandable"]["space"]
            m = re.search(r"/([^/]+)$", space_path)
            if m:
                space = m.group(1)
        last_mod = r.get("lastModified", content.get("history", {}).get("lastUpdated", {}).get("when", ""))
        if last_mod:
            last_mod = last_mod[:10]
        lines.append(f"| {ctype} | {cid} | {title} | {space} | {last_mod} |")

    return "\n".join(lines)


def format_comments_markdown(results: list[dict]) -> str:
    """Format page comments as markdown."""
    lines = [f"## Comments ({len(results)})"]
    lines.append("")
    if not results:
        lines.append("No comments.")
        return "\n".join(lines)
    for c in results:
        cid = c.get("id", "")
        author = c.get("authorId", "")
        created = c.get("createdAt", "")
        version = c.get("version", {})
        body = c.get("body", {})
        storage = body.get("storage", {})
        text = ""
        if isinstance(storage, dict) and storage.get("value"):
            text = _strip_html(storage["value"])
        lines.append(f"### Comment {cid} — {author} — {created}")
        lines.append("")
        if text:
            lines.append(text)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_view(args: argparse.Namespace) -> None:
    """View a single page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str] = {"body-format": "storage"}
    if args.include_labels:
        params["include-labels"] = "true"
    data = confluence_request("GET", f"/pages/{page_id}", base_url, token, params=params)
    print(format_page_markdown(data, base_url))


def cmd_search(args: argparse.Namespace) -> None:
    """Search content via CQL."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str | int] = {
        "cql": args.cql,
        "limit": args.limit,
    }
    if args.cursor:
        params["cursor"] = args.cursor
    data = confluence_request(
        "GET", "/search", base_url, token, params=params,
        api_prefix="/wiki/rest/api",
    )
    print(format_search_results(data) + cursor_note(data))


def cmd_pages(args: argparse.Namespace) -> None:
    """List pages, optionally filtered by space."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str | int] = {"limit": args.limit}
    if args.title:
        params["title"] = args.title
    if args.status:
        params["status"] = args.status
    if args.cursor:
        params["cursor"] = args.cursor

    if args.space_id:
        data = confluence_request("GET", f"/spaces/{args.space_id}/pages", base_url, token, params=params)
    else:
        data = confluence_request("GET", "/pages", base_url, token, params=params)

    results = data.get("results", [])
    print(format_pages_table(results) + cursor_note(data))


def cmd_spaces(args: argparse.Namespace) -> None:
    """List spaces."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str | int] = {"limit": args.limit}
    if args.type:
        params["type"] = args.type
    if args.status:
        params["status"] = args.status
    if args.cursor:
        params["cursor"] = args.cursor
    data = confluence_request("GET", "/spaces", base_url, token, params=params)
    results = data.get("results", [])
    print(format_spaces_table(results) + cursor_note(data))


def cmd_create(args: argparse.Namespace) -> None:
    """Create a new page."""
    token = get_token()
    base_url = get_base_url()
    body: dict = {
        "spaceId": args.space_id,
        "status": "current",
        "title": args.title,
        "body": {
            "representation": "storage",
            "value": args.body or "",
        },
    }
    if args.parent_id:
        body["parentId"] = args.parent_id

    data = confluence_request("POST", "/pages", base_url, token, data=body)
    page_id = data.get("id", "")
    links = data.get("_links", {})
    webui = links.get("webui", "")
    link_base = links.get("base", base_url)
    url = f"{link_base}{webui}" if webui else f"{base_url}/wiki/pages/{page_id}"
    print(f"Created page {page_id}: {data.get('title', '')}")
    print(f"URL: {url}")


def cmd_update(args: argparse.Namespace) -> None:
    """Update an existing page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)

    current = confluence_request("GET", f"/pages/{page_id}", base_url, token, params={"body-format": "storage"})
    current_version = current.get("version", {}).get("number", 1)
    current_title = current.get("title", "")
    current_status = current.get("status", "current")

    payload: dict = {
        "id": page_id,
        "status": current_status,
        "title": args.title or current_title,
        "body": {
            "representation": "storage",
            "value": args.body if args.body is not None else current.get("body", {}).get("storage", {}).get("value", ""),
        },
        "version": {
            "number": current_version + 1,
            "message": args.version_message or "",
        },
    }

    confluence_request("PUT", f"/pages/{page_id}", base_url, token, data=payload)
    print(f"Updated page {page_id}: {payload['title']} (version {current_version + 1})")
    links = current.get("_links", {})
    webui = links.get("webui", "")
    link_base = links.get("base", base_url)
    if webui:
        print(f"URL: {link_base}{webui}")


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a page (moves to trash)."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str] = {}
    if args.purge:
        params["purge"] = "true"
    confluence_request("DELETE", f"/pages/{page_id}", base_url, token, params=params or None)
    action = "Purged" if args.purge else "Deleted (moved to trash)"
    print(f"{action} page {page_id}")


def cmd_comments(args: argparse.Namespace) -> None:
    """List comments on a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str | int] = {"body-format": "storage", "limit": args.limit}
    data = confluence_request("GET", f"/pages/{page_id}/footer-comments", base_url, token, params=params)
    results = data.get("results", [])
    print(format_comments_markdown(results))


def cmd_comment(args: argparse.Namespace) -> None:
    """Add a comment to a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    body = {
        "pageId": page_id,
        "body": {
            "representation": "storage",
            "value": f"<p>{html.escape(args.body)}</p>",
        },
    }
    data = confluence_request("POST", "/footer-comments", base_url, token, data=body)
    print(f"Comment added to page {page_id} (id: {data.get('id', '')})")


def cmd_labels(args: argparse.Namespace) -> None:
    """List labels on a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str | int] = {"limit": args.limit}
    data = confluence_request("GET", f"/pages/{page_id}/labels", base_url, token, params=params)
    results = data.get("results", [])
    if not results:
        print(f"No labels on page {page_id}.")
        return
    names = [lb.get("name", "") for lb in results]
    print(f"Labels on page {page_id}: {', '.join(names)}")


def cmd_add_label(args: argparse.Namespace) -> None:
    """Add labels to a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    labels_data = [{"name": name} for name in args.names]
    confluence_request("POST", f"/pages/{page_id}/labels", base_url, token, data=labels_data)
    print(f"Added labels to page {page_id}: {', '.join(args.names)}")


def format_attachments_table(results: list[dict], page_id: str) -> str:
    """Format a list of attachments as a markdown table."""
    lines = [f"## Attachments for page {page_id} ({len(results)})"]
    lines.append("")

    if not results:
        lines.append("No attachments found.")
        return "\n".join(lines)

    lines.append("| ID | Title | Media Type | Size (Bytes) | Created At |")
    lines.append("|----|-------|------------|--------------|------------|")

    for a in results:
        aid = a.get("id", "")
        title = a.get("title", "")
        if len(title) > 40:
            title = title[:37] + "..."
        media_type = a.get("mediaType", "")
        file_size = a.get("fileSize", "-")
        created_at = a.get("createdAt", "")[:10] if a.get("createdAt") else ""
        lines.append(f"| {aid} | {title} | {media_type} | {file_size} | {created_at} |")

    return "\n".join(lines)


def cmd_attachments(args: argparse.Namespace) -> None:
    """List attachments on a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str | int] = {"limit": args.limit}
    if args.cursor:
        params["cursor"] = args.cursor
    data = confluence_request("GET", f"/pages/{page_id}/attachments", base_url, token, params=params)
    results = data.get("results", [])
    print(format_attachments_table(results, page_id) + cursor_note(data))


MAX_ATTACHMENT_PAGES = 20


def cmd_download_attachment(args: argparse.Namespace) -> None:
    """Download page attachments (all images by default) into the cache dir."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    results: list[dict] = []
    params: dict[str, str | int] = {"limit": 250}
    for _ in range(MAX_ATTACHMENT_PAGES):
        data = confluence_request("GET", f"/pages/{page_id}/attachments", base_url, token, params=params)
        results.extend(data.get("results", []))
        cursor = next_cursor(data)
        if not cursor:
            break
        params["cursor"] = cursor
    selected, missing = select_attachments(results, args.names)
    for name in missing:
        print(f"ERROR: no attachment titled {name!r} on page {page_id}", file=sys.stderr)
    if not selected:
        if not missing:
            print(f"No image attachments on page {page_id}.", file=sys.stderr)
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
            url = attachment_download_url(base_url, att)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            failed += 1
            continue
        name = safe_attachment_name(str(att.get("title", "")))
        stem, dot, ext = name.rpartition(".")
        n = 1
        while name in used:
            n += 1
            name = f"{stem}_{n}.{ext}" if dot else f"{ext}_{n}"
        used.add(name)
        dest = out_dir / name
        dest.write_bytes(download_binary(url, token))
        print(dest)
    if failed:
        sys.exit(1)


def cmd_children(args: argparse.Namespace) -> None:
    """List child pages of a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str | int] = {"limit": args.limit}
    if args.cursor:
        params["cursor"] = args.cursor
    data = confluence_request("GET", f"/pages/{page_id}/direct-children", base_url, token, params=params)
    results = data.get("results", [])
    print(format_pages_table(results, f"Children of page {page_id}") + cursor_note(data))


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

PAGE_HELP = "Page ID (e.g. 12345) or full Confluence page URL"


def main() -> None:
    parser = argparse.ArgumentParser(description="Confluence REST API client for developer workflows.")
    sub = parser.add_subparsers(dest="command", required=True)

    # view
    p_view = sub.add_parser("view", help="View a single page")
    p_view.add_argument("page", help=PAGE_HELP)
    p_view.add_argument("--include-labels", action="store_true", help="Include labels")
    p_view.set_defaults(func=cmd_view)

    # search
    p_search = sub.add_parser("search", help="Search content via CQL")
    p_search.add_argument("cql", help='CQL query string (e.g. "space=TEAM AND type=page")')
    p_search.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    p_search.add_argument("--cursor", help="Pagination cursor from a previous result")
    p_search.set_defaults(func=cmd_search)

    # pages
    p_pages = sub.add_parser("pages", help="List pages")
    p_pages.add_argument("--space-id", help="Filter by space ID")
    p_pages.add_argument("--title", help="Filter by exact title")
    p_pages.add_argument("--status", help="Filter by status (current, draft, trashed)")
    p_pages.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_pages.add_argument("--cursor", help="Pagination cursor from a previous result")
    p_pages.set_defaults(func=cmd_pages)

    # spaces
    p_spaces = sub.add_parser("spaces", help="List spaces")
    p_spaces.add_argument("--type", help="Filter by type (global, personal)")
    p_spaces.add_argument("--status", help="Filter by status (current, archived)")
    p_spaces.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_spaces.add_argument("--cursor", help="Pagination cursor from a previous result")
    p_spaces.set_defaults(func=cmd_spaces)

    # create
    p_create = sub.add_parser("create", help="Create a new page")
    p_create.add_argument("--space-id", required=True, help="Space ID")
    p_create.add_argument("--title", required=True, help="Page title")
    p_create.add_argument("--body", help="Page body in Confluence storage format (HTML)")
    p_create.add_argument("--parent-id", help="Parent page ID")
    p_create.set_defaults(func=cmd_create)

    # update
    p_update = sub.add_parser("update", help="Update an existing page")
    p_update.add_argument("page", help=PAGE_HELP)
    p_update.add_argument("--title", help="New title")
    p_update.add_argument("--body", help="New body in storage format (HTML)")
    p_update.add_argument("--version-message", help="Version comment")
    p_update.set_defaults(func=cmd_update)

    # delete
    p_delete = sub.add_parser("delete", help="Delete a page")
    p_delete.add_argument("page", help=PAGE_HELP)
    p_delete.add_argument("--purge", action="store_true", help="Permanently delete (skip trash)")
    p_delete.set_defaults(func=cmd_delete)

    # comments
    p_comments = sub.add_parser("comments", help="List comments on a page")
    p_comments.add_argument("page", help=PAGE_HELP)
    p_comments.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_comments.set_defaults(func=cmd_comments)

    # comment
    p_comment = sub.add_parser("comment", help="Add a comment to a page")
    p_comment.add_argument("page", help=PAGE_HELP)
    p_comment.add_argument("body", help="Comment text")
    p_comment.set_defaults(func=cmd_comment)

    # labels
    p_labels = sub.add_parser("labels", help="List labels on a page")
    p_labels.add_argument("page", help=PAGE_HELP)
    p_labels.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_labels.set_defaults(func=cmd_labels)

    # add-label
    p_add_label = sub.add_parser("add-label", help="Add labels to a page")
    p_add_label.add_argument("page", help=PAGE_HELP)
    p_add_label.add_argument("names", nargs="+", help="Label names to add")
    p_add_label.set_defaults(func=cmd_add_label)

    # children
    p_children = sub.add_parser("children", help="List child pages")
    p_children.add_argument("page", help=PAGE_HELP)
    p_children.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_children.add_argument("--cursor", help="Pagination cursor from a previous result")
    p_children.set_defaults(func=cmd_children)

    # attachments
    p_attachments = sub.add_parser("attachments", help="List page attachments")
    p_attachments.add_argument("page", help=PAGE_HELP)
    p_attachments.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_attachments.add_argument("--cursor", help="Pagination cursor from a previous result")
    p_attachments.set_defaults(func=cmd_attachments)

    # download-attachment
    p_dl = sub.add_parser(
        "download-attachment",
        help="Download page attachments (default: all images) into the skill cache dir",
    )
    p_dl.add_argument("page", help=PAGE_HELP)
    p_dl.add_argument("names", nargs="*", help="Attachment titles (default: every image attachment)")
    p_dl.add_argument("--out-dir", help="Destination directory (default: a new dir under the unified cache)")
    p_dl.set_defaults(func=cmd_download_attachment)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

