# Plan Review — round 2+ and loop rules

"The planner" below means whoever writes the plan: the planner subagent
at full tier, the orchestrator itself at lean tier.

Read this when a plan review round returns `NEEDS_FIXES`, or when a
`NEEDS_USER_DECISION` answer sends the plan back for another pass. A plan
that passes on its first round never needs this file. The non-negotiables
in `SKILL.md` Step 4.5 (never weaken a plan, a narrowed `REQ` is the
user's call, contradicting an answered clarification is a P0) bind every
round; they are not repeated here.

## Counting the rounds — the cap counts passes, and a re-plan starts a new loop

- The cap — lean: 1 pass + 1 confirmation; full: 3 passes — counts
  independent plan-review passes within the current loop.
- A **re-plan** starts a new loop. When the user answers a
  `NEEDS_USER_DECISION` with a different design and the planner rewrites the
  documents instead of amending them, the rewritten plan is a new proposal:
  its review is pass 1 of the new loop, and the cap is measured from there.
  Earlier rounds stay in `review.md` as history and are not re-counted. A
  rewrite changes design choices — a different option, a different data
  shape, a scope that moved — not wording.
- An answer that only **amends** the existing plan continues the current
  loop: the review of the amendment is the next pass of that same loop.
- A **mechanical-gate re-check** after a revision (`plan_lint` / Mermaid /
  DAG) is never a pass.

Record which loop the current round belongs to in `review.md` §状态速览 /
§Status Overview, next to the round count — `方案审查 4 轮（第 2–4 轮同一循环，
上限 3 轮）`. Without it a reader cannot tell a run that reached the cap from
one that quietly ignored it, and neither can the next agent.

## Round 2+ briefs — incremental, minimal, fresh

From round 2 on — every re-review after a revision — the brief holds ONLY
six items:

1. The latest round's complete output;
2. A `review.md` status-overview snapshot (§状态速览 / §Status Overview);
3. The Evidence table;
4. This round's change list — what the planner revised and where;
5. The diff or revised sections awaiting verification;
6. **Where the changed names are still used** — `grep -n` across
   `analysis.md` and `plan.md` for every id, field, endpoint, task, or
   criterion the revision renamed, removed, or redefined, with each hit's
   line. This is how a reviewer that does not re-read untouched sections
   still catches a revision that contradicts one.

A full re-read of earlier rounds and of the four documents is forbidden
in this brief — history lives in `review.md` and git, fetched on demand.
Dispatch the round-2+ confirmation as a **fresh agent** with this minimal
brief; do not continue an existing heavyweight subagent session — context
that grows every round is what makes repeats slow and unconvergent. When
no agent can be spawned, the fallback in `SKILL.md` Step 4.5 applies
unchanged.

## Rules that keep the loop convergent

- **The planner must answer every P0/P1** — fix it, or reject it with a
  written rationale, which you record in the same round as
  `Rejected: <reason>`. A finding silently dropped during revision becomes
  a P0 in the next round.
- **Round 2+ verifies the previous findings and the content changed to
  resolve them only** — never a fresh full audit. Otherwise every round
  harvests new P2s and the plan never converges.
- **Oscillation stops the loop.** If a round produces more new findings
  than the previous round resolved, stop and close the loop with a Plan
  Review Closure record (see below), then report the residual risks in
  Step 5.
- **Ending a loop that did not converge.** Lean confirmation still
  `NEEDS_FIXES`, the full cap reached, or oscillation: turn every open
  P1/P2 into an `R<n>` row in `plan.md` §Risks, then append the closure
  record from `template-review.<lang>.md` right after the last round —
  `**Why**`, `**Residual**: R<n>, …`, verdict `PASS_WITH_RISKS`. Leave the
  reviewer's `NEEDS_FIXES` verdict as written. An open P0 is never closed
  this way; `plan_lint` rejects a closure whose round still lists an
  unrejected `[P0]`.
- **Re-run the affected mechanical gates after revisions** — `plan_lint`
  after any document edit, the Mermaid gate if a diagram changed, the DAG
  gate if the repositories table changed. At lean tier this mechanical
  re-check runs in the same round as the revision and does not count as
  a review round.
