# Notion REST API Reference

> **Official docs**: https://developers.notion.com/reference/intro
> **Versioning**: https://developers.notion.com/reference/versioning
> **Authentication**: https://developers.notion.com/reference/authentication
> **Markdown content**: https://developers.notion.com/guides/data-apis/working-with-markdown-content
> **Upgrade guide 2026-03-11**: https://developers.notion.com/guides/get-started/upgrade-guide-2026-03-11
> **Upgrade guide 2025-09-03**: https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03

Base URL: `https://api.notion.com/v1`

**This skill uses `Notion-Version: 2026-03-11`** (the current latest version, confirmed on the official Versioning page).

## Authentication

All requests need these headers:

```
Authorization: Bearer {NOTION_API_KEY}
Notion-Version: 2026-03-11
Content-Type: application/json
```

Token types (https://developers.notion.com/reference/authentication):

| Type | How to obtain | Identity | Used by this skill |
|------|--------------|----------|--------------------|
| Personal access token (PAT) | https://www.notion.so/developers/tokens → **New token** → **Notion API** capability | Acts as the creating user; inherits their page permissions; no per-page sharing needed | **Yes** — `NOTION_API_KEY` |
| Internal connection token | Developer portal → **Internal connections** → **Configuration** → API token | Separate bot user; must be granted page access via **Content access** or **Add connection** | No |
| OAuth access token | Public connection OAuth flow | Acts as the authorizing user | No (use the official hosted MCP instead) |

PAT specifics: shown only once; expiration 7/30/90/180 days or 1 year (default 1 year); `GET /v1/users` (list all users) is **not** available to PATs — use `GET /v1/users/me` or **Retrieve token's bot user**. Admins revoke PATs from **Settings → Connections → All personal access tokens**.

## Endpoint map

| Operation | Method / Path | Skill command |
|-----------|---------------|---------------|
| Verify token / identity | `GET /v1/users/me` | `check`, `myself` |
| Search workspace | `POST /v1/search` | `search` |
| Retrieve page metadata | `GET /v1/pages/{page_id}` | `view` (and all write commands, to get the URL) |
| Retrieve page content as markdown | `GET /v1/pages/{page_id}/markdown?markdown_version=v2` | `view` |
| Create a page | `POST /v1/pages` (body `markdown`, `markdown_version`, optional `parent`) | `create`, `create-item` |
| Insert markdown content | `PATCH /v1/pages/{page_id}/markdown` with `type: insert_content` | `append` |
| Replace exact strings | `PATCH /v1/pages/{page_id}/markdown` with `type: update_content` | `update` |
| Update page properties / trash | `PATCH /v1/pages/{page_id}` (`properties`, `in_trash`) | `set-property`, `delete` |
| List comments | `GET /v1/comments?block_id={page_id}` | `comments` |
| Add a comment | `POST /v1/comments` (body `parent.page_id`, `markdown`, `markdown_version`) | `comment` |
| List data sources of a database | `GET /v1/databases/{database_id}` → `data_sources[]` | `data-sources` |
| Query a data source | `PATCH /v1/data_sources/{data_source_id}/query` | `query` |
| Retrieve a data source schema | `GET /v1/data_sources/{data_source_id}` | — (see below) |
| Append block children | `PATCH /v1/blocks/{block_id}/children` | — (not covered; use blocks API for fine-grained control) |

`GET /v1/pages/{page_id}/markdown` returns a `page_markdown` object:

```json
{
  "object": "page_markdown",
  "id": "...",
  "markdown": "# Title\n\nBody...",
  "truncated": false,
  "unknown_block_ids": [],
  "warnings": []
}
```

Check `truncated`, `unknown_block_ids`, and `warnings`; the `view` command reports all three.

`PATCH /v1/pages/{page_id}/markdown` accepts `allow_async: true` for large documents, returning an `async_task` with a `status_url`. The skill does not currently use async mode.

## Markdown versions

| Version | Syntax | Status |
|---------|--------|--------|
| `v1` | Enhanced markdown (XML-like tags) | **Deprecated**; default on current API versions; a future version will reject it with `400 validation_error` |
| `v2` | Notion-flavored Markdown | **Recommended**; this skill always sends `markdown_version: "v2"` |

Where the parameter goes: query param on `GET /v1/pages/{id}/markdown`; body param on `PATCH /v1/pages/{id}/markdown`, `POST /v1/pages` (next to `markdown`), `POST /v1/comments` and `PATCH /v1/comments/{id}`. Sending `markdown_version` with `children` or `rich_text` instead of `markdown` returns `400 validation_error`.

Migration guide: https://developers.notion.com/guides/data-apis/migrate-to-notion-flavored-markdown

## Breaking changes in 2026-03-11

| Before (2025-09-03) | After (2026-03-11) |
|---------------------|--------------------|
| `archived` field | `in_trash` field (pages, databases, blocks, data sources) |
| `after` string param on Append block children | `position` object (`after_block`, `start`, `end`) |
| `transcription` block type | `meeting_notes` block type |

## Data sources (since 2025-09-03)

A database can contain multiple **data sources**, each with its own schema and ID. A database ID and a data source ID are **not interchangeable**.

- `GET /v1/databases/{id}` now returns the list of `data_sources` (each with `id` and `name`).
- `GET /v1/data_sources/{id}` returns the schema (`properties`) of a single data source.
- `PATCH /v1/data_sources/{id}/query` replaces the old `POST /v1/databases/{id}/query`.
- Creating a page in a data source uses `parent: {"type": "data_source_id", "data_source_id": "..."}`.
- Search filter values changed from `"database"` to `"data_source"`.

Use the skill's `data-sources DATABASE_ID` command to discover the right ID before running `query` or `create-item`.

## Limits

| Item | Value |
|------|-------|
| Rate limit | ~3 requests/second (bursts allowed); `429` includes `Retry-After` |
| `page_size` on paginated endpoints | up to 100; inspect `has_more` and `next_cursor` |
| Append block children | max 100 children per request, 2 levels of nesting |
| Payload size | 500 KB |
| Rich text length | 2,000 characters |
| Multi-select options / related pages | 100 each |

Treat `next_cursor` as opaque: pass it back verbatim as `start_cursor` (`--start-cursor` on `search` / `query`). Do not parse page URLs to derive IDs — use the `id` field.

## Error codes

| Code | Meaning / fix |
|------|---------------|
| `unauthorized` (401) | Token invalid/expired — recreate a PAT at https://www.notion.so/developers/tokens |
| `restricted_resource` (403) | Missing capability or no page access — check the token's **Notion API** capability |
| `object_not_found` (404) | Wrong ID — a database ID is not a data source ID |
| `validation_error` (400) | Check v2 markdown syntax and property types |
| `rate_limited` (429) | Respect `Retry-After` |
| `conflict_error` (409) | Concurrent modification — retry |
| `row_limit_exceeded` (406) | Reduce the requested page size / data source size |
