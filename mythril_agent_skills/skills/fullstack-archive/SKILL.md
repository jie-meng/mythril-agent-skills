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
  finished and should be moved out of the active listing.
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

## Step 1 — Identify the Work Item

1. **If the user named a work item** (e.g. "archive add-dark-mode"),
   locate it under `<docs-dir>/changes/<type>/<work-name>/`.
2. **If the user said "archive it" without naming it**, list the active
   work items under `changes/{feat,refactor,fix}/` and ask which one.
3. **If the named item is already archived**, report that it's already
   in the archive and stop.

Confirm the type (feat / refactor / fix) — it comes from the parent
directory name.

## Step 2 — Integrity Check (WARN ONLY, non-blocking)

Check the four work-tracking documents exist:

- `analysis.md`, `plan.md`, `progress.md`, `review.md`

Also check `review.md` has at least one `### Verdict` (English) or
`### 结论` (Chinese) section.

**These checks are advisory, not blocking.** Archive proceeds even if a
document is missing or review is incomplete — but you MUST report any
deficiency to the user so they can fix the record or consciously accept
it as-is.

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
- <any integrity warnings from Step 2>
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
- Integrity checks are advisory — report deficiencies, don't block.
- The docs repo is the only repo touched. No code repos are modified.
