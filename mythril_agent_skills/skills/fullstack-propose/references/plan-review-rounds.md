# Plan Review — round 2+ and loop rules

"The planner" below means whoever writes the plan: the planner subagent
at full tier, the orchestrator itself at lean tier.

Read this when a plan review round returns `NEEDS_FIXES`, or when a
`NEEDS_USER_DECISION` answer sends the plan back for another pass. A plan
that passes on its first round never needs this file.

## Counting the rounds — the cap counts passes, and a re-plan starts a new loop


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

Do not skip the gate because the plan "looks fine" — that judgment is the
thing being tested.

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
no agent can be spawned, the fallback above applies unchanged.

**A plan that contradicts an answered clarification is a P0.** The
`§Clarifications` answers are part of the baseline the reviewer falsifies
against; a plan that re-opens a settled decision, or silently substitutes
its own assumption for the user's answer, is not a wording issue — it is
the plan promising something the user already declined.

## Rules that keep the loop convergent

- **The planner must answer every P0/P1** — fix it, or reject it with a
  written rationale, which you record in the same round as
  `Rejected: <reason>`. A finding silently dropped during revision becomes
  a P0 in the next round.
- **Round 2+ verifies the previous findings and the content changed to
  resolve them only** — never a fresh full audit. Otherwise every round
  harvests new P2s and the plan never converges.
- **Never weaken a plan to satisfy a reviewer.** Deleting a criterion,
  widening a contract to "TBD", or dropping a requirement to reach `PASS`
  is worse than shipping with a documented P1. If the honest fix is a
  choice only the user can make, that is `NEEDS_USER_DECISION`.
- **A finding whose fix narrows a `REQ` is not the planner's to resolve.**
  When the only available fix shrinks what a requirement promises — the
  accepted behavior becomes a subset of what `REQ<n>` says as the user
  wrote it — reporting `NEEDS_USER_DECISION` is required, with the
  requirement quoted and the subset named. Writing the subset down as a
  documented boundary is correct engineering *and* still a scope
  decision; from inside the plan the two look identical, which is why
  this needs its own rule rather than riding on the one above.
- **Oscillation stops the loop.** If a round produces more new findings
  than the previous round resolved, stop, record the residual items as
  known risks in `plan.md`, and report them in Step 5.
- **Re-run the affected mechanical gates after revisions** — `plan_lint`
  after any document edit, the Mermaid gate if a diagram changed, the DAG
  gate if the repositories table changed. At lean tier this mechanical
  re-check runs in the same round as the revision and does not count as
  a review round.
