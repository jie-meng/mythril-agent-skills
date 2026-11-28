## `review.md` header


### Chinese

```markdown
# 审查：<工作名称>

本文件是该工作项的证伪记录。规范顺序：状态速览（原地更新）→ 证据核验
（此处预填，代码审查逐仓库填写，收尾补齐）→ 方案审查轮次（fullstack-propose）→ 代码审查
轮次与跨仓库审查（fullstack-apply）→ 最终结论。

## 状态速览（本节原地更新；其下所有轮次与证据 append-only）

**最新结论**：<方案审查 PASS_WITH_RISKS（第 N 轮）| 已完成——最终结论见文末>

**审查轮次**：<方案审查 N 轮；代码审查 M 轮（repo 名）>

**活风险**：<N 项，每项一行：编号（人话描述，怎么跟进）>

**待决策**：<无 | 列表>

## 证据核验

由 fullstack-propose 预填：plan.md 中每条成功标准一行（全部标 `待核验`），
各仓库代码审查时填写对应证据，收尾阶段补齐其余。这里没有行的成功标准就是没人核验的标准——
`plan_lint.py` 会在交付门与收尾门上报错。

| 成功标准 | 结果 | 证据 |
|---------|------|------|
| 标准 1 | ✅ 通过 | <测试结果 / PR 链接 / 截图> |
| 标准 2 | ❌ 未通过 | <反证依据> |
| 标准 3 | ⚠️ 跳过 | <测试未运行 — 无框架或无已记录的运行命令> |
```

The per-round review section format and cross-repo review format are
defined in `review-formats.<lang>.md`.

---


## Plan review round

Written by **fullstack-propose** (Step 4.5), one section per round, before
any implementation starts. The plan-reviewer subagent returns the content; the
orchestrator appends it. Section labels follow the work item's language.


### Chinese

```markdown
## 方案审查 — 第 <N> 轮 — <date>

### 审查范围

- 文档：analysis.md、plan.md — <与上一轮的差异>
- 需求来源：analysis.md §需求原文 + §澄清记录（REQ ids + Q ids）— <有 Jira / Confluence 时附编号>
- 代码核验：<检查的仓库> — graphify：已用 | 跳过：<理由> | 无

### 需求覆盖

`analysis.md` §需求原文 里每个 `REQ` 编号一行——声明了却在这里缺行，
或这里引用了未声明的编号，`plan_lint.py` 都会报错。用编号，不要用转述：
`R<n>` 是 plan.md 风险表的编号，`REQ<n>` 才是需求的编号。

| 需求 | 对应成功标准 | 对应任务 | 状态 |
|------|------------|---------|------|
| REQ1 | 标准 1 | 阶段一 / 任务 2 | 覆盖 |
| REQ2 | — | — | **遗漏** |
| REQ3 | 标准 2 | 阶段一 / 任务 3 | **收窄** — <砍掉了什么，以及由谁裁定> |

### 问题清单

- [P0] <文档/章节> — <问题> — 影响：<会出什么错> — 建议：<如何解决>
- [P1] <文档/章节> — <问题> — 影响：<返工成本> — 建议：<...>

### 已核验

<一行：核验了多少条论断、哪几类（路径、符号、契约、机制）。完整清单留在审查代理的
返回里，不抄进本文件——之后每个代理都要重读它。>

### 未核验

- <无法核验的内容及所需条件>

### 结论

<PASS | PASS_WITH_RISKS | NEEDS_FIXES | NEEDS_USER_DECISION> — <总结>

### 待决策事项（仅 NEEDS_USER_DECISION）

| 决策点 | 选项 | 为何 AI 无法决定 | 是否阻塞 |
|-------|------|----------------|---------|
| <问题> | A / B | <产品或策略选择> | 是/否 |
```

结论含义：`PASS`（可直接实施）、`PASS_WITH_RISKS`（无未决 P0/P1，风险
已列明）、`NEEDS_FIXES`（planner 可自行修复的 P0/P1）、
`NEEDS_USER_DECISION`（阻塞项只能由人决定）。`FAIL` / `BLOCKED` 属于
代码审查结论，不适用于方案。

planner 拒绝某条问题时，orchestrator 在同一轮记录：

```markdown
- [P0] <问题> — **已拒绝**：<planner 的理由>
```

未经 `已拒绝` 标注即在修订中消失的问题，在下一轮按新的 P0 处理。


### Author self-check (optional section)

An author's own pre-check of the plan is allowed and often worth
recording — it catches cheap things before the independent audit runs.
It is a **working artifact, not a gate**: its conclusion never
substitutes for a `## Plan Review` round, and the exit criteria ignore
it. Record it above the first plan-review round, clearly labelled:

```markdown
## 设计复核（可选，作者自审，非门禁）— <date>

**结论**：<作者的判断，仅供参考>
```

```markdown
## Design Self-Check (optional, author, NOT a gate) — <date>

**Conclusion**: <the author's own assessment — informational only>
```

### Reconciliation after a revision (MANDATORY)

Planner revisions touch one document at a time and the chain drifts.
After applying revisions, sync in the same edit:

| Revision | Must also update |
|----------|------------------|
| Success Criteria added / renamed / removed | the `## Evidence` table rows in `review.md` |
| A task added / removed / rescoped | the affected-task list in the round's 修订 section |
| Any round or revision | a dated section in `progress.md` |
| A diagram | re-run the Mermaid gate |
| The repositories table | re-run the DAG gate |

Then run the consistency gate:

```bash
python3 SKILL_PATH/scripts/plan_lint.py <docs-dir>/changes/<type>/<work-name>
```

`STATUS=PASS` is required before the plan may be reported ready. It
reports an unclosed review (last round ending in `NEEDS_FIXES`), an
Evidence row missing for a criterion, broken round numbering, and task
ids that no longer exist.

---
