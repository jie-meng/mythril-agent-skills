# Follow-up Mode — Building on Closed Work

After a work item is **closed** (PR merged, shipped to production),
real projects keep evolving. Days, weeks, or months later, the user
asks for follow-on changes that build on the same shipped feature or
fix — extend the dark-mode toggle to follow system, harden the login
fix for one more edge case, refactor the import/export flow that
already shipped.

These are NOT iterations of the closed work item — that ship has
sailed, that PR is merged, that branch is deleted. They are **new
work items with predecessor context**. Follow-up Mode is the protocol
that ensures:

1. The new work runs through the full Step 1-9 flow (it IS a new
   work item, not a casual edit).
2. The new work explicitly inherits and references the predecessor's
   analysis / plan / learnings — so the agent does not re-derive
   decisions the predecessor already settled.
3. The predecessor's docs gain a back-link, so the audit trail
   evolves into a chain instead of orphaned silos.

> Reading order: this document covers Follow-up Mode in depth. For a
> quick comparison with Reference Mode and Iteration Mode, see
> [`mode-selection.md`](mode-selection.md).

## When Follow-up Mode applies

Follow-up Mode kicks in when ALL of these are true:

1. The current request targets the **same scope** as a previously
   closed work item (same feature area, same repos, often the same
   Jira theme).
2. The matching work directory's `plan.md` `Status` normalizes to
   `Closed` (any of: `Closed`, `已关闭`, `Merged into main`, `Shipped`,
   `已合并`, `已发布`, `已上线`).
3. The user uses an explicit follow-up verb (see "Triggers" below) OR
   the user confirms a follow-up proposal when asked.

`route_check.py` checks all three deterministically and returns
`ROUTE=Followup` only when they hold. If any of these are not met →
it is NOT Follow-up Mode. Either:
- A new fresh work item (no predecessor link), OR
- Reference Mode — see [`reference-mode.md`](reference-mode.md), OR
- Iteration Mode — see [`iteration-mode.md`](iteration-mode.md), OR
- AskUser (the script will prompt the 3-option clarifying question).

## Iteration vs Follow-up — the boundary

The two modes look similar (both modify a previously-finalized work
item) but differ in lifecycle stage, naming, and audit trail. Picking
the wrong one is expensive — see the cost table below.

| Aspect | Iteration | Follow-up |
|--------|-----------|-----------|
| Trigger condition | Status = `Done` (PR not yet merged) | Status = `Closed` (shipped) |
| Work directory | Same (`<work-name>/`) | New (`<work-name>-vN/`) |
| Branch suffix | `-iter-N` (per round) | `-vN` (per follow-up work item) |
| `Predecessor:` field | No | Yes (mandatory) |
| `## Predecessor Context` section | No | Yes (mandatory) |
| `## Successors` back-link in old dir | No | Yes (mandatory) |
| Backward-compat cross-repo check | No | Yes |
| Cost of misroute (Iteration → Followup) | Phantom `-v2` directory + back-link in a Done dir | Cleanup needs `git mv` + delete back-link |
| Cost of misroute (Followup → Iteration) | Iteration audit trail spans two effective work items | Cleanup needs reopening the closed dir |

### Boundary case — Status = Done but commits already on default branch

When the work item's status is `Done` (not `Closed`) but the feature
branch was already merged to default (commits exist there, original
branch deleted), the route is genuinely ambiguous:

- It could be **Iteration**: the work was finalized, the PR was
  squash-merged for convenience, but the user / team still considers
  the work "open" until production deployment.
- It could be **Follow-up**: the work is effectively shipped (default
  branch is the truth), the user's request is a real continuation.

`route_check.py` returns `ROUTE=AskUser` here. Ask the user the
3-option clarifying question (Follow-up / Iteration on hotfix branch /
Independent fresh fix) — see [`mode-selection.md`](mode-selection.md).
Do NOT auto-pick.

### Quick decision flow

```
Status normalizes to ...
  ├── Done    → Iteration  (with -iter-N branch via the matrix in iteration-mode.md)
  ├── Closed  → Follow-up  (with -vN dir + branch, predecessor inheritance)
  └── Unknown → AskUser    (status field is free-form; agent cannot decide)
```

## Triggers — explicit verbs only

Follow-up Mode is entered ONLY when the user uses an explicit
follow-up verb. The agent does NOT auto-propose follow-up based on
scope overlap alone — overlap is a signal to ASK, not to act.

### Recognized follow-up verbs

| Language | Phrasing |
|----------|----------|
| English | "follow up on X", "extend X", "build on top of X", "on top of X", "based on X (work / docs)", "继续做 X" |
| Chinese | "在 X 基础上", "基于 X 做后续", "X 的后续", "扩展 X", "follow up X" |

The user must name the predecessor (the closed work directory's name,
or a clear synonym like the feature name). When the user names the
predecessor with one of these verbs, route to Follow-up Mode without
further questions.

### When the user does NOT use a follow-up verb

If the user describes a request whose scope happens to overlap a
closed work item but uses no follow-up verb:

- Default to **a fresh new work item** (no predecessor link).
- IF the overlap is high (same repos AND same surface), present a
  clarifying question:

  ```
  I noticed a closed work item that overlaps your request:
    feat/dark-mode/  (Closed 2026-04-15)

  Three ways to proceed:

    A) Follow-up — create feat/dark-mode-v2/ that explicitly builds on
       the closed work, inheriting its decisions and architecture.
       Best when this is a true continuation of dark-mode.

    B) Reference — start a fresh work item, but I'll read
       feat/dark-mode/'s docs as background context (no Predecessor
       link, no back-link in the old dir). Best when your work is
       related but independent.

    C) Independent — start a fresh work item with no link to dark-mode
       at all. Best when the overlap is coincidental.

  Which fits?
  ```

  Wait for the user's pick before proceeding. Do NOT pick A
  unilaterally. Picking the wrong route here costs more than asking.

## Naming convention — `-vN` suffix

Predecessor and successor are sibling directories under the same work
type. The successor's name is derived from the predecessor by
appending `-v2`, `-v3`, etc.

```
<docs-dir>/feat/
├── dark-mode/                  # Closed predecessor (untouched)
│   ├── analysis.md
│   ├── plan.md
│   ├── progress.md             # ← gets a Successors back-link appended
│   └── review.md
├── dark-mode-v2/               # First follow-up
│   ├── analysis.md             # ← Predecessor field + Predecessor Context section
│   ├── plan.md                 # ← Predecessor field
│   ├── progress.md
│   └── review.md
└── dark-mode-v3/               # Second follow-up (only if v2 is also closed later)
    └── ...
```

**Rules:**

- The successor lives in the **same `<type>/` directory** as the
  predecessor — a follow-up to a `feat/` work is also `feat/`. If
  the follow-up is fundamentally a fix on shipped code, classify as
  `fix/` and use `fix/<name>/` instead — but link the predecessor
  in the same way.
- `-v2` always counts from the original — `dark-mode` →
  `dark-mode-v2`, not `dark-mode-v1-v2`. If `dark-mode-v2` is later
  closed and a third follow-up arrives, the new directory is
  `dark-mode-v3` (NOT `dark-mode-v2-v2`).
- Lowercase-hyphenated, English-only — same as all work directory
  names.

## Branch naming — `-vN` suffix on the descriptive part

Append `-v2`, `-v3`, etc. to the descriptive title in each affected
repo's branch name. The Jira key may change (new ticket for the new
work) or stay the same (rare, but allowed):

| Scenario | Predecessor branch | Successor branch |
|----------|-------------------|------------------|
| New Jira ticket for follow-up | `feat/MOBILE-301/Dark-Mode-Toggle` | `feat/MOBILE-580/Dark-Mode-Toggle-v2` |
| Reusing same Jira (allowed, but warn) | `feat/MOBILE-301/Dark-Mode-Toggle` | `feat/MOBILE-301/Dark-Mode-Toggle-v2` |
| No Jira | `feat/Dark-Mode-Toggle` | `feat/Dark-Mode-Toggle-v2` |

When the user reuses the same Jira key, gently suggest opening a new
ticket — but do not block on this. The user may have valid reasons.

**Branch source**: successor branches start from the repo's **current
default branch**, NOT from the predecessor's merged feature branch.
The predecessor's branch is dead — basing on it inherits stale code.

## Predecessor inheritance — MANDATORY fields

Every successor's `analysis.md` and `plan.md` MUST add a
**Predecessor** line to the header right after `Status`:

**English:**

```markdown
**Source**: <Jira link / user prompt>
**Type**: feat | refactor | fix
**Branch**: <branch-name>
**Created**: <date>
**Status**: Planning
**Predecessor**: feat/dark-mode/ (closed 2026-04-15)
```

**Chinese:**

```markdown
**来源**：<Jira 链接 / 用户需求>
**类型**：feat | refactor | fix
**分支**：<branch-name>
**创建时间**：<date>
**状态**：规划中
**前置工作**：feat/dark-mode/（2026-04-15 关闭）
```

## `analysis.md` — MANDATORY `## Predecessor Context` section

Every successor's `analysis.md` MUST contain a `## Predecessor
Context` (English) or `## 前置工作上下文` (Chinese) section, placed
IMMEDIATELY after the header and BEFORE `## Current State`. It
captures four things, concise, no copy-paste from the predecessor:

### English template

```markdown
## Predecessor Context

**Predecessor work**: [`feat/dark-mode/`](../dark-mode/) — closed 2026-04-15

### What was shipped

<2-4 lines summarizing what the predecessor delivered. The reader should
understand the baseline this follow-up builds on without opening the
predecessor's docs.>

### Decisions inherited (still valid)

- <Architectural / API / data-model decision from predecessor that this
  follow-up keeps as-is. One bullet per decision. Link the
  predecessor's analysis.md anchor when relevant.>
- ...

### Assumptions that changed (why we're back)

- <The specific reason this follow-up exists — a new requirement, a
  user-reported edge case, a refactor opportunity that became viable.
  This is the delta from "closed" to "needs more work".>
- ...

### Predecessor's known caveats / debt

- <Any "Follow-ups" notes, residual issues, or tech debt the
  predecessor explicitly recorded. State whether this follow-up
  addresses them or defers them again.>
```

### Chinese template

```markdown
## 前置工作上下文

**前置工作**：[`feat/dark-mode/`](../dark-mode/) — 2026-04-15 关闭

### 上一轮交付了什么

<2-4 行总结上一轮的交付物。让读者无需打开前置工作的文档即可理解
本轮的起点。>

### 沿用的决策（仍然有效）

- <上一轮做出的、本轮保留不变的架构 / 接口 / 数据模型决策。每条一行。
  必要时链接到前置工作 analysis.md 的具体章节。>
- ...

### 改变的前提（为什么要做后续）

- <本轮工作存在的具体原因 —— 新需求、用户反馈的边界情况、
  之前没条件做现在可以做的重构。这是从「已关闭」到「需要再动一次」
  之间的真正增量。>
- ...

### 上一轮已知的遗留 / 债务

- <前置工作 `## Follow-ups` 章节记录的事项、残留问题、或主动延后的
  技术债。说明本轮是否处理它们，或继续延后。>
```

The rest of `analysis.md` (Current State, Requirements, Design
Options, etc.) follows the standard template from
[`document-templates.md`](document-templates.md) — but keep the
Current State section concise where it overlaps with "Decisions
inherited", linking to the predecessor instead of repeating.

## Predecessor back-link — `## Successors` table

When a follow-up work directory is created, the predecessor's
`progress.md` MUST gain a `## Successors` (English) or `## 后续工作`
(Chinese) section appended at the very end. This makes the chain
discoverable from BOTH directions.

**English:**

```markdown
## Successors

| Date | Successor | Type | Reason |
|------|-----------|------|--------|
| 2026-05-02 | [`feat/dark-mode-v2/`](../dark-mode-v2/) | feat | Add follow-system option |
```

**Chinese:**

```markdown
## 后续工作

| 日期 | 后续工作 | 类型 | 原因 |
|------|----------|------|------|
| 2026-05-02 | [`feat/dark-mode-v2/`](../dark-mode-v2/) | feat | 增加跟随系统选项 |
```

If a third follow-up later arrives, append another row to the SAME
table in the original predecessor's `progress.md` (and add a
successor row to v2's `progress.md` as well — every closed work
item maintains its own Successors table for its direct children).

The predecessor commit happens in the **same docs-repo commit** as
the successor's initial four documents.

## Execution flow — Step 1-9 with adjustments

After the user confirms Follow-up Mode, run Steps 1-9 with these
adjustments:

| Step | Standard behavior | Follow-up adjustment |
|------|-------------------|---------------------|
| 1 — Gather Context | Read external links, workspace context | ALSO read the predecessor's four docs in full |
| 3 — Identify Affected Repos | Confirm repos with user | Show "Predecessor: feat/dark-mode/" in the confirmation block; default to the same repo set as predecessor unless requirements say otherwise |
| 4 — Branch Management | Create `<type>/<title>` branches | Append `-v2` (or `-vN`) to the descriptive title; branch source is the repo's default branch, NOT the predecessor branch |
| 5 — Create Work Plan | Create four files in `<type>/<work-name>/` | Use `<work-name>-vN/`; populate the `Predecessor` field; `analysis.md` MUST start with `## Predecessor Context`; append `## Successors` row to predecessor's `progress.md` |
| 6 — Implement | Per-repo serial implementation | Unchanged |
| 7 — Cross-Repo Review | Multi-repo consistency | Unchanged, plus the backward-compat addendum below |
| 8 — Create PRs | One PR per repo | Unchanged |
| 9 — Finalize Round 0 | Verify gates, commit docs | The four-file consistency gate MUST also verify the `Predecessor` field is present in `analysis.md` AND `plan.md`, and that `## Predecessor Context` is non-empty |

After Step 9, **Iteration Mode applies as usual** to the follow-up
work item. If the follow-up itself later closes and yet another
round of work comes, that round opens `<work-name>-v3/` linking back
to v2 (NOT back to v1 directly — every link points to the immediate
predecessor).

## Backward-compatibility gate (cross-repo review addendum)

Because the predecessor is shipped to production, the follow-up's
cross-repo review (Step 7) MUST add an explicit backward-compat
check:

- **API contracts**: any field / endpoint the predecessor introduced
  MUST remain compatible (or, if breaking, the change is an explicit
  goal of this follow-up and is documented in `analysis.md`'s Design
  Options).
- **Database migrations**: any migration MUST be additive or include
  a rollout / rollback plan compatible with the predecessor's
  deployed schema.
- **Shared types**: type evolution rules apply — adding optional
  fields is safe, removing or making fields required is a breaking
  change that must be explicit.

Append the backward-compat result as its own bullet under `Checks
Performed` in the cross-repo review section of `review.md`. See
[`review-formats.md`](review-formats.md) for the bullet format.

## Anti-patterns to refuse

| Anti-pattern | Why it's wrong | Correct behavior |
|--------------|---------------|------------------|
| Reopen the closed predecessor's work directory and add a new Iteration Log row | Closed means closed — Iteration Log is for pre-closure rounds only; reopening corrupts the audit trail | Create `<name>-v2/` and link via Predecessor + Successors |
| Skip `## Predecessor Context` because "the user knows the history" | Future readers, other agents, and the user themselves in 3 months don't have that context | Always write the section, even briefly |
| Copy-paste the predecessor's `analysis.md` into the successor | Duplicates content, drifts over time, hides what is actually new in this follow-up | Reference and link; only document what is NEW or DIFFERENT |
| Branch off the predecessor's old (merged) feature branch | That branch is dead; basing on it inherits stale code | Branch off the repo's current default branch — predecessor's code is already merged into it |
| Skip the back-link to predecessor's `progress.md` | Audit trail becomes one-directional; readers landing on the old work can't discover the follow-up | Always append `## Successors` to predecessor's progress.md in the same docs commit |
| Auto-propose follow-up based on scope overlap alone (without an explicit follow-up verb from the user) | Risks creating phantom Predecessor links the user did not ask for; expensive to clean up across two directories | Default to a fresh new work item; ASK if the overlap is high; only enter Follow-up Mode when the user picks A in the question |
