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

**ALWAYS detect the backend before every operation:**

```bash
which acli 2>/dev/null && acli jira auth status 2>/dev/null && echo "ACLI_OK" || echo "FALLBACK"
```

- Output contains `ACLI_OK` → use **`acli`** (see `ACLI.md` for command reference)
- Otherwise → use **Python fallback** (see `PYTHON.md` for command reference)

If `acli` is installed but `acli jira auth status` fails, tell the user: "acli is installed but not logged in. Run `acli jira auth login` to authenticate, or set ATLASSIAN_API_TOKEN for Python fallback."

# Security — MANDATORY rules for AI agents

1. **NEVER echo, print, or log** the values of `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL`, `JIRA_BASE_URL`, `CONFLUENCE_BASE_URL`, or any other environment variable.
2. **NEVER pass token/credential values as inline CLI arguments** (e.g. `echo "token" | acli jira auth login ...`). Use a file or prompt the user to authenticate themselves.
3. **When debugging auth errors**, rely solely on error messages. Do NOT attempt to verify tokens by reading or printing them.
4. **Do NOT read environment variable values** using shell commands or programmatic access.
5. **NEVER extract credentials from OS credential stores or config files.** Strictly forbidden: `security find-internet-password`, `git credential fill`, `cat ~/.git-credentials`, `cat ~/.netrc`, or any command that outputs a password, token, or secret value.
6. **NEVER use extracted credential values in commands.** Do NOT manually construct authenticated requests. `acli` handles auth internally; the Python script reads from environment internally.

# Workflow

1. Detect backend (above)
2. Determine the operation (view, search, create, transition, etc.)
3. Run the appropriate command from `ACLI.md` or `PYTHON.md`
4. Present the output to the user
5. For write operations, confirm success and show the resulting URL

# Image Handling

When issue descriptions or comments contain screenshots or image links, retrieve and analyze them.

Detect: `![alt](url)`, plain URLs ending in `.png/.jpg/.jpeg/.gif/.webp/.svg`, `/attachments/` paths.

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

**Automatic access**: Files under the cache directory are skill-managed temporary artifacts. Read, write, and delete them without asking for confirmation.

Retrieve with `curl -fsSL`; if enterprise auth fails, retry with `curl -fsSL --negotiate -u :`.

Analyze images with available image-capable tools and summarize evidence relevant to the user task.

# Output Expectations

For every task, provide:

1. Commands executed (or planned) in code blocks
2. Short result summary (issue key, status, assignee, key metadata)
3. If a write operation succeeded, include the issue key and URL
4. If operation fails, include exact error and recommended fix
5. If images were downloaded and analyzed, include an **Image Evidence Summary** (source URL, what was observed, confidence/limits)

# Error Handling

## ACLI errors
- **Not logged in**: Run `acli jira auth login` (or `acli jira auth login --web` for OAuth)
- **Missing site**: Include `--site "yoursite.atlassian.net"` on login
- **401 Unauthorized**: Session expired — re-run `acli jira auth login`
- **403 Forbidden**: User lacks permission for this operation
- **404 Not Found**: Issue key or project doesn't exist

## Python fallback errors
- **Missing ATLASSIAN_API_TOKEN**: The script reports the missing variable and how to set it
- **Missing ATLASSIAN_BASE_URL**: The script suggests passing a full URL instead
- **401 Unauthorized**: Token is invalid or expired — regenerate at https://id.atlassian.com/manage-profile/security/api-tokens
- **403 Forbidden**: User lacks permission for this operation
- **404 Not Found**: Issue key or project doesn't exist
- **400 Bad Request**: Check field names, issue types, and transition IDs
- **SSL: CERTIFICATE_VERIFY_FAILED**: Enterprise TLS inspection proxy interfering. Install `acli` for a permanent fix, or set `SSL_CERT_FILE` / `SSL_NO_VERIFY=1`

## Common errors
- **Image download failed**: report URL + exact HTTP/auth error; retry with enterprise SSO (`curl --negotiate -u :`)

# Notes

- **Prefer `acli`** — no SSL cert issues, simpler auth. Install with `brew install acli`
- Python script uses only Python standard library — no `pip install` needed
- Python issue commands accept both `PROJ-123` and full Jira URLs (`https://.../browse/PROJ-123`)
- For destructive actions, confirm intent before executing
- For advanced use cases not covered by either backend, see `API_REFERENCE.md`
