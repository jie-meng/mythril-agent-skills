#!/usr/bin/env python3
"""Notion REST API client for common developer workflows.

Required environment variable:
  NOTION_API_KEY — Notion personal access token (PAT)

Uses only Python 3.10+ standard library (zero dependencies).
Pinned to Notion API version 2026-03-11 and Notion-flavored Markdown v2.
Get a token: https://www.notion.so/developers/tokens
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlencode

BASE_URL = "https://api.notion.com/v1"
API_VERSION = "2026-03-11"
MARKDOWN_VERSION = "v2"
TOKEN_ENV = "NOTION_API_KEY"
TOKEN_URL = "https://www.notion.so/developers/tokens"

TOKEN_HELP = f"""Get a personal access token:
  1. Open {TOKEN_URL}
  2. Select 'New token', choose the 'Notion API' capability, set an expiration
  3. Select 'Create token' and copy it (shown only once)
  4. Business/Enterprise: ask a workspace owner to allow PATs in Settings -> Connections
Then set: export {TOKEN_ENV}=..."""

_ID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"|[0-9a-fA-F]{32}"
)
_BARE_ID_RE = re.compile(
    r"^(?:[0-9a-fA-F]{32}"
    r"|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)

PROPERTY_TYPES = ("select", "status", "rich_text", "checkbox", "number", "url", "date")


# ---------------------------------------------------------------------------
# Auth / HTTP
# ---------------------------------------------------------------------------


def _create_ssl_context() -> ssl.SSLContext | None:
    """Build an SSL context respecting enterprise network configuration."""
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
    """Return NOTION_API_KEY from the environment; never print its value."""
    token = os.environ.get(TOKEN_ENV, "").strip()
    if not token:
        print(f"ERROR: {TOKEN_ENV} not set.", file=sys.stderr)
        print("", file=sys.stderr)
        print(TOKEN_HELP, file=sys.stderr)
        sys.exit(1)
    return token


def build_headers(token: str) -> dict[str, str]:
    """Return the three headers every Notion REST request needs."""
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": API_VERSION,
        "Content-Type": "application/json",
    }


def notion_request(
    method: str,
    path: str,
    token: str,
    data: dict | None = None,
    params: dict | None = None,
) -> dict | None:
    """Make an authenticated request to the Notion REST API."""
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urlencode(params)
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    for key, value in build_headers(token).items():
        req.add_header(key, value)
    try:
        ctx = _create_ssl_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"ERROR: Notion API {e.code} {method} {path}: {body_text}", file=sys.stderr)
        if e.code == 401:
            print("HINT: token is invalid or expired.", file=sys.stderr)
            print(TOKEN_HELP, file=sys.stderr)
        elif e.code == 403:
            print(
                "HINT: token lacks the Notion API capability, or the page is not "
                "accessible to the token creator.",
                file=sys.stderr,
            )
        elif e.code == 404:
            print(
                "HINT: verify the ID; a database ID is not a data source ID "
                "(use 'data-sources').",
                file=sys.stderr,
            )
        elif e.code == 429:
            print(
                "HINT: rate limited (~3 requests/second). Respect Retry-After and retry.",
                file=sys.stderr,
            )
        elif e.code == 400:
            print(
                "HINT: check Notion-flavored Markdown v2 syntax and property types.",
                file=sys.stderr,
            )
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Pure helpers / formatters (no network calls)
# ---------------------------------------------------------------------------


def parse_page_input(value: str) -> str:
    """Extract a Notion ID from a bare ID or a full Notion URL."""
    v = value.strip()
    if _BARE_ID_RE.fullmatch(v):
        return v.replace("-", "")
    matches = list(_ID_RE.finditer(v))
    if not matches:
        print(f"ERROR: cannot find a Notion ID in: {value}", file=sys.stderr)
        sys.exit(1)
    return matches[-1].group(0).replace("-", "")


def plain_text(rich_text: list[dict]) -> str:
    """Flatten a Notion rich_text array to plain text."""
    out = []
    for item in rich_text or []:
        if not isinstance(item, dict):
            continue
        if item.get("plain_text"):
            out.append(item["plain_text"])
        elif isinstance(item.get("text"), dict):
            out.append(item["text"].get("content", ""))
    return "".join(out)


def page_title(obj: dict) -> str:
    """Best-effort title for a page or data source object."""
    if obj.get("name"):
        return obj["name"]
    for prop in (obj.get("properties") or {}).values():
        if isinstance(prop, dict) and prop.get("type") == "title":
            return plain_text(prop.get("title", [])) or "(untitled)"
    return "(untitled)"


def _cursor_note(data: dict) -> str:
    if not data.get("has_more"):
        return ""
    return "\n\nMore results available. Re-run with --start-cursor " + str(
        data.get("next_cursor", "")
    )


def format_page_markdown(page: dict, md: dict) -> str:
    """Render page metadata plus its full markdown content."""
    lines = [f"## {page_title(page)}", ""]
    for label, key in (
        ("ID", "id"),
        ("URL", "url"),
        ("Created", "created_time"),
        ("Last edited", "last_edited_time"),
    ):
        if page.get(key):
            lines.append(f"- **{label}**: {page[key]}")
    lines += ["", "### Content", "", (md.get("markdown") or "").rstrip()]
    if md.get("truncated"):
        lines += ["", "> Note: the API truncated this page's content."]
    unknown = md.get("unknown_block_ids") or []
    if unknown:
        lines += [
            "",
            f"> Note: {len(unknown)} block(s) could not be converted to markdown.",
        ]
    for warning in md.get("warnings") or []:
        if isinstance(warning, dict):
            lines += [
                "",
                f"> Warning: {warning.get('code', '')}: {warning.get('message', '')}",
            ]
    return "\n".join(lines)


def format_search_results(data: dict) -> str:
    """Render POST /v1/search results as a markdown table."""
    results = data.get("results") or []
    if not results:
        return "No results found."
    lines = ["| Title | Type | ID | URL |", "|---|---|---|---|"]
    for obj in results:
        lines.append(
            f"| {page_title(obj)} | {obj.get('object', '')} | "
            f"{obj.get('id', '')} | {obj.get('url', '')} |"
        )
    return "\n".join(lines) + _cursor_note(data)


def format_query_results(data: dict) -> str:
    """Render data source query results as a markdown table."""
    results = data.get("results") or []
    if not results:
        return "No items found."
    lines = ["| Title | ID | URL |", "|---|---|---|"]
    for page in results:
        lines.append(
            f"| {page_title(page)} | {page.get('id', '')} | {page.get('url', '')} |"
        )
    return "\n".join(lines) + _cursor_note(data)


def format_data_sources(db: dict) -> str:
    """Render the data_sources list from GET /v1/databases/{id}."""
    items = db.get("data_sources") or []
    if not items:
        return "No data sources found."
    lines = ["| Name | ID |", "|---|---|"]
    for ds in items:
        lines.append(f"| {ds.get('name') or '(unnamed)'} | {ds.get('id', '')} |")
    return "\n".join(lines)


def format_comments(results: list[dict]) -> str:
    """Render comments as a markdown list."""
    if not results:
        return "No comments."
    lines = []
    for comment in results:
        author = (comment.get("created_by") or {}).get("id", "unknown")
        text = plain_text(comment.get("rich_text", [])) or comment.get("markdown", "")
        lines.append(f"- **{author}** ({comment.get('created_time', '')}): {text}")
    return "\n".join(lines)


def format_user(user: dict) -> str:
    """Render a user object as a short markdown list."""
    lines = []
    for label, key in (("Name", "name"), ("ID", "id"), ("Type", "type")):
        if user.get(key):
            lines.append(f"- {label}: {user[key]}")
    return "\n".join(lines) or "(no user details returned)"


def format_check_result(user: dict) -> str:
    """Render the outcome of the check command."""
    return (
        f"OK: {TOKEN_ENV} is set and the Notion API accepted it "
        f"(Notion-Version {API_VERSION}).\n{format_user(user)}"
    )


def with_title(title: str, markdown: str) -> str:
    """Prepend an H1 title unless the markdown already starts with one."""
    if not title:
        return markdown
    if markdown.lstrip().startswith("# "):
        return markdown
    return f"# {title}\n\n{markdown}"


def build_property_value(prop_type: str, value: str) -> dict:
    """Build a Notion page property value for the given type."""
    if prop_type == "select":
        return {"select": {"name": value}}
    if prop_type == "status":
        return {"status": {"name": value}}
    if prop_type == "rich_text":
        return {"rich_text": [{"text": {"content": value}}]}
    if prop_type == "checkbox":
        return {"checkbox": value.strip().lower() in ("1", "true", "yes", "on")}
    if prop_type == "number":
        return {"number": float(value)}
    if prop_type == "url":
        return {"url": value}
    if prop_type == "date":
        return {"date": {"start": value}}
    raise ValueError(f"unsupported property type: {prop_type}")


def _warnings_note(result: dict) -> str:
    warnings = [w for w in (result.get("warnings") or []) if isinstance(w, dict)]
    if not warnings:
        return ""
    return "Warnings: " + "; ".join(
        f"{w.get('code', '')}: {w.get('message', '')}" for w in warnings
    )


def _parse_json_arg(value: str, flag: str):
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        print(f"ERROR: {flag} is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _load_page(token: str, page_id: str) -> dict:
    """Fetch page metadata first, so write commands can report its URL."""
    return notion_request("GET", f"/pages/{page_id}", token) or {}


def _write_result(action: str, page: dict, page_id: str, extra: str = "") -> None:
    print(f"{action} page: {page_id}")
    if extra:
        print(extra)
    if page.get("url"):
        print(f"URL: {page['url']}")


def cmd_check(args: argparse.Namespace) -> None:
    token = get_token()
    user = notion_request("GET", "/users/me", token) or {}
    print(format_check_result(user))
    print(f"\nNeed a new token? {TOKEN_URL}")


def cmd_myself(args: argparse.Namespace) -> None:
    token = get_token()
    user = notion_request("GET", "/users/me", token) or {}
    print(format_user(user))


def cmd_view(args: argparse.Namespace) -> None:
    token = get_token()
    page_id = parse_page_input(args.page)
    page = _load_page(token, page_id)
    md = notion_request(
        "GET",
        f"/pages/{page_id}/markdown",
        token,
        params={"markdown_version": MARKDOWN_VERSION},
    ) or {}
    print(format_page_markdown(page, md))


def cmd_search(args: argparse.Namespace) -> None:
    token = get_token()
    data = {"query": args.query, "page_size": min(max(args.limit, 1), 100)}
    if args.start_cursor:
        data["start_cursor"] = args.start_cursor
    result = notion_request("POST", "/search", token, data=data) or {}
    print(format_search_results(result))


def cmd_create(args: argparse.Namespace) -> None:
    if not args.title and not args.markdown:
        print("ERROR: provide --title or --markdown.", file=sys.stderr)
        sys.exit(1)
    token = get_token()
    body = {
        "markdown": with_title(args.title or "", args.markdown or ""),
        "markdown_version": MARKDOWN_VERSION,
    }
    if args.parent:
        ident = parse_page_input(args.parent)
        if args.parent_type == "data_source_id":
            body["parent"] = {"type": "data_source_id", "data_source_id": ident}
        else:
            body["parent"] = {"type": "page_id", "page_id": ident}
    page = notion_request("POST", "/pages", token, data=body) or {}
    print(f"Created page: {page.get('id', '')}")
    if page.get("url"):
        print(f"URL: {page['url']}")


def cmd_append(args: argparse.Namespace) -> None:
    token = get_token()
    page_id = parse_page_input(args.page)
    page = _load_page(token, page_id)
    insert: dict = {"content": args.markdown}
    if args.position:
        insert["position"] = {"type": args.position}
    body = {
        "type": "insert_content",
        "insert_content": insert,
        "markdown_version": MARKDOWN_VERSION,
    }
    result = notion_request("PATCH", f"/pages/{page_id}/markdown", token, data=body) or {}
    _write_result("Appended content to", page, page_id, _warnings_note(result))


def cmd_update(args: argparse.Namespace) -> None:
    token = get_token()
    page_id = parse_page_input(args.page)
    page = _load_page(token, page_id)
    body = {
        "type": "update_content",
        "update_content": {
            "content_updates": [{"old_str": args.old, "new_str": args.new}]
        },
        "markdown_version": MARKDOWN_VERSION,
    }
    result = notion_request("PATCH", f"/pages/{page_id}/markdown", token, data=body) or {}
    _write_result("Updated content on", page, page_id, _warnings_note(result))


def cmd_delete(args: argparse.Namespace) -> None:
    token = get_token()
    page_id = parse_page_input(args.page)
    page = _load_page(token, page_id)
    notion_request("PATCH", f"/pages/{page_id}", token, data={"in_trash": True})
    _write_result("Moved to trash", page, page_id)


def cmd_comments(args: argparse.Namespace) -> None:
    token = get_token()
    page_id = parse_page_input(args.page)
    result = notion_request(
        "GET",
        "/comments",
        token,
        params={"block_id": page_id, "page_size": min(max(args.limit, 1), 100)},
    ) or {}
    print(format_comments(result.get("results", [])))


def cmd_comment(args: argparse.Namespace) -> None:
    token = get_token()
    page_id = parse_page_input(args.page)
    page = _load_page(token, page_id)
    body = {
        "parent": {"page_id": page_id},
        "markdown": args.body,
        "markdown_version": MARKDOWN_VERSION,
    }
    result = notion_request("POST", "/comments", token, data=body) or {}
    _write_result(
        "Added comment to", page, page_id, f"Comment ID: {result.get('id', '')}"
    )


def cmd_data_sources(args: argparse.Namespace) -> None:
    token = get_token()
    db_id = parse_page_input(args.database)
    result = notion_request("GET", f"/databases/{db_id}", token) or {}
    print(format_data_sources(result))


def cmd_query(args: argparse.Namespace) -> None:
    token = get_token()
    ds_id = parse_page_input(args.data_source)
    body: dict = {"page_size": min(max(args.limit, 1), 100)}
    if args.filter:
        body["filter"] = _parse_json_arg(args.filter, "--filter")
    if args.sorts:
        body["sorts"] = _parse_json_arg(args.sorts, "--sorts")
    if args.start_cursor:
        body["start_cursor"] = args.start_cursor
    result = notion_request("PATCH", f"/data_sources/{ds_id}/query", token, data=body) or {}
    print(format_query_results(result))


def cmd_create_item(args: argparse.Namespace) -> None:
    token = get_token()
    ds_id = parse_page_input(args.data_source)
    body: dict = {
        "parent": {"type": "data_source_id", "data_source_id": ds_id},
        "markdown": with_title(args.title, args.markdown or ""),
        "markdown_version": MARKDOWN_VERSION,
    }
    if args.status:
        body["properties"] = {
            args.status_property: {"select": {"name": args.status}}
        }
    page = notion_request("POST", "/pages", token, data=body) or {}
    print(f"Created item: {page.get('id', '')}")
    if page.get("url"):
        print(f"URL: {page['url']}")


def cmd_set_property(args: argparse.Namespace) -> None:
    token = get_token()
    page_id = parse_page_input(args.page)
    page = _load_page(token, page_id)
    try:
        prop = build_property_value(args.type, args.value)
    except ValueError as e:
        print(f"ERROR: invalid property value: {e}", file=sys.stderr)
        sys.exit(1)
    notion_request(
        "PATCH", f"/pages/{page_id}", token, data={"properties": {args.name: prop}}
    )
    _write_result(f"Set {args.name} = {args.value} on", page, page_id)


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

PAGE_HELP = "Page ID (32 hex chars or UUID) or full Notion page URL"
DS_HELP = "Data source ID or URL (use 'data-sources' to discover it)"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"Notion REST API client for developer workflows (Notion-Version {API_VERSION})."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="Verify token and API connectivity")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("myself", help="Show the token owner identity")
    p.set_defaults(func=cmd_myself)

    p = sub.add_parser("view", help="View a page as markdown")
    p.add_argument("page", help=PAGE_HELP)
    p.set_defaults(func=cmd_view)

    p = sub.add_parser("search", help="Search pages and data sources")
    p.add_argument("query", help="Search text")
    p.add_argument("--limit", type=int, default=20, help="Max results (default 20)")
    p.add_argument("--start-cursor", help="Pagination cursor from a previous result")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("create", help="Create a page from markdown")
    p.add_argument("--title", help="Page title (first H1 in markdown is used otherwise)")
    p.add_argument("--markdown", default="", help="Page content as Notion-flavored Markdown v2")
    p.add_argument("--parent", help="Parent page/data source ID or URL")
    p.add_argument(
        "--parent-type", choices=("page_id", "data_source_id"), default="page_id"
    )
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("append", help="Append markdown content to a page")
    p.add_argument("page", help=PAGE_HELP)
    p.add_argument("--markdown", required=True, help="Markdown to insert")
    p.add_argument(
        "--position", choices=("start", "end"), help="Insert at start or end (default: end)"
    )
    p.set_defaults(func=cmd_append)

    p = sub.add_parser("update", help="Replace an exact string inside a page")
    p.add_argument("page", help=PAGE_HELP)
    p.add_argument("--old", required=True, help="Existing text to find")
    p.add_argument("--new", required=True, help="Replacement text")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Move a page to trash")
    p.add_argument("page", help=PAGE_HELP)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("comments", help="List comments on a page")
    p.add_argument("page", help=PAGE_HELP)
    p.add_argument("--limit", type=int, default=25, help="Max results (default 25)")
    p.set_defaults(func=cmd_comments)

    p = sub.add_parser("comment", help="Add a comment to a page")
    p.add_argument("page", help=PAGE_HELP)
    p.add_argument("body", help="Comment text (markdown)")
    p.set_defaults(func=cmd_comment)

    p = sub.add_parser("data-sources", help="List data sources in a database")
    p.add_argument("database", help="Database ID or URL")
    p.set_defaults(func=cmd_data_sources)

    p = sub.add_parser("query", help="Query items in a data source")
    p.add_argument("data_source", help=DS_HELP)
    p.add_argument("--filter", help="Filter object as JSON")
    p.add_argument("--sorts", help="Sorts array as JSON")
    p.add_argument("--limit", type=int, default=25, help="Max results (default 25)")
    p.add_argument("--start-cursor", help="Pagination cursor from a previous result")
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("create-item", help="Create a ticket item in a data source")
    p.add_argument("data_source", help=DS_HELP)
    p.add_argument("--title", required=True, help="Item title")
    p.add_argument("--markdown", default="", help="Item body as markdown")
    p.add_argument("--status", help="Status value (select property)")
    p.add_argument(
        "--status-property", default="Status", help="Status property name (default Status)"
    )
    p.set_defaults(func=cmd_create_item)

    p = sub.add_parser("set-property", help="Change a page property (ticket status)")
    p.add_argument("page", help=PAGE_HELP)
    p.add_argument("--name", required=True, help="Property name")
    p.add_argument("--value", required=True, help="New value")
    p.add_argument("--type", choices=PROPERTY_TYPES, default="select")
    p.set_defaults(func=cmd_set_property)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
