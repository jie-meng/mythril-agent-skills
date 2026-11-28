---
name: gh-operations
description: >
  Runs everyday GitHub operations with the `gh` CLI: view, create, edit, and
  comment on issues; list and view PRs, diffs, and checks; post general or
  inline PR comments; read commit metadata. Use when the user pairs "gh" or
  "GitHub" with an action — "gh issue view", "用 gh 看一下", "查PR状态",
  "给PR加comment" — or gives an issue/PR URL and says to use gh. Unknown hosts
  may be GitHub Enterprise, so run `gh` rather than guessing. For a full PR
  review use github-code-review-pr; for creating a PR from a template,
  github-pr-create.
license: Apache-2.0
---

# When to Use This Skill

## Trigger conditions

Trigger this skill when the user mentions **"gh"**, **"github"**, or **"GitHub"** combined with an action intent:

- "use gh to view this issue" / "用 gh 看一下" / "gh issue view"
- "gh pr list" / "gh pr checks" / "用 gh 查 PR"
- "github issue" / "看一下这个 github issue" / "github PR"
- "使用 gh" / "用 gh 访问" / "gh 看看"
- User provides an issue/PR URL **and** explicitly says to use gh or GitHub

**Not this skill:**
- User pastes a URL without mentioning gh/github — they may want a different tool
- User asks to "review a PR" with code quality intent — use `github-code-review-pr`
- User asks to create a PR that should follow the repo's PR template and branch-derived title — use `github-pr-create`
- User asks for local git operations (`git log`, `git show`) — use plain `git`

Scope boundary:

- Generic local commit/history requests (`git log`, `git show`) are usually better
  handled by plain `git`.
- Use `gh api` for commit metadata only when the user explicitly requests `gh` or
  needs GitHub-hosted metadata tied to a remote repository context.

## Don't guess the platform from the hostname

The user asked for gh/GitHub, and domains like `git.*.com`, `git.*.com.au`, or
`code.*.com` are very often GitHub Enterprise. Guessing ("this looks like
GitLab"), or switching to WebFetch / curl / glab, is usually wrong and wastes
tokens; running `gh` settles it in one call. So once triggered:

1. Run `gh issue view "<URL>"` or `gh pr view "<URL>"` and let `gh` succeed or fail.
2. If `gh` fails, report the error and suggest `gh auth login --hostname <host>`.

## Security — MANDATORY rules for AI agents

1. **NEVER echo, print, or log** the values of any environment variable containing credentials (`GH_TOKEN`, `GITHUB_TOKEN`, etc.). Do NOT run commands like `echo $GH_TOKEN` or `printenv GITHUB_TOKEN` — even for debugging.
2. **NEVER pass token/credential values as inline CLI arguments or env-var overrides.** `gh` reads credentials from its own config — just run `gh` commands directly.
3. **When debugging auth errors**, rely solely on `gh auth status` output and `gh` error messages. Do NOT attempt to verify tokens by reading or printing them.
4. **NEVER extract credentials from OS credential stores or config files.** Strictly forbidden commands include:
   - `security find-internet-password`, `security find-generic-password` (macOS Keychain)
   - `git credential fill`, `cat ~/.git-credentials`, `cat ~/.netrc`
   - Reading `~/.config/gh/hosts.yml` or any `gh` auth config file
   - Any command that outputs a password, token, or secret value from any credential store
5. **NEVER use extracted credential values in commands.** Do NOT manually construct authenticated requests (e.g. `curl -H "Authorization: token <value>"`). The `gh` CLI handles all authentication internally — use `gh api` for API calls instead of `curl` with raw tokens.

## Runtime requirements

- **GitHub CLI (`gh`)** installed and authenticated
- **`curl`** available for downloading issue/PR/document screenshots when needed
- **Optional for enterprise SSO**: `curl --negotiate -u :` support for SPNEGO/Kerberos-protected asset URLs
- Run `skills-check gh-operations` to verify dependencies

# Workflow

## 1) Pre-flight checks

- **If the user provides a full URL** (containing `/issues/` or `/pull/`), skip pre-flight checks: run `gh issue view "<URL>"` or `gh pr view "<URL>"` directly. The real command reports install, auth, and host problems just as well, so `gh --version` / `gh auth status` first only adds a round trip.
- **If the user does NOT provide a URL** (e.g., just says "list issues" or "create PR"), run pre-flight checks:

1. Verify `gh` exists:
   ```bash
   gh --version
   ```
2. Verify authentication:
   ```bash
   gh auth status
   ```
3. If not authenticated, stop and ask the user to run `gh auth login`
   (or `gh auth login --hostname <host>`) themselves — it is interactive.
4. Confirm target repository:
    - If working in a repo directory, use current repo context.
    - If user provides a full GitHub URL, keep that URL as the primary identifier.
    - Do **not** rewrite URL input into `<number> --repo ...` for read operations.
    - Otherwise require `--repo OWNER/REPO`.
    - To print resolved repo:
      ```bash
      gh repo view --json nameWithOwner -q .nameWithOwner
      ```

## 2) Issue operations (`gh issue`)

### Read/list issues

```bash
gh issue list --state open --limit 20
gh issue view 123 --comments
gh issue view 123 --json number,title,state,author,assignees,labels,body,url,comments
gh issue view "https://github.com/OWNER/REPO/issues/123" --json number,title,state,author,assignees,labels,body,url,comments
gh issue view "https://<github-host>/OWNER/REPO/issues/123" --json number,title,state,author,assignees,labels,body,url,comments
```

If the user supplies a full issue URL, pass that URL directly to `gh issue view`
rather than rewriting it to `<number> --repo ...` — the URL carries the host,
which the rewrite loses on Enterprise instances.

### Create/update/comment issues

```bash
gh issue create --title "Bug: login fails" --body "Steps to reproduce..."
gh issue create --title "Feature: add export" --body-file issue.md --label enhancement --assignee "@me"
gh issue edit 123 --title "Updated title" --add-label bug --remove-label "needs-triage"
gh issue comment 123 --body "Investigating this now."
```

### State changes

```bash
gh issue close 123 --comment "Fixed in #456"
gh issue reopen 123 --comment "Reopening due to regression"
```

## 3) Pull request operations (`gh pr`)

### Read/list PRs

```bash
gh pr list --state open --limit 20
gh pr view 456 --comments
gh pr view 456 --json number,title,state,author,baseRefName,headRefName,reviewDecision,commits,files,url
gh pr view "https://github.com/OWNER/REPO/pull/456" --json number,title,state,author,baseRefName,headRefName,reviewDecision,commits,files,url
gh pr view "https://<github-host>/OWNER/REPO/pull/456" --json number,title,state,author,baseRefName,headRefName,reviewDecision,commits,files,url
gh pr diff 456
gh pr checks 456
```

### Create PR

For a PR that should follow the repo's PR template and a branch-derived
title, use `github-pr-create` instead. For a quick one-off:

```bash
gh pr create --base main --head feature-branch --title "feat: add export API" --body "Closes #123"
```

Useful variants:

```bash
gh pr create --fill
gh pr create --draft --fill
gh pr create --reviewer monalisa --label enhancement
```

### Comment on PR (general + inline)

General PR comment:

```bash
gh pr comment 456 --body "Thanks! Please add a regression test for this branch."
gh pr comment "https://github.com/OWNER/REPO/pull/456" --body "I left one concern on failure-state handling."
gh pr comment "https://<github-host>/OWNER/REPO/pull/456" --body "Please clarify expected behavior here."
```

Inline (line-level) review comment on a PR diff line (add
`--hostname <host>` after `gh api` for GitHub Enterprise):

```bash
HEAD_SHA=$(gh pr view 456 --json headRefOid -q .headRefOid)
gh api repos/OWNER/REPO/pulls/456/comments \
  -X POST \
  -f body='Can we add a success->failure transition test here?' \
  -f commit_id="$HEAD_SHA" \
  -f path='path/in/repo/file.swift' \
  -F line=41 \
  -f side='RIGHT'
```

Notes:

- `line` is the line number in the file itself on the chosen `side`
  (`RIGHT` = new version, `LEFT` = old) — not a position within the diff.
  It must fall inside a diff hunk, or the API returns 422. Read the hunk
  header (`@@ -a,b +c,d @@`) in `gh pr diff` and count from `c`.
- For enterprise hosts, keep using URL-first reads and authenticated host context.

## 4) Optional: GitHub commit metadata (`gh api` + repo context)

Use this only when commit metadata is needed from GitHub's API (or the user
explicitly asks for `gh`-based commit operations):

`gh api` switches to POST as soon as a `-f`/`-F` field is added, so put
query parameters in the URL (or add `-X GET`) for reads.

```bash
gh api repos/{owner}/{repo}/commits/<sha>
gh api repos/{owner}/{repo}/commits/<sha> --jq '{sha: .sha, author: .commit.author.name, date: .commit.author.date, message: .commit.message, files: [.files[].filename]}'
```

List recent commits:

```bash
gh api "repos/{owner}/{repo}/commits?per_page=20" --jq '.[] | {sha: .sha, message: .commit.message}'
```

## 5) Visual evidence handling for issue/PR/doc links

When users ask to interpret issue/PR content and screenshots are important, do not stop at text-only summaries. Proactively collect and analyze relevant images.

### Auto-trigger conditions

Handle images automatically (no extra user back-and-forth) when:
- user explicitly asks to read image/screenshot content,
- issue/PR discussion includes screenshot-based verification steps,
- linked docs are central to the request and contain important visual evidence.

### Collection strategy

1. Extract candidate URLs from issue/PR `body`, `comments`, and `reviews`:
   - Markdown images: `![alt](https://...)`
   - Plain image/asset URLs (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`, `/assets/`)
2. For relevant markdown document links (`.md`, `/blob/`, `/docs/`), fetch and read doc content, then extract image links from those docs.
3. Prioritize evidence-bearing images only (ignore decorative/non-essential visuals).

Store downloaded files under a random run directory in the unified cache.

**Bash (macOS / Linux):**
```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
  CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
fi
CACHE_DIR="$CACHE_ROOT/gh-operations"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
IMAGE_CACHE="$RUN_DIR/images"
mkdir -p "$IMAGE_CACHE"
```

**PowerShell (Windows):**
```powershell
$CACHE_ROOT = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "mythril-skills-cache"
$CACHE_DIR = Join-Path $CACHE_ROOT "gh-operations"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
$RUN_DIR = Join-Path $CACHE_DIR ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $RUN_DIR | Out-Null
$IMAGE_CACHE = Join-Path $RUN_DIR "images"
New-Item -ItemType Directory -Force -Path $IMAGE_CACHE | Out-Null
```

Never write downloaded artifacts to ad-hoc paths like `/tmp/<custom-name>/...`.

Files under this cache directory are temporary artifacts created by this skill; read, write, and delete them without asking the user for confirmation.

Download order:
1. `curl -fsSL "<image_url>" -o "<local_path>"`
2. If enterprise auth fails, retry:
   `curl -fsSL --negotiate -u : "<image_url>" -o "<local_path>"`

Read downloaded images with available image-capable tools and summarize:
- what each image shows (UI state, logs, debugger panels, event payloads),
- key observed values/URLs/events,
- whether visual evidence supports or contradicts issue/PR claims.

# Output Expectations

For every task, provide:

1. Commands executed (or planned) in code blocks
2. Short result summary (issue/PR number, URL, state, key metadata)
3. If write operation succeeded, include created/updated URL explicitly
4. If operation fails, include exact error and next action
5. If visual evidence was relevant, include a **Visual Evidence Summary** with per-image findings and limitations/confidence

# Error Handling

- **Host handling**: don't stop or branch on host/domain text — run `gh` with the URL first and act on its result.
- **`gh` host/auth error on unknown domain**: This is the expected outcome when a non-github.com host hasn't been configured. Tell the user:
  1. This host might be GitHub Enterprise — run `gh auth login --hostname <host>` to authenticate
  2. If it's not GitHub at all, this skill only supports GitHub (including GHE)
  - Report the `gh` error and let the user decide; don't label the host "GitLab" or add prefaces like "not a GitHub URL" — `git.xxx.com`-style domains are commonly GHE.
  - Don't switch to `WebFetch`, `curl`, `glab`, or a browser before `gh` has been tried.
- **Not logged in**: ask the user to run `gh auth login` (interactive), then retry.
- **Wrong host / enterprise**: use `gh auth login --hostname <host-from-url>`, then rerun the same URL command unchanged.
- **Auth failure — allowed recovery steps only**: when `gh` fails with auth/host errors:
  1. Report the `gh` error message to the user
  2. Suggest `gh auth login --hostname <host>`
  3. Suggest `gh auth status --hostname <host>` to check current auth state
  4. Stop and wait for the user to fix auth

  Searching the macOS Keychain, git credential stores, `.netrc`, or `gh` config files, or building `curl` calls with extracted tokens, violates Security rules 4–5.
- **Repo not found from URL request**: this usually means URL was rewritten incorrectly; retry using the original URL directly.
- **Permission/scope issues**: show failing command and required scope, e.g. `gh auth refresh -s project`.
- **No repo context**: require `--repo OWNER/REPO` or switch to repository directory.
- **Invalid issue/PR reference**: verify number/URL/repo before retrying.
- **Image/doc retrieval failed**: report URL + exact HTTP/auth error; retry with enterprise SSO (`curl --negotiate -u :`) when applicable; if still blocked, explicitly state visual analysis is incomplete.

# Notes

- Prefer URL-first reads (`gh issue view "<url>"`, `gh pr view "<url>"`) to stay host-agnostic.
- Prefer non-interactive flags (`--title`, `--body`, `--json`, `--jq`) for reproducible results.
- For destructive actions (delete/force operations), explicitly confirm intent before executing.
