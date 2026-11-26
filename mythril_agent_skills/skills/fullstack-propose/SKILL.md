---
name: fullstack-propose
description: >
  Plans a feature, fix, or refactor across a multi-repo fullstack workspace:
  gathers context, designs the approach, runs a spike for unknowns, and writes
  the work-tracking documents, gated by an independent plan review. Planning
  only — no code edits. Also re-reviews an existing plan; "grill me" / "拷问我"
  asks requirement questions first. Triggers: "fullstack propose", "fullstack
  plan", "全栈提案", "全栈规划", "全栈 spike", "plan this", "设计一下", "review this plan",
  "审一下方案". A small root-caused one-repo bug goes to fullstack-apply.
license: Apache-2.0
---

# Fullstack Propose

Turn an idea into a planned work item in a workspace initialized by
`fullstack-init`. The output is a work directory of four documents that
`fullstack-apply` implements:

```text
<docs-dir>/changes/<type>/<work-name>/
├── analysis.md   requirements baseline + technical analysis (always first)
├── plan.md       Summary, Success Criteria, repos, Code Map, tasks
├── progress.md   dated change log
└── review.md     Status Overview, Evidence table, plan review rounds
```

## How this skill works

**Quick fix first — not every change is a work item.** A bug whose root
cause is already established with evidence, or a fully specified small
tweak — confined to one repo, with no cross-repo contract / persisted-data /
schema / external API change, small enough to review in one sitting, and
touching no code an active work item owns — does not get a work directory.
The full conditions live in `fullstack-apply`'s
`references/quick-fix.md`. Recommend that path in the Step 3 message
(`Tier: quick fix — no work item`); if the user accepts, stop here — write
nothing, commit nothing — and hand off. The user can always insist on a
work item.

| | Lean tier | Full tier |
|---|---|---|
| **When** | Single repo, no cross-repo contract, no persisted-data / schema / migration change, no API consumed outside the repo (any non-production change — docs, skills, tests — also qualifies) | Everything else: multi-repo, any frozen contract, data/schema/migration, external API, architectural refactor, deep (spike) mode |
| **Who writes the plan** | You (the orchestrator) — you already hold the context | The **planner** subagent, writing straight to disk |
| **Plan review** | 1 independent pass + at most 1 confirmation | Loop, capped at 3 passes |

Both tiers write the same four documents, pass the same mechanical gates
(`plan_lint`, Mermaid, DAG) and the same independent plan review. The tier
changes who writes and how many review rounds run — never whether checks
run. If a condition cannot be confirmed, use full. An explicit user request
for either tier wins.

**Modes.** *Standard* when requirements are clear. *Deep (spike)* when
unknowns need validating first — read `references/spike-mode.md`. Deep mode
is always full tier and its output IS the final work directory.

**Reading discipline — load only what the current step needs.** Each
reference below is read at the step that names it, never up front.

| File | Read when |
|------|-----------|
| `references/template-analysis.<lang>.md` | Writing `analysis.md` (lean: you; full: the planner) |
| `references/template-plan.<lang>.md` | Writing `plan.md` |
| `references/template-progress.<lang>.md` | Writing `progress.md` |
| `references/template-review.<lang>.md` | Writing `review.md` and a plan review round |
| `references/template-rules.<lang>.md` | Writing any document or user-facing question (writing rules + visualization rules) |
| `references/interrogation.md` | Step 3.5 runs |
| `references/spike-mode.md` | Deep mode |
| `references/plan-review-rounds.md` | A review round returns `NEEDS_FIXES` / a decision sends the plan back |
| `references/review-only.md` | The user asks to review an existing plan |
| `references/issue-sourced.md` | The work comes from an active issue under `<docs-dir>/issues/` |
| `references/MERMAID-RULES.md` | Before drawing a diagram |

`SKILL_PATH` is this skill's installed directory (the folder holding this
`SKILL.md`). `<lang>` is `en` or `zh` (see Language).

## Planning Boundary

The request authorizes planning only — **even if it asks to build or fix
something**. No project code edits (except temporary, uncommitted spike
changes, cleaned up before finishing), no branches, no commits outside the
docs repo, no PRs, no implementation in the same response. After the
documents are complete, **stop**; `fullstack-apply` implements on a new
request.

## Workspace Validation Gate

```bash
python3 SKILL_PATH/scripts/check_workspace.py
```

It prints `WORKSPACE_VALID`, `MISSING`, `DOCS_DIR`, `GITHUB_REPOS`.

- `WORKSPACE_VALID=false` → STOP: tell the user the workspace was not
  detected, list the `MISSING=` markers, and ask them to `cd` to the
  workspace root and restart the agent, or run `fullstack-init` first.
- `WORKSPACE_VALID=true` → output EXACTLY this line (always English, a
  machine-readable marker), then continue:

  ```
  Workspace: VALID | docs_dir=<DOCS_DIR> | github_repos=<true|false>
  ```

## Language

Documents and user-facing messages match the user's prompt: an explicitly
requested language wins; otherwise any Chinese character → Chinese (`zh`);
otherwise English (`en`). Work directory names are always
lowercase-hyphenated English; branch names English Title-Case-With-Hyphens.

## Step 1 — Gather Context

1. **External links** — read every linked resource before going further:
   Jira key/URL → `jira`; Confluence → `confluence`; GitHub PR/issue →
   `gh-operations`; Figma → `figma`. **Capture requirements verbatim** —
   the user's sentences, the ticket text, the symptom as reported. They go
   word-for-word into `analysis.md` §Original Requirements / §需求原文, one
   `REQ<n>` per ask; a summary by the agent being audited cannot show a
   narrowed requirement.
2. **Workspace** — `fullstack.json`, the workspace `AGENTS.md` (repo
   table, conventions), `<docs-dir>/AGENTS.md`.
3. **Knowledge graphs** — for each relevant repo run
   `python3 SKILL_PATH/scripts/graphify_check.py <repo>` (not Glob — it is
   immune to `.gitignore`). No `graphify-out/` is a normal state. When it
   exists, prefer `graphify query "<question>"` before grep/read (raise
   `--budget 8000` on `TRUNCATED`). When the claims are few enough to
   verify by direct read, skip it — but every review round records
   `graphify: used | skipped: <reason> | n/a`.
4. **Prior context** — a referenced work item: read its documents under
   `changes/` or the archive and cite it under `**Source**`; new work on
   an archived item's scope is a `<name>-vN` successor. Scan active
   issues under `<docs-dir>/issues/` (not `issues/archive/`); if the
   request plans work for one, read `references/issue-sourced.md`.

## Step 2 — Determine Work Type

`feat` (new capability) → `changes/feat/`; `refactor` (restructure, tech
debt) → `changes/refactor/`; `fix` (bug) → `changes/fix/`. Ask if
ambiguous. A successor is `<work-name>-vN/` in the same type directory,
with a predecessor reference under `**Source**`.

## Step 3 — Confirm Repos, Work Name, and Tier

Always present your analysis and wait for confirmation, even when
confident:

```
Based on the requirements, I plan to involve these repositories:

  1. shared-lib/ — Add theme constants to shared types
  2. api/ — Add user preference endpoint for theme setting

Work type: feat
Work name: add-dark-mode
Tier: full (two repos share a new contract)
     (a fix that qualifies: "quick fix — no work item, fullstack-apply fixes it directly")

Confirm, or add/remove repos, or change the type, name, or tier.
```

Do NOT proceed until the user confirms; on a correction, update and
reconfirm. The tier given here is provisional — Step 4 re-checks it once
the Code Map exists.

## Step 3.5 — Requirements Interrogation Gate

Ask only the questions whose answers change the plan. A decision is
**plan-shaping** when its answer changes scope, user-visible behavior or
acceptance criteria, a cross-repo contract / data shape / migration order,
rollout / rollback / compatibility, or priority between conflicting
requirements.

**Skip** when any holds: the requirements already pin every plan-shaping
decision; the user said not to ask ("just plan", "直接出方案", "别问",
"你定"); the change is mechanical (typo, version bump, formatting);
review-only re-entry. A skip is recorded — its reason becomes the first
`progress.md` entry in Step 4. Never skip silently.

**Facts are your job, decisions are the user's.** If the code, docs, or
`AGENTS.md` answer it, look it up (dispatch the `explore` subagent for a
deep fact-find if the host has one). Ask only intent, priority, acceptable
trade-offs, rollout policy, and requirement conflicts.

**When the gate runs, read `references/interrogation.md` first** — it
holds the question format (plain words, a concrete example, a
recommendation, the cost of being wrong; at most five per round), standard
vs. grill mode, and the `### Clarifications` / `### 澄清记录` record. Every
open decision ends answered, assumed as `A<n>` with a reversal condition
(non-blocking only), or `NEEDS_USER_DECISION`. No silent assumptions.

## Step 4 — Write the Plan

### 4a. Baseline first (you, both tiers)

1. Create the work directory and all four files. **All four are
   mandatory** — `analysis.md` is never optional; scale its depth to the
   work (trivial: 1–2 sections; simple: 3–4; complex: full template).
2. Write `analysis.md` §Original Requirements / §需求原文 (one `REQ<n>` per
   ask, verbatim) plus §Clarifications / §澄清记录 from Step 3.5 — or, if
   the gate was skipped, the skip reason as the first `progress.md` entry.
   Templates: `template-analysis.<lang>.md`, `template-progress.<lang>.md`.
3. Write the `review.md` header (Status Overview, empty Evidence table)
   from `template-review.<lang>.md`. Once `plan.md` exists (4b), seed one
   Evidence row per Success Criterion — read only that section.

The baseline exists on disk before anyone writes the plan, so the review
can falsify the plan against the user's words rather than a restatement.

### 4b. The plan itself

**`fix` type, either tier:** the plan is built on an established root
cause. When this session already established it with evidence (log lines,
code path, data), write it into `analysis.md` §Root Cause / §根因分析 and
do **not** re-run the analysis. Otherwise delegate root-cause analysis to
the **debugger** subagent first.

**Lean tier — write it yourself.** Read `template-analysis`,
`template-plan`, and `template-rules` for `<lang>`, then write the rest of
`analysis.md` and `plan.md` directly. No planner subagent: you already hold
the gathered context, and handing it to a fresh agent would re-gather it.

**Full tier — the planner writes to disk.** Delegate to the **planner**
subagent with a brief holding:

- the absolute work-directory path, and the absolute paths of
  `SKILL_PATH/references/template-{analysis,plan,rules}.<lang>.md`;
- the requirements baseline (point at the section on disk — it exists
  now) and the confirmed repos, work type, and tier;
- the context you gathered: external-link content, relevant `AGENTS.md`
  rows, graphify findings, prior work items;
- for `fix`, the debugger's findings.

The planner writes `analysis.md` (below the baseline) and `plan.md`, and
returns a short report — files written, approach, repos/waves, open
decisions. Do not ask it to return document text and do not re-read the
documents just to restate them; read a section only when a later step
needs it. (A planner from an older workspace may still return full text —
write it to disk yourself, and suggest re-running `fullstack-init` to
refresh the workspace agents.)

### 4c. What every plan must carry

These bind whoever writes. The templates hold the exact shapes.

- **The smallest change that meets the requirements.** The recommended
  option is the smallest one that satisfies every `REQ` — for a `fix`, the
  smallest one that removes the reported symptom. Generalized hardening,
  framework-level fallbacks, and "while we are here" refactors go to
  §Follow-up as candidates unless a `REQ` asks for them; list the larger
  option in the strategy table with why it was not chosen. Every extra
  mechanism adds risks, tests, and review findings of its own.
- **Testable Success Criteria.** "Works correctly" is not one; "returns 200
  with JSON matching schema X for inputs A, B, C" is.
- **Frozen cross-repo contracts (multi-repo).** `fullstack-apply` derives
  parallel waves from the `Depends On` column, and downstream repos code
  against interfaces while upstream is still being built. So every
  interface crossing a dependency edge is frozen in `analysis.md`: exact
  signatures and field names/types, error codes, shared types, env-var
  names, migration order. Never leave names to be improvised during apply.
- **`plan.md` §Summary / §摘要** — the decision-maker's six-line entry point
  (one sentence with no ids or file refs / plain words: what is different
  once this ships / status incl. tier / decisions needed / not solved /
  where to read). The only section updated in place as the item evolves.
- **`plan.md` §Code Map / §代码地图** — one row per expected file:
  `repo | repo-relative path | symbols | what changed`. Planned paths are
  fine; apply replaces them with actual ones. It is the reverse index a
  later fix uses to find this item from a file.
- **Writing Rules for Decision Readers** (`template-rules.<lang>.md`) bind
  every section: conclusion first, terms explained on first use, costs as
  concrete rework. The user approves without reading the codebase.

### 4d. Mechanical gates

Run each that applies; fix and re-run until it passes.

| Gate | When | Command |
|------|------|---------|
| Mermaid | Any document has a ` ```mermaid ` block | `python3 SKILL_PATH/scripts/mermaid_lint.py <file>...` → `STATUS=PASS` |
| DAG | Multi-repo | `python3 SKILL_PATH/scripts/compute_waves.py <work-dir>` → `REPOS/WAVES/WAVE_i`; record "Parallel waves: W1(a,b) → W2(c)" under the repositories table. `ERROR_*` → fix the table; `CYCLE_REPOS` → restructure dependencies or split the item |
| Consistency | Before each plan review round, and before reporting | `python3 SKILL_PATH/scripts/plan_lint.py <work-dir>` → `STATUS=PASS`. `ERROR:` lines name what to fix; turn `WARN:` `TBD` / `待确认` markers into `NEEDS_USER_DECISION`. Fix — never reason around a failure |

### 4e. Re-check the tier

Now that `plan.md` has its repositories table and Code Map, confirm the
tier against the table in "How this skill works". If a lean item turned out
to need full (a second repo, a contract, a schema change), upgrade it,
tell the user in one line, and continue at full. Record the tier in the
§Summary status line (`…—— lean 档` / `…—— lean tier`).

## Step 4.5 — Plan Review Gate

The gates above check shape; this checks meaning. Delegate to the
**plan-reviewer** subagent to falsify the plan against the original
requirements. It must be a fresh context: whoever wrote the plan carries
its assumptions, and a self-review re-runs them.

**The reviewer receives:** the path to the work directory and the
instruction to read `analysis.md` §Original Requirements and
§Clarifications plus `analysis.md` and `plan.md` **from disk** (never your
summary); the workspace `AGENTS.md` repo table; the affected repos'
`AGENTS.md` / `README.md` paths; the round number. If §Original
Requirements is missing or has no `REQ` ids, stop and write it first.
§Clarifications may be absent only when `progress.md` records a Step 3.5
skip.

If the host cannot load `plan-reviewer`, use any fresh-context read-only
subagent with the agent file as its brief; if even that is impossible,
review it yourself and **label it a self-review in `review.md`**.

**Depth.** Lean: 1 pass; on `NEEDS_FIXES`, fix, re-run the mechanical
gates (not a round), then one confirmation pass; still not converged →
record residual P1/P2 as known risks and close `PASS_WITH_RISKS` (an open
P0 moves the item to the full loop). Full: pass → revise → re-review, at
most 3 passes. Do not skip the gate because the plan "looks fine".

**Verdicts.** Append each round to `review.md` as
`## Plan Review — Round <N> — <date>` / `## 方案审查 — 第 <N> 轮 — <date>`
(format: `template-review.<lang>.md`).

| Verdict | Action |
|---------|--------|
| `PASS` | Step 5 |
| `PASS_WITH_RISKS` | Step 5; the risks appear in `plan.md` §Risks |
| `NEEDS_FIXES` | **Read `references/plan-review-rounds.md`.** Send the P0/P1 findings verbatim to the planner (full) or fix them yourself (lean) — affected sections only, every P0/P1 fixed or rejected with a written reason; then the next round on the minimal round-2+ brief, as a fresh agent |
| `NEEDS_USER_DECISION` | Stop the loop; ask the user in the Step 5 report |

Non-negotiable in every round:

- **Never weaken a plan to pass** — no deleting criteria, widening a
  contract to "TBD", or dropping a requirement. An honest choice only the
  user can make is `NEEDS_USER_DECISION`.
- **A fix that narrows a `REQ` is the user's call** — report
  `NEEDS_USER_DECISION`, quoting the requirement and naming the subset.
- **A plan that contradicts an answered clarification is a P0.**
- **In the same edit as any revision**, keep the documents in step:
  Success Criteria ↔ `review.md` Evidence rows; `REQ` ids ↔ coverage
  matrix; tasks ↔ affected-task list; touched files ↔ Code Map; a moved
  responsibility / changed flow / altered contract ↔ the `analysis.md`
  section and diagram, rewritten (never a contradicting note appended);
  a dated `progress.md` entry; `plan.md` §Summary and `review.md` §Status
  Overview updated in place. Then re-run the affected mechanical gates.

**Exit criteria — all must hold before reporting the plan as ready:**
verdict `PASS` / `PASS_WITH_RISKS` with no open P0/P1; §Original
Requirements has one verbatim `REQ<n>` per ask; every plan-shaping
decision is answered, `A<n>` with a reversal condition, or escalated; every
requirement maps to ≥1 Success Criterion and every criterion to ≥1 task;
frozen contracts complete (or `TBD` with the user's decision recorded);
every path / symbol / endpoint cited as existing is verified; dependency
edges verified semantically; Mermaid and DAG gates pass; §Summary matches
the body; `plan_lint.py` reports `STATUS=PASS`. Otherwise report the
blocking items instead.

## Step 5 — Commit and Report

1. Commit the work directory to the docs repo (the only repo this skill
   commits to).
2. Report — verdict first, plain words:

```
Planned: <work-name> (<feat|fix|refactor>)
Location: <docs-dir>/changes/<type>/<work-name>/
Mode: standard | deep (spike) — tier: lean | full

- In plain words: <what will be different once this ships, and the biggest remaining risk — no ids>
- Requirements: <summary>   Success Criteria: <N>
- Repos: <list>   Parallel waves: W1(<repos>) → W2(<repos>)
- Contracts frozen: <list | single-repo — none>
- Design: <one line>
- Plan review: <PASS | PASS_WITH_RISKS> — <N> rounds, <N> findings fixed
- Open decisions: <none | list>

Next: tell me to "implement this" to run fullstack-apply — preferably in a
fresh session; the work-directory documents are the handoff.
```

On `NEEDS_USER_DECISION`, replace `Next:` with a request for the decisions
("answer the open decisions above — I will re-run the plan review").

3. Issue-sourced work: close the issue as described in
   `references/issue-sourced.md`.

## Resuming and Re-reviewing

- **Resume** ("continue planning X"): read the work directory, find what is
  incomplete (missing sections, unfilled verdict, open findings or
  decisions in `review.md`), resume from that step; re-confirm repos if the
  plan changed. If the scope grows a lot (a new repo joins, the task list
  roughly doubles, a second independent goal appears), recommend splitting
  a successor work item unless the user asks to fold it in.
- **Review only** ("审一下这个方案", "is this plan ready?"): do not re-run
  Steps 1–4 — read `references/review-only.md`.

## Guardrails

- Planning only; no branches, no code-repo commits, no PRs.
- Four documents for every work item; `plan.md` always carries §Summary
  and the Code Map. A qualifying quick fix is not a work item — route it to
  `fullstack-apply`.
- Every plan passes the Plan Review Gate; never report it ready with an
  open P0/P1, an unanswered `NEEDS_USER_DECISION`, or a failing gate.
- Never weaken a plan to reach `PASS`.
- Multi-repo plans freeze cross-repo contracts and pass the DAG gate.
- Deep mode's output IS the work directory — no separate spike directory.
- Requirements: Python 3.10+; `jira`, `confluence`, `gh-operations`,
  `figma` skills as needed.
