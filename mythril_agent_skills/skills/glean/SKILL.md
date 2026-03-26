---
name: glean
description: >
  Use Glean CLI (`glean`) for enterprise knowledge search, AI chat, and API
  operations from terminal. Trigger when user mentions "glean" combined with
  an action — e.g. "glean search", "search glean", "ask glean", "glean chat",
  "用 glean 搜", "glean 搜索", "问一下 glean", "glean 问答", "search company
  knowledge", "搜公司知识库", "公司文档搜索", "glean api", "glean agents",
  "glean documents", "glean shortcuts", "glean collections". Also trigger
  when user asks to search company/internal knowledge, docs, or people and
  Glean is the implied tool. This skill covers search, chat, AI agents,
  documents, collections, shortcuts, pins, announcements, entities,
  verification, insights, messages, activity, and raw API access.
license: MIT
---

# When to Use This Skill

## Trigger conditions

Trigger this skill when the user mentions **"glean"** combined with an action intent:

- "glean search vacation policy" / "用 glean 搜一下请假规定"
- "glean chat summarize Q1 goals" / "问一下 glean 季度目标"
- "search company docs" / "搜公司知识库" / "搜内部文档"
- "glean agents list" / "glean documents get"
- "glean shortcuts create" / "create a go-link"
- "glean api" / "look up people in glean" / "glean 查人"

**NOT a trigger** (do NOT invoke this skill):
- Generic web search not targeting company knowledge
- User asks to search GitHub issues/PRs — use `gh-operations`
- User asks to search Confluence — use `confluence` skill

## Security — MANDATORY rules for AI agents

1. **NEVER echo, print, or log** the values of any environment variable containing credentials (`GLEAN_API_TOKEN`, etc.). Do NOT run commands like `echo $GLEAN_API_TOKEN` or `printenv GLEAN_API_TOKEN` — even for debugging.
2. **NEVER pass token/credential values as inline CLI arguments or env-var overrides.** `glean` reads credentials from its own config or environment — just run `glean` commands directly.
3. **NEVER read environment variable values** using shell commands or programmatic access. The AI agent should not inspect, verify, or access token values in any way.
4. **When debugging auth errors**, rely solely on `glean auth status` output and `glean` error messages. Do NOT attempt to verify tokens by reading or printing them.
5. **NEVER extract credentials from OS credential stores or config files.** Strictly forbidden commands include:
   - macOS Keychain: `security find-internet-password`, `security find-generic-password`
   - Reading `~/.glean/config.json` or any `glean` auth config file
   - Any command that outputs a password, token, or secret value from any credential store
6. **NEVER use extracted credential values in commands.** The `glean` CLI handles all authentication internally — use `glean api` for API calls instead of `curl` with raw tokens.

## Runtime requirements

- **Glean CLI (`glean`)** installed and authenticated
- Run `skills-check glean` to verify dependencies

# Workflow

## 1) Pre-flight checks

MANDATORY execution rule:
- **If the user provides a clear glean action** (e.g., "glean search X"), go straight to the relevant operation. Do NOT run `glean --version` or `glean auth status` first — let the command succeed or fail.
- **If running glean for the first time** or encountering auth errors, check:

1. Verify `glean` exists:
   ```bash
   glean --version
   ```
2. Verify authentication:
   ```bash
   glean auth status
   ```
3. If not authenticated:
   ```bash
   glean auth login    # OAuth via browser (recommended)
   ```
4. For CI/CD environments, credentials are set via environment variables:
   - `GLEAN_API_TOKEN` — API token
   - `GLEAN_HOST` — Glean backend hostname (e.g. `your-company-be.glean.com`)

## 2) Search (`glean search`)

Search across company knowledge:

```bash
glean search "vacation policy"
glean search "Q1 planning" --datasource confluence --page-size 5
glean search "docs" --output ndjson | jq .title
glean search "onboarding" --fields "results.document.title,results.document.url"
glean search --json '{"query":"onboarding","pageSize":3}'
glean search --dry-run "test"
```

| Flag | Description |
|---|---|
| `--output` / `--format` | `json` (default), `ndjson` (one result per line), `text` |
| `--fields` | Dot-path field projection — prefix paths with `results.` |
| `--datasource` / `-d` | Filter by datasource (repeatable) |
| `--type` / `-t` | Filter by document type (repeatable) |
| `--page-size` | Results per page (default 10) |
| `--json` | Raw SDK request body (overrides all flags) |
| `--dry-run` | Print request body without sending |

## 3) Chat (`glean chat`)

Chat with Glean Assistant (non-interactive):

```bash
glean chat "What are our company holidays?"
glean chat --timeout 120000 "Summarize all Q1 OKRs across teams"
glean chat --json '{"messages":[{"author":"USER","messageType":"CONTENT","fragments":[{"text":"What is Glean?"}]}]}'
echo "What is Glean?" | glean chat
glean chat    # interactive multiline input, Ctrl+D to send
```

| Flag | Description |
|---|---|
| `--timeout` | Request timeout in milliseconds (default 60000) |
| `--json` | Raw SDK request body (overrides all flags) |
| `--dry-run` | Print request body without sending |
| `--save` | Persist chat for continuation (default true) |

## 4) Schema introspection (`glean schema`)

Discover commands and flags programmatically:

```bash
glean schema | jq '.commands'
glean schema search | jq '.flags | keys'
glean schema search | jq '.flags["--output"]'
```

## 5) AI Agents (`glean agents`)

```bash
glean agents list | jq '.agents[] | {id: .agent_id, name: .name}'
glean agents get --json '{"agentId":"<id>"}'
glean agents schemas --json '{"agentId":"<id>"}'
glean agents run --json '{"agentId":"<id>","messages":[{"author":"USER","fragments":[{"text":"summarize Q1 results"}]}]}'
```

## 6) Documents (`glean documents`)

```bash
glean documents get --json '{"documentSpecs":[{"url":"https://..."}]}'
glean documents summarize --json '{"documentSpecs":[{"url":"https://..."}]}'
```

## 7) Collections (`glean collections`)

```bash
glean collections list
glean collections get --json '{"id":"<collection-id>"}'
glean collections create --json '{"name":"My Collection","description":"..."}'
glean collections add-items --json '{"id":"<collection-id>","addedDocumentSpecs":[{"url":"https://..."}]}'
```

## 8) Shortcuts / go-links (`glean shortcuts`)

```bash
glean shortcuts list
glean shortcuts create --json '{"data":{"inputAlias":"onboarding","destinationUrl":"https://..."}}'
glean shortcuts create --json '{"data":{"inputAlias":"jira","urlTemplate":"https://jira.example.com/browse/{arg}"}}'
```

## 9) Other namespace commands

All namespace commands accept `--json`, `--output`, and `--dry-run`.

| Namespace | Subcommands | Description |
|---|---|---|
| `glean answers` | `list`, `get`, `create`, `update`, `delete` | Curated Q&A pairs |
| `glean announcements` | `create`, `update`, `delete` | Company announcements |
| `glean pins` | `list`, `get`, `create`, `update`, `remove` | Promoted search results |
| `glean entities` | `list`, `read-people` | People, teams, custom entities |
| `glean verification` | `list`, `verify`, `remind` | Document verification |
| `glean insights` | `get` | Search and usage analytics |
| `glean messages` | `get` | Indexed messages (Slack, Teams) |
| `glean activity` | `report`, `feedback` | User activity reporting |
| `glean tools` | `list`, `run` | Platform tools |

## 10) Raw API access (`glean api`)

```bash
glean api search --method POST --raw-field '{"query":"rust","pageSize":3}'
glean api --preview search --method POST --raw-field '{"query":"test"}'
```

## 11) Interactive TUI

Running `glean` with no arguments opens a full-screen chat:

```bash
glean            # open TUI
glean --continue # resume the most recent session
```

# Output Expectations

For every task, provide:

1. Commands executed (or planned) in code blocks
2. Short result summary
3. If write operation succeeded, include the result explicitly
4. If operation fails, include exact error and next action

All `glean` commands return structured JSON on stdout and errors on stderr. Use `jq` for parsing. Use `--dry-run` to preview requests before sending.

# Error Handling

- **`glean` not installed**: Tell user to install via `brew install gleanwork/tap/glean-cli` or the install script. Run `skills-check glean` to verify.
- **Not authenticated**: Run `glean auth login` (OAuth via browser). For CI/CD, set `GLEAN_API_TOKEN` and `GLEAN_HOST` environment variables.
- **Auth failure — ONLY allowed recovery steps**:
  1. Report the `glean` error message to the user
  2. Suggest `glean auth login` or `glean auth status`
  3. For token-based auth, suggest checking `GLEAN_API_TOKEN` and `GLEAN_HOST` are set
  4. Stop and wait for the user to fix auth
- **API errors**: Report status code and error body. Use `--dry-run` to debug request shape.
- **Unknown command**: Use `glean schema` to discover available commands and flags.

# Notes

- Every command returns JSON — pipe to `jq` for field extraction.
- Use `--dry-run` to preview requests before sending.
- Use `glean schema <command>` for machine-readable flag documentation.
- Use `--output ndjson` for streaming large result sets.
- The interactive TUI (`glean` with no args) is for human-interactive sessions; prefer `glean chat "..."` or `glean search "..."` for agent workflows.
