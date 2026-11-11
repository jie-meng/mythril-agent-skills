---
name: notion
description: >
  Use the Notion REST API (via a bundled Python script) for common Notion workflows
  from terminal. Trigger whenever the user asks to view, search, create, edit, or
  comment on Notion pages, query or create items in a Notion database or data source,
  or says phrases like "notion page", "notion 页面", "看 notion", "搜 notion",
  "notion 文档", "notion ticket", "create notion page", "update notion",
  "query notion database", "notion wiki". Also trigger when the user pastes a
  Notion page URL and wants to interact with it. No third-party CLI tools required —
  only Python 3.10+ standard library.
license: Apache-2.0
---

# When to Use This Skill

- A user pastes a Notion page URL and wants to view or edit it
- Page operations: view, search, create, append, update, trash, comment
- Ticket operations: list data sources, query items, create items, change a property such as Status
- Any request mentioning Notion pages, docs, wiki, databases, or data sources

Notion has no native issue/ticket object: a ticket is one page inside a data source. Jira's `transition` maps here to changing a property (e.g. `Status`) with `set-property`; there is no built-in workflow.

# Prerequisites

Requires `NOTION_API_KEY` — a Notion **personal access token (PAT)**. See `README.md` in this skill directory for setup.

### Get a token

1. Open **Personal access tokens** in the Developer portal: https://www.notion.so/developers/tokens
2. Select **New token**
3. Name it, choose the **Notion API** capability, set an **Expiration** (default 1 year), and select **Create token**
4. Copy the token immediately — it is shown only once

If you cannot create a token: on Business/Enterprise plans only workspace owners can by default; ask an admin to allow PATs in **Settings → Connections**. Only full workspace members can create PATs (guests cannot).

Then set the environment variable:

```bash
export NOTION_API_KEY="your-token"
```

A PAT acts as the user who created it, so it can read/write everything that user can access — you do **not** need to share each page via "Add connections" (that is only required for internal-connection bots).

## Security — MANDATORY rules for AI agents

1. **NEVER echo, print, or log** the value of `NOTION_API_KEY` or any other environment variable. Do NOT run commands like `echo $NOTION_API_KEY` or `printenv NOTION_API_KEY` — even for debugging.
2. **NEVER pass token/credential values as inline CLI arguments or env-var overrides** (e.g. `NOTION_API_KEY=xxx python3 ...`). The script reads the credential from the environment automatically — just run the script directly.
3. **When debugging auth errors**, rely solely on the script's error output (401, 403, 404 messages). Do NOT attempt to verify tokens by reading or printing them.
4. **Do NOT read environment variable values** using shell commands or programmatic access. The script handles all credential access internally.
5. **NEVER extract credentials from OS credential stores or config files.** Strictly forbidden commands include:
   - `security find-internet-password`, `security find-generic-password` (macOS Keychain)
   - `git credential fill`, `cat ~/.git-credentials`, `cat ~/.netrc`
   - Any command that outputs a password, token, or secret value from any credential store
6. **NEVER use extracted credential values in commands.** Do NOT manually construct authenticated requests using raw credential values. The bundled script handles all authentication internally.

## Runtime requirements

- Python 3.10+ for `scripts/notion_api.py` (standard library only, zero dependencies)
- Pinned to `Notion-Version: 2026-03-11` and Notion-flavored Markdown v2

# Workflow

1. Determine what the user wants (view, search, create, query, change status, etc.)
2. Run the appropriate script command
3. Read the markdown output and present it to the user
4. For write operations, confirm success and show the resulting URL
5. If a token is missing or returns 401, the script prints the token-creation link: https://www.notion.so/developers/tokens

# Running the Script

One script is available in `scripts/` relative to this skill directory. Run it from this directory:

```bash
python3 scripts/notion_api.py --help
```

All commands accept a bare page ID (32 hex chars, with or without dashes) or a full Notion URL — the script parses the ID out automatically. When the user pastes a URL, pass it directly.

### Check setup and connectivity

```bash
python3 scripts/notion_api.py check
```

Verifies `NOTION_API_KEY` is set and the API accepts it (`GET /v1/users/me`). On missing/invalid token it prints the token-creation link and the 4 steps above.

### View a page (full markdown)

```bash
python3 scripts/notion_api.py view "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef"
python3 scripts/notion_api.py view 1234567890abcdef1234567890abcdef
```

Uses `GET /v1/pages/{id}/markdown?markdown_version=v2` — one request returns the whole page, no recursive block traversal.

### Search the workspace

```bash
python3 scripts/notion_api.py search "deployment guide"
python3 scripts/notion_api.py search "release" --limit 10 --start-cursor "<cursor>"
```

### Create a page

```bash
python3 scripts/notion_api.py create --title "Design Doc" --markdown "## Overview\n\nDetails here."
python3 scripts/notion_api.py create --title "Meeting Notes" --markdown "- [ ] Follow up" \
  --parent "https://www.notion.so/Team-1234567890abcdef1234567890abcdef" --parent-type page_id
```

The first `#` heading becomes the page title automatically. Without `--parent` the page is created in Private.

### Append and edit content

```bash
# Append markdown to the end of a page
python3 scripts/notion_api.py append PAGE --markdown "## Next steps\n\n- [ ] Review"
python3 scripts/notion_api.py append PAGE --markdown "# Top note" --position start

# Replace an exact string inside a page
python3 scripts/notion_api.py update PAGE --old "old text" --new "new text"
```

Both use `PATCH /v1/pages/{id}/markdown` with `markdown_version: v2`. `append` uses `insert_content`; `update` uses `update_content` with `content_updates`.

### Move a page to trash

```bash
python3 scripts/notion_api.py delete PAGE
```

Uses `PATCH /v1/pages/{id}` with `in_trash: true` (the `archived` field was removed in 2026-03-11). Confirm intent before running.

### Comments

```bash
python3 scripts/notion_api.py comments PAGE
python3 scripts/notion_api.py comment PAGE "Looks good, ship it."
```

### Data sources and ticket items

```bash
# Discover data source IDs for a database (a database can hold several)
python3 scripts/notion_api.py data-sources DATABASE_ID

# Query items in a data source (NOT a database ID)
python3 scripts/notion_api.py query DATA_SOURCE_ID
python3 scripts/notion_api.py query DATA_SOURCE_ID --filter '{"property":"Status","select":{"equals":"In Progress"}}'
python3 scripts/notion_api.py query DATA_SOURCE_ID --limit 50 --start-cursor "<cursor>"

# Create an item in a data source
python3 scripts/notion_api.py create-item DATA_SOURCE_ID --title "Fix login timeout" \
  --markdown "## Description\n\nUsers hit a 30s timeout." --status "Todo"
python3 scripts/notion_api.py create-item DATA_SOURCE_ID --title "Add export" \
  --status "In Progress" --status-property "State"

# Change a property (maps to a ticket status transition)
python3 scripts/notion_api.py set-property PAGE --name Status --value Done
python3 scripts/notion_api.py set-property PAGE --name Priority --value High --type select
python3 scripts/notion_api.py set-property PAGE --name Notes --value "text" --type rich_text
```

`set-property` supports `--type` values: `select` (default), `status`, `rich_text`, `checkbox`, `number`, `url`, `date`.

### Current identity

```bash
python3 scripts/notion_api.py myself
```

Uses `GET /v1/users/me`; `GET /v1/users` is not available to PATs.

## Using the Output

The script outputs structured markdown. When the user asks to "view" or "read" a page, run `view` and present the output. For search/query results, the output is a summary table — follow up with `view` for detail.

For write operations (create, create-item, append, update, delete, comment, set-property), the script prints a confirmation with the page ID and URL.

# Output Expectations

For every task, provide:

1. Commands executed (or planned) in code blocks
2. Short result summary (page title, ID, URL, key metadata)
3. If a write operation succeeded, include the page ID and URL
4. If an operation fails, include the exact error and the recommended fix

# Error Handling

- **Missing `NOTION_API_KEY`**: the script reports the missing variable and prints the token-creation link plus the 4 setup steps.
- **401 Unauthorized**: token is invalid or expired — recreate a PAT at https://www.notion.so/developers/tokens (PATs expire; default 1 year).
- **403 Forbidden**: the token lacks the needed capability, or the target page is not accessible to the token creator. Check the **Notion API** capability on the token.
- **404 Not Found**: verify the ID. A database ID is not a data source ID — use `data-sources` to discover the right one.
- **400 Bad Request**: check Notion-flavored Markdown v2 syntax and property types. v2 parse errors start with `Markdown errors blocked parsing`.
- **429 Too Many Requests**: rate limited (~3 requests/second). Respect `Retry-After` and retry.
- **validation_error on markdown**: v1 enhanced markdown is deprecated; always send `markdown_version: v2` (the script does this for you).
- **SSL: CERTIFICATE_VERIFY_FAILED**: enterprise TLS inspection proxy. Set `SSL_CERT_FILE` / `CURL_CA_BUNDLE` / `REQUESTS_CA_BUNDLE` to your CA bundle, or `SSL_NO_VERIFY=1` as a last resort.

# Notes

- The script uses only the Python standard library — no `pip install` needed.
- Pinned to `Notion-Version: 2026-03-11`. Breaking changes in that version: `archived` → `in_trash`, block `after` → `position`, `transcription` → `meeting_notes`.
- Databases are split into **data sources** since `2025-09-03`: query with `PATCH /v1/data_sources/{id}/query`, create pages with `parent: {"type": "data_source_id", ...}`. `GET /v1/databases/{id}` now returns the list of data sources. Database IDs and data source IDs are not interchangeable.
- Markdown endpoints default to v1 on current versions but v1 is deprecated; the script always sends `markdown_version: v2`.
- PATs are user-scoped and expire. For team-owned automation that must not depend on one person, use an internal connection (bot token) instead — but that requires granting page access via **Connections → + Add connection** or the Developer portal's **Content access** tab.
- For advanced endpoints not covered here, see `API_REFERENCE.md` in this skill directory.
- For destructive actions (delete, overwriting content), confirm intent before executing.
