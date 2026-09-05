---
name: fullstack-apply
description: |
  Implement a planned work item across a multi-repo fullstack workspace —
  implement repos in dependency-order waves (independent repos are
  developed, reviewed, and committed in parallel; dependents wait), run
  staged and cross-repo reviews against the plan's Success Criteria,
  create PRs, and finalize the four work-tracking documents. Input is
  a work directory produced by fullstack-propose; no planning happens
  here. Stays sticky on an active work item: follow-up edits driven by
  user feedback, error logs, manual testing, or bug reports run the
  same review loop even when the user does not re-mention the skill.
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

This skill implements the plan in dependency-order waves — repos with
no mutual dependencies run their develop → review → commit cycles in
parallel, while dependent repos wait for upstream commits. It then
reviews the changes against the plan's Success Criteria (a single
cross-repo review after the final wave), opens PRs, and finalizes the
documents. It does NOT plan — if no work directory exists for the
request, tell the user to run `fullstack-propose` first.

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

### Repos without version control

If a repo has no git metadata (`git rev-parse --git-dir` fails), it
cannot support branches, staging, commits, or diffs. Handle it as
follows for the WHOLE run — do not improvise per step:

- Skip branch creation (this step), staging (`git add .`), commit
  (4e), PR creation (Step 6), and branch push (Step 7). The repo
  still gets its developer → review loop and its wave position.
- The developer cannot stage, so it MUST return the exact list of
  every file it created or modified, each with a path relative to the
  repo root — that list replaces the staged diff in every later step.
- Review (4d) runs over that file list — the reviewer reads the named
  files instead of a diff. If reviewer delegation is impossible, the
  orchestrator may self-review, and the review section must say so
  explicitly ("orchestrator self-review").
- In `review.md`, its per-repo section records a `### Changed files`
  / `### 改动文件` list INSTEAD of `### Commits` — one row per file,
  repo-relative path, concrete per-file change description (template
  and rules in
  [`references/review-formats.md`](references/review-formats.md)).
  Without git there is no diff and no commit history to inspect
  later, so this list is the only durable change record the team has
  when they commit the repo by hand.
- State in `progress.md` and the final report that the team must
  commit these changes themselves.

## Step 4 — Implement (dependency-wave parallel delegation)

You are the **orchestrator**. Manage the high-level flow, confirm
decisions with the user, and delegate detail work to subagents. Do NOT
try to "become" the developer or reviewer — delegate to them.

### The wave model

Implementation is organized into **waves** computed from the plan's
`Affected Repositories` table (`Depends On` column). Repos in the same
wave share no dependency edges; each runs its full
develop → review → commit cycle **in parallel** with its wave
siblings. A wave is a barrier: the next wave starts only when every
repo in the current wave has committed.

```text
plan DAG:   shared-lib ← api ← web
                        api ← android

Wave 1:  shared-lib                (no deps)
             │ commit + gate
Wave 2:  api                       (deps committed)
             │ commit + gate
Wave 3:  web ∥ android             (mutually independent → parallel)
             │ all committed
Step 5:  ONE cross-repo review     (the single global barrier)
```

**Why waves instead of strict serial:** dependency order is respected
where it exists (downstream compilation/tests need upstream code), but
repos the planner already analyzed as independent stop paying each
other's latency. The plan's `Depends On` column IS the parallelization
decision — made at planning time, honored mechanically here.

**Quality invariants that do NOT change with parallelism** (parallelism
changes *when* work happens, never *whether* checks happen):

1. Every repo still gets staged review before its own commit.
2. Downstream work never sees unverified upstream code — the wave gate
   releases dependents only after upstream commits.
3. The cross-repo consistency review (Step 5) still sees ALL repos'
   final diffs together, once, after everything is done.
4. Success Criteria gate, Mermaid gate, four-file consistency: untouched.

**Degeneration property:** a fully-chained plan produces waves of size
1 → behavior identical to serial implementation. Wave width = degree of
parallelism; there is no case where the wave model is less safe than
serial, only faster when width > 1.

### Agent roles and boundaries

| Agent | Owns | Must NOT touch | Invoked by |
|-------|------|----------------|------------|
| **planner** | `analysis.md` content, `plan.md` content | Source code files | Orchestrator (you) |
| **developer** | Production code, test files, env setup | `review.md`, `progress.md` | Orchestrator (you) |
| **reviewer** | Review findings (per-repo + cross-repo) | Source code files | Orchestrator (you) |
| **debugger** | Root-cause analysis + fix spec (fix-type plans, and escalation for non-obvious failures); temporary debug instrumentation | `plan.md`, commits | Orchestrator (you) |
| **orchestrator (you)** | `progress.md`, `review.md` (append agent output), PRs, user communication | — | The user |

**Key rules:**
- Only the **orchestrator writes files** from subagent output. Subagents
  return structured results; you write them to the work directory. This
  single-writer rule is what makes parallel delegation safe — parallel
  developers never share mutable state.
- The **reviewer is invoked for BOTH** per-repo review and cross-repo
  review. One reviewer role, two modes; per-repo reviewers run as
  separate parallel instances.
- The **developer** handles implementation + validation per repo and
  returns results. You don't write code in the main agent.
- If a repo has its own `.agents/agents/` (repo-level agents), prefer
  them for that repo's concerns — pass them the same context and delegate.
- **One repo, one agent at a time.** Never delegate two agents into the
  same repository concurrently — even a read-only reviewer overlapping a
  developer risks racing git index state./repos are the unit of isolation.

### Wave computation — MANDATORY SCRIPT CALL

Do NOT layer repos by eyeballing the table — transitive dependencies and
cycles are silent failure modes when judged by eye. Immediately after
Step 3's branch confirmation, run `compute_waves.py` from this skill's
bundled `scripts/` directory on the work directory:

```bash
python3 SKILL_PATH/scripts/compute_waves.py <docs-dir>/changes/<type>/<work-name>
```

Output is machine-readable:

| Output | Meaning | Action |
|--------|---------|--------|
| `REPOS=<n>` / `WAVES=<k>` / `WAVE_i=a,b` | Layered plan | Announce waves to the user, then implement per wave |
| `ERROR_NO_REPOS_TABLE=…` | plan.md missing/broken repositories table | STOP — send back to fullstack-propose |
| `CYCLE_REPOS=a,b,…` | Dependency cycle in the plan | STOP — cycles cannot be ordered; replan via fullstack-propose |
| `ERROR_UNKNOWN_DEP=repo: ghost` | Depends On references a repo not in the table | STOP — incomplete table; fix the plan first |
| `ERROR_DUPLICATE_REPO=x` / `ERROR_SELF_DEPENDENCY=x` | Malformed rows | STOP — fix the plan first |

Any `ERROR_*` or `CYCLE_REPOS` output is a hard stop: the plan's DAG is
the contract every later step trusts. Re-run fullstack-propose for that
work item before applying. Do NOT hand-patch the ordering yourself.

Announce the computed waves to the user together with the Step 2
confirmation, e.g.:

```
Wave plan (from plan.md dependency table):
  Wave 1: shared-lib
  Wave 2: api                (waits for shared-lib commit)
  Wave 3: web ∥ android      (parallel — no mutual deps)
```

### Per-wave implementation loop

For each wave, in order (`WAVE_1`, then `WAVE_2`, …):

#### 4a. Assemble self-contained per-repo briefs

Before delegating, build one **brief per repo** so each developer
subagent can work without asking you follow-up questions. Each brief is
a slice of the plan, not the whole thing:

- The repo's row from the `Affected Repositories` table + its tasks
  from `plan.md`
- The Success Criteria that THIS repo's evidence will prove
- The relevant sections of `analysis.md` (design decisions, contracts,
  target architecture)
- For consumers: the **frozen contract** from `analysis.md` for every
  upstream interface it integrates with (field names, types, error
  codes). Frozen means downstream code targets exactly these names —
  not whatever upstream happened to write on the day.
- The repo's branch name and its wave position ("wave N of k")
- Work-dir path and where progress/review updates go (return them —
  you, the orchestrator, write the files)

Do NOT paste the whole four documents into every brief — parallel
developers duplicate context cheaply, and unfocused briefs are how
parallel agents drift out of scope.

#### 4b. Delegate developer subagents — all repos of a wave in parallel

In ONE turn, delegate every repo of the current wave to its developer
subagent (they own disjoint repositories — there is nothing to race
on). If the host runs delegates serially despite the single-turn fan
out, they still run in wave order — correctness is unaffected; only
wall-clock time changes.

Each developer subagent MUST, inside its own repo:

1. **Read repo conventions first**: `AGENTS.md` (coding style, commit
   format, architecture constraints — MANDATORY), then `README.md`
   (build / test / lint commands). When both document tests,
   `AGENTS.md` wins over `README.md`.
2. **Check for repo-level agents** at `<repo>/.agents/agents/` — if the
   repo has specialized agents, defer internal details to them.
3. **Check for `graphify-out/`** — run
   `python3 SKILL_PATH/scripts/graphify_check.py <repo>`. When present,
   the developer MUST use `graphify query "<question>"` to understand
   the codebase before reading individual files.
4. **Determine the repo's test harness** — language-agnostic:
   1. **README.md / AGENTS.md** documents how to run tests (`pytest` /
      `go test` / `npm test` / `cargo test` / `mix test` / `dotnet
      test` / `bundle exec rspec` / …) → that is the command.
   2. Conventional test layout exists (`test*/`, `spec/`,
      `__tests__/`, `tests/`, `*_test.*`, `*.spec.*`) but no documented
      command → tests exist but can't be run reliably; record that.
   3. No evidence at all → classify **no-test**.
5. Set up the repo environment (venv, nvm, etc.)
6. Implement the changes following repo conventions and the brief.
7. Run lint → type-check → tests → build, **limited to what the repo
   supports.** If a test command is documented, run it and report what
   ran and whether it passed. Never invent or run a guessed test
   command — see 4c for reporting codes.
8. Do NOT start long-running dev servers or listen on ports — parallel
   siblings would collide.
9. Stage all changes (`git add .`). A repo without version control
   cannot stage — it records the changed-file list instead (see Step
   3 "Repos without version control") and returns it in the summary.
10. Return: summary of changes, test result code (`tests: passed` /
    `tests: failed` / `tests: unknown (no run command documented)` /
    `tests: none`), any deviation from the frozen contract it observed
    upstream, and a recommended commit message

#### 4c. Handle developer output — failure isolation

Handle each repo's output as it returns; never block healthy siblings
on a broken one:

1. **Tests ran and passed** → record in `progress.md`, proceed to 4d.
2. **Tests ran and failed** → send THAT repo back to ITS developer
   with the failure details until passing. The fix loop is scoped to
   the failing repo; other repos of the wave continue untouched. A red
   repo does NOT release its dependents (see the wave gate in 4e).
3. **Tests exist but no run command documented** (`tests: unknown`) →
   record an explicit `tests: unknown (no run command in <repo>
   README/AGENTS)` note in `progress.md`, flag it in review so the gap
   is visible — these tests weren't executed. Mention the gap in the
   final report and offer to add the test run command to the repo's
   `AGENTS.md` — but never edit any repo document yourself without the
   user's explicit approval.
4. **No tests at all** (`tests: none`) → record an explicit
   `tests: none (<repo> has no test harness)` note in `progress.md`.
   Untested code must never pass silently.
5. Write each completed summary to `progress.md`, then proceed to
   staged review for that repo.

#### 4d. Per-repo staged review — delegate to a reviewer subagent per repo

As soon as a developer has staged changes in a repo, delegate to a
**reviewer** subagent for that repo's staged review — reviewers of
different repos run as parallel instances and never wait for each
other:

1. Provide the reviewer with: `plan.md` (especially Success Criteria),
   `analysis.md`, `progress.md`, the same frozen-contract sections from
   4a, and the staged diff (`git diff --cached` in the repo) — for a
   repo without version control, the changed-file list from 4b instead
   (see Step 3 "Repos without version control").
2. The reviewer returns findings in P0/P1/P2 format with a verdict
   (PASS / PASS_WITH_RISKS / NEEDS_FIXES / FAIL), scoped to its repo.
3. You append the reviewer's output to `review.md`.
4. **If NEEDS_FIXES**: send the P0/P1 items back to THAT repo's
   developer subagent. Developer fixes → re-validates (lint/test/build)
   → stages (`git add .`). Then invoke its reviewer again. Max 3 rounds
   total, tracked per repo. If the same P0/P1 survives one developer
   fix round, or its cause is not evident from the diff, delegate to
   the **debugger** subagent for that repo first (root cause + fix
   spec, scoped-edit rules) and route its findings through the same
   developer → reviewer loop.
5. **If PASS**: proceed to commit for that repo.

#### 4e. Commit per repo, then the wave gate

Commit each repo individually as it passes review (do not hold a green
repo hostage to a red sibling):

```bash
cd <repo-dir>
git commit -m "<message>"
```

- Use the commit message from the developer subagent's summary. If the
  repo has its own convention (from `AGENTS.md`), reconcile — repo
  convention wins.
- A repo without version control has nothing to commit — its
  `### Changed files` section in `review.md` is the change record
  (Step 3). Skip the commit; note in `progress.md` that the team
  commits by hand.
- Update `progress.md` with the commit summary and review verdict.
- Run `python3 SKILL_PATH/scripts/graphify_check.py <repo>` — if
  `graphify-out/` exists, `cd` into the repo and run `graphify update`.

**Wave gate — before releasing wave N+1**, verify ALL of the following.
This is where the harness refuses downstream work on unproven upstream
code:

1. Every repo of wave N is committed (not merely staged or "done"
   according to an agent's say-so).
2. Any frozen contract items belonging to wave-N repos were compared
   against what was actually implemented: if upstream drifted from the
   contract (renamed field, changed type, different error code), fix
   upstream NOW via its dev→review loop, or freeze the actual shape as
   an explicit contract amendment recorded in `analysis.md` — do NOT
   let downstream guess which one applies.
3. Downstream briefs are refreshed with any amended contracts before
   their developers start.

After the final wave's gate passes → proceed to Step 5.

## Step 5 — Cross-Repo Consistency Review (multi-repo only)

Skip this step for single-repo work. For multi-repo, this is **the one
global barrier** of the whole implementation: after the final wave's
gate, delegate to the **reviewer** subagent in cross-repo mode to
verify changes are consistent across all affected repos. Per-repo
staged reviews (4d) never substitute for it — each saw only its own
diff; integration defects live between diffs.

### 5a. Collect cross-repo context

For each affected repo:

```bash
cd <repo-dir>
git diff <default-branch>...<feature-branch>
```

For a repo without version control, there is no diff — provide its
`### Changed files` list from `review.md` plus direct reads of the
named files instead (see Step 3 "Repos without version control").

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
1. Fix upstream repo first, then downstream (topological order — the
   wave plan from Step 4 is the order).
2. For each repo needing fixes, go through its scoped developer →
   reviewer loop again (Steps 4b through 4e). Fixes to MUTUALLY
   INDEPENDENT repos may fan out in parallel, exactly like a normal
   wave.
3. Re-run the cross-repo review after all fix repos pass.
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

PR creation is per-repo with no cross-repo interaction — create the PRs
for all affected repos in parallel (or sequentially when the host
runs one command at a time). For each repo:

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

Evidence is one of `✅ Pass` / `❌ Fail` / `⚠️ Skipped`. Where a criterion
can be proven only by a test run but the tests were not run — no test
harness in the repo, or a test layout exists but no run command is
documented — mark it `⚠️ Skipped (no verified test run in <repo>)` —
never `✅ Pass`. Untested is unproven; record the gap explicitly rather
than claiming a result.

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

   (If Step 6 already pushed, this is a no-op. Skip repos without
   version control — see Step 3.)
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

## Step 8 — Lessons Learned (optional, value-gated)

The four work-tracking documents already record **what happened**. This
step exists to convert a genuinely new, transferable insight into the
docs repo's knowledge so a future session does not rediscover it the
hard way. It is optional and value-gated — most work items produce no
lesson, so a deliberate skip is the correct default, never a default of
"fill a template". Write a lesson when any of these is true:

1. **Non-obvious trap / gotcha** that cost real implementation or review
   time — a library quirk, an ordering or dependency constraint the plan
   did not surface, a silent failure mode.
2. **Cross-repo / cross-tool constraint** that will affect similar
   future work — an env var required by two repos, a build step, a
   migration ordering, a service boundary invariant.
3. **A design decision whose rationale is non-obvious** — one that took
   deep analysis or a falsified hypothesis to reach. If the reasoning is
   already self-evident in `analysis.md`, do not duplicate it.
4. **A recurring mistake corrected** — a bug you misdiagnosed at least
   once, so the correction (and how to recognize the symptom early) is
   worth preserving.

Skip (the default) when the lesson is really just the work item itself —
that belongs in `progress.md` / `review.md`, not in a knowledge doc — or
when the topic is already recorded elsewhere in the docs repo: update
that existing doc, don't create a duplicate.

### Where to put it — follow the docs repo's own structure

Do NOT impose a fixed lessons directory or a generic name like
`lessons-learned/`. First explore the docs repo's existing knowledge
layout (the directories beside `changes/`, e.g. `docs/` organized by
domain / architecture / platform). Find where this work's insight
naturally belongs — the doc for the component, the architecture or
platform section, the topic folder it extends. Write the lesson there
following that area's existing convention: append a `## <Title>`
subsection, add to an existing topic file, or create a domain file if
none exists.

Only when no existing place fits, create a directory named for the
lesson's own subject — the topic the insight actually covers, not a
generic bucket. Choose a concise lowercase-hyphenated name (the repo's
naming convention) that a future reader would search for, e.g.
`docs/<subject>/<subject>.md`. Write the lesson there, short: what you
learned, why it matters, and the guard to apply. Reuse the same file or
directory for later lessons on the same subject rather than inventing a
new name.

When in doubt, ask the user where the lesson belongs before creating a
new directory — do not guess a location the team then has to relocate.

### Record the outcome

- **If you wrote a lesson**, append one bullet to the final entry in
  `progress.md`: `- Captured insight to <relative path> — <summary>`
- **If you deliberately skipped**, record nothing. The absence is the
  correct, intentional outcome and needs no justification entry.

Commit the docs repo (with any captured insight) in the same Step 7
finalization commit.

## After Finalization — Follow-up Edits

Round 0 is not necessarily the end. Manual testing, pasted error logs,
code review feedback, QA pushback, edge cases, or new tiny requirements
all produce follow-up edits to the same work item.

When the user gives any feedback / fix / log on the same work item
(before it is archived), run the same loop on the existing work
directory:

1. Read the four documents to understand current state.
2. Determine which repos/files are affected. If the reported problem is
   a failure whose cause is not obvious (misleading symptoms, suspected
   cross-repo boundary, no identifiable introducing change), delegate
   to the **debugger** subagent for root-cause analysis first and fold
   its findings into the briefs. Obvious, change-caused failures go
   straight into the wave loop.
3. Re-run `compute_waves.py` on the affected repos, then run the same
   wave loop: parallel developer → reviewer cycles (Steps 4a–4e).
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
   Waves still apply on resume: recompute waves with `compute_waves.py`
   and resume per wave — a partially completed wave reruns only its
   unfinished repos.

## Error Handling

- **Test failures**: Fix test failures caused by your changes before
  committing that repo (scoped dev→review loop, 4c). Never commit a red
  repo, and never release its dependents — but do not block sibling
  repos of the same wave from finishing their own cycles.
- **Non-obvious failures**: when a failure's cause is not evident —
  symptoms contradict the diff, a cross-repo boundary is suspected, or
  a developer fix round did not make the tests pass — delegate the
  **debugger** subagent for root cause before another developer round.
  Do not "try and see".
- **Environment issues**: If a venv is missing, node version is wrong,
  or dependencies can't be installed, check the repo's README for setup
  instructions. If setup fails, note in `progress.md` and ask.
- **Cross-repo contract mismatch**: If a downstream repo's tests fail
  because an upstream repo's API changed unexpectedly, go back and fix
  the upstream repo first, then re-validate downstream. Prevent this
  class of bug upstream of apply by freezing contracts in the plan
  (fullstack-propose) and at every wave gate (4e).
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
- Waves come from the script, not from judgment: always derive wave
  order via `compute_waves.py`; on any structural error (cycle,
  unknown/duplicate/self dependency) STOP and send the work item back
  to fullstack-propose instead of hand-ordering.
- Parallelism only between repos with no dependency path between them;
  a dependent repo starts strictly after its upstream commits pass the
  wave gate. One repo is never worked by two agents concurrently.
- Every repo keeps its own staged review before commit, regardless of
  parallelism; a red repo never releases its dependents but also never
  blocks independent siblings.
- A repo without version control gets a `### Changed files` record in
  `review.md` — one row per file, repo-relative path, concrete per-file
  change description — never a compressed prose list. That list is the
  team's only change record for a repo they must commit by hand.
- The cross-repo consistency review runs ONCE over all repos' final
  diffs — per-repo reviews do not substitute for it.
- Subagents must not start long-running servers or occupy ports during
  parallel waves.
- The docs repo does NOT use feature branches.
- Never reopen an archived work directory; successors are new `-vN`
  work items via `fullstack-propose`.
- Mermaid gate must PASS before finalizing.
