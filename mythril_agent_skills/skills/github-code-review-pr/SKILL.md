---
name: github-code-review-pr
description: >
  Performs a comprehensive code review of a GitHub Pull Request with the `gh`
  CLI, reading the surrounding repo code, not just the diff. Use when the user asks to review a PR URL (any URL containing `/pull/`)
  or PR number: "review this PR", "PR code review", "审查这个PR", "帮我看这个PR",
  "CR". Unknown hosts may be GitHub Enterprise, so run `gh` rather than guessing
  the platform. For routine PR actions without a full review, use
  gh-operations; for local staged changes, use code-review-staged.
license: Apache-2.0
---

# GitHub PR Code Review

## When to use

Use this skill when the user wants a Pull Request reviewed:
- "review this PR" / "PR review" / "PR code review" / "help me review this pull request"
- "审查这个PR" / "帮我看这个PR" / "PR审查"
- Any URL containing `/pull/`, or a PR number, plus a request for review/feedback
- The user shared a PR URL earlier, then says "使用技能" / "use this skill"

**Don't guess the platform from the hostname.** Domains like `git.company.com`
or `code.company.com.au` are very often GitHub Enterprise. Speculating ("this
looks like GitLab") wastes tokens and is often wrong; running `gh` and letting
it succeed or fail is fast and conclusive. So for any `/pull/` URL with review
intent:

1. Run `review_runner.py prepare <URL>` immediately — no host analysis and no
   `gh auth status` pre-check first.
2. If `gh` fails, report the error and suggest `gh auth login --hostname <host>`.

The output gate also rejects platform-guessing phrases, so speculation makes
the review fail its own check.

This skill reviews remote PRs via `gh`. For local staged changes, use
`code-review-staged`; for comparing two local branches, `branch-diff-review`.

## Requirements

- **GitHub CLI (`gh`)** installed and authenticated
- **`curl`** for downloading PR screenshots/assets
- **Optional for enterprise SSO**: `curl --negotiate -u :` support for SPNEGO/Kerberos-protected asset URLs
- Run `skills-check github-code-review-pr` to verify dependencies

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

## Review standards

- Comprehensive and rigorous: identify all potential issues and flag suspicious code.
- Actionable: concrete suggestions with file paths and line references.
- Grounded in the project's existing conventions, patterns, and style.
- Written in the user's language (see Step 5).

## Workflow

`SKILL_PATH` is this skill's installed directory. All bundled scripts live in
`SKILL_PATH/scripts/`. If `SKILL_PATH` cannot be resolved or the scripts are
missing, follow [references/manual-fallback.md](references/manual-fallback.md)
instead of Steps 2–3 and the cleanup in Step 7a.

### Step 1: Parse the PR reference

Accepted forms:
- Full URL: `https://github.com/owner/repo/pull/123`
- Full URL with any host: `https://git.mycompany.com/owner/repo/pull/123`
- PR number (inside a repo): `123`
- PR number with repo: `owner/repo#123`

Extract owner, repo, PR number, and hostname, then go straight to Step 2.

### Step 2: Prepare the session with the runner

Use the runner instead of calling `gh pr view` / `gh pr diff` yourself. It
fetches once, selects the repo-access path, checks out the PR branch, and wires
cleanup in one deterministic call — and the gate in Step 7 checks that the
fetch happened exactly once.

```bash
python3 SKILL_PATH/scripts/review_runner.py prepare <URL_or_NUMBER>
```

What it does:
1. Fetches PR metadata (`gh pr view`) and diff (`gh pr diff`) exactly once.
2. Runs `path_select.py` (A → B → C → D with `[PATH-CHECK]` / `[PATH-SELECTED]` trace).
3. When neither A nor B matches, queries repo size via `gh api` to pick C vs D:
   - ≤ 100 MB → Path C: clone into the shared cache via `repo_manager.py sync` (reusable)
   - \> 100 MB → pauses with **exit code 10** for a user decision (below)
   - Size query fails → Path C (falls back to D if the clone fails)
4. Checks out the PR branch, falling back to `pull/<PR>/head`.
5. Saves all outputs to a session manifest.

Repo-access paths:

| Path | Condition | Context depth |
|---|---|---|
| A | Already inside the target repo | Full repo |
| B | Repo found in shared cache | Full repo |
| C | Not cached, ≤ 100 MB — cloned to shared cache (kept for reuse) | Full repo |
| D | > 100 MB (user chose D), or Path C clone failed — sparse temp clone | Targeted files only |
| DIFF_ONLY | User chose no clone (large repo) | PR diff + metadata only |

Machine-readable output (exit code 0):
- `RUN_MANIFEST=<path>` — session manifest JSON (needed for cleanup and gate)
- `PR_VIEW_JSON_PATH=<path>` — saved PR metadata JSON
- `PR_DIFF_PATH=<path>` — saved PR diff
- `CLEANUP_LOG_PATH=<path>` — where to tee cleanup output in Step 7a
- `REVIEW_TEXT_PATH=<path>` — where to write the review text in Step 7b
- `SELECTED_PATH=A|B|C|D|DIFF_ONLY`
- `REPO_WORKDIR=<path>` — local repo directory (empty if diff-only)
- `PR_STATE=OPEN|CLOSED|MERGED`
- `CONTEXT_MODE=full_repo|diff_only`
- `CONTEXT_LIMITATION=<message>` — explanation when context is limited
- `CHECKOUT_DONE=true|false` — whether the PR branch is already checked out at `REPO_WORKDIR`
- `NOTE: PR branch is already checked out...` — human-readable confirmation

#### Handling exit code 10 (large repo — user decision required)

When the repo exceeds the threshold and neither A nor B matched, `prepare`
exits with code **10** and emits:

- `NEEDS_USER_DECISION=true`
- `REPO_SIZE_MB=<float>`, `THRESHOLD_MB=<int>`
- `RECOMMENDED_DEFAULT=D|diff-only`
- `PENDING_RUN_DIR=<path>` — session directory with saved metadata/diff
- `PR_VIEW_JSON_PATH=<path>`, `PR_DIFF_PATH=<path>` — already fetched, reusable

Present three options to the user, with the default pre-selected by this table
(follow it rather than inventing your own recommendation — it encodes the
download-cost trade-off):

| Repo size | Default option | Rationale |
|---|---|---|
| ≤ 1 GB | **2. Sparse clone (Path D)** | Blobless sparse clone downloads only tree metadata (usually <50 MB even for large repos) and fetches file content on demand. |
| > 1 GB | **3. Diff-only** | Monorepo-scale repos have huge tree objects; tree metadata alone can take minutes. |

Pre-select the default (cursor on it) and don't add "(Recommended)" text — the
pre-selection is the recommendation.

> This repository is **{REPO_SIZE_MB} MB** (exceeds the {THRESHOLD_MB} MB threshold).
>
> How would you like to proceed?
> 1. Clone to shared cache (Path C) — larger download, but cached for future reviews
> 2. Sparse clone to temp dir (Path D) — smaller download, only PR-related files, deleted after review
> 3. Diff-only — no clone, review based on PR diff and metadata only (limited context)

Then resume the pending session (reuses the fetched metadata and diff, no new
`gh pr view` / `gh pr diff`):

```bash
python3 SKILL_PATH/scripts/review_runner.py prepare <URL_or_NUMBER> \
    --force-path C|D|diff-only --run-dir <PENDING_RUN_DIR>
```

#### After prepare succeeds

1. Read metadata from `PR_VIEW_JSON_PATH` and the diff from `PR_DIFF_PATH` —
   don't re-run `gh pr view` / `gh pr diff` (a second fetch fails the gate).
2. If `CHECKOUT_DONE=true`, the PR branch is already checked out at
   `REPO_WORKDIR`. Run no git commands to prepare the repo (`git fetch`,
   `git checkout`, `gh pr checkout`) — just `cd <REPO_WORKDIR>` and read files.
   Extra checkouts can leave the shared cache on the wrong branch.
3. Keep `RUN_MANIFEST`, `CLEANUP_LOG_PATH`, and `REVIEW_TEXT_PATH` for Step 7.
4. If the PR body, comments, or reviews contain image links, read
   [references/pr-images.md](references/pr-images.md) and analyze the relevant
   screenshots (when the user asks about them, or they are verification
   evidence for the PR).

### Step 3: Repo access

Already done by the runner — go to Step 4. Only without the runner do you
select and prepare a path yourself, per
[references/manual-fallback.md](references/manual-fallback.md).

### Step 4: Gather repository context

**Full repo (Paths A, B, C).** Read files directly; the blobless clone fetches
blob content on demand.

- **4a. Structure:** `git ls-tree -r --name-only HEAD | head -200` — module
  organization, naming conventions, architecture.
- **4b. Conventions:** read 3–5 of the most relevant config files for the
  changed files' languages; skim, and skip files larger than ~50 KB.

  | AI instruction file (highest priority) | Tool |
  |---|---|
  | `AGENTS.md` | Cross-tool standard (Codex, Cursor, Copilot, Amp, Windsurf, Devin) |
  | `CLAUDE.md` | Claude Code |
  | `GEMINI.md` | Gemini CLI |
  | `.github/copilot-instructions.md` | GitHub Copilot |
  | `.cursorrules` / `.cursor/rules/` | Cursor |
  | `.windsurfrules` / `.windsurf/rules/` | Windsurf |

  Project/build config: `README.md`, `CONTRIBUTING.md`, `pyproject.toml` /
  `setup.cfg`, `package.json`, `.editorconfig`, `.eslintrc.*` / `biome.json`,
  `Makefile` / `Justfile`, `Cargo.toml`, `go.mod`, `.clang-format` /
  `.clang-tidy`.
- **4c. Modified files**, driven by change volume:
  - \> 50 lines changed (additions + deletions): read the full file
  - 5–50 lines: read the full file — surrounding code matters for correctness
  - < 5 lines: the diff may suffice, unless it's a critical path (security, auth, financial logic)
  - New files: always read in full
  - Skip binary files and files > 100 KB (all files, including new ones) — use the diff
- **4d. Related files not in the diff:** read 3–5 that are strictly needed to
  validate correctness (interfaces, base classes, callers of changed
  functions, related tests).

**Path D (sparse checkout).** Tree objects are complete, so 4a works the same;
root-level config files are already checked out; modified files' directories
are checked out. For related files in other directories, run
`git sparse-checkout add <directory>` first, then read them.

**DIFF_ONLY.** No local repo. Infer conventions from the diff itself, use only
the hunks in `PR_DIFF_PATH`, and flag that project structure and cross-file
validation were unavailable. State in section 2 of the review that it was done
in diff-only mode — the user accepted that limitation and should see it.

**Other repositories.** If the user points to another repo during the review
(e.g. a backend API to check schema compatibility), use the `git-repo-reader`
skill rather than cloning it yourself — its clone lands in the shared cache and
is reused later. If that skill isn't available, do a blobless clone in this
skill's cache (as in Path D).

### Step 5: Detect the review language

- Any Chinese characters (U+4E00–U+9FFF) in the user's input → Chinese review,
  even when mixed with English (e.g. "review 一下这个PR").
- Only English → English review.

### Step 6: Write the review

**Evidence certainty.** Keep confirmed findings separate from potential risks:
- A confirmed finding is directly supported by the diff, file content, or PR
  metadata.
- A potential risk is labeled as such and includes one concrete validation
  step.
- Don't present speculative runtime/CI behavior as fact.

**Finding groups.** Split findings into `Confirmed Findings` / `已确认问题` and
`Potential Risks` / `潜在风险`. Each item belongs to exactly one group; write
`Confirmed Findings: none` / `Potential Risks: none` when a group is empty.

**Consistency check before output.**
1. Remove items disproven later in the same run.
2. No self-contradicting pairs ("Issue: X" and later "No issue for X") — keep
   only the final conclusion.
3. The verdict (`Approve` / `Request Changes` / `Comment`) matches the final
   severity of the issues.

**Structure: exactly 6 sections, in order.** 1 PR Overview · 2 Repository
Context Analysis · 3 Code Quality & Clean Code Evaluation · 4 Major Issues and
Risks · 5 Incremental Suggestions · 6 Summary Verdict (Chinese: PR 概览 ·
仓库上下文分析 · 代码质量 & Clean Code 评价 · 潜在的重大问题和风险 · 增量建议 ·
总结评价). What each section contains, in both languages, is in
[references/review-template.md](references/review-template.md). Generate the
skeleton first to avoid structural drift, then fill each `[fill]` placeholder
with evidence:

```bash
RUN_DIR="$(dirname "<RUN_MANIFEST>")"
REVIEW_DRAFT_PATH="$RUN_DIR/review_draft.md"
python3 SKILL_PATH/scripts/review_template_builder.py \
  --manifest <RUN_MANIFEST> \
  --output "$REVIEW_DRAFT_PATH" \
  --language en   # or zh
```

Don't show the review to the user yet — it goes through Step 7 first.

### Step 7: Clean up, gate, and send

Always run this step, even if the review hit errors, and in this order: the
review is shown only after the gate passes.

**7a. Cleanup (restores the repo, keeps session files).** Tee the output to
`CLEANUP_LOG_PATH` — the gate reads that file and fails with
`CLEANUP_EVIDENCE_PASS: FAIL` if it is missing:

```bash
python3 SKILL_PATH/scripts/review_runner.py cleanup <RUN_MANIFEST> 2>&1 | tee <CLEANUP_LOG_PATH>
```

Without the runner, use the cleanup function in
[references/manual-fallback.md](references/manual-fallback.md#manual-cleanup).

**7b. Quality gate.** Run the script rather than checking mentally:

1. Write the complete 6-section review to `REVIEW_TEXT_PATH`:
   ```bash
   cat > <REVIEW_TEXT_PATH> << 'REVIEW_EOF'
   <paste your complete review content here>
   REVIEW_EOF
   ```
2. Run the gate:
   ```bash
   python3 SKILL_PATH/scripts/review_output_gate.py \
     --manifest <RUN_MANIFEST> \
     --review-text <REVIEW_TEXT_PATH> \
     --cleanup-log <CLEANUP_LOG_PATH>
   ```
3. Exit `0` → go to 7c. Non-zero → read the FAIL details, fix the review text,
   and re-run.

If `review_output_gate.py` is missing, check and report each item manually:
1. `NO_SPECULATION_PASS` — no platform-guessing text before the first `gh` command.
2. `SINGLE_FETCH_PASS` — `gh pr view` and `gh pr diff` each ran exactly once.
3. `CLEANUP_EVIDENCE_PASS` — `[PATH-CLEANUP]` marker present in cleanup output.
4. `VERDICT_STATE_PASS` — verdict consistent with PR state (no `Request Changes` on merged/closed PRs unless the user asked).

**7c. Send and purge.** Present the review once, after the gate passes — no
draft before it. Show the full 6-section review as-is; don't condense it into a
shorter summary (e.g. "关键问题 / 优点 / 建议"), because the 6 sections are the
deliverable. Then delete the session artifacts:

```bash
python3 SKILL_PATH/scripts/review_runner.py purge <RUN_MANIFEST>
```

If purge fails or is skipped, `skills-clean-cache` removes the leftovers later.

## Error handling

- **Unknown host / `gh` host or auth error.** Expected when a non-github.com
  host isn't configured. Report the `gh` error and say: the host may be GitHub
  Enterprise — run `gh auth login --hostname <host>`; if it isn't GitHub at
  all, this skill only supports GitHub (including GHE). Don't label the host
  "GitLab" or similar.
- **Auth failure — allowed recovery only:** report the `gh` error; suggest
  `gh auth login --hostname <host>` and `gh auth status --hostname <host>`;
  then stop and wait for the user. Searching the Keychain, git credential
  store, `.netrc`, or `~/.config/gh/hosts.yml`, or building `curl` calls with
  extracted tokens, violates Security rules 4–5.
- **`gh` not installed:** suggest `skills-check github-code-review-pr`.
- **`gh` not authenticated for github.com:** suggest `gh auth login`.
- **PR not found:** verify the URL/number and repo access.
- **PR image download failed:** see [references/pr-images.md](references/pr-images.md#failures).
- **Clone failure:** review with diff-only context and state the limitation.
- **Large PR (> 50 files):** warn the review may be less thorough; focus on the most critical files.
- **Binary files:** skip them in the review and note that they are present.
- **Private repo access denied:** report it clearly.

## Examples

1. "帮我审查一下这个 PR https://github.com/owner/repo/pull/42" → runner finds
   the repo in cache (Path B), checks out the PR branch → 6-section Chinese
   review with full repo context.
2. "Review this PR: https://github.com/owner/repo/pull/99" → cache miss, clone
   to shared cache (Path C) → 6-section English review; repo now cached.
3. "Review PR #15" inside the repo → Path A → review, original branch restored
   at cleanup.
4. "帮我看一下这个 PR https://git.example.com/owner/repo/pull/123" → run the
   runner immediately → full review if GHE is configured, otherwise the `gh`
   error plus `gh auth login --hostname git.example.com`. Not: "this looks like
   GitLab", or asking the user which platform it is.

## After the review: posting comments

If the user asks to post comments about specific issues back to the PR, read
[references/pr-comments.md](references/pr-comments.md). Default to inline
line-level comments; use a general PR comment only for whole-PR feedback or
when explicitly asked.
