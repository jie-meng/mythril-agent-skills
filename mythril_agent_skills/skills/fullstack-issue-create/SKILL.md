---
name: fullstack-issue-create
description: |
  Record or update a workspace issue in the docs repo's issues/ directory —
  capture a problem, bug, or phenomenon now so it can be triaged into a work
  item later. One skill, two operations (create / update); closing is a
  separate lifecycle operation owned by fullstack-issue-archive. Trigger:
  "fullstack issue", "全栈 issue", "记录一个工作区 issue"; ALSO when the
  user asks to record a problem/bug/phenomenon for later triage in this
  workspace — "记录这个问题", "把这个 bug 先记下来", "先记个 issue 以后再处理",
  "沉淀一个问题", "track this problem", "log this problem", "note this issue
  for later". For closing an issue ("close issue", "archive issue",
  "归档 issue"), use fullstack-issue-archive instead. NOT for GitHub/GitLab/Jira
  issues — requests mentioning gh/github/a remote repo/an issue URL route to
  gh-operations or jira instead. Bare English "create an issue" defaults to
  GitHub unless workspace context is present. Ambiguous bare "issue" with no
  platform context → this skill, announced, GitHub offered.
license: Apache-2.0
---

# Fullstack Issue Create

Record a problem in the docs repo's `issues/` directory before it can
become a work item — a lightweight, evidence-first issue slip that
`fullstack-explore` and `fullstack-propose` later consume. One skill,
two operations:

| Operation | When | What happens |
|-----------|------|--------------|
| **Create** | A problem is observed but cannot be planned yet | New issue dir under `issues/` with README.md + `log/` evidence |
| **Update** | New findings or evidence for an active issue | Dated entry in 更新记录, files added to `log/` |

Closing is a distinct lifecycle operation handled by
**`fullstack-issue-archive`** — this skill never performs it (see Step 3).

## Core Principle — Directory Location Is the State（目录位置即状态）

An issue's lifecycle state is its directory location — the same
philosophy as the work item system (`changes/`), deliberately
isomorphic:

| Location | State |
|----------|-------|
| `issues/YYYY-MM-DD-<kebab-name>/` | Active (recorded, awaiting triage) |
| `issues/archive/YYYY-MM-DD-<kebab-name>/` | **Closed** (proposed / resolved / wontfix / merged) |

There is no `Status` field. Unlike work items — which only gain a date
prefix when archived — an issue carries its record date in its name
from birth, so the archive listing sorts naturally by record day.
Closing is a directory **move**, never a delete: the directories are
project history. The close itself is performed by
`fullstack-issue-archive`.

## Prerequisites — Workspace Validation Gate (MANDATORY SCRIPT CALL)

This skill MUST NOT proceed past this gate. Run `check_workspace.py`
and inspect its output.

```python
import pathlib, subprocess, sys

candidates = [
    pathlib.Path.home() / ".config/opencode/skills/fullstack-issue-create/scripts/check_workspace.py",
    pathlib.Path.home() / ".claude/skills/fullstack-issue-create/scripts/check_workspace.py",
    pathlib.Path.home() / ".copilot/skills/fullstack-issue-create/scripts/check_workspace.py",
    pathlib.Path.home() / ".cursor/skills/fullstack-issue-create/scripts/check_workspace.py",
    pathlib.Path.home() / ".gemini/skills/fullstack-issue-create/scripts/check_workspace.py",
    pathlib.Path.home() / ".codex/skills/fullstack-issue-create/scripts/check_workspace.py",
    pathlib.Path.home() / ".qwen/skills/fullstack-issue-create/scripts/check_workspace.py",
    pathlib.Path.home() / ".grok/skills/fullstack-issue-create/scripts/check_workspace.py",
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

## Document/Issue Language Selection

The issue's `README.md` language follows the user's prompt — the same
rule as the work-tracking documents:

1. If the user **explicitly requests a language** → use that language.
2. If the user's prompt contains **any Chinese characters** → use Chinese.
3. Otherwise → use English (default).

Directory names are ALWAYS lowercase-hyphenated English regardless of
the README language.

The skeleton in Step 1 shows Chinese labels (spec keywords, kept in
Chinese). When writing an English issue, substitute the labels from
this table — the section set and their order never change:

| 中文 | English |
|------|---------|
| `**记录时间**` | `**Recorded**` |
| `**领域**` | `**Domain**` |
| `**涉及**` | `**Involves**` |
| `**证据**` | `**Evidence**` |
| `## 现象` | `## Symptom` |
| `## 证据` | `## Evidence` |
| `## 分析` | `## Analysis` |
| `## 已排除` | `## Ruled Out` |
| `## 关联` | `## Related` |
| `## 下一步 / 排查方向` | `## Next Steps` |
| `## 更新记录` | `## Update Log` |
| `## 闭环` | `## Closure` |

## Step 1 — Create: Record a New Issue

1. **Locate the docs dir** — `DOCS_DIR` from the validation gate.
2. **Ensure the directories exist** — do NOT depend on `fullstack-init`
   having run recently; old workspaces self-provision:

   ```bash
   mkdir -p <docs-dir>/issues/archive
   ```

3. **Name the issue directory** `YYYY-MM-DD-<kebab-name>`:
   - **Date = the record day (today)** — fixed at birth, never changes.
   - `<kebab-name>`: short lowercase-hyphenated English slug, e.g.
     `brownout-during-4g-bursts`.
   - **Collision**: if `<docs-dir>/issues/YYYY-MM-DD-<name>/` already
     exists, append a `-HHMM` suffix (current time) — check BEFORE
     creating. Never overwrite an existing issue.
4. **Store raw evidence in `log/`** (rules below).
5. **Write `README.md`** using the fixed skeleton (below).
6. **Commit the docs repo** (directly on its main branch):

   ```bash
   cd <docs-dir>
   git add issues/YYYY-MM-DD-<name>
   git commit -m "docs: record issue <name>"
   ```

### log/ Rules (MANDATORY)

- The issue directory contains a `log/` subdirectory holding the raw
  captured files (device dumps, tool outputs, scenario recordings).
- **Filename**: `YYYY-MM-DD-<source>[-<description>].log` — the source
  is a device id, a tool, or a scenario, e.g.
  `log/2026-10-11-robo-az3-serial-capture.log`.
- **A raw file is NEVER modified once archived.** To keep a trimmed or
  filtered version, write a derived file with the SAME basename plus a
  `.cleaned.log` suffix (e.g.
  `log/2026-10-11-robo-az3-serial-capture.cleaned.log`) and state the
  derivation in the README's 证据 section — raw and processed evidence
  never blur.
- **Large files are trimmed to the relevant time window BEFORE
  archiving**, so the docs repo does not bloat.

### README.md Fixed Skeleton

```markdown
# <one-sentence title: what device/module shows what symptom>

**记录时间**: 2026-10-11 14:30

**领域**: 固件 (firmware)

**涉及**: <repo> @ <version>, device <id>

**证据**: log/2026-10-11-robo-az3-serial-capture.log

## 现象

<observed behavior — one-line conclusion plus reproduction conditions>

## 证据

- `log/2026-10-11-robo-az3-serial-capture.log` — 串口原始日志（来源：设备 robo-az3 串口抓取）
- `log/2026-10-11-robo-az3-serial-capture.cleaned.log` — 原始件的精简版（派生方式：仅保留 14:28–14:35 时间窗与 ERROR 行）

## 分析

<current hypothesis and reasoning — evolves with 更新记录>

## 已排除

- <ruled-out cause + one line of why it was ruled out>

## 关联

- 相关 issue: <issues/YYYY-MM-DD-...> 或 issues/archive/YYYY-MM-DD-...（无则删行）
- 工作项: <changes/<type>/<name>>（无则删行）

## 下一步 / 排查方向

- <actionable investigation step>

## 更新记录

- 2026-10-11 — 创建 issue，录入初始现象与证据。

<!-- ## 闭环 — 关闭时才追加（fullstack-issue-archive）：方式 + 日期 + 指向 -->
```

Skeleton rules:

- The field area (记录时间 / 领域 / 涉及 / 证据) uses bold labels with
  **exactly one blank line between each bold field line**.
- **领域** is free text — 硬件 / 固件 / 后端 / 应用 / 流程 / …
- **涉及** lists the repos, device ids, and versions concerned.
- **证据** lists the `log/` files.
- `## 证据` (section) points at each `log/` file and says where it came
  from; derived `.cleaned.log` files state their derivation.
- `## 关联` cross-references related issues (active or archived), work
  items, and archived work items; delete lines that do not apply.
- `## 更新记录` is append-only — one dated entry per update.
- `## 闭环` is appended ONLY at close time by
  `fullstack-issue-archive`; at create time it stays a placeholder
  comment. There is **no `Status` field** anywhere.

## Step 2 — Update: Append to an Active Issue

Only ACTIVE issues (under `issues/`) may be updated:

1. Append a dated entry to the README's `## 更新记录` — what was
   learned, tried, or decided (one line per entry).
2. New evidence goes into `log/` under the same naming rules
   (`YYYY-MM-DD-<source>[-<description>].log`; raw files immutable;
   trimmed versions as `.cleaned.log`), and is mentioned in `## 证据`.
3. Commit the docs repo in the same round.

An ARCHIVED issue (under `issues/archive/`) must NEVER be edited. If
the problem resurfaces or the investigation continues, create a NEW
issue and cross-reference both directions under `## 关联`.

## Step 3 — Close: Delegate to `fullstack-issue-archive`

Closing is a separate lifecycle operation owned by the
**`fullstack-issue-archive`** skill — this skill only creates and
updates active issues. Do not improvise the close here: when the user
asks to close or archive an issue ("close issue", "archive issue",
"归档 issue"), invoke `fullstack-issue-archive`.

That skill owns all four close modes — `proposed`, `resolved`,
`wontfix`, `merged` — plus the move into `issues/archive/`, the
`## 闭环` record, and the docs-repo commit. Before moving, it verifies
the issue is genuinely settled (a fix pointer plus verification for
`resolved`, an existing work item for `proposed`) and refuses to
relabel an unresolved issue as `resolved`. In short:

| Mode | Meaning |
|------|---------|
| `proposed` | Became a work item (`changes/<type>/<name>/`) |
| `resolved` | Fixed directly, no work item needed (pointer: the commit) |
| `wontfix` | Reviewed, deliberately not pursued |
| `merged` | Folded into another issue or work item |

Two rules remain visible from here:

- Only ACTIVE issues (under `issues/`) can be updated; an archived
  issue is read-only forever.
- When closing as `proposed`, the pointer target is the work item
  directory `fullstack-propose` just created and committed — the
  propose flow closes the issue in the same round its four
  work-tracking documents are committed to the docs repo.

## Boundary with GitHub / GitLab / Jira Issues

This skill records WORKSPACE issues in the docs repo. It is **NOT a trigger** for platform issue tracking:

- Requests mentioning `gh`, GitHub, GitLab, Jira, a remote repository,
  or an issue URL → route to `gh-operations` (or `jira`) instead; do
  NOT run this skill.
- Bare English "create an issue" defaults to a GitHub issue unless the
  workspace context is clearly present.
- A genuinely ambiguous bare "issue" with no platform context defaults
  to THIS skill — but announce it in one sentence (e.g. "先记到工作区
  issues/ 目录") and offer to file a GitHub issue instead if that was
  what the user meant.

## Requirements

- Python 3.10+
- Workspace initialized by `fullstack-init` (must pass workspace
  validation gate)
- A docs repo (independent git repo) whose root is `DOCS_DIR`

## Guardrails

- The docs repo is the ONLY repo touched. No code repos are modified,
  no branches are created.
- Nothing under `issues/` is ever deleted — the directories are
  project history. Closing is a move into `issues/archive/`, not a
  removal.
- Same-day name collisions get a `-HHMM` suffix — never overwrite an
  existing issue directory.
- Raw evidence files are immutable once archived; trimming produces a
  `.cleaned.log` derivative, never an in-place edit.
- Only active issues (under `issues/`) can be updated; archived issues
  are read-only forever. Closing is delegated to
  `fullstack-issue-archive`.
