---
name: fullstack-archive
description: |
  Archive a completed work item by moving its directory into the archive
  with a date and type prefix. Marks the work item as done: the lifecycle
  state of a work item is its directory location — under changes/type/
  it is active, under changes/archive/YYYY-MM-DD-type-name/ it is
  archived. Trigger: "fullstack archive", "archive it", "归档",
  "做完了", "ship it", "结了", "merged", "已完成", "收尾". Use when the
  user says a feature, fix, or refactor is done, shipped, merged, or
  finished and should be moved out of the active listing. NOT for
  workspace issues — a directory under issues/ is closed by
  fullstack-issue-archive; when the user says only "archive it", list
  active work items and active issues, then ask which one. Refuses to
  archive unfinished work: failing Success Criteria or a NEEDS_FIXES
  review verdict must be resolved, or explicitly overridden and recorded
  in progress.md.
license: Apache-2.0
---

# Fullstack Archive

Move a completed work item out of the active listing and into the
archive. This is the **only** state transition a work item makes —
one directory move, atomic and unambiguous.

## Core Principle — The Move Is the State

A work item's lifecycle state is its directory location:

| Location | State |
|----------|-------|
| `changes/feat\|refactor\|fix/<work-name>/` | Active (in progress) |
| `changes/archive/YYYY-MM-DD-<type>-<work-name>/` | **Archived** (done) |

There is no `Status` field to update. Archiving IS the status change.
After archiving, the work item is closed for good — no further edits.

## Prerequisites — Workspace Validation Gate (MANDATORY SCRIPT CALL)

This skill MUST NOT proceed past this gate. Run `check_workspace.py`
and inspect its output.

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/fullstack-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".claude/skills/fullstack-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".copilot/skills/fullstack-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".cursor/skills/fullstack-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".gemini/skills/fullstack-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".codex/skills/fullstack-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".qwen/skills/fullstack-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".grok/skills/fullstack-archive/scripts/check_workspace.py",
]
script = next((p for p in candidates if p.exists()), None)
if not script:
    print("ERROR: check_workspace.py not found", file=sys.stderr)
    sys.exit(1)
result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
print(result.stdout)
```

- `WORKSPACE_VALID=true` → proceed to Step 1
- `WORKSPACE_VALID=false` → STOP and tell the user the workspace is not
  a valid fullstack workspace (list `MISSING=` items); `cd` to the
  workspace root or run `fullstack-init` first.

Record `DOCS_DIR` for the archive path.

## Step 1 — Route by Target Type, Then Identify the Work Item

There are two archives in a fullstack workspace: work items under
`changes/` and issues under `issues/`. Check the first matching row
BEFORE doing anything else:

| # | Signal | Target | Action |
|---|--------|--------|--------|
| 1 | Path under `<docs-dir>/changes/archive/` | Work item, already archived | Report it is already archived; stop. |
| 2 | Path under `<docs-dir>/changes/{feat,refactor,fix}/` | Work item | Continue with this skill |
| 3 | Path under `<docs-dir>/issues/archive/` | Issue, already closed | Report it is already closed; stop. |
| 4 | Path under `<docs-dir>/issues/` | Issue | STOP — hand off to `fullstack-issue-archive` |
| 5 | Bare name matching exactly one active work item | Work item | Continue; confirm the match with the user |
| 6 | Bare name matching exactly one active issue | Issue | STOP — hand off to `fullstack-issue-archive` |
| 7 | Bare "archive it" / "归档一下" with no name | Ambiguous | List active work items AND active issues, then ask which one; route by the answer |

Rules:

- **Path beats prose.** When the user gave a path, the tree it lives in
  decides the type — never the user's wording. `changes/` → this skill;
  `issues/` → `fullstack-issue-archive`.
- **Context counts.** Work item names, plans, branch names, Progress/
  Review references point at a work item. Issue names, symptoms (现象),
  `log/` evidence, or an `issues/…` back-reference point at an issue.
- **One match or ask.** If a bare name matches more than one candidate,
  list the candidates with their paths and ask — do not guess.
- Never close an issue from this skill, and never archive a work item
  from `fullstack-issue-archive` — say what you found and invoke the
  right skill.

Then identify the work item:

1. **If the user named a work item** (e.g. "archive add-dark-mode"),
   locate it under `<docs-dir>/changes/<type>/<work-name>/`.
2. **If the user said "archive it" without naming it**, list the active
   work items under `changes/{feat,refactor,fix}/` and ask which one.
3. **If the named item is already archived**, report that it's already
   in the archive and stop.

Confirm the type (feat / refactor / fix) — it comes from the parent
directory name.

## Step 2 — Verify Done State and Check Integrity (MANDATORY)

### 2a — Done gate (BLOCKING)

**"Archive it" is not proof that the work is finished.** Read `plan.md`,
`review.md`, and `progress.md` and verify all of the following:

| Check | Done when | Not done when |
|-------|-----------|---------------|
| Success Criteria | every criterion in `plan.md` has an Evidence row in `review.md` marked `✅ Pass` / `✅ 通过`, or is explicitly waived (`⚠️ Skipped` / `⚠️ 跳过`) with a documented reason the user has accepted | any `❌ Fail` / `❌ 未通过`, `待核验` / `Pending`, missing row, or an unaccepted `⚠️ Skipped` / `⚠️ 跳过` |
| Review verdict | the newest code-review verdict (the last `### Verdict` / `### 结论`, or the Status Overview's latest verdict) is `PASS` or `PASS_WITH_RISKS` | `NEEDS_FIXES`, `FAIL`, `BLOCKED`, or `NEEDS_USER_DECISION` |
| Open work | `progress.md` ends in a completed state (merged / shipped / done) | an open blocker, an in-progress tail, or an unresolved decision |

If any row is "not done", **STOP** — report `NOT DONE` with the failing
checks and do not archive. Ask the user to finish the work or to
explicitly confirm an early archive.

**Informed override.** If the user explicitly says to archive anyway
after hearing the failures, append a dated entry to `progress.md` BEFORE
the move, recording the unmet checks and the user's decision (e.g.
`Archived with SC-3 ⚠️ Skipped by user decision`). Then continue. An
archived item must read as unfinished when it is unfinished — the move
must never imply completion.

### 2b — Document integrity (advisory, non-blocking)

Check the four work-tracking documents exist:

- `analysis.md`, `plan.md`, `progress.md`, `review.md`
- `plan.md` carries a `## 代码地图` / `## Code Map` table listing the files
  the item ended up actually owning. Archiving is the last moment that
  table can be corrected: nothing re-lints an archived item, and a stale
  map sends every later `--find` for those files to the wrong place. The
  archive stays in `--find`'s scope, so the map keeps working after the
  move — it is just never fixed again.

Also check `review.md` has at least one `### Verdict` (English) or
`### 结论` (Chinese) section.

Also check the issue back-reference: when `plan.md`'s **Source** /
**来源** points at an issue (an `issues/…` path), that issue directory
must already live under `<docs-dir>/issues/archive/`. If it is still in
the active area (`<docs-dir>/issues/<name>/`), report it and suggest
closing it first via `fullstack-issue-archive` — an archived work item
pointing at an active issue is a dangling reference — but archive
proceeds regardless.

**These integrity checks are advisory, not blocking.** Report any
deficiency to the user so they can fix the record or consciously accept
it. Completion is decided by the 2a done gate, not by document count.

## Step 3 — Optional Changelog Entry

If `<docs-dir>/` contains a changelog directory (e.g.
`robocontrol-changelog/`, `changelog/`), append an entry following that
directory's existing naming convention. Otherwise skip this step.

If a changelog entry is written, it is committed with the docs repo in
Step 5.

## Step 4 — Compute the Archive Target

Archive directory name:

```text
YYYY-MM-DD-<type>-<work-name>
```

Rules:

- **`<type>`**: from the source parent directory — `feat`, `fix`, or
  `refactor`.
- **`<date>`**: **today** (the archive day). This differs from
  `fullstack-docs-migration`, which uses the last-active day to
  preserve historical timestamps.
- **Idempotence**: if the source work-name already starts with
  `YYYY-MM-DD-` (a migration leftover), do NOT stack a second date —
  keep the existing date and add only the type prefix.
- **Collision**: if `<docs-dir>/changes/archive/YYYY-MM-DD-<type>-<work-name>/`
  already exists, **FAIL HARD** — do not overwrite. Report the collision
  and ask the user how to proceed.

## Step 5 — Archive

```bash
mkdir -p <docs-dir>/changes/archive
mv <docs-dir>/changes/<type>/<work-name> <docs-dir>/changes/archive/YYYY-MM-DD-<type>-<work-name>
```

Then commit the docs repo (including any changelog entry from Step 3):

```bash
cd <docs-dir>
git add changes/archive/YYYY-MM-DD-<type>-<work-name>
git commit -m "docs: archive <work-name>"
```

## Step 6 — Report

Output a summary:

```
Archived: <work-name> (<type>)
From: <docs-dir>/changes/<type>/<work-name>/
To:   <docs-dir>/changes/archive/YYYY-MM-DD-<type>-<work-name>/
Date: <YYYY-MM-DD>

Contents:
- analysis.md   ✓ / missing
- plan.md       ✓ / missing
- progress.md   ✓ / missing
- review.md     ✓ / missing  (verdict: present / missing)

Notes:
- <done-gate failures + any integrity warnings from Step 2>
- <informed override recorded in progress.md: yes/no>
- <changelog entry written: yes/no>
```

## After Archiving

- **No further edits** to the archived directory. Future work on the
  same scope is a NEW work item.
- If the user later wants to continue the archived work, suggest
  `fullstack-propose` to create a successor (`<work-name>-vN`), which
  will reference the archived predecessor under `**Predecessor**:`.

## Requirements

- Python 3.10+
- Workspace initialized by `fullstack-init` (must pass workspace
  validation gate)
- A work item under `changes/{feat,refactor,fix}/` that the user
  confirms is done

## Guardrails

- Archive is a move, not a copy. The work item leaves the active
  listing.
- Never overwrite an existing archive directory — fail hard on collision.
- Never reopen an archived directory. Successors are new work items.
- The 2a done gate is blocking: never archive an item with failing
  Success Criteria or a `NEEDS_FIXES` / `FAIL` review verdict. An
  informed override must be recorded in `progress.md` before the move.
- Document integrity checks are advisory — report deficiencies, don't
  block.
- The docs repo is the only repo touched. No code repos are modified.
