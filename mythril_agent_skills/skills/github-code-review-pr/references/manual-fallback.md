# Manual Fallback (no review_runner.py)

Use this file only when `review_runner.py` cannot be run — for example the
skill's `scripts/` directory is missing or `SKILL_PATH` cannot be resolved.
When the runner works, it already performs everything below (fetch, path
selection, checkout, cleanup wiring); running these steps as well would fetch
twice and break the gate's single-fetch check.

## Contents

- [Locating the scripts without SKILL_PATH](#locating-the-scripts-without-skill_path)
- [Step 2 (manual): fetch metadata and diff](#step-2-manual-fetch-metadata-and-diff)
- [Step 3 (manual): path selection](#step-3-manual-path-selection)
- [Execution guardrail](#execution-guardrail)
- [Path A: already inside the target repo](#path-a-already-inside-the-target-repo)
- [Path B: shared repo cache hit](#path-b-shared-repo-cache-hit)
- [Path C: clone into shared cache](#path-c-clone-into-shared-cache)
- [Path D: blobless sparse clone to temp directory](#path-d-blobless-sparse-clone-to-temp-directory)
- [Path selection summary](#path-selection-summary)
- [Manual cleanup](#manual-cleanup)

## Locating the scripts without SKILL_PATH

Check these fixed install paths in order and use the first that exists. Do not
use Glob, `find`, `rg`, or any recursive search of `~` — recursive home-dir
scans trigger permission prompts and are slow. This works on macOS, Linux, and
Windows:

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/github-code-review-pr/scripts/review_runner.py",
    pathlib.Path.home() / ".claude/skills/github-code-review-pr/scripts/review_runner.py",
    pathlib.Path.home() / ".copilot/skills/github-code-review-pr/scripts/review_runner.py",
    pathlib.Path.home() / ".cursor/skills/github-code-review-pr/scripts/review_runner.py",
    pathlib.Path.home() / ".gemini/skills/github-code-review-pr/scripts/review_runner.py",
    pathlib.Path.home() / ".codex/skills/github-code-review-pr/scripts/review_runner.py",
    pathlib.Path.home() / ".qwen/skills/github-code-review-pr/scripts/review_runner.py",
    pathlib.Path.home() / ".grok/skills/github-code-review-pr/scripts/review_runner.py",
]
script = next((p for p in candidates if p.exists()), None)
if not script:
    print("ERROR: review_runner.py not found at any known install path", file=sys.stderr)
    sys.exit(1)
subprocess.run([sys.executable, str(script), "prepare", "<URL_or_NUMBER>"])
```

If you run shell commands instead of Python, convert this to equivalent
`ls` / `test -f` checks. If the runner is found this way, go back to SKILL.md
and use it — the rest of this file applies only when it is truly unavailable.

## Step 2 (manual): fetch metadata and diff

You still have to run `path_select.py` before any clone or fetch (see Step 3
below).

### 2a. PR metadata

```bash
GH_PAGER=cat gh pr view <URL_or_NUMBER> --json number,title,body,state,author,baseRefName,headRefName,labels,reviewDecision,additions,deletions,changedFiles,commits,files,comments,reviews,url,headRefOid,isCrossRepository
```

Key fields:
- `title`, `body` — PR description and intent
- `baseRefName`, `headRefName` — branches involved
- `files` — list of changed files with `path`, `additions`, `deletions`
- `commits` — commit history in the PR
- `comments`, `reviews` — existing discussion context
- `url` — used to extract `owner/repo`

### 2b. PR diff

```bash
GH_PAGER=cat gh pr diff <URL_or_NUMBER>
```

### 2b.1 Single-fetch rule (avoid repeated network calls)

- Fetch metadata and diff once, then reuse the captured output throughout the
  review.
- Do not re-run `gh pr diff` / `gh pr view` unless the output is missing or
  corrupted, or the PR head changed during the review.
- Persist the first successful outputs to files (for example
  `PR_VIEW_JSON_PATH`, `PR_DIFF_PATH`) and reuse them for all later analysis.
- Any second `gh pr view` / `gh pr diff` call must be preceded by a log line:
  `[REFETCH-REASON] <specific reason>`. "Need to read another section" is not
  a valid reason — read from the captured output instead.

## Step 3 (manual): path selection

The goal is repo context available locally, so context gathering is plain file
reads instead of per-file API requests.

Do not write inline path-check logic. Run the bundled `path_select.py`: it
checks A → B → C → D in order and prints `[PATH-CHECK]` / `[PATH-SELECTED]`
lines as it runs, so the trace appears in the execution log at decision time
(the gate later looks for it). Run it with Python directly — shell `eval` or
complex expansions may be blocked by safety filters in some AI tools. Prefer
`SKILL_PATH/scripts/path_select.py`; if `SKILL_PATH` is unknown, use the fixed
candidate directories below (no recursive search):

```python
import subprocess, os, pathlib

# Step 1: locate path_select.py from known install locations
search_dirs = [
    pathlib.Path.home() / ".config/opencode/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".claude/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".copilot/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".cursor/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".gemini/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".codex/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".qwen/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".grok/skills/github-code-review-pr/scripts",
]
script = next((d / "path_select.py" for d in search_dirs if (d / "path_select.py").exists()), None)

# Step 2: get current repo (empty string if not inside any repo or gh unavailable)
result = subprocess.run(
    ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
    capture_output=True, text=True, env={**os.environ, "GH_PAGER": "cat"}
)
current_repo = result.stdout.strip() if result.returncode == 0 else ""

# Step 3: run path selection — prints [PATH-CHECK] / [PATH-SELECTED] trace lines
# and prints machine-readable lines: SELECTED_PATH=..., REPO_PATH=...
output = subprocess.run(
    ["python3", str(script), "https://<host>/<owner>/<repo>", current_repo],
    capture_output=False  # prints trace directly to stdout
)
```

Read `SELECTED_PATH` and `REPO_PATH` from the `KEY=VALUE` lines in the output,
or re-run with `capture_output=True` to parse them programmatically.

Rules:
- Run this block before any `git fetch`, `git checkout`, or clone command.
- Do not proceed to Step 4 until `[PATH-SELECTED]` is visible in the log.
- Always use the script rather than re-implementing the checks inline.

## Execution guardrail

Immediately after parsing `SELECTED_PATH` / `REPO_PATH`, register cleanup
handling (see [Manual cleanup](#manual-cleanup)) **before** any
fetch/checkout/clone, so cleanup still runs on mid-review failures.

- Keep `SELECTED_PATH` in a shell variable for cleanup branching.
- For Path A, capture `ORIGINAL_BRANCH` immediately.
- For Path B, capture `REPO_PATH` and resolve `DEFAULT_BRANCH` once.
- For Path C, capture `REPO_PATH` (same as Path B — it's a shared cache repo).
- For Path D, capture created temp dirs (`REVIEW_DIR`, `RUN_DIR`) as soon as
  they are created.
- Use an `EXIT` trap (or equivalent) so cleanup executes whether the review
  succeeds, partially fails, or exits early.

## Path A: already inside the target repo

When `SELECTED_PATH=A`:

Commit or stash local work first — this switches the working tree.

```bash
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git fetch origin <baseRefName>
# pull/<PR_NUMBER>/head is the PR's exact head for fork and same-repo PRs.
# Never check out origin/<headRefName>: for a fork PR that is an unrelated
# upstream branch that merely shares the name (main, patch-1, ...).
if FETCH_ERR="$(git fetch origin "pull/<PR_NUMBER>/head" 2>&1)"; then
  git checkout --detach FETCH_HEAD
else
  CONTEXT_MODE="diff_only"
  CONTEXT_LIMITATION="PR head checkout failed: $FETCH_ERR"
fi
```

Use plain git rather than `gh pr checkout`, which can fail on Enterprise hosts
that need a separate `gh auth login --hostname` even when `gh pr view/diff`
works. After the review, restore the original branch (see
[Manual cleanup](#manual-cleanup)).

## Path B: shared repo cache hit

When `SELECTED_PATH=B`, `$REPO_PATH` is already set by the path-selection
script. Update the cached repo and check out the PR branch (`headRefName` is
known from 2a):

```bash
cd "$REPO_PATH"
git fetch origin <baseRefName>
# pull/<PR_NUMBER>/head is the PR's exact head for fork and same-repo PRs.
# Never check out origin/<headRefName>: for a fork PR that is an unrelated
# upstream branch that merely shares the name (main, patch-1, ...).
if FETCH_ERR="$(git fetch origin "pull/<PR_NUMBER>/head" 2>&1)"; then
  git checkout --detach FETCH_HEAD
else
  CONTEXT_MODE="diff_only"
  CONTEXT_LIMITATION="PR head checkout failed: $FETCH_ERR"
fi
```

When `CONTEXT_MODE=diff_only`:
- Continue the review using Step 2 metadata + diff only (no fake local-context
  claims).
- State this limitation explicitly in the review output.
- Still run cleanup and print `[PATH-CLEANUP] ...` status lines.

**Why plain git instead of `gh pr checkout`:** `gh pr checkout` can fail if the
host hasn't been authenticated with `gh auth login --hostname <host>`, even
when `gh pr view/diff` succeeds (they may use a different auth path).

For base-branch comparison, use `origin/<baseRefName>` (the remote-tracking
ref, fresh after the fetch).

## Path C: clone into shared cache

When `SELECTED_PATH=C`, the repo is not yet available locally. Before cloning,
query the repo's disk size with `gh api repos/<owner>/<repo> --jq '.size'`:

- **Repo ≤ 100 MB** → proceed with Path C (clone into the shared cache).
- **Repo > 100 MB** → ask the user to choose Path C anyway, Path D, or
  diff-only (same three options and default rule as "Handling exit code 10" in
  SKILL.md).
- **Size query fails** → proceed with Path C (fall back to D if the clone
  fails).

Path C clones into the shared `git-repo-cache` via the bundled `repo_manager.py
sync`. This is a blobless clone reusable across sessions and skills — the next
review of the same repo hits Path B instantly:

```bash
python3 SKILL_PATH/scripts/repo_manager.py sync "<repo-url>"
```

This command:
1. Checks `repo_map.json` for an existing entry (handles stale entries
   automatically).
2. Clones with `--filter=blob:none` into
   `git-repo-cache/repos/<host>/<owner>/<repo>/`.
3. Resets the working tree to a clean state on the default branch.
4. Registers the repo in `repo_map.json` for future lookups.
5. Prints the local path to stdout.

Then check out the PR head exactly as in Path B:

```bash
cd "$REPO_PATH"
git fetch origin <baseRefName>
# pull/<PR_NUMBER>/head is the PR's exact head for fork and same-repo PRs.
# Never check out origin/<headRefName>: for a fork PR that is an unrelated
# upstream branch that merely shares the name (main, patch-1, ...).
if FETCH_ERR="$(git fetch origin "pull/<PR_NUMBER>/head" 2>&1)"; then
  git checkout --detach FETCH_HEAD
else
  CONTEXT_MODE="diff_only"
  CONTEXT_LIMITATION="PR head checkout failed: $FETCH_ERR"
fi
```

**Why Path C over a direct sparse clone:** for most repos (up to tens of
thousands of files) the blobless clone is only a few MB of tree/commit
metadata, and the repo persists in the shared cache, so future reviews,
`git-repo-reader` queries, and other skills reuse it without cloning. Blobs
are fetched on demand when files are read.

**Fallback to Path D:** if `repo_manager.py sync` fails at runtime (auth or
network errors), degrade to Path D and emit a `[PATH-FALLBACK]` trace line.

After the review, reset the repo to the default branch (same cleanup as Path
B). Do not delete the cached repo — it is shared and reusable.

## Path D: blobless sparse clone to temp directory

Path D is for large repos (> 100 MB per the GitHub API, when the user chose D)
or as the fallback when Path C fails. It uses a blobless clone plus sparse
checkout into a disposable directory, downloading only what the review needs.

**Why not `--depth=1` or `--single-branch`:** `--single-branch` restricts the
refspec to one branch, so a later `git fetch origin pull/<PR_NUMBER>/head` is
impossible; `--depth=1` implies `--single-branch`. `--filter=blob:none
--sparse` keeps all refs and history metadata at minimal cost — blobs are only
fetched when files are checked out.

Clone into the unified skill cache, never `/tmp`, `$TMPDIR`, or another ad-hoc
directory (so `skills-clean-cache` can find leftovers).

**Bash (macOS / Linux):**
```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
  CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
fi
CACHE_DIR="$CACHE_ROOT/github-code-review-pr"
mkdir -p "$CACHE_DIR"
REVIEW_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
gh repo clone <owner/repo> "$REVIEW_DIR" -- --filter=blob:none --sparse
cd "$REVIEW_DIR"
```

**PowerShell (Windows):**
```powershell
$CACHE_ROOT = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "mythril-skills-cache"
$CACHE_DIR = Join-Path $CACHE_ROOT "github-code-review-pr"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
$REVIEW_DIR = Join-Path $CACHE_DIR ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $REVIEW_DIR | Out-Null
gh repo clone <owner/repo> "$REVIEW_DIR" -- --filter=blob:none --sparse
Set-Location $REVIEW_DIR
```

The clone has sparse checkout enabled (cone mode); only root-level files
(README.md, AGENTS.md, pyproject.toml, etc.) are checked out. Add the
directories the review needs, based on the Step 2 metadata:

1. Directories containing PR-modified files (from the `files` list in 2a):
   ```bash
   git sparse-checkout add src/components src/utils tests/unit
   ```
2. Directories for related files the diff references (imports, base classes):
   ```bash
   git sparse-checkout add src/types src/shared
   ```

Then check out the PR head exactly as in Path B (`pull/<PR_NUMBER>/head`,
detached — never `origin/<headRefName>`, which is wrong for fork PRs):

```bash
git fetch origin "pull/<PR_NUMBER>/head" && git checkout --detach FETCH_HEAD
```

After the review, delete the temp directory (see below).

## Path selection summary

| Path | Condition | Speed | Context depth |
|---|---|---|---|
| A | Already inside target repo | Instant | Full repo |
| B | Repo found in shared cache | Fast (just `fetch` two branches) | Full repo |
| C | Repo not cached, ≤ 100 MB — clone to shared cache | Moderate (blobless clone, reusable) | Full repo |
| D | Repo > 100 MB (user chose D), or Path C clone failed | Moderate (blobless sparse clone, disposable) | Targeted files only |
| DIFF_ONLY | User explicitly chose no clone (large repo) | Instant | PR diff + metadata only |

Paths B and C may degrade to diff-only when branch fetch/checkout fails — only
after the fallback sequence above was attempted and logged. Path C falls back
to Path D if `repo_manager.py sync` fails at runtime.

## Manual cleanup

Register cleanup right after path selection, not at the end of the review.
Use an `EXIT` trap (or equivalent in non-shell tools) so it runs on success,
command failure, or early return. The `[PATH-CLEANUP]` lines must come from
`echo` inside the cleanup script, not be written later as prose — the gate
checks the cleanup log for them.

```bash
cleanup_review_env() {
  case "${SELECTED_PATH:-}" in
    A)
      if [[ -n "${ORIGINAL_BRANCH:-}" ]]; then
        git checkout "$ORIGINAL_BRANCH" >/dev/null 2>&1 || true
        echo "[PATH-CLEANUP] Path A - restored branch to $ORIGINAL_BRANCH"
      else
        echo "[PATH-CLEANUP] Path A - skipped (ORIGINAL_BRANCH unavailable)"
      fi
      ;;
    B|C)
      if [[ -n "${REPO_PATH:-}" ]] && [[ -d "$REPO_PATH/.git" ]]; then
        cd "$REPO_PATH" || true
        DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD --short 2>/dev/null | sed 's|origin/||')
        git checkout "${DEFAULT_BRANCH:-main}" >/dev/null 2>&1 || true
        git reset --hard "origin/${DEFAULT_BRANCH:-main}" >/dev/null 2>&1 || true
        git clean -fd >/dev/null 2>&1 || true
        echo "[PATH-CLEANUP] Path ${SELECTED_PATH} - reset cached repo to ${DEFAULT_BRANCH:-main}, ready for next use"
      else
        echo "[PATH-CLEANUP] Path ${SELECTED_PATH} - skipped (REPO_PATH unavailable)"
      fi
      ;;
    D)
      REMOVED=()
      for d in "${REVIEW_DIR:-}" "${RUN_DIR:-}"; do
        if [[ -n "$d" ]] && [[ -e "$d" ]]; then
          rm -rf "$d" && REMOVED+=("$d") || echo "[PATH-CLEANUP] Path D - failed to delete: $d"
        fi
      done
      if [[ ${#REMOVED[@]} -gt 0 ]]; then
        echo "[PATH-CLEANUP] Path D - deleted temp dirs: ${REMOVED[*]}"
      else
        echo "[PATH-CLEANUP] Path D - no temp dirs to delete"
      fi
      ;;
    DIFF_ONLY)
      echo "[PATH-CLEANUP] DIFF_ONLY - no repo to clean up"
      ;;
    *)
      echo "[PATH-CLEANUP] skipped - SELECTED_PATH not set"
      ;;
  esac
}

trap cleanup_review_env EXIT
```

What cleanup does per path:
- **Path A** (existing repo): restore the original branch:
  `git checkout "$ORIGINAL_BRANCH"`.
- **Path B / Path C** (shared cache): reset to a clean default branch so the
  cached repo is ready for the next use:
  ```bash
  cd "$REPO_PATH"
  DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD --short 2>/dev/null | sed 's|origin/||')
  git checkout "${DEFAULT_BRANCH:-main}"
  git reset --hard "origin/${DEFAULT_BRANCH:-main}"
  git clean -fd
  ```
  Do not delete the cached repo — it is shared and reused.
- **Path D** (sparse clone): delete every temp directory created for this
  review under `mythril-skills-cache/github-code-review-pr/` (including
  `"$REVIEW_DIR"` and `"$RUN_DIR"` when present): `rm -rf "<dir>"`. Don't
  substitute the Path B/C branch reset here — that would leave the temp clone
  behind.
- **DIFF_ONLY** (no clone): no repo cleanup; just purge session artifacts.

After cleanup, tell the user it succeeded and which temp paths were removed
(or how many). If a directory cannot be deleted, report the remaining path and
the error, and suggest `skills-clean-cache`.

Image artifacts and Path D temp directories live under
`mythril-skills-cache/github-code-review-pr/`. Leftovers from interrupted
sessions can be removed with:

```bash
skills-clean-cache
```
