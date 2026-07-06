# Python Fallback Command Reference

Bundled script: `scripts/jira_api.py`. Python 3.10+ standard library only (zero pip dependencies).

## Prerequisites

- `ATLASSIAN_API_TOKEN` (**required**) — API token or Personal Access Token
- `ATLASSIAN_USER_EMAIL` (**required for Jira Cloud**) — Atlassian account email, used for Basic auth
- `JIRA_BASE_URL` (optional — takes precedence) — e.g. `https://jira.yourcompany.com`
- `ATLASSIAN_BASE_URL` (optional — shared fallback) — e.g. `https://yoursite.atlassian.net`

Base URL resolution: `JIRA_BASE_URL` > `ATLASSIAN_BASE_URL`. When neither is set, issue commands accept a full Jira URL. For commands without a specific issue (search, create, boards, sprints, myself), a base URL is required.

If Confluence and Jira share the same base URL, set only `ATLASSIAN_BASE_URL`. If they differ, set `JIRA_BASE_URL` for Jira and `CONFLUENCE_BASE_URL` for Confluence.

**SSL cert issues**: Supports `SSL_CERT_FILE` / `CURL_CA_BUNDLE` / `REQUESTS_CA_BUNDLE` for custom CA bundles, and `SSL_NO_VERIFY=1` as last resort. For a permanent fix, install `acli`.

## Runtime requirements

- Python 3.10+
- `curl` for downloading linked screenshots/images

## Common JQL patterns

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

## View an issue

Accepts an issue key or a full Jira URL:

```bash
python3 scripts/jira_api.py view PROJ-123
python3 scripts/jira_api.py view "https://yoursite.atlassian.net/browse/PROJ-123"
```

When the user pastes a Jira URL, pass it directly — the script parses out the base URL and issue key.

## Search issues via JQL

```bash
python3 scripts/jira_api.py search "project=PROJ AND status='In Progress'"
python3 scripts/jira_api.py search "assignee=currentUser() AND status!=Done" --max-results 30
python3 scripts/jira_api.py search "project=PROJ AND created >= -7d ORDER BY created DESC"
```

## Create an issue

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

## Edit an issue

```bash
python3 scripts/jira_api.py edit PROJ-123 --summary "Updated summary" --priority High
python3 scripts/jira_api.py edit "https://yoursite.atlassian.net/browse/PROJ-123" --labels urgent backend
```

## Assign an issue

```bash
python3 scripts/jira_api.py assign PROJ-123 5b10ac8d82e05b22cc7d4ef5
python3 scripts/jira_api.py assign PROJ-123 none    # unassign
```

## Transition (move) an issue

Two-step: list available transitions, then apply one.

```bash
python3 scripts/jira_api.py transitions PROJ-123
python3 scripts/jira_api.py transition PROJ-123 31
python3 scripts/jira_api.py transition PROJ-123 31 --comment "Starting work on this"
python3 scripts/jira_api.py transition PROJ-123 41 --resolution Fixed
```

## Comment on an issue

```bash
python3 scripts/jira_api.py comment PROJ-123 "Investigating the root cause now."
```

## List comments

```bash
python3 scripts/jira_api.py comments PROJ-123
python3 scripts/jira_api.py comments PROJ-123 --max-results 5
```

## Link two issues

```bash
python3 scripts/jira_api.py link PROJ-123 PROJ-456 Blocks
```

## Current user info

```bash
python3 scripts/jira_api.py myself
```

## List boards / sprints / sprint issues

```bash
python3 scripts/jira_api.py boards --project PROJ
python3 scripts/jira_api.py sprints 42 --state active
python3 scripts/jira_api.py sprint-issues 123
```
