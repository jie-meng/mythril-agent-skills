# Iteration Mode — Post-Implementation Sticky Loop

After Step 9 marks a work item as `Done`/`已完成`, real life rarely
ends there. Manual testing, pasted error logs, code review feedback,
QA pushback, edge cases, or new tiny requirements all produce
follow-up edits to the **same** work item — same scope, same branch,
PR not yet merged. Those edits MUST stay inside the same discipline as
the initial implementation: same staged review, same four-document
sync, same audit trail.

This document defines that discipline as a sticky, autonomous loop.

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

## Detection cues — enter Iteration Mode automatically

The agent enters Iteration Mode silently (no announcement needed)
when any of these signals appear in an active workspace with a
finalized or in-progress work item:

| Signal | Examples |
|--------|----------|
| Bug report on shipped code | "this is wrong", "doesn't work", "这里不对", "调一下", "再改一下" |
| Pasted error / log / stack trace | "got this error: ...", "log says ...", "报错：..." |
| Manual test feedback | "I clicked X and Y didn't happen", "tested on iOS, broken" |
| Reviewer comment | "PR comment says ...", "reviewer asked to ..." |
| Small follow-up requirement | "also add ...", "顺便加一下 ..." |
| Direct code edit request on touched files | "change this function", "把这个改成 ..." |

## The Iteration Loop (run for EVERY follow-up edit)

```
User feedback / log / bug report
        │
        ▼
1. Identify scope ──► which repo(s) and which work directory?
        │
        ▼
2. For each affected repo:
        │
        ├─► 2a. Edit code (smallest fix that addresses the feedback)
        │
        ├─► 2b. Validate (lint / type / test / build per repo conventions)
        │
        ├─► 2c. git add .   (stage the candidate commit)
        │
        ├─► 2d. Invoke `code-review-staged`
        │            │
        │            ├─► PASS         → continue
        │            └─► NEEDS_FIXES  → fix → re-stage → re-review
        │                              (max 3 rounds)
        │
        ├─► 2e. Append review round to review.md
        │       (use the per-round template in review-formats.md)
        │
        └─► 2f. git commit (use recommended commit message)
        │
        ▼
3. Sync the four documents (see "Per-iteration doc sync" below)
        │
        ▼
4. If the iteration touched MULTIPLE repos → re-run cross-repo
   consistency review (Step 7), append to review.md
        │
        ▼
5. Append a row to progress.md → Iteration Log
        │
        ▼
6. Report concise summary to the user (what changed, review verdict,
   updated docs, any residual issues)
```

## Per-iteration doc sync (MANDATORY checklist)

After each iteration round, BEFORE finishing the turn, run this
checklist. It is a hard gate — do NOT skip even for "trivial" fixes.

```
For each iteration that produced a code change:

  [ ] review.md   — appended this round's `code-review-staged` output
                    + Verdict (PASS / NEEDS_FIXES → resolved)
  [ ] progress.md — Iteration Log row added (date, trigger, repos,
                    files, review verdict, commit SHA)
  [ ] plan.md     — if scope changed: tasks added/removed; if not,
                    explicitly note "no plan change" in the iteration
                    log row
  [ ] analysis.md — if root cause, chosen approach, architecture, or
                    risk profile changed: update the relevant section
                    and add an "Updated" date stamp; if not, explicitly
                    note "no analysis change" in the iteration log row

  [ ] Mermaid Gate — if any tracked .md file with ```mermaid blocks
                    was edited, run `mermaid_validate.py`; the round
                    is NOT complete until STATUS=PASS. See
                    document-templates.md for the gate details.

  [ ] Commit the docs repo with all four files in a single commit
      (message: "<work-name>: iteration N — <one-line summary>")
```

The "explicitly note no change" requirement exists to prove the agent
**considered** each upstream document, not just skipped it. A silent
omission is indistinguishable from forgetting.

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

ONE iteration round ends when ALL of:

1. Code change committed in each affected repo.
2. `review.md` updated with this round's output and verdict.
3. `progress.md` Iteration Log row appended.
4. `analysis.md` and `plan.md` either updated or explicitly noted as
   unchanged for this round.
5. Docs repo commit created.
6. **Automated structural check passes** — see "Self-check" below.

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
| Edit code → commit directly without `code-review-staged` | Bypasses the audit loop; prior commits had reviews, this one doesn't → inconsistent history | Always stage → review → commit, even for one-line fixes |
| Update `review.md` only, leave `progress.md` Iteration Log empty | Loses the per-iteration audit trail | Every code-touching round MUST add a log row |
| Update `progress.md` but leave `analysis.md` stale after a root-cause discovery | Future readers see plan/progress that no longer matches the analysis | Update `analysis.md` and add an "Updated" date when the underlying technical understanding shifts |
| Treat the "second turn" as casual chat and skip the loop | Sticky loop is the whole point; "small fixes" are where regressions hide | Run the full loop; the loop is cheap when the change is small |
| Switch to a different work item silently when the user pastes an unrelated bug | Mixes audit trails | Recognize the scope mismatch, ask the user, and start a separate work item |

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
