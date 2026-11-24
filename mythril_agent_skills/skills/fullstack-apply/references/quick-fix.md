# Quick Fix — a small bug fix with no work item

Most bugs do not need a plan. When the root cause is already known and the
fix is small, writing four documents and running a plan review costs more
than the fix itself and catches nothing the code review would not. The
quick-fix path goes straight from the known cause to a reviewed commit.

## When it applies — all must hold

1. **The root cause is established** — in this session, with evidence
   (log lines, a code path, a failing test, data), or it is obvious from
   the error itself. A symptom with a guessed cause is not established:
   find the cause first (the **debugger** subagent, or inline), then come
   back here.
2. **One repo.**
3. **No contract change** — no cross-repo interface, persisted data /
   schema / migration, or API consumed outside the repo changes shape.
   Changing behavior *behind* an existing interface is fine.
4. **Small** — a reviewer can read the diff in one sitting. As a guide:
   at most ~5 production files and ~150 changed production lines; tests
   do not count.
5. **No owner** — the code is not owned by an active work item. Check with
   `python3 SKILL_PATH/scripts/plan_lint.py --find <path-or-symbol>
   <docs-dir>` for each file you expect to touch; only a `CODEMAP:` line
   under an active `changes/<type>/` directory is an owner. An active owner
   → run that item's follow-up loop (`references/follow-up.md`) instead. An
   archived owner (`changes/archive/…`) does not block a quick fix.

Any condition fails → this is a work item: send the user to
`fullstack-propose`. An explicit user request either way wins ("就直接修",
"开个工作项").

## The fix is the smallest one that removes the symptom

Fix what was reported. Generalized hardening — "while we are here, also
guard every other caller", a new framework-level fallback, a refactor —
is not part of a quick fix even if it would prevent a related bug. Name
it in the report as a possible follow-up and let the user decide; if they
want it, it is its own quick fix or work item.

A product-rule change the user decides mid-fix (a time window, a limit, a
copy change) is a separate quick fix with its own commit when it still
meets the conditions above — never folded silently into the first one.

## Steps

1. **Confirm once.** Skip this when the user already approved this exact
   fix ("按你的推荐修", "fix it that way"). Otherwise, one message:

   ```
   Quick fix (no work item):
     Repo:    robo-server/    Branch: fix/Voice-Message-Empty-Playback
     Cause:   <one line, with the evidence anchor>
     Fix:     <one or two lines — the smallest change>
     Not included: <hardening you are deliberately leaving out, or "—">
     Verify:  <regression test + how the symptom is re-checked>
   ```

2. **Branch** — Step 3 naming (`fix/<Title-Hyphenated>`).
3. **Implement** — the implementer checklist (Step 4) and the Code Comment
   Policy. Add a regression test that fails without the fix whenever the
   repo has tests.
4. **Independent review** — one fresh **code-reviewer** pass, mode
   per-repo. Brief: the symptom, the root-cause evidence, the fix in one
   paragraph, the test result, and the acceptance line "the reported
   symptom no longer occurs, nothing else changes behavior". It runs
   `git diff --cached` itself. `NEEDS_FIXES` → the lean-loop rule in
   `SKILL.md` Step 4 (mechanically proven P1 fixes need no new round; a P0
   or unproven fix gets one confirmation). Findings outside the fix's
   scope are reported to the user, not fixed.
5. **Commit** — the repo's convention. The commit body is the record:
   symptom, root cause (with the evidence anchor), what changed, how it
   was verified.
6. **Ship** — `github_repos=true` → `references/pr-creation.md`. Deploy
   only when the user asks and a repo skill defines how.
7. **Issue** — if an active issue under `<docs-dir>/issues/` describes
   this bug, close it with `fullstack-issue-archive` as `resolved`,
   citing the commit.

No work directory, no `plan_lint`, no plan review. If a document trail is
wanted later, the commit message is it.

## Escalate mid-fix

Stop and tell the user in one line when, while fixing, any condition above
stops holding — a second repo, a contract change, the diff outgrowing
"small", or a cause that turns out to be different. Offer a work item via
`fullstack-propose`; code already written stays uncommitted on the branch
for the planner to reuse.

## Report

```
Quick fix: <one sentence, plain words>
Repo: <repo>   Branch: <branch>   Commit: <sha>
Cause: <one line>
Verified: <tests: passed | …> — review: <PASS | PASS_WITH_RISKS>
Not included: <possible follow-ups, or "—">
```
