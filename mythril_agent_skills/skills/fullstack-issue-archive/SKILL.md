---
name: fullstack-issue-archive
description: |
  Close a workspace issue by moving its directory into `issues/archive/` —
  the directory location is the issue's state, exactly like work items.
  Four close modes: `proposed` (became a work item), `resolved` (fixed
  directly, no work item needed), `wontfix`, `merged`. Trigger:
  "archive issue", "close issue", "归档 issue", "关闭 issue",
  "issue 归档", "把 issue 关掉", "问题修好了，归档 issue",
  "close the issue", "issue 处理完了", or any path under the docs
  repo's `issues/` directory. NOT for work items — a directory under
  `changes/{feat,refactor,fix}/` belongs to `fullstack-archive`;
  GitHub / GitLab / Jira issues belong to `gh-operations` or `jira`.
  When the user says only "archive it", list active work items and
  active issues, then ask which one before acting. Closing must be
  evidence-backed: an unresolved issue stays active or is closed as
  `wontfix`, never relabelled `resolved`.
license: Apache-2.0
---

# Fullstack Issue Archive

Close a workspace issue: move it out of the active `issues/` listing and
into `issues/archive/`. Closing is an issue's **only** state transition —
deliberately isomorphic to the work item lifecycle (`fullstack-archive`):

| Location | State |
|----------|-------|
| `issues/YYYY-MM-DD-<name>/` | Active (recorded, awaiting triage) |
| `issues/archive/YYYY-MM-DD-<name>/` | **Closed** (proposed / resolved / wontfix / merged) |

The directory name does not change on close — an issue carries its
record date from birth. There is no `Status` field; the move IS the
close, and nothing under `issues/` is ever deleted.

This is the closing half of the issue lifecycle. Recording and updating
an active issue belongs to `fullstack-issue-create`.

## Prerequisites — Workspace Validation Gate (MANDATORY SCRIPT CALL)

This skill MUST NOT proceed past this gate. Run `check_workspace.py`
and inspect its output.

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/fullstack-issue-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".claude/skills/fullstack-issue-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".copilot/skills/fullstack-issue-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".cursor/skills/fullstack-issue-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".gemini/skills/fullstack-issue-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".codex/skills/fullstack-issue-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".qwen/skills/fullstack-issue-archive/scripts/check_workspace.py",
    pathlib.Path.home() / ".grok/skills/fullstack-issue-archive/scripts/check_workspace.py",
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

Record `DOCS_DIR` from the output — every issue path below is relative
to it.

## Step 1 — Route by Target Type (auto-detection)

There are two archives in a fullstack workspace: work items under
`changes/` and issues under `issues/`. Use the user's words, any path
they gave, and the workspace contents to decide — the first matching
row wins:

| # | Signal | Target | Action |
|---|--------|--------|--------|
| 1 | Path under `<docs-dir>/issues/archive/` | Issue, already closed | Report it is already closed; stop. Never move or edit it. |
| 2 | Path under `<docs-dir>/issues/` | Issue | Continue with this skill |
| 3 | Path under `<docs-dir>/changes/archive/` | Work item, already archived | Report it is already archived; stop. |
| 4 | Path under `<docs-dir>/changes/{feat,refactor,fix}/` | Work item | STOP — hand off to `fullstack-archive` |
| 5 | Bare name matching exactly one active issue | Issue | Continue; confirm the match with the user |
| 6 | Bare name matching exactly one active work item | Work item | STOP — hand off to `fullstack-archive` |
| 7 | Bare "archive it" / "关了它" with no name | Ambiguous | List active issues AND active work items, then ask which one; route by the answer |

Rules:

- **Path beats prose.** When the user gave a path, the tree it lives in
  decides the type — never the user's wording. `issues/` → this skill;
  `changes/` → `fullstack-archive`.
- **Context counts.** An issue discussed in this session, `log/`
  evidence, a symptom (现象), or an `issues/…` back-reference points at
  an issue. Work item names, plans, Progress/Review references point at
  a work item.
- **One match or ask.** If a bare name matches more than one candidate,
  list the candidates with their paths and ask — do not guess.
- Never archive a work item from this skill, and never close an issue
  from `fullstack-archive` — say what you found and invoke the right
  skill.

## Step 2 — Identify the Issue

1. Locate the issue directory `<docs-dir>/issues/YYYY-MM-DD-<name>/`.
   The user may pass a full path, a docs-dir-relative path, or a bare
   name.
2. **Already archived?** If it already lives under `issues/archive/`,
   report that and stop — a closed issue is read-only forever.
3. **Not found?** List the active issues under `<docs-dir>/issues/` and
   ask. Do not fuzzy-match; never close an issue the user did not mean.

## Step 3 — Determine the Close Mode

| Mode | Meaning | Required to close | 闭环 pointer |
|------|---------|-------------------|--------------|
| `proposed` | Became a work item — the main path | the work item directory exists and its plan covers this issue | the `changes/<type>/<name>/` directory `fullstack-propose` created |
| `resolved` | Fixed directly, no work item needed | a concrete fix pointer AND verification that the symptom is gone | the commit / PR / change that resolved it |
| `wontfix` | Reviewed, deliberately not pursued | an explicit user decision plus the reason | one line saying why |
| `merged` | Folded into another issue or work item | the absorbing target exists | the absorbing issue / work item path |

A mode is a claim about what happened. Never pick a mode to make the
close easy — an unresolved issue cannot be closed as `resolved`.

Infer from context, confirm when unsure — explicit user intent wins over
the issue record:

- The user says the problem is fixed ("I fixed it", "just patched it",
  "改完了") → `resolved`. Record a concrete pointer — look up the commit
  in the repo named by the issue's **涉及** field
  (`git -C <repo> log --oneline -5`) rather than writing "fixed".
  No work item is created for a directly-fixed issue; the 闭环 pointer
  to the commit is the record.
- The user decided not to pursue it → `wontfix`, with the reason.
- The user says another issue or work item absorbed it → `merged`,
  pointing at the absorbing path.
- No explicit user statement: the issue's `## 关联` points at a work
  item that exists (active or archived) → `proposed`.
- Cannot infer → ask; never guess a mode. `resolved` requires a pointer:
  when the fix is not committed anywhere yet, say so and offer to close
  after the commit lands. A commit alone is not proof the symptom is
  gone — Step 4a still requires verification.

## Step 4 — Verify Closure and Integrity (MANDATORY, BLOCKING)

### 4a — Closure verification gate

**"Archive it" is not proof that the problem is solved.** Before moving
anything, establish what proves the issue is genuinely settled. If the
evidence is not already in this session, ASK the user:

> 这个问题确认解决了吗？依据是什么（提交 / PR / 测试结果 / 设备验证）？
> If it is not solved, should it stay active, or be closed as `wontfix`?

Mode-specific gate — every required item must hold before the move:

| Mode | Must have |
|------|-----------|
| `proposed` | The work item directory exists under `changes/<type>/<name>/` and its plan covers this issue. The problem is tracked, not necessarily fixed — say so in the report. |
| `resolved` | A concrete fix pointer (commit hash / PR / change) AND verification that the symptom is gone — a test result, a device check, or an explicit user confirmation after the user was told what is unverified. |
| `wontfix` | An explicit decision from the user not to pursue it, plus the reason. Not the fallback for "we didn't get to it". |
| `merged` | The absorbing issue or work item exists and is named as the continuation. |

**Hard stops — do NOT move the issue, and tell the user exactly what is
missing:**

- `resolved` with no fix pointer, or with a pointer but no verification.
- The symptom still reproduces, the relevant tests fail, or the issue's
  `## 下一步` / `## Next Steps` still lists an unresolved investigation
  step.
- `proposed` but the work item does not exist.
- `merged` but the absorbing path does not exist.
- `wontfix` with no explicit user decision.

When a hard stop hits, report `NOT CLOSED: <mode>` with the gap list and
offer the honest alternatives: keep the issue active; close as `wontfix`
if the user knowingly stops tracking it; close as `proposed` once a work
item exists. **Never relabel an unresolved issue as `resolved`.**

**Informed override.** If the user explicitly says to close an issue
that is still unresolved, do not use `resolved`: use `wontfix` with a
reason such as "closed without a verified fix by user decision", or
`proposed` when a work item takes it over. If the user has manually
verified the fix but there is no automated or device evidence, that is a
legitimate `resolved` close — write the verification field honestly
(`用户手动验证；无自动化/设备证据` / `user manually verified; no
automated or device evidence`) rather than leaving it blank.

### 4b — Document integrity (advisory; structural blockers stop)

Before moving, check:

- `README.md` exists in the issue directory.
- The README does **not** already carry a `## 闭环` / `## Closure`
  section — that means it was closed before; stop and ask instead of
  writing a second close record.
- Every path under `## 关联` resolves (active or archived) — a pointer
  to a missing path would become a dangling reference in the archive.
- When the mode is `proposed`, the pointer target
  (`changes/<type>/<name>/`) actually exists; 4a blocks otherwise — never
  switch modes silently to get past the gate.

Report deficiencies in the final summary. Once 4a passes, the close
proceeds regardless of 4b deficiencies — except for a missing README or
an existing 闭环, which are hard stops.

## Step 5 — Close (order of operations is MANDATORY — move first, then write)

1. **Move the issue directory into the archive** — the directory name
   does not change. First verify `<docs-dir>/issues/archive/<name>/`
   does not already exist — if it does, FAIL HARD, report the collision,
   and ask; never nest one issue inside another:

   ```bash
   mkdir -p <docs-dir>/issues/archive
   mv <docs-dir>/issues/<name> <docs-dir>/issues/archive/<name>
   ```

2. **Then append the close record** to the issue README. The README's
   existing language decides the heading — a Chinese issue gets
   `## 闭环`, an English issue gets `## Closure`; never mix. Replace the
   `<!-- ## 闭环 — ... -->` placeholder comment if the README still
   carries it:

   ```markdown
   ## 闭环

   - 方式: resolved
   - 日期: 2026-10-20
   - 指向: <commit / PR / work item path / reason>
   - 验证: <测试结果 / 设备验证 / 用户确认；proposed / wontfix / merged 可写 n/a>
   ```

   English issues:

   ```markdown
   ## Closure

   - Mode: resolved
   - Date: 2026-10-20
   - Pointer: <commit / PR / work item path / reason>
   - Verification: <test result / device check / user confirmation; `n/a` for proposed / wontfix / merged>
   ```

   Every reference is written with the POST-MOVE archive path
   (`issues/archive/<name>/…`), never the pre-move active path — that
   path stops resolving the moment the move lands.

3. **Commit the docs repo** — `git add issues/` (the parent directory)
   stages both sides of the move (the new archive path and the old
   active path's deletion):

   ```bash
   cd <docs-dir>
   git add issues/
   git commit -m "docs: close issue <name> (<mode>)"
   ```

## Step 6 — Report

Output a summary:

```
Closed: <name> (<mode>)
From: <docs-dir>/issues/<name>/
To:   <docs-dir>/issues/archive/<name>/
Date: <YYYY-MM-DD>
Pointer: <commit / PR / work item path / reason>
Verification: <how closure was confirmed; n/a for proposed / wontfix / merged>

Notes:
- <any integrity warnings from Step 4b>
- <the problem is tracked by work item X, not fixed — proposed mode>
```

## After Closing

- **Closed is closed** — the archived issue is never edited again. New
  findings go to the work item's `progress.md` (when the mode was
  `proposed`), or into a NEW issue cross-referenced from both sides
  under `## 关联` (when the problem resurfaces). There is no reopen.
- `## 更新记录` is not modified at close time — the `## 闭环` block is
  the close record.

## Boundaries

| You actually want | Use |
|---|---|
| Archive a completed work item under `changes/` | `fullstack-archive` |
| Record or update an active issue | `fullstack-issue-create` |
| A GitHub / GitLab / Jira issue | `gh-operations` / `jira` |
| Reopen a closed issue | Not possible — create a new issue and cross-reference |

## Requirements

- Python 3.10+
- Workspace initialized by `fullstack-init` (must pass workspace
  validation gate)
- An ACTIVE issue under `<docs-dir>/issues/` that the user confirms is
  closed, together with its close mode and pointer

## Guardrails

- The docs repo is the ONLY repo touched. No code repos are modified,
  no branches are created.
- Closing is a move, not a delete — the directories are project history.
- Never overwrite an existing archive directory. If
  `issues/archive/<name>/` already exists, FAIL HARD, report the
  collision, and ask the user how to proceed.
- Only ACTIVE issues (under `issues/`) can be closed; an archived issue
  is read-only forever.
- Never close an unresolved issue as `resolved`. If the fix is not
  verified, keep it active or record `wontfix` with the user's explicit
  decision.
- The `验证` / `Verification` field is part of the close record — it must
  not be empty for a `resolved` close.
- Never guess the close mode; ask when it cannot be inferred from the
  issue record or the session context.
