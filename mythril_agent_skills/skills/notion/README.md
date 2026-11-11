# Notion Skill

This skill helps AI assistants read and write Notion pages and data source items using the official REST API — the same shape as the `jira` and `confluence` skills:

- View a page as full markdown in one request
- Search the workspace, create and edit pages, add comments
- Discover data sources, query items, create ticket items, change properties such as Status
- `check` command verifies the token and prints the token-creation link when needed

No third-party CLI tools required — uses only the Notion REST API via a bundled Python script (Python 3.10+ standard library, zero dependencies).

**Official API docs**: https://developers.notion.com/reference/intro
**API version**: `Notion-Version: 2026-03-11`
**Full API reference**: See [`API_REFERENCE.md`](./API_REFERENCE.md) in this directory.

## Prerequisites

### 1. Get a personal access token (PAT)

1. Open **Personal access tokens** in the Notion Developer portal: **https://www.notion.so/developers/tokens**
2. Select **New token**
3. Name it, choose the **Notion API** capability (this covers read/create/update/search content and read/create comments), and set an **Expiration** (7 days / 30 days / 90 days / 180 days / 1 year; default 1 year)
4. Select **Create token** and copy the value immediately — **it is shown only once**

Notes:

- If you do not see **New token**: on Business/Enterprise plans PAT creation is restricted to workspace owners by default; ask an admin to allow it in **Settings → Connections**. Guests cannot create PATs.
- A PAT acts as the user who created it, so it accesses everything that user can access. You do **not** need to share pages via "Add connections" (that is only for internal-connection bots).
- PATs expire. When one expires, create a new one at the same link and update `NOTION_API_KEY`.

Need a team-owned token that does not depend on one person? Use an **internal connection** instead (`https://app.notion.com/developers/connections` → **Internal connections** → **Configuration** → API token), but you must grant it page access via the **Content access** tab or each page's **Connections → + Add connection**.

### 2. Set the environment variable

Add to your shell config (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
export NOTION_API_KEY="your-token"
```

Or run `skills-check notion` (the workspace dependency checker), which prints the same link and writes the variable for you.

Reload your shell or run `source ~/.zshrc`.

### 3. Verify setup

```bash
python3 scripts/notion_api.py check
```

This verifies `NOTION_API_KEY` is set and that the API accepts it (`GET /v1/users/me`). If the token is missing or invalid, the command prints **https://www.notion.so/developers/tokens** and the 4 setup steps above.

## Usage

Run from this skill directory. All page arguments accept a bare ID or a full Notion URL.

```bash
# Verify setup
python3 scripts/notion_api.py check

# View a page (full markdown)
python3 scripts/notion_api.py view "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef"

# Search
python3 scripts/notion_api.py search "deployment guide"

# Create a page (the first H1 becomes the title)
python3 scripts/notion_api.py create --title "Design Doc" --markdown "## Overview\n\nDetails."

# Append / replace content
python3 scripts/notion_api.py append PAGE --markdown "## Next steps\n\n- [ ] Review"
python3 scripts/notion_api.py update PAGE --old "old text" --new "new text"

# Comments
python3 scripts/notion_api.py comments PAGE
python3 scripts/notion_api.py comment PAGE "Looks good!"

# Ticket workflows: discover data sources, query, create, change status
python3 scripts/notion_api.py data-sources DATABASE_ID
python3 scripts/notion_api.py query DATA_SOURCE_ID --filter '{"property":"Status","select":{"equals":"Todo"}}'
python3 scripts/notion_api.py create-item DATA_SOURCE_ID --title "Fix login timeout" --status Todo
python3 scripts/notion_api.py set-property PAGE --name Status --value Done
```

Run `python3 scripts/notion_api.py --help` (and `<command> --help`) for all commands and flags.

## API version notes

This skill is pinned to `2026-03-11` and always sends `markdown_version: v2`:

- `archived` was replaced by `in_trash`; block append `after` became a `position` object; `transcription` blocks became `meeting_notes`.
- Databases are split into **data sources**: query with `PATCH /v1/data_sources/{id}/query`, create pages with `parent: {"type": "data_source_id", ...}`. A database ID is not a data source ID.
- v1 enhanced markdown is deprecated; the next API version will reject it.

See [`API_REFERENCE.md`](./API_REFERENCE.md) for the endpoint list and upgrade-guide links.
