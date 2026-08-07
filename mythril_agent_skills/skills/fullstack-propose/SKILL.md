---
name: fullstack-propose
description: |
  Propose a new work item across a multi-repo fullstack workspace —
  gather context, design the approach, validate unknowns (spike) if
  needed, and write the work-tracking documents in one step. Standard
  mode for clear requirements; deep mode (spike) for uncertain ones.
  Trigger: "fullstack propose", "fullstack plan", "fullstack spike",
  "全栈提案", "全栈规划", "全栈计划", "全栈 spike", "全栈探针",
  "全栈验证", "全栈 poc"; ALSO when the user asks to plan, design, or
  prototype a feature/fix/refactor before implementing — "plan this",
  "设计一下", "怎么做X", "先验证X", "we should add X". Planning only —
  does not edit project code or create branches.
license: Apache-2.0
---

# Fullstack Propose

Turn an idea into a planned work item in a multi-repo fullstack workspace
initialized by `fullstack-init`. This skill produces the work-tracking
documents that `fullstack-apply` later implements.

## How this skill works

Two modes, one work directory:

| Mode | When | What happens |
|------|------|--------------|
| **Standard** | Requirements are clear, no major unknowns | Write the four work-tracking documents directly |
| **Deep (spike)** | Unknowns need validation first | Record Objective/Hypothesis/Unknowns/Success Criteria in `analysis.md`, run experiments, append Design Options / Target Architecture to the **same file**, then write `plan.md` |

The deep mode's output IS the final work directory — there is no rewrite
on handoff to `fullstack-apply`. One directory, one analysis, one
lifecycle.

## Planning Boundary (MANDATORY)

This skill creates planning artifacts only. The user request that
triggered this skill authorizes planning only — **even if it asks to
build or fix something**. Do not:

- Edit project code (except temporary, uncommitted spike changes in deep
  mode — and those are cleaned up before finishing)
- Create branches (`git checkout -b`)
- Commit changes or push to any code repo
- Create Pull Requests
- Start implementation in the same response

After the planning artifacts are complete, **stop** and wait for a new
user request. Then `fullstack-apply` implements the plan.

## Prerequisites — Workspace Validation Gate (MANDATORY SCRIPT CALL)

This skill MUST NOT proceed past this gate. Run `check_workspace.py` and
inspect its output before planning anything.

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/fullstack-propose/scripts/check_workspace.py",
    pathlib.Path.home() / ".claude/skills/fullstack-propose/scripts/check_workspace.py",
    pathlib.Path.home() / ".copilot/skills/fullstack-propose/scripts/check_workspace.py",
    pathlib.Path.home() / ".cursor/skills/fullstack-propose/scripts/check_workspace.py",
    pathlib.Path.home() / ".gemini/skills/fullstack-propose/scripts/check_workspace.py",
    pathlib.Path.home() / ".codex/skills/fullstack-propose/scripts/check_workspace.py",
    pathlib.Path.home() / ".qwen/skills/fullstack-propose/scripts/check_workspace.py",
    pathlib.Path.home() / ".grok/skills/fullstack-propose/scripts/check_workspace.py",
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
| `DOCS_DIR=<name>` | Docs directory name |
| `GITHUB_REPOS=true\|false` | Whether apply should create PRs later |

Decision logic:

- `WORKSPACE_VALID=true` → announce the Workspace contract line (below), then proceed to Step 1
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
machine-readable contract marker.

## Document Language Selection

All four work-tracking documents and user-facing messages MUST match the
language of the user's prompt.

1. If the user **explicitly requests a language** → use that language.
2. If the user's prompt contains **any Chinese characters** → use Chinese.
3. Otherwise → use English (default).

This applies independently per invocation. It does NOT affect work
directory names (always lowercase-hyphenated English) or branch names
(always English Title-Case-With-Hyphens).

## Step 1 — Gather Context

### 1a. Read external links in the user's prompt

| Link type | Skill | What to extract |
|-----------|-------|-----------------|
| Jira URL or issue key (e.g. `PROJ-123`) | `jira` | Summary, description, acceptance criteria, subtasks |
| Confluence URL | `confluence` | Page content, requirements, specs |
| GitHub PR/issue URL | `gh-operations` | Description, comments, linked issues |
| Figma URL | `figma` | Design specs, components, layout, colors, typography |

Read ALL linked resources BEFORE proceeding.

### 1b. Read workspace context

1. **`fullstack.json`** — get the docs directory name and `github_repos`
2. **`AGENTS.md`** — repo table, conventions, structure
3. **`<docs-dir>/AGENTS.md`** — documentation conventions

### 1c. Check knowledge graphs (MANDATORY when available)

For each repo relevant to the request, run
`python3 SKILL_PATH/scripts/graphify_check.py <repo>` to check for
`graphify-out/`. This script uses a direct filesystem check immune to
`.gitignore` filtering — do NOT use Glob. When `graphify-out/` exists,
`cd` into the repo and MUST use `graphify query "<question>"` to
understand the codebase BEFORE grep/read. If output shows `TRUNCATED`,
raise the budget (`--budget 8000`) or narrow the query.

### 1d. Check prior context

- If the user references a previous work item or spike, read its
  documents from `<docs-dir>/changes/<type>/<name>/` (or the archive)
  to build on prior work. Record it under `**Source**` in the plan.
- If the referenced work item is **archived** and this is genuinely new
  work on the same scope, plan a `-vN` successor (see Step 2).

## Step 2 — Determine Work Type

| Category | Directory | Branch prefix | When to use |
|----------|-----------|--------------|-------------|
| Feature | `changes/feat/` | `feat/` | New features, capabilities, enhancements |
| Refactor | `changes/refactor/` | `refactor/` | Code restructuring, tech debt, cleanup |
| Fix | `changes/fix/` | `fix/` | Bug fixes, issue resolution |

If ambiguous, ask.

For a successor to an archived work item, the directory is
`<work-name>-vN/` in the same `<type>/`, and `analysis.md` must carry a
predecessor reference under `**Source**`.

## Step 3 — Identify Affected Repos

### Decision tree

1. **User explicitly listed repos** → use those, but still confirm
2. **User's description implies specific repos** → propose your analysis
3. **Ambiguous** → ask explicitly

### Confirmation (MANDATORY)

ALWAYS present your analysis to the user for confirmation, even when
confident. Format:

```
Based on the requirements, I plan to involve these repositories:

  1. shared-lib/ — Add theme constants to shared types
  2. api/ — Add user preference endpoint for theme setting
  3. android/ — Add dark mode toggle to settings screen

Work type: feat
Work name: add-dark-mode

Does this look correct? You can:
- Confirm to proceed
- Remove repos that shouldn't be involved
- Add repos I missed
- Change the work type or work name
```

Do NOT proceed until the user confirms. If the user corrects you,
update and reconfirm.

## Step 4 — Create the Work Plan

Create a work directory under `<docs-dir>/changes/<type>/`:

```
<docs-dir>/changes/<type>/<work-name>/
├── analysis.md   (technical analysis — ALWAYS created first)
├── plan.md       (execution plan — derived from analysis)
├── progress.md   (status tracking — initial state)
└── review.md     (review findings — header only, filled during apply)
```

### Four-File Invariant (MANDATORY)

All four files MUST be created. `analysis.md` is NEVER optional — even
for "trivial" work. A one-page analysis is fine; a missing analysis is
not. The four files form a causal chain:
`analysis.md → plan.md → progress.md → review.md`. Removing any link
breaks traceability.

**Scaling by complexity** — analysis depth should match the work:

| Work complexity | analysis.md depth |
|----------------|-------------------|
| Trivial (typo, config, version bump) | 1-2 sections: brief current state + change rationale |
| Simple (single repo, clear scope) | 3-4 sections: current state, requirements, chosen approach |
| Complex (multi-repo, architectural) | Full template: diagrams, options, trade-offs, risk matrix |

### Standard mode — write the four documents

Delegate to the **planner** subagent (read-only, returns content; you
write the files):

| Work type | Analysis | Planning |
|-----------|----------|----------|
| `feat/` / `refactor/` | Delegate to **planner** | Delegate to **planner** |
| `fix/` | Delegate to **debugger** (root cause) → then **planner** | From debugger's analysis |

The planner must include testable **Success Criteria** in `plan.md` —
not subjective ones. "Works correctly" is not a criterion; "returns 200
with valid JSON matching schema X for inputs A, B, C" is.

Then write `progress.md` (initial state) and `review.md` (header)
yourself. Follow the templates in
[`references/document-templates.md`](references/document-templates.md).

### Deep mode (spike) — validate unknowns first

Use this when Step 1 reveals significant unknowns (technical risk,
unproven feasibility, unclear design choice). The output is the SAME
work directory — no separate spike directory, no rewrite later.

**4a. Write the spike part of `analysis.md`:**

```markdown
# Analysis: <Work Name>
**Created**: <date>   **Type**: <feat|fix|refactor>   **Author**: Planner

## Objective
<What are we trying to find out? What question does this spike answer?>

## Current State
<Existing system behavior / architecture / limitations>
### Architecture (as-is)
```mermaid
flowchart LR
    A[Component A] --> B[Component B]
```

## Hypothesis
<What do we believe will work? What assumptions are we testing?>

## Spike Approach
| Step | What to try | Repo | Expected outcome | Risk |
|------|-------------|------|-----------------|------|
| 1 | ... | api/ | ... | Low |

## Unknowns
- <What we don't know and need to find out>

## Success Criteria
<How do we know the validation succeeded? What evidence do we need?>
- [ ] Criterion 1
- [ ] Criterion 2
```

**4b. Execute the spike (temporary, uncommitted):**

1. Read each affected repo's `AGENTS.md` and `README.md`; use graphify
   when available (same protocol as Step 1c).
2. Make temporary code changes to validate the hypothesis. Do NOT run
   `git add` or `git commit` on any code repo.
3. Run tests, start dev servers, check logs — whatever validates the
   criteria.
4. Record each experiment, its result, and evidence directly in
   `analysis.md` under a `## Experiments` section (appended as you go).

**4c. Complete the analysis — same file:**

After validation, append to `analysis.md` (still the same file):

```markdown
## Experiments
### Experiment 1: <title>
**What was tried**: ...   **Result**: ...   **Evidence**: ...

## Verdict
<FEASIBLE | NOT_FEASIBLE | NEEDS_MORE_RESEARCH> — one paragraph
summarizing whether the approach works and what was learned.

## Design Options
| Option | Approach | Pros | Cons | Complexity |
|--------|----------|------|------|-----------|
| A (chosen) | ... | ... | ... | Medium |

## Target Architecture
```mermaid
flowchart LR
    A[Component A] --> B[Component B]
```

## Cross-Repo Impact
| Repo | Impact | Breaking Change? |
|------|--------|------------------|
| api/ | ... | No |

## Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
```

**4d. Write `plan.md` from the verdict.** If NOT_FEASIBLE, write the
plan documenting why it's not proceeding (the plan still exists — the
record matters). If FEASIBLE, the plan reflects the chosen Design Option.

**4e. Clean up temporary spike changes** before finishing:

```bash
cd <repo-1> && git checkout .
cd <repo-2> && git checkout .
```

...unless the user explicitly says to keep the spike changes for
`fullstack-apply`.

### Mermaid Compatibility Gate (MANDATORY when diagrams are written)

After writing any doc with ` ```mermaid ` blocks, invoke `mermaid_lint.py`
from this skill's own bundled `scripts/` directory. Read
[`references/MERMAID-RULES.md`](references/MERMAID-RULES.md) before
authoring any diagram.

Locating the script across AI tools — check candidate paths in this
order, use the first that exists:
`~/.config/opencode/skills/fullstack-propose/scripts/mermaid_lint.py`,
`~/.claude/skills/fullstack-propose/scripts/mermaid_lint.py`,
`~/.copilot/...`, `~/.cursor/...`, `~/.gemini/...`, `~/.codex/...`,
`~/.qwen/...`, `~/.grok/...`. (If `fullstack-propose` is not installed
but `fullstack-apply` is, the same script lives under that skill's
bundled `scripts/` directory.)

If `STATUS=FAIL`, read each `ERROR:` line, apply the suggested fix,
save, and re-run until `STATUS=PASS`. Do NOT proceed with `STATUS=FAIL`.

## Step 5 — Report the Plan

1. **Commit the work directory to the docs repo** (the ONLY repo that
   gets commits in this skill).
2. **Report to the user**:

```
Planned: <work-name> (<feat|fix|refactor>)
Location: <docs-dir>/changes/<type>/<work-name>/
Mode: standard | deep (spike)

- Requirements: <summary>
- Success Criteria: <N criteria>
- Repos: <list>
- Design: <one-line summary of chosen option>

Next: tell me to "implement this" to run fullstack-apply.
```

## Resuming a Previous Plan

When invoked with a reference to an existing un-archived work item
(e.g. "continue planning X", "继续规划 X"):

1. Read the existing four documents in `<docs-dir>/changes/<type>/<name>/`
2. Determine what's incomplete (missing sections, unanswered Success
   Criteria, unfilled verdict)
3. Resume from the last incomplete step; re-confirm repos if the plan
   has changed

## Requirements

- Python 3.10+
- Workspace initialized by `fullstack-init` (must pass workspace
  validation gate)
- Other skills as needed: `jira`, `confluence`, `gh-operations`, `figma`

## Guardrails

- Planning only. Any implementation instruction in the request does not
  carry forward — stop after artifacts are presented.
- No branches, no commits to code repos, no PRs.
- The four documents are mandatory — a missing `analysis.md` is a failure.
- Success Criteria must be testable and specific, not subjective.
- Deep mode's output IS the work directory — never create a separate
  spike directory and never rewrite analysis on handoff.
- Mermaid gate must PASS before finalizing.
