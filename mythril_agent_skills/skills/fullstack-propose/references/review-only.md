# Review-only re-entry — re-run the Plan Review Gate

When the user points at an existing plan and asks for it to be
**reviewed** rather than replanned ("审一下这个方案", "review the plan
for X", "re-review the plan", "方案靠谱吗", "is this plan ready?"), do
NOT re-run Steps 1–4 — the plan already exists. Run the gate alone:

1. **Locate the work item** — `<docs-dir>/changes/<type>/<name>/`. Search
   the active type directories; if several match, ask. If `plan.md` is
   missing, this is not a re-review — tell the user to plan it first.
2. **Determine the round** — read `review.md`, take the highest existing
   `## Plan Review — Round <N>` / `## 方案审查 — 第 <N> 轮`; the new round is N+1. If there are no
   rounds yet, this is a first review (round 1) — fine, proceed.
3. **Recover the requirements source** — read `**Source**` in `plan.md`
   and fetch it (`jira`, `confluence`, `gh-operations`, or the referenced
   work item). If the original requirements cannot be recovered — only a
   paraphrase survived — ask the user for them. A coverage check without
   the requirements is theater.
4. **Collect what changed since the last round** — the docs repo is a
   git repo:

   ```bash
   cd <docs-dir>
   git log --oneline -- changes/<type>/<name>/
   git log -p --since=<last round date> -- changes/<type>/<name>/
   ```

   Hand the plan-reviewer the changed sections, not "please re-read
   everything" — round discipline (see Step 4.5) is what keeps repeats
   convergent.
5. **Delegate to plan-reviewer** with the round number, the documents as
   written to disk, the requirements source, and the diff — the same
   inputs Step 4.5 specifies.
6. **Handle the verdict** exactly as Step 4.5 does: `PASS` /
   `PASS_WITH_RISKS` → report with the Step 5 template; `NEEDS_FIXES` →
   the planner revises the affected sections only, then round N+2;
   `NEEDS_USER_DECISION` → ask the user. Re-run the Mermaid gate if a
   diagram changed and the DAG gate if the repositories table changed.
7. **Commit the docs repo** (the review rounds are part of the record)
   and report using the Step 5 template. Run `plan_lint.py` first — the
   consistency gate applies to a re-review exactly as it does to Step 4.5.

Boundaries for this path: it reviews and revises only. It never re-plans
the item from scratch, never creates branches, and never touches project
code. If the review shows the plan is wrong at the **requirements** level
rather than merely incomplete, stop — that is a new planning round; say so
and run the normal steps.
