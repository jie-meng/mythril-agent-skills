---
name: jira
description: >
  Use Atlassian CLI (`acli`) or a bundled Python script for common Jira workflows
  from terminal. Trigger whenever the user asks to view, create, edit, assign,
  move, or comment on Jira issues/epics/sprints, or says phrases like "jira issue",
  "jira card", "看卡", "看 jira", "jira ticket", "move ticket", "assign ticket",
  "sprint issues", "create jira issue", "transition issue", "search jira". Also
  trigger when the user mentions a Jira issue key (e.g. PROJ-123) or pastes a
  Jira URL and wants to interact with it. Runs with zero dependencies when using
  `acli`; Python 3.10+ standard library fallback otherwise.
license: Apache-2.0
---

# When to Use This Skill

- A user mentions a Jira issue key (e.g. `PROJ-123`) or pastes a Jira URL and wants details
- Issue operations: view, search, create, edit, assign, move/transition, comment, link
- Sprint/board operations: list boards, list sprints, view sprint issues
- Any request mentioning Jira tickets, cards, or stories

# Backend Selection

This skill has two backends. Always prefer `acli` when available — it avoids SSL cert issues common in enterprise environments.

**FIRST, for EVERY operation, detect the backend:**

```bash
which acli 2>/dev/null && acli jira auth status 2>/dev/null && echo "ACLI_OK" || echo "FALLBACK"
```

- If the output contains `ACLI_OK` → use **acli** (primary path, below)
- Otherwise → use **Python fallback** (secondary path, below)

If `acli` is installed but `acli jira auth status` fails, tell the user: "acli is installed but not logged in. Run `acli jira auth login` to authenticate, or set ATLASSIAN_API_TOKEN for Python fallback."

---

# Primary Path: Atlassian CLI (`acli`)

Install once with `brew install acli` (macOS) or follow https://developer.atlassian.com/cloud/acli/guides/install-acli/. Login once with:

```bash
echo "<api-token>" | acli jira auth login --site "yoursite.atlassian.net" --email "you@example.com" --token
# Or OAuth (opens browser):
acli jira auth login --web
```

After login, no env vars needed. Commands use your auth session. No SSL cert issues — `acli` is a native binary.

## Security — MANDATORY rules for AI agents

1. **NEVER echo, print, or log** the values of `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL`, `JIRA_BASE_URL`, `CONFLUENCE_BASE_URL`, or any other environment variable.
2. **NEVER pass token/credential values as inline CLI arguments** (e.g. `echo "token" | acli jira auth login ...`). Use a file or prompt the user to authenticate themselves.
3. **When debugging auth errors**, rely solely on error messages. Do NOT attempt to verify tokens by reading or printing them.
4. **Do NOT read environment variable values** using shell commands or programmatic access.
5. **NEVER extract credentials from OS credential stores or config files.** Strictly forbidden: `security find-internet-password`, `git credential fill`, `cat ~/.git-credentials`, `cat ~/.netrc`, or any command that outputs a password, token, or secret value.
6. **NEVER use extracted credential values in commands.** Do NOT manually construct authenticated requests. `acli` handles auth internally; the Python script reads from environment internally.

## Workflow (acli)

1. Determine what the user wants (view, search, create, transition, etc.)
2. Run the appropriate `acli` command
3. Present the output to the user
4. For write operations, confirm success and show the resulting URL

## Image handling

When issue descriptions or comments contain screenshots or image links, proactively retrieve and analyze them.

Detect image links: Markdown syntax `![alt](url)`, plain URLs ending in `.png/.jpg/.jpeg/.gif/.webp/.svg`, and `/attachments/` paths.

Download under the unified cache.

**Bash (macOS / Linux):**
```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
  CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
fi
CACHE_DIR="$CACHE_ROOT/jira"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
IMAGE_CACHE="$RUN_DIR/images"
mkdir -p "$IMAGE_CACHE"
```

**Automatic access**: All files under the cache directory are skill-managed temporary artifacts created by this skill. Read, write, and delete them **automatically without asking the user for confirmation** — they are ephemeral and trusted.

Retrieve with `curl -fsSL`; if enterprise auth fails, retry with `curl -fsSL --negotiate -u :`.

Analyze images with available image-capable tools and summarize only evidence relevant to the user task.

## Commands (acli)

### View an issue

```bash
acli jira workitem view --key PROJ-123
acli jira workitem view --key "PROJ-123,PROJ-456"   # view multiple
```

### Search issues via JQL

```bash
acli jira workitem search --jql "project=PROJ AND status='In Progress'"
acli jira workitem search --jql "assignee=currentUser() AND status!=Done" --limit 30
acli jira workitem search --jql "project=PROJ AND created >= -7d ORDER BY created DESC"
acli jira workitem search --jql "summary ~ 'login bug' AND priority=High"
```

Common JQL patterns:

| JQL | Purpose |
|-----|---------|
| `assignee=currentUser()` | My issues |
| `assignee=currentUser() AND status!='Done'` | My open issues |
| `project=PROJ AND sprint in openSprints()` | Current sprint issues |
| `project=PROJ AND status='In Progress'` | In-progress work |
| `project=PROJ AND created >= -7d` | Created in last 7 days |
| `project=PROJ AND updated >= -1d` | Updated in last 24 hours |
| `project=PROJ AND type=Bug AND priority=High` | High priority bugs |
| `summary ~ 'keyword'` | Search in summary |
| `text ~ 'keyword'` | Full text search |

### Create an issue

```bash
acli jira workitem create --summary "Fix login timeout" --project PROJ --type Bug
acli jira workitem create --summary "Add export feature" --project PROJ --type Story \
  --description "Users should be able to export data as CSV" \
  --priority High --label "feature,backend" --parent PROJ-100
```

### Edit an issue

```bash
acli jira workitem edit --key PROJ-123 --summary "Updated summary" --priority High
acli jira workitem edit --key "PROJ-123,PROJ-456" --label "urgent,backend"
```

### Assign an issue

```bash
acli jira workitem assign --key PROJ-123 --user 5b10ac8d82e05b22cc7d4ef5
acli jira workitem assign --key PROJ-123 --user none      # unassign
```

### Transition (move) an issue

`acli` transitions by status name (not ID), so no two-step needed:

```bash
acli jira workitem transition --key PROJ-123 --status "In Progress"
acli jira workitem transition --key PROJ-123 --status Done --comment "Work complete"
```

To see available statuses, view the issue first — the output shows current status. For transition names, use the target status name (e.g. "In Progress", "Done", "To Do").

### Comment on an issue

```bash
acli jira workitem comment-create --key PROJ-123 --body "Investigating the root cause now."
```

### List comments

```bash
acli jira workitem comment-list --key PROJ-123
```

### Link two issues

```bash
acli jira workitem link --type Relates --inward PROJ-456 --outward PROJ-123
```

### List boards / sprints / sprint issues

```bash
acli jira board list --project PROJ
acli jira sprint list --board-id 42 --state active
acli jira sprint issue-list --sprint-id 123
```

### Current user info

```bash
acli jira auth status
```

---

# Fallback Path: Python Script

When `acli` is not available, use the bundled Python script `scripts/jira_api.py`. Requires Python 3.10+ standard library (zero pip dependencies).

## Prerequisites (Python fallback)

- `ATLASSIAN_API_TOKEN` (**required**) — API token or Personal Access Token
- `ATLASSIAN_USER_EMAIL` (**required for Jira Cloud**) — Atlassian account email, used for Basic auth
- `JIRA_BASE_URL` (optional — takes precedence) — e.g. `https://jira.yourcompany.com`
- `ATLASSIAN_BASE_URL` (optional — shared fallback) — e.g. `https://yoursite.atlassian.net`

Base URL resolution: `JIRA_BASE_URL` > `ATLASSIAN_BASE_URL`. When neither is set, issue commands accept a full Jira URL instead of an issue key. For commands without a specific issue (search, create, boards, sprints, myself), one of these base URLs is required.

If your Confluence and Jira share the same base URL, set only `ATLASSIAN_BASE_URL`. If they differ (e.g. self-hosted), set `JIRA_BASE_URL` for Jira and `CONFLUENCE_BASE_URL` for Confluence.

**SSL cert issues in enterprise environments**: The script supports `SSL_CERT_FILE` / `CURL_CA_BUNDLE` / `REQUESTS_CA_BUNDLE` for custom CA bundles, and `SSL_NO_VERIFY=1` as last resort. For a permanent fix, install `acli`.

## Runtime requirements (Python fallback)

- Python 3.10+ for `scripts/jira_api.py`
- Optional: `curl` for downloading linked screenshots/images

## Workflow (Python fallback)

1. Determine what the user wants (view, search, create, transition, etc.)
2. Run the appropriate script command
3. Read the markdown output and present it to the user
4. For write operations, confirm success and show the resulting URL

## Commands (Python fallback)

### View an issue

Accepts either an issue key or a full Jira URL:

```bash
python3 scripts/jira_api.py view PROJ-123
python3 scripts/jira_api.py view "https://yoursite.atlassian.net/browse/PROJ-123"
```

When the user pastes a Jira URL, pass it directly — the script parses out the base URL and issue key automatically.

### Search issues via JQL

```bash
python3 scripts/jira_api.py search "project=PROJ AND status='In Progress'"
python3 scripts/jira_api.py search "assignee=currentUser() AND status!=Done" --max-results 30
python3 scripts/jira_api.py search "project=PROJ AND created >= -7d ORDER BY created DESC"
```

### Create an issue

```bash
python3 scripts/jira_api.py create --project PROJ --summary "Fix login timeout" --type Bug
python3 scripts/jira_api.py create --project PROJ --summary "Add export feature" --type Story \
  --description "Users should be able to export data as CSV" \
  --priority High --labels feature backend --parent PROJ-100
```

| Flag | Required | Description |
|------|----------|-------------|
| `--project` | Yes | Project key |
| `--summary` | Yes | Issue summary |
| `--type` | No | Issue type (default: Task) |
| `--description` | No | Description text |
| `--priority` | No | Priority name (High, Medium, Low, etc.) |
| `--assignee` | No | Assignee account ID |
| `--labels` | No | Space-separated labels |
| `--parent` | No | Parent issue key |
| `--components` | No | Space-separated component names |

### Edit an issue

```bash
python3 scripts/jira_api.py edit PROJ-123 --summary "Updated summary" --priority High
python3 scripts/jira_api.py edit "https://yoursite.atlassian.net/browse/PROJ-123" --labels urgent backend
```

### Assign an issue

```bash
python3 scripts/jira_api.py assign PROJ-123 5b10ac8d82e05b22cc7d4ef5
python3 scripts/jira_api.py assign PROJ-123 none    # unassign
```

### Transition (move) an issue

Two-step: list available transitions, then apply one.

```bash
python3 scripts/jira_api.py transitions PROJ-123
python3 scripts/jira_api.py transition PROJ-123 31
python3 scripts/jira_api.py transition PROJ-123 31 --comment "Starting work on this"
python3 scripts/jira_api.py transition PROJ-123 41 --resolution Fixed
```

### Comment on an issue

```bash
python3 scripts/jira_api.py comment PROJ-123 "Investigating the root cause now."
```

### List comments

```bash
python3 scripts/jira_api.py comments PROJ-123
python3 scripts/jira_api.py comments PROJ-123 --max-results 5
```

### Link two issues

```bash
python3 scripts/jira_api.py link PROJ-123 PROJ-456 Blocks
```

### Current user info

```bash
python3 scripts/jira_api.py myself
```

### List boards / sprints / sprint issues

```bash
python3 scripts/jira_api.py boards --project PROJ
python3 scripts/jira_api.py sprints 42 --state active
python3 scripts/jira_api.py sprint-issues 123
```

# Using the Output

Both backends output structured content. When the user asks to "view" or "see" a ticket, run the `view` command and present the output. For search results, the output is a summary table — if the user wants more detail on a specific issue, follow up with `view`.

For write operations (create, edit, transition, comment), confirm success and show the issue key and URL.

## API Reference

For advanced use cases not covered by either backend, see `API_REFERENCE.md` in this skill directory for the full Jira REST API endpoint reference.

# Output Expectations

For every task, provide:

1. Commands executed (or planned) in code blocks
2. Short result summary (issue key, status, assignee, key metadata)
3. If a write operation succeeded, include the issue key and URL
4. If operation fails, include exact error and recommended fix
5. If images were downloaded and analyzed, include an **Image Evidence Summary** (source URL, what was observed, confidence/limits)

# Error Handling

## ACLI errors
- **Not logged in**: Run `acli jira auth login` (or `acli jira auth login --web` for OAuth).
- **Missing site**: Include `--site "yoursite.atlassian.net"` on login.
- **401 Unauthorized**: Session expired — re-run `acli jira auth login`.
- **403 Forbidden**: User lacks permission for this operation in the target project.
- **404 Not Found**: Issue key or project doesn't exist — verify the key format (e.g. `PROJ-123`).

## Python fallback errors
- **Missing ATLASSIAN_API_TOKEN**: The script reports the missing variable and how to set it.
- **Missing ATLASSIAN_BASE_URL**: The script suggests passing a full URL instead.
- **401 Unauthorized**: Token is invalid or expired — regenerate at https://id.atlassian.com/manage-profile/security/api-tokens
- **403 Forbidden**: User lacks permission for this operation in the target project.
- **404 Not Found**: Issue key or project doesn't exist — verify the key format (e.g. `PROJ-123`).
- **400 Bad Request**: Check field names, issue types, and transition IDs are valid for this project.
- **SSL: CERTIFICATE_VERIFY_FAILED**: Enterprise TLS inspection proxy interfering. Install `acli` for a permanent fix, or set `SSL_CERT_FILE` / `SSL_NO_VERIFY=1`.

## Common errors
- **Image download failed**: report URL + exact HTTP/auth error; retry with enterprise SSO (`curl --negotiate -u :`) when applicable.

# Notes

- **Prefer `acli`** — no SSL cert issues, simpler auth. Install with `brew install acli`.
- The Python script uses only Python standard library — no `pip install` needed.
- Python issue commands accept both `PROJ-123` and full Jira URLs (`https://.../browse/PROJ-123`).
- When the user pastes a Jira URL, pass it directly (Python fallback) or extract the key for acli.
- For destructive actions, confirm intent before executing.
