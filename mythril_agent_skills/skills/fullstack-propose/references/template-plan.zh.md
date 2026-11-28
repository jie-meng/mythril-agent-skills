## `plan.md`

### Status is the directory location — no Status field

The lifecycle state of a work item is expressed by its directory
location, NOT a text field. Active work lives in
`<docs-dir>/changes/<type>/<work-name>/`; archived work lives in
`<docs-dir>/changes/archive/YYYY-MM-DD-<type>-<work-name>/`. Do NOT
write a `**Status**:` field in `plan.md`.


### Chinese

```markdown
# <工作名称>

**来源**：<Jira 链接 / 用户需求 / Confluence 页面 / 前置工作项>

**类型**：feat | refactor | fix

**分支**：<branch-name>

**创建时间**：<date>

## 摘要（给人读的——全工作项唯一允许原地更新的章节）

**一句话**：<这是什么问题、打算怎么解决。不引用编号，不引用文件名。>

**大白话**：<上线之后哪里会变得不一样——一行给不写代码的人看的话，不引用编号；有残留风险就带一句最大的风险。>

**状态**：<规划中 | 审查通过待实施 | 实施中 | 已完成>——<lean | full> 档——<一行最新结论，如：方案审查第 2 轮 PASS>

**需要你决策的事**：<无；或每条一行：问题 → 选项 → 我们的推荐>

**没解决的事**：<明确排除项、待验证项、残留风险——每条一行>

**读哪里**：问题细节→analysis.md；怎么实施→本文件正文；审查与证据→review.md

## 需求

<根据采集到的上下文整理的需求摘要>

## 成功标准

<可测试、具体的验收标准 —— "能正常工作" 不算标准；"对输入 A、B、C
返回符合 schema X 的 200 响应" 才算。每条标准在 review.md 中对照证据核验。
每条标准带一个 `SC<n>` 编号——不加连字符，工作项内顺序编号、不复用。证据
核验表与需求覆盖矩阵引用这个编号，`plan_lint.py` 也按编号把证据行对上标准。>

- [ ] **SC1** — <可观察行为 + 预期结果>
- [ ] **SC2** — <...>
- [ ] **SC3** — <...>

## 涉及仓库（按依赖顺序）

| # | 仓库 | 分支 | 变更内容 | 依赖 | 优先级 |
|---|------|------|---------|------|--------|
| 1 | shared-lib | feat/Dark-Mode-Toggle | 添加主题类型定义 | — | P0 |
| 2 | api | feat/BE-450/Dark-Mode-Toggle | 添加偏好设置接口 | shared-lib | P0 |
| 3 | android | feat/MOBILE-301/Dark-Mode-Toggle | 添加切换页面 | shared-lib, api | P1 |

仓库必须按依赖顺序列出：上游优先（共享库、数据模型），然后是服务层
（api、backend），最后是消费者（web、ios、android）。fullstack-apply
依据本表推导并行波次——无依赖边交叉的仓库会同时开发与提交。所有被下
游消费的跨仓接口必须在 analysis.md 中冻结（精确字段名、类型、错误码）：
并行开发者以冻结契约为准，而非可能尚未实现的上游代码。

## 代码地图（Code Map）

<反向索引——本工作项拥有哪些文件。规划阶段先填计划要改的路径；
fullstack-apply 在每一轮把预测路径换成实际改动路径。后来的人靠这张表
从文件路径找回对应的工作项，因此"改了代码却没登记在这里"等于留下一处
无法追溯的改动。>

| 仓库 | 路径 | 符号 | 改了什么 |
|------|------|------|---------|
| api | `src/preferences/dark_mode.py` | `ThemePreference`、`GET /pref` | 新增偏好设置接口 |
| android | `app/src/ui/SettingsScreen.kt` | `DarkModeToggle` | 设置页新增开关行 |

规则：

- **路径相对仓库根目录**（`src/preferences/dark_mode.py`），不写机器绝对
  路径，也不只写文件名。仓库列 + 仓内相对路径这两列合起来，才能被工作区
  相对路径反查到。确实在仓库根的文件写作 `./README.md`——`./` 表示"就在
  根"，而光一个 `README.md` 让反查无法判断它和别的仓库同名文件谁是目标。
- **符号列可留空**——文件名说不清改了什么时必填。它是"只知道 `computeWave`
  这个函数算错了、不知道在哪个文件"这种提问的检索入口。
- **整表原地更新**。与 progress.md 不同，这里记录当前状态而不是流水账：
  改后又回滚的路径不再保留，历史留在 progress.md。但此前轮次改过的
  路径要留着——这张表是整个工作项的归属清单，不是本轮的 diff。
- **一行一个文件**，不写区间（`src/ui/*`），也不把多个文件塞进一格
  （`src/a.py`、`src/b.py`）——通配符与合并格都无法被路径检索命中，等于
  悄悄丢掉它覆盖的每个文件的追溯性。目录（`src/ui/`）与占位符（`—`、
  `待定`）同样不算登记了一个文件。

## 实现计划

<每个任务带一个 `T<n>` 编号，跨阶段顺序编号、不复用；审查轮次与需求覆盖
矩阵引用这个编号。>

### 阶段一：<名称>
- [ ] **T1**（repo-x）— <任务>
- [ ] **T2**（repo-y）— <任务>

### 阶段二：<名称>
- [ ] **T3**（repo-x）— <任务>

## 依赖关系

<跨仓库依赖、顺序约束>

## 风险 / 待确认问题

**活风险**

| # | 风险 | 可能性 | 影响 | 应对 |
|---|------|--------|------|------|
| R1 | <风险，直接写结论> | 中 | 高 | <应对> |

**已闭环**

（无——核销的风险移到这里，各保留一行：为何闭环、在哪里解决。行不删除；
分区让"现在还悬着什么"一眼可读。）
```

Update timing for the summary（`## 摘要` / `## Summary`）: rewrite it when
the plan-review verdict changes, when requirements change, and at
implementation close-out. History stays in `progress.md` / `review.md` —
this section states only the current position. 方案审查结论变化、需求变更、
实施收尾时更新；历史留在 progress/review，本节只写当前。


### Successor addition

When this work item inherits from an archived predecessor, add a
`Predecessor` line to the header right after `Created`:

- English: `**Predecessor**: feat/dark-mode/ (archived 2026-04-15)`
- Chinese: `**前置工作**：feat/dark-mode/（2026-04-15 归档）`

---
