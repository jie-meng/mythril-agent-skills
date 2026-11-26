---
name: github-pr-create
description: >
  Creates GitHub Pull Requests with the `gh` CLI: pushes the branch if needed,
  fills the repo's PR template from the actual changes, and derives a
  conventional title from the branch name. Use when the user says "create PR",
  "open PR", "提PR", "创建PR", "帮我提个PR", or "push and create PR". Unknown hosts
  may be GitHub Enterprise, so run `gh` rather than guessing the platform. For
  reviewing PRs use github-code-review-pr; for viewing/listing, gh-operations.
license: Apache-2.0
---

# When to Use This Skill

## Don't guess the platform from the hostname

Hosts like `git.company.com` are very often GitHub Enterprise. Guessing ("this
looks like GitLab", "gh won't work with this host") is usually wrong and wastes
tokens, while running `gh` settles it in one call. So once triggered:

1. Run the `gh` commands below and let `gh` succeed or fail.
2. If `gh` fails, report the error and suggest `gh auth login --hostname <host>`.

## Trigger conditions

Trigger this skill when the user wants to **create a Pull Request**:

- "create PR" / "create a PR" / "create pull request"
- "提PR" / "创建PR" / "开PR" / "提交PR" / "发PR"
- "帮我提个PR" / "PR提一下" / "提一下PR"
- "gh pr create" / "submit PR" / "open PR"
- "push and create PR" / "push + PR"
- "create PR to main" / "create PR from this branch"

**Not this skill:**
- User asks to "review a PR" — use `github-code-review-pr`
- User asks to "view PR" or "list PRs" — use `gh-operations`
- User asks for local git operations — use plain `git`

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
- **`git`** CLI installed
- Must be inside a git repository with a remote pointing to GitHub (or GitHub Enterprise)
- Run `skills-check github-pr-create` to verify dependencies

# Implementation

## Step 1: Pre-flight Validation

### 1a. Verify current branch is NOT the main/default branch

A PR from the default branch into itself is meaningless and pushing there could publish unreviewed commits, so this check blocks the rest of the flow.

```bash
# Detect default branch
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD --short 2>/dev/null | sed 's|origin/||')
if [ -z "$DEFAULT_BRANCH" ]; then
  DEFAULT_BRANCH=$(git remote show origin 2>/dev/null | grep 'HEAD branch' | awk '{print $NF}')
fi
if [ -z "$DEFAULT_BRANCH" ]; then
  DEFAULT_BRANCH="main"
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "$CURRENT_BRANCH" = "$DEFAULT_BRANCH" ]; then
  echo "ERROR: You are on the default branch ($DEFAULT_BRANCH). Cannot create a PR from the default branch."
  echo "Please switch to a feature branch first."
  exit 1
fi
```

If the user is on the default branch, **stop immediately** and tell them they need to be on a feature/topic branch.

### 1b. Check for unpushed commits

```bash
git status
git log origin/$CURRENT_BRANCH..HEAD --oneline 2>/dev/null
```

If there are unpushed commits, push the branch before creating the PR:

```bash
git push -u origin "$CURRENT_BRANCH"
```

If the remote branch does not exist yet, `git push -u origin HEAD` will create it.

### 1c. Determine the base branch (merge target)

- If the user explicitly specifies a target branch (e.g., "create PR to develop"), use that branch.
- Otherwise, use the detected default branch (`$DEFAULT_BRANCH`).

## Step 2: Gather PR Context

### 2a. Collect commit information

```bash
git log origin/$DEFAULT_BRANCH..HEAD --pretty=format:"%h %s" --no-merges
```

This shows all commits that will be included in the PR.

### 2b. Collect diff summary

```bash
git diff origin/$DEFAULT_BRANCH..HEAD --stat
```

### 2c. Read full diff for PR body generation

```bash
git diff origin/$DEFAULT_BRANCH..HEAD
```

Use this to understand the actual code changes for filling in the PR template.

## Step 3: Detect and Load PR Template

### Detect with the bundled script

`SKILL_PATH` is this skill's installed directory. The script handles the
multi-template directory case and encodes content safely, so prefer it over
checking paths by hand:

```bash
python3 SKILL_PATH/scripts/detect_pr_template.py
```

If `SKILL_PATH` cannot be resolved, check these fixed install paths in order and
use the first that exists (no recursive search of `~`):

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/github-pr-create/scripts/detect_pr_template.py",
    pathlib.Path.home() / ".claude/skills/github-pr-create/scripts/detect_pr_template.py",
    pathlib.Path.home() / ".copilot/skills/github-pr-create/scripts/detect_pr_template.py",
    pathlib.Path.home() / ".cursor/skills/github-pr-create/scripts/detect_pr_template.py",
    pathlib.Path.home() / ".gemini/skills/github-pr-create/scripts/detect_pr_template.py",
    pathlib.Path.home() / ".codex/skills/github-pr-create/scripts/detect_pr_template.py",
    pathlib.Path.home() / ".qwen/skills/github-pr-create/scripts/detect_pr_template.py",
    pathlib.Path.home() / ".grok/skills/github-pr-create/scripts/detect_pr_template.py",
]
script = next((p for p in candidates if p.exists()), None)
```

The script checks these locations (in order) for PR templates:
1. `.github/pull_request_template.md`
2. `.github/PULL_REQUEST_TEMPLATE.md`
3. `pull_request_template.md`
4. `PULL_REQUEST_TEMPLATE.md`
5. `.github/PULL_REQUEST_TEMPLATE/` directory (multiple templates)
6. `docs/pull_request_template.md`

Machine-readable output:
- `TEMPLATE_FOUND=true|false`
- `TEMPLATE_PATH=<path>` — relative path to the template file
- `TEMPLATE_CONTENT=<base64>` — base64-encoded template content
- `MULTIPLE_TEMPLATES=true|false` — whether multiple templates exist
- `TEMPLATE_NAMES=<comma-separated>` — names of available templates (when multiple)

### Fallback: Manual template detection

If the script is not found, check template paths manually:

```bash
for f in .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md pull_request_template.md PULL_REQUEST_TEMPLATE.md docs/pull_request_template.md; do
  if [ -f "$f" ]; then
    echo "TEMPLATE_FOUND=true"
    echo "TEMPLATE_PATH=$f"
    break
  fi
done
```

## Step 4: Fill PR Title and Body

### 4a. Generate PR title

The PR title follows the same format as commit messages, so PR titles and
commit messages stay consistent. The full rules are in
[`references/commit-format.md`](references/commit-format.md) (shared with
`code-review-staged`); read it for long-title compression details. Summary:

- Format: `<type>[scope]: <subject>` — single line, max 72 characters
- `<type>` from branch prefix: `feat/` → `feat`, `fix/` → `fix`, etc.
- `[scope]` auto-derived from branch name:
  - `<type>/<JIRA>/<Title>` → scope = JIRA key (e.g. `feat[XYZ-123]: add export endpoint`)
  - `<type>/<Title>` with title ≤ 30 chars → scope = lowercase-hyphenated title
  - `<type>/<Title>` with title > 30 chars → compress: drop filler verbs/connectives (add, update, the, for, with…), keep the first 2–3 meaningful words, aim for ≤ 30 chars, keep any `-vN`
  - `-iter-N` is stripped from scope; `-vN` is kept
  - Bare branches (master/main/dev) → no scope, use `type: subject`
- `<subject>`: imperative mood, lowercase first letter, no period, English
- Never use the repo name as scope — repo identity is already in the PR metadata

When the PR has multiple commits, use the same scope (derived from
the branch name) and write a subject that summarizes the whole PR's
intent.

Examples:

- Branch `feat/XYZ-123/Add-Export` → PR title `feat[XYZ-123]: add CSV and JSON export endpoints`
- Branch `feat/Dark-Mode-Toggle` → PR title `feat[dark-mode-toggle]: add theme switcher in settings`
- Branch `feat/Dark-Mode-Toggle-v2` → PR title `feat[dark-mode-toggle-v2]: add follow-system option`
- Branch `master` → PR title `chore: bump version to 1.2.0` (no scope)

### 4b. Fill PR body

**If a PR template was found (Step 3):**

Fill the template with information from the code changes:

1. **Sections you CAN fill automatically** — fill them based on the diff and commit messages:
   - Summary / Description / What — describe what the PR does based on actual code changes
   - Changes / What changed — list the key changes
   - Type of change — check the appropriate checkbox based on the nature of changes (bug fix, feature, refactor, etc.)
   - Testing / How to test — describe what was tested if evident from the diff (e.g., new test files added)

2. **Sections to leave alone unless you actually have the information** (a wrong link or invented test claim is worse than a placeholder):
   - Screenshots / Screen recordings — leave as-is (AI cannot capture screenshots)
   - Jira ticket / Issue link — only fill if the user provided it, or if the branch name contains a ticket ID (e.g., `feat/XYZ-123/...`)
   - Tech doc / Design doc links — only fill if the user provided them
   - Reviewer checklist — leave as-is for the reviewer
   - Any placeholder with `[link]`, `[url]`, `[screenshot]` — leave the placeholder text as-is

3. **When in doubt, preserve the template's original text.** The user can edit it on the web afterwards. It is better to leave a placeholder than to fill in incorrect information.

**If no PR template was found:**

Generate a reasonable PR body:

```markdown
## Summary

<concise description of changes based on diff>

## Changes

- <change 1>
- <change 2>
- ...
```

### 4c. Language matching

Match the PR body language to the template language if a template is used. If no template, match the user's input language.

## Step 5: Create the PR

### Using `gh pr create`

```bash
gh pr create \
  --base "$BASE_BRANCH" \
  --head "$CURRENT_BRANCH" \
  --title "$PR_TITLE" \
  --body "$PR_BODY"
```

**Additional options based on user request:**
- `--draft` — if user wants a draft PR
- `--reviewer <user>` — if user specifies reviewers
- `--label <label>` — if user specifies labels
- `--assignee @me` — if user wants to self-assign

**For GitHub Enterprise (custom host):**

`gh` auto-detects the host from the git remote — no special handling needed. If auth fails, suggest:
```bash
gh auth login --hostname <host>
```

## Step 6: Output Result

On success, output the PR URL clearly:

```
PR created successfully: https://github.com/owner/repo/pull/123
```

The PR URL is the most important output — make sure the user can see it and click on it.

On failure, report the error and suggest fixes:
- Auth failure → `gh auth login`
- Branch not pushed → `git push -u origin HEAD`
- No commits → explain that there are no changes to create a PR for

# Error Handling

- **Host handling**: don't stop or branch on host/domain text — run `gh` directly and act on its result.
- **`gh` host/auth error on unknown domain**: Tell the user:
  1. This host might be GitHub Enterprise — run `gh auth login --hostname <host>` to authenticate
  2. If it's not GitHub at all, this skill only supports GitHub (including GHE)
  - Don't label the host "GitLab" or any other platform.
- **On default branch**: Report clearly that PRs cannot be created from the default branch.
- **No remote**: Suggest `git remote add origin <url>` or verify the remote is set up.
- **Merge conflicts with base**: Warn the user about potential conflicts but still create the PR. GitHub will show conflict status.
- **Auth failure — allowed recovery steps only**:
  1. Report the `gh` error message to the user
  2. Suggest `gh auth login --hostname <host>`
  3. Suggest `gh auth status --hostname <host>` to check current auth state
  4. Stop and wait for the user to fix auth

  Searching the macOS Keychain, git credential stores, `.netrc`, or any other credential storage violates the Security rules above.

# Examples

### Example 1: Simple PR creation (English)
**User input**: "Create a PR"
**Action**: Check branch → push if needed → detect template → fill body → `gh pr create` → output URL
**Output**: `PR created successfully: https://github.com/owner/repo/pull/42`

### Example 2: PR with target branch (Chinese)
**User input**: "帮我提个PR到develop分支"
**Action**: Check branch → push → use `develop` as base → fill body in Chinese → create PR
**Output**: `PR 创建成功: https://github.com/owner/repo/pull/43`

### Example 3: Draft PR with reviewer
**User input**: "Create a draft PR and add @alice as reviewer"
**Action**: Push → fill body → `gh pr create --draft --reviewer alice`
**Output**: `Draft PR created: https://github.com/owner/repo/pull/44`

### Example 4: PR with Jira context
**User input**: "Create a PR, the Jira ticket is PROJ-456"
**Action**: Push → fill template with Jira link → create PR
**Output**: `PR created successfully: https://github.com/owner/repo/pull/45`

### Example 5: GitHub Enterprise
**User input**: "帮我在 git.mycompany.com 提个PR"
**Action**: Run `gh pr create` directly → if auth error, suggest `gh auth login --hostname git.mycompany.com`
**Not**: saying "this might not be GitHub" before trying `gh`.
