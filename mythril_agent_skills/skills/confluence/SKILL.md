---
name: confluence
description: >
  Reads and manages Confluence Cloud pages through a bundled REST API script:
  view, search (CQL), create, update, delete pages, list spaces, child pages and
  attachments, and add comments or labels. Use when the user wants to read or
  change Confluence/wiki content or pastes a Confluence URL — e.g. "confluence
  page", "wiki page", "search confluence", "update confluence", "看 wiki",
  "看 confluence", "confluence 页面", "wiki 空间".
license: Apache-2.0
---

# When to Use This Skill

- A user pastes a Confluence page URL and wants to view or edit it
- Page operations: view, search, create, update, delete
- Space operations: list spaces
- Comment operations: list comments, add comment
- Label operations: list labels, add labels
- Child page listing, attachment listing and download
- Any request mentioning Confluence pages, wiki, or spaces

# Prerequisites

Requires `ATLASSIAN_API_TOKEN` and `ATLASSIAN_USER_EMAIL`. See `README.md` in this skill directory for setup.

- `ATLASSIAN_API_TOKEN` (**required**) — Atlassian API token
- `ATLASSIAN_USER_EMAIL` (**required**) — Atlassian account email, used for Basic auth
- `CONFLUENCE_BASE_URL` (optional — takes precedence) — e.g. `https://yoursite.atlassian.net` or a custom Cloud domain
- `ATLASSIAN_BASE_URL` (optional — shared fallback) — e.g. `https://yoursite.atlassian.net`

The script targets **Confluence Cloud** (REST API v2, `/wiki/api/v2`); self-hosted Data Center/Server is not supported.

Base URL resolution: `CONFLUENCE_BASE_URL` > `ATLASSIAN_BASE_URL`. When neither is set, page commands accept a full Confluence URL instead of a page ID. For commands without a specific page (search, spaces, pages, create), one of these base URLs is required.

**Pasted URLs are host-checked**: credentials are only sent to the configured base URL's host, or to an `*.atlassian.net` site when no base URL is configured (or the configured one is itself on atlassian.net). Plain `http://` URLs are refused. If the script refuses a URL, tell the user — do not work around it.

If your Confluence and Jira share the same base URL, set only `ATLASSIAN_BASE_URL`. If they differ, set `CONFLUENCE_BASE_URL` for Confluence and `JIRA_BASE_URL` for Jira.

## Security — MANDATORY rules for AI agents

1. **NEVER echo, print, or log** the values of `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL`, `CONFLUENCE_BASE_URL`, `JIRA_BASE_URL`, or any other environment variable. Do NOT run commands like `echo $ATLASSIAN_API_TOKEN` or `printenv ATLASSIAN_API_TOKEN` — even for debugging.
2. **NEVER pass token/credential values as inline CLI arguments or env-var overrides** (e.g. `ATLASSIAN_API_TOKEN=xxx python3 ...`). The script reads credentials from the environment automatically — just run the script directly.
3. **When debugging auth errors**, rely solely on the script's error output (401, 403, 404 messages). Do NOT attempt to verify tokens by reading or printing them.
4. **Do NOT read environment variable values** using shell commands or programmatic access. The script handles all credential access internally.
5. **NEVER extract credentials from OS credential stores or config files.** Strictly forbidden commands include:
   - `security find-internet-password`, `security find-generic-password` (macOS Keychain)
   - `git credential fill`, `cat ~/.git-credentials`, `cat ~/.netrc`
   - Any command that outputs a password, token, or secret value from any credential store
6. **NEVER use extracted credential values in commands.** Do NOT manually construct authenticated requests using raw credential values. The bundled script handles all authentication internally.
7. **Use only the documented CLI subcommands.** Do NOT `import` the bundled script or call its internal functions (`get_token()`, `*_request()`, etc.) via `python3 -c` or ad-hoc code — that bypasses the CLI's argument handling, and a misordered argument can put the credential into a URL or error message. If a needed subcommand is missing, tell the user instead of scripting around it. Script output redacts credentials as `[REDACTED]`; if a credential value ever appears in any output anyway, do NOT repeat it — tell the user to rotate it.

## Runtime requirements

- Python 3.10+ for `scripts/confluence_api.py`
- Optional: `curl` for downloading images hosted **outside** Confluence (public URLs, no credentials)

# Workflow

1. Determine what the user wants (view, search, create, update, etc.)
2. Run the appropriate script command
3. Read the markdown output and present it to the user
4. For write operations, confirm success and show the resulting URL

## Image handling

When a viewed page, comments, or search result contains screenshots or image links, proactively retrieve and analyze them.

- **Confluence attachments** — `view` renders attached images as `![name](attachment:name)`, and any URL on the Confluence host (`/download/attachments/`, `/wiki/...`) is an attachment too. These need authentication: download them with the bundled subcommand, never with `curl`:

  ```bash
  python3 SKILL_PATH/scripts/confluence_api.py download-attachment 12345              # every image attachment
  python3 SKILL_PATH/scripts/confluence_api.py download-attachment 12345 "shot 1.png"  # by title
  ```

  It saves into a new directory under the unified cache (`<user-cache-root>/mythril-skills-cache/confluence/<random>/`) and prints each saved path. Pass `--out-dir` only when the user named a destination.
- **External images** (public hosts, e.g. `![](https://example.com/a.png)`) — download with `curl -fsSL -o "<cache-dir>/<name>" "<url>"` into the same cache directory (macOS: `~/Library/Caches/mythril-skills-cache/confluence/`, Linux: `${XDG_CACHE_HOME:-~/.cache}/mythril-skills-cache/confluence/`, Windows: `%LOCALAPPDATA%\mythril-skills-cache\confluence\`). Never add credentials to `curl`.

**Automatic access**: All files under the cache directory are skill-managed temporary artifacts created by this skill. Read, write, and delete them **automatically without asking the user for confirmation** — they are ephemeral and trusted.

Analyze images with available image-capable tools and summarize only evidence relevant to the user task.

## Running the Script

All commands use `scripts/confluence_api.py` (Python 3.10+ standard library only). `SKILL_PATH` below is this skill's installed directory.

### View a page

Accepts either a page ID or a full Confluence URL:

```bash
# With ATLASSIAN_BASE_URL set
python3 SKILL_PATH/scripts/confluence_api.py view 12345

# Without ATLASSIAN_BASE_URL — pass the full URL directly
python3 SKILL_PATH/scripts/confluence_api.py view "https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345/Page+Title"

# Include labels
python3 SKILL_PATH/scripts/confluence_api.py view 12345 --include-labels
```

When the user pastes a Confluence URL, pass it directly — the script parses out the base URL and page ID automatically.

### Search content via CQL

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 SKILL_PATH/scripts/confluence_api.py search "space=TEAM AND type=page"
python3 SKILL_PATH/scripts/confluence_api.py search "text ~ 'deployment guide'" --limit 10
python3 SKILL_PATH/scripts/confluence_api.py search "type=page AND lastModified >= now('-7d')"
python3 SKILL_PATH/scripts/confluence_api.py search "label = 'architecture' AND type=page"
python3 SKILL_PATH/scripts/confluence_api.py search "space=TEAM" --cursor "<cursor>"   # next page
```

List commands (`search`, `spaces`, `pages`, `children`, `attachments`) print `More results available. Re-run with --cursor '...'` when the result was cut at `--limit` — never treat a truncated list as complete.

Common CQL patterns:

| CQL | Purpose |
|-----|---------|
| `space=TEAM AND type=page` | All pages in a space |
| `type=page AND lastModified >= now('-7d')` | Pages modified in last 7 days |
| `text ~ 'keyword'` | Full text search |
| `title = 'Page Title'` | Exact title match |
| `title ~ 'partial'` | Title contains text |
| `label = 'my-label' AND type=page` | Pages with a specific label |
| `creator = currentUser() AND type=page` | Pages I created |
| `space=TEAM AND ancestor = 12345` | Pages under a specific parent |

### List spaces

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 SKILL_PATH/scripts/confluence_api.py spaces
python3 SKILL_PATH/scripts/confluence_api.py spaces --type global
python3 SKILL_PATH/scripts/confluence_api.py spaces --limit 50
```

### List pages

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 SKILL_PATH/scripts/confluence_api.py pages --space-id 12345
python3 SKILL_PATH/scripts/confluence_api.py pages --title "Meeting Notes"
python3 SKILL_PATH/scripts/confluence_api.py pages --limit 50
```

### Create a page

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 SKILL_PATH/scripts/confluence_api.py create --space-id 12345 --title "New Page"
python3 SKILL_PATH/scripts/confluence_api.py create --space-id 12345 --title "Design Doc" \
  --body "<h2>Overview</h2><p>This document describes...</p>" \
  --parent-id 67890
```

| Flag | Required | Description |
|------|----------|-------------|
| `--space-id` | Yes | Space ID (use `spaces` command to find) |
| `--title` | Yes | Page title |
| `--body` | No | Body in Confluence storage format (HTML) |
| `--parent-id` | No | Parent page ID |

### Update a page

```bash
python3 SKILL_PATH/scripts/confluence_api.py update 12345 --title "Updated Title"
python3 SKILL_PATH/scripts/confluence_api.py update 12345 --body "<p>New content here</p>" --version-message "Fixed typo"
python3 SKILL_PATH/scripts/confluence_api.py update "https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345" --title "New Title"
```

The script automatically handles version numbering — it fetches the current version and increments it.

### Delete a page

**Confirm with the user before running** — `--purge` cannot be undone.

```bash
python3 SKILL_PATH/scripts/confluence_api.py delete 12345
python3 SKILL_PATH/scripts/confluence_api.py delete 12345 --purge  # permanently delete
```

### List comments on a page

```bash
python3 SKILL_PATH/scripts/confluence_api.py comments 12345
python3 SKILL_PATH/scripts/confluence_api.py comments 12345 --limit 10
```

### Add a comment to a page

```bash
python3 SKILL_PATH/scripts/confluence_api.py comment 12345 "This looks good, ship it!"
```

### List labels on a page

```bash
python3 SKILL_PATH/scripts/confluence_api.py labels 12345
```

### Add labels to a page

```bash
python3 SKILL_PATH/scripts/confluence_api.py add-label 12345 architecture backend
```

### List child pages

```bash
python3 SKILL_PATH/scripts/confluence_api.py children 12345
```

Uses the non-deprecated `/pages/{id}/direct-children` endpoint under Confluence v2 API.

### List page attachments

```bash
python3 SKILL_PATH/scripts/confluence_api.py attachments 12345
```

### Download attachments

```bash
python3 SKILL_PATH/scripts/confluence_api.py download-attachment 12345                    # all image attachments
python3 SKILL_PATH/scripts/confluence_api.py download-attachment 12345 spec.pdf diagram.png
```

Saves under the unified cache dir (see Image handling) and prints one path per file. Exit code 1 if any named attachment is missing.

## Using the Output

The script outputs structured markdown. When the user asks to "view" or "read" a page, run the `view` command and present the output. For search results, the output is a summary table — if the user wants more detail on a specific page, follow up with `view`.

For write operations (create, update, delete, comment), the script prints a confirmation with the page ID and URL.

## API Reference

For advanced use cases or when the bundled script doesn't cover an operation, see `SKILL_PATH/references/API_REFERENCE.md` for the full Confluence REST API endpoint reference.

# Output Expectations

For every task, provide:

1. Commands executed (or planned) in code blocks
2. Short result summary (page title, ID, space, key metadata)
3. If a write operation succeeded, include the page ID and URL
4. If operation fails, include exact error and recommended fix
5. If images were downloaded and analyzed, include an **Image Evidence Summary** (source URL, what was observed, confidence/limits)

# Error Handling

- **Missing ATLASSIAN_API_TOKEN**: The script reports the missing variable and how to set it.
- **Missing ATLASSIAN_BASE_URL**: Only required for non-URL commands. The script suggests passing a full URL instead.
- **401 Unauthorized**: Token is invalid or expired — regenerate at https://id.atlassian.com/manage-profile/security/api-tokens
- **403 Forbidden**: User lacks permission for this operation in the target space.
- **404 Not Found**: Page or space doesn't exist — verify the page ID or space ID.
- **400 Bad Request**: Check field names, CQL syntax, and body format.
- **Refusing to send credentials / non-https URL**: the pasted URL is not on the configured Confluence host. Ask the user to confirm the site and set `CONFLUENCE_BASE_URL` if it is theirs.
- **Image download failed**: report the attachment/URL and the exact error; for attachments, use `download-attachment` (never a hand-built authenticated request).

# Notes

- The script uses only Python standard library — no `pip install` needed.
- Page commands accept both numeric page IDs and full Confluence URLs.
- When the user pastes a Confluence URL, prefer passing it directly to the script (URL-first).
- For destructive actions (delete, purge), confirm intent before executing.
- Page body uses Confluence storage format (HTML-like). For simple text, wrap in `<p>` tags.
- Shares the same `ATLASSIAN_API_TOKEN` and `ATLASSIAN_USER_EMAIL` as the Jira skill. For the base URL, use `ATLASSIAN_BASE_URL` as a shared default or set `CONFLUENCE_BASE_URL` / `JIRA_BASE_URL` individually if your instances are on different URLs.
