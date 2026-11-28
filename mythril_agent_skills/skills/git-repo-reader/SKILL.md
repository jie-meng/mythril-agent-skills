---
name: git-repo-reader
description: >
  Clones any git repository by URL (HTTPS or SSH, any host — GitHub, GitLab,
  Gitee, Bitbucket, self-hosted) into a shared local cache and reads its code,
  so later questions in this or future sessions reuse the clone. Use when the
  user shares a repo URL and asks about the code: "look at this repo", "how
  does this repo implement X", "analyze this repository", "看看这个仓库",
  "这个仓库怎么实现的". For reviewing a GitHub PR, use github-code-review-pr.
license: Apache-2.0
---

# Git Repo Reader

Clone, cache, and read any git repository for code exploration and analysis.

## Requirements

- **`git`** must be installed and available in PATH
- Run `skills-check git-repo-reader` to verify

## When to Use

- User shares a git repo URL (HTTPS or SSH) and asks about the code
- User wants to understand how a project implements something
- User asks to explore, read, or analyze a remote codebase
- The URL can be from **any** git hosting platform — GitHub, GitLab, Gitee, Bitbucket, Azure DevOps, self-hosted, etc.

## How It Works

`SKILL_PATH` is this skill's installed directory. This skill uses a helper script (`SKILL_PATH/scripts/repo_manager.py`) to handle all repo operations deterministically. The script manages a cache of cloned repos and a mapping file (`repo_map.json`) so repos persist across conversation sessions. The repo cache is shared with other skills (e.g., `github-code-review-pr`) — they use an identical copy of the same script, reading/writing the same cache directory.

All cached repos live under the unified cache directory:
- **macOS**: `~/Library/Caches/mythril-skills-cache/git-repo-cache/`
- **Linux**: `${XDG_CACHE_HOME:-~/.cache}/mythril-skills-cache/git-repo-cache/`
- **Windows**: `%LOCALAPPDATA%\mythril-skills-cache\git-repo-cache\`

The user can clean up all cached repos at any time via `skills-clean-cache`.

## Workflow

### Step 1: Parse the repo URL

Accept URLs in any of these formats:
- HTTPS: `https://github.com/owner/repo`, `https://github.com/owner/repo.git`
- SSH: `git@github.com:owner/repo.git`
- Any host: `https://gitlab.com/org/project`, `git@git.example.com:team/service.git`
- Browser URLs: `https://github.com/owner/repo/tree/main/src`, `https://gitlab.com/g/repo/-/blob/main/x` — trimmed to the repo

Pass the URL to the script as given: it keeps SSH URLs as SSH, clones everything else over HTTPS, drops credentials embedded in the URL, and rejects URLs whose path contains `.`/`..` or unusual characters.

### Step 2: Clone or reuse cached repo

Run the helper script to get the repo. The script handles everything: checking the mapping file, reusing existing clones, pulling latest code, or cloning fresh.

```bash
python3 SKILL_PATH/scripts/repo_manager.py clone "<repo-url>"
```

The script will:
1. Normalize the URL and compute a deterministic local path
2. Check `repo_map.json` for an existing entry
3. If found and the checkout is healthy → check out `--branch` if given, fetch and fast-forward to the remote, then return the path. If the refresh fails (offline, auth), it keeps the cached copy and warns that it may be stale — a network failure never deletes the cache
4. If found but the directory is missing or broken → remove the stale entry, clone fresh
5. If not found → clone the repo (blobless clone), add entry to `repo_map.json`
6. Print the local path to stdout on success

If the user asks for a specific branch:
```bash
python3 SKILL_PATH/scripts/repo_manager.py clone "<repo-url>" --branch dev
```

### Step 3: Read and analyze the code

Once you have the local path, explore the codebase freely — read files, search for patterns, understand the architecture. The repo is a normal local git checkout; use all your usual file-reading and search tools.

Start with an overview:
- Read `README.md`, `AGENTS.md`, or other top-level docs
- List the directory structure to understand project layout
- Then dive into the specific files the user asked about

Because the repo is cached locally, follow-up questions in the **same session** can directly access the files at the same path — no need to re-run the script.

For a **new session**, run the script again — it will find the cached repo, pull latest changes, and return the path. This ensures you always work with up-to-date code.

### Step 4: Post-completion notice

After answering the user's question, include a brief note like:

> This repo has been cached locally for reuse. If you want me to clean it up, just let me know.

When the user asks to clean up (e.g., "帮我清理", "clean up the repo", "删掉这个仓库"):
- **Always clean the specific repo** the user was just working with — don't run `skills-clean-cache` (that wipes all skills' caches, not just this repo).
- Use the `remove` command with the repo URL:

```bash
python3 SKILL_PATH/scripts/repo_manager.py remove "<repo-url>"
```

This deletes the cloned repo directory and removes its entry from `repo_map.json`, leaving other cached repos untouched.

## Script Reference

`SKILL_PATH/scripts/repo_manager.py` supports these subcommands:

| Command | Description |
|---|---|
| `clone <url> [--branch B]` | Clone or reuse a cached repo. Prints the local path. |
| `sync <url>` | Clone or refresh a repo, reset to clean default branch. Caller fetches specific branches as needed. |
| `lookup <url>` | Look up cached path for a URL without cloning. Prints path or exits 1. |
| `remove <url>` | Delete a cached repo and its mapping entry. |
| `list` | List all cached repos (URL → path). |
| `pull <url>` | Fetch and reset the current branch of a cached repo to its upstream. |

All commands print results to stdout and errors to stderr. Exit code 0 means success.

**How URLs are normalized**: The script strips `.git` suffixes, normalizes SSH URLs to a comparable form, and generates a deterministic directory structure: `<cache-root>/repos/<host>/<owner>/<repo>/`. This means `https://github.com/owner/repo`, `https://github.com/owner/repo.git`, and `git@github.com:owner/repo.git` all map to the same local directory.

## Error Handling

- **git not installed**: Print error, suggest `skills-check git-repo-reader`
- **Clone fails** (auth, network, invalid URL): Report the git error. For private repos, suggest the user configure credentials or SSH keys.
- **Refresh fails** on an existing cache: the script already falls back to the cached copy — tell the user the code may be stale. Don't delete the cache yourself.
- **`Unsafe path segment` / `Invalid host`**: the URL is malformed or crafted; ask the user for the plain repo URL.
- **Branch not found**: Report error, suggest checking available branches with `git branch -r`.

## Examples

### Example 1: Explore a public repo (Chinese)
**User**: "帮我看看 https://github.com/example-org/example-project 这个仓库是怎么实现打包功能的"
**Action**: Clone (or reuse cache) → read project structure → find packaging-related code → explain in Chinese

### Example 2: Analyze implementation (English)
**User**: "How does https://github.com/example-org/awesome-tool implement the plugin system?"
**Action**: Clone (or reuse cache) → read plugin-related files → explain the implementation flow

### Example 3: Specific branch
**User**: "看一下 https://git.example.com/team/backend-service 的 dev 分支有什么新功能"
**Action**: Clone with `--branch dev` → explore recent changes → summarize new features

### Example 4: Follow-up question (same session)
**User**: "刚才那个仓库里有没有用到什么测试框架？"
**Action**: Repo is already cached and path is known → directly search for test files → answer

### Example 5: Clean up
**User**: "帮我清理一下刚才下载的仓库"
**Action**: Run `repo_manager.py remove <url>` → delete the specific repo and its mapping entry → confirm to user
