# Iteration Mode — Post-Implementation Sticky Loop

After Step 9 marks a work item as `Done`/`已完成`, real life rarely
ends there. Manual testing, pasted error logs, code review feedback,
QA pushback, edge cases, or new tiny requirements all produce
follow-up edits to the **same** work item — same scope, same work
item, PR not yet merged. Those edits MUST stay inside the same
discipline as the initial implementation: same staged review, same
four-document sync, same audit trail.

This document defines that discipline as a sticky, autonomous loop.

> **Pre-flight:** before reading further, you must have already
> announced `Mode: Iteration` per the SKILL.md Step 1d-ii contract,
> AND `route_check.py` must have returned `ROUTE=Iteration`. If you
> are reading this doc out of order or to "decide if it applies",
> stop and re-run Step 1d.

> **Iteration vs. Follow-up vs. Reference** — these three modes look
> similar at a glance but apply to different lifecycle stages. See
> [`mode-selection.md`](mode-selection.md) for the routing table.
> In one sentence: Iteration is for an open work item *before*
> closure; Follow-up is for *after* closure (PR merged, shipped);
> Reference is for *reading* prior work without writing into it.

## When Iteration Mode is active

Iteration Mode is **active** for a given work directory whenever ALL
of these hold:

1. The work directory `<docs-dir>/<type>/<work-name>/` exists with the
   four files in place.
2. `plan.md` `Status` is `Done`/`已完成`, OR at least one repo has been
   committed under the work item's feature branch (real code shipped
   to a branch, even if not merged).
3. The user is making a change request that touches the same scope —
   even a one-line tweak, even when the user does not say "fullstack
   impl" again.

If the request is **clearly a brand-new unrelated work item**
(different feature, different repos), do NOT route it into the active
work directory — start a fresh `fullstack-impl` flow instead. If
ambiguous, ask the user.

## Detection cues — handled by `route_check.py`

The agent does NOT make Iteration vs Reference vs Followup decisions
from prose anymore. `route_check.py` (called in SKILL.md Step 1d)
detects all of these signals deterministically and reports
`ROUTE=Iteration`:

| Signal | Examples |
|--------|----------|
| Bug report on shipped code | "this is wrong", "doesn't work", "这里不对", "调一下", "再改一下" |
| Pasted error / log / stack trace | "got this error: ...", "log says ...", "报错：..." |
| Manual test feedback | "I clicked X and Y didn't happen", "tested on iOS, broken" |
| Reviewer comment | "PR comment says ...", "reviewer asked to ..." |
| Small follow-up requirement | "also add ...", "顺便加一下 ..." |
| Direct code edit request on touched files | "change this function", "把这个改成 ..." |
| Compound read+modify | "看一下 feat/X 我想改一下" — modify wins |

If you find yourself in this doc but the script said `ROUTE=Reference`
or `ROUTE=Followup` or `ROUTE=AskUser`, you are reading the wrong
mode doc — go back to Step 1d.

## Branch source — MANDATORY decision before any code edit

The single most common Iteration Mode failure is **editing on the
default branch directly** because the work item's feature branch was
already merged. Before touching any code, decide which branch each
affected repo should be on.

### Decision matrix (run per repo)

For each repo affected by this iteration:

```bash
cd <repo-dir>
git fetch
git branch --list "<work-item-branch>"            # local exists?
git branch -r --list "origin/<work-item-branch>"  # remote exists?
git log <default-branch>..<work-item-branch> 2>/dev/null  # commits ahead of default?
git log <work-item-branch>..<default-branch> 2>/dev/null  # commits behind default?
```

Then apply this table:

| State | What it means | What to do |
|-------|---------------|-----------|
| Feature branch exists locally AND has commits not in default | The original branch is alive, PR not merged | `git checkout <feature-branch>`, work directly on it |
| Feature branch exists ONLY on remote | Local was deleted but remote is alive | `git checkout -b <feature-branch> origin/<feature-branch>` |
| Feature branch was merged (commits exist in default branch but feature branch is fast-forwardable / equal to default) | Original work shipped to default, PR closed | Create a NEW branch `<type>/<work-name>-iter-N` off the **default branch**; iteration commits go there |
| Feature branch deleted AND commits are in default | Same as above (most common after squash-merge) | Same — create `<type>/<work-name>-iter-N` |
| Feature branch deleted AND commits NOT in default (work was abandoned) | Anomaly — never happens normally | Stop and ASK the user how to proceed |
| You don't know which state applies | Anomaly | Stop and ASK the user |

`<work-item-branch>` is the branch name recorded in `plan.md`'s
`**Branch**` field. The `-iter-N` suffix is sequential per work item
(`-iter-1`, `-iter-2`, ...) — N matches the iteration number that
will be appended to `progress.md`'s Iteration Log this round.

### Forbidden — committing iteration changes directly to default

NEVER commit iteration changes to `main` / `master` / `dev`. Even
when the original feature branch was already merged, the iteration
must live on its own branch so the resulting PR can be reviewed and
merged independently. Direct-to-default commits:

1. Bypass code review (no PR exists for staged review's recommended
   commit message to attach to).
2. Pollute the default branch with un-reviewed changes.
3. Make rollback per-iteration impossible.

If the default branch is the only branch the agent finds itself on at
the start of an iteration round, that is a routing failure — go back
to Step 1d, the work item likely needs a new `-iter-N` branch.

### Update `plan.md`'s Branch field per round

When a new `-iter-N` branch is created, append it to `plan.md`'s
`**Branch**` field as a comma-separated list, e.g.
`feat/Dark-Mode-Toggle, feat/Dark-Mode-Toggle-iter-1`. This keeps the
audit trail intact: future readers can see all branches that ever
held code for this work item.

> **Followup vs Iteration branch suffix:** `-iter-N` is for
> Iteration Mode (open work item, same `<work-name>/` directory).
> `-vN` is for Follow-up Mode (closed predecessor, new
> `<work-name>-vN/` directory). Do NOT mix the two suffixes — see
> [`followup-mode.md`](followup-mode.md).

## The Iteration Loop (run for EVERY follow-up edit)

```
User feedback / log / bug report
        │
        ▼
1. Identify scope ──► which repo(s) and which work directory?
        │
        ▼
2. Branch source decision (run the matrix above per repo)
        │
        ▼
3. For each affected repo:
        │
        ├─► 3a. Edit code (smallest fix that addresses the feedback)
        │
        ├─► 3b. Validate (lint / type / test / build per repo conventions)
        │
        ├─► 3c. git add .   (stage the candidate commit)
        │
        ├─► 3d. Invoke `code-review-staged`
        │            │
        │            ├─► PASS         → continue
        │            └─► NEEDS_FIXES  → fix → re-stage → re-review
        │                              (max 3 rounds)
        │
        └─► 3e. Append review round to review.md
                (use the per-round template in review-formats.md)
        │
        ▼
4. Sync the four documents (see "Per-iteration doc sync" below)
        │
        ▼
5. Run `iteration_log_check.py` — round is NOT complete until PASS
        │
        ▼
6. NOW commit each repo (use the recommended commit message from 3d)
        │
        ▼
7. If the iteration touched MULTIPLE repos → re-run cross-repo
   consistency review (Step 7 of SKILL.md), append to review.md
        │
        ▼
8. Commit the docs repo with the four updated files
        │
        ▼
9. Report concise summary to the user (what changed, review verdict,
   updated docs, any residual issues)
```

The order above is intentional: **doc sync happens BEFORE code commit**
(steps 4-6 precede step 6). This makes it physically impossible to
"forget" the doc updates after committing — if the docs aren't synced,
there is no commit yet to forget about.

## Per-iteration doc sync (MANDATORY pre-commit checklist)

Run this checklist BETWEEN finishing the staged review (step 3e) and
committing the code change (step 6). It is a hard gate — do NOT skip
even for "trivial" fixes, and do NOT defer it to "after the commit".

```
For each iteration that produced a code change:

  [ ] review.md   — appended this round's `code-review-staged` output
                    + Verdict (PASS / NEEDS_FIXES → resolved)
  [ ] progress.md — Iteration Log row added (date, trigger, repos,
                    files, review verdict, commit SHA — use a
                    placeholder like `<pending>` if not yet committed,
                    update to the real SHA right after `git commit`)
  [ ] plan.md     — if scope changed: tasks added/removed; if branch
                    list changed (new `-iter-N` branch), update the
                    Branch field; if neither: explicitly note
                    "no plan change" in the iteration log row
  [ ] analysis.md — if root cause, chosen approach, architecture, or
                    risk profile changed: update the relevant section
                    and add an "Updated" date stamp; if not, explicitly
                    note "no analysis change" in the iteration log row

  [ ] Mermaid Gate — if any tracked .md file with ```mermaid blocks
                    was edited, run `mermaid_validate.py`; the round
                    is NOT complete until STATUS=PASS. See
                    document-templates.md for the gate details.

  [ ] Self-check — run `iteration_log_check.py` against the work
                    directory; the round is NOT complete until
                    STATUS=PASS. Catches missing rows, blank columns,
                    non-sequential numbers. See "Self-check" below.

After ALL boxes are checked AND both gates pass, THEN:
  [ ] git commit each affected repo (with the recommended commit message)
  [ ] Update the placeholder commit SHA in progress.md to the real SHA
  [ ] git commit the docs repo with all four updated files
       (message: "<work-name>: iteration N — <one-line summary>")
```

The "explicitly note no change" requirement exists to prove the agent
**considered** each upstream document, not just skipped it. A silent
omission is indistinguishable from forgetting.

The "doc sync before commit" requirement closes the original failure
mode where post-commit doc updates were "easy to skip" because the
agent already considered the work done. With the order reversed, you
literally cannot finish the round without the docs.

## Iteration Log — appended to progress.md per round

Every iteration round appends ONE row to the **Iteration Log** table
in `progress.md`. Schema:

| Field | Content |
|-------|---------|
| `#` | Sequential iteration number (1, 2, 3, ...) starting AFTER initial finalization |
| `Date` | ISO date of the iteration |
| `Trigger` | One-line summary of the user's feedback (e.g. "iOS settings screen crashes on toggle") |
| `Repos` | Affected repo(s) for this round |
| `Files` | Key files changed (≤ 5; if more, write "N files in <area>") |
| `Review` | `PASS (round N)` / `RESIDUAL: <count>` |
| `analysis.md` | `unchanged` / `updated: <section>` |
| `plan.md` | `unchanged` / `updated: <section>` |
| `Commit` | Commit SHA(s) per repo (short form, e.g. `api@a1b2c3d`) |

## Stopping conditions for an iteration

ONE iteration round ends when ALL of (in this order):

1. `review.md` updated with this round's output and verdict.
2. `progress.md` Iteration Log row appended.
3. `analysis.md` and `plan.md` either updated or explicitly noted as
   unchanged for this round.
4. **`iteration_log_check.py` returns `STATUS=PASS`** — see
   "Self-check" below.
5. Code change committed in each affected repo (with the recommended
   commit message from `code-review-staged`).
6. Iteration Log row's commit SHA placeholder updated to the real SHA.
7. Docs repo commit created.

If the user gives more feedback → start round N+1. The loop continues
indefinitely until the user explicitly closes the work item.

## Self-check — `iteration_log_check.py` after each round

Before declaring the round done, run the bundled validator against
the work directory. It catches the most common "the agent forgot to
maintain the audit trail" failures: missing columns, non-sequential
iteration numbers, more iterations than review rounds, free-form text
where `unchanged`/`updated: ...` is required.

**How to locate and invoke the script:** check candidate paths in
this order, use the first that exists:

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/fullstack-impl/scripts/iteration_log_check.py",
    pathlib.Path.home() / ".claude/skills/fullstack-impl/scripts/iteration_log_check.py",
    pathlib.Path.home() / ".copilot/skills/fullstack-impl/scripts/iteration_log_check.py",
    pathlib.Path.home() / ".cursor/skills/fullstack-impl/scripts/iteration_log_check.py",
    pathlib.Path.home() / ".gemini/skills/fullstack-impl/scripts/iteration_log_check.py",
    pathlib.Path.home() / ".codex/skills/fullstack-impl/scripts/iteration_log_check.py",
    pathlib.Path.home() / ".qwen/skills/fullstack-impl/scripts/iteration_log_check.py",
    pathlib.Path.home() / ".grok/skills/fullstack-impl/scripts/iteration_log_check.py",
]
script = next((p for p in candidates if p.exists()), None)
if script:
    result = subprocess.run(
        [sys.executable, str(script), "<docs-dir>/<type>/<work-name>"],
        capture_output=True, text=True,
    )
    print(result.stdout)
```

**Decision logic from the script's output:**

| Output line | Action |
|-------------|--------|
| `STATUS=PASS` | Round complete; report summary to user |
| `STATUS=WARN` | Round complete BUT report each `WARNING:` line to the user so they know what to tighten next time |
| `STATUS=FAIL` | Round NOT complete; fix every `ERROR:` line (usually means: append the missing Iteration Log row, fill empty columns, append the missing review round, or renumber rows), then re-run the script until it passes |

If the script is not found at any of the candidate paths, fall back
to manual checking against the per-iteration doc sync checklist
above. Skipping the self-check entirely is not an acceptable shortcut.

## Anti-patterns to refuse

| Anti-pattern | Why it's wrong | Correct behavior |
|--------------|---------------|------------------|
| Commit iteration changes directly to `main`/`master`/`dev` | Iteration commits MUST live on a reviewable branch | Use the Branch source decision matrix above; create `<work-name>-iter-N` if needed |
| Edit code → commit directly without `code-review-staged` | Bypasses the audit loop; prior commits had reviews, this one doesn't → inconsistent history | Always stage → review → commit, even for one-line fixes |
| Commit code first, then update docs "later" | "Later" = forgotten; the original failure pattern this skill exists to prevent | Doc sync runs BEFORE `git commit` (steps 4-5 precede step 6 in the loop above) |
| Update `review.md` only, leave `progress.md` Iteration Log empty | Loses the per-iteration audit trail | Every code-touching round MUST add a log row before committing |
| Update `progress.md` but leave `analysis.md` stale after a root-cause discovery | Future readers see plan/progress that no longer matches the analysis | Update `analysis.md` and add an "Updated" date when the underlying technical understanding shifts |
| Treat the "second turn" as casual chat and skip the loop | Sticky loop is the whole point; "small fixes" are where regressions hide | Run the full loop; the loop is cheap when the change is small |
| Switch to a different work item silently when the user pastes an unrelated bug | Mixes audit trails | Recognize the scope mismatch, ask the user, and start a separate work item |
| Skip Mode announcement because "the user didn't say `fullstack impl`" | The `Mode:` line is contractual — without it, the agent can claim afterwards it was "just chatting" and skip the loop | Always announce `Mode: Iteration` at the start of the round per SKILL.md Step 1d-ii |

## Closing the work item

The work item is **closed** only when the user explicitly signals it
(merged PR, "done", "ship it", "结了"). On closure:

1. `plan.md` `Status` → `Closed` / `已关闭`
2. `progress.md` `Overall status` → `Closed` / `已关闭`, append final
   Iteration Log row marking closure
3. Docs repo commit: `<work-name>: closed — N iteration rounds`

After closure, any new request on the same scope does NOT reopen this
work item. Instead, it creates a NEW work item that explicitly inherits
context from the closed predecessor — see [`followup-mode.md`](followup-mode.md).
