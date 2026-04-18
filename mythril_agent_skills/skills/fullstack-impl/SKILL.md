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

  1. web/ — Add new dashboard component for dark mode toggle
  2. api/ — Add user preference endpoint for theme setting
  3. shared-lib/ — Add theme constants to shared types

Work type: feat
Branch name: feat/XYZ-706/Dark-Mode-Toggle

Does this look correct? You can:
- Confirm to proceed
- Remove repos that shouldn't be changed
- Add repos I missed
- Change the work type or branch name
- Type the repo directory names yourself
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

## Affected Repositories

| # | Repository | Changes Needed | Priority |
|---|-----------|---------------|----------|
| 1 | repo-name | Description of changes | P0/P1/P2 |

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

Read `.agents/agents/planner.md` first if the work is complex enough to
warrant planning (multi-phase, multiple repos, unclear approach). For
straightforward work, proceed directly to implementation.

For each affected repository, in dependency order:

### Before touching a repo

1. **Read the repo's `AGENTS.md`** (if it exists) — follow its conventions
2. **Read the repo's `README.md`** — understand build/test/lint instructions
3. **Check for repo-level agents** at `<repo>/.agents/agents/` — if the repo
   has its own specialized agents, prefer using them for that repo's changes

### Implementation rules

- Follow each repo's own coding conventions (from AGENTS.md/README.md)
- Run repo-specific tests/linting as specified in their docs
- Commit and test each repo independently
- After completing changes in each repo, update `progress.md` in the docs repo

### Agent delegation

- **Workspace agents** (`.agents/agents/`) handle cross-repo coordination
- **Repo-level agents** (`<repo>/.agents/agents/`) handle repo-internal concerns
- When both exist, repo-level agents take priority for that repo's code
- For `fix/` work type, use the **debugger** agent for root-cause analysis

## Step 7 — Review

After implementation is complete (or at logical checkpoints):

1. **Read `.agents/agents/reviewer.md`** for review guidelines
2. For each affected repo, review the changes:
   - Run `git diff` in the repo to see all changes
   - Check against the repo's `AGENTS.md` conventions
   - Verify cross-repo consistency (API contracts, shared types, etc.)
3. If a repo has its own review agent, defer to it for repo-specific concerns
4. **Append findings to `review.md`** in the work directory

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

- If a repo's tests fail after changes, fix the tests before moving to the
  next repo
- If cross-repo consistency checks fail (e.g. API contract mismatch), pause
  and notify the user
- If implementation hits an unexpected blocker, update `progress.md` with
  the blocker details and ask the user for guidance

## Requirements

- Python 3.10+
- Workspace initialized by `fullstack-init` (`fullstack.json` present)
- Other skills as needed: `jira`, `confluence`, `gh-operations`, `figma`
