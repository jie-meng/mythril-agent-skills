# Fullstack Skills — Lightweight Roadmap

A running record of the effort to keep the fullstack family proportionate:
the process a change goes through should scale with what can go wrong, not
with the fact that a change happened. Each round lists what was cut, what
was deliberately kept, and the evidence that triggered it. Add a new round
at the bottom of [History](#history) whenever the family is slimmed again,
and keep [Open items](#open-items) current.

**Hand-off use.** This document is the entry point for continuing the
work in a new session. Feed it to the agent together with a description
of the problem you observed (a run log, a work directory that felt too
heavy, a step that was skipped when it should not have been). The agent
reads [Current state](#current-state) to know where things stand, then
follows [Continuing the work](#continuing-the-work).

---

## Current state

*Updated 2026-11-24, after Round 3. Update this section in place at the
end of every round. Everything below [History](#history) is append-only.*

**Round status**

| Round | Status |
|---|---|
| Round 1 — slim the steps | Committed (`83fd454`) |
| Round 2 — quick-fix path | Committed (`381152f`) |
| Round 3 — family-wide review fixes | Implemented in the working tree and validated (pytest 1322 passed, descriptions ≤ 1024, shared assets and marketplaces in sync, `fullstack-init` rehearsed on a copy of a real workspace); committed 2026-11-24 as five `[fullstack-*]` / `[plan_lint]` / `[docs]` commits. Quick fix not yet exercised on a real change |

**How a change is routed today**

| Path | When | What runs | Documents |
|---|---|---|---|
| **Quick fix** (apply) | A bug root-caused with evidence, or a fully specified small tweak; one repo; no contract / schema / external-API change; small (~≤5 production files, ~≤150 lines); no active owner (an archived owner does not block) | Confirm once → branch → regression test → 1 independent code review → commit | None. The commit message is the record |
| **Lean** (propose → apply) | One repo, no cross-repo contract, no data / schema / migration, no external API | Orchestrator writes plan → plan review (1 pass + ≤1 confirmation) → orchestrator writes code → code review (1 + ≤1) | Four documents |
| **Full** (propose → apply) | Everything else, and deep (spike) mode | Planner → plan review loop (≤3) → developer per repo in waves → per-repo code review (≤3) → cross-repo review | Four documents |
| **Follow-up** on an active item | Feedback, log, manual-test finding, new REQ mid-implementation | Lean loop (one repo) or wave loop (several repos / contract change). **Never a new plan review** | Only the invalidated docs, plus a compact review round and a one-line Document Sync |

**Rules in force across all paths:** an independent code review before
every commit; the smallest change that meets the requirements (hardening
becomes a follow-up candidate); reviewers do not audit bookkeeping
wording; the debugger is skipped when the session already holds the
root-cause evidence. `plan_lint` blocks only on broken chains (criteria ↔
evidence, Code Map, task ids, round closure); writing-format checks
(Document Sync line, summary freshness, repo-skills line) are warnings.

**Workspace files:** `fullstack-init` refreshes three-way against a
baseline of what it generated last time. Template updates reach untouched
sections, bullets, repo rows, agent files, and README; user edits are
kept; real conflicts and first-run differences are parked in
`.agents/init-pending/` for a by-hand merge. The README language is saved
in `fullstack.json`.

**Where each rule lives**

| Rule | File |
|---|---|
| Quick-fix conditions and steps (**canonical** — other places summarize and point here) | `mythril_agent_skills/skills/fullstack-apply/references/quick-fix.md` |
| Rule consistency guard (quick-fix and lean-tier terms in every place that states them) | `tests/test_fullstack_rule_consistency.py` |
| Workspace `AGENTS.md` rules, incl. Docs-Code Lockstep routing (active owner / quick fix / work item) | `mythril_agent_skills/skills/fullstack-init/scripts/workspace_init.py` (`generate_agents_md`) |
| Three-way workspace refresh | `mythril_agent_skills/skills/fullstack-init/scripts/workspace_init.py` (`three_way`, `merge_agents_md_report`, `install_agents`, `bootstrap_workspace`) |
| Quick-fix routing, tier table, debugger skip, smallest-change rule | `mythril_agent_skills/skills/fullstack-propose/SKILL.md` (How this skill works, Step 3, 4b, 4c) |
| Apply entry points, lean loop, wave loop | `mythril_agent_skills/skills/fullstack-apply/SKILL.md` (Step 1, Step 4) |
| Follow-up loop, no plan re-review, compact rounds | `mythril_agent_skills/skills/fullstack-apply/references/follow-up.md` |
| Plan-review round caps and briefs | `mythril_agent_skills/skills/fullstack-propose/references/plan-review-rounds.md` |
| Reviewer and planner behavior (copied into workspaces by `fullstack-init`) | `mythril_agent_skills/skills/fullstack-init/agents/{plan-reviewer,planner,code-reviewer,debugger,developer}.md` |
| Mechanical cross-document checks and their severity | `mythril_agent_skills/shared/plan/plan_lint.py` (canonical; bundled copies via `scripts/sync-shared-assets.py`) |
| Document templates | `mythril_agent_skills/shared/plan/document-templates.md`, `review-formats.md` (canonical; split per part and language) |
| Next-step recommendations, capturing findings as issues | `mythril_agent_skills/skills/fullstack-explore/SKILL.md` (Step 7) |

**Known caveat:** a workspace picks up Rounds 2–3 (agent rules, the new
Lockstep routing, the three-way baseline) only after `fullstack-init` is
re-run there. The first re-run lists sections that differ from the
template under `Review once`; merge them from `.agents/init-pending/`.

## Continuing the work

When a new problem report arrives:

1. **Classify the weight.** Decide whether it is per-step cost (one step is
   slow or reads too much) or fixed per-item overhead (a whole stage ran
   that the change did not need). Use the table in
   [Where the weight comes from](#where-the-weight-comes-from).
2. **Measure the run.** Record the measures from Round 2's table: first-diff
   size, document size, review rounds by kind, confirmation stops, time to
   the first code. Also record which findings were real defects and which
   were bookkeeping.
3. **Find the rule that caused it.** Use [Where each rule lives](#current-state).
   Often the cause is a sentence that makes a step mandatory "in every
   tier" or "every round".
4. **Check it against the principles.** Never remove a check that caught a
   real defect in the measured run. Prefer routing (a lighter path for a
   clearly defined case) over weakening a check everywhere.
5. **Change and validate.** Edit canonical files only: shared assets
   under `mythril_agent_skills/shared/`, then run
   `python3 scripts/sync-shared-assets.py`. Then run
   `python3 scripts/validate-skill-descriptions.py`,
   `python3 scripts/sync-shared-assets.py --check`, and `pytest`. Update
   `workflows.md` / `overview.md` / `README.md` when user-facing behavior
   changes.
6. **Record it here.** Append a new round under [History](#history) with
   its trigger, measures, changes, and what was kept on purpose. Rewrite
   [Current state](#current-state) and prune or add [Open items](#open-items).

---

## Principles

1. **Ceremony scales with the stakes.** A plan exists to be falsified while
   it is still cheap to change. When nothing in a plan can be wrong in an
   expensive way (one repo, a known root cause, no contract change), the
   plan is overhead and the code review is the real check.
2. **Cut the fixed overhead, not the independent checks.** The checks that
   catch real defects are an independent code review before every commit
   and testable acceptance. Those stay at every size. What shrinks is
   documents, plan-review rounds, and hand-offs.
3. **The smallest change that meets the requirements.** Every extra
   mechanism a plan adds brings its own risks, tests, and review findings,
   and reviews then dig into all of them. Hardening that no requirement
   asks for is a candidate follow-up, not part of the fix.
4. **Reviews check meaning, scripts check bookkeeping.** Cross-document
   consistency (criteria ↔ evidence rows, task ids, round numbering) is
   `plan_lint.py`'s job. A reviewer round spent on wording drift between
   logs is a wasted round.
5. **Follow-ups do not re-open planning.** Once code exists, the code
   review of each fix is the check. New requirements mid-implementation are
   appended, not re-planned.

## Where the weight comes from

Two different costs, and they need different fixes:

| Cost | What it looks like | Fixed by |
|---|---|---|
| **Per-step cost** | Large `SKILL.md` files read in full, the planner returning a full document that is then written again, diffs pasted into reviewer briefs, every template loaded up front | Round 1 |
| **Fixed per-item overhead** | Four documents, `plan_lint`, an independent plan review, and per-round document attestation for *every* change — even a small, already-diagnosed bug | Round 2 |

Round 1 made each step cheaper but explicitly kept the fixed overhead
("the tier changes who writes and how many review rounds run — never
whether checks run"). Small fixes still felt heavy, which led to Round 2.

---

## History

### Round 1 — slim the steps (2026-11-23, commit `83fd454`)

**Changes**

- The planner subagent writes `analysis.md` / `plan.md` to disk and returns
  a short summary instead of the full text, so nothing is generated twice.
- Lean tier widened: the 5-file cap was removed. At lean tier the
  orchestrator writes the plan and the code itself, still gated by an
  independent plan review and code review.
- Follow-up fixes pick the lean loop or the wave loop by the size of the
  fix, not the size of the item.
- `fullstack-propose` and `fullstack-apply` `SKILL.md` went from ~50 KB to
  ~20 KB each. Conditional paths moved into `references/` and are read on
  demand.
- `document-templates.md` is split by `sync-shared-assets.py` into one file
  per part (`rules` / `plan` / `progress` / `analysis` / `review`), so each
  step reads only the template it writes.
- Reviewers fetch diffs themselves rather than receiving pasted diffs.

**Kept on purpose:** four documents and the same mechanical gates at every
tier, plus an independent plan review even at lean.

### Round 2 — a quick-fix path below lean (2026-11-24)

**Trigger — a real run on a small bug.** A voice-message playback bug in
one backend repo. The root cause had already been established in the
session with device and server logs and database evidence: the playback
window held no messages, and an empty tool response left the device's TTS
session open. The user asked for a work item, and the run went through the
full propose → apply flow:

| Measure | Value |
|---|---|
| First code change | 10 files, +208 / −12, about half of it tests |
| Work-item documents | 4 files, ~717 lines, ~90 KB; `review.md` alone ~58 KB |
| Review rounds | 3 plan reviews + 2 code reviews |
| User confirmation stops before code | 2 (open the item, start apply) |
| Time from "open a work item" to the first code | ~70 minutes |

What the run showed:

- **The design was inflated, not only the process.** The analysis already
  listed a minimal option: return a localized "no messages" prompt, which
  the normal chat pipeline speaks and closes. That was 3 files and low
  risk, and it removed both user-visible symptoms. The plan chose a broader
  option that added a generic "close an empty TTS turn" fallback (a
  side-speech counter, a turn-id snapshot, changes in three more files).
  Most of the registered risks and most review findings came from that
  fallback.
- **Plan-review rounds were spent on bookkeeping.** The round-2 plan
  review's two findings were both wording mismatches between
  `progress.md` / `review.md` and `plan.md`.
- **The root cause was analyzed twice.** For `fix` items, the debugger
  subagent was mandatory even though the session had already root-caused
  the bug with evidence.
- **A follow-up triggered a third plan review.** A product-rule change
  decided after device testing (widen the playback window to the retention
  period) caused another full plan-review round, then a code review. The
  code review alone would have caught the real defects. It did catch two
  real P1s: a 9-day-old message announced as a weekday, and an unread
  count that did not follow the configured window.

**Changes**

- `fullstack-apply/references/quick-fix.md` (new): a root-caused, one-repo,
  small bug fix, with no contract / schema / external-API change and no
  active owner (`plan_lint.py --find`), is fixed with **no work item**:
  confirm once (skipped if the user already approved the exact fix) →
  branch → regression test → one independent code review → commit. The
  commit message is the record. Mid-fix escalation goes to
  `fullstack-propose` when a condition stops holding. A product-rule
  change decided mid-fix becomes its own quick fix and its own commit.
- `fullstack-propose`: a qualifying fix is routed to the quick fix at
  Step 3 and nothing is written. The debugger is skipped when the session
  already holds the root-cause evidence. New 4c rule: recommend the
  smallest change that meets every `REQ`, and list broader hardening as a
  follow-up candidate together with why it was not chosen.
- `planner.md` (workspace agent): the same smallest-change rule.
- `plan-reviewer.md` (workspace agent): bookkeeping is not audited.
  Wording drift in `progress.md` / `review.md` is not a finding; only a
  `plan.md` §Summary that misstates scope / status / decisions is (P1).
- `fullstack-apply/references/follow-up.md`: a follow-up never re-runs the
  plan review. A requirement added mid-implementation is appended as the
  next `REQ` with its criterion and tasks, and covered by the code review.
  Only the documents the round invalidated are updated. Follow-up review
  rounds are compact (scope, findings, verdict, the Evidence rows changed,
  Repo Skills, and a one-line Document Sync).
- `fullstack-explore`: recommends a quick fix for a root-caused small bug.
- `workflows.md`, `overview.md`, and `README.md` were updated to match.

**Kept on purpose:** the independent code review before every commit,
including quick fixes. The Document Sync attestation for work items is
also kept, because `plan_lint` check 10 enforces it and it costs one line.
Work items keep the four documents and the plan review.

**Rollout note:** `planner.md` and `plan-reviewer.md` are templates that
`fullstack-init` copies into each workspace. Existing workspaces must
re-run `fullstack-init` to pick up the new rules.

### Round 3 — family-wide review fixes (2026-11-24)

**Trigger.** A design review of the whole `fullstack-*` family after
Round 2, and a check of whether re-running `fullstack-init` is safe. The
review found the skeleton sound: directory-as-state lifecycle,
deterministic gates in scripts, single-source shared assets with a drift
test, independent reviews, and broad tests. The weaknesses were
duplicated prose rules, a workspace rule that made every code edit heavy,
lint coupled to writing format, and an init re-run that could neither
deliver template updates nor protect edits. Round 2 had already caused one
real drift: the generated workspace `AGENTS.md` still said every change
needs a work item, which contradicted the new quick fix.

**Findings and changes**

| # | Finding | Change |
|---|---|---|
| 1 | Rules duplicated across skills, agent templates, and the generated `AGENTS.md`, with no guard | Canonical source named for the quick-fix conditions (`quick-fix.md`); the docs-dir `AGENTS.md` bullet became a pointer; `tests/test_fullstack_rule_consistency.py` pins the quick-fix and lean-tier terms in every place that states them |
| 2 | The workspace Lockstep rule applied full document ceremony to **every** code edit, and any edit to archived code needed a new work item | Lockstep rewritten as a three-way routing: active owner → follow-up; no active owner + quick-fix conditions → quick fix; otherwise ask about a work item. The quick fix widened from bugs to fully specified small tweaks |
| 3 | `plan_lint` treated writing format as blocking errors | Checks 10 (Document Sync line), 12 (summary freshness), and 14 (repo-skills line) became warnings; structural checks stay errors |
| 4 | `fullstack-init` re-runs: untouched sections never received template updates (a real workspace still had a years-old *Work Tracking* section); repo-table edits and notes were overwritten; agent files were always overwritten; README language flipped with the prompt language; template-dropped sections lingered; and the merge dropped the text between H1 and the first section and reordered hand-written files | Three-way refresh against `.agents/.fullstack-init-baseline.json` for AGENTS.md sections / convention bullets / repo rows, agent files, README, and the docs `AGENTS.md`; conflicts and first-run differences parked in `.agents/init-pending/`; README language saved in `fullstack.json`; preamble and section order preserved; a hand-written docs `AGENTS.md` gets no sections added |
| 5 | `fullstack-explore` was the largest `SKILL.md` (22 KB) despite being read-only and the most used | Cut to ~8 KB; graphify query detail and answer formats moved to `references/` |
| 6 | Explore inconsistencies: a hand-written workspace gate, a legacy `<docs-dir>/feat/` path, no Code Map lookup, and "capture findings" writing a one-document work item | Explore uses `check_workspace.py`, looks up file/symbol owners via `plan_lint --find`, and records findings through `fullstack-issue-create`; `check_workspace.py` now also fails when the configured docs directory is missing |

**Rehearsal.** `fullstack-init` was run on a copy of a real workspace with
no baseline. The hand-written docs `AGENTS.md` was untouched. In the
workspace `AGENTS.md`, only the skill-owned Lockstep section changed. The
agent files received the Round 2 rules, and README gained the quick-fix
section. The stale *Work Tracking* section was listed once for review, with
the new template parked. A second run was quiet apart from the pending
reminder.

**Kept on purpose:** `--force` still exists as the explicit "discard my
edits" switch. Skill-owned `AGENTS.md` sections (*Directory Structure*,
*Docs-Code Lockstep*, *Documentation Diagrams*) and shipped convention
bullets still always take the template, because their commands are
machine-resolved. `fullstack-docs-migration` is unchanged; see Open
items.

---

## Open items

Candidates for the next round, roughly in order of expected payoff:

1. **`review.md` size for full work items.** Plan-review and code-review
   rounds still append the reviewer's full output (scope, coverage,
   findings, verified, unverified). Consider a compact round format for
   every round, keeping only findings, verdict, and evidence rows. Move
   the verified / unverified detail to a collapsible block, or drop it
   once the verdict is `PASS`.
2. **Lean-tier plan review.** For a lean item whose requirements are
   unambiguous, the independent plan review mostly re-checks what the code
   review will check. Measure how often lean plan reviews raise a P0/P1
   that the code review would not have caught. If that is rare, make the
   lean plan review opt-in.
3. **Stale workspaces.** Re-running `fullstack-init` is now safe, but
   nothing tells the user it is due. Record a template digest in the
   baseline, and have `check_workspace.py` (or the init skill itself)
   compare it with the installed templates and warn when a re-run would
   change something.
4. **`plan_lint` coupling to four documents.** Archive, `--find`, and the
   lint all assume the four-file layout. If a lighter work-item shape
   (for example a single `fix.md`) is ever wanted between the quick fix
   and lean, those three need to accept it first. Round 3 only lowered
   the format checks to warnings; 1600 lines of prose-matching remain.
5. **Confirmation stops.** Propose Step 3 and apply Step 2 each stop for
   confirmation. When apply follows directly from an approved propose in
   the same session with an unchanged repo list, the second stop could be
   skipped.
6. **Quick-fix calibration.** The "small" guide (~5 production files,
   ~150 lines) is a first guess. Revisit it after a handful of real quick
   fixes: escalations mid-fix mean it is too loose, and work items that
   could have been quick fixes mean it is too tight.
7. **Retire `fullstack-docs-migration`.** It is a one-time migrator from
   the pre-`changes/` layout. Once no workspace on the old layout remains,
   mark it deprecated and later remove it, so it stops costing upkeep.
8. **Remaining prose duplication.** The consistency test pins key terms
   only. The document-update table still appears in the workspace
   `AGENTS.md` and in `follow-up.md`; if it drifts again, generate one from
   the other.

## How to evaluate a slimming change

Before calling a round done, run it on a real item. Record the result in
that round's entry using the same measures as Round 2's table: first-diff
size, document size, review rounds by kind, confirmation stops, time to
the first code, and which review findings were real defects versus
bookkeeping. A slimming change is a regression if it removes a check that
caught a real defect in the previous measurement.
