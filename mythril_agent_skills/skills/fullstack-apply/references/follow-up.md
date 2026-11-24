# Follow-up Edits and Resuming

Round 0 is not necessarily the end. Manual testing, pasted error logs,
code review feedback, QA pushback, edge cases, or new tiny requirements
all produce follow-up edits to the same work item.

When the user gives any feedback / fix / log on the same work item
(before it is archived), run the same loop on the existing work
directory:

1. Read what the fix needs, not everything: `plan.md` (Success Criteria,
   Code Map), `review.md` §Status Overview, the latest `progress.md`
   entry, and the `analysis.md` sections the fix touches. When the user
   points at code instead of at this work directory, confirm the item owns
   that code before touching it: `plan_lint.py --find <path-or-symbol>`
   answers from the Code Map. If some other item owns it — or an archived
   one does — say so and route the change there; never fix code against the
   wrong spec, and never reopen an archived directory.
2. Determine which repos/files are affected. If the reported problem is
   a failure whose cause is not obvious (misleading symptoms, suspected
   cross-repo boundary, no identifiable introducing change), delegate
   to the **debugger** subagent for root-cause analysis first and fold
   its findings into the briefs. Obvious, change-caused failures go
   straight into the wave loop.
3. Pick the loop by the size of the fix, not the size of the item:
   - **One repo, no frozen contract touched** (the common case — a pasted
     log, a manual-test finding, a small tweak) → the **lean loop** of
     `SKILL.md` Step 4: you edit the code yourself, one independent
     code-reviewer pass, at most one confirmation.
   - **Several repos, or a frozen contract changes** → re-run
     `compute_waves.py` on the affected repos and run the wave loop
     (Steps 4a–4e), then the cross-repo review.

   **A follow-up never re-runs the plan review.** The code review of the
   fix is the check. When the user adds a requirement mid-implementation
   (a product rule, a window, a copy change) that stays inside the item's
   repos and contracts, append it as the next `REQ<n>` verbatim in
   `analysis.md` §Original Requirements, add its Success Criterion and
   tasks to `plan.md`, and run the loop above. Only a new goal, a new repo,
   or a changed frozen contract that the user wants planned first goes
   back to `fullstack-propose` — as a `-vN` successor or a separate item,
   never as plan-review round N+1 on this one.
4. Update the documents this round invalidated, in the same pass as the
   code — and only those:

   | What the round changed | What must change |
   |---|---|
   | any code edit | `progress.md` — new dated entry |
   | structure or flow: a responsibility moved between modules or layers, a call order changed, a component appeared or vanished, a frozen contract altered | `analysis.md` — rewrite the affected *Current State / Target Architecture / User Flow / Cross-Repo Impact* section and its diagram. These sections describe structure, so a structural fix makes them false; do not append a correction under a body that still says the opposite |
   | behavior a Success Criterion covers | `plan.md` criterion + its `review.md` Evidence row |
   | scope genuinely changed | `plan.md` Success Criteria, with user awareness |
   | files touched | `plan.md` Code Map — replace planned paths with the paths actually changed |
   | every round | `review.md` — a compact code-review round: scope, findings, verdict, the Evidence rows it changed, the `**仓库技能**` / `**Repo Skills**` line when the repo ships skills, and the `**文档同步**` / `**Document Sync**` line |

   The Document Sync line is one line, not a report: a document the round
   did not touch gets a few words ("未变——仅改实现" / "unchanged —
   implementation only"). Do not rewrite sections that are still true, and
   do not paste the reviewer's full verified / unverified lists into
   `review.md` for a follow-up round — the findings and verdict are the
   record.

5. Re-run the Mermaid gate and four-file consistency check, then
   `plan_lint.py` — it fails the round on a broken chain (a missing Code
   Map row, a criterion with no Evidence row) and warns on a missing
   attestation; fix both.

A small fix gets a small loop, never a skipped one: every code-touching
round gets a progress entry, an independent code review, and the one-line
Document Sync attestation — nothing more.

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
6. If the `Workspace:` line is not in the transcript, re-run
   `check_workspace.py` once and re-announce it.
