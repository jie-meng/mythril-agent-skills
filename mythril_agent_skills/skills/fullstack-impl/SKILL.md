---
name: fullstack-impl
description: |
  Implement features, refactors, and fixes across a multi-repo fullstack
  workspace. Gathers context from Jira/Confluence/GitHub/Figma, creates
  branches, delegates to workspace agents, and tracks progress in docs repo.
license: Apache-2.0
---

# Fullstack Implementation

Implement features, refactors, and fixes across a multi-repo fullstack
workspace that was initialized by `fullstack-init`. This skill handles the
full lifecycle: gather context, plan, create branches, implement across
repos, review, and track progress.

## Prerequisites

This skill requires a workspace initialized by `fullstack-init`. Verify by
checking for `fullstack.json` in the workspace root.

If `fullstack.json` is missing, inform the user:
> This workspace hasn't been initialized yet. Run `fullstack-init` first
> to set up the workspace infrastructure.

## Step 1 — Gather Context

Before doing ANY implementation work, gather all available context.

### External links in the user's prompt

Scan the user's message for links. For each type, use the corresponding skill:

| Link type | Skill to use | What to extract |
|-----------|-------------|-----------------|
| Jira URL or issue key (e.g. `PROJ-123`) | `jira` skill | Summary, description, acceptance criteria, subtasks |
| Confluence URL | `confluence` skill | Page content, requirements, specs |
| GitHub PR/issue URL | `gh-operations` skill | Description, comments, linked issues |
| Figma URL | `figma` skill | Design specs, components, layout, colors, typography |

**IMPORTANT**: Read ALL linked resources BEFORE proceeding to Step 2. Do not
start planning or implementing with incomplete context.

### Workspace context

Read these files from the workspace root:

1. **`fullstack.json`** — get the docs directory name
2. **`AGENTS.md`** — understand the repo table, conventions, and structure
3. **`<docs-dir>/AGENTS.md`** — understand documentation conventions

## Step 2 — Determine Work Type

Classify the work into one of three categories:

| Category | Directory | Branch prefix | When to use |
|----------|-----------|--------------|-------------|
| Feature | `<docs-dir>/feat/` | `feat/` | New features, capabilities, enhancements |
| Refactor | `<docs-dir>/refactor/` | `refactor/` | Code restructuring, tech debt, cleanup |
| Fix | `<docs-dir>/fix/` | `fix/` | Bug fixes, issue resolution |

If the work type is ambiguous, ask the user.

## Step 3 — Identify Affected Repos

Based on the gathered context, determine which repositories need changes.

### Decision tree

1. **User explicitly listed repos** → use those, but still confirm
2. **User's description implies specific repos** (e.g. "add API endpoint" →
   api repo; "update the dashboard" → web repo) → propose your analysis
3. **Ambiguous or unclear** → ask the user explicitly

### Confirmation (MANDATORY)

**ALWAYS** present your analysis to the user for confirmation, even if you
are confident. Format:

```
Based on the requirements, I plan to modify these repositories:

  1. shared-lib/ — Add theme constants to shared types
     Branch: feat/Dark-Mode-Toggle
  2. api/ — Add user preference endpoint for theme setting
     Branch: feat/BE-450/Dark-Mode-Toggle
  3. android/ — Add dark mode toggle to settings screen
     Branch: feat/MOBILE-301/Dark-Mode-Toggle
  4. ios/ — Add dark mode toggle to settings screen
     Branch: feat/MOBILE-302/Dark-Mode-Toggle

Work type: feat

Does this look correct? You can:
- Confirm to proceed
- Remove repos that shouldn't be changed
- Add repos I missed
- Change the work type or branch names
- Reassign a Jira ticket to a different repo
```

**Do NOT proceed until the user confirms.** If the user corrects you, update
your plan accordingly and confirm again.

## Step 4 — Branch Management

### Branch naming convention

| Scenario | Format | Example |
|----------|--------|---------|
| With Jira key | `<type>/<JIRA-KEY>/<Title-Hyphenated>` | `feat/XYZ-706/Import-Export` |
| Without Jira | `<type>/<Title-Hyphenated>` | `refactor/Refine-Models` |

The descriptive part uses **Title-Case-With-Hyphens**.

### Multiple Jira tickets → per-repo branch names

When the user provides **multiple Jira tickets** (common in cross-platform
work), different repos may get **different branch names** based on which
ticket belongs to which platform.

**How to match tickets to repos:**

1. Read each Jira ticket's title, description, labels, and component fields
   (already gathered in Step 1).
2. Read each repo's identity from the workspace `AGENTS.md` repo table
   (role, tech stack, description) and, if needed, the repo's own
   `AGENTS.md` and `README.md` for more context.
3. Cross-reference: match each ticket to the repo whose role/platform best
   fits the ticket's content. Do NOT hardcode keyword lists — use your
   understanding of both sides to make the match.
4. If a ticket is clearly cross-cutting and doesn't map to a single repo,
   assign it to the most relevant shared/infra repo.
5. If matching is ambiguous, ask the user.

**Result**: Each repo gets its own branch name with its own Jira key:

| Repo | Jira ticket | Branch name |
|------|-------------|-------------|
| android/ | MOBILE-301 | `feat/MOBILE-301/Dark-Mode-Toggle` |
| ios/ | MOBILE-302 | `feat/MOBILE-302/Dark-Mode-Toggle` |
| api/ | BE-450 | `feat/BE-450/Dark-Mode-Toggle` |
| shared-lib/ | — (no ticket) | `feat/Dark-Mode-Toggle` |

**Rules:**
- Repos without a matching ticket use the no-Jira format (type + title only)
- All branches share the same descriptive title (the work name)
- The `plan.md` must record each repo's specific branch name

### Creating branches in affected repos

For **each affected code repo** (NOT the docs repo):

1. **Detect the default branch**: check for `main`, `master`, or `dev`
   (in that order) by running `git branch -a` in the repo.
2. **Check if the target branch already exists**: run `git branch --list <branch-name>`.
   - If the branch **already exists** and the repo is already on it →
     **skip checkout** (this is a resume scenario — see "Resuming Previous Work").
   - If the branch exists but the repo is on a different branch →
     `git checkout <branch-name>`.
3. **If creating a new branch**:
   ```bash
   git checkout <default-branch>
   git pull
   git checkout -b <branch-name>
   ```

### The docs repo does NOT use feature branches

The `<docs-dir>/` repo is an independent git repo for work tracking docs.
All work tracking documents (plan.md, progress.md, review.md) are committed
directly to the docs repo's main branch. Do NOT create feature branches in
the docs repo.

## Step 5 — Create Work Plan

Create a work directory under `<docs-dir>/<type>/`:

```
<docs-dir>/<type>/<work-name>/
├── plan.md
├── progress.md
└── review.md     (created empty, filled during review)
```

### Work name

Derive from the requirement. Use lowercase-hyphenated format:
- Jira card `PROJ-123: Add dark mode` → `add-dark-mode`
- User prompt "implement user search" → `user-search`
- If ambiguous, ask the user

### plan.md template

```markdown
# <Work Name>

**Source**: <Jira link / user prompt / Confluence page>
**Type**: feat | refactor | fix
**Branch**: <branch-name>
**Created**: <date>
**Status**: Planning

## Requirements

<Summary of requirements from gathered context>

## Affected Repositories (in dependency order)

| # | Repository | Branch | Changes Needed | Depends On | Priority |
|---|-----------|--------|---------------|-----------|----------|
| 1 | shared-lib | feat/Dark-Mode-Toggle | Add theme types | — | P0 |
| 2 | api | feat/BE-450/Dark-Mode-Toggle | Add preference endpoint | shared-lib | P0 |
| 3 | android | feat/MOBILE-301/Dark-Mode-Toggle | Add toggle screen | shared-lib, api | P1 |

Repos MUST be listed in dependency order: upstream first (shared libs,
data models), then services (api, backend), then consumers (web, ios,
android). The implementation phase follows this exact order.

## Implementation Plan

### Phase 1: <name>
- [ ] Task 1 in repo-x
- [ ] Task 2 in repo-y

### Phase 2: <name>
- [ ] Task 3 in repo-x

## Dependencies

<Cross-repo dependencies, order constraints>

## Risks / Open Questions

<Known risks, things to clarify>
```

### progress.md template

```markdown
# Progress: <Work Name>

**Last updated**: <date>
**Overall status**: In Progress
**Branch**: <branch-name>

## Completed Steps

(none yet)

## In Progress

- [ ] <current step>

## Blocked

(none)

## Change Log

### <date> — Started
- Created work plan
- Identified affected repos: <list>
- Created branches in: <list>
```

### review.md — create with just a header:

```markdown
# Review: <Work Name>

Review findings will be appended here by the reviewer agent.
```

## Step 6 — Implement

### Orchestration model

Implementation follows a **serial per-repo** strategy: repos are modified
one at a time, in the dependency order established in `plan.md`. This is
the default — even when the work seems parallelizable.

**Why serial is the default:**

1. Cross-repo dependencies are the norm (shared types → API → consumers).
   Parallel agents can't see each other's WIP, leading to contract mismatches.
2. The developer accumulates cross-repo context naturally — what was built
   in repo A informs what needs to happen in repo B.
3. Shared docs (`progress.md`) can't be safely written concurrently.
4. Debugging failures is simpler with a clean sequential audit trail.

**Exception — truly independent repos**: If the planner explicitly confirms
that two or more repos have ZERO shared interfaces, ZERO data model overlap,
and ZERO dependency edges, they MAY be implemented in parallel via sub-agents.
The planner must document this independence in `plan.md`. When in doubt,
default to serial.

### Agent roles during implementation

Read `.agents/agents/planner.md` first if the work is complex enough to
warrant planning (multi-phase, multiple repos, unclear approach). For
straightforward work, proceed directly to implementation.

| Agent | When | What |
|-------|------|------|
| Planner | Complex work | Analyze requirements, create `plan.md` |
| Developer | Always | Implement code, fix tests, the only agent that writes code |
| Reviewer | After impl | Review diffs, cross-repo consistency, append `review.md` |
| Debugger | `fix/` type | Root-cause analysis before implementing the fix |

- **Workspace agents** (`.agents/agents/`) handle cross-repo coordination
- **Repo-level agents** (`<repo>/.agents/agents/`) handle repo-internal concerns
- When both exist, repo-level agents take priority for that repo's code

### Per-repo implementation loop

For each affected repository, in the dependency order from `plan.md`:

#### 6a. Read repo conventions

1. **Read `AGENTS.md`** (if it exists) — coding style, commit format,
   architecture constraints. These are MANDATORY to follow.
2. **Read `README.md`** — build commands, test commands, lint commands,
   environment setup instructions.
3. **Check for repo-level agents** at `<repo>/.agents/agents/` — if the
   repo has specialized agents, prefer them for that repo's changes.

#### 6b. Set up repo environment

Before running any build, test, or lint commands, activate the repo's
required environment:

| Indicator | Action |
|-----------|--------|
| `venv/`, `.venv/`, or `requirements.txt` / `pyproject.toml` with Python deps | Activate: `source <repo>/.venv/bin/activate` or `source <repo>/venv/bin/activate`. If venv doesn't exist but is documented, create it per README instructions. |
| `.nvmrc` or `.node-version` | Run `nvm use` in the repo directory |
| `Gemfile` | Run `bundle install` if needed |
| `go.mod` | Go modules — typically no setup needed |
| Dockerfile / docker-compose | Follow README for containerized dev workflow |

**Rules:**
- ALWAYS check if the repo documents a specific environment setup in its
  README or AGENTS.md. Follow those instructions exactly.
- If a venv/environment exists but isn't activated, activate it before
  running tests or linting.
- If the repo requires environment setup and you can't determine how,
  ask the user.

#### 6c. Implement changes

- Follow the repo's coding conventions strictly (from AGENTS.md/README.md)
- Write code that is consistent with the repo's existing patterns
- If the repo has a specific commit message format, follow it

#### 6d. Validate changes

Run all validation steps the repo requires, in this order:

1. **Lint / format** — if the repo has a linter configured (eslint,
   ruff, black, prettier, etc.), run it and fix any issues
2. **Type check** — if the repo uses type checking (mypy, pyright, tsc),
   run it and fix any issues
3. **Tests** — run the repo's test suite as documented in README/AGENTS.md:
   - Find the exact test command (e.g. `pytest`, `npm test`, `go test ./...`)
   - Run it in the correct environment (venv activated, correct node version)
   - If tests fail:
     a. Read the failure output carefully
     b. Determine if the failure is caused by your changes or was pre-existing
     c. Fix test failures caused by your changes
     d. If existing tests need updating due to intentional behavior changes,
        update them
     e. If pre-existing failures unrelated to your changes exist, note them
        in `progress.md` but do not try to fix them
   - Re-run tests after fixes until they pass
4. **Build** — if the repo has a build step, verify it succeeds

**IMPORTANT**: Do NOT skip validation steps. If a repo has tests, you MUST
run them. If tests fail due to your changes, you MUST fix them before
moving to the next repo.

#### 6e. Commit and update progress

- Commit changes in the repo (follow the repo's commit message convention)
- Update `progress.md` in the docs repo with:
  - What was implemented in this repo
  - Test results (pass/fail, number of tests)
  - Any issues encountered and how they were resolved

## Step 7 — Review

After implementation is complete (or at logical checkpoints):

1. **Read `.agents/agents/reviewer.md`** for review guidelines
2. For each affected repo, review the changes:
   - Run `git diff <default-branch>...<feature-branch>` to see all changes
   - Check against the repo's `AGENTS.md` conventions
   - Verify tests pass (re-run in the correct environment)
3. **Cross-repo consistency checks** (critical for multi-repo work):
   - API contracts: request/response shapes match between producer and consumer
   - Shared types: type definitions in shared-lib match usage in all consumers
   - Environment variables: any new env vars are documented in all affected repos
   - Database migrations: schema changes are compatible across services
4. If a repo has its own review agent, defer to it for repo-specific concerns
5. **Append findings to `review.md`** in the work directory

### Review finding format

```markdown
## Review Pass <N> — <date>

### Findings

- [P0] <repo>: <critical issue> — must fix before merge
- [P1] <repo>: <important issue> — should fix
- [P2] <repo>: <suggestion> — nice to have

### Verdict

<PASS | NEEDS_FIXES | FAIL> — <summary>
```

### Fix cycle

If the review finds issues:
1. Dev agent addresses P0 and P1 findings
2. Update `progress.md` with fixes made
3. Re-run review (only on fixed items)
4. Repeat until verdict is PASS (max 3 cycles)

## Step 8 — Finalize

After review passes:

1. **Update `progress.md`**:
   - Set overall status to "Complete"
   - Add final changelog entry with summary
2. **Update `plan.md`**:
   - Set status to "Done"
   - Check off all completed tasks
3. **Report to user**: Summarize what was implemented across which repos

## Resuming Previous Work

When this skill is invoked, check for existing work directories under
`<docs-dir>/feat/`, `<docs-dir>/refactor/`, and `<docs-dir>/fix/`.

If the user says something like "continue the dark mode feature" or
"look at the docs and keep going":

1. Find the matching work directory
2. Read `plan.md` and `progress.md` to understand current state
3. Check which tasks are incomplete
4. Verify the branches still exist in the affected repos
5. If repos are already on the correct branch, skip checkout
6. Resume from the last incomplete step

This handles the scenario where an AI session was closed mid-work and the
user starts a new session wanting to continue.

## Error Handling

- **Test failures**: Fix test failures caused by your changes before moving
  to the next repo. Re-run tests in the correct environment (venv, nvm, etc.)
  until they pass. Do not skip to the next repo with broken tests.
- **Environment issues**: If a venv is missing, node version is wrong, or
  dependencies can't be installed, check the repo's README for setup
  instructions. If setup fails, note the issue in `progress.md` and ask
  the user.
- **Cross-repo contract mismatch**: If a downstream repo's tests fail because
  an upstream repo's API changed in a way that wasn't anticipated, go back
  and fix the upstream repo first, then re-validate downstream.
- **Pre-existing failures**: If a repo's tests were already failing before
  your changes, document the pre-existing failures in `progress.md` but do
  not block on them.
- **Unexpected blockers**: Update `progress.md` with blocker details and ask
  the user for guidance.

## Requirements

- Python 3.10+
- Workspace initialized by `fullstack-init` (`fullstack.json` present)
- Other skills as needed: `jira`, `confluence`, `gh-operations`, `figma`
