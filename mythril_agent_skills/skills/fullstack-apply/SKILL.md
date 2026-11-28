---
name: fullstack-apply
description: >
  Implements a planned work item across a multi-repo fullstack workspace:
  repos in dependency-order waves, staged and cross-repo reviews against the
  plan's Success Criteria, PRs, and the four tracking documents. Input is a
  work dir from fullstack-propose. Sticky on an active work item — follow-up
  fixes from feedback or pasted logs run the same review loop. Also does a
  one-repo quick fix with no work item. Triggers: "fullstack implement",
  "全栈实现", "implement this plan", "实现这个方案"; inside a fullstack
  workspace (fullstack.json at the root) also "fix this", "这里不对", "直接修",
  "quick fix" — outside one, those are ordinary fix requests, not this
  skill.
license: Apache-2.0
---

# Fullstack Apply

Implement a planned work item in a workspace initialized by
`fullstack-init`. The input is a work directory created by
`fullstack-propose`:

```text
<docs-dir>/changes/<type>/<work-name>/
├── analysis.md   # why and how (may include spike findings)
├── plan.md       # Summary, Success Criteria, repos, Code Map, tasks
├── progress.md   # dated change log
└── review.md     # plan review rounds + code review rounds + Evidence table
```

This skill does NOT plan. No work directory for the request → tell the
user to run `fullstack-propose` first — except a **quick fix**: a bug whose
root cause is already established (or a fully specified small tweak), in
one repo, small, with no contract change, is made directly with no work
item (`references/quick-fix.md`).

## How this skill works

| | Lean tier | Full tier |
|---|---|---|
| **When** | The tier `plan.md` §Summary records as lean (single repo, no cross-repo contract, no data/schema/migration or external-API change) | Everything else |
| **Who writes code** | You, directly in the repo | **developer** subagents, one per repo, repos of a wave in parallel |
| **Review** | 1 independent **code-reviewer** pass + at most 1 confirmation | Per-repo code-reviewer (≤3 rounds) + one cross-repo review |

Both tiers keep: an independent code review before every commit, the
Success Criteria gate, `plan_lint`, the Mermaid gate, and documents updated
in the same pass as code. Lean drops the developer hand-off — for one repo
it costs a full context rebuild and buys no parallelism.

**Reading discipline — load only what the current step needs.**

| File | Read when |
|------|-----------|
| `references/template-progress.<lang>.md` | Writing a `progress.md` entry |
| `references/template-plan.<lang>.md` | Updating `plan.md` §Summary or Code Map |
| `references/template-analysis.<lang>.md` | Rewriting an `analysis.md` section the code invalidated |
| `references/template-rules.<lang>.md` | Writing document prose or the final report |
| `references/review-formats.<lang>.md` | Writing a code review or cross-repo section in `review.md` |
| `references/cross-repo-review.md` | After the final wave of a multi-repo item |
| `references/full-tier.md` | Step 4, only at full tier |
| `references/pr-creation.md` | Step 7, only when `github_repos=true` |
| `references/no-vcs-repos.md` | A repo in scope has no git metadata |
| `references/quick-fix.md` | A root-caused bug or fully specified small tweak — one repo, small — with no work directory |
| `references/follow-up.md` | Feedback, a log, or a fix request on an implemented item; resuming |
| `references/lessons-learned.md` | Step 8, only when a lesson clears its value bar |
| `references/MERMAID-RULES.md` | Before editing a diagram |

`SKILL_PATH` is this skill's installed directory. `<lang>` is `en` or `zh`.

## Workspace Validation Gate

Before reading any work directory (later steps need the values it prints):

```bash
python3 SKILL_PATH/scripts/check_workspace.py
```

It prints `WORKSPACE_VALID`, `MISSING`, `DOCS_DIR`, `GITHUB_REPOS`. Never
substitute a manual file check — later steps need `docs_dir` and
`github_repos` from it.

- `WORKSPACE_VALID=false` → STOP: tell the user the workspace was not
  detected, list the `MISSING=` markers, and ask them to `cd` to the
  workspace root and restart the agent, or run `fullstack-init` first.
- `WORKSPACE_VALID=true` → output EXACTLY this line (always English), then
  continue:

  ```
  Workspace: VALID | docs_dir=<DOCS_DIR> | github_repos=<true|false>
  ```

This line commits you: `github_repos` decides Step 7, `docs_dir` locates
work directories. If you lose track mid-session, re-run the script once and
re-announce — never guess.

## Language

Documents and user-facing messages match the user's prompt: an explicitly
requested language wins; otherwise any Chinese character → Chinese;
otherwise English. Branch names are English Title-Case-With-Hyphens; commit
messages follow each repo's convention.

## Code Comment Policy

Generated and modified code has **no comments by default** — the code says
what it does. Exceptions, in order: (1) **repo convention wins** —
mandatory docstrings, license headers, a comment language; (2) without a
convention, only critical **why** comments — a non-obvious trade-off, a
workaround and its reason, a bug reference, an order-sensitive constraint.
Never explain *what*. Keep existing comments unless their lines are
removed. This policy goes verbatim into every developer brief.

## Step 1 — Identify the Work Item

1. Named item ("implement add-dark-mode") → find it under
   `<docs-dir>/changes/<type>/<name>/`.
2. Unnamed reference → list active items under `changes/{feat,refactor,fix}/`
   and ask.
3. A bug fix or small tweak with no work directory → if it meets every
   condition in `references/quick-fix.md` (cause or change fully
   understood, one repo, no contract change, small, code not owned by an
   active item), read it and follow it instead of Steps 2–7. Any other new requirement → STOP;
   `fullstack-propose` first.
4. Feedback / a log / a fix on an already-implemented item → read
   `references/follow-up.md` and follow it instead of Steps 2–7.

**Start clean.** When this session already holds propose, exploration, or
unrelated discussion, recommend running apply in a fresh session before
starting: every orchestration step re-sends that history, and the work
directory is the complete handoff.

**Read what you need, not everything.** Read `plan.md` and `analysis.md` in
full — they are the spec. From `review.md` read §Status Overview and the
Evidence table; from `progress.md` the latest entries. Open older review
rounds or log entries only when a step needs them; the history is on disk.

**Tier.** Use the tier recorded in `plan.md` §Summary. Run full when none is
recorded, the user asks for full, or the work has outgrown lean (a second
repo, a cross-repo contract, persisted data / schema / migration, an API
consumed outside the repo). Record an upgrade in `progress.md`.

Partially complete → see "Resuming" in `references/follow-up.md`.

## Step 2 — Confirm Repos, Branches, and Waves

For multi-repo items, first compute the waves (do not layer repos by eye —
transitive dependencies and cycles hide there):

```bash
python3 SKILL_PATH/scripts/compute_waves.py <work-dir>
```

`REPOS=<n>` / `WAVES=<k>` / `WAVE_i=a,b` → the wave plan. Any `ERROR_*` or
`CYCLE_REPOS` → STOP and send the item back to `fullstack-propose`; never
hand-patch the order.

Then present, even when confident, and wait for confirmation:

```
Based on the plan, I'll modify these repositories:

  1. shared-lib/ — Add theme constants      Branch: feat/Dark-Mode-Toggle
  2. api/ — Add user preference endpoint     Branch: feat/BE-450/Dark-Mode-Toggle
  3. web/ — Settings toggle                  Branch: feat/WEB-77/Dark-Mode-Toggle

Wave plan:  W1 shared-lib → W2 api → W3 web
Tier: full

Does this look correct?
```

## Step 3 — Branches

**Naming:** `<type>/<JIRA-KEY>/<Title-Hyphenated>` with a Jira key,
`<type>/<Title-Hyphenated>` without, `-vN` appended for a successor. Take
branch names from `plan.md`; derive any that are missing. With several Jira
tickets, match each ticket to its repo by platform / component (ask if
ambiguous) and record each repo's branch in `plan.md`.

**For each affected code repo** (never the docs repo — it commits straight
to its main branch): find the default branch (`main`, `master`, `dev`, in
that order); if the target branch exists, check it out (or stay if already
on it); otherwise `git checkout <default> && git pull && git checkout -b
<branch>`. A repo without git metadata → read `references/no-vcs-repos.md`.

## Step 4 — Implement

### The implementer checklist (both tiers)

Whoever writes the code — you at lean, the developer at full — inside the
repo:

1. Read the repo's `AGENTS.md` (mandatory conventions), then `README.md`
   (build / test / lint). `AGENTS.md` wins where both speak.
2. Load repo skills: `python3 SKILL_PATH/scripts/repo_skills.py <repo>`
   prints the index (repo-private skills are invisible from the workspace
   root). Read the `SKILL.md` of each skill matching the task and treat it
   as binding; run its commands from the repo root. Skip non-matching ones.
3. Repo-level agents in `<repo>/.agents/agents/` handle that repo's
   internals when present.
4. `python3 SKILL_PATH/scripts/graphify_check.py <repo>` — when
   `graphify-out/` exists, `graphify query` before reading files.
5. Find the test command: documented in README/AGENTS → use it; a test
   layout but no documented command → `tests: unknown`; nothing → `tests:
   none`. Never invent or run a guessed test command.
6. Set up the environment (venv, nvm, …), implement per the plan and the
   Code Comment Policy. While iterating, run the tests of the touched
   modules; before staging, run lint → type-check → tests → build once as
   the repo supports, keeping only the summary and failures in the output.
   A test that proves a Success Criterion exercises the boundary the
   criterion names — never a mock of it. Porting existing logic → a
   differential check (original vs port on the same generated inputs),
   kept as a test or re-runnable script.
7. No long-running dev servers or listening ports.
8. Stage everything (`git add .`). Result: changed files (repo-relative),
   test result (`tests: passed | failed | unknown (no run command
   documented) | none`), any drift from a frozen contract, a commit message
   in the repo's convention.

### Lean loop (one repo)

1. Run the implementer checklist yourself.
2. **Independent review** — delegate to a fresh **code-reviewer**
   subagent, mode per-repo, with: the repo's tasks and the Success Criteria
   it proves (quote them), the relevant `analysis.md` section paths, your
   change summary and test result, and the work-dir path. It runs
   `git diff --cached` itself. Never self-review when a subagent is
   available — you wrote the code and carry its assumptions.
3. `NEEDS_FIXES` → fix. If every finding is P1 and each fix is proven by
   tests / lint / build, re-run those instead of a review round. A P0, or a
   fix nothing mechanical proves, gets **one** confirmation review — a
   fresh code-reviewer on the round-2+ brief below. Still open after it →
   escalate to the user (a P0 never closes as a known risk).
4. `PASS` / `PASS_WITH_RISKS` → commit and bookkeep (4e).

### Full tier — the wave loop

**Read `references/full-tier.md`.** Repos run in dependency waves from
`compute_waves.py`; a wave is a barrier (the next starts only when every
repo of the current one has committed). Each repo — or each phase of a
large repo slice — gets a fresh **developer** subagent, then its own
per-repo code review (≤3 rounds) and commit (4e below); fix rounds go to
a fresh developer. You write only the tracking documents, commits, and
PRs. After the final wave's gate → Step 5.

### Reviews and commits (both tiers)

If the host cannot load `code-reviewer`, use any fresh-context read-only
subagent with the agent file as its brief; failing that, self-review and
**say so in `review.md`**.

**Round 2+ briefs (both tiers).** Every re-review runs as a **fresh**
code-reviewer on ONLY: the previous round's output, the `review.md` §Status
Overview, the Evidence table, this round's change list, and the instruction
to read the staged diff. No document history — it lives on disk.

**4e. Commit and bookkeep, per repo, as each passes** (never hold a green
repo hostage to a red sibling):

1. `git commit -m "<message>"` — the developer's message reconciled with
   repo convention. One commit per repo per round unless `plan.md`
   schedules phases or the user asks.
2. `progress.md` — commit summary and verdict (`**Result**:` / `**结果**：`
   first line, process notes in the tail; see the template).
3. `plan.md` Code Map — merge the round's actual paths (union of
   `git show --name-only` over every commit of the round). Rows from earlier
   rounds stay; unplanned touched files go in.
4. `review.md` — the round's `**Document Sync**` / `**文档同步**` line (one
   clause per document: what changed or why nothing did), and for a repo
   that ships `.agents/skills/`, the `**Repo Skills**` / `**仓库技能**` line
   listing every indexed skill and which were read. A round that moved a
   responsibility, changed a call order, or altered a contract has
   invalidated `analysis.md` — rewrite that section now. Formats:
   `review-formats.<lang>.md`.
5. `graphify_check.py <repo>` → if present, `graphify update` in the repo.

## Step 5 — Cross-Repo Consistency Review (multi-repo only)

Single-repo items skip this. Multi-repo: read
`references/cross-repo-review.md` and run it — once, over all repos' final
diffs. Per-repo reviews never substitute for it.

## Step 6 — Finalize the documents

Runs before anything leaves the machine — no push, no PR while a gate
fails.

1. Bring the documents to their final state: `analysis.md` updated in
   place if the approach, structure, or flow changed (the dated note goes
   in `progress.md`), the final `progress.md` entry, `plan.md` tasks
   checked off and §Summary refreshed to the final state, the Evidence
   table closed, and `review.md` §Status Overview refreshed.
2. Run the gates — all must pass; fix and re-run, never reason around one:
   - **Review completion** — `review.md` has a code-review verdict
     (`### Verdict` / `### 结论`) for every repo, and a cross-repo verdict for
     multi-repo items. A plan-review verdict does not count — it predates the
     code.
   - **Success Criteria** — every criterion is `✅ Pass` with evidence,
     `❌ Fail`, or waived with a documented reason. A criterion only a test
     run can prove, with no verified run, is `⚠️ Skipped (no verified test run
     in <repo>)` — never `✅`. A criterion changed during implementation syncs
     its Evidence row in the same edit.
   - **Documents match the code** — `analysis.md`'s approach, structure, flow,
     and diagrams describe what was committed (contradicted sections are
     rewritten, not annotated); `plan.md` tasks match `progress.md`; the Code
     Map covers every changed file; every code-review round carries its
     Document Sync (and Repo Skills) line.
   - **Mermaid** — `python3 SKILL_PATH/scripts/mermaid_lint.py <file>...` on
     every work-dir file with a ` ```mermaid ` block → `STATUS=PASS`.
   - **Consistency** — `python3 SKILL_PATH/scripts/plan_lint.py <work-dir>` →
     `STATUS=PASS` (run it last; a stale Evidence table is its most common
     failure).
3. Commit the docs repo.

## Step 7 — Push, Pull Requests, Report

1. Push each code repo's branch (`git push -u origin HEAD`; skip repos
   without git).
2. Pull requests — read the `Workspace:` line you announced (re-run
   `check_workspace.py` once if it is not in the transcript).
   - `github_repos=false` → output EXACTLY this line. Do not inspect
     remotes, look for other platform CLIs, or build compare URLs:

     ```
     Step 7: PRs skipped (github_repos=false — non-GitHub remote, PR creation is the user's responsibility)
     ```

   - `github_repos=true` → read `references/pr-creation.md` and follow it.
3. Report: with `github_repos=true`, the PR URL per repo; with `false`, the
   pushed branch per repo and "PR creation is your responsibility". Note
   any `tests: unknown` gap and offer to add the test command to that
   repo's `AGENTS.md` (never edit a repo document without approval).
4. Remind: "Tell me 'archive it' when you're ready (fullstack-archive)."

## Step 8 — Lessons Learned (optional)

Skip by default — most items produce no transferable lesson. Only for a
non-obvious trap, a cross-repo constraint future work will hit, a
hard-won design rationale, or a corrected recurring mistake: read
`references/lessons-learned.md`.

## Error Handling

- Test failures → fix them yourself (lean) or a fresh developer on a fix
  brief (full: `references/full-tier.md` 4c); non-obvious failures →
  debugger first, never "try and see".
- Environment setup fails → follow the repo README; if still failing, note
  it in `progress.md` and ask.
- Contract mismatch → fix upstream first, re-validate downstream (wave
  gate).
- Pre-existing failures → document in `progress.md`, do not block.
- Unexpected blockers → record in `progress.md` and ask.

## Guardrails

- Implements, never plans. No work directory → `fullstack-propose`, unless
  the request qualifies as a quick fix (`references/quick-fix.md`).
- Every commit is preceded by an independent code review; a red repo never
  releases its dependents and never blocks independent siblings.
- Waves come from `compute_waves.py`; structural errors send the item back
  to `fullstack-propose`. One agent per repo at a time.
- Code and documents move in the same pass, attested per round; the user
  never has to ask for the documents a second time.
- Never finalize with a failing gate or a silently dropped Success
  Criterion.
- The docs repo has no feature branches. Never reopen an archived work
  directory — successors are `-vN` items via `fullstack-propose`.
- Requirements: Python 3.10+; `jira`, `confluence`, `gh-operations`,
  `figma` as needed; `github-pr-create` + authenticated `gh` when
  `github_repos=true`.
