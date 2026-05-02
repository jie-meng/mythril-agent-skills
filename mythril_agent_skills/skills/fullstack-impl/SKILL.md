---
name: fullstack-impl
description: |
  Implement features, refactors, and fixes across a multi-repo fullstack
  workspace — gather context, branch, implement, review, create PRs,
  keep iterating after finalization, open follow-up work on closed
  shipped work, or read prior work as background context. Once a work
  item exists under docs (feat/refactor/fix), this skill stays sticky:
  every follow-up edit driven by user feedback, error logs, manual
  testing, or bug reports MUST run the same staged-review +
  four-doc-sync loop, even when the user does not re-mention the skill.
  Trigger: "fullstack implement", "fullstack develop", "fullstack impl",
  "全栈实现", "全栈开发", "全栈 impl"; ALSO on follow-up edit/fix in
  an active work dir — "this is wrong", "fix this", "调一下",
  "再改一下", "这里不对", "log 报错", pasted error/log; ALSO on
  extending a closed work item — "follow up on X", "extend X",
  "在 X 基础上"; ALSO on reading prior work as context —
  "look at feat/X", "参考 feat/X", "based on X docs"; or when scope
  matches a closed dir under docs/{feat,refactor,fix}/.
license: Apache-2.0
---

# Fullstack Implementation

Implement features, refactors, and fixes across a multi-repo fullstack
workspace that was initialized by `fullstack-init`. This skill handles
the full lifecycle: gather context, plan, create branches, implement
across repos, review, track progress, and keep iterating after
finalization.

## How this skill is organized

This `SKILL.md` covers the main flow (Steps 1-9) end-to-end. Cross-cutting
concerns and lifecycle modes live in the `references/` directory and
are loaded by reading the file when relevant:

| File | Read when |
|------|-----------|
| [`references/mode-selection.md`](references/mode-selection.md) | At Step 1 to route the request among Fresh / Reference / Iteration / Follow-up |
| [`references/document-templates.md`](references/document-templates.md) | At Step 5 to write the four work-tracking documents (templates + Mermaid Compatibility Gate) |
| [`references/review-formats.md`](references/review-formats.md) | At Step 6e and Step 7 to format review sections in `review.md` |
| [`references/iteration-mode.md`](references/iteration-mode.md) | After Step 9, when the user gives any feedback / bug / log on the same work item |
| [`references/followup-mode.md`](references/followup-mode.md) | When the user extends a closed work item (`-v2` / `-vN` directory) |
| [`references/reference-mode.md`](references/reference-mode.md) | When the user wants to read prior work as background but the new work is independent |

Always read the files relevant to the current step. They are concise
on purpose; do not skim.

## Prerequisites — Workspace Validation Gate (MANDATORY SCRIPT CALL)

This skill MUST NOT proceed past this gate. Before reading any work
directory or planning anything, run `check_workspace.py` and inspect
its output. This is a hard precondition — skipping the script and
"checking files manually" is forbidden, because the script also reports
`docs_dir` and `github_repos` which are needed in Step 1d and Step 8.

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/fullstack-impl/scripts/check_workspace.py",
    pathlib.Path.home() / ".claude/skills/fullstack-impl/scripts/check_workspace.py",
    pathlib.Path.home() / ".copilot/skills/fullstack-impl/scripts/check_workspace.py",
    pathlib.Path.home() / ".cursor/skills/fullstack-impl/scripts/check_workspace.py",
    pathlib.Path.home() / ".gemini/skills/fullstack-impl/scripts/check_workspace.py",
    pathlib.Path.home() / ".codex/skills/fullstack-impl/scripts/check_workspace.py",
    pathlib.Path.home() / ".qwen/skills/fullstack-impl/scripts/check_workspace.py",
    pathlib.Path.home() / ".grok/skills/fullstack-impl/scripts/check_workspace.py",
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
| `GITHUB_REPOS=true\|false` | Whether Step 8 should create PRs |
| `CONFIG_FOUND=true\|false` | Was fullstack.json found? |
| `CONFIG_PATH=<path>` | Full path to the config that was read |

Decision logic:

- `WORKSPACE_VALID=true` → record `DOCS_DIR` and `GITHUB_REPOS` for later
  steps, then proceed to Step 1
- `WORKSPACE_VALID=false` → STOP and tell the user:

  > **Workspace not detected.** This skill requires a fullstack
  > workspace initialized by `fullstack-init`. Missing markers:
  > _(list from `MISSING=`)_.
  >
  > Please `cd` to your project workspace root and restart your AI
  > agent there, or run `fullstack-init` first to set up the workspace.

This gate exists because `fullstack-impl` relies on the workspace
structure (repo table in AGENTS.md, agent definitions in .agents/,
docs directory config in fullstack.json) to function correctly. The
script also eliminates a class of LLM failures: skipping the gate
because "the directory looks like a workspace", or running the gate but
mis-reading whether `.agents/` is a file vs a directory.

## Document Language Selection

All four work-tracking documents (`analysis.md`, `plan.md`,
`progress.md`, `review.md`) and user-facing messages MUST match the
language of the user's prompt.

1. If the user **explicitly requests a language** → use that language.
2. If the user's prompt contains **any Chinese characters** → use Chinese.
3. Otherwise → use English (default).

This rule applies independently per invocation. Different work items
in the same docs repo may use different languages — that is fine.

**What this affects**: section headers, content, confirmation
messages, completion reports.
**What this does NOT affect**: branch names (always English
Title-Case-With-Hyphens), work directory names (always
lowercase-hyphenated English), Markdown structure, Git commit messages
(follow each repo's own convention).

## Step 1 — Gather Context and Route

Before any implementation work, gather context AND determine which
mode to run in.

### 1a. Read external links in the user's prompt

For each link, use the corresponding skill:

| Link type | Skill | What to extract |
|-----------|-------|-----------------|
| Jira URL or issue key (e.g. `PROJ-123`) | `jira` | Summary, description, acceptance criteria, subtasks |
| Confluence URL | `confluence` | Page content, requirements, specs |
| GitHub PR/issue URL | `gh-operations` | Description, comments, linked issues |
| Figma URL | `figma` | Design specs, components, layout, colors, typography |

Read ALL linked resources BEFORE proceeding. Do not start planning
with incomplete context.

### 1b. Read workspace context

From the workspace root:

1. **`fullstack.json`** — get the docs directory name and the
   `github_repos` flag (decides whether PRs will be created in Step 8)
2. **`AGENTS.md`** — repo table, conventions, structure
3. **`<docs-dir>/AGENTS.md`** — documentation conventions

### 1c. Read prior spike context (if mentioned)

If the user references a spike (e.g. "implement based on the spike",
"基于 spike 结果实现"), or mentions a name that exists under
`<docs-dir>/spike/`, read all three spike documents:
`analysis.md`, `findings.md`, `verdict.md`. Use them as **additional
context** for planning. The work-directory `analysis.md` is still
required (four-file invariant) — it may reference the spike's
analysis instead of repeating it. Record the spike reference in
both `analysis.md` and `plan.md` under the `Source` field.

The spike may have left temporary code changes in the affected repos.
These are **not committed**. Run `git checkout .` in affected repos
before creating feature branches, unless the user explicitly says to
keep the spike changes.

### 1d. Determine routing — MANDATORY two-step protocol

This step has been the #1 source of skill failures (wrong Mode →
wrong workflow → no audit trail). To eliminate the failure mode, this
step is now a **strict two-step protocol**: run a deterministic helper
script first, then announce the chosen Mode in a fixed format BEFORE
doing anything else.

#### Step 1d-i. Run `route_check.py`

If the user's prompt mentions a work directory by name (e.g.
`@<docs-dir>/feat/X/`, "feat/X", or just "X"), pass it as
`--work-dir-name`. If no name is mentioned, pass empty. ALWAYS pass
the user's prompt via `--prompt` so the script can detect verbs.

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/fullstack-impl/scripts/route_check.py",
    pathlib.Path.home() / ".claude/skills/fullstack-impl/scripts/route_check.py",
    pathlib.Path.home() / ".copilot/skills/fullstack-impl/scripts/route_check.py",
    pathlib.Path.home() / ".cursor/skills/fullstack-impl/scripts/route_check.py",
    pathlib.Path.home() / ".gemini/skills/fullstack-impl/scripts/route_check.py",
    pathlib.Path.home() / ".codex/skills/fullstack-impl/scripts/route_check.py",
    pathlib.Path.home() / ".qwen/skills/fullstack-impl/scripts/route_check.py",
    pathlib.Path.home() / ".grok/skills/fullstack-impl/scripts/route_check.py",
]
script = next((p for p in candidates if p.exists()), None)
result = subprocess.run(
    [
        sys.executable, str(script),
        "--workspace-root", "<workspace-root>",
        "--work-dir-name", "<name-or-empty>",
        "--prompt", "<the user's prompt verbatim>",
    ],
    capture_output=True, text=True,
)
print(result.stdout)
```

The script outputs a deterministic recommendation:

| Key | Meaning |
|-----|---------|
| `ROUTE=Fresh\|Reference\|Iteration\|Followup\|Resume\|AskUser` | Recommended Mode |
| `WORK_DIR=<path>` | Absolute path of the matched work directory (empty if no match) |
| `WORK_TYPE=feat\|refactor\|fix\|<empty>` | Work type from the directory layout |
| `STATUS_NORMALIZED=Planning\|InProgress\|Done\|Closed\|Unknown\|<empty>` | Plan.md Status mapped to a fixed enum |
| `STATUS_RAW=<text>` | Original Status text from plan.md (for transparency) |
| `HAS_SUCCESSORS=true\|false` | Does progress.md have a `## Successors` table? |
| `LATEST_SUCCESSOR=<path>` | Most recent successor link, if any |
| `ITERATION_LOG_FOUND=true\|false` | Does progress.md already have an Iteration Log section? |
| `TRIGGERS_DETECTED=read\|followup\|iteration\|resume\|none` | Verbs found in the prompt |
| `RECOMMENDED_NEXT_DOC=<reference file to read>` | Which reference doc to consult next |

If `LATEST_SUCCESSOR` is non-empty, restart routing against the latest
successor (re-run the script with that name) — followups chain forward,
and the user almost always means the latest link in the chain.

**The script is the source of truth, not the LLM's intuition.** If
`ROUTE=AskUser`, you MUST ask the user the question `mode-selection.md`
provides — do not guess.

#### Step 1d-ii. Announce the Mode (MANDATORY OUTPUT)

After the script returns, output EXACTLY these two lines to the user
before any other action:

```
Mode: <Fresh | Reference | Iteration | Followup | Resume | AskUser>
Reason: <one-line summary including STATUS_NORMALIZED and TRIGGERS_DETECTED>
```

Use English for these two lines regardless of conversation language —
they are machine-readable contract markers, not user-facing prose. The
explanatory text after them follows the user's language.

**Why these two lines are mandatory:**

- They force the agent to commit to a Mode in a structured way.
- They make Mode mismatches obvious to the user at a glance.
- All subsequent actions (which doc to read, which branch convention
  to use, which checklist to run) MUST be consistent with the
  announced Mode. If you announce `Mode: Iteration` but skip the
  Iteration Log update, that is a contract violation visible in the
  transcript.

#### Step 1d-iii. Read the recommended reference doc

Based on `ROUTE`:

| ROUTE | Read this doc next | Then |
|-------|-------------------|------|
| `Fresh` | (none — proceed with Steps 2-9 below) | Standard flow |
| `Reference` | [`references/reference-mode.md`](references/reference-mode.md) | Follow Reference Mode for the rest of the work |
| `Iteration` | [`references/iteration-mode.md`](references/iteration-mode.md) | Follow Iteration Mode (sticky loop, doc sync) |
| `Followup` | [`references/followup-mode.md`](references/followup-mode.md) | Create `-vN` successor with predecessor inheritance |
| `Resume` | (re-enter Step 1-9 from the last incomplete step in `progress.md`) | See "Resuming Previous Work" |
| `AskUser` | [`references/mode-selection.md`](references/mode-selection.md) | Ask the appropriate clarifying question |

Do NOT auto-route to Follow-up Mode based on scope overlap alone. The
agent must see an explicit follow-up verb OR get user confirmation
through the 3-option question. Misrouting Reference as Follow-up is
expensive (modifies a closed dir, creates phantom links). The script
encodes this rule already — trust its `AskUser` outputs.

## Step 2 — Determine Work Type

Classify the work into one of three categories:

| Category | Directory | Branch prefix | When to use |
|----------|-----------|--------------|-------------|
| Feature | `<docs-dir>/feat/` | `feat/` | New features, capabilities, enhancements |
| Refactor | `<docs-dir>/refactor/` | `refactor/` | Code restructuring, tech debt, cleanup |
| Fix | `<docs-dir>/fix/` | `fix/` | Bug fixes, issue resolution |

If ambiguous, ask. For Follow-up Mode, the successor stays in the
same `<type>/` as the predecessor (unless the follow-up is
fundamentally a fix on shipped code — then `fix/` even if predecessor
was `feat/`).

## Step 3 — Identify Affected Repos

### Decision tree

1. **User explicitly listed repos** → use those, but still confirm
2. **User's description implies specific repos** (e.g. "add API
   endpoint" → api repo; "update the dashboard" → web repo) → propose
3. **Ambiguous** → ask explicitly

### Confirmation (MANDATORY)

ALWAYS present your analysis to the user for confirmation, even when
confident. Format:

```
Based on the requirements, I plan to modify these repositories:

  1. shared-lib/ — Add theme constants to shared types
     Branch: feat/Dark-Mode-Toggle
  2. api/ — Add user preference endpoint for theme setting
     Branch: feat/BE-450/Dark-Mode-Toggle
  3. android/ — Add dark mode toggle to settings screen
     Branch: feat/MOBILE-301/Dark-Mode-Toggle

Work type: feat

Does this look correct? You can:
- Confirm to proceed
- Remove repos that shouldn't be changed
- Add repos I missed
- Change the work type or branch names
- Reassign a Jira ticket to a different repo
```

For **Follow-up Mode**, also include the predecessor line: `Predecessor:
feat/dark-mode/` and use `-vN` suffixes on branch names. For
**Reference Mode**, mention the prior work being read as context but
keep the new work's name and branches free of `-vN` suffixes.

Do NOT proceed until the user confirms. If the user corrects you,
update and reconfirm.

## Step 4 — Branch Management

### Branch naming convention

| Scenario | Format | Example |
|----------|--------|---------|
| With Jira key | `<type>/<JIRA-KEY>/<Title-Hyphenated>` | `feat/XYZ-706/Import-Export` |
| Without Jira | `<type>/<Title-Hyphenated>` | `refactor/Refine-Models` |
| Follow-up Mode | append `-vN` to the descriptive part | `feat/MOBILE-580/Dark-Mode-Toggle-v2` |

The descriptive part uses **Title-Case-With-Hyphens**.

### Multiple Jira tickets → per-repo branch names

When the user provides multiple Jira tickets (common in cross-platform
work), each repo may get a different branch name based on which
ticket belongs to which platform.

To match tickets to repos:

1. Read each Jira ticket's title, description, labels, and component
   fields (already gathered in Step 1).
2. Read each repo's identity from the workspace `AGENTS.md` repo
   table; if needed, the repo's own `AGENTS.md` and `README.md`.
3. Cross-reference: match each ticket to the repo whose role/platform
   best fits. Do NOT hardcode keyword lists — use understanding of
   both sides.
4. If a ticket is cross-cutting and doesn't map to a single repo,
   assign it to the most relevant shared/infra repo.
5. If matching is ambiguous, ask.

Each repo gets its own branch name with its own Jira key. Repos
without a matching ticket use the no-Jira format. The `plan.md` MUST
record each repo's specific branch name.

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

For **Follow-up Mode**, the branch source is the repo's **current
default branch**, NOT the predecessor's merged feature branch
(that branch is dead — basing on it inherits stale code).

### The docs repo does NOT use feature branches

The `<docs-dir>/` repo is an independent git repo for work tracking
docs. All work tracking documents are committed directly to its main
branch. Do NOT create feature branches in the docs repo.

## Step 5 — Create Work Plan

Create a work directory under `<docs-dir>/<type>/`:

```
<docs-dir>/<type>/<work-name>/
├── analysis.md   (technical analysis — ALWAYS created first)
├── plan.md       (execution plan — derived from analysis)
├── progress.md   (status tracking — updated throughout)
└── review.md     (review findings — filled during review)
```

For **Follow-up Mode**, the directory is `<work-name>-vN/`. See
[`references/followup-mode.md`](references/followup-mode.md) for the
mandatory `Predecessor` field, `## Predecessor Context` section, and
`## Successors` back-link in the predecessor's `progress.md`.

### Four-File Invariant (MANDATORY)

All four files MUST be created. No exceptions. `analysis.md` is
NEVER optional — even for "trivial" work. A one-page analysis is fine;
a missing analysis is not. Why this is non-negotiable:

1. `analysis.md` is the **foundation** — it captures *why* decisions
   were made and *what* was considered. Without it, the plan has no
   traceable rationale.
2. The four files form a **causal chain**: analysis → plan → progress
   → review. Removing any link breaks traceability.
3. External consumers (human reviewers, future sessions, other
   agents) expect all four files. A missing file signals incomplete
   work.

If the user specifies an external tech doc location, STILL create
`analysis.md` in the work directory alongside the other three. The
content may reference or summarize the external doc, but the file
MUST exist locally — the four files must be co-located and
self-contained.

**Scaling by complexity** — analysis depth should match the work:

| Work complexity | analysis.md depth |
|----------------|-------------------|
| Trivial (typo, config, version bump) | 1-2 sections: brief current state + change rationale |
| Simple (single repo, clear scope) | 3-4 sections: current state, requirements, chosen approach |
| Complex (multi-repo, architectural) | Full template: diagrams, options, trade-offs, risk matrix |

### Agent dispatch — analysis before planning

| Work type | Analysis agent | Analysis focus |
|-----------|---------------|----------------|
| `feat/` | Planner | Requirements flow, architecture design, tech trade-offs |
| `refactor/` | Planner | Current-state analysis, target architecture, migration path |
| `fix/` | Debugger | Root-cause analysis, reproduction, fix strategy |

Sequence:

1. **Read the agent file** — `.agents/agents/planner.md` (feat/refactor)
   or `.agents/agents/debugger.md` (fix).
2. **Write `analysis.md`** — the analysis agent writes the technical
   thinking using the appropriate template.
3. **Then write `plan.md`** — informed by the analysis.

### Templates and Mermaid Compatibility Gate

All four documents follow strict templates (English / Chinese,
identical structure, different labels). See
[`references/document-templates.md`](references/document-templates.md)
for the templates and visualization rules.

After writing any `.md` file containing ` ```mermaid ` blocks, run
the **Mermaid Compatibility Gate** — invoke `mermaid_validate.py` on
every just-written file. The gate is detailed in
[`document-templates.md`](references/document-templates.md#mermaid-1023-compatibility).
Skipping the gate is the single most common cause of broken diagrams
on GitHub Enterprise, Confluence, Notion exports, and internal wikis.

### Work name

Derive from the requirement, lowercase-hyphenated:

- Jira `PROJ-123: Add dark mode` → `add-dark-mode`
- User prompt "implement user search" → `user-search`
- If ambiguous, ask

### Document Lifecycle & Consistency (MANDATORY)

The four documents form a causal chain — each is derived from its
predecessor. When any document is updated, its downstream documents
MUST be checked for consistency and corrected if needed.

```
analysis.md ──→ plan.md ──→ progress.md ──→ review.md
 (why)          (what)       (status)       (quality)
```

| Event | Required sync |
|-------|---------------|
| `analysis.md` updated (new option chosen, risk identified) | Check `plan.md` — update affected tasks, dependencies, risks |
| `plan.md` updated (scope change, repo added/removed) | Check `progress.md` — update task list, status |
| Review finds issues → code fixed | Update `progress.md` (changelog). If fix changes architecture or approach, update `analysis.md` and `plan.md` too |
| Scope change mid-implementation | Update ALL four files: analysis rationale → plan tasks → progress status → review scope |
| **Post-finalization iteration** | Run the full per-iteration doc sync checklist defined in [`iteration-mode.md`](references/iteration-mode.md) |

Consistency checkpoints — verify at:

1. **Before Step 6 starts** — `analysis.md` conclusions match
   `plan.md` approach (no stale divergence from prior edits)
2. **After cross-repo review (Step 7)** — if review findings require
   architectural changes, propagate back to `analysis.md` and `plan.md`
3. **During finalization (Step 9)** — all four files reflect the
   final state
4. **After EVERY iteration round** (post-finalization) — run the
   per-iteration doc sync; finalization is NOT the end of the
   discipline, it is just the end of round 0

**Anti-pattern**: updating `review.md` with fix information but
leaving `analysis.md` and `plan.md` stale. If a review-driven fix
changes the technical approach, ALL upstream documents must reflect
that change. This is most dangerous in the post-finalization phase,
where small fixes accumulate without anyone re-reading the analysis
— see [`iteration-mode.md`](references/iteration-mode.md).

## Step 6 — Implement

### Orchestration model — serial per-repo

Implementation follows a **serial per-repo** strategy: repos are
modified one at a time, in the dependency order from `plan.md`. This
is the default — even when the work seems parallelizable.

Why serial:

1. Cross-repo dependencies are the norm (shared types → API →
   consumers). Parallel agents can't see each other's WIP, leading
   to contract mismatches.
2. The developer accumulates cross-repo context naturally — what was
   built in repo A informs what needs to happen in repo B.
3. Shared docs (`progress.md`) can't be safely written concurrently.
4. Debugging failures is simpler with a clean sequential audit trail.

**Exception — truly independent repos**: If the planner explicitly
confirms ZERO shared interfaces, ZERO data model overlap, and ZERO
dependency edges, repos MAY be implemented in parallel via sub-agents.
The planner must document this independence in `plan.md`. When in
doubt, default to serial.

### Agent roles

| Agent | Writes | Reads | Never touches |
|-------|--------|-------|---------------|
| Planner | `analysis.md` (feat/refactor), `plan.md` | everything | source code, `review.md` |
| Debugger | `analysis.md` (fix) | everything | `plan.md`, `review.md` |
| Developer | source code, `progress.md`, `review.md` (append review output) | `analysis.md`, `plan.md` | — |
| `code-review-staged` (skill) | (output consumed by developer) | staged diff, repo context | — |

**Agent hierarchy**: workspace agents (`.agents/agents/`) handle
cross-repo coordination; repo-level agents (`<repo>/.agents/agents/`)
handle repo-internal concerns. When both exist, repo-level agents
take priority for that repo's code.

### Per-repo implementation loop

For each affected repository, in the dependency order from `plan.md`:

#### 6a. Read repo conventions

1. **Read `AGENTS.md`** (if it exists) — coding style, commit format,
   architecture constraints. MANDATORY to follow.
2. **Read `README.md`** — build / test / lint commands, environment
   setup.
3. **Check for repo-level agents** at `<repo>/.agents/agents/` — if
   the repo has specialized agents, prefer them for that repo's
   changes.

#### 6b. Set up repo environment

Activate the repo's required environment before running any commands:

| Indicator | Action |
|-----------|--------|
| `venv/`, `.venv/`, or `requirements.txt` / `pyproject.toml` with Python deps | Activate: `source <repo>/.venv/bin/activate` (create if documented but missing) |
| `.nvmrc` or `.node-version` | `nvm use` in the repo directory |
| `Gemfile` | `bundle install` if needed |
| `go.mod` | Go modules — typically no setup |
| Dockerfile / docker-compose | Follow README for containerized dev |

ALWAYS check the repo's documented setup. If you can't determine how,
ask.

#### 6c. Implement changes

- Follow the repo's coding conventions strictly (from
  `AGENTS.md`/`README.md`)
- Be consistent with existing patterns
- If the repo has a specific commit message format, follow it

#### 6d. Validate changes

Run all validation in this order:

1. **Lint / format** — if a linter is configured (eslint, ruff, black,
   prettier, etc.), run and fix issues
2. **Type check** — if type checking is used (mypy, pyright, tsc),
   run and fix issues
3. **Tests** — find the test command (e.g. `pytest`, `npm test`,
   `go test ./...`), run in the correct environment:
   - If tests fail caused by your changes → fix
   - If existing tests need updating due to intentional behavior
     changes → update
   - Pre-existing failures unrelated to your changes → note in
     `progress.md`, do not try to fix
   - Re-run until passing
4. **Build** — verify any build step succeeds

Do NOT skip validation. If a repo has tests, you MUST run them. If
tests fail due to your changes, you MUST fix them before moving to
the next repo.

#### 6e. Stage, review, and commit (per-repo staged review loop)

After validation passes, each repo goes through a **staged review
loop** before committing. This uses the `code-review-staged` skill
to perform a thorough, context-aware review of the staged diff —
catching issues before they become commits.

Why review before commit (not after):

1. Staged changes are the exact "candidate commit" — reviewing here
   prevents bad code from entering git history.
2. `code-review-staged` gathers rich context that a post-commit branch
   diff review cannot match.
3. Fix cycles are cleaner — just edit files and re-stage, no amend.

**Flow per repo:**

```
Implement → Validate (lint/test/build) → git add . → code-review-staged
                                                          │
                                          ┌───────────────┴───────────────┐
                                     Has P0/P1                      No P0/P1
                                          │                               │
                                  Fix code → git add .              Commit with
                                          │                      recommended message
                                  code-review-staged
                                     (round N+1)
                                          │
                                   max 3 rounds
```

##### 6e-i. Stage all changes

```bash
cd <repo-dir>
git add .
```

Do NOT commit yet. The staged changes are the review input.

##### 6e-ii. Invoke `code-review-staged`

Trigger the `code-review-staged` skill. It will:

1. Run `git diff --cached` to collect the staged diff
2. Gather repo context (project structure, config files, full file
   contents, related files)
3. Produce a structured review with: Change Overview, Code Quality,
   Major Issues and Risks, Incremental Suggestions, and a Recommended
   Commit Message

##### 6e-iii. Evaluate and record to `review.md`

Map the output to a verdict (PASS / NEEDS_FIXES) and append the round
to `review.md` using the template in
[`references/review-formats.md`](references/review-formats.md).

##### 6e-iv. Fix cycle (max 3 rounds)

If `NEEDS_FIXES`:

1. Fix only P0/P1 issues — do NOT refactor unrelated code or chase
   P2 suggestions during fix rounds.
2. Re-validate (lint/test/build).
3. `git add .`
4. Invoke `code-review-staged` again on the new staged diff.
5. Append the new round to `review.md`.
6. Repeat until `PASS` or 3 rounds exhausted.

After 3 rounds: if P0/P1 issues remain, record as **residual** in
`review.md` and `progress.md`, then proceed to commit. Flag in the
final summary.

**Convergence principle**: each round should have FEWER findings
than the previous. If a round introduces MORE new issues than it
fixes, the developer is over-editing — stop and commit with residuals
noted.

##### 6e-v. Commit

1. Use the **recommended commit message** from the last
   `code-review-staged` output. If the repo has its own convention
   (from `AGENTS.md`), reconcile — repo convention wins.
2. `git commit -m "<message>"`
3. Update `progress.md`: what was implemented, review result, test
   results, issues encountered.

##### 6e-vi. Forward pointer — what happens AFTER round 0

The staged-review-then-commit loop above is the discipline for
**round 0** — the initial implementation. After Step 9 finalizes
round 0, every follow-up edit driven by user feedback, error logs,
manual test results, or reviewer comments MUST run through the
**same** stage → review → fix → commit loop, augmented with a
per-round doc-sync checklist and an Iteration Log row in
`progress.md`.

Read [`references/iteration-mode.md`](references/iteration-mode.md)
for the full round-N protocol. Do NOT downgrade the discipline just
because the change is small or the user did not say "fullstack impl"
again.

## Step 7 — Cross-Repo Consistency Review (multi-repo only)

Skip this step for single-repo work. For multi-repo, this verifies
that changes across repos are consistent with each other — separate
from per-repo staged review (Step 6e), which focuses on code quality
within a single repo.

### 7a. Collect cross-repo diffs

For each affected repo:

```bash
cd <repo-dir>
git diff <default-branch>...<feature-branch>
```

### 7b. Cross-repo consistency checks

Verify across ALL affected repos:

- **API contracts**: request/response shapes match between producer
  and consumer
- **Shared types**: type definitions in shared-lib match usage in
  consumers
- **Environment variables**: any new env vars are documented in all
  affected repos
- **Database migrations**: schema changes are compatible across
  services
- **Error contracts**: error codes/messages are consistent across
  boundaries
- **Version compatibility**: dependency version bumps are aligned

For **Follow-up Mode**, also verify backward-compatibility against
the predecessor's shipped contracts. See
[`followup-mode.md`](references/followup-mode.md#backward-compatibility-gate-cross-repo-review-addendum).

### 7c. Write cross-repo findings to `review.md`

Append a cross-repo review section using the template in
[`references/review-formats.md`](references/review-formats.md). Even
if no issues are found, write a `PASS` confirmation documenting what
was checked.

### 7d. Fix cross-repo issues

If P0/P1 cross-repo issues are found:

1. Fix the upstream repo first, then downstream.
2. For each repo that needs fixes, go through the staged review loop
   again (Step 6e-i through 6e-v).
3. Re-run the cross-repo check.
4. Max 2 fix rounds for cross-repo issues — if issues persist, record
   as residual.

## Step 8 — Create Pull Requests (GitHub repos only)

### Use the `GITHUB_REPOS` value from the Workspace Validation Gate

The Workspace Validation Gate at the top of this skill already ran
`check_workspace.py` and recorded the `GITHUB_REPOS` flag. Reuse that
recorded value here — do NOT re-derive from repo URLs or domain names.

Decision logic:

- `GITHUB_REPOS=true` → proceed with PR creation below
- `GITHUB_REPOS=false` → **skip this entire step**, go to Step 9

If for any reason the workspace gate value was lost (e.g. resuming a
session without re-running the gate), re-run `check_workspace.py`
once. The legacy `check_github_repos.py` script still works as a
backward-compatible wrapper — both report the same `GITHUB_REPOS`
value.

**Why a script instead of reading JSON directly:** the LLM must NEVER
decide whether a repo is "GitHub" or "not GitHub" based on domain
names, remote URLs, or any heuristic. The `fullstack-init` skill
already asked the user during workspace setup and saved the answer.
This eliminates the failure mode where GitHub Enterprise URLs like
`git.company.com` get misclassified.

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
   Requests` header stays English; `仓库 / PR 链接 / 状态` for
   columns.)

2. **Commit** the docs repo with the updated progress.

### Error handling

If `gh pr create` fails for a repo (auth, not a GitHub remote, branch
not pushed, etc.), record the failure in `progress.md` and move on:

```markdown
| api | — | Failed: `gh` error: ... |
```

Do NOT block the entire finalization on one repo's PR failure — create
PRs for all repos that succeed and report failures separately.

## Step 9 — Finalize Round 0

Step 9 closes the **initial implementation round** (round 0). It does
NOT close the work item — follow-up edits continue under
[`iteration-mode.md`](references/iteration-mode.md). Treat
finalization as the end of the green-field phase, not the end of the
work item.

### Review completion gate (MANDATORY)

Before finalizing, verify `review.md` contains at least one
`### Verdict` (English) or `### 结论` (Chinese) section from per-repo
staged reviews (Step 6e). For multi-repo work, also verify the
cross-repo review (Step 7) has a verdict. If either is missing,
**STOP** and complete the review.

### Four-file consistency gate (MANDATORY)

Verify all four documents exist and are internally consistent:

1. All four files exist and are non-empty
2. `analysis.md` recommended approach matches `plan.md` chosen
   approach
3. `plan.md` tasks match `progress.md` completed/in-progress items
4. If review found issues that changed the approach, are
   `analysis.md` and `plan.md` updated to reflect the final state?

For **Follow-up Mode** also verify:

5. The `Predecessor:` field is present in `analysis.md` AND `plan.md`
6. The `## Predecessor Context` section in `analysis.md` is non-empty
7. The predecessor's `progress.md` has the `## Successors` row

Then run the **Mermaid Compatibility Gate** against EVERY `.md` file
in the work directory that contains ` ```mermaid ` blocks. If
`STATUS=FAIL` on any, fix and re-run; do NOT finalize with broken
diagrams. See [`document-templates.md`](references/document-templates.md#mermaid-1023-compatibility).

### Finalization steps

After review passes (and PRs created if applicable):

1. **Update `analysis.md`** if the review cycle or implementation
   changed the technical approach (add an "Updated" date and note
   what changed).
2. **Update `progress.md`**: `Overall status` → `Complete`/`已完成`,
   add final changelog entry.
3. **Update `plan.md`**: `Status` → `Done`/`已完成`, check off all
   completed tasks.
4. **Commit** the docs repo with all tracking doc updates.
5. **Report to user**: summarize what was implemented across which
   repos. If PRs were created, list all PR URLs clearly:

   ```
   Implementation complete. Pull Requests created:

     1. shared-lib — https://github.com/owner/shared-lib/pull/42
     2. api       — https://github.com/owner/api/pull/99
     3. web       — https://github.com/owner/web/pull/77
   ```

## After Finalization — Iteration Mode and Closure

Round 0 is just the start. Real life rarely ends at finalization.
Manual testing, pasted error logs, code review feedback, QA pushback,
edge cases, or new tiny requirements all produce follow-up edits to
the same work item.

When the user gives any feedback / fix / log on a finalized
(but not yet closed) work item, enter **Iteration Mode** silently and
run the sticky loop. Do NOT downgrade the discipline because the
change is small. See
[`references/iteration-mode.md`](references/iteration-mode.md) for
the full protocol — per-iteration doc sync checklist, Iteration Log
schema, self-check via `iteration_log_check.py`, anti-patterns, and
how to close the work item.

After the user explicitly closes the work item ("merged", "ship it",
"结了"), any new request on the same scope creates a NEW work item.
Whether it links to the closed predecessor (Follow-up Mode) or just
references it (Reference Mode) depends on user intent. See
[`references/mode-selection.md`](references/mode-selection.md).

## Resuming Previous Work

The routing decision in Step 1d already covers this. Specifically:
when `route_check.py` matches a work directory, it reports
`STATUS_NORMALIZED`, `HAS_SUCCESSORS`, `LATEST_SUCCESSOR`, and
`ITERATION_LOG_FOUND` — everything the agent needs to decide whether
to **Resume** an open work item, **Iterate** on a Done item, or chain
forward through `LATEST_SUCCESSOR`.

When the recommended route is `Resume`:

1. Read all four documents (`analysis.md`, `plan.md`, `progress.md`,
   `review.md`) to understand current state, including any prior
   Iteration Log rows AND any existing `## Successors` table.
2. **Run `iteration_log_check.py` against the work directory** (see
   [`iteration-mode.md`](references/iteration-mode.md#self-check--iteration_log_checkpy-after-each-round)).
   If `STATUS=FAIL` or `WARN`, the previous session left the audit
   trail degraded — fix BEFORE adding any new rounds.
3. Check which tasks in `plan.md` are incomplete.
4. Verify branches still exist in the affected repos.
5. If repos are already on the correct branch, skip checkout.
6. Re-enter Step 1-9 from the last incomplete step recorded in
   `progress.md`.

When `LATEST_SUCCESSOR` is non-empty, the named work item is part of a
chain (predecessor → successor → ...). Re-run `route_check.py` against
the **latest** successor — followups chain forward, and the user
almost always means the most recent link in the chain, not the
original.

The routing protocol handles all four real-world scenarios:

1. A session was closed mid-work and the user starts a new session
   to continue → `STATUS_NORMALIZED=InProgress` + resume verb →
   **Resume**.
2. The work was finalized but PR review is generating fixes →
   `STATUS_NORMALIZED=Done` + iteration verb → **Iteration**.
3. The work shipped last week and the user is reporting a production
   bug → `STATUS_NORMALIZED=Closed` + iteration verb →
   **AskUser** (Iteration on a hotfix branch vs a fresh `fix/` is the
   user's call, not the agent's).
4. The work shipped a month ago and the user wants to extend the
   feature → `STATUS_NORMALIZED=Closed` + follow-up verb →
   **Followup** (`feat/<name>-v2/`).

## Error Handling

- **Test failures**: Fix test failures caused by your changes before
  moving to the next repo. Re-run tests in the correct environment
  (venv, nvm, etc.) until they pass. Do not skip to the next repo
  with broken tests.
- **Environment issues**: If a venv is missing, node version is
  wrong, or dependencies can't be installed, check the repo's README
  for setup instructions. If setup fails, note in `progress.md` and
  ask.
- **Cross-repo contract mismatch**: If a downstream repo's tests fail
  because an upstream repo's API changed unexpectedly, go back and
  fix the upstream repo first, then re-validate downstream.
- **Pre-existing failures**: Document pre-existing failures in
  `progress.md` but do not block on them.
- **Unexpected blockers**: Update `progress.md` with details and ask
  the user.

## Requirements

- Python 3.10+
- Workspace initialized by `fullstack-init` (must pass workspace
  validation gate: `fullstack.json` + `AGENTS.md` + `.agents/` all
  present)
- Other skills as needed: `jira`, `confluence`, `gh-operations`,
  `figma`
- For PR creation (Step 8): `github-pr-create` skill + `gh` CLI
  installed and authenticated (only when `fullstack.json` has
  `"github_repos": true`)
