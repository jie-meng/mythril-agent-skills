---
name: fullstack-apply
description: |
  Implement a planned work item across a multi-repo fullstack workspace —
  implement per repo in dependency order, run staged and cross-repo
  reviews against the plan's Success Criteria, create PRs, and finalize
  the four work-tracking documents. Input is a work directory produced
  by fullstack-propose; no planning happens here. Stays sticky on an
  active work item: follow-up edits driven by user feedback, error
  logs, manual testing, or bug reports run the same review loop even
  when the user does not re-mention the skill.
  Trigger: "fullstack implement", "fullstack develop", "fullstack impl",
  "全栈实现", "全栈开发", "全栈 impl", "implement this plan",
  "实现这个方案"; ALSO on follow-up edit/fix in an active work dir —
  "this is wrong", "fix this", "调一下", "再改一下", "这里不对",
  "log 报错", pasted error/log; or when continuing an existing work
  item under changes/{feat,refactor,fix}/.
license: Apache-2.0
---

# Fullstack Apply

Implement a planned work item across a multi-repo fullstack workspace
initialized by `fullstack-init`. The input is a **work directory**
created by `fullstack-propose`:

```text
<docs-dir>/changes/<type>/<work-name>/
├── analysis.md   # why and how (may include spike findings)
├── plan.md       # requirements, Success Criteria, tasks
├── progress.md   # dated change log
└── review.md     # review findings + Evidence table
```

This skill implements the plan, repo by repo in dependency order,
reviews the changes against the plan's Success Criteria, opens PRs, and
finalizes the documents. It does NOT plan — if no work directory
exists for the request, tell the user to run `fullstack-propose` first.

## How this skill is organized

Cross-cutting details live in `references/` and are read when relevant:

| File | Read when |
|------|-----------|
| [`references/document-templates.md`](references/document-templates.md) | Writing/updating the four work-tracking documents (templates + Mermaid Compatibility Gate) |
| [`references/review-formats.md`](references/review-formats.md) | Formatting per-repo and cross-repo review sections in `review.md` |

Always read the files relevant to the current step. They are concise on
purpose; do not skim.

## Prerequisites — Workspace Validation Gate (MANDATORY SCRIPT CALL)

This skill MUST NOT proceed past this gate. Before reading any work
directory, run `check_workspace.py` and inspect its output. This is a
hard precondition — skipping the script and "checking files manually" is
forbidden, because the script also reports `docs_dir` and `github_repos`
which are needed later.

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/fullstack-apply/scripts/check_workspace.py",
    pathlib.Path.home() / ".claude/skills/fullstack-apply/scripts/check_workspace.py",
    pathlib.Path.home() / ".copilot/skills/fullstack-apply/scripts/check_workspace.py",
    pathlib.Path.home() / ".cursor/skills/fullstack-apply/scripts/check_workspace.py",
    pathlib.Path.home() / ".gemini/skills/fullstack-apply/scripts/check_workspace.py",
    pathlib.Path.home() / ".codex/skills/fullstack-apply/scripts/check_workspace.py",
    pathlib.Path.home() / ".qwen/skills/fullstack-apply/scripts/check_workspace.py",
    pathlib.Path.home() / ".grok/skills/fullstack-apply/scripts/check_workspace.py",
]
script = next((p for p in candidates if p.exists()), None)
if not script:
    print("ERROR: check_workspace.py not found", file=sys.stderr)
    sys.exit(1)
result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
print(result.stdout)
```

The script reports:

| Key | Meaning |
|-----|---------|
| `WORKSPACE_VALID=true\|false` | All three markers present? |
| `MISSING=<list>` | Comma-separated list of missing markers |
| `DOCS_DIR=<name>` | Docs directory name (e.g. `ai-documents`, `docs`) |
| `GITHUB_REPOS=true\|false` | Whether the PR step should create PRs |

Decision logic:

- `WORKSPACE_VALID=true` → announce the Workspace contract line (below),
  then proceed to Step 1
- `WORKSPACE_VALID=false` → STOP and tell the user:

  > **Workspace not detected.** This skill requires a fullstack
  > workspace initialized by `fullstack-init`. Missing markers:
  > _(list from `MISSING=`)_.
  >
  > Please `cd` to your project workspace root and restart your AI
  > agent there, or run `fullstack-init` first to set up the workspace.

### Announce the Workspace contract (MANDATORY OUTPUT)

When `WORKSPACE_VALID=true`, output EXACTLY this line before doing
anything else:

```
Workspace: VALID | docs_dir=<DOCS_DIR> | github_repos=<true|false>
```

Use English for this line regardless of conversation language — it is a
machine-readable contract marker. It commits you to specific values that
later steps MUST honor:

- `github_repos` decides whether the PR step runs. Without the announce,
  the value gets "remembered" only in the agent's head and drifts.
- `docs_dir` is used in every later step to locate work directories.

If you ever lose track of these values mid-session, re-run
`check_workspace.py` ONCE and re-announce — do NOT guess.

## Document Language Selection

All four work-tracking documents and user-facing messages MUST match the
language of the user's prompt.

1. If the user **explicitly requests a language** → use that language.
2. If the user's prompt contains **any Chinese characters** → use Chinese.
3. Otherwise → use English (default).

This applies independently per invocation. It does NOT affect branch
names (always English Title-Case-With-Hyphens), work directory names
(always lowercase-hyphenated English), or Git commit messages (follow
each repo's own convention).

## Step 1 — Identify the Work Item

Locate the work directory the user means:

1. **If the user named a work item** (e.g. "implement add-dark-mode",
   "继续 dark-mode"), find it under `<docs-dir>/changes/<type>/<name>/`.
2. **If the user references an active work item without naming it**,
   list the active items under `changes/{feat,refactor,fix}/` and ask
   which one they mean.
3. **If the user gave a new requirement with no work directory**, STOP
   and tell them to run `fullstack-propose` first — this skill does not
   plan.

Read all four documents in full. The `plan.md` Success Criteria are the
definition of done; `analysis.md` carries the technical approach;
`progress.md` shows what's already complete; `review.md` shows review
history.

**Resume**: if the work is partially complete, resume from the last
incomplete step recorded in `progress.md`. Check that branches still
exist in the affected repos.

## Step 2 — Confirm Repos and Branches (MANDATORY)

Present the plan's affected repos and branch names for confirmation, even
when confident:

```
Based on the plan, I'll modify these repositories:

  1. shared-lib/ — Add theme constants to shared types
     Branch: feat/Dark-Mode-Toggle
  2. api/ — Add user preference endpoint for theme setting
     Branch: feat/BE-450/Dark-Mode-Toggle
  3. android/ — Add dark mode toggle to settings screen
     Branch: feat/MOBILE-301/Dark-Mode-Toggle

Does this look correct?
```

Do NOT proceed until the user confirms. If the user corrects you, update
and reconfirm.

## Step 3 — Branch Management

### Branch naming convention

| Scenario | Format | Example |
|----------|--------|---------|
| With Jira key | `<type>/<JIRA-KEY>/<Title-Hyphenated>` | `feat/XYZ-706/Import-Export` |
| Without Jira | `<type>/<Title-Hyphenated>` | `refactor/Refine-Models` |
| Successor work (`-vN`) | append `-vN` to the descriptive part | `feat/MOBILE-580/Dark-Mode-Toggle-v2` |

The descriptive part uses **Title-Case-With-Hyphens**. Branch names come
from `plan.md` (recorded per repo); if a repo's branch is missing from
the plan, derive it.

### Multiple Jira tickets → per-repo branch names

When the plan involves multiple Jira tickets (common in cross-platform
work), each repo may get a different branch name based on which ticket
belongs to which platform. Match tickets to repos by cross-referencing
each ticket's title/description/labels/components with each repo's
role/platform/tech stack from the workspace `AGENTS.md` table. If
matching is ambiguous, ask. The `plan.md` MUST record each repo's
specific branch name.

### Creating branches in affected repos

For **each affected code repo** (NOT the docs repo):

1. **Detect the default branch**: check for `main`, `master`, `dev`
   (in that order) by running `git branch -a`.
2. **Check if the target branch already exists**: `git branch --list <branch-name>`.
   - If branch exists and repo is on it → **skip checkout** (resume
     scenario)
   - If branch exists but repo is on a different branch → `git checkout`
3. **If creating a new branch**:
   ```bash
   git checkout <default-branch>
   git pull
   git checkout -b <branch-name>
   ```

### The docs repo does NOT use feature branches

The `<docs-dir>/` repo is an independent git repo for work tracking
docs. All work tracking documents are committed directly to its main
branch. Do NOT create feature branches in the docs repo.

## Step 4 — Implement (serial per-repo with subagent delegation)

You are the **orchestrator**. Manage the high-level flow, confirm
decisions with the user, and delegate detail work to subagents. Do NOT
try to "become" the developer or reviewer — delegate to them.

Implementation follows **serial per-repo** order from `plan.md`. For each
repo, delegate to the **developer** subagent, then to the **reviewer**
subagent. This is the default — even when repos appear independent.

**Why serial:**
1. Cross-repo dependencies are the norm (shared types → API → consumers).
2. Context accumulates — repo A's implementation informs repo B's.
3. Serial audit trail is cleaner for debugging failures.

**Exception — truly independent repos**: If the planner confirmed ZERO
shared interfaces and ZERO dependency edges in `plan.md`, repos MAY be
delegated in parallel. When in doubt, default to serial.

### Agent roles and boundaries

| Agent | Owns | Must NOT touch | Invoked by |
|-------|------|----------------|------------|
| **planner** | `analysis.md` content, `plan.md` content | Source code files | Orchestrator (you) |
| **developer** | Production code, test files, env setup | `review.md` | Orchestrator (you) |
| **reviewer** | Review findings (per-repo + cross-repo) | Source code files | Orchestrator (you) |
| **debugger** | `analysis.md` content (fix type), minimal code fixes | `plan.md` | Orchestrator (you) |
| **orchestrator (you)** | `progress.md`, `review.md` (append agent output), PRs, user communication | — | The user |

**Key rules:**
- Only the **orchestrator writes files** from subagent output. Subagents
  return structured results; you write them to the work directory.
- The **reviewer is invoked for BOTH** per-repo review and cross-repo
  review. One reviewer, two modes.
- The **developer** handles implementation + validation per repo and
  returns results. You don't write code in the main agent.
- If a repo has its own `.agents/agents/` (repo-level agents), prefer
  them for that repo's concerns — pass them the same context and delegate.

### Per-repo implementation loop

For each affected repository, in the dependency order from `plan.md`:

#### 4a. Read repo conventions

1. **Read `AGENTS.md`** (if it exists) — coding style, commit format,
   architecture constraints. MANDATORY to follow.
2. **Read `README.md`** — build / test / lint commands, environment setup.
3. **Check for repo-level agents** at `<repo>/.agents/agents/` — if the
   repo has specialized agents, prefer them for that repo's changes.
4. **Check for `graphify-out/`** — run
   `python3 SKILL_PATH/scripts/graphify_check.py <repo>` to check.
   When `graphify-out/` exists, `cd` into the repo and you MUST use
   `graphify query "<question>"` to understand the codebase before
   reading individual files.

#### 4b. Delegate to developer subagent

Provide the developer subagent with:
- `plan.md` — the implementation plan
- `analysis.md` — technical context
- The repo's `AGENTS.md` and `README.md`
- The repo's branch name and dependency order context
- Any graphify query results

The developer subagent will:
1. Set up the repo environment (venv, nvm, etc.)
2. Implement the changes following repo conventions
3. Run lint → type-check → tests → build
4. Stage all changes (`git add .`)
5. Return: summary of changes, test results, recommended commit message

#### 4c. Handle developer output

1. If tests fail → send back to developer with failure details until passing
2. If implementation complete → write the summary to `progress.md`
3. Proceed to staged review

#### 4d. Per-repo staged review — delegate to reviewer subagent

After the developer has staged changes in a repo, delegate to the
**reviewer** subagent for per-repo staged review:

1. Provide the reviewer with: `plan.md` (especially Success Criteria),
   `analysis.md`, `progress.md`, and the staged diff
   (`git diff --cached` in the repo).
2. The reviewer returns findings in P0/P1/P2 format with a verdict
   (PASS / PASS_WITH_RISKS / NEEDS_FIXES / FAIL).
3. You append the reviewer's output to `review.md`.
4. **If NEEDS_FIXES**: send the P0/P1 items back to the developer
   subagent. Developer fixes → re-validates (lint/test/build) → stages
   (`git add .`). Then invoke reviewer again. Max 3 rounds total.
5. **If PASS**: proceed to commit.

#### 4e. Commit per repo

```bash
cd <repo-dir>
git commit -m "<message>"
```

- Use the commit message from the developer subagent's summary. If the
  repo has its own convention (from `AGENTS.md`), reconcile — repo
  convention wins.
- Update `progress.md` with the commit summary and review verdict.
- Run `python3 SKILL_PATH/scripts/graphify_check.py <repo>` — if
  `graphify-out/` exists, `cd` into the repo and run `graphify update`.

Proceed to the next repo, or to Step 5 if all repos are done.

## Step 5 — Cross-Repo Consistency Review (multi-repo only)

Skip this step for single-repo work. For multi-repo, delegate to the
**reviewer** subagent in cross-repo mode to verify changes are consistent
across all affected repos.

### 5a. Collect cross-repo context

For each affected repo:

```bash
cd <repo-dir>
git diff <default-branch>...<feature-branch>
```

### 5b. Delegate to reviewer subagent (cross-repo mode)

Provide the reviewer with:
- `plan.md`, `analysis.md`, `progress.md` — full work context
- Cross-repo diffs from all affected repos
- For successor work (`-vN`): the predecessor's shipped contracts
  (backward-compatibility check)

The reviewer checks:
- **API contracts**: request/response shapes match between producer and consumer
- **Shared types**: type definitions in shared-lib match usage in consumers
- **Environment variables**: new env vars documented in all affected repos
- **Database migrations**: schema changes compatible across services
- **Error contracts**: error codes/messages consistent across boundaries
- **Version compatibility**: dependency version bumps aligned
- **Backward-compat** (successor work): no breaking changes vs predecessor

### 5c. Write cross-repo findings

Append the reviewer's output to `review.md` using the template in
[`references/review-formats.md`](references/review-formats.md). Even if
no issues are found, write a `PASS` confirmation documenting what was
checked.

### 5d. Fix cross-repo issues

If P0/P1 cross-repo issues are found:
1. Fix upstream repo first, then downstream.
2. For each repo needing fixes, go through the developer → reviewer loop
   again (Steps 4b through 4e).
3. Re-run cross-repo review.
4. Max 2 fix rounds — if issues persist, record as residual.

## Step 6 — Create Pull Requests (only when github_repos=true)

### Gate (FIRST ACTION OF STEP 6 — read the announced contract)

Find the `Workspace:` line you announced at the top of this session.
Read its `github_repos=` value.

Decision logic:

| `github_repos=` | Action |
|-----------------|--------|
| `true` | Continue to "Pre-conditions" below and create PRs |
| `false` | **SKIP this entire step.** Output the skip line below, then go directly to Step 7 |

If `github_repos=false`, output EXACTLY this single line, then jump
straight to Step 7 — do not read any further part of Step 6:

```
Step 6: skipped (github_repos=false — non-GitHub remote, PR creation is the user's responsibility)
```

If the `Workspace:` line is not visible in your transcript (resumed
session), re-run `check_workspace.py` ONCE, re-announce the `Workspace:`
line, and apply the table above.

### Anti-patterns (forbidden when github_repos=false)

| Anti-pattern | Why it's wrong |
|--------------|----------------|
| Inspecting `git remote -v` to "decide" whether the host is GitHub | The user already answered this during `fullstack-init`. Re-deriving from hostname is misclassification |
| Running `which gh glab gitee` to look for an alternative platform CLI | Not your job. The user configures their own tooling |
| Constructing compare URLs (`/compare/main...feat/X`) and presenting them as "PR URLs" | These are not PRs — they are diff views |
| Parsing `git push` output for "Create pull request" hints | Not in scope |
| Asking the user "should I open a PR via the web UI?" | PR creation is the user's responsibility for non-GitHub remotes |

### Pre-conditions

- All repos must have changes committed and pushed
- Review verdict is PASS (or residuals documented)
- Each repo's current branch is a feature branch (not the default)

### Per-repo PR creation

For each affected code repo (in dependency order):

1. `cd` into the repo directory
2. Push the branch if not already pushed: `git push -u origin HEAD`
3. Use the `github-pr-create` skill to create the PR:
   - Base = the repo's default branch
   - Title reflects the work item (derived from branch name or
     `plan.md` title)
   - Body filled per the repo's PR template (if any), using the code
     changes diff + `plan.md` context
   - Include the Jira ticket reference if available
4. Record the PR URL

PR body filling rules:

- If the repo has a PR template, follow it strictly — only fill
  sections where you have information from the implementation
- Leave screenshot/image placeholders as-is
- Leave unfamiliar link placeholders as-is
- Fill Jira/ticket links and tech doc links from gathered context
  when fields ask for them
- When in doubt, preserve the template's original text

### After all PRs are created

1. **Update `progress.md`** — add a "Pull Requests" section:

   ```markdown
   ## Pull Requests

   | Repository | PR URL | Status |
   |-----------|--------|--------|
   | shared-lib | https://github.com/owner/shared-lib/pull/42 | Created |
   | api | https://github.com/owner/api/pull/99 | Created |
   ```

   (Use Chinese labels for Chinese language work items: `## Pull
   Requests` header stays English; `仓库 / PR 链接 / 状态` for columns.)

2. **Commit** the docs repo with the updated progress.

### Error handling

If `gh pr create` fails for a repo (auth, not a GitHub remote, branch
not pushed, etc.), record the failure in `progress.md` and move on:

```markdown
| api | — | Failed: `gh` error: ... |
```

Do NOT block the entire finalization on one repo's PR failure — create
PRs for all repos that succeed and report failures separately.

## Step 7 — Finalize

### Review completion gate (MANDATORY)

Before finalizing, verify `review.md` contains at least one
`### Verdict` (English) or `### 结论` (Chinese) section from per-repo
staged reviews (Step 4d). For multi-repo work, also verify the
cross-repo review (Step 5) has a verdict. If either is missing,
**STOP** and complete the review.

### Success Criteria gate (MANDATORY)

Verify every Success Criterion in `plan.md` is either met (with
evidence in the `review.md` Evidence table) or explicitly waived with a
documented reason. This is the pre-agreed definition of done — do not
finalize with unmet criteria silently dropped.

### Four-file consistency gate (MANDATORY)

Verify all four documents exist and are internally consistent:

1. All four files exist and are non-empty
2. `analysis.md` recommended approach matches `plan.md` chosen approach
3. `plan.md` tasks match `progress.md` completed/in-progress items
4. If review found issues that changed the approach, are `analysis.md`
   and `plan.md` updated to reflect the final state?

Then run the **Mermaid Compatibility Gate** against EVERY `.md` file in
the work directory that contains ` ```mermaid ` blocks. If `STATUS=FAIL`
on any, fix and re-run; do NOT finalize with broken diagrams. See
[`document-templates.md`](references/document-templates.md#mermaid-1023-compatibility).

### Finalization steps

After review passes (and PRs created in Step 6 if applicable):

1. **Update `analysis.md`** if the review cycle or implementation
   changed the technical approach (add an "Updated" date and note what
   changed).
2. **Update `progress.md`** — add final changelog entry recording the
   completed work and PR links.
3. **Update `plan.md`** — check off all completed tasks.
4. **Fill the Evidence table** in `review.md` — map each Success
   Criterion to concrete proof (test results, PR links, screenshots).
5. **Push feature branches** in each affected code repo so the user has
   reviewable code on the remote, regardless of whether PRs were created
   in Step 6:

   ```bash
   cd <repo-dir>
   git push -u origin HEAD
   ```

   (If Step 6 already pushed, this is a no-op.)
6. **Commit** the docs repo with all tracking doc updates.
7. **Report to user** — the report format depends on the `github_repos`
   value announced at the top of the session:

   **If `github_repos=true`** (PRs were created in Step 6):

   ```
   Implementation complete. Pull Requests created:

     1. shared-lib — https://github.com/owner/shared-lib/pull/42
     2. api       — https://github.com/owner/api/pull/99
     3. web       — https://github.com/owner/web/pull/77
   ```

   **If `github_repos=false`** (Step 6 was skipped — non-GitHub remote):

   ```
   Implementation complete. Branches pushed (PR creation is your
   responsibility — non-GitHub remote):

     1. shared-lib — feat/Dark-Mode-Toggle  (pushed to origin)
     2. api       — feat/BE-450/Dark-Mode-Toggle  (pushed to origin)
   ```

   For `github_repos=false`, do NOT construct or guess merge-request /
   compare URLs, shell out to `glab` / Gitee CLIs / Bitbucket CLIs, parse
   `git push` output for "Create pull request" hints, or ask the user
   "should I open a PR via the web UI?" Just push the branches, list
   them, and stop.

8. **Remind the user** that the work item is ready to archive:

   ```
   The work item is complete. Tell me "archive it" when you're ready
   to move it into changes/archive/ (fullstack-archive).
   ```

## After Finalization — Follow-up Edits

Round 0 is not necessarily the end. Manual testing, pasted error logs,
code review feedback, QA pushback, edge cases, or new tiny requirements
all produce follow-up edits to the same work item.

When the user gives any feedback / fix / log on the same work item
(before it is archived), run the same loop on the existing work
directory:

1. Read the four documents to understand current state.
2. Determine which repos/files are affected.
3. For each repo: developer → reviewer loop (Steps 4b–4e).
4. Update `progress.md` (new dated entry) and `review.md` (new review
   round) after each edit.
5. Update `plan.md` Success Criteria if scope genuinely changed (with
   user awareness).
6. Re-run the Mermaid gate and four-file consistency check.

Do NOT downgrade the discipline because the change is small. Every
code-touching round gets a progress entry and a review round.

**After the user archives the item** (via `fullstack-archive`), any new
request on the same scope creates a NEW work item — never reopen an
archived directory. If the new work continues the archived one, plan a
`<name>-vN` successor via `fullstack-propose`.

## Resuming Previous Work

When the user references an existing work directory:

1. Read all four documents to understand current state.
2. Check which tasks in `plan.md` are incomplete.
3. Verify branches still exist in the affected repos.
4. If repos are already on the correct branch, skip checkout.
5. Re-enter from the last incomplete step recorded in `progress.md`.

## Error Handling

- **Test failures**: Fix test failures caused by your changes before
  moving to the next repo. Re-run tests in the correct environment
  (venv, nvm, etc.) until they pass. Do not skip to the next repo with
  broken tests.
- **Environment issues**: If a venv is missing, node version is wrong,
  or dependencies can't be installed, check the repo's README for setup
  instructions. If setup fails, note in `progress.md` and ask.
- **Cross-repo contract mismatch**: If a downstream repo's tests fail
  because an upstream repo's API changed unexpectedly, go back and fix
  the upstream repo first, then re-validate downstream.
- **Pre-existing failures**: Document pre-existing failures in
  `progress.md` but do not block on them.
- **Unexpected blockers**: Update `progress.md` with details and ask the
  user.

## Requirements

- Python 3.10+
- Workspace initialized by `fullstack-init` (must pass workspace
  validation gate: `fullstack.json` + `AGENTS.md` + `.agents/` all
  present)
- A planned work item under `changes/{feat,refactor,fix}/` (produced by
  `fullstack-propose`)
- Other skills as needed: `jira`, `confluence`, `gh-operations`, `figma`
- For PR creation (Step 6): `github-pr-create` skill + `gh` CLI
  installed and authenticated (only when `fullstack.json` has
  `"github_repos": true`)

## Guardrails

- This skill implements; it does not plan. No work directory → run
  `fullstack-propose` first.
- The four documents and Success Criteria gate are mandatory — do not
  finalize with unmet criteria silently dropped.
- Only the orchestrator writes files from subagent output.
- The docs repo does NOT use feature branches.
- Never reopen an archived work directory; successors are new `-vN`
  work items via `fullstack-propose`.
- Mermaid gate must PASS before finalizing.
